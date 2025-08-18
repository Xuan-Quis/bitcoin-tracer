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
from typing import List, Dict, Set, Tuple
import pandas as pd
import requests
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from investigation.coinjoin_investigator import CoinJoinInvestigator
from investigation.cluster_analyzer import ClusterAnalyzer
from investigation.coinjoin_detector import CoinJoinDetector
from data.transaction_storage import TransactionStorage
from utils.config import Config
from utils.logger import setup_logger

class CoinJoinTrainer:
    def __init__(self, config_path: str = "config/training_config.yaml"):
        """Khởi tạo trainer với config"""
        self.config = Config(config_path)
        self.logger = setup_logger("coinjoin_trainer")
        
        # Khởi tạo các component
        self.investigator = CoinJoinInvestigator(self.config)
        self.storage = TransactionStorage(
            base_directory=self.config.get('storage.base_directory', 'data/training_results')
        )
        
        # Tạo thư mục lưu trữ
        os.makedirs(self.config.get('storage.base_directory', 'data/training_results'), exist_ok=True)
        
        # Blockstream API endpoint
        self.blockstream_api = "https://blockstream.info/api"
        
        # Tracking
        self.processed_txs = set()
        self.coinjoin_txs = set()
        self.normal_txs = set()
        
    def load_datasets(self) -> Tuple[List[str], List[str]]:
        """Load 2 dataset có sẵn"""
        self.logger.info("Loading datasets...")
        
        # Load CoinJoinsMain dataset
        coinjoins_df = pd.read_csv("dataset/CoinJoinsMain_20211221.csv")
        coinjoin_txs = coinjoins_df['tx_hash'].tolist()
        self.logger.info(f"Loaded {len(coinjoin_txs)} CoinJoin transactions from CoinJoinsMain")
        
        # Load Wasabi dataset
        with open("dataset/wasabi_txs_02-2022.txt", 'r') as f:
            wasabi_txs = [line.strip() for line in f if line.strip()]
        self.logger.info(f"Loaded {len(wasabi_txs)} transactions from Wasabi dataset")
        
        return coinjoin_txs, wasabi_txs
    
    def get_transaction_data(self, txid: str) -> Dict:
        """Lấy dữ liệu transaction từ Blockstream API"""
        try:
            url = f"{self.blockstream_api}/tx/{txid}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching tx {txid}: {e}")
            return None
    
    def get_address_transactions(self, address: str) -> List[Dict]:
        """Lấy danh sách transactions của một địa chỉ"""
        try:
            url = f"{self.blockstream_api}/address/{address}/txs"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching address {address}: {e}")
            return []
    
    def extract_addresses_from_tx(self, tx_data: Dict) -> Tuple[List[str], List[str]]:
        """Trích xuất input và output addresses từ transaction"""
        input_addresses = []
        output_addresses = []
        
        # Extract input addresses
        for vin in tx_data.get('vin', []):
            if 'prevout' in vin and 'scriptpubkey_address' in vin['prevout']:
                input_addresses.append(vin['prevout']['scriptpubkey_address'])
        
        # Extract output addresses
        for vout in tx_data.get('vout', []):
            if 'scriptpubkey_address' in vout:
                output_addresses.append(vout['scriptpubkey_address'])
        
        return input_addresses, output_addresses
    
    def investigate_transaction_recursive(self, txid: str, depth: int = 0, max_depth: int = 5) -> Dict:
        """Điều tra transaction đệ quy theo kịch bản"""
        if depth > max_depth or txid in self.processed_txs:
            return None
        
        self.processed_txs.add(txid)
        self.logger.info(f"Investigating tx {txid} at depth {depth}")
        
        # Lấy dữ liệu transaction
        tx_data = self.get_transaction_data(txid)
        if not tx_data:
            return None
        
        # Trích xuất addresses
        input_addresses, output_addresses = self.extract_addresses_from_tx(tx_data)
        
        # Điều tra các addresses liên quan
        related_txs = []
        consecutive_normal = 0
        
        # Điều tra input addresses
        for addr in input_addresses[:5]:  # Giới hạn 5 addresses để tránh quá tải
            addr_txs = self.get_address_transactions(addr)
            for addr_tx in addr_txs[:3]:  # Giới hạn 3 transactions per address
                if addr_tx['txid'] not in self.processed_txs:
                    related_txs.append(addr_tx['txid'])
        
        # Điều tra output addresses
        for addr in output_addresses[:5]:
            addr_txs = self.get_address_transactions(addr)
            for addr_tx in addr_txs[:3]:
                if addr_tx['txid'] not in self.processed_txs:
                    related_txs.append(addr_tx['txid'])
        
        # Điều tra đệ quy các transactions liên quan
        investigation_results = {
            'txid': txid,
            'depth': depth,
            'tx_data': tx_data,
            'input_addresses': input_addresses,
            'output_addresses': output_addresses,
            'related_transactions': [],
            'coinjoin_score': 0,
            'is_coinjoin': False
        }
        
        # Điều tra các transactions liên quan
        for related_txid in related_txs[:10]:  # Giới hạn 10 related transactions
            if consecutive_normal >= 10:  # Dừng nếu 10 tx liên tiếp không phải CoinJoin
                break
                
            related_result = self.investigate_transaction_recursive(related_txid, depth + 1, max_depth)
            if related_result:
                investigation_results['related_transactions'].append(related_result)
                
                # Kiểm tra nếu là CoinJoin
                if related_result.get('is_coinjoin', False):
                    consecutive_normal = 0
                    self.coinjoin_txs.add(related_txid)
                else:
                    consecutive_normal += 1
                    self.normal_txs.add(related_txid)
        
        # Phân tích transaction hiện tại
        try:
            # Sử dụng CoinJoinDetector để phân tích
            detector = CoinJoinDetector()
            analyzer = ClusterAnalyzer()
            
            # Tạo dữ liệu giả lập cho phân tích
            analysis_data = {
                'inputs': input_addresses,
                'outputs': output_addresses,
                'input_values': [vin.get('value', 0) for vin in tx_data.get('vin', [])],
                'output_values': [vout.get('value', 0) for vout in tx_data.get('vout', [])]
            }
            
            # Phân tích cluster
            cluster_result = analyzer.analyze_transaction(analysis_data)
            
            # Phát hiện CoinJoin
            coinjoin_result = detector.detect_coinjoin(cluster_result)
            
            investigation_results['coinjoin_score'] = coinjoin_result.get('coinjoin_score', 0)
            investigation_results['is_coinjoin'] = coinjoin_result.get('is_coinjoin', False)
            investigation_results['cluster_analysis'] = cluster_result
            
            if investigation_results['is_coinjoin']:
                self.coinjoin_txs.add(txid)
            else:
                self.normal_txs.add(txid)
                
        except Exception as e:
            self.logger.error(f"Error analyzing tx {txid}: {e}")
        
        return investigation_results
    
    def train_from_datasets(self):
        """Train model từ 2 dataset có sẵn"""
        self.logger.info("Starting training from datasets...")
        
        # Load datasets
        coinjoin_txs, wasabi_txs = self.load_datasets()
        
        # Combine datasets
        all_txs = list(set(coinjoin_txs + wasabi_txs))
        self.logger.info(f"Total unique transactions to investigate: {len(all_txs)}")
        
        # Điều tra từng transaction
        investigation_results = []
        
        for i, txid in enumerate(all_txs[:100]):  # Giới hạn 100 transactions để test
            self.logger.info(f"Processing {i+1}/{min(100, len(all_txs))}: {txid}")
            
            try:
                result = self.investigate_transaction_recursive(txid, depth=0, max_depth=3)
                if result:
                    investigation_results.append(result)
                
                # Delay để tránh rate limit
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error processing tx {txid}: {e}")
                continue
        
        # Lưu kết quả
        self.save_training_results(investigation_results)
        
        # In thống kê
        self.print_training_stats()
    
    def save_training_results(self, results: List[Dict]):
        """Lưu kết quả training"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Lưu kết quả đầy đủ
        full_results_file = f"data/training_results/full_investigation_{timestamp}.json"
        with open(full_results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Lưu chỉ các CoinJoin transactions
        coinjoin_results = [r for r in results if r.get('is_coinjoin', False)]
        coinjoin_file = f"data/training_results/coinjoin_only_{timestamp}.json"
        with open(coinjoin_file, 'w') as f:
            json.dump(coinjoin_results, f, indent=2)
        
        # Lưu thống kê
        stats = {
            'total_investigated': len(results),
            'coinjoin_detected': len(coinjoin_results),
            'normal_transactions': len(results) - len(coinjoin_results),
            'processed_txs': len(self.processed_txs),
            'timestamp': timestamp
        }
        
        stats_file = f"data/training_results/training_stats_{timestamp}.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        self.logger.info(f"Results saved to {full_results_file}")
        self.logger.info(f"CoinJoin results saved to {coinjoin_file}")
        self.logger.info(f"Stats saved to {stats_file}")
    
    def print_training_stats(self):
        """In thống kê training"""
        self.logger.info("=== TRAINING STATISTICS ===")
        self.logger.info(f"Total processed transactions: {len(self.processed_txs)}")
        self.logger.info(f"CoinJoin transactions detected: {len(self.coinjoin_txs)}")
        self.logger.info(f"Normal transactions: {len(self.normal_txs)}")
        self.logger.info(f"Detection rate: {len(self.coinjoin_txs)/len(self.processed_txs)*100:.2f}%")

def main():
    """Main function"""
    print("=== AI CoinJoin Training System ===")
    print("Training from datasets with recursive investigation...")
    
    # Khởi tạo trainer
    trainer = CoinJoinTrainer()
    
    # Bắt đầu training
    trainer.train_from_datasets()
    
    print("Training completed!")

if __name__ == "__main__":
    main()
