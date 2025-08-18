#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced AI CoinJoin Training Script with Recursive Investigation
"""

import os
import json
import time
import logging
import pandas as pd
import requests
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedTrainer:
    def __init__(self):
        self.blockstream_api = 'https://blockstream.info/api'
        self.processed_txs = set()
        self.coinjoin_txs = set()
        self.normal_txs = set()
        self.consecutive_normal_count = 0
        
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data/training_results', exist_ok=True)
        
    def load_datasets(self):
        logger.info('Loading datasets...')
        
        # Load CoinJoinsMain dataset
        coinjoins_df = pd.read_csv('dataset/CoinJoinsMain_20211221.csv')
        coinjoin_txs = coinjoins_df['tx_hash'].tolist()
        
        # Load Wasabi dataset
        with open('dataset/wasabi_txs_02-2022.txt', 'r') as f:
            wasabi_txs = [line.strip() for line in f if line.strip()]
        
        logger.info(f'Loaded {len(coinjoin_txs)} CoinJoin + {len(wasabi_txs)} Wasabi transactions')
        return coinjoin_txs, wasabi_txs
    
    def get_transaction_data(self, txid):
        try:
            url = f"{self.blockstream_api}/tx/{txid}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching tx {txid}: {e}")
            return None
    
    def get_address_transactions(self, address):
        try:
            url = f"{self.blockstream_api}/address/{address}/txs"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching address {address}: {e}")
            return []
    
    def analyze_coinjoin(self, tx_data):
        input_count = len(tx_data.get('vin', []))
        output_count = len(tx_data.get('vout', []))
        
        # Extract addresses
        input_addresses = []
        output_addresses = []
        
        for vin in tx_data.get('vin', []):
            if 'prevout' in vin and 'scriptpubkey_address' in vin['prevout']:
                input_addresses.append(vin['prevout']['scriptpubkey_address'])
        
        for vout in tx_data.get('vout', []):
            if 'scriptpubkey_address' in vout:
                output_addresses.append(vout['scriptpubkey_address'])
        
        # Calculate score
        score = 0.0
        if input_count > 5:
            score += 0.2
        if output_count > 5:
            score += 0.2
        
        # Check output uniformity
        output_values = [vout.get('value', 0) for vout in tx_data.get('vout', [])]
        if len(set(output_values)) <= 3:
            score += 0.3
        
        # Check input diversity
        if len(set(input_addresses)) > 3:
            score += 0.2
        
        if input_count + output_count > 10:
            score += 0.1
        
        is_coinjoin = score > 0.6
        
        return {
            'is_coinjoin': is_coinjoin,
            'score': min(score, 1.0),
            'input_addresses': input_addresses,
            'output_addresses': output_addresses
        }
    
    def investigate_recursive(self, txid, depth=0, max_depth=3):
        if depth > max_depth or txid in self.processed_txs:
            return None
        
        self.processed_txs.add(txid)
        logger.info(f"Investigating {txid} at depth {depth}")
        
        tx_data = self.get_transaction_data(txid)
        if not tx_data:
            return None
        
        analysis = self.analyze_coinjoin(tx_data)
        
        result = {
            'txid': txid,
            'depth': depth,
            'is_coinjoin': analysis['is_coinjoin'],
            'score': analysis['score'],
            'related_txs': []
        }
        
        # Recursive investigation
        if depth < max_depth and self.consecutive_normal_count < 10:
            all_addresses = analysis['input_addresses'] + analysis['output_addresses']
            
            for addr in all_addresses[:2]:  # Limit 2 addresses
                try:
                    addr_txs = self.get_address_transactions(addr)
                    
                    for addr_tx in addr_txs[:1]:  # Limit 1 transaction per address
                        if addr_tx['txid'] not in self.processed_txs:
                            related = self.investigate_recursive(addr_tx['txid'], depth + 1, max_depth)
                            if related:
                                result['related_txs'].append(related)
                                
                                if related.get('is_coinjoin', False):
                                    self.consecutive_normal_count = 0
                                else:
                                    self.consecutive_normal_count += 1
                                
                                if self.consecutive_normal_count >= 10:
                                    logger.info("Stopping: 10 consecutive normal transactions")
                                    break
                except Exception as e:
                    logger.error(f"Error investigating {addr}: {e}")
                    continue
        
        # Update tracking
        if result['is_coinjoin']:
            self.coinjoin_txs.add(txid)
        else:
            self.normal_txs.add(txid)
        
        return result
    
    def train(self):
        logger.info("Starting advanced training with recursive investigation...")
        
        coinjoin_txs, wasabi_txs = self.load_datasets()
        all_txs = list(set(coinjoin_txs + wasabi_txs))
        
        results = []
        sample_size = min(15, len(all_txs))  # Test with 15 transactions
        
        for i, txid in enumerate(all_txs[:sample_size]):
            logger.info(f"Processing {i+1}/{sample_size}: {txid}")
            
            try:
                self.consecutive_normal_count = 0  # Reset for each starting transaction
                result = self.investigate_recursive(txid)
                if result:
                    results.append(result)
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error processing {txid}: {e}")
                continue
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save full results
        with open(f'data/training_results/advanced_results_{timestamp}.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save only CoinJoin
        coinjoin_results = [r for r in results if r.get('is_coinjoin', False)]
        with open(f'data/training_results/advanced_coinjoin_{timestamp}.json', 'w') as f:
            json.dump(coinjoin_results, f, indent=2)
        
        # Save stats
        stats = {
            'total_investigated': len(results),
            'coinjoin_detected': len(coinjoin_results),
            'normal_transactions': len(results) - len(coinjoin_results),
            'processed_txs': len(self.processed_txs),
            'detection_rate': len(coinjoin_results) / len(results) if results else 0
        }
        
        with open(f'data/training_results/advanced_stats_{timestamp}.json', 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"Total processed: {len(self.processed_txs)}")
        logger.info(f"CoinJoin detected: {len(self.coinjoin_txs)}")
        logger.info(f"Normal transactions: {len(self.normal_txs)}")

def main():
    print("=== Advanced AI CoinJoin Training ===")
    trainer = AdvancedTrainer()
    trainer.train()
    print("Advanced training completed!")

if __name__ == "__main__":
    main()
