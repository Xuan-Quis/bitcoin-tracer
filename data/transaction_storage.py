"""
Transaction Storage cho AI Investigation
Lưu trữ các transaction liên quan đến CoinJoin
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime

from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TransactionStorage:
    """Storage class cho transactions"""
    
    def __init__(self, config: Config):
        self.config = config
        self.storage_dir = config.get('storage_dir', './storage')
        self.save_only_coinjoin = config.get('save_only_coinjoin', True)
        
        # Tạo thư mục storage
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(os.path.join(self.storage_dir, 'transactions'), exist_ok=True)
        os.makedirs(os.path.join(self.storage_dir, 'clusters'), exist_ok=True)
        os.makedirs(os.path.join(self.storage_dir, 'metadata'), exist_ok=True)
    
    def store_coinjoin_transactions(self, transactions: List[Dict]):
        """Lưu trữ các transaction CoinJoin"""
        if not transactions:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Lọc chỉ lưu CoinJoin transactions nếu được cấu hình
        if self.save_only_coinjoin:
            transactions_to_save = [tx for tx in transactions if tx.get('is_coinjoin', False)]
        else:
            transactions_to_save = transactions
        
        if not transactions_to_save:
            logger.info("No transactions to save")
            return
        
        # Lưu transactions
        transactions_file = os.path.join(
            self.storage_dir, 
            'transactions', 
            f'coinjoin_transactions_{timestamp}.json'
        )
        
        with open(transactions_file, 'w') as f:
            json.dump(transactions_to_save, f, indent=2, default=str)
        
        logger.info(f"Saved {len(transactions_to_save)} transactions to {transactions_file}")
        
        # Lưu metadata
        self._save_metadata(transactions_to_save, timestamp)
    
    def store_clustering_data(self, clusters: Dict, timestamp: str = None):
        """Lưu trữ clustering data"""
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        clusters_file = os.path.join(
            self.storage_dir,
            'clusters',
            f'clusters_{timestamp}.json'
        )
        
        with open(clusters_file, 'w') as f:
            json.dump(clusters, f, indent=2, default=str)
        
        logger.info(f"Saved clustering data to {clusters_file}")
    
    def _save_metadata(self, transactions: List[Dict], timestamp: str):
        """Lưu metadata về transactions"""
        metadata = {
            'timestamp': timestamp,
            'transaction_count': len(transactions),
            'coinjoin_count': len([tx for tx in transactions if tx.get('is_coinjoin', False)]),
            'total_value': sum(tx.get('total_output_value', 0) for tx in transactions),
            'average_score': 0.0,
            'score_distribution': {},
            'indicators_summary': {}
        }
        
        # Tính điểm trung bình
        coinjoin_txs = [tx for tx in transactions if tx.get('is_coinjoin', False)]
        if coinjoin_txs:
            scores = [tx.get('coinjoin_score', 0) for tx in coinjoin_txs]
            metadata['average_score'] = sum(scores) / len(scores)
        
        # Phân tích indicators
        all_indicators = {}
        for tx in coinjoin_txs:
            indicators = tx.get('coinjoin_indicators', {})
            for indicator, value in indicators.items():
                if indicator not in all_indicators:
                    all_indicators[indicator] = []
                all_indicators[indicator].append(value)
        
        # Tính summary cho indicators
        for indicator, values in all_indicators.items():
            metadata['indicators_summary'][indicator] = {
                'count': len(values),
                'average': sum(values) / len(values),
                'min': min(values),
                'max': max(values)
            }
        
        metadata_file = os.path.join(
            self.storage_dir,
            'metadata',
            f'metadata_{timestamp}.json'
        )
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"Saved metadata to {metadata_file}")
    
    def load_transactions(self, file_path: str) -> List[Dict]:
        """Load transactions từ file"""
        try:
            with open(file_path, 'r') as f:
                transactions = json.load(f)
            logger.info(f"Loaded {len(transactions)} transactions from {file_path}")
            return transactions
        except Exception as e:
            logger.error(f"Error loading transactions from {file_path}: {str(e)}")
            return []
    
    def load_clusters(self, file_path: str) -> Dict:
        """Load clusters từ file"""
        try:
            with open(file_path, 'r') as f:
                clusters = json.load(f)
            logger.info(f"Loaded clusters from {file_path}")
            return clusters
        except Exception as e:
            logger.error(f"Error loading clusters from {file_path}: {str(e)}")
            return {}
    
    def get_storage_stats(self) -> Dict:
        """Lấy thống kê về storage"""
        stats = {
            'total_files': 0,
            'total_transactions': 0,
            'total_coinjoin': 0,
            'storage_size_mb': 0
        }
        
        # Đếm files và transactions
        transactions_dir = os.path.join(self.storage_dir, 'transactions')
        if os.path.exists(transactions_dir):
            for filename in os.listdir(transactions_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(transactions_dir, filename)
                    try:
                        with open(file_path, 'r') as f:
                            transactions = json.load(f)
                            stats['total_files'] += 1
                            stats['total_transactions'] += len(transactions)
                            stats['total_coinjoin'] += len([tx for tx in transactions if tx.get('is_coinjoin', False)])
                    except Exception as e:
                        logger.warning(f"Error reading {file_path}: {str(e)}")
        
        # Tính kích thước storage
        total_size = 0
        for root, dirs, files in os.walk(self.storage_dir):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
        
        stats['storage_size_mb'] = total_size / (1024 * 1024)
        
        return stats
