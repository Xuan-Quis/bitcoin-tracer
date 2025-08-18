"""
Cluster Analyzer cho CoinJoin Detection
Phân tích và gom nhóm các địa chỉ trong transactions để phát hiện mối quan hệ sở hữu
"""

import logging
from collections import defaultdict, deque
from typing import List, Dict, Set, Optional, Tuple
import statistics
import numpy as np
from datetime import datetime, timedelta

from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)

class UnionFind:
    """Union-Find data structure để gom nhóm địa chỉ"""
    
    def __init__(self):
        self.parent = {}
        self.rank = {}
        self.cluster_sizes = {}
    
    def make_set(self, element: str):
        """Khởi tạo một tập hợp cho phần tử"""
        if element not in self.parent:
            self.parent[element] = element
            self.rank[element] = 0
            self.cluster_sizes[element] = 1
    
    def find(self, element: str) -> str:
        """Tìm đại diện (root) của cụm chứa phần tử, sử dụng path compression"""
        if element not in self.parent:
            self.make_set(element)
        
        if self.parent[element] != element:
            self.parent[element] = self.find(self.parent[element])
        
        return self.parent[element]
    
    def union(self, element1: str, element2: str):
        """Hợp nhất hai cụm, sử dụng union by rank"""
        root1 = self.find(element1)
        root2 = self.find(element2)
        
        if root1 != root2:
            if self.rank[root1] < self.rank[root2]:
                root1, root2 = root2, root1
            
            self.parent[root2] = root1
            self.cluster_sizes[root1] += self.cluster_sizes[root2]
            
            if self.rank[root1] == self.rank[root2]:
                self.rank[root1] += 1
    
    def get_clusters(self) -> Dict[str, List[str]]:
        """Lấy tất cả các cụm"""
        clusters = defaultdict(list)
        
        for element in self.parent:
            root = self.find(element)
            clusters[root].append(element)
        
        return dict(clusters)

class ClusterAnalyzer:
    """
    Phân tích clustering cho các transaction để phát hiện mối quan hệ sở hữu
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.similarity_threshold = config.get('cluster_similarity_threshold', 0.7)
        self.min_cluster_size = config.get('min_cluster_size', 2)
        self.max_cluster_size = config.get('max_cluster_size', 100)
        
        # Cache để tối ưu performance
        self.address_patterns = {}
        self.transaction_history = defaultdict(list)
    
    def analyze_transaction_clusters(self, transactions: List[Dict]) -> Dict:
        """
        Phân tích clustering cho các transaction
        
        Args:
            transactions: Danh sách transactions cần phân tích
            
        Returns:
            Dict chứa thông tin clustering
        """
        logger.info(f"Phân tích clustering cho {len(transactions)} transactions")
        
        # 1. Gom nhóm input addresses
        input_clusters = self.group_input_addresses(transactions)
        
        # 2. Gom nhóm output addresses
        output_clusters = self.group_output_addresses(transactions)
        
        # 3. Tìm connections giữa clusters
        cross_connections = self.find_cluster_connections(input_clusters, output_clusters)
        
        # 4. Phân tích patterns
        cluster_patterns = self.analyze_cluster_patterns(input_clusters, output_clusters)
        
        result = {
            'input_clusters': input_clusters,
            'output_clusters': output_clusters,
            'cross_cluster_connections': cross_connections,
            'cluster_patterns': cluster_patterns,
            'total_clusters': len(input_clusters) + len(output_clusters),
            'total_connections': len(cross_connections)
        }
        
        logger.info(f"Tìm thấy {len(input_clusters)} input clusters, {len(output_clusters)} output clusters")
        return result
    
    def group_input_addresses(self, transactions: List[Dict]) -> Dict:
        """
        Gom nhóm địa chỉ input theo cùng sở hữu
        """
        uf = UnionFind()
        
        # Khởi tạo tất cả địa chỉ input
        for tx in transactions:
            input_addresses = []
            for inp in tx.get('inputs', []):
                if 'address' in inp and inp['address']:
                    input_addresses.append(inp['address'])
                    uf.make_set(inp['address'])
            
            # Hợp nhất các địa chỉ input trong cùng transaction
            if len(input_addresses) > 1:
                first_addr = input_addresses[0]
                for addr in input_addresses[1:]:
                    uf.union(first_addr, addr)
        
        # Tạo clusters từ Union-Find
        clusters = uf.get_clusters()
        
        # Format clusters
        formatted_clusters = {}
        for cluster_id, addresses in clusters.items():
            if len(addresses) >= self.min_cluster_size:
                cluster_data = self._analyze_cluster(addresses, transactions, 'input')
                formatted_clusters[f"input_cluster_{len(formatted_clusters)}"] = cluster_data
        
        return formatted_clusters
    
    def group_output_addresses(self, transactions: List[Dict]) -> Dict:
        """
        Gom nhóm địa chỉ output theo patterns
        """
        # Sử dụng value-based clustering cho outputs
        value_clusters = defaultdict(list)
        
        for tx in transactions:
            outputs = tx.get('outputs', [])
            
            # Gom nhóm theo giá trị gần nhau
            for i, out1 in enumerate(outputs):
                if 'address' not in out1 or not out1['address']:
                    continue
                
                value1 = out1.get('value', 0)
                
                for j, out2 in enumerate(outputs[i+1:], i+1):
                    if 'address' not in out2 or not out2['address']:
                        continue
                    
                    value2 = out2.get('value', 0)
                    
                    # Kiểm tra giá trị gần nhau (CoinJoin thường có outputs cùng giá trị)
                    if self._are_values_similar(value1, value2):
                        value_clusters[f"value_{value1}"].extend([out1['address'], out2['address']])
        
        # Format clusters
        formatted_clusters = {}
        for value_key, addresses in value_clusters.items():
            unique_addresses = list(set(addresses))
            if len(unique_addresses) >= self.min_cluster_size:
                cluster_data = self._analyze_cluster(unique_addresses, transactions, 'output')
                formatted_clusters[f"output_cluster_{len(formatted_clusters)}"] = cluster_data
        
        return formatted_clusters
    
    def find_cluster_connections(self, input_clusters: Dict, output_clusters: Dict) -> List[Dict]:
        """
        Tìm connections giữa input và output clusters
        """
        connections = []
        
        for input_cluster_id, input_cluster in input_clusters.items():
            input_addresses = set(input_cluster['addresses'])
            
            for output_cluster_id, output_cluster in output_clusters.items():
                output_addresses = set(output_cluster['addresses'])
                
                # Tìm địa chỉ chung
                common_addresses = input_addresses & output_addresses
                
                if common_addresses:
                    connection = {
                        'from_cluster': input_cluster_id,
                        'to_cluster': output_cluster_id,
                        'common_addresses': list(common_addresses),
                        'connection_strength': len(common_addresses),
                        'connection_type': 'address_overlap'
                    }
                    connections.append(connection)
        
        return connections
    
    def analyze_cluster_patterns(self, input_clusters: Dict, output_clusters: Dict) -> Dict:
        """
        Phân tích patterns của các clusters
        """
        patterns = {
            'input_cluster_sizes': [],
            'output_cluster_sizes': [],
            'value_distributions': {},
            'temporal_patterns': {},
            'coinjoin_indicators': {}
        }
        
        # Phân tích kích thước clusters
        for cluster in input_clusters.values():
            patterns['input_cluster_sizes'].append(cluster['address_count'])
        
        for cluster in output_clusters.values():
            patterns['output_cluster_sizes'].append(cluster['address_count'])
        
        # Phân tích phân phối giá trị
        all_values = []
        for cluster in output_clusters.values():
            all_values.extend(cluster.get('values', []))
        
        if all_values:
            patterns['value_distributions'] = {
                'mean': statistics.mean(all_values),
                'std': statistics.stdev(all_values) if len(all_values) > 1 else 0,
                'min': min(all_values),
                'max': max(all_values),
                'uniformity': self._calculate_uniformity(all_values)
            }
        
        # Phân tích indicators cho CoinJoin
        patterns['coinjoin_indicators'] = self._calculate_coinjoin_indicators(
            input_clusters, output_clusters
        )
        
        return patterns
    
    def _analyze_cluster(self, addresses: List[str], transactions: List[Dict], cluster_type: str) -> Dict:
        """
        Phân tích chi tiết một cluster
        """
        cluster_data = {
            'addresses': addresses,
            'address_count': len(addresses),
            'cluster_type': cluster_type,
            'total_value': 0,
            'transaction_count': 0,
            'values': [],
            'first_seen': None,
            'last_seen': None,
            'patterns': {}
        }
        
        # Tính toán thống kê
        for tx in transactions:
            if cluster_type == 'input':
                tx_addresses = [inp.get('address', '') for inp in tx.get('inputs', [])]
            else:
                tx_addresses = [out.get('address', '') for out in tx.get('outputs', [])]
            
            # Kiểm tra xem transaction có chứa địa chỉ trong cluster không
            if any(addr in addresses for addr in tx_addresses):
                cluster_data['transaction_count'] += 1
                
                # Tính tổng giá trị
                if cluster_type == 'input':
                    for inp in tx.get('inputs', []):
                        if inp.get('address') in addresses:
                            cluster_data['total_value'] += inp.get('value', 0)
                else:
                    for out in tx.get('outputs', []):
                        if out.get('address') in addresses:
                            value = out.get('value', 0)
                            cluster_data['total_value'] += value
                            cluster_data['values'].append(value)
                
                # Cập nhật thời gian
                tx_time = tx.get('time')
                if tx_time:
                    if not cluster_data['first_seen'] or tx_time < cluster_data['first_seen']:
                        cluster_data['first_seen'] = tx_time
                    if not cluster_data['last_seen'] or tx_time > cluster_data['last_seen']:
                        cluster_data['last_seen'] = tx_time
        
        # Phân tích patterns
        cluster_data['patterns'] = self._analyze_address_patterns(addresses, transactions)
        
        return cluster_data
    
    def _analyze_address_patterns(self, addresses: List[str], transactions: List[Dict]) -> Dict:
        """
        Phân tích patterns của các địa chỉ trong cluster
        """
        patterns = {
            'co_spend_frequency': 0,
            'value_correlation': 0,
            'temporal_correlation': 0,
            'transaction_patterns': []
        }
        
        # Đếm tần suất co-spend
        co_spend_count = 0
        total_tx_with_cluster = 0
        
        for tx in transactions:
            tx_input_addresses = [inp.get('address', '') for inp in tx.get('inputs', [])]
            cluster_addresses_in_tx = [addr for addr in addresses if addr in tx_input_addresses]
            
            if cluster_addresses_in_tx:
                total_tx_with_cluster += 1
                if len(cluster_addresses_in_tx) > 1:
                    co_spend_count += 1
        
        if total_tx_with_cluster > 0:
            patterns['co_spend_frequency'] = co_spend_count / total_tx_with_cluster
        
        return patterns
    
    def _are_values_similar(self, value1: int, value2: int, threshold: float = 0.05) -> bool:
        """
        Kiểm tra xem hai giá trị có gần nhau không
        """
        if value1 == 0 or value2 == 0:
            return False
        
        difference = abs(value1 - value2)
        average = (value1 + value2) / 2
        
        return difference / average <= threshold
    
    def _calculate_uniformity(self, values: List[int]) -> float:
        """
        Tính độ đồng đều của các giá trị (0-1, 1 = hoàn toàn đồng đều)
        """
        if not values or len(values) < 2:
            return 1.0
        
        mean_value = statistics.mean(values)
        variance = statistics.variance(values)
        
        if mean_value == 0:
            return 1.0
        
        # Coefficient of variation
        cv = (variance ** 0.5) / mean_value
        
        # Uniformity score (1 - normalized CV)
        uniformity = max(0, 1 - cv)
        
        return uniformity
    
    def _calculate_coinjoin_indicators(self, input_clusters: Dict, output_clusters: Dict) -> Dict:
        """
        Tính toán các indicators cho CoinJoin detection
        """
        indicators = {
            'input_diversity': len(input_clusters),
            'output_uniformity': 0,
            'cluster_size_distribution': {},
            'value_patterns': {}
        }
        
        # Tính output uniformity
        all_output_values = []
        for cluster in output_clusters.values():
            all_output_values.extend(cluster.get('values', []))
        
        if all_output_values:
            indicators['output_uniformity'] = self._calculate_uniformity(all_output_values)
        
        # Phân tích phân phối kích thước cluster
        input_sizes = [cluster['address_count'] for cluster in input_clusters.values()]
        output_sizes = [cluster['address_count'] for cluster in output_clusters.values()]
        
        if input_sizes:
            indicators['cluster_size_distribution']['input'] = {
                'mean': statistics.mean(input_sizes),
                'std': statistics.stdev(input_sizes) if len(input_sizes) > 1 else 0,
                'min': min(input_sizes),
                'max': max(input_sizes)
            }
        
        if output_sizes:
            indicators['cluster_size_distribution']['output'] = {
                'mean': statistics.mean(output_sizes),
                'std': statistics.stdev(output_sizes) if len(output_sizes) > 1 else 0,
                'min': min(output_sizes),
                'max': max(output_sizes)
            }
        
        return indicators
    
    def get_cluster_similarity(self, cluster1: Dict, cluster2: Dict) -> float:
        """
        Tính độ tương đồng giữa hai clusters
        """
        addresses1 = set(cluster1['addresses'])
        addresses2 = set(cluster2['addresses'])
        
        intersection = len(addresses1 & addresses2)
        union = len(addresses1 | addresses2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def merge_similar_clusters(self, clusters: Dict) -> Dict:
        """
        Hợp nhất các clusters tương tự
        """
        merged_clusters = {}
        processed = set()
        
        cluster_items = list(clusters.items())
        
        for i, (cluster_id1, cluster1) in enumerate(cluster_items):
            if cluster_id1 in processed:
                continue
            
            merged_cluster = cluster1.copy()
            processed.add(cluster_id1)
            
            for j, (cluster_id2, cluster2) in enumerate(cluster_items[i+1:], i+1):
                if cluster_id2 in processed:
                    continue
                
                similarity = self.get_cluster_similarity(cluster1, cluster2)
                
                if similarity >= self.similarity_threshold:
                    # Hợp nhất clusters
                    merged_cluster['addresses'].extend(cluster2['addresses'])
                    merged_cluster['addresses'] = list(set(merged_cluster['addresses']))
                    merged_cluster['address_count'] = len(merged_cluster['addresses'])
                    merged_cluster['total_value'] += cluster2.get('total_value', 0)
                    merged_cluster['transaction_count'] += cluster2.get('transaction_count', 0)
                    
                    processed.add(cluster_id2)
            
            merged_clusters[cluster_id1] = merged_cluster
        
        return merged_clusters
