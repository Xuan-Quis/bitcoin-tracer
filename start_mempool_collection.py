#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để bắt đầu thu thập dữ liệu CoinJoin từ mempool
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import sys
import os

# Thêm current directory vào Python path
sys.path.insert(0, os.getcwd())

from utils.config import Config
from api.mempool_monitor import MempoolMonitor
from api.neo4j_storage import Neo4jStorage

async def start_mempool_collection():
    """Bắt đầu thu thập dữ liệu từ mempool"""
    print("🚀 Bắt đầu thu thập dữ liệu CoinJoin từ mempool...")
    print("=" * 60)
    
    # Load config
    config = Config()
    
    # Khởi tạo Neo4j storage
    neo4j_storage = Neo4jStorage(config)
    try:
        await neo4j_storage.connect()
        print("✅ Kết nối Neo4j thành công")
    except Exception as e:
        print(f"❌ Lỗi kết nối Neo4j: {e}")
        print("⚠️  API sẽ vẫn chạy nhưng không thể lưu trữ dữ liệu")
    
    # Khởi tạo mempool monitor
    mempool_monitor = MempoolMonitor(config)
    
    try:
        print("📡 Bắt đầu giám sát mempool...")
        print("⏱️  Tần suất: 1 giây/lần")
        print("🎯 Mục tiêu: Phát hiện và điều tra CoinJoin transactions")
        print("💾 Lưu trữ: Neo4j database")
        print("-" * 60)
        
        # Bắt đầu monitoring
        await mempool_monitor.start_monitoring()
        
    except KeyboardInterrupt:
        print("\n⏹️  Dừng thu thập dữ liệu...")
    except Exception as e:
        print(f"❌ Lỗi trong quá trình thu thập: {e}")
    finally:
        # Dọn dẹp
        await mempool_monitor.close()
        await neo4j_storage.close()
        print("✅ Đã dừng thu thập dữ liệu")

async def check_collection_status():
    """Kiểm tra trạng thái thu thập dữ liệu"""
    print("📊 Kiểm tra trạng thái thu thập dữ liệu...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Kiểm tra API status
            async with session.get("http://localhost:8000/monitoring/status") as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"📡 Trạng thái monitoring: {status}")
                else:
                    print("❌ Không thể kết nối API")
            
            # Kiểm tra thống kê
            async with session.get("http://localhost:8000/statistics") as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    print(f"📈 Thống kê: {json.dumps(stats, indent=2)}")
                else:
                    print("❌ Không thể lấy thống kê")
            
            # Kiểm tra đồ thị CoinJoin
            async with session.get("http://localhost:8000/coinjoin/graphs") as resp:
                if resp.status == 200:
                    graphs = await resp.json()
                    print(f"🕸️  Số lượng đồ thị CoinJoin: {len(graphs.get('graphs', []))}")
                else:
                    print("❌ Không thể lấy đồ thị CoinJoin")
                    
    except Exception as e:
        print(f"❌ Lỗi kiểm tra trạng thái: {e}")

if __name__ == "__main__":
    print("🔍 CoinJoin Mempool Data Collection")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        # Chỉ kiểm tra trạng thái
        asyncio.run(check_collection_status())
    else:
        # Bắt đầu thu thập dữ liệu
        print("💡 Sử dụng: python start_mempool_collection.py status")
        print("   để kiểm tra trạng thái thu thập dữ liệu")
        print()
        asyncio.run(start_mempool_collection())
