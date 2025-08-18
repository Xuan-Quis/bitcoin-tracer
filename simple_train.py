#!/usr/bin/env python3
"""
Simple AI CoinJoin Training Script
"""

import os
import json
import time
import logging
from datetime import datetime
import pandas as pd
import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleTrainer:
    def __init__(self):
        self.blockstream_api = "https://blockstream.info/api"
        self.processed_txs = set()
        self.coinjoin_txs = set()
        
        os.makedirs("logs", exist_ok=True)
        os.makedirs("data/training_results", exist_ok=True)
        
    def load_datasets(self):
        logger.info("Loading datasets...")
        
        # Load CoinJoinsMain dataset
        coinjoins_df = pd.read_csv("dataset/CoinJoinsMain_20211221.csv")
        coinjoin_txs = coinjoins_df['tx_hash'].tolist()
        
        # Load Wasabi dataset
        with open("dataset/wasabi_txs_02-2022.txt", 'r') as f:
            wasabi_txs = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Loaded {len(coinjoin_txs)} CoinJoin + {len(wasabi_txs)} Wasabi transactions")
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
    
    def analyze_coinjoin(self, tx_data):
        input_count = len(tx_data.get('vin', []))
        output_count = len(tx_data.get('vout', []))
        
        # Simple heuristic
        is_coinjoin = False
        score = 0.0
        
        if input_count > 5 and output_count > 5:
            output_values = [vout.get('value', 0) for vout in tx_data.get('vout', [])]
            if len(set(output_values)) <= 3:
                is_coinjoin = True
                score = 0.8
        
        return {
            'is_coinjoin': is_coinjoin,
            'score': score,
            'input_count': input_count,
            'output_count': output_count
        }
    
    def investigate_recursive(self, txid, depth=0, max_depth=2):
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
        if depth < max_depth:
            addresses = []
            for vin in tx_data.get('vin', []):
                if 'prevout' in vin and 'scriptpubkey_address' in vin['prevout']:
                    addresses.append(vin['prevout']['scriptpubkey_address'])
            
            for vout in tx_data.get('vout', []):
                if 'scriptpubkey_address' in vout:
                    addresses.append(vout['scriptpubkey_address'])
            
            consecutive_normal = 0
            for addr in addresses[:2]:  # Limit 2 addresses
                try:
                    url = f"{self.blockstream_api}/address/{addr}/txs"
                    response = requests.get(url, timeout=10)
                    addr_txs = response.json()[:1]  # Limit 1 transaction
                    
                    for addr_tx in addr_txs:
                        if addr_tx['txid'] not in self.processed_txs:
                            related = self.investigate_recursive(addr_tx['txid'], depth + 1, max_depth)
                            if related:
                                result['related_txs'].append(related)
                                
                                if related.get('is_coinjoin', False):
                                    consecutive_normal = 0
                                else:
                                    consecutive_normal += 1
                                
                                if consecutive_normal >= 5:  # Stop after 5 normal tx
                                    break
                except Exception as e:
                    logger.error(f"Error fetching {addr}: {e}")
                    continue
        
        if result['is_coinjoin']:
            self.coinjoin_txs.add(txid)
        
        return result
    
    def train(self):
        logger.info("Starting training...")
        
        coinjoin_txs, wasabi_txs = self.load_datasets()
        all_txs = list(set(coinjoin_txs + wasabi_txs))
        
        results = []
        for i, txid in enumerate(all_txs[:20]):  # Test with 20 transactions
            logger.info(f"Processing {i+1}/20: {txid}")
            
            try:
                result = self.investigate_recursive(txid)
                if result:
                    results.append(result)
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error processing {txid}: {e}")
                continue
        
        self.save_results(results)
        self.print_stats()
    
    def save_results(self, results):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save full results
        with open(f"data/training_results/training_{timestamp}.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save only CoinJoin
        coinjoin_results = [r for r in results if r.get('is_coinjoin', False)]
        with open(f"data/training_results/coinjoin_{timestamp}.json", 'w') as f:
            json.dump(coinjoin_results, f, indent=2)
        
        logger.info(f"Results saved to data/training_results/")
    
    def print_stats(self):
        logger.info(f"Total processed: {len(self.processed_txs)}")
        logger.info(f"CoinJoin detected: {len(self.coinjoin_txs)}")

def main():
    print("=== AI CoinJoin Training ===")
    trainer = SimpleTrainer()
    trainer.train()
    print("Training completed!")

if __name__ == "__main__":
    main()
