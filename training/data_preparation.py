#!/usr/bin/env python3
"""
Data Preparation Script for CoinJoin Detection AI Training
Chuẩn bị dữ liệu từ heuristic labels để train model AI
"""

import os
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import argparse
from pathlib import Path
import logging
from collections import defaultdict
import pickle

# Django imports
import sys
sys.path.append('../blockchain')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blockchain.settings')
import django
django.setup()

from bitcoin.models import Transaction, TxInput, TxOutput, Address
from django.db.models import Q, Count, Sum, Avg
from django.db import connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoinJoinDataPreparator:
    """Chuẩn bị dữ liệu training cho CoinJoin detection"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Tạo thư mục con
        (self.output_dir / 'raw').mkdir(exist_ok=True)
        (self.output_dir / 'labeled').mkdir(exist_ok=True)
        (self.output_dir / 'processed').mkdir(exist_ok=True)
        
    def extract_coinjoin_transactions(self) -> List[Dict]:
        """Trích xuất các giao dịch được đánh tag CoinJoin"""
        logger.info("Trích xuất giao dịch CoinJoin từ database...")
        
        # Lấy tất cả giao dịch có tag 'coinjoin'
        coinjoin_txs = Transaction.objects.filter(
            tags__icontains='coinjoin'
        ).prefetch_related('inputs', 'outputs', 'inputs__address', 'outputs__address')
        
        logger.info(f"Tìm thấy {coinjoin_txs.count()} giao dịch CoinJoin")
        
        coinjoin_data = []
        for tx in coinjoin_txs:
            tx_data = self._extract_transaction_features(tx)
            tx_data['label'] = 1  # CoinJoin = 1
            coinjoin_data.append(tx_data)
            
        return coinjoin_data
    
    def extract_non_coinjoin_transactions(self, sample_size: int = 1000) -> List[Dict]:
        """Trích xuất giao dịch không phải CoinJoin làm negative samples"""
        logger.info(f"Trích xuất {sample_size} giao dịch không phải CoinJoin...")
        
        # Lấy giao dịch không có tag coinjoin
        non_coinjoin_txs = Transaction.objects.filter(
            ~Q(tags__icontains='coinjoin')
        ).prefetch_related('inputs', 'outputs', 'inputs__address', 'outputs__address')
        
        # Lấy sample ngẫu nhiên
        non_coinjoin_txs = non_coinjoin_txs.order_by('?')[:sample_size]
        
        non_coinjoin_data = []
        for tx in non_coinjoin_txs:
            tx_data = self._extract_transaction_features(tx)
            tx_data['label'] = 0  # Non-CoinJoin = 0
            non_coinjoin_data.append(tx_data)
            
        return non_coinjoin_data
    
    def _extract_transaction_features(self, tx: Transaction) -> Dict:
        """Trích xuất features từ một giao dịch"""
        
        inputs = list(tx.inputs.all())
        outputs = list(tx.outputs.all())
        
        # Basic transaction features
        features = {
            'tx_hash': tx.hash,
            'block_height': tx.block.height if tx.block else None,
            'timestamp': tx.time.isoformat() if tx.time else None,
            
            # Input/Output counts
            'input_count': len(inputs),
            'output_count': len(outputs),
            
            # Value features
            'total_input_value': sum(inp.value for inp in inputs),
            'total_output_value': sum(out.value for out in outputs),
            'fee': float(tx.fee) if tx.fee else 0,
            'fee_per_byte': float(tx.fee) / tx.size if tx.size > 0 else 0,
            
            # Size features
            'tx_size': tx.size,
            'tx_weight': tx.weight if hasattr(tx, 'weight') else 0,
            
            # Value distribution features
            'output_values': [float(out.value) for out in outputs],
            'input_values': [float(inp.value) for inp in inputs],
            
            # Address features
            'input_addresses': [inp.address.address if inp.address else None for inp in inputs],
            'output_addresses': [out.address.address if out.address else None for out in outputs],
            
            # Heuristic scores
            'anomaly_score': float(tx.anomaly_score) if tx.anomaly_score else 0,
            
            # Tags
            'tags': tx.tags.split(',') if tx.tags else [],
            
            # CoinJoin specific features
            'coinjoin_matrix': tx.coinjoin_matrix if hasattr(tx, 'coinjoin_matrix') else None,
        }
        
        # Tính toán statistical features
        features.update(self._calculate_statistical_features(features))
        
        return features
    
    def _calculate_statistical_features(self, features: Dict) -> Dict:
        """Tính toán các features thống kê"""
        
        output_values = features['output_values']
        input_values = features['input_values']
        
        if not output_values:
            return {}
        
        # Value uniformity features (quan trọng cho CoinJoin)
        mean_output = np.mean(output_values)
        std_output = np.std(output_values)
        cv_output = std_output / mean_output if mean_output > 0 else 0
        
        # Value variance (CoinJoin thường có output values đồng đều)
        variance_output = np.var(output_values)
        uniformity_score = 1.0 - (variance_output / (mean_output ** 2)) if mean_output > 0 else 0
        
        # Percentile features
        percentiles = [25, 50, 75, 90, 95]
        output_percentiles = np.percentile(output_values, percentiles)
        
        return {
            'output_mean': mean_output,
            'output_std': std_output,
            'output_cv': cv_output,  # Coefficient of variation
            'output_variance': variance_output,
            'output_uniformity': uniformity_score,
            'output_min': min(output_values),
            'output_max': max(output_values),
            'output_range': max(output_values) - min(output_values),
            'output_percentiles': output_percentiles.tolist(),
            
            # Input features
            'input_mean': np.mean(input_values) if input_values else 0,
            'input_std': np.std(input_values) if input_values else 0,
            'input_variance': np.var(input_values) if input_values else 0,
            
            # Address diversity
            'unique_input_addresses': len(set(features['input_addresses']) - {None}),
            'unique_output_addresses': len(set(features['output_addresses']) - {None}),
            'input_address_diversity': len(set(features['input_addresses']) - {None}) / len(input_values) if input_values else 0,
            'output_address_diversity': len(set(features['output_addresses']) - {None}) / len(output_values) if output_values else 0,
        }
    
    def create_training_dataset(self, balance_ratio: float = 0.5) -> pd.DataFrame:
        """Tạo dataset training cân bằng"""
        logger.info("Tạo dataset training...")
        
        # Lấy CoinJoin transactions
        coinjoin_data = self.extract_coinjoin_transactions()
        logger.info(f"CoinJoin samples: {len(coinjoin_data)}")
        
        # Lấy non-CoinJoin transactions
        non_coinjoin_count = int(len(coinjoin_data) / balance_ratio)
        non_coinjoin_data = self.extract_non_coinjoin_transactions(non_coinjoin_count)
        logger.info(f"Non-CoinJoin samples: {len(non_coinjoin_data)}")
        
        # Kết hợp data
        all_data = coinjoin_data + non_coinjoin_data
        
        # Chuyển thành DataFrame
        df = pd.DataFrame(all_data)
        
        # Lưu raw data
        raw_path = self.output_dir / 'raw' / 'coinjoin_dataset.json'
        with open(raw_path, 'w') as f:
            json.dump(all_data, f, indent=2, default=str)
        logger.info(f"Lưu raw data tại: {raw_path}")
        
        # Lưu DataFrame
        df_path = self.output_dir / 'labeled' / 'coinjoin_dataset.csv'
        df.to_csv(df_path, index=False)
        logger.info(f"Lưu labeled data tại: {df_path}")
        
        return df
    
    def create_feature_matrix(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Tạo feature matrix và labels cho training"""
        logger.info("Tạo feature matrix...")
        
        # Chọn features cho training
        feature_columns = [
            'input_count', 'output_count',
            'total_input_value', 'total_output_value',
            'fee', 'fee_per_byte', 'tx_size',
            'anomaly_score',
            'output_mean', 'output_std', 'output_cv', 'output_variance', 'output_uniformity',
            'output_min', 'output_max', 'output_range',
            'input_mean', 'input_std', 'input_variance',
            'unique_input_addresses', 'unique_output_addresses',
            'input_address_diversity', 'output_address_diversity'
        ]
        
        # Thêm percentile features
        for i, p in enumerate([25, 50, 75, 90, 95]):
            feature_columns.append(f'output_percentiles_{p}')
        
        # Tạo feature matrix
        X = df[feature_columns].fillna(0).values
        y = df['label'].values
        
        # Lưu processed data
        processed_path = self.output_dir / 'processed'
        np.save(processed_path / 'X_train.npy', X)
        np.save(processed_path / 'y_train.npy', y)
        
        # Lưu feature names
        with open(processed_path / 'feature_names.pkl', 'wb') as f:
            pickle.dump(feature_columns, f)
        
        logger.info(f"Feature matrix shape: {X.shape}")
        logger.info(f"Labels shape: {y.shape}")
        logger.info(f"Positive samples: {np.sum(y == 1)}")
        logger.info(f"Negative samples: {np.sum(y == 0)}")
        
        return X, y

def main():
    parser = argparse.ArgumentParser(description='Chuẩn bị dữ liệu training cho CoinJoin detection')
    parser.add_argument('--output-dir', default='data', help='Thư mục output')
    parser.add_argument('--balance-ratio', type=float, default=0.5, help='Tỷ lệ cân bằng positive/negative')
    parser.add_argument('--sample-size', type=int, default=1000, help='Số lượng negative samples')
    
    args = parser.parse_args()
    
    # Khởi tạo preparator
    preparator = CoinJoinDataPreparator(args.output_dir)
    
    # Tạo dataset
    df = preparator.create_training_dataset(args.balance_ratio)
    
    # Tạo feature matrix
    X, y = preparator.create_feature_matrix(df)
    
    logger.info("Hoàn thành chuẩn bị dữ liệu!")

if __name__ == '__main__':
    main()
