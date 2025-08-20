#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Optimization Performance
Kiểm tra hiệu suất sau khi tối ưu
"""

import asyncio
import aiohttp
import time
import json
from typing import Dict, Any

async def test_investigation_performance(txid: str, max_depth: int = 8) -> Dict[str, Any]:
    """Test performance của endpoint /investigate với các tham số tối ưu"""
    
    url = "http://localhost:8000/investigate"
    payload = {
        "txid": txid,
        "max_depth": max_depth
    }
    
    print(f"🔍 Testing investigation for tx: {txid[:10]}...")
    print(f"   Max depth: {max_depth}")
    
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    print(f"✅ Success in {duration:.2f}s")
                    
                    # Analyze tree structure
                    tree = result.get('tree', {})
                    tree_stats = analyze_tree_structure(tree)
                    
                    return {
                        "success": True,
                        "duration": duration,
                        "tree_stats": tree_stats,
                        "result": result
                    }
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}"
                    }
                    
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ Exception after {duration:.2f}s: {e}")
        return {
            "success": False,
            "error": str(e),
            "duration": duration
        }

def analyze_tree_structure(tree: Dict[str, Any]) -> Dict[str, Any]:
    """Phân tích cấu trúc cây để đánh giá hiệu suất"""
    
    def count_nodes(node: Dict[str, Any], depth: int = 0) -> Dict[str, int]:
        """Đếm số lượng nodes và depth của cây"""
        if not node or 'tx' not in node:
            return {"nodes": 0, "max_depth": depth, "branches": 0}
        
        current_nodes = 1
        max_depth = depth
        total_branches = 0
        
        children = node.get('out', [])
        total_branches += len(children)
        
        for child in children:
            child_stats = count_nodes(child, depth + 1)
            current_nodes += child_stats["nodes"]
            max_depth = max(max_depth, child_stats["max_depth"])
            total_branches += child_stats["branches"]
        
        return {
            "nodes": current_nodes,
            "max_depth": max_depth,
            "branches": total_branches
        }
    
    stats = count_nodes(tree)
    
    print(f"   📊 Tree Analysis:")
    print(f"      - Total nodes: {stats['nodes']}")
    print(f"      - Max depth: {stats['max_depth']}")
    print(f"      - Total branches: {stats['branches']}")
    
    return stats

async def test_cache_management():
    """Test các endpoint quản lý cache"""
    
    base_url = "http://localhost:8000"
    
    print("\n🧠 Testing Cache Management...")
    
    # Test cache status
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/cache/status") as response:
                if response.status == 200:
                    status = await response.json()
                    print(f"✅ Cache Status: {status['cache_size']} items")
                else:
                    print(f"❌ Cache status failed: {response.status}")
    except Exception as e:
        print(f"❌ Cache status error: {e}")
    
    # Test cache cleanup
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{base_url}/cache/cleanup") as response:
                if response.status == 200:
                    cleanup = await response.json()
                    print(f"✅ Cache Cleanup: {cleanup['cleaned_count']} items")
                else:
                    print(f"❌ Cache cleanup failed: {response.status}")
    except Exception as e:
        print(f"❌ Cache cleanup error: {e}")

async def test_multiple_transactions():
    """Test nhiều transactions để đánh giá performance tổng thể"""
    
    # Test transactions với độ phức tạp khác nhau
    test_cases = [
        {"txid": "83e4d97eb3fc1557462581827d834ea98d19ae09514c37b8f042a931a20da458", "depth": 6},
        {"txid": "83e4d97eb3fc1557462581827d834ea98d19ae09514c37b8f042a931a20da458", "depth": 8},
    ]
    
    print("\n🚀 Testing Multiple Transactions...")
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        result = await test_investigation_performance(
            test_case["txid"], 
            test_case["depth"]
        )
        results.append({
            "test_case": i,
            "depth": test_case["depth"],
            "result": result
        })
        
        # Wait between tests
        await asyncio.sleep(1)
    
    # Summary
    print("\n📈 Performance Summary:")
    successful_tests = [r for r in results if r["result"]["success"]]
    if successful_tests:
        avg_duration = sum(r["result"]["duration"] for r in successful_tests) / len(successful_tests)
        print(f"   - Successful tests: {len(successful_tests)}/{len(results)}")
        print(f"   - Average duration: {avg_duration:.2f}s")
        
        # Compare with previous performance
        if avg_duration < 30:  # Assuming previous performance was >30s
            print(f"   - 🎉 Performance improved! (was >30s, now {avg_duration:.2f}s)")
        else:
            print(f"   - ⚠️ Performance still needs improvement ({avg_duration:.2f}s)")
    else:
        print("   - ❌ No successful tests")

async def main():
    """Main test function"""
    
    print("🧪 COINJOIN INVESTIGATION OPTIMIZATION TEST")
    print("=" * 60)
    
    # Test 1: Single transaction investigation
    print("\n1️⃣ Single Transaction Test")
    result = await test_investigation_performance(
        "83e4d97eb3fc1557462581827d834ea98d19ae09514c37b8f042a931a20da458"
    )
    
    # Test 2: Cache management
    await test_cache_management()
    
    # Test 3: Multiple transactions
    await test_multiple_transactions()
    
    print("\n" + "=" * 60)
    print("✅ Optimization test completed!")

if __name__ == "__main__":
    asyncio.run(main())
