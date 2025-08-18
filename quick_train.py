#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple AI CoinJoin Training Script
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

class Trainer:
    def __init__(self):
        self.blockstream_api = 'https://blockstream.info/api'
        self.processed_txs = set()
        self.coinjoin_txs = set()
        
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
    
    def get_tx_data(self, txid):
        try:
            url = f'{self.blockstream_api}/tx/{txid}'
            response = requests.get(url, timeout=10)
            return response.json()
        except:
            return None
    
    def analyze_coinjoin(self, tx_data):
        input_count = len(tx_data.get('vin', []))
        output_count = len(tx_data.get('vout', []))
        
        # Simple heuristic
        is_coinjoin = input_count > 5 and output_count > 5
        return {'is_coinjoin': is_coinjoin, 'score': 0.8 if is_coinjoin else 0.0}
    
    def investigate(self, txid, depth=0, max_depth=2):
        if depth > max_depth or txid in self.processed_txs:
            return None
        
        self.processed_txs.add(txid)
        logger.info(f'Investigating {txid} at depth {depth}')
        
        tx_data = self.get_tx_data(txid)
        if not tx_data:
            return None
        
        analysis = self.analyze_coinjoin(tx_data)
        result = {
            'txid': txid,
            'depth': depth,
            'is_coinjoin': analysis['is_coinjoin'],
            'score': analysis['score']
        }
        
        if result['is_coinjoin']:
            self.coinjoin_txs.add(txid)
        
        return result
    
    def train(self):
        logger.info('Starting training...')
        
        coinjoin_txs, wasabi_txs = self.load_datasets()
        all_txs = list(set(coinjoin_txs + wasabi_txs))
        
        results = []
        for i, txid in enumerate(all_txs[:10]):  # Test with 10 transactions
            logger.info(f'Processing {i+1}/10: {txid}')
            
            try:
                result = self.investigate(txid)
                if result:
                    results.append(result)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f'Error: {e}')
                continue
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'data/training_results/results_{timestamp}.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f'Total processed: {len(self.processed_txs)}')
        logger.info(f'CoinJoin detected: {len(self.coinjoin_txs)}')

# Run training
if __name__ == "__main__":
    print("=== AI CoinJoin Training ===")
    trainer = Trainer()
    trainer.train()
    print("Training completed!")
