"""
Neo4j Storage - Lưu trữ dữ liệu CoinJoin investigation vào Neo4j
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging

from neo4j import AsyncGraphDatabase
from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

class Neo4jStorage:
    """
    Lưu trữ dữ liệu CoinJoin investigation vào Neo4j database
    """
    
    def __init__(self, config: Config):
        self.config = config
        
        # Neo4j connection settings
        self.neo4j_uri = config.get('neo4j_uri', 'bolt://192.168.100.128:7687')
        self.neo4j_user = config.get('neo4j_user', 'neo4j')
        # Default to requested credentials
        self.neo4j_password = config.get('neo4j_password', 'password123')
        
        # Initialize driver
        self.driver = None
        
    async def connect(self):
        """Kết nối đến Neo4j database"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            # Test connection
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
            
            logger.info(f"✅ Kết nối Neo4j thành công: {self.neo4j_uri}")
            
        except Exception as e:
            logger.error(f"❌ Lỗi kết nối Neo4j: {e}")
            raise
    
    async def close(self):
        """Đóng kết nối Neo4j"""
        if self.driver:
            await self.driver.close()
            logger.info("Đã đóng kết nối Neo4j")
    
    async def can_connect(self) -> bool:
        """Kiểm tra có kết nối được tới Neo4j không (không raise)."""
        try:
            await self.connect()
            return True
        except Exception:
            return False
    
    async def store_coinjoin_investigation(self, investigation_data: Dict):
        """Lưu kết quả điều tra CoinJoin vào Neo4j"""
        if not self.driver:
            await self.connect()
        
        try:
            async with self.driver.session() as session:
                # Create original transaction node
                await self.create_transaction_node(session, investigation_data['original_transaction'])
                
                # Create CoinJoin addresses
                for address in investigation_data['coinjoin_addresses']:
                    await self.create_address_node(session, address, 'coinjoin')
                
                # Create related addresses
                for address in investigation_data['related_addresses']:
                    if address not in investigation_data['coinjoin_addresses']:
                        await self.create_address_node(session, address, 'related')
                
                # Create relationships
                await self.create_relationships(session, investigation_data)
                
                # Create investigation metadata
                await self.create_investigation_metadata(session, investigation_data)
                
            logger.info(f"💾 Đã lưu investigation vào Neo4j: {investigation_data['original_transaction']['txid']}")
            
        except Exception as e:
            logger.error(f"Error storing to Neo4j: {e}")
    
    async def create_transaction_node(self, session, tx_data: Dict):
        """Tạo node transaction"""
        query = """
        MERGE (t:Transaction {txid: $txid})
        SET t.timestamp = $timestamp,
            t.coinjoin_score = $coinjoin_score,
            t.detection_method = $detection_method,
            t.fee = $fee,
            t.size = $size,
            t.indicators = $indicators,
            t.is_coinjoin = true
        """
        
        await session.run(query, {
            'txid': tx_data['txid'],
            'timestamp': tx_data['timestamp'],
            'coinjoin_score': tx_data['coinjoin_score'],
            'detection_method': tx_data['detection_method'],
            'fee': tx_data['fee'],
            'size': tx_data['size'],
            'indicators': str(tx_data['indicators'])
        })
    
    async def create_address_node(self, session, address: str, address_type: str):
        """Tạo node địa chỉ"""
        query = """
        MERGE (a:Address {address: $address})
        SET a.type = $address_type,
            a.first_seen = COALESCE(a.first_seen, $timestamp),
            a.last_seen = $timestamp
        """
        
        await session.run(query, {
            'address': address,
            'address_type': address_type,
            'timestamp': datetime.now().isoformat()
        })
    
    async def create_relationships(self, session, investigation_data: Dict):
        """Tạo các mối quan hệ giữa nodes"""
        txid = investigation_data['original_transaction']['txid']
        
        # Connect original transaction to CoinJoin addresses
        for address in investigation_data['coinjoin_addresses']:
            # Input relationship
            input_query = """
            MATCH (t:Transaction {txid: $txid})
            MATCH (a:Address {address: $address})
            MERGE (a)-[:INPUT_TO]->(t)
            """
            await session.run(input_query, {'txid': txid, 'address': address})
            
            # Output relationship
            output_query = """
            MATCH (t:Transaction {txid: $txid})
            MATCH (a:Address {address: $address})
            MERGE (t)-[:OUTPUT_TO]->(a)
            """
            await session.run(output_query, {'txid': txid, 'address': address})
        
        # Connect related addresses (limited relationships)
        for address in investigation_data['related_addresses'][:50]:  # Limit to avoid too many relationships
            if address not in investigation_data['coinjoin_addresses']:
                related_query = """
                MATCH (t:Transaction {txid: $txid})
                MATCH (a:Address {address: $address})
                MERGE (a)-[:RELATED_TO]->(t)
                """
                await session.run(related_query, {'txid': txid, 'address': address})
    
    async def create_investigation_metadata(self, session, investigation_data: Dict):
        """Tạo metadata cho investigation"""
        query = """
        CREATE (i:Investigation {
            txid: $txid,
            timestamp: $timestamp,
            depth_reached: $depth_reached,
            addresses_processed: $addresses_processed,
            coinjoin_found: $coinjoin_found,
            normal_found: $normal_found,
            total_coinjoin_addresses: $total_coinjoin_addresses,
            total_related_addresses: $total_related_addresses
        })
        """
        
        stats = investigation_data['investigation_stats']
        
        await session.run(query, {
            'txid': investigation_data['original_transaction']['txid'],
            'timestamp': investigation_data['original_transaction']['timestamp'],
            'depth_reached': stats['depth_reached'],
            'addresses_processed': stats['addresses_processed'],
            'coinjoin_found': stats['coinjoin_found'],
            'normal_found': stats['normal_found'],
            'total_coinjoin_addresses': len(investigation_data['coinjoin_addresses']),
            'total_related_addresses': len(investigation_data['related_addresses'])
        })
    
    async def get_coinjoin_statistics(self) -> Dict:
        """Lấy thống kê CoinJoin từ Neo4j"""
        if not self.driver:
            await self.connect()
        
        try:
            async with self.driver.session() as session:
                # Total CoinJoin transactions
                result = await session.run("MATCH (t:Transaction {is_coinjoin: true}) RETURN count(t) as count")
                total_coinjoin_txs = (await result.single())['count']
                
                # Total CoinJoin addresses
                result = await session.run("MATCH (a:Address {type: 'coinjoin'}) RETURN count(a) as count")
                total_coinjoin_addresses = (await result.single())['count']
                
                # Recent CoinJoin transactions (last 24h)
                result = await session.run("""
                    MATCH (t:Transaction {is_coinjoin: true})
                    WHERE t.timestamp > datetime() - duration({hours: 24})
                    RETURN count(t) as count
                """)
                recent_coinjoin_txs = (await result.single())['count']
                
                # Detection methods distribution
                result = await session.run("""
                    MATCH (t:Transaction {is_coinjoin: true})
                    RETURN t.detection_method as method, count(t) as count
                    ORDER BY count DESC
                """)
                detection_methods = [(record['method'], record['count']) for record in await result.data()]
                
                return {
                    'total_coinjoin_transactions': total_coinjoin_txs,
                    'total_coinjoin_addresses': total_coinjoin_addresses,
                    'recent_coinjoin_transactions_24h': recent_coinjoin_txs,
                    'detection_methods': detection_methods
                }
                
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    async def search_coinjoin_by_address(self, address: str) -> List[Dict]:
        """Tìm kiếm CoinJoin transactions theo địa chỉ"""
        if not self.driver:
            await self.connect()
        
        try:
            async with self.driver.session() as session:
                query = """
                MATCH (a:Address {address: $address})-[:INPUT_TO|OUTPUT_TO]->(t:Transaction {is_coinjoin: true})
                RETURN t.txid as txid, t.timestamp as timestamp, t.coinjoin_score as score, t.detection_method as method
                ORDER BY t.timestamp DESC
                LIMIT 10
                """
                
                result = await session.run(query, {'address': address})
                return await result.data()
                
        except Exception as e:
            logger.error(f"Error searching by address: {e}")
            return []
    
    async def get_all_coinjoin_graphs(self) -> List[Dict]:
        """Lấy tất cả đồ thị CoinJoin đã lưu trữ"""
        try:
            if not self.driver:
                await self.connect()
            
            async with self.driver.session() as session:
                # Query để lấy tất cả investigation metadata
                query = """
                MATCH (i:Investigation)
                RETURN i.txid as txid,
                       i.timestamp as timestamp,
                       i.depth_reached as depth_reached,
                       i.addresses_processed as addresses_processed,
                       i.coinjoin_found as coinjoin_found,
                       i.normal_found as normal_found,
                       i.total_coinjoin_addresses as total_coinjoin_addresses,
                       i.total_related_addresses as total_related_addresses
                ORDER BY i.timestamp DESC
                """
                
                result = await session.run(query)
                investigations = []
                
                async for record in result:
                    investigation = {
                        'txid': record['txid'],
                        'timestamp': record['timestamp'],
                        'depth_reached': record['depth_reached'],
                        'addresses_processed': record['addresses_processed'],
                        'coinjoin_found': record['coinjoin_found'],
                        'normal_found': record['normal_found'],
                        'total_coinjoin_addresses': record['total_coinjoin_addresses'],
                        'total_related_addresses': record['total_related_addresses']
                    }
                    investigations.append(investigation)
                
                return investigations
                
        except Exception as e:
            logger.error(f"Error getting all CoinJoin graphs: {e}")
            return []
    
    async def get_coinjoin_graph_by_id(self, investigation_id: str) -> Optional[Dict]:
        """Lấy đồ thị CoinJoin theo investigation ID (sử dụng txid)"""
        try:
            if not self.driver:
                await self.connect()
            
            async with self.driver.session() as session:
                # Query để lấy investigation metadata
                metadata_query = """
                MATCH (i:Investigation {txid: $txid})
                RETURN i
                """
                
                metadata_result = await session.run(metadata_query, txid=investigation_id)
                metadata_record = await metadata_result.single()
                
                if not metadata_record:
                    return None
                
                metadata = metadata_record['i']
                
                # Query để lấy tất cả transactions liên quan
                tx_query = """
                MATCH (i:Investigation {txid: $txid})
                MATCH (t:Transaction)
                WHERE t.txid = $txid OR t.txid IN $related_txids
                RETURN t.txid as txid,
                       t.value as value,
                       t.timestamp as timestamp,
                       t.is_coinjoin as is_coinjoin,
                       t.coinjoin_score as coinjoin_score
                """
                
                # Lấy danh sách related transaction IDs từ metadata
                related_txids = getattr(metadata, 'related_txids', [])
                
                tx_result = await session.run(tx_query, txid=investigation_id, related_txids=related_txids)
                transactions = []
                
                async for record in tx_result:
                    tx = {
                        'txid': record['txid'],
                        'value': record['value'],
                        'timestamp': record['timestamp'],
                        'is_coinjoin': record['is_coinjoin'],
                        'coinjoin_score': record['coinjoin_score']
                    }
                    transactions.append(tx)
                
                # Query để lấy tất cả addresses liên quan
                addr_query = """
                MATCH (i:Investigation {txid: $txid})
                MATCH (a:Address)
                WHERE a.address IN $coinjoin_addresses OR a.address IN $related_addresses
                RETURN DISTINCT a.address as address,
                       a.balance as balance,
                       a.tx_count as tx_count,
                       a.type as type
                """
                
                coinjoin_addresses = getattr(metadata, 'coinjoin_addresses', [])
                related_addresses = getattr(metadata, 'related_addresses', [])
                
                addr_result = await session.run(addr_query, 
                                              txid=investigation_id, 
                                              coinjoin_addresses=coinjoin_addresses,
                                              related_addresses=related_addresses)
                addresses = []
                
                async for record in addr_result:
                    addr = {
                        'address': record['address'],
                        'balance': record['balance'],
                        'tx_count': record['tx_count'],
                        'type': record['type']
                    }
                    addresses.append(addr)
                
                # Query để lấy relationships
                rel_query = """
                MATCH (i:Investigation {txid: $txid})
                MATCH (t:Transaction)-[r:HAS_INPUT|HAS_OUTPUT]->(a:Address)
                WHERE t.txid = $txid OR t.txid IN $related_txids
                RETURN t.txid as txid,
                       type(r) as relationship_type,
                       a.address as address
                """
                
                rel_result = await session.run(rel_query, txid=investigation_id, related_txids=related_txids)
                relationships = []
                
                async for record in rel_result:
                    rel = {
                        'txid': record['txid'],
                        'relationship_type': record['relationship_type'],
                        'address': record['address']
                    }
                    relationships.append(rel)
                
                return {
                    'investigation_id': investigation_id,
                    'metadata': {
                        'txid': metadata['txid'],
                        'timestamp': metadata['timestamp'],
                        'depth_reached': metadata['depth_reached'],
                        'addresses_processed': metadata['addresses_processed'],
                        'coinjoin_found': metadata['coinjoin_found'],
                        'normal_found': metadata['normal_found'],
                        'total_coinjoin_addresses': metadata['total_coinjoin_addresses'],
                        'total_related_addresses': metadata['total_related_addresses']
                    },
                    'transactions': transactions,
                    'addresses': addresses,
                    'relationships': relationships
                }
                
        except Exception as e:
            logger.error(f"Error getting CoinJoin graph by ID: {e}")
            return None
