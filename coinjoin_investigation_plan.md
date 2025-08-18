# Kế Hoạch AI Phát Hiện CoinJoin với Clustering và Điều Tra Đệ Quy

## 🎯 Mục Tiêu
Xây dựng hệ thống AI tự động điều tra và phát hiện các giao dịch CoinJoin dựa trên dataset địa chỉ ban đầu, sử dụng clustering để gom nhóm và điều tra đệ quy cho đến khi không còn phát hiện bất thường.

## 🏗️ Kiến Trúc Hệ Thống

### 1. **Core Components**

```
AI/
├── investigation/
│   ├── __init__.py
│   ├── coinjoin_investigator.py      # Core investigation engine
│   ├── transaction_fetcher.py        # API transaction fetcher
│   ├── cluster_analyzer.py           # Clustering analysis
│   ├── coinjoin_detector.py          # CoinJoin detection logic
│   └── investigation_pipeline.py     # Main pipeline orchestrator
├── data/
│   ├── __init__.py
│   ├── dataset_loader.py             # Load initial dataset
│   ├── transaction_storage.py        # Store related transactions
│   └── cluster_storage.py            # Store cluster data
├── api/
│   ├── __init__.py
│   ├── blockchain_api.py             # Generic blockchain API interface
│   ├── bitcoin_core_api.py           # Bitcoin Core specific
│   ├── blockstream_api.py            # Blockstream API
│   └── mempool_api.py                # Mempool.space API
├── models/
│   ├── __init__.py
│   ├── investigation_models.py       # Data models
│   ├── cluster_models.py             # Cluster data structures
│   └── transaction_models.py         # Transaction data structures
├── utils/
│   ├── __init__.py
│   ├── config.py                     # Configuration management
│   ├── logger.py                     # Logging utilities
│   └── validators.py                 # Data validation
└── config/
    ├── investigation_config.yaml     # Investigation parameters
    └── api_config.yaml              # API configurations
```

## 🔍 Thuật Toán Điều Tra

### 1. **Investigation Flow**

```python
class CoinJoinInvestigator:
    def investigate_addresses(self, initial_addresses: List[str], api_source: str):
        """
        Điều tra đệ quy các địa chỉ CoinJoin
        
        Flow:
        1. Load dataset địa chỉ ban đầu
        2. Fetch transactions cho mỗi địa chỉ
        3. Phân tích clustering
        4. Phát hiện CoinJoin patterns
        5. Điều tra đệ quy các địa chỉ liên quan
        6. Dừng khi không còn bất thường
        """
        
        # Khởi tạo
        self.investigation_queue = deque(initial_addresses)
        self.investigated_addresses = set()
        self.related_transactions = []
        self.clusters = {}
        self.coinjoin_transactions = []
        
        # Điều tra đệ quy
        while self.investigation_queue:
            address = self.investigation_queue.popleft()
            
            if address in self.investigated_addresses:
                continue
                
            # Fetch transactions
            transactions = self.fetch_transactions(address, api_source)
            
            # Phân tích clustering
            clusters = self.analyze_clustering(transactions)
            
            # Phát hiện CoinJoin
            coinjoin_txs = self.detect_coinjoin(transactions, clusters)
            
            if coinjoin_txs:
                # Thêm vào danh sách điều tra
                self.add_related_addresses(coinjoin_txs)
                self.coinjoin_transactions.extend(coinjoin_txs)
            
            # Kiểm tra điều kiện dừng
            if self.should_stop_investigation():
                break
```

### 2. **Clustering Analysis**

```python
class ClusterAnalyzer:
    def analyze_transaction_clusters(self, transactions: List[Dict]) -> Dict:
        """
        Phân tích clustering cho các transaction
        
        Returns:
        {
            'input_clusters': {
                'cluster_1': {
                    'addresses': ['addr1', 'addr2', 'addr3'],
                    'total_value': 1000000,
                    'transaction_count': 5
                }
            },
            'output_clusters': {
                'cluster_1': {
                    'addresses': ['addr4', 'addr5'],
                    'total_value': 500000,
                    'transaction_count': 3
                }
            },
            'cross_cluster_connections': [
                {
                    'from_cluster': 'input_cluster_1',
                    'to_cluster': 'output_cluster_1',
                    'common_addresses': ['addr1'],
                    'connection_strength': 1
                }
            ]
        }
        """
        
        # 1. Gom nhóm input addresses
        input_clusters = self.group_input_addresses(transactions)
        
        # 2. Gom nhóm output addresses  
        output_clusters = self.group_output_addresses(transactions)
        
        # 3. Tìm connections giữa clusters
        connections = self.find_cluster_connections(input_clusters, output_clusters)
        
        return {
            'input_clusters': input_clusters,
            'output_clusters': output_clusters,
            'cross_cluster_connections': connections
        }
    
    def group_input_addresses(self, transactions: List[Dict]) -> Dict:
        """Gom nhóm địa chỉ input theo cùng sở hữu"""
        clusters = {}
        
        for tx in transactions:
            input_addresses = tx.get('inputs', [])
            
            # Sử dụng Union-Find để gom nhóm
            for i, input1 in enumerate(input_addresses):
                for j, input2 in enumerate(input_addresses[i+1:], i+1):
                    if self.are_addresses_related(input1, input2):
                        self.merge_clusters(clusters, input1, input2)
        
        return clusters
    
    def are_addresses_related(self, addr1: str, addr2: str) -> bool:
        """
        Kiểm tra xem hai địa chỉ có liên quan không
        - Cùng xuất hiện trong nhiều transaction
        - Có pattern giao dịch tương tự
        - Cùng thời gian hoạt động
        """
        # Implementation logic
        pass
```

### 3. **CoinJoin Detection với Clustering**

```python
class CoinJoinDetector:
    def detect_coinjoin_with_clusters(self, transactions: List[Dict], clusters: Dict) -> List[Dict]:
        """
        Phát hiện CoinJoin dựa trên clustering analysis
        
        CoinJoin Indicators:
        1. Nhiều input clusters khác nhau
        2. Output clusters có giá trị đồng đều
        3. Ít hoặc không có cross-cluster connections
        4. Kích thước transaction lớn
        """
        
        coinjoin_transactions = []
        
        for tx in transactions:
            score = 0.0
            indicators = {}
            
            # 1. Kiểm tra input cluster diversity
            input_cluster_count = len(self.get_input_clusters(tx, clusters))
            if input_cluster_count >= 3:
                score += 2.0
                indicators['input_diversity'] = input_cluster_count
            
            # 2. Kiểm tra output uniformity
            output_uniformity = self.calculate_output_uniformity(tx, clusters)
            if output_uniformity > 0.8:
                score += 2.0
                indicators['output_uniformity'] = output_uniformity
            
            # 3. Kiểm tra cross-cluster connections
            cross_connections = self.count_cross_connections(tx, clusters)
            if cross_connections <= 1:
                score += 1.0
                indicators['low_cross_connections'] = cross_connections
            
            # 4. Kiểm tra transaction size
            if tx.get('vin_sz', 0) >= 5 and tx.get('vout_sz', 0) >= 5:
                score += 1.0
                indicators['large_size'] = True
            
            # 5. Kiểm tra change outputs
            change_outputs = self.detect_change_outputs(tx, clusters)
            if change_outputs:
                score += 0.5
                indicators['has_change'] = len(change_outputs)
            
            # Đánh giá CoinJoin
            if score >= 4.0:
                tx['coinjoin_score'] = score
                tx['coinjoin_indicators'] = indicators
                tx['is_coinjoin'] = True
                coinjoin_transactions.append(tx)
        
        return coinjoin_transactions
```

## 🔄 Điều Tra Đệ Quy

### 1. **Recursive Investigation Logic**

```python
class RecursiveInvestigator:
    def investigate_recursively(self, initial_addresses: List[str], max_depth: int = 10):
        """
        Điều tra đệ quy các địa chỉ liên quan
        
        Parameters:
        - initial_addresses: Danh sách địa chỉ ban đầu
        - max_depth: Độ sâu tối đa của điều tra
        - stop_conditions: Điều kiện dừng
        """
        
        self.investigation_depth = 0
        self.investigation_path = []
        self.related_addresses = set()
        
        for address in initial_addresses:
            self.investigate_address_recursive(address, depth=0, max_depth=max_depth)
    
    def investigate_address_recursive(self, address: str, depth: int, max_depth: int):
        """Điều tra đệ quy một địa chỉ"""
        
        if depth >= max_depth:
            return
        
        if address in self.investigated_addresses:
            return
        
        # Đánh dấu đã điều tra
        self.investigated_addresses.add(address)
        self.investigation_path.append(address)
        
        # Fetch transactions
        transactions = self.fetch_transactions(address)
        
        # Phân tích clustering
        clusters = self.analyze_clustering(transactions)
        
        # Phát hiện CoinJoin
        coinjoin_txs = self.detect_coinjoin(transactions, clusters)
        
        if coinjoin_txs:
            # Lưu trữ transaction liên quan
            self.store_related_transactions(coinjoin_txs)
            
            # Tìm địa chỉ liên quan để điều tra tiếp
            related_addresses = self.extract_related_addresses(coinjoin_txs, clusters)
            
            # Điều tra đệ quy các địa chỉ liên quan
            for related_addr in related_addresses:
                if related_addr not in self.investigated_addresses:
                    self.investigate_address_recursive(related_addr, depth + 1, max_depth)
        
        # Kiểm tra điều kiện dừng
        if self.should_stop_investigation():
            return
    
    def should_stop_investigation(self) -> bool:
        """
        Kiểm tra điều kiện dừng điều tra
        
        Điều kiện dừng:
        1. Đã điều tra 10 transaction liên tiếp không phát hiện CoinJoin
        2. Output addresses không được cluster vào các transaction ban đầu
        3. Đã đạt độ sâu tối đa
        4. Không còn địa chỉ nào để điều tra
        """
        
        # Kiểm tra 10 transaction liên tiếp không CoinJoin
        recent_txs = self.get_recent_transactions(10)
        coinjoin_count = sum(1 for tx in recent_txs if tx.get('is_coinjoin', False))
        
        if coinjoin_count == 0 and len(recent_txs) >= 10:
            return True
        
        # Kiểm tra output clustering
        if not self.has_cluster_connections():
            return True
        
        return False
```

## 💾 Lưu Trữ Dữ Liệu

### 1. **Transaction Storage**

```python
class TransactionStorage:
    def store_coinjoin_transactions(self, transactions: List[Dict]):
        """Chỉ lưu trữ các transaction liên quan đến CoinJoin"""
        
        for tx in transactions:
            if tx.get('is_coinjoin', False):
                # Lưu vào database
                self.save_transaction(tx)
                
                # Lưu clustering data
                self.save_clustering_data(tx)
                
                # Lưu investigation metadata
                self.save_investigation_metadata(tx)
    
    def save_transaction(self, tx: Dict):
        """Lưu transaction vào database"""
        transaction_data = {
            'hash': tx['hash'],
            'block_height': tx.get('block_height'),
            'time': tx.get('time'),
            'vin_sz': tx.get('vin_sz'),
            'vout_sz': tx.get('vout_sz'),
            'fee': tx.get('fee'),
            'coinjoin_score': tx.get('coinjoin_score', 0),
            'coinjoin_indicators': json.dumps(tx.get('coinjoin_indicators', {})),
            'investigation_depth': tx.get('investigation_depth', 0),
            'investigation_path': json.dumps(tx.get('investigation_path', []))
        }
        
        # Save to database
        pass
    
    def save_clustering_data(self, tx: Dict):
        """Lưu clustering data"""
        clustering_data = {
            'transaction_hash': tx['hash'],
            'input_clusters': json.dumps(tx.get('input_clusters', {})),
            'output_clusters': json.dumps(tx.get('output_clusters', {})),
            'cross_connections': json.dumps(tx.get('cross_connections', []))
        }
        
        # Save to database
        pass
```

## 🚀 Implementation Plan

### **Phase 1: Core Infrastructure (Week 1)**
1. Tạo cấu trúc thư mục và models
2. Implement API interfaces
3. Tạo clustering algorithms
4. Implement basic CoinJoin detection

### **Phase 2: Investigation Engine (Week 2)**
1. Implement recursive investigation logic
2. Tạo transaction fetcher
3. Implement cluster analyzer
4. Tạo investigation pipeline

### **Phase 3: Storage & Optimization (Week 3)**
1. Implement transaction storage
2. Tạo cluster storage
3. Optimize performance
4. Add caching mechanisms

### **Phase 4: Testing & Deployment (Week 4)**
1. Unit testing
2. Integration testing
3. Performance testing
4. Deployment và monitoring

## 📊 Expected Output

### **Investigation Results**
```json
{
    "investigation_summary": {
        "initial_addresses": 10,
        "investigated_addresses": 150,
        "coinjoin_transactions": 25,
        "clusters_found": 8,
        "investigation_depth": 5,
        "total_related_transactions": 45
    },
    "coinjoin_transactions": [
        {
            "hash": "abc123...",
            "coinjoin_score": 6.5,
            "input_clusters": 4,
            "output_clusters": 3,
            "investigation_depth": 2,
            "related_addresses": ["addr1", "addr2", "addr3"]
        }
    ],
    "clusters": [
        {
            "cluster_id": "cluster_1",
            "addresses": ["addr1", "addr2", "addr3"],
            "total_value": 1000000,
            "coinjoin_count": 5
        }
    ]
}
```

## 🎯 Key Features

1. **Intelligent Clustering**: Tự động gom nhóm địa chỉ cùng sở hữu
2. **Recursive Investigation**: Điều tra đệ quy cho đến khi không còn bất thường
3. **Smart Stopping**: Dừng thông minh dựa trên nhiều điều kiện
4. **Efficient Storage**: Chỉ lưu trữ transaction liên quan
5. **API Flexibility**: Hỗ trợ nhiều nguồn API khác nhau
6. **Real-time Analysis**: Phân tích real-time với caching
7. **Comprehensive Reporting**: Báo cáo chi tiết về investigation

## 🔧 Configuration

### **investigation_config.yaml**
```yaml
investigation:
  max_depth: 10
  max_consecutive_non_coinjoin: 10
  min_coinjoin_score: 4.0
  cluster_similarity_threshold: 0.8
  api_rate_limit: 100  # requests per minute
  
clustering:
  union_find_enabled: true
  address_tree_enabled: true
  similarity_threshold: 0.7
  
storage:
  save_only_coinjoin: true
  compress_data: true
  cache_enabled: true
```

Đây là kế hoạch chi tiết để xây dựng hệ thống AI phát hiện CoinJoin theo yêu cầu của bạn. Hệ thống sẽ tự động điều tra, gom nhóm và chỉ lưu trữ các transaction liên quan đến CoinJoin.
