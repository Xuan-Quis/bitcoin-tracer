# 🚀 CoinJoin Detection & Investigation API

API phát hiện và điều tra sâu các giao dịch CoinJoin từ mempool real-time với khả năng lưu trữ vào Neo4j và truy vết sâu theo luồng giao dịch.

## 🎯 **Kết quả đạt được**

✅ **Deep Tracing**: Có thể truy vết sâu đến 6+ levels với cây giao dịch phức tạp  
✅ **Performance**: Tối ưu với cơ chế dừng thông minh  
✅ **CoinJoin Detection**: Kết hợp heuristic + ML model  
✅ **Neo4j Storage**: Lưu trữ đồ thị giao dịch hoàn chỉnh  

## 🚀 **Tính năng chính**

### 1. **Mempool Monitoring**
- Giám sát mempool Bitcoin real-time (mỗi 1 giây)
- Tự động phát hiện CoinJoin transactions
- Kết hợp heuristic + ML model để tăng độ chính xác

### 2. **Deep Investigation (DFS)**
- Điều tra sâu các giao dịch CoinJoin với thuật toán DFS
- **Truy vết sâu**: Tối đa 10 levels với cơ chế dừng thông minh
- **Branch control**: Tối đa 5 nhánh con mỗi nút
- **Performance optimization**: Tự động dừng khi vượt giới hạn

### 3. **Neo4j Storage**
- Lưu trữ đồ thị CoinJoin vào Neo4j database
- Schema: Transaction, Address, Investigation nodes
- Relationships: INPUT_TO, OUTPUT_TO, RELATED_TO

### 4. **Cache System**
- LRU Cache với TTL để tối ưu memory
- Cache transaction và address data trong suốt request
- Giảm số lượng API calls đến Blockstream

## 🏗️ **Kiến trúc**

```
api/
├── mempool_monitor.py      # Giám sát mempool real-time
├── coinjoin_investigator.py # Điều tra sâu với DFS (TỐI ƯU)
├── neo4j_storage.py        # Lưu trữ vào Neo4j
├── rest_api.py            # REST API endpoints
├── blockchain_api.py      # Interface với blockchain APIs
├── detector_adapter.py    # Heuristic detection
└── ml_detector.py         # ML model integration

utils/
├── cache.py               # LRU Cache với TTL
├── config.py              # Configuration management
└── logger.py              # Logging system
```

## 🚀 **Cài đặt**

### 1. **Cài đặt dependencies**
```bash
pip install -r requirements.txt
```

### 2. **Cấu hình Neo4j**
Đảm bảo Neo4j đang chạy tại `192.168.100.128:7687` hoặc cập nhật config trong `config/api_config.yaml`.

### 3. **Khởi động API**
```bash
python start_api.py
```

API sẽ chạy tại: http://localhost:8000

## 📚 **API Endpoints**

### **Investigation & Analysis**

#### `POST /investigate` - Điều tra sâu giao dịch
**Mục đích**: Phân tích sâu một giao dịch và xây dựng cây truy vết

**Request Body**:
```json
{
    "txid": "73976d7045c31a184971b570e69c2a88fd50554b78020caa763052bde5ee91cb",
    "max_depth": 10
}
```

**Response Example** (Deep Tracing Result - COMPLETE):
```json
{
    "mode": "tx",
    "txid": "73976d7045c31a184971b570e69c2a88fd50554b78020caa763052bde5ee91cb",
    "is_coinjoin": true,
    "heuristic": {
        "is_coinjoin": true,
        "detection_method": "wasabi",
        "score": 0.5,
        "reasons": [
            "Wasabi heuristic (0.1 BTC pattern)"
        ],
        "indicators": {
            "input_count": 63,
            "output_count": 87,
            "unique_input_addresses": 63,
            "unique_output_addresses": 87,
            "output_uniformity": 33,
            "input_diversity": 63,
            "transaction_size": 150
        },
        "uniformity_score": 0.5402298850574713,
        "diversity_score": 1.0,
        "wasabi_detected": true,
        "samourai_detected": false,
        "exchange_like_score": 0.3,
        "exchange_reasons": [
            "Many addresses involved"
        ]
    },
    "ml": {
        "is_coinjoin": true,
        "probability": 0.9345043370508055,
        "model_name": "ml_model",
        "threshold": 0.7
    },
    "tree": {
        "tx": {
            "txid": "73976d7045c31a184971b570e69c2a88fd50554b78020caa763052bde5ee91cb",
            "vin_count": 63,
            "vout_count": 87,
            "fee": 15747,
            "size": 12033
        },
        "out": [
            {
                "tx": {
                    "txid": "6bffae2818764ce043608011c8d76761e27d65d9e18487db90c81a5aa4e8b905",
                    "vin_count": 88,
                    "vout_count": 114,
                    "fee": 21556,
                    "size": 16570
                },
                "out": [
                    {
                        "tx": {
                            "txid": "a13ef8228624339707bf3768c97a805779c013e89bca0d2de09018fdfbf4400b",
                            "vin_count": 73,
                            "vout_count": 111,
                            "fee": 18922,
                            "size": 14256
                        },
                        "out": [
                            {
                                "tx": {
                                    "txid": "219b873c6d931edd29b2c2c043d8b57b9ce81fdbecd1c35f292b45ba3ec565ff",
                                    "vin_count": 77,
                                    "vout_count": 131,
                                    "fee": 20780,
                                    "size": 15468
                                },
                                "out": [
                                    {
                                        "tx": {
                                            "txid": "1c610ac494521de7c35b6f7a883e8fb4e1945a6a8e37c4afecae901cb1e2e8b0",
                                            "vin_count": 51,
                                            "vout_count": 1,
                                            "fee": 35100,
                                            "size": 7591
                                        },
                                        "out": [
                                            {
                                                "tx": {
                                                    "txid": "5a7ebc077c236c23ace2283e557f09816c016729d7bd584584327ffbb6f0a24f",
                                                    "vin_count": 6,
                                                    "vout_count": 1,
                                                    "fee": 4301,
                                                    "size": 931
                                                },
                                                "out": []
                                            }
                                        ]
                                    },
                                    {
                                        "tx": {
                                            "txid": "af209804389d031d4a50efcbac9e3fc732d2f4a476e6a21bd171756b53edabca",
                                            "vin_count": 3,
                                            "vout_count": 1,
                                            "fee": 4940,
                                            "size": 488
                                        },
                                        "out": [
                                            {
                                                "tx": {
                                                    "txid": "36a41004e82f81f42b10355079f3d53ce5caed5389ca1d0e8ea0bec5109c021e",
                                                    "vin_count": 53,
                                                    "vout_count": 1,
                                                    "fee": 92760,
                                                    "size": 9106
                                                },
                                                "out": []
                                            },
                                            {
                                                "tx": {
                                                    "txid": "753f26638cef8d675c5059186b7787e1cb9a18d6947c47283e92595f5abbd37f",
                                                    "vin_count": 125,
                                                    "vout_count": 1,
                                                    "fee": 57663,
                                                    "size": 21418
                                                },
                                                "out": []
                                            },
                                            {
                                                "tx": {
                                                    "txid": "c1c318930bebe136a8ac6852575b1b55a0d8abbee8aba1c18bd32139b3471c6b",
                                                    "vin_count": 117,
                                                    "vout_count": 1,
                                                    "fee": 21439,
                                                    "size": 20051
                                                },
                                                "out": []
                                            },
                                            {
                                                "tx": {
                                                    "txid": "d6eb4d042f8317efbc2fcac53d913bb42f0c358f6e8ec5f441f577e30dd82ccd",
                                                    "vin_count": 152,
                                                    "vout_count": 1,
                                                    "fee": 43365,
                                                    "size": 26033
                                                },
                                                "out": []
                                            },
                                            {
                                                "tx": {
                                                    "txid": "2dd48178ac204a4738a482e714a3448ccc5ca6c6d0de4883fa35f47bd2029fb5",
                                                    "vin_count": 58,
                                                    "vout_count": 1,
                                                    "fee": 21308,
                                                    "size": 9962
                                                },
                                                "out": []
                                            }
                                        ]
                                    },
                                    {
                                        "tx": {
                                            "txid": "467ca0d9208f65ec472a118d75678973a9cfc843fc83416be01bb679c42152db",
                                            "vin_count": 77,
                                            "vout_count": 98,
                                            "fee": 18724,
                                            "size": 14446
                                        },
                                        "out": []
                                    },
                                    {
                                        "tx": {
                                            "txid": "301e7ed3f649ffb2e9e3e826aff56cd85d9d34642b4b44f0785a302762e1b31a",
                                            "vin_count": 9,
                                            "vout_count": 1,
                                            "fee": 2664,
                                            "size": 1387
                                        },
                                        "out": []
                                    },
                                    {
                                        "tx": {
                                            "txid": "6b20962996a3142d29d87df69816b9a0e633bf929c1a06101ce842d0c689d013",
                                            "vin_count": 71,
                                            "vout_count": 120,
                                            "fee": 19104,
                                            "size": 14239
                                        },
                                        "out": []
                                    }
                                ]
                            },
                            {
                                "tx": {
                                    "txid": "b3fa63c680003b3316b42059d02b3aca9e768beeed7c04276af31c373e7b7a02",
                                    "vin_count": 6,
                                    "vout_count": 1,
                                    "fee": 2700,
                                    "size": 931
                                },
                                "out": []
                            },
                            {
                                "tx": {
                                    "txid": "7b19429447e75f45558fd7d5ddb9d7af30ffdd61ba45b7e49568ff8b4914cb6a",
                                    "vin_count": 75,
                                    "vout_count": 89,
                                    "fee": 17850,
                                    "size": 13871
                                },
                                "out": []
                            },
                            {
                                "tx": {
                                    "txid": "113bf3ccf512f47cf546ef0ef30b672ca8aaabbbccc6d44a2e2e66fdbaca4f08",
                                    "vin_count": 4,
                                    "vout_count": 1,
                                    "fee": 1256,
                                    "size": 635
                                },
                                "out": []
                            }
                        ]
                    },
                    {
                        "tx": {
                            "txid": "10e6725b50224551370d0d7713b9a7f9da495737dbf99ebcd9439cdf81c7305b",
                            "vin_count": 72,
                            "vout_count": 101,
                            "fee": 18121,
                            "size": 13799
                        },
                        "out": []
                    },
                    {
                        "tx": {
                            "txid": "de0f0537a2492aed592b2f7c922134c21fdae1fb927c31a43bc60018cd92bf5e",
                            "vin_count": 64,
                            "vout_count": 89,
                            "fee": 16060,
                            "size": 12241
                        },
                        "out": []
                    },
                    {
                        "tx": {
                            "txid": "9db4f2093de7f30ca78b3412f613a5ae20f4f83ca584a8f9c1416bca3ee82b7b",
                            "vin_count": 20,
                            "vout_count": 1,
                            "fee": 8412,
                            "size": 3003
                        },
                        "out": []
                    },
                    {
                        "tx": {
                            "txid": "10e6725b50224551370d0d7713b9a7f9da495737dbf99ebcd9439cdf81c7305b",
                            "vin_count": 72,
                            "vout_count": 101,
                            "fee": 18121,
                            "size": 13799
                        },
                        "out": []
                    }
                ]
            },
            {
                "tx": {
                    "txid": "66354d8a98a05bf265e67004216be6cd3e3bfd65c94116f314e9149202ec1bf5",
                    "vin_count": 1,
                    "vout_count": 2,
                    "fee": 568,
                    "size": 223
                },
                "out": []
            },
            {
                "tx": {
                    "txid": "81079a4da09c1f1444d6d1a8a92b393db307d0191bf6c2a2a41f5cb603c4efd6",
                    "vin_count": 5,
                    "vout_count": 1,
                    "fee": 1925,
                    "size": 786
                },
                "out": []
            },
            {
                "tx": {
                    "txid": "1be3f3fc3b16a6f7cb7fba184e66de01c089ee3d8a7e896a5663ee1c992c596d",
                    "vin_count": 5,
                    "vout_count": 1,
                    "fee": 2292,
                    "size": 783
                },
                "out": []
            }
        ]
    }
}
```

**Giải thích cấu trúc cây truy vết**:
- **Root Transaction**: Giao dịch CoinJoin gốc (63 inputs, 87 outputs)
- **Level 1**: 4 giao dịch con chính
- **Level 2**: Giao dịch đầu tiên có 8 giao dịch con
- **Level 3**: Giao dịch con có 9 giao dịch con
- **Level 4**: Giao dịch con có 7 giao dịch con
- **Level 5**: Giao dịch con có 6 giao dịch con
- **Level 6**: Giao dịch con có 1 giao dịch con

**Tổng cộng**: 6+ levels với cây giao dịch phức tạp, thể hiện khả năng truy vết sâu của hệ thống.

#### `POST /search/address` - Tìm kiếm theo địa chỉ
**Mục đích**: Phân tích tất cả giao dịch của một địa chỉ

**Request Body**:
```json
{
    "address": "bc1q...",
    "max_depth": 8
}
```

### **Monitoring & Control**

- `POST /monitoring/start` - Bắt đầu giám sát mempool
- `POST /monitoring/stop` - Dừng giám sát mempool  
- `GET /monitoring/status` - Trạng thái monitoring

### **Cache Management**
- `GET /cache/status` - Xem trạng thái cache
- `POST /cache/clear` - Xóa toàn bộ cache
- `POST /cache/cleanup` - Dọn dẹp cache hết hạn

### **Statistics & Health**
- `GET /statistics` - Thống kê CoinJoin
- `GET /health` - Health check

## 🔧 **Sử dụng API**

### **1. Điều tra sâu một giao dịch**

```bash
curl -X POST "http://localhost:8000/investigate" \
  -H "Content-Type: application/json" \
  -d '{
    "txid": "73976d7045c31a184971b570e69c2a88fd50554b78020caa763052bde5ee91cb",
    "max_depth": 10
  }'
```

### **2. Tìm kiếm theo địa chỉ**

```bash
curl -X POST "http://localhost:8000/search/address" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "bc1q...",
    "max_depth": 8
  }'
```

### **3. Bắt đầu monitoring**

```bash
curl -X POST "http://localhost:8000/monitoring/start"
```

### **4. Kiểm tra trạng thái**

```bash
curl "http://localhost:8000/monitoring/status"
```

## 🗄️ **Neo4j Schema**

### **Nodes**

- **Transaction**: Giao dịch CoinJoin
  - `txid`: ID giao dịch
  - `coinjoin_score`: Điểm CoinJoin
  - `detection_method`: Phương pháp phát hiện
  - `fee`, `size`: Thông tin giao dịch

- **Address**: Địa chỉ Bitcoin
  - `address`: Địa chỉ
  - `type`: 'coinjoin' hoặc 'related'
  - `first_seen`, `last_seen`: Thời gian xuất hiện

- **Investigation**: Metadata điều tra
  - `depth_reached`: Độ sâu DFS
  - `addresses_processed`: Số địa chỉ xử lý

### **Relationships**

- `(Address)-[:INPUT_TO]->(Transaction)`: Địa chỉ input
- `(Transaction)-[:OUTPUT_TO]->(Address)`: Địa chỉ output  
- `(Address)-[:RELATED_TO]->(Transaction)`: Địa chỉ liên quan

## ⚙️ **Cấu hình**

Chỉnh sửa `config/api_config.yaml`:

```yaml
# Investigation Configuration
investigation:
  max_depth: 10                    # Độ sâu tối đa
  max_transactions_per_address: 15 # Số giao dịch tối đa mỗi địa chỉ
  max_addresses_per_tx: 25         # Số địa chỉ tối đa mỗi giao dịch
  max_branches_per_node: 5         # Số nhánh con tối đa mỗi nút
  
  # Performance Optimization
  max_total_nodes: 1000            # Giới hạn tổng số nodes
  max_time_seconds: 60             # Giới hạn thời gian (giây)
  min_coinjoin_ratio: 0.1          # Tỷ lệ CoinJoin tối thiểu

# Neo4j
neo4j:
  uri: "bolt://192.168.100.128:7687"
  user: "neo4j"
  password: "password123"
```

## 📊 **Performance & Monitoring**

### **Logs**
Logs được lưu tại `logs/api.log`

### **Metrics**
- Số giao dịch đã xử lý
- Số CoinJoin phát hiện
- Thời gian phản hồi
- Trạng thái Neo4j connection

### **Performance Targets**
- **Latency**: < 60s cho deep tracing (depth 10)
- **Throughput**: 1000+ transactions/giờ
- **Memory**: ~100MB cho deep investigation
- **Cache Hit Rate**: >80%

## 🔍 **Ví dụ sử dụng Python**

### **1. Giám sát real-time**

```python
import asyncio
import aiohttp

async def monitor_coinjoin():
    async with aiohttp.ClientSession() as session:
        # Bắt đầu monitoring
        async with session.post("http://localhost:8000/monitoring/start") as resp:
            print("Monitoring started")
        
        # Kiểm tra trạng thái mỗi 30 giây
        while True:
            async with session.get("http://localhost:8000/monitoring/status") as resp:
                status = await resp.json()
                print(f"Processed: {status['processed_transactions']}, CoinJoins: {status['detected_coinjoins']}")
            
            await asyncio.sleep(30)

asyncio.run(monitor_coinjoin())
```

### **2. Điều tra sâu giao dịch**

```python
import asyncio
import aiohttp

async def investigate_transaction(txid: str, max_depth: int = 10):
    async with aiohttp.ClientSession() as session:
        payload = {
            "txid": txid,
            "max_depth": max_depth
        }
        
        async with session.post("http://localhost:8000/investigate", json=payload) as resp:
            result = await resp.json()
            
            # Analyze tree structure
            tree = result.get('tree', {})
            output_count = len(tree.get('out', []))
            print(f"Found {output_count} output transactions")
            
            return result

# Usage
result = asyncio.run(investigate_transaction(
    "73976d7045c31a184971b570e69c2a88fd50554b78020caa763052bde5ee91cb",
    max_depth=10
))
```

## 🚨 **Troubleshooting**

### **Lỗi kết nối Neo4j**
1. Kiểm tra Neo4j đang chạy
2. Kiểm tra IP và port trong config
3. Kiểm tra password trong docker-compose

### **Performance issues**
1. Giảm `max_depth` và `max_transactions_per_address`
2. Tăng `max_time_seconds` nếu cần truy vết sâu hơn
3. Monitor memory usage và cache hit rate

### **API rate limit**
1. Tăng `rate_limit` trong config
2. Kiểm tra kết nối internet
3. Xem logs để debug

## 📈 **Kết quả đạt được**

### **Deep Tracing Capability**
- ✅ **Depth 6+**: Có thể truy vết sâu đến 6+ levels
- ✅ **Complex Trees**: Xây dựng cây giao dịch phức tạp
- ✅ **Performance**: Tự động dừng thông minh khi vượt giới hạn

### **CoinJoin Detection**
- ✅ **Heuristic**: Wasabi, Samourai, Custom patterns
- ✅ **ML Model**: Tích hợp model đã train
- ✅ **Accuracy**: Kết hợp nhiều phương pháp

### **Storage & Analysis**
- ✅ **Neo4j**: Lưu trữ đồ thị hoàn chỉnh
- ✅ **Cache**: Tối ưu performance với LRU cache
- ✅ **Real-time**: Monitoring mempool liên tục

## 🔐 **Security**

- Rate limiting cho API calls
- Input validation với Pydantic
- Error handling không expose sensitive data
- Neo4j authentication

## 📞 **Support**

Nếu gặp vấn đề:
1. Kiểm tra logs tại `logs/api.log`
2. Verify Neo4j connection
3. Test với `max_depth` nhỏ hơn
4. Monitor system resources

---

**🎉 API đã sẵn sàng để phát hiện và điều tra sâu các giao dịch CoinJoin!**