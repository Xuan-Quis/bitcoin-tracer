"""
LRU Cache Utility cho CoinJoin Detection System
Tối ưu memory usage và performance
"""

from typing import Any, Dict, Optional
from collections import OrderedDict
import time
import logging

logger = logging.getLogger(__name__)

class LRUCache:
    """
    LRU Cache với TTL (Time To Live) để quản lý memory hiệu quả
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        
    def get(self, key: str) -> Optional[Any]:
        """Lấy value từ cache, trả về None nếu không có hoặc đã hết hạn"""
        if key not in self.cache:
            return None
            
        value, timestamp = self.cache[key]
        current_time = time.time()
        
        # Kiểm tra TTL
        if current_time - timestamp > self.ttl_seconds:
            del self.cache[key]
            return None
            
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return value
        
    def set(self, key: str, value: Any) -> None:
        """Đặt value vào cache"""
        current_time = time.time()
        
        # Nếu key đã tồn tại, xóa trước
        if key in self.cache:
            del self.cache[key]
            
        # Nếu cache đầy, xóa item cũ nhất
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.debug(f"Cache full, removed oldest key: {oldest_key[:10]}...")
            
        # Thêm item mới
        self.cache[key] = (value, current_time)
        
    def has(self, key: str) -> bool:
        """Kiểm tra key có trong cache không (và còn hạn)"""
        return self.get(key) is not None
        
    def clear(self) -> None:
        """Xóa toàn bộ cache"""
        self.cache.clear()
        
    def size(self) -> int:
        """Trả về số lượng items trong cache"""
        return len(self.cache)
        
    def cleanup_expired(self) -> int:
        """Dọn dẹp các items hết hạn, trả về số lượng đã xóa"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]
            
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache items")
            
        return len(expired_keys)

class TransactionCache:
    """
    Cache chuyên dụng cho transaction data
    """
    
    def __init__(self, max_size: int = 500, ttl_seconds: int = 600):
        self.cache = LRUCache(max_size, ttl_seconds)
        
    def get_transaction(self, txid: str) -> Optional[Dict]:
        """Lấy transaction từ cache"""
        return self.cache.get(f"tx:{txid}")
        
    def set_transaction(self, txid: str, tx_data: Dict) -> None:
        """Lưu transaction vào cache"""
        self.cache.set(f"tx:{txid}", tx_data)
        
    def get_address_transactions(self, address: str) -> Optional[list]:
        """Lấy danh sách transactions của address từ cache"""
        return self.cache.get(f"addr:{address}")
        
    def set_address_transactions(self, address: str, txs: list) -> None:
        """Lưu danh sách transactions của address vào cache"""
        self.cache.set(f"addr:{address}", txs)
        
    def clear(self) -> None:
        """Xóa toàn bộ cache"""
        self.cache.clear()
        
    def cleanup(self) -> int:
        """Dọn dẹp cache hết hạn"""
        return self.cache.cleanup_expired()

# Global cache instance để sử dụng chung
transaction_cache = TransactionCache()
