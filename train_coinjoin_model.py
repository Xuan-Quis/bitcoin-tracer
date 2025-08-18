#!/usr/bin/env python3
"""
AI CoinJoin Training Script
Train model từ dataset có sẵn và điều tra đệ quy các transaction
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Set
import pandas as pd
import requests

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from investigation.coinjoin_investigator import CoinJoinInvestigator
from investigation.cluster_analyzer import ClusterAnalyzer
from investigation.coinjoin_detector import CoinJoinDetector
from data.transaction_storage import TransactionStorage
from utils.config import Config
from utils.logger import setup_logger

class CoinJoinTrainer:
    def __init__(self):
        """Khởi tạo trainer"""
        self.logger = setup_logger("coinjoin_trainer")
        self.blockstream_api = "https://blockstream.info/api"
        self.processed_txs = set()
        self.coinjoin_txs = set()
        
    def load_datasets(self):
        """Load 2 dataset có sẵn"""
        self.logger.info("Loading datasets...")
        
        # Load CoinJoinsMain dataset
        coinjoins_df = pd.read_csv("dataset/CoinJoinsMain_20211221.csv")
        coinjoin_txs = coinjoins_df['tx_hash'].tolist()
        
        # Load Wasabi dataset
        with open("dataset/wasabi_txs_02-2022.txt", 'r') as f:
            wasabi_txs = [line.strip() for line in f if line.strip()]
        
        self.logger.info(f"Loaded {len(coinjoin_txs)} CoinJoin + {len(wasabi_txs)} Wasabi transactions")
        return coinjoin_txs, wasabi_txs
    
    def get_transaction_data(self, txid: str):
        """Lấy dữ liệu transaction từ Blockstream API"""
        try:
            url = f"{self.blockstream_api}/tx/{txid}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching tx {txid}: {e}")
            return None
    
    def investigate_transaction_recursive(self, txid: str, depth: int = 0, max_depth: int = 3):
        """Điều tra transaction đệ quy"""
        if depth > max_depth or txid in self.processed_txs:
            return None
        
        self.processed_txs.add(txid)
        self.logger.info(f"Investigating tx {txid} at depth {depth}")
        
        # Lấy dữ liệu transaction
        tx_data = self.get_transaction_data(txid)
        if not tx_data:
            return None
        
        # Phân tích transaction
        result = {
            'txid': txid,
            'depth': depth,
            'is_coinjoin': False,
            'coinjoin_score': 0,
            'related_txs': []
        }
        
        # Điều tra đệ quy nếu chưa đạt max depth
        if depth < max_depth:
            # Lấy addresses từ transaction
            addresses = []
            for vin in tx_data.get('vin', []):
                if 'prevout' in vin and 'scriptpubkey_address' in vin['prevout']:
                    addresses.append(vin['prevout']['scriptpubkey_address'])
            
            for vout in tx_data.get('vout', []):
                if 'scriptpubkey_address' in vout:
                    addresses.append(vout['scriptpubkey_address'])
            
            # Điều tra các addresses liên quan
            consecutive_normal = 0
            for addr in addresses[:3]:  # Giới hạn 3 addresses
                try:
                    url = f"{self.blockstream_api}/address/{addr}/txs"
                    response = requests.get(url, timeout=10)
                    addr_txs = response.json()[:2]  # Giới hạn 2 transactions
                    
                    for addr_tx in addr_txs:
                        if addr_tx['txid'] not in self.processed_txs:
                            related_result = self.investigate_transaction_recursive(
                                addr_tx['txid'], depth + 1, max_depth
                            )
                            if related_result:
                                result['related_txs'].append(related_result)
                                
                                if related_result.get('is_coinjoin', False):
                                    consecutive_normal = 0
                                else:
                                    consecutive_normal += 1
                                
                                # Dừng nếu 10 tx liên tiếp không phải CoinJoin
                                if consecutive_normal >= 10:
                                    break
                except Exception as e:
                    self.logger.error(f"Error fetching address {addr}: {e}")
                    continue
        
        # Đánh giá CoinJoin (đơn giản)
        input_count = len(tx_data.get('vin', []))
        output_count = len(tx_data.get('vout', []))
        
        # Heuristic đơn giản: nhiều input/output và giá trị output đồng đều
        if input_count > 5 and output_count > 5:
            output_values = [vout.get('value', 0) for vout in tx_data.get('vout', [])]
            if len(set(output_values)) <= 3:  # Ít loại giá trị output
                result['is_coinjoin'] = True
                result['coinjoin_score'] = 0.8
                self.coinjoin_txs.add(txid)
        
        return result
    
    def train_from_datasets(self):
        """Train model từ datasets"""
        self.logger.info("Starting training...")
        
        # Load datasets
        coinjoin_txs, wasabi_txs = self.load_datasets()
        all_txs = list(set(coinjoin_txs + wasabi_txs))
        
        # Điều tra từng transaction
        results = []
        for i, txid in enumerate(all_txs[:50]):  # Giới hạn 50 để test
            self.logger.info(f"Processing {i+1}/50: {txid}")
            
            try:
                result = self.investigate_transaction_recursive(txid)
                if result:
                    results.append(result)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                self.logger.error(f"Error processing {txid}: {e}")
                continue
        
        # Lưu kết quả
        self.save_results(results)
        self.print_stats()
    
    def save_results(self, results):
        """Lưu kết quả"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Tạo thư mục
        os.makedirs("data/training_results", exist_ok=True)
        
        # Lưu kết quả
        with open(f"data/training_results/training_{timestamp}.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        # Lưu chỉ CoinJoin
        coinjoin_results = [r for r in results if r.get('is_coinjoin', False)]
        with open(f"data/training_results/coinjoin_{timestamp}.json", 'w') as f:
            json.dump(coinjoin_results, f, indent=2)
        
        self.logger.info(f"Results saved to data/training_results/")
    
    def print_stats(self):
        """In thống kê"""
        self.logger.info(f"Total processed: {len(self.processed_txs)}")
        self.logger.info(f"CoinJoin detected: {len(self.coinjoin_txs)}")

def main():
    print("=== AI CoinJoin Training ===")
    trainer = CoinJoinTrainer()
    trainer.train_from_datasets()
    print("Training completed!")

if __name__ == "__main__":
    main()
