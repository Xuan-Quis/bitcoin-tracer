#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Deep Tracing Performance
Kiểm tra khả năng truy vết sâu sau khi điều chỉnh tối ưu
"""

import asyncio
import aiohttp
import time
import json
from typing import Dict, Any

async def test_deep_tracing(txid: str, max_depth: int = 10) -> Dict[str, Any]:
    """Test khả năng truy vết sâu với các tham số đã điều chỉnh"""
    
    url = "http://localhost:8000/investigate"
    payload = {
        "txid": txid,
        "max_depth": max_depth
    }
    
    print(f"🔍 Testing DEEP tracing for tx: {txid[:10]}...")
    print(f"   Max depth: {max_depth}")
    print(f"   Expected: More output transactions and deeper tree")
    
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
                    tree_stats = analyze_deep_tree_structure(tree)
                    
                    # Check if we got more output transactions
                    output_count = len(tree.get('out', []))
                    print(f"   📊 Output transactions found: {output_count}")
                    
                    if output_count > 2:
                        print(f"   🎉 SUCCESS: Found {output_count} output transactions (was only 2 before)")
                    else:
                        print(f"   ⚠️ Still limited: Only {output_count} output transactions")
                    
                    return {
                        "success": True,
                        "duration": duration,
                        "tree_stats": tree_stats,
                        "output_count": output_count,
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

def analyze_deep_tree_structure(tree: Dict[str, Any]) -> Dict[str, Any]:
    """Phân tích cấu trúc cây sâu để đánh giá khả năng truy vết"""
    
    def count_nodes_recursive(node: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """Đếm nodes và phân tích cấu trúc cây chi tiết"""
        if not node or 'tx' not in node:
            return {
                "nodes": 0, 
                "max_depth": depth, 
                "branches": 0,
                "depth_distribution": {},
                "branch_sizes": []
            }
        
        current_nodes = 1
        max_depth = depth
        total_branches = 0
        depth_distribution = {depth: 1}
        branch_sizes = []
        
        children = node.get('out', [])
        total_branches += len(children)
        branch_sizes.append(len(children))
        
        # Update depth distribution
        if depth not in depth_distribution:
            depth_distribution[depth] = 0
        depth_distribution[depth] += 1
        
        for child in children:
            child_stats = count_nodes_recursive(child, depth + 1)
            current_nodes += child_stats["nodes"]
            max_depth = max(max_depth, child_stats["max_depth"])
            total_branches += child_stats["branches"]
            
            # Merge depth distribution
            for d, count in child_stats["depth_distribution"].items():
                depth_distribution[d] = depth_distribution.get(d, 0) + count
            
            # Merge branch sizes
            branch_sizes.extend(child_stats["branch_sizes"])
        
        return {
            "nodes": current_nodes,
            "max_depth": max_depth,
            "branches": total_branches,
            "depth_distribution": depth_distribution,
            "branch_sizes": branch_sizes
        }
    
    stats = count_nodes_recursive(tree)
    
    print(f"   📊 Deep Tree Analysis:")
    print(f"      - Total nodes: {stats['nodes']}")
    print(f"      - Max depth: {stats['max_depth']}")
    print(f"      - Total branches: {stats['branches']}")
    
    # Analyze depth distribution
    depth_dist = stats['depth_distribution']
    if depth_dist:
        print(f"      - Depth distribution:")
        for depth in sorted(depth_dist.keys()):
            print(f"        Depth {depth}: {depth_dist[depth]} nodes")
    
    # Analyze branch sizes
    branch_sizes = stats['branch_sizes']
    if branch_sizes:
        avg_branch_size = sum(branch_sizes) / len(branch_sizes)
        max_branch_size = max(branch_sizes)
        print(f"      - Branch analysis:")
        print(f"        Average branch size: {avg_branch_size:.1f}")
        print(f"        Max branch size: {max_branch_size}")
    
    return stats

async def test_multiple_depths():
    """Test với các độ sâu khác nhau để so sánh"""
    
    txid = "2354f07d27616ad7333dc0e50505d615bdcd18d5ee62a5e91633b4e4369a4d87"
    
    print("\n🚀 Testing Multiple Depths...")
    
    test_depths = [6, 8, 10]
    results = []
    
    for depth in test_depths:
        print(f"\n--- Testing Depth {depth} ---")
        result = await test_deep_tracing(txid, depth)
        results.append({
            "depth": depth,
            "result": result
        })
        
        # Wait between tests
        await asyncio.sleep(2)
    
    # Summary
    print("\n📈 Depth Comparison Summary:")
    successful_tests = [r for r in results if r["result"]["success"]]
    if successful_tests:
        for test in successful_tests:
            depth = test["depth"]
            output_count = test["result"].get("output_count", 0)
            duration = test["result"].get("duration", 0)
            print(f"   - Depth {depth}: {output_count} outputs in {duration:.2f}s")
        
        # Find best depth
        best_test = max(successful_tests, key=lambda x: x["result"].get("output_count", 0))
        best_depth = best_test["depth"]
        best_outputs = best_test["result"].get("output_count", 0)
        print(f"\n   🏆 Best depth: {best_depth} with {best_outputs} outputs")
    else:
        print("   - ❌ No successful tests")

async def main():
    """Main test function"""
    
    print("🧪 COINJOIN DEEP TRACING TEST")
    print("=" * 60)
    print("🎯 Goal: Test if we can now trace deeper and find more output transactions")
    print("📊 Previous result: Only 2 output transactions")
    print("🚀 Expected: More outputs and deeper tree structure")
    
    # Test 1: Deep tracing with max depth
    print("\n1️⃣ Deep Tracing Test (Depth 10)")
    result = await test_deep_tracing(
        "2354f07d27616ad7333dc0e50505d615bdcd18d5ee62a5e91633b4e4369a4d87",
        max_depth=10
    )
    
    # Test 2: Multiple depths comparison
    await test_multiple_depths()
    
    print("\n" + "=" * 60)
    if result.get("success") and result.get("output_count", 0) > 2:
        print("✅ SUCCESS: Deep tracing is working! Found more output transactions.")
    else:
        print("⚠️ Still needs improvement: Limited output transactions found.")
    print("✅ Deep tracing test completed!")

if __name__ == "__main__":
    asyncio.run(main())
