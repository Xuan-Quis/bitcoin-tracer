#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để theo dõi quá trình thu thập dữ liệu CoinJoin từ mempool
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import time

async def monitor_collection():
    """Theo dõi quá trình thu thập dữ liệu"""
    base_url = "http://localhost:8000"
    
    print("🔍 Monitoring CoinJoin Data Collection")
    print("=" * 60)
    print("⏰ Started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                print(f"\n📊 Status Check - {datetime.now().strftime('%H:%M:%S')}")
                print("-" * 40)
                
                # 1. Check monitoring status
                try:
                    async with session.get(f"{base_url}/monitoring/status") as resp:
                        if resp.status == 200:
                            status = await resp.json()
                            print(f"📡 Monitoring: {'🟢 Running' if status.get('is_running') else '🔴 Stopped'}")
                        else:
                            print("📡 Monitoring: ❌ Error")
                except:
                    print("📡 Monitoring: ❌ Connection Error")
                
                # 2. Check statistics
                try:
                    async with session.get(f"{base_url}/statistics") as resp:
                        if resp.status == 200:
                            stats = await resp.json()
                            statistics = stats.get('statistics', {})
                            print(f"📈 CoinJoin Transactions: {statistics.get('total_coinjoin_transactions', 0)}")
                            print(f"📈 CoinJoin Addresses: {statistics.get('total_coinjoin_addresses', 0)}")
                            print(f"📈 Recent (24h): {statistics.get('recent_coinjoin_transactions_24h', 0)}")
                        else:
                            print("📈 Statistics: ❌ Error")
                except:
                    print("📈 Statistics: ❌ Connection Error")
                
                # 3. Check graphs
                try:
                    async with session.get(f"{base_url}/coinjoin/graphs") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            graphs = data.get('graphs', [])
                            print(f"🕸️  Total Graphs: {len(graphs)}")
                            
                            if graphs:
                                # Show latest graph
                                latest = graphs[0]
                                print(f"🕸️  Latest: {latest.get('txid', 'N/A')[:16]}...")
                                print(f"🕸️  Addresses: {latest.get('total_coinjoin_addresses', 0)} coinjoin, {latest.get('total_related_addresses', 0)} related")
                        else:
                            print("🕸️  Graphs: ❌ Error")
                except:
                    print("🕸️  Graphs: ❌ Connection Error")
                
                # 4. Check health
                try:
                    async with session.get(f"{base_url}/health") as resp:
                        if resp.status == 200:
                            health = await resp.json()
                            status = health.get('status', 'unknown')
                            print(f"💚 Health: {'🟢 Healthy' if status == 'healthy' else '🔴 Unhealthy'}")
                        else:
                            print("💚 Health: ❌ Error")
                except:
                    print("💚 Health: ❌ Connection Error")
                
                print("-" * 40)
                
                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                print("\n⏹️  Monitoring stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in monitoring: {e}")
                await asyncio.sleep(5)

async def show_detailed_graphs():
    """Hiển thị chi tiết các đồ thị CoinJoin"""
    base_url = "http://localhost:8000"
    
    print("\n📋 Detailed CoinJoin Graphs")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{base_url}/coinjoin/graphs") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    graphs = data.get('graphs', [])
                    
                    if not graphs:
                        print("ℹ️  No graphs found yet")
                        return
                    
                    print(f"Found {len(graphs)} graphs:")
                    print()
                    
                    for i, graph in enumerate(graphs[:10]):  # Show first 10
                        print(f"Graph {i+1}:")
                        print(f"  TXID: {graph.get('txid', 'N/A')}")
                        print(f"  Timestamp: {graph.get('timestamp', 'N/A')}")
                        print(f"  Depth Reached: {graph.get('depth_reached', 'N/A')}")
                        print(f"  Addresses Processed: {graph.get('addresses_processed', 'N/A')}")
                        print(f"  CoinJoin Found: {graph.get('coinjoin_found', 'N/A')}")
                        print(f"  Normal Found: {graph.get('normal_found', 'N/A')}")
                        print(f"  Total CoinJoin Addresses: {graph.get('total_coinjoin_addresses', 'N/A')}")
                        print(f"  Total Related Addresses: {graph.get('total_related_addresses', 'N/A')}")
                        print()
                        
                        # Show detailed graph if requested
                        if i == 0:  # Show details for first graph
                            txid = graph.get('txid')
                            if txid:
                                print(f"🔍 Getting detailed graph for {txid}...")
                                try:
                                    async with session.get(f"{base_url}/coinjoin/graphs/{txid}") as resp2:
                                        if resp2.status == 200:
                                            graph_data = await resp2.json()
                                            detailed_graph = graph_data.get('graph', {})
                                            
                                            print(f"📊 Detailed Graph Data:")
                                            print(f"  Metadata: {json.dumps(detailed_graph.get('metadata', {}), indent=4)}")
                                            print(f"  Transactions: {len(detailed_graph.get('transactions', []))}")
                                            print(f"  Addresses: {len(detailed_graph.get('addresses', []))}")
                                            print(f"  Relationships: {len(detailed_graph.get('relationships', []))}")
                                            
                                            # Show sample transactions
                                            transactions = detailed_graph.get('transactions', [])
                                            if transactions:
                                                print(f"  Sample Transactions:")
                                                for j, tx in enumerate(transactions[:3]):
                                                    print(f"    {j+1}. {tx.get('txid', 'N/A')[:16]}... - {tx.get('value', 'N/A')} sats")
                                            
                                            # Show sample addresses
                                            addresses = detailed_graph.get('addresses', [])
                                            if addresses:
                                                print(f"  Sample Addresses:")
                                                for j, addr in enumerate(addresses[:3]):
                                                    print(f"    {j+1}. {addr.get('address', 'N/A')[:16]}... - {addr.get('type', 'N/A')}")
                                                    
                                        else:
                                            print(f"❌ Failed to get detailed graph: {resp2.status}")
                                except Exception as e:
                                    print(f"❌ Error getting detailed graph: {e}")
                                
                                print("-" * 40)
                                break
                else:
                    print(f"❌ Failed to get graphs: {resp.status}")
                    
        except Exception as e:
            print(f"❌ Error showing detailed graphs: {e}")

if __name__ == "__main__":
    print("🚀 CoinJoin Collection Monitor")
    print("=" * 60)
    
    # Show detailed graphs first
    asyncio.run(show_detailed_graphs())
    
    # Start monitoring
    print("\n🔄 Starting continuous monitoring...")
    print("Press Ctrl+C to stop")
    asyncio.run(monitor_collection())
