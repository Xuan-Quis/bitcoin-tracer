"""
Core Investigation Engine cho CoinJoin Detection
Tự động điều tra và phát hiện các giao dịch CoinJoin dựa trên clustering
"""

import logging
from collections import deque, defaultdict
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime, timedelta
import json
import time

from ..api.blockchain_api import BlockchainAPI
from ..data.transaction_storage import TransactionStorage
from .cluster_analyzer import ClusterAnalyzer
from .coinjoin_detector import CoinJoinDetector
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)

class CoinJoinInvestigator:
    """
    Core investigation engine để phát hiện CoinJoin với clustering và điều tra đệ quy
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.api_client = BlockchainAPI(config)
        self.storage = TransactionStorage(config)
        self.cluster_analyzer = ClusterAnalyzer(config)
        self.coinjoin_detector = CoinJoinDetector(config)
        
        # Investigation state
        self.investigation_queue = deque()
        self.investigated_addresses = set()
        self.related_transactions = []
        self.clusters = {}
        self.coinjoin_transactions = []
        self.investigation_path = []
        self.consecutive_non_coinjoin = 0
        
        # Statistics
        self.stats = {
            'initial_addresses': 0,
            'investigated_addresses': 0,
            'coinjoin_transactions': 0,
            'clusters_found': 0,
            'investigation_depth': 0,
            'total_related_transactions': 0,
            'start_time': None,
            'end_time': None
        }
    
    def investigate_addresses(self, initial_addresses: List[str], api_source: str = 'blockstream') -> Dict:
        """
        Điều tra đệ quy các địa chỉ CoinJoin
        
        Args:
            initial_addresses: Danh sách địa chỉ ban đầu để điều tra
            api_source: Nguồn API để fetch transactions
            
        Returns:
            Dict chứa kết quả điều tra
        """
        logger.info(f"Bắt đầu điều tra {len(initial_addresses)} địa chỉ ban đầu")
        
        # Khởi tạo investigation
        self.stats['start_time'] = datetime.now()
        self.stats['initial_addresses'] = len(initial_addresses)
        self.investigation_queue = deque(initial_addresses)
        self.investigated_addresses.clear()
        self.related_transactions.clear()
        self.clusters.clear()
        self.coinjoin_transactions.clear()
        self.investigation_path.clear()
        self.consecutive_non_coinjoin = 0
        
        # Điều tra đệ quy
        while self.investigation_queue:
            address = self.investigation_queue.popleft()
            
            if address in self.investigated_addresses:
                continue
            
            logger.info(f"Điều tra địa chỉ: {address[:10]}...")
            
            try:
                # Fetch transactions
                transactions = self.api_client.fetch_address_transactions(address, api_source)
                
                if not transactions:
                    logger.warning(f"Không tìm thấy transaction cho địa chỉ: {address}")
                    continue
                
                # Phân tích clustering
                clusters = self.cluster_analyzer.analyze_transaction_clusters(transactions)
                
                # Phát hiện CoinJoin
                coinjoin_txs = self.coinjoin_detector.detect_coinjoin_with_clusters(transactions, clusters)
                
                # Cập nhật investigation state
                self.investigated_addresses.add(address)
                self.stats['investigated_addresses'] += 1
                
                if coinjoin_txs:
                    logger.info(f"Phát hiện {len(coinjoin_txs)} giao dịch CoinJoin cho địa chỉ {address}")
                    
                    # Reset consecutive counter
                    self.consecutive_non_coinjoin = 0
                    
                    # Thêm vào danh sách điều tra
                    self.add_related_addresses(coinjoin_txs, clusters)
                    self.coinjoin_transactions.extend(coinjoin_txs)
                    self.stats['coinjoin_transactions'] += len(coinjoin_txs)
                    
                    # Lưu trữ transaction liên quan
                    self.storage.store_coinjoin_transactions(coinjoin_txs)
                    
                else:
                    # Tăng counter cho non-coinjoin transactions
                    self.consecutive_non_coinjoin += 1
                    logger.debug(f"Không phát hiện CoinJoin cho địa chỉ {address}. Consecutive: {self.consecutive_non_coinjoin}")
                
                # Kiểm tra điều kiện dừng
                if self.should_stop_investigation():
                    logger.info("Điều kiện dừng được kích hoạt")
                    break
                
                # Rate limiting
                time.sleep(self.config.get('api_rate_limit_delay', 0.1))
                
            except Exception as e:
                logger.error(f"Lỗi khi điều tra địa chỉ {address}: {str(e)}")
                continue
        
        # Kết thúc investigation
        self.stats['end_time'] = datetime.now()
        self.stats['clusters_found'] = len(self.clusters)
        self.stats['total_related_transactions'] = len(self.related_transactions)
        
        return self.generate_investigation_report()
    
    def add_related_addresses(self, coinjoin_txs: List[Dict], clusters: Dict):
        """
        Thêm các địa chỉ liên quan vào queue điều tra
        """
        related_addresses = set()
        
        for tx in coinjoin_txs:
            # Lấy tất cả địa chỉ input và output
            input_addresses = set()
            output_addresses = set()
            
            for inp in tx.get('inputs', []):
                if 'address' in inp:
                    input_addresses.add(inp['address'])
            
            for out in tx.get('outputs', []):
                if 'address' in out:
                    output_addresses.add(out['address'])
            
            # Thêm vào related addresses
            all_addresses = input_addresses | output_addresses
            related_addresses.update(all_addresses)
        
        # Thêm vào investigation queue (chưa điều tra)
        for addr in related_addresses:
            if addr not in self.investigated_addresses and addr not in self.investigation_queue:
                self.investigation_queue.append(addr)
                logger.debug(f"Thêm địa chỉ liên quan vào queue: {addr[:10]}...")
    
    def should_stop_investigation(self) -> bool:
        """
        Kiểm tra điều kiện dừng điều tra
        
        Điều kiện dừng:
        1. Đã điều tra 10 transaction liên tiếp không phát hiện CoinJoin
        2. Output addresses không được cluster vào các transaction ban đầu
        3. Đã đạt độ sâu tối đa
        4. Không còn địa chỉ nào để điều tra
        """
        
        # 1. Kiểm tra 10 transaction liên tiếp không CoinJoin
        if self.consecutive_non_coinjoin >= self.config.get('max_consecutive_non_coinjoin', 10):
            logger.info(f"Dừng điều tra: {self.consecutive_non_coinjoin} transaction liên tiếp không phát hiện CoinJoin")
            return True
        
        # 2. Kiểm tra output clustering
        if not self.has_cluster_connections():
            logger.info("Dừng điều tra: Output addresses không được cluster vào transaction ban đầu")
            return True
        
        # 3. Kiểm tra độ sâu tối đa
        max_depth = self.config.get('max_investigation_depth', 10)
        if len(self.investigation_path) >= max_depth:
            logger.info(f"Dừng điều tra: Đã đạt độ sâu tối đa ({max_depth})")
            return True
        
        # 4. Kiểm tra queue rỗng
        if not self.investigation_queue:
            logger.info("Dừng điều tra: Không còn địa chỉ nào để điều tra")
            return True
        
        return False
    
    def has_cluster_connections(self) -> bool:
        """
        Kiểm tra xem có connections giữa clusters không
        """
        if not self.clusters:
            return False
        
        # Kiểm tra cross-cluster connections
        for cluster_data in self.clusters.values():
            if cluster_data.get('cross_cluster_connections'):
                return True
        
        return False
    
    def generate_investigation_report(self) -> Dict:
        """
        Tạo báo cáo chi tiết về investigation
        """
        duration = self.stats['end_time'] - self.stats['start_time'] if self.stats['end_time'] else timedelta(0)
        
        report = {
            'investigation_summary': {
                'initial_addresses': self.stats['initial_addresses'],
                'investigated_addresses': self.stats['investigated_addresses'],
                'coinjoin_transactions': self.stats['coinjoin_transactions'],
                'clusters_found': self.stats['clusters_found'],
                'investigation_depth': len(self.investigation_path),
                'total_related_transactions': self.stats['total_related_transactions'],
                'duration_seconds': duration.total_seconds(),
                'consecutive_non_coinjoin': self.consecutive_non_coinjoin
            },
            'coinjoin_transactions': [
                {
                    'hash': tx.get('hash', ''),
                    'coinjoin_score': tx.get('coinjoin_score', 0),
                    'input_clusters': len(tx.get('input_clusters', {})),
                    'output_clusters': len(tx.get('output_clusters', {})),
                    'investigation_depth': tx.get('investigation_depth', 0),
                    'related_addresses': list(set([
                        inp.get('address', '') for inp in tx.get('inputs', [])
                    ] + [
                        out.get('address', '') for out in tx.get('outputs', [])
                    ]))
                }
                for tx in self.coinjoin_transactions
            ],
            'clusters': [
                {
                    'cluster_id': cluster_id,
                    'addresses': cluster_data.get('addresses', []),
                    'total_value': cluster_data.get('total_value', 0),
                    'coinjoin_count': cluster_data.get('coinjoin_count', 0),
                    'address_count': len(cluster_data.get('addresses', []))
                }
                for cluster_id, cluster_data in self.clusters.items()
            ],
            'investigation_path': self.investigation_path,
            'config_used': {
                'max_depth': self.config.get('max_investigation_depth', 10),
                'max_consecutive_non_coinjoin': self.config.get('max_consecutive_non_coinjoin', 10),
                'min_coinjoin_score': self.config.get('min_coinjoin_score', 4.0),
                'cluster_similarity_threshold': self.config.get('cluster_similarity_threshold', 0.8)
            }
        }
        
        return report
    
    def get_investigation_status(self) -> Dict:
        """
        Lấy trạng thái hiện tại của investigation
        """
        return {
            'queue_size': len(self.investigation_queue),
            'investigated_count': len(self.investigated_addresses),
            'coinjoin_found': len(self.coinjoin_transactions),
            'consecutive_non_coinjoin': self.consecutive_non_coinjoin,
            'current_depth': len(self.investigation_path),
            'is_running': len(self.investigation_queue) > 0
        }
    
    def reset_investigation(self):
        """
        Reset investigation state
        """
        self.investigation_queue.clear()
        self.investigated_addresses.clear()
        self.related_transactions.clear()
        self.clusters.clear()
        self.coinjoin_transactions.clear()
        self.investigation_path.clear()
        self.consecutive_non_coinjoin = 0
        self.stats = {
            'initial_addresses': 0,
            'investigated_addresses': 0,
            'coinjoin_transactions': 0,
            'clusters_found': 0,
            'investigation_depth': 0,
            'total_related_transactions': 0,
            'start_time': None,
            'end_time': None
        }
        logger.info("Đã reset investigation state")
