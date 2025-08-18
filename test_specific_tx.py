#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test specific transactions with detailed analysis
"""

import os
import json
import time
import logging
import requests
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class TransactionTester:
    def __init__(self):
        self.blockstream_api = 'https://blockstream.info/api'
        
    def get_transaction_data(self, txid):
        try:
            url = f"{self.blockstream_api}/tx/{txid}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching tx {txid}: {e}")
            return None
    
    def analyze_transaction_detailed(self, tx_data):
        """Phân tích transaction chi tiết"""
        input_count = len(tx_data.get('vin', []))
        output_count = len(tx_data.get('vout', []))
        
        # Extract addresses and values
        input_addresses = []
        output_addresses = []
        input_values = []
        output_values = []
        
        for vin in tx_data.get('vin', []):
            if 'prevout' in vin:
                if 'scriptpubkey_address' in vin['prevout']:
                    input_addresses.append(vin['prevout']['scriptpubkey_address'])
                input_values.append(vin['prevout'].get('value', 0))
        
        for vout in tx_data.get('vout', []):
            if 'scriptpubkey_address' in vout:
                output_addresses.append(vout['scriptpubkey_address'])
            output_values.append(vout.get('value', 0))
        
        # Calculate CoinJoin indicators
        indicators = {
            'input_count': input_count,
            'output_count': output_count,
            'unique_input_addresses': len(set(input_addresses)),
            'unique_output_addresses': len(set(output_addresses)),
            'total_input_value': sum(input_values),
            'total_output_value': sum(output_values),
            'fee': sum(input_values) - sum(output_values),
            'output_uniformity': len(set(output_values)),
            'input_diversity': len(set(input_addresses)),
            'transaction_size': input_count + output_count
        }
        
        # Calculate CoinJoin score
        score = 0.0
        reasons = []
        
        # 1. Many inputs/outputs
        if input_count > 5:
            score += 0.2
            reasons.append(f"Many inputs ({input_count})")
        if output_count > 5:
            score += 0.2
            reasons.append(f"Many outputs ({output_count})")
        
        # 2. Output uniformity
        if indicators['output_uniformity'] <= 3:
            score += 0.3
            reasons.append(f"Uniform outputs ({indicators['output_uniformity']} unique values)")
        
        # 3. Input diversity
        if indicators['input_diversity'] > 3:
            score += 0.2
            reasons.append(f"Diverse inputs ({indicators['input_diversity']} unique addresses)")
        
        # 4. Large transaction size
        if indicators['transaction_size'] > 10:
            score += 0.1
            reasons.append(f"Large transaction ({indicators['transaction_size']} total)")
        
        is_coinjoin = score > 0.6
        
        return {
            'is_coinjoin': is_coinjoin,
            'score': min(score, 1.0),
            'reasons': reasons,
            'indicators': indicators,
            'input_addresses': input_addresses,
            'output_addresses': output_addresses,
            'input_values': input_values,
            'output_values': output_values
        }
    
    def test_transaction(self, txid):
        """Test một transaction cụ thể"""
        logger.info(f"Testing transaction: {txid}")
        
        tx_data = self.get_transaction_data(txid)
        if not tx_data:
            return None
        
        analysis = self.analyze_transaction_detailed(tx_data)
        
        result = {
            'txid': txid,
            'analysis': analysis,
            'raw_data': {
                'vin_count': len(tx_data.get('vin', [])),
                'vout_count': len(tx_data.get('vout', [])),
                'status': tx_data.get('status', {}),
                'weight': tx_data.get('weight', 0),
                'fee': tx_data.get('fee', 0)
            }
        }
        
        return result
    
    def test_multiple_transactions(self, txids):
        """Test nhiều transactions"""
        results = []
        
        for i, txid in enumerate(txids):
            logger.info(f"Testing {i+1}/{len(txids)}: {txid}")
            
            try:
                result = self.test_transaction(txid)
                if result:
                    results.append(result)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Error testing {txid}: {e}")
                continue
        
        return results

def main():
    print("=== Transaction Testing ===")
    
    # Test với một số transaction cụ thể
    test_txids = [
        "9701e6e66b33b22dd1cb9cd568a831f612768b6ab10f5a179086bebaf1c413cd",  # CoinJoin từ dataset
        "277c7fd9618efa76141235dfb458289a6d989f526384341ca03fa26732711e30",  # CoinJoin với related tx
        "634660b011f02ee0479e309ff2182dd7e84e82cb78980cd6b8be732e1bc20961",  # Related transaction
    ]
    
    tester = TransactionTester()
    results = tester.test_multiple_transactions(test_txids)
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(f'data/training_results/detailed_test_{timestamp}.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n=== TEST RESULTS ===")
    for result in results:
        analysis = result['analysis']
        print(f"\nTransaction: {result['txid']}")
        print(f"  CoinJoin: {analysis['is_coinjoin']}")
        print(f"  Score: {analysis['score']:.2f}")
        print(f"  Reasons: {', '.join(analysis['reasons'])}")
        print(f"  Inputs: {analysis['indicators']['input_count']}, Outputs: {analysis['indicators']['output_count']}")
        print(f"  Unique Input Addresses: {analysis['indicators']['unique_input_addresses']}")
        print(f"  Output Uniformity: {analysis['indicators']['output_uniformity']} unique values")
    
    print(f"\nResults saved to: data/training_results/detailed_test_{timestamp}.json")

if __name__ == "__main__":
    main()
