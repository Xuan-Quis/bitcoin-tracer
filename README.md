# AI CoinJoin Investigation System

## 🎯 Tổng Quan

Hệ thống AI tự động điều tra và phát hiện các giao dịch CoinJoin dựa trên dataset địa chỉ ban đầu. Hệ thống sử dụng clustering để gom nhóm địa chỉ và điều tra đệ quy cho đến khi không còn phát hiện bất thường.

## 🚀 Tính Năng Chính

### 1. **Intelligent Clustering**
- Tự động gom nhóm địa chỉ cùng sở hữu
- Phân tích mối quan hệ giữa input/output addresses
- Union-Find algorithm cho clustering hiệu quả

### 2. **Recursive Investigation**
- Điều tra đệ quy các địa chỉ liên quan
- Dừng thông minh dựa trên nhiều điều kiện
- Theo dõi investigation path và depth

### 3. **Multi-Source API Support**
- Blockstream API
- Mempool.space API
- Bitcoin Core RPC
- Fallback tự động giữa các nguồn

### 4. **Advanced CoinJoin Detection**
- Phân tích clustering patterns
- Tính toán CoinJoin score
- Phát hiện change outputs
- Validation và confidence scoring

### 5. **Efficient Storage**
- Chỉ lưu trữ transaction liên quan
- Metadata và statistics
- JSON format cho dễ xử lý

## 📁 Cấu Trúc Thư Mục

```
AI/
├── investigation/
│   ├── coinjoin_investigator.py      # Core investigation engine
│   ├── cluster_analyzer.py           # Clustering analysis
│   ├── coinjoin_detector.py          # CoinJoin detection logic
│   └── investigation_pipeline.py     # Main pipeline orchestrator
├── api/
│   ├── blockchain_api.py             # Generic blockchain API interface
│   ├── blockstream_api.py            # Blockstream API
│   ├── mempool_api.py                # Mempool.space API
│   └── bitcoin_core_api.py           # Bitcoin Core RPC
├── data/
│   ├── transaction_storage.py        # Store related transactions
│   └── cluster_storage.py            # Store cluster data
├── utils/
│   ├── config.py                     # Configuration management
│   ├── logger.py                     # Logging utilities
│   └── validators.py                 # Data validation
├── config/
│   ├── investigation_config.yaml     # Investigation parameters
│   └── api_config.yaml              # API configurations
├── run_investigation.py              # Main execution script
├── requirements.txt                  # Python dependencies
└── README.md                        # This file
```

## 🛠️ Cài Đặt

### 1. **Clone Repository**
```bash
git clone <repository-url>
cd blockchain_truyvet/AI
```

### 2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 3. **Configuration**
Tạo file config hoặc sử dụng default:
```bash
# Sử dụng default config
python run_investigation.py --addresses addr1,addr2,addr3
```

## 🚀 Sử Dụng

### 1. **Basic Usage**
```bash
# Điều tra một số địa chỉ
python run_investigation.py --addresses "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh,bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"

# Sử dụng file chứa địa chỉ
python run_investigation.py --address-file addresses.txt

# Chỉ định API source
python run_investigation.py --addresses addr1,addr2 --api-source mempool
```

### 2. **Advanced Configuration**
```bash
# Sử dụng config file
python run_investigation.py --config config.yaml --addresses addr1,addr2

# Tùy chỉnh parameters
python run_investigation.py \
    --addresses addr1,addr2 \
    --max-depth 15 \
    --min-score 3.5 \
    --output-dir ./my_results
```

### 3. **Command Line Options**
```bash
python run_investigation.py --help
```

**Options:**
- `--addresses`: Comma-separated list of addresses
- `--address-file`: File containing addresses (one per line)
- `--api-source`: API source (blockstream, mempool, bitcoin_core)
- `--config`: Path to configuration file
- `--output-dir`: Output directory for results
- `--max-depth`: Maximum investigation depth
- `--min-score`: Minimum CoinJoin score threshold
- `--save-only-coinjoin`: Save only CoinJoin-related transactions

## 📊 Output Format

### 1. **Investigation Results**
```json
{
    "investigation_summary": {
        "initial_addresses": 10,
        "investigated_addresses": 150,
        "coinjoin_transactions": 25,
        "clusters_found": 8,
        "investigation_depth": 5,
        "total_related_transactions": 45,
        "duration_seconds": 120.5,
        "consecutive_non_coinjoin": 3
    },
    "coinjoin_transactions": [
        {
            "hash": "abc123...",
            "coinjoin_score": 6.5,
            "input_clusters": 4,
            "output_clusters": 3,
            "investigation_depth": 2,
            "related_addresses": ["addr1", "addr2", "addr3"],
            "coinjoin_indicators": {
                "input_diversity": 0.8,
                "output_uniformity": 0.9,
                "cross_connections": 0.2
            }
        }
    ],
    "clusters": [
        {
            "cluster_id": "cluster_1",
            "addresses": ["addr1", "addr2", "addr3"],
            "total_value": 1000000,
            "coinjoin_count": 5,
            "address_count": 3
        }
    ]
}
```

### 2. **File Structure**
```
investigation_results/
├── investigation_results_20231201_143022.json    # Full results
├── investigation_summary_20231201_143022.json    # Summary
└── coinjoin_transactions_20231201_143022.json    # CoinJoin only
```

## ⚙️ Configuration

### 1. **investigation_config.yaml**
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

### 2. **API Configuration**
```yaml
api:
  blockstream_base_url: "https://blockstream.info/api"
  mempool_base_url: "https://mempool.space/api"
  bitcoin_core_rpc_url: "http://localhost:8332"
  rate_limit_delay: 0.1
```

## 🔍 Thuật Toán

### 1. **Investigation Flow**
```
1. Load dataset địa chỉ ban đầu
2. Fetch transactions cho mỗi địa chỉ
3. Phân tích clustering
4. Phát hiện CoinJoin patterns
5. Điều tra đệ quy các địa chỉ liên quan
6. Dừng khi không còn bất thường
```

### 2. **Clustering Algorithm**
- **Union-Find**: Gom nhóm địa chỉ input cùng sở hữu
- **Value-based Clustering**: Gom nhóm output theo giá trị
- **Cross-cluster Analysis**: Tìm mối quan hệ giữa clusters

### 3. **CoinJoin Detection**
- **Input Diversity**: Nhiều clusters input khác nhau
- **Output Uniformity**: Giá trị output đồng đều
- **Cross-connections**: Ít connections giữa clusters
- **Transaction Size**: Kích thước lớn
- **Change Outputs**: Phát hiện change outputs

## 📈 Performance

### 1. **Benchmarks**
- **Processing Speed**: ~1000 addresses/hour
- **Memory Usage**: ~500MB cho 10,000 transactions
- **API Efficiency**: Rate limiting và caching
- **Storage**: Chỉ lưu transaction liên quan

### 2. **Optimization**
- Lazy loading cho large datasets
- Caching cho API calls
- Parallel processing cho clustering
- Memory-efficient data structures

## 🧪 Testing

### 1. **Unit Tests**
```bash
pytest tests/ -v
```

### 2. **Integration Tests**
```bash
pytest tests/integration/ -v
```

### 3. **Performance Tests**
```bash
pytest tests/performance/ -v
```

## 🔧 Development

### 1. **Adding New API Sources**
1. Implement `BlockchainAPI` interface
2. Add to `BlockchainAPIFactory`
3. Update configuration

### 2. **Extending Detection Logic**
1. Add new indicators to `CoinJoinDetector`
2. Update scoring algorithm
3. Add validation tests

### 3. **Custom Clustering**
1. Extend `ClusterAnalyzer`
2. Implement new clustering algorithms
3. Add configuration options

## 📝 Logging

### 1. **Log Levels**
- **INFO**: General progress information
- **DEBUG**: Detailed debugging information
- **WARNING**: Non-critical issues
- **ERROR**: Critical errors

### 2. **Log Format**
```
2023-12-01 14:30:22 - coinjoin_investigator - INFO - Starting investigation for 10 addresses
2023-12-01 14:30:23 - cluster_analyzer - INFO - Found 5 input clusters, 3 output clusters
2023-12-01 14:30:24 - coinjoin_detector - INFO - Detected 3 CoinJoin transactions
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

- **Issues**: Create GitHub issue
- **Documentation**: Check README and docstrings
- **Examples**: See `examples/` directory

---

**Lưu ý**: Hệ thống này được thiết kế để điều tra và phân tích các giao dịch Bitcoin một cách có đạo đức và tuân thủ pháp luật. Chỉ sử dụng cho mục đích nghiên cứu và phân tích hợp pháp.
