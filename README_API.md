# 🚀 CoinJoin Detection API

API phát hiện và điều tra CoinJoin transactions từ mempool real-time với khả năng lưu trữ vào Neo4j.

## 📋 Tính năng

- **Real-time Monitoring**: Giám sát mempool mỗi giây để phát hiện CoinJoin
- **DFS Investigation**: Điều tra sâu với thuật toán DFS để tìm các địa chỉ liên quan
- **Neo4j Storage**: Lưu trữ đồ thị các địa chỉ tham gia CoinJoin
- **REST API**: API đầy đủ để quản lý và truy vấn dữ liệu
- **Fast Detection**: Sử dụng model đã train để phát hiện nhanh

## 🏗️ Kiến trúc

```
api/
├── mempool_monitor.py      # Giám sát mempool real-time
├── coinjoin_investigator.py # Điều tra sâu với DFS
├── neo4j_storage.py        # Lưu trữ vào Neo4j
├── rest_api.py            # REST API endpoints
└── blockchain_api.py      # Interface với blockchain APIs
```

## 🚀 Cài đặt

### 1. Cài đặt dependencies

```bash
pip install -r requirements_api.txt
```

### 2. Cấu hình Neo4j

Đảm bảo Neo4j đang chạy tại `192.168.100.128:7687` hoặc cập nhật config trong `config/api_config.yaml`.

### 3. Khởi động API

```bash
python start_api.py
```

API sẽ chạy tại: http://localhost:8000

## 📚 API Endpoints

### Monitoring

- `POST /monitoring/start` - Bắt đầu giám sát mempool
- `POST /monitoring/stop` - Dừng giám sát mempool  
- `GET /monitoring/status` - Trạng thái monitoring

### Investigation

- `POST /investigate` - Điều tra một transaction cụ thể
- `POST /search/address` - Tìm kiếm theo địa chỉ

### Statistics

- `GET /statistics` - Thống kê CoinJoin
- `GET /health` - Health check

## 🔧 Sử dụng

### 1. Bắt đầu monitoring

```bash
curl -X POST "http://localhost:8000/monitoring/start"
```

### 2. Kiểm tra trạng thái

```bash
curl "http://localhost:8000/monitoring/status"
```

### 3. Điều tra transaction

```bash
curl -X POST "http://localhost:8000/investigate" \
  -H "Content-Type: application/json" \
  -d '{"txid": "your_transaction_id"}'
```

### 4. Tìm kiếm theo địa chỉ

```bash
curl -X POST "http://localhost:8000/search/address" \
  -H "Content-Type: application/json" \
  -d '{"address": "bc1q..."}'
```

## 🗄️ Neo4j Schema

### Nodes

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

### Relationships

- `(Address)-[:INPUT_TO]->(Transaction)`: Địa chỉ input
- `(Transaction)-[:OUTPUT_TO]->(Address)`: Địa chỉ output  
- `(Address)-[:RELATED_TO]->(Transaction)`: Địa chỉ liên quan

## ⚙️ Cấu hình

Chỉnh sửa `config/api_config.yaml`:

```yaml
# Neo4j
neo4j:
  uri: "bolt://192.168.100.128:7687"
  user: "neo4j"
  password: "your_password"

# Investigation
investigation:
  max_depth: 3
  max_transactions_per_address: 5
  consecutive_normal_limit: 10
```

## 📊 Monitoring

### Logs

Logs được lưu tại `logs/api.log`

### Metrics

- Số giao dịch đã xử lý
- Số CoinJoin phát hiện
- Thời gian phản hồi
- Trạng thái Neo4j connection

## 🔍 Ví dụ sử dụng

### 1. Giám sát real-time

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

### 2. Truy vấn Neo4j

```cypher
// Tìm tất cả CoinJoin transactions
MATCH (t:Transaction {is_coinjoin: true})
RETURN t.txid, t.coinjoin_score, t.detection_method
ORDER BY t.coinjoin_score DESC
LIMIT 10

// Tìm địa chỉ liên quan đến CoinJoin
MATCH (a:Address {type: 'coinjoin'})-[:INPUT_TO]->(t:Transaction)
RETURN a.address, count(t) as coinjoin_count
ORDER BY coinjoin_count DESC
LIMIT 20
```

## 🚨 Troubleshooting

### Lỗi kết nối Neo4j

1. Kiểm tra Neo4j đang chạy
2. Kiểm tra IP và port trong config
3. Kiểm tra password trong docker-compose

### Lỗi API rate limit

1. Tăng `rate_limit` trong config
2. Kiểm tra kết nối internet
3. Xem logs để debug

### Performance issues

1. Giảm `max_depth` và `max_transactions_per_address`
2. Tăng `consecutive_normal_limit`
3. Monitor memory usage

## 📈 Performance

- **Latency**: < 100ms cho mỗi transaction
- **Throughput**: 1000+ transactions/giờ
- **Memory**: ~50MB cho monitoring
- **Storage**: Neo4j size tùy theo dữ liệu

## 🔐 Security

- Rate limiting cho API calls
- Input validation với Pydantic
- Error handling không expose sensitive data
- Neo4j authentication
