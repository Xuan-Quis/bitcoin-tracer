#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để test detect và sinh đồ thị CoinJoin cho transaction cụ thể
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime

# Thêm current directory vào Python path
sys.path.insert(0, os.getcwd())

from utils.config import Config
from api.coinjoin_investigator import CoinJoinInvestigator
from api.neo4j_storage import Neo4jStorage

async def test_coinjoin_detection():
    """Test detect và sinh đồ thị cho transaction cụ thể"""
    print("🧪 Test CoinJoin Detection và Graph Generation")
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
        print("⚠️  Sẽ test mà không lưu vào Neo4j")
        neo4j_storage = None
    
    # Khởi tạo investigator
    investigator = CoinJoinInvestigator(config)
    
    # Test với transaction từ dataset
    test_txid = "83e4d97eb3fc1557462581827d834ea98d19ae09514c37b8f042a931a20da458"
    
    print(f"🔍 Testing với transaction: {test_txid}")
    print("-" * 40)
    
    try:
        # Fetch transaction details từ Blockstream
        print("📡 Fetching transaction details...")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://blockstream.info/api/tx/{test_txid}") as response:
                if response.status == 200:
                    tx_data = await response.json()
                    print(f"✅ Fetched transaction: {len(tx_data.get('vin', []))} inputs, {len(tx_data.get('vout', []))} outputs")
                else:
                    print(f"❌ Failed to fetch transaction: {response.status}")
                    return
        
        # Analyze for CoinJoin
        print("🔍 Analyzing for CoinJoin...")
        coinjoin_analysis = await investigator.analyze_transaction_coinjoin(tx_data)
        
        if coinjoin_analysis and coinjoin_analysis.get('is_coinjoin', False):
            print(f"🚨 CoinJoin detected! Score: {coinjoin_analysis.get('coinjoin_score', 0)}")
            print(f"📊 Indicators: {coinjoin_analysis.get('coinjoin_indicators', {})}")
            
            # Start investigation
            print("🔍 Starting DFS investigation...")
            await investigator.investigate_coinjoin(test_txid, tx_data, coinjoin_analysis)
            
            print("✅ Investigation completed!")
            
            # Check if graph was created
            if neo4j_storage:
                print("📊 Checking stored graph...")
                try:
                    graphs = await neo4j_storage.get_all_coinjoin_graphs()
                    if graphs:
                        latest_graph = graphs[0]
                        print(f"🕸️  Graph created: {latest_graph.get('txid', 'N/A')}")
                        print(f"📈 Addresses: {latest_graph.get('total_coinjoin_addresses', 0)} coinjoin, {latest_graph.get('total_related_addresses', 0)} related")
                        print(f"🔍 Depth: {latest_graph.get('depth_reached', 'N/A')}")
                    else:
                        print("ℹ️  No graphs found in database")
                except Exception as e:
                    print(f"❌ Error checking graphs: {e}")
            
        else:
            print("ℹ️  Transaction is not CoinJoin")
            print(f"📊 Analysis result: {coinjoin_analysis}")
            
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()

async def test_multiple_transactions():
    """Test với nhiều transactions từ dataset"""
    print("\n🧪 Test Multiple Transactions from Dataset")
    print("=" * 60)
    
    # Load config
    config = Config()
    
    # Khởi tạo investigator
    investigator = CoinJoinInvestigator(config)
    
    # Test transactions từ dataset
    test_transactions = [
        "83e4d97eb3fc1557462581827d834ea98d19ae09514c37b8f042a931a20da458",
        "724f2b81834c7fa60918f4f55d4f4bce235fc03bb50d7fef2ce495b06d3bf634",
        "dd499f5dc50a9baf940e8e10ad0d29402e9e849210815018a3e7979ea454ffe5"
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for i, txid in enumerate(test_transactions, 1):
            print(f"\n🔍 Testing transaction {i}/{len(test_transactions)}: {txid}")
            print("-" * 40)
            
            try:
                # Fetch transaction details
                async with session.get(f"https://blockstream.info/api/tx/{txid}") as response:
                    if response.status == 200:
                        tx_data = await response.json()
                        
                        # Analyze for CoinJoin
                        coinjoin_analysis = await investigator.analyze_transaction_coinjoin(tx_data)
                        
                        result = {
                            'txid': txid,
                            'is_coinjoin': coinjoin_analysis.get('is_coinjoin', False),
                            'score': coinjoin_analysis.get('coinjoin_score', 0),
                            'indicators': coinjoin_analysis.get('coinjoin_indicators', {}),
                            'inputs': len(tx_data.get('vin', [])),
                            'outputs': len(tx_data.get('vout', []))
                        }
                        
                        results.append(result)
                        
                        if result['is_coinjoin']:
                            print(f"🚨 CoinJoin detected! Score: {result['score']}")
                            print(f"📊 Indicators: {result['indicators']}")
                            
                            # Start investigation
                            print("🔍 Starting investigation...")
                            await investigator.investigate_coinjoin(txid, tx_data, coinjoin_analysis)
                            print("✅ Investigation completed!")
                        else:
                            print(f"ℹ️  Not CoinJoin. Score: {result['score']}")
                        
                    else:
                        print(f"❌ Failed to fetch transaction: {response.status}")
                        results.append({
                            'txid': txid,
                            'error': f'HTTP {response.status}'
                        })
                        
            except Exception as e:
                print(f"❌ Error testing transaction: {e}")
                results.append({
                    'txid': txid,
                    'error': str(e)
                })
    
    # Print summary
    print("\n📊 Test Results Summary")
    print("=" * 60)
    for result in results:
        if 'error' in result:
            print(f"❌ {result['txid'][:16]}... - Error: {result['error']}")
        else:
            status = "🚨 CoinJoin" if result['is_coinjoin'] else "ℹ️  Normal"
            print(f"{status} {result['txid'][:16]}... - Score: {result['score']:.2f} ({result['inputs']}→{result['outputs']})")
    
    coinjoin_count = sum(1 for r in results if r.get('is_coinjoin', False))
    print(f"\n🎯 Summary: {coinjoin_count}/{len(results)} transactions detected as CoinJoin")

async def test_with_api():
    """Test thông qua API"""
    print("\n🌐 Testing through API")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # Test transaction
        test_txid = "83e4d97eb3fc1557462581827d834ea98d19ae09514c37b8f042a931a20da458"
        
        print(f"🔍 Investigating transaction via API: {test_txid}")
        
        try:
            payload = {"txid": test_txid}
            async with session.post(f"{base_url}/investigate", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ API Response: {data}")
                    
                    if data.get('is_coinjoin', False):
                        print("🚨 CoinJoin detected via API!")
                        
                        # Wait a bit for investigation to complete
                        print("⏳ Waiting for investigation to complete...")
                        await asyncio.sleep(10)
                        
                        # Check graphs
                        async with session.get(f"{base_url}/coinjoin/graphs") as resp2:
                            if resp2.status == 200:
                                graphs_data = await resp2.json()
                                graphs = graphs_data.get('graphs', [])
                                print(f"📊 Total graphs: {len(graphs)}")
                                
                                # Look for our test transaction
                                for graph in graphs:
                                    if graph.get('txid') == test_txid:
                                        print(f"✅ Found graph for test transaction!")
                                        print(f"📈 Addresses: {graph.get('total_coinjoin_addresses', 0)} coinjoin, {graph.get('total_related_addresses', 0)} related")
                                        break
                                else:
                                    print("ℹ️  Graph not found yet")
                            else:
                                print(f"❌ Failed to get graphs: {resp2.status}")
                    else:
                        print("ℹ️  Not CoinJoin via API")
                        
                else:
                    print(f"❌ API investigation failed: {resp.status}")
                    
        except Exception as e:
            print(f"❌ Error testing via API: {e}")

if __name__ == "__main__":
    print("🚀 CoinJoin Detection Test")
    print("=" * 60)
    
    # Run tests
    asyncio.run(test_coinjoin_detection())
    asyncio.run(test_multiple_transactions())
    asyncio.run(test_with_api())
    
    print("\n✨ Test completed!")
