"""
CoinJoin Detector cho AI Investigation
Phát hiện các giao dịch CoinJoin dựa trên clustering analysis
"""

import logging
from typing import List, Dict, Optional, Tuple
import statistics
import numpy as np
from collections import defaultdict

from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)

class CoinJoinDetector:
    """
    Phát hiện CoinJoin dựa trên clustering analysis và các patterns
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.min_coinjoin_score = config.get('min_coinjoin_score', 4.0)
        self.output_uniformity_threshold = config.get('output_uniformity_threshold', 0.8)
        self.input_diversity_threshold = config.get('input_diversity_threshold', 3)
        self.min_transaction_size = config.get('min_transaction_size', 5)
        
        # Weights cho các indicators
        self.weights = {
            'input_diversity': 2.0,
            'output_uniformity': 2.0,
            'cross_cluster_connections': 1.0,
            'transaction_size': 1.0,
            'change_outputs': 0.5,
            'value_patterns': 1.0,
            'temporal_patterns': 0.5
        }
    
    def detect_coinjoin_with_clusters(self, transactions: List[Dict], clusters: Dict) -> List[Dict]:
        """
        Phát hiện CoinJoin dựa trên clustering analysis
        
        Args:
            transactions: Danh sách transactions cần phân tích
            clusters: Kết quả clustering analysis
            
        Returns:
            List các transactions được phát hiện là CoinJoin
        """
        logger.info(f"Phát hiện CoinJoin cho {len(transactions)} transactions")
        
        coinjoin_transactions = []
        
        for tx in transactions:
            # Phân tích transaction với clusters
            coinjoin_score, indicators = self._analyze_transaction_coinjoin(tx, clusters)
            
            if coinjoin_score >= self.min_coinjoin_score:
                tx['coinjoin_score'] = coinjoin_score
                tx['coinjoin_indicators'] = indicators
                tx['is_coinjoin'] = True
                tx['input_clusters'] = clusters.get('input_clusters', {})
                tx['output_clusters'] = clusters.get('output_clusters', {})
                tx['cross_connections'] = clusters.get('cross_cluster_connections', [])
                
                coinjoin_transactions.append(tx)
                
                logger.info(f"Phát hiện CoinJoin: {tx.get('hash', '')[:10]}... (score: {coinjoin_score:.2f})")
        
        logger.info(f"Tìm thấy {len(coinjoin_transactions)} giao dịch CoinJoin")
        return coinjoin_transactions
    
    def _analyze_transaction_coinjoin(self, tx: Dict, clusters: Dict) -> Tuple[float, Dict]:
        """
        Phân tích một transaction để phát hiện CoinJoin
        
        Returns:
            Tuple (score, indicators)
        """
        score = 0.0
        indicators = {}
        
        # 1. Kiểm tra input cluster diversity
        input_diversity_score = self._calculate_input_diversity(tx, clusters)
        if input_diversity_score > 0:
            score += input_diversity_score * self.weights['input_diversity']
            indicators['input_diversity'] = input_diversity_score
        
        # 2. Kiểm tra output uniformity
        output_uniformity_score = self._calculate_output_uniformity(tx, clusters)
        if output_uniformity_score > 0:
            score += output_uniformity_score * self.weights['output_uniformity']
            indicators['output_uniformity'] = output_uniformity_score
        
        # 3. Kiểm tra cross-cluster connections
        cross_connection_score = self._calculate_cross_connection_score(tx, clusters)
        if cross_connection_score > 0:
            score += cross_connection_score * self.weights['cross_cluster_connections']
            indicators['cross_connections'] = cross_connection_score
        
        # 4. Kiểm tra transaction size
        size_score = self._calculate_transaction_size_score(tx)
        if size_score > 0:
            score += size_score * self.weights['transaction_size']
            indicators['transaction_size'] = size_score
        
        # 5. Kiểm tra change outputs
        change_score = self._detect_change_outputs(tx, clusters)
        if change_score > 0:
            score += change_score * self.weights['change_outputs']
            indicators['change_outputs'] = change_score
        
        # 6. Kiểm tra value patterns
        value_pattern_score = self._analyze_value_patterns(tx, clusters)
        if value_pattern_score > 0:
            score += value_pattern_score * self.weights['value_patterns']
            indicators['value_patterns'] = value_pattern_score
        
        # 7. Kiểm tra temporal patterns
        temporal_score = self._analyze_temporal_patterns(tx, clusters)
        if temporal_score > 0:
            score += temporal_score * self.weights['temporal_patterns']
            indicators['temporal_patterns'] = temporal_score
        
        return score, indicators
    
    def _calculate_input_diversity(self, tx: Dict, clusters: Dict) -> float:
        """
        Tính điểm diversity của input clusters
        """
        input_clusters = clusters.get('input_clusters', {})
        tx_input_addresses = set()
        
        for inp in tx.get('inputs', []):
            if 'address' in inp and inp['address']:
                tx_input_addresses.add(inp['address'])
        
        if not tx_input_addresses:
            return 0.0
        
        # Đếm số clusters chứa input addresses
        involved_clusters = set()
        for cluster_id, cluster_data in input_clusters.items():
            cluster_addresses = set(cluster_data.get('addresses', []))
            if tx_input_addresses & cluster_addresses:
                involved_clusters.add(cluster_id)
        
        # Tính điểm diversity
        diversity_score = len(involved_clusters) / max(1, len(tx_input_addresses))
        
        # Bonus cho nhiều clusters khác nhau
        if len(involved_clusters) >= self.input_diversity_threshold:
            diversity_score += 0.5
        
        return min(1.0, diversity_score)
    
    def _calculate_output_uniformity(self, tx: Dict, clusters: Dict) -> float:
        """
        Tính điểm uniformity của output values
        """
        outputs = tx.get('outputs', [])
        if len(outputs) < 2:
            return 0.0
        
        # Lấy các giá trị output
        output_values = [out.get('value', 0) for out in outputs if out.get('value', 0) > 0]
        
        if len(output_values) < 2:
            return 0.0
        
        # Tính uniformity
        mean_value = statistics.mean(output_values)
        variance = statistics.variance(output_values)
        
        if mean_value == 0:
            return 0.0
        
        # Coefficient of variation
        cv = (variance ** 0.5) / mean_value
        
        # Uniformity score (1 - normalized CV)
        uniformity = max(0, 1 - cv)
        
        # Bonus cho uniformity cao
        if uniformity >= self.output_uniformity_threshold:
            uniformity += 0.2
        
        return min(1.0, uniformity)
    
    def _calculate_cross_connection_score(self, tx: Dict, clusters: Dict) -> float:
        """
        Tính điểm dựa trên cross-cluster connections
        CoinJoin thường có ít cross-connections
        """
        cross_connections = clusters.get('cross_cluster_connections', [])
        
        if not cross_connections:
            return 0.5  # Không có connections = có thể là CoinJoin
        
        # Tính số connections liên quan đến transaction này
        tx_addresses = set()
        for inp in tx.get('inputs', []):
            if 'address' in inp and inp['address']:
                tx_addresses.add(inp['address'])
        for out in tx.get('outputs', []):
            if 'address' in out and out['address']:
                tx_addresses.add(out['address'])
        
        relevant_connections = 0
        for connection in cross_connections:
            common_addresses = set(connection.get('common_addresses', []))
            if tx_addresses & common_addresses:
                relevant_connections += 1
        
        # Ít connections = điểm cao hơn
        if relevant_connections == 0:
            return 1.0
        elif relevant_connections == 1:
            return 0.5
        else:
            return max(0, 1.0 - (relevant_connections * 0.2))
    
    def _calculate_transaction_size_score(self, tx: Dict) -> float:
        """
        Tính điểm dựa trên kích thước transaction
        """
        vin_count = tx.get('vin_sz', 0)
        vout_count = tx.get('vout_sz', 0)
        
        if vin_count >= self.min_transaction_size and vout_count >= self.min_transaction_size:
            return 1.0
        elif vin_count >= 3 and vout_count >= 3:
            return 0.5
        else:
            return 0.0
    
    def _detect_change_outputs(self, tx: Dict, clusters: Dict) -> float:
        """
        Phát hiện change outputs
        """
        outputs = tx.get('outputs', [])
        if len(outputs) < 2:
            return 0.0
        
        # Tính giá trị trung bình của outputs
        output_values = [out.get('value', 0) for out in outputs]
        mean_value = statistics.mean(output_values)
        
        # Tìm change outputs (giá trị khác biệt đáng kể)
        change_outputs = []
        for out in outputs:
            value = out.get('value', 0)
            if value > 0 and abs(value - mean_value) / mean_value > 0.1:  # > 10% khác biệt
                change_outputs.append(out)
        
        # Có change outputs = điểm cao hơn
        if change_outputs:
            return min(1.0, len(change_outputs) * 0.3)
        
        return 0.0
    
    def _analyze_value_patterns(self, tx: Dict, clusters: Dict) -> float:
        """
        Phân tích patterns giá trị
        """
        outputs = tx.get('outputs', [])
        if len(outputs) < 2:
            return 0.0
        
        output_values = [out.get('value', 0) for out in outputs if out.get('value', 0) > 0]
        
        if len(output_values) < 2:
            return 0.0
        
        # Kiểm tra các patterns CoinJoin
        patterns_found = 0
        
        # 1. Kiểm tra giá trị đồng đều
        mean_value = statistics.mean(output_values)
        variance = statistics.variance(output_values)
        cv = (variance ** 0.5) / mean_value if mean_value > 0 else 0
        
        if cv < 0.1:  # Độ biến thiên thấp
            patterns_found += 1
        
        # 2. Kiểm tra số lượng outputs
        if 3 <= len(output_values) <= 10:  # Range phổ biến cho CoinJoin
            patterns_found += 1
        
        # 3. Kiểm tra phân phối giá trị
        value_counts = defaultdict(int)
        for value in output_values:
            value_counts[value] += 1
        
        # Nhiều outputs cùng giá trị
        max_count = max(value_counts.values()) if value_counts else 0
        if max_count >= 2:
            patterns_found += 1
        
        return min(1.0, patterns_found * 0.33)
    
    def _analyze_temporal_patterns(self, tx: Dict, clusters: Dict) -> float:
        """
        Phân tích patterns thời gian
        """
        # Kiểm tra thời gian giao dịch
        tx_time = tx.get('time')
        if not tx_time:
            return 0.0
        
        # CoinJoin thường xảy ra trong khoảng thời gian ngắn
        # (có thể mở rộng để phân tích patterns thời gian phức tạp hơn)
        
        # Tạm thời trả về điểm cơ bản
        return 0.3
    
    def detect_coinjoin_patterns(self, transactions: List[Dict]) -> Dict:
        """
        Phát hiện patterns CoinJoin tổng thể
        """
        patterns = {
            'coinjoin_count': 0,
            'coinjoin_ratio': 0.0,
            'average_score': 0.0,
            'score_distribution': {},
            'common_indicators': {},
            'temporal_distribution': {}
        }
        
        coinjoin_txs = [tx for tx in transactions if tx.get('is_coinjoin', False)]
        
        if not coinjoin_txs:
            return patterns
        
        patterns['coinjoin_count'] = len(coinjoin_txs)
        patterns['coinjoin_ratio'] = len(coinjoin_txs) / len(transactions)
        
        # Tính điểm trung bình
        scores = [tx.get('coinjoin_score', 0) for tx in coinjoin_txs]
        patterns['average_score'] = statistics.mean(scores)
        
        # Phân tích indicators phổ biến
        all_indicators = defaultdict(int)
        for tx in coinjoin_txs:
            indicators = tx.get('coinjoin_indicators', {})
            for indicator, value in indicators.items():
                all_indicators[indicator] += 1
        
        patterns['common_indicators'] = dict(all_indicators)
        
        return patterns
    
    def validate_coinjoin_detection(self, transactions: List[Dict], clusters: Dict) -> Dict:
        """
        Validate kết quả phát hiện CoinJoin
        """
        validation = {
            'total_transactions': len(transactions),
            'coinjoin_detected': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'validation_errors': []
        }
        
        coinjoin_txs = [tx for tx in transactions if tx.get('is_coinjoin', False)]
        validation['coinjoin_detected'] = len(coinjoin_txs)
        
        # Validation logic có thể được mở rộng dựa trên ground truth data
        # Hiện tại chỉ tính toán cơ bản
        
        return validation
    
    def get_coinjoin_confidence(self, tx: Dict, clusters: Dict) -> float:
        """
        Tính độ tin cậy của phát hiện CoinJoin
        """
        if not tx.get('is_coinjoin', False):
            return 0.0
        
        score = tx.get('coinjoin_score', 0)
        indicators = tx.get('coinjoin_indicators', {})
        
        # Tính confidence dựa trên score và số lượng indicators
        confidence = min(1.0, score / 10.0)  # Normalize score
        
        # Bonus cho nhiều indicators
        indicator_count = len(indicators)
        if indicator_count >= 5:
            confidence += 0.1
        elif indicator_count >= 3:
            confidence += 0.05
        
        # Bonus cho indicators mạnh
        strong_indicators = ['input_diversity', 'output_uniformity']
        for indicator in strong_indicators:
            if indicator in indicators and indicators[indicator] > 0.8:
                confidence += 0.05
        
        return min(1.0, confidence)
