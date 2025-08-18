#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full Scale AI CoinJoin Training Script
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

class FullScaleTrainer:
    def __init__(self):
        self.blockstream_api = 'https://blockstream.info/api'
        self.processed_txs = set()
        self.coinjoin_txs = set()
        self.normal_txs = set()
        
        self.total_processed = 0
        self.total_coinjoin = 0
        self.total_normal = 0
        self.errors = 0
        
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data/training_results', exist_ok=True)
        
    def load_all_datasets(self):
        logger.info('Loading all datasets...')
        
        coinjoins_df = pd.read_csv('dataset/CoinJoinsMain_20211221.csv')
        coinjoin_txs = coinjoins_df['tx_hash'].tolist()
        
        with open('dataset/wasabi_txs_02-2022.txt', 'r') as f:
            wasabi_txs = [line.strip() for line in f if line.strip()]
        
        all_txs = list(set(coinjoin_txs + wasabi_txs))
        
        logger.info(f'Loaded {len(coinjoin_txs)} CoinJoin + {len(wasabi_txs)} Wasabi transactions')
        logger.info(f'Total unique transactions: {len(all_txs)}')
        
        return all_txs
    
    def get_transaction_data(self, txid):
        try:
            url = f"{self.blockstream_api}/tx/{txid}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching tx {txid}: {e}")
            return None
    
    def analyze_coinjoin(self, tx_data):
        input_count = len(tx_data.get('vin', []))
        output_count = len(tx_data.get('vout', []))
        
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
        
        indicators = {
            'input_count': input_count,
            'output_count': output_count,
            'unique_input_addresses': len(set(input_addresses)),
            'unique_output_addresses': len(set(output_addresses)),
            'output_uniformity': len(set(output_values)),
            'input_diversity': len(set(input_addresses)),
            'transaction_size': input_count + output_count
        }
        
        score = 0.0
        reasons = []
        
        if input_count > 5:
            score += 0.15
            reasons.append(f"Many inputs ({input_count})")
        if output_count > 5:
            score += 0.15
            reasons.append(f"Many outputs ({output_count})")
        
        if indicators['output_uniformity'] <= 5:
            score += 0.25
            reasons.append(f"Uniform outputs ({indicators['output_uniformity']} unique values)")
        
        if indicators['input_diversity'] > 3:
            score += 0.20
            reasons.append(f"Diverse inputs ({indicators['input_diversity']} unique addresses)")
        
        if indicators['transaction_size'] > 10:
            score += 0.10
            reasons.append(f"Large transaction ({indicators['transaction_size']} total)")
        
        if indicators['output_uniformity'] <= 3 and len(output_values) > 5:
            score += 0.15
            reasons.append("CoinJoin-like output pattern")
        
        is_coinjoin = score > 0.6
        
        return {
            'is_coinjoin': is_coinjoin,
            'score': min(score, 1.0),
            'reasons': reasons,
            'indicators': indicators
        }
    
    def process_transaction(self, txid):
        if txid in self.processed_txs:
            return None
        
        self.processed_txs.add(txid)
        
        tx_data = self.get_transaction_data(txid)
        if not tx_data:
            self.errors += 1
            return None
        
        analysis = self.analyze_coinjoin(tx_data)
        
        result = {
            'txid': txid,
            'is_coinjoin': analysis['is_coinjoin'],
            'score': analysis['score'],
            'reasons': analysis['reasons'],
            'indicators': analysis['indicators'],
            'timestamp': datetime.now().isoformat()
        }
        
        self.total_processed += 1
        if result['is_coinjoin']:
            self.coinjoin_txs.add(txid)
            self.total_coinjoin += 1
        else:
            self.normal_txs.add(txid)
            self.total_normal += 1
        
        return result
    
    def train_full_scale(self, sample_size=None):
        logger.info("Starting FULL SCALE training...")
        start_time = datetime.now()
        
        all_txs = self.load_all_datasets()
        
        if sample_size:
            all_txs = all_txs[:sample_size]
            logger.info(f"Using sample size: {sample_size}")
        
        logger.info(f"Processing {len(all_txs)} transactions...")
        
        all_results = []
        batch_size = 100
        total_batches = (len(all_txs) + batch_size - 1) // batch_size
        
        for i in range(0, len(all_txs), batch_size):
            batch = all_txs[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} transactions)")
            
            batch_results = []
            for txid in batch:
                try:
                    result = self.process_transaction(txid)
                    if result:
                        batch_results.append(result)
                    time.sleep(0.2)
                except Exception as e:
                    logger.error(f"Error processing {txid}: {e}")
                    self.errors += 1
                    continue
            
            all_results.extend(batch_results)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            batch_file = f'data/training_results/batch_{batch_num:04d}_{timestamp}.json'
            with open(batch_file, 'w') as f:
                json.dump(batch_results, f, indent=2)
            
            progress = (batch_num / total_batches) * 100
            logger.info(f"Progress: {progress:.1f}% - Processed: {self.total_processed}, CoinJoin: {self.total_coinjoin}, Normal: {self.total_normal}, Errors: {self.errors}")
        
        self.save_final_results(all_results, start_time)
        logger.info("FULL SCALE training completed!")
    
    def save_final_results(self, all_results, start_time):
        end_time = datetime.now()
        duration = end_time - start_time
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        all_results_file = f'data/training_results/full_scale_results_{timestamp}.json'
        with open(all_results_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        coinjoin_results = [r for r in all_results if r.get('is_coinjoin', False)]
        coinjoin_file = f'data/training_results/full_scale_coinjoin_{timestamp}.json'
        with open(coinjoin_file, 'w') as f:
            json.dump(coinjoin_results, f, indent=2)
        
        stats = {
            'total_transactions': len(all_results),
            'coinjoin_detected': self.total_coinjoin,
            'normal_transactions': self.total_normal,
            'errors': self.errors,
            'detection_rate': self.total_coinjoin / len(all_results) if all_results else 0,
            'processing_time_minutes': duration.total_seconds() / 60,
            'transactions_per_minute': len(all_results) / (duration.total_seconds() / 60) if duration.total_seconds() > 0 else 0,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration': str(duration)
        }
        
        stats_file = f'data/training_results/full_scale_stats_{timestamp}.json'
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info("=" * 60)
        logger.info("FULL SCALE TRAINING COMPLETED!")
        logger.info("=" * 60)
        logger.info(f"Total transactions processed: {len(all_results)}")
        logger.info(f"CoinJoin detected: {self.total_coinjoin}")
        logger.info(f"Normal transactions: {self.total_normal}")
        logger.info(f"Errors: {self.errors}")
        logger.info(f"Detection rate: {stats['detection_rate']:.2%}")
        logger.info(f"Processing time: {stats['processing_time_minutes']:.1f} minutes")
        logger.info(f"Speed: {stats['transactions_per_minute']:.1f} transactions/minute")

def main():
    print("=" * 60)
    print("FULL SCALE AI COINJOIN TRAINING")
    print("Training on ALL transactions from dataset")
    print("=" * 60)
    
    # Start with 1000 transactions first
    sample_size = 1000  # Change to None for full dataset
    
    print(f"Configuration:")
    print(f"  • Sample size: {sample_size if sample_size else 'ALL'}")
    print(f"  • Rate limiting: 0.2s per transaction")
    print(f"  • Batch size: 100 transactions")
    print()
    
    trainer = FullScaleTrainer()
    trainer.train_full_scale(sample_size=sample_size)

if __name__ == "__main__":
    main()
