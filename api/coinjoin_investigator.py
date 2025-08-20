"""
CoinJoin Investigator - Điều tra sâu các giao dịch CoinJoin với DFS
"""

import asyncio
import aiohttp
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
import logging

from api.blockchain_api import BlockstreamAPI
from api.neo4j_storage import Neo4jStorage
from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

class CoinJoinInvestigator:
    """
    Điều tra sâu các giao dịch CoinJoin với thuật toán DFS
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.blockstream_api = BlockstreamAPI(config)
        self.neo4j_storage = Neo4jStorage(config)
        
        # DFS parameters
        self.max_depth = config.get('investigation_max_depth', 3)
        self.max_transactions_per_address = config.get('max_transactions_per_address', 5)
        self.max_addresses_per_tx = config.get('max_addresses_per_tx', 10)
        self.consecutive_normal_limit = config.get('consecutive_normal_limit', 10)
        self.max_non_cluster_steps = config.get('max_non_cluster_steps', 5)
        
        # Tracking
        self.visited_addresses = set()
        self.visited_transactions = set()
        self.coinjoin_addresses = set()
        self.coinjoin_transactions = set()
        self.original_input_addresses = set()
        self.start_address = None
        
    async def investigate_coinjoin(self, txid: str, tx_data: Dict, coinjoin_analysis: Dict):
        """Điều tra sâu một giao dịch CoinJoin"""
        logger.info(f"🔍 Bắt đầu điều tra CoinJoin: {txid}")
        
        try:
            # Initialize investigation
            self.visited_addresses.clear()
            self.visited_transactions.clear()
            self.coinjoin_addresses.clear()
            self.coinjoin_transactions.clear()
            
            # Extract addresses from CoinJoin transaction
            addresses = self.extract_addresses_from_transaction(tx_data)
            # Set original input cluster and start address (only 1 address as requested)
            self.original_input_addresses = {
                vin['prevout']['scriptpubkey_address']
                for vin in tx_data.get('vin', [])
                if 'prevout' in vin and 'scriptpubkey_address' in vin['prevout']
            }
            self.start_address = next(iter(self.original_input_addresses), None)
            if not self.start_address:
                # fallback to first output
                for vout in tx_data.get('vout', []):
                    if 'scriptpubkey_address' in vout:
                        self.start_address = vout['scriptpubkey_address']
                        break
            if not self.start_address:
                logger.error("Không xác định được địa chỉ bắt đầu")
                return
            
            # Add to CoinJoin sets
            self.coinjoin_addresses.update(addresses)
            self.coinjoin_transactions.add(txid)
            
            # Start linear investigation from single start address
            investigation_results = await self.linear_investigation(
                current_address=self.start_address,
                depth=0,
                non_cluster_steps=0
            )
            
            # Store results to Neo4j
            await self.store_investigation_results(
                txid, 
                tx_data, 
                coinjoin_analysis, 
                investigation_results
            )
            
            logger.info(f"✅ Hoàn thành điều tra CoinJoin: {txid}")
            logger.info(f"   - Địa chỉ CoinJoin: {len(self.coinjoin_addresses)}")
            logger.info(f"   - Giao dịch CoinJoin: {len(self.coinjoin_transactions)}")
            logger.info(f"   - Địa chỉ liên quan: {len(self.visited_addresses)}")
            
        except Exception as e:
            logger.error(f"Error investigating CoinJoin {txid}: {e}")

    async def investigate_from_address(self, address: str, max_depth: int | None = None) -> Dict:
        """Điều tra tuyến tính bắt đầu từ một địa chỉ duy nhất (không cần coinjoin trước).
        - Cluster chỉ điểm đầu (address) và điểm cuối theo từng bước.
        - Dừng nếu quay về điểm đầu hoặc sau 5 giao dịch mà không chạm cụm input.
        Trả về dict kết quả (không ghi Neo4j).
        """
        # Reset state
        self.visited_addresses.clear()
        self.visited_transactions.clear()
        self.coinjoin_addresses.clear()
        self.coinjoin_transactions.clear()
        self.original_input_addresses = {address}
        self.start_address = address
        original_max_depth = self.max_depth
        if isinstance(max_depth, int) and max_depth > 0:
            self.max_depth = max_depth

        try:
            results = await self.linear_investigation(address, depth=0, non_cluster_steps=0)
            return results
        finally:
            # restore
            self.max_depth = original_max_depth

    async def linear_investigation(self, current_address: str, depth: int, non_cluster_steps: int) -> Dict:
        """Điều tra tuyến tính theo 1 địa chỉ, chỉ cluster điểm đầu/cuối.
        Dừng nếu điểm cuối trùng điểm đầu, hoặc sau 5 tx không tìm thấy cluster với input cluster.
        """
        if depth >= self.max_depth:
            return {
                'depth': depth,
                'addresses_processed': len(self.visited_addresses),
                'coinjoin_found': len(self.coinjoin_transactions),
                'normal_found': 0,
                'related_addresses': set(),
                'related_transactions': set()
            }

        self.visited_addresses.add(current_address)

        # Fetch transactions of current address (limit)
        address_txs = await self.fetch_address_transactions(current_address)
        address_txs = (address_txs or [])[: self.max_transactions_per_address]

        results = {
            'depth': depth,
            'addresses_processed': len(self.visited_addresses),
            'coinjoin_found': 0,
            'normal_found': 0,
            'related_addresses': set(),
            'related_transactions': set()
        }

        for tx in address_txs:
            txid = tx.get('txid')
            if not txid or txid in self.visited_transactions:
                continue
            self.visited_transactions.add(txid)

            tx_addresses = self.extract_addresses_from_transaction(tx)
            results['related_addresses'].update(tx_addresses)
            results['related_transactions'].add(txid)

            # Check loop closure: end matches start
            if self.start_address in tx_addresses and depth > 0:
                logger.info(f"🔁 Điểm cuối trùng điểm đầu tại tx {txid}, dừng điều tra")
                return results

            # Analyze coinjoin
            coinjoin_analysis = await self.analyze_transaction_coinjoin(tx)
            if coinjoin_analysis.get('is_coinjoin', False):
                self.coinjoin_transactions.add(txid)
                self.coinjoin_addresses.update(tx_addresses)
                results['coinjoin_found'] += 1

            # Cluster match with original input cluster?
            cluster_match_found = bool(tx_addresses & self.original_input_addresses)
            if cluster_match_found:
                non_cluster_steps = 0
            else:
                non_cluster_steps += 1
                if non_cluster_steps >= self.max_non_cluster_steps:
                    logger.info("⛔ Không tìm thấy cluster với input sau 5 tx, dừng điều tra")
                    return results

            # Choose next end address (first address not equal current)
            next_address = None
            for addr in tx_addresses:
                if addr != current_address:
                    next_address = addr
                    break
            if not next_address:
                continue

            # Recurse linearly
            sub = await self.linear_investigation(next_address, depth + 1, non_cluster_steps)
            # Merge minimal counters
            results['addresses_processed'] = max(results['addresses_processed'], sub.get('addresses_processed', 0))
            results['coinjoin_found'] += sub.get('coinjoin_found', 0)
            results['normal_found'] += sub.get('normal_found', 0)
            results['related_addresses'].update(sub.get('related_addresses', set()))
            results['related_transactions'].update(sub.get('related_transactions', set()))

            # After first successful walk, stop (single-path)
            break

        return results
    
    def extract_addresses_from_transaction(self, tx_data: Dict) -> Set[str]:
        """Trích xuất tất cả địa chỉ từ transaction"""
        addresses = set()
        
        # Input addresses
        for vin in tx_data.get('vin', []):
            if 'prevout' in vin and 'scriptpubkey_address' in vin['prevout']:
                addresses.add(vin['prevout']['scriptpubkey_address'])
        
        # Output addresses
        for vout in tx_data.get('vout', []):
            if 'scriptpubkey_address' in vout:
                addresses.add(vout['scriptpubkey_address'])
        
        return addresses
    
    async def dfs_investigation(
        self, 
        addresses: Set[str], 
        depth: int, 
        consecutive_normal: int
    ) -> Dict:
        """DFS investigation cho các địa chỉ"""
        
        if depth >= self.max_depth:
            logger.debug(f"Đạt độ sâu tối đa: {depth}")
            return {}
        
        if consecutive_normal >= self.consecutive_normal_limit:
            logger.debug(f"Gặp quá nhiều giao dịch normal liên tiếp: {consecutive_normal}")
            return {}
        
        investigation_results = {
            'depth': depth,
            'addresses_processed': len(addresses),
            'coinjoin_found': 0,
            'normal_found': 0,
            'related_addresses': set(),
            'related_transactions': set()
        }
        
        for address in addresses:
            if address in self.visited_addresses:
                continue
                
            self.visited_addresses.add(address)
            
            # Fetch address transactions
            address_txs = await self.fetch_address_transactions(address)
            if not address_txs:
                continue
            
            # Limit transactions per address
            address_txs = address_txs[:self.max_transactions_per_address]
            
            local_consecutive_normal = consecutive_normal
            
            for tx in address_txs:
                txid = tx.get('txid')
                if not txid or txid in self.visited_transactions:
                    continue
                
                self.visited_transactions.add(txid)
                
                # Analyze transaction for CoinJoin
                coinjoin_analysis = await self.analyze_transaction_coinjoin(tx)
                
                if coinjoin_analysis.get('is_coinjoin', False):
                    logger.info(f"🔍 Phát hiện CoinJoin liên quan: {txid} (depth: {depth})")
                    
                    # Add to CoinJoin sets
                    self.coinjoin_transactions.add(txid)
                    tx_addresses = self.extract_addresses_from_transaction(tx)
                    self.coinjoin_addresses.update(tx_addresses)
                    investigation_results['related_addresses'].update(tx_addresses)
                    investigation_results['related_transactions'].add(txid)
                    investigation_results['coinjoin_found'] += 1
                    
                    # Reset consecutive normal counter
                    local_consecutive_normal = 0
                    
                    # Continue DFS for this CoinJoin
                    if depth < self.max_depth - 1:
                        await self.dfs_investigation(
                            tx_addresses, 
                            depth + 1, 
                            local_consecutive_normal
                        )
                else:
                    local_consecutive_normal += 1
                    investigation_results['normal_found'] += 1
                    
                    # Add addresses from normal transaction (limited)
                    tx_addresses = self.extract_addresses_from_transaction(tx)
                    limited_addresses = set(list(tx_addresses)[:self.max_addresses_per_tx])
                    investigation_results['related_addresses'].update(limited_addresses)
                    investigation_results['related_transactions'].add(txid)
        
        return investigation_results
    
    async def fetch_address_transactions(self, address: str) -> List[Dict]:
        """Fetch transactions của một địa chỉ"""
        try:
            url = f"https://blockstream.info/api/address/{address}/txs"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    return []
        except Exception as e:
            logger.error(f"Error fetching transactions for {address}: {e}")
            return []
    
    async def analyze_transaction_coinjoin(self, tx_data: Dict) -> Dict:
        """Phân tích một transaction có phải CoinJoin không (heuristic)"""
        from api.detector_adapter import detect_coinjoin
        return detect_coinjoin(tx_data)
    
    # --- Tree-building investigation (unified for tx/address) ---
    async def fetch_transaction_details_async(self, txid: str) -> Optional[Dict]:
        """Fetch chi tiết transaction (async)."""
        try:
            url = f"https://blockstream.info/api/tx/{txid}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
        except Exception as e:
            logger.error(f"Error fetching transaction {txid}: {e}")
            return None

    async def build_tree_from_txid(self, txid: str, max_depth: int = 10) -> Dict:
        """Xây dựng cây giao dịch bắt đầu từ 1 txid.
        Dừng khi cụm đầu ra chạm cụm input ban đầu hoặc đạt depth = max_depth (tối đa 10).
        """
        self.visited_transactions.clear()
        self.visited_addresses.clear()
        self.coinjoin_addresses.clear()
        self.coinjoin_transactions.clear()

        self.max_depth = min(int(max_depth or 10), 10)

        root_tx = await self.fetch_transaction_details_async(txid)
        if not root_tx:
            return {}

        # Original input cluster: all input addresses of root tx
        self.original_input_addresses = {
            vin.get('prevout', {}).get('scriptpubkey_address')
            for vin in root_tx.get('vin', [])
            if vin.get('prevout', {}).get('scriptpubkey_address')
        }

        return await self._build_tree_recursive(root_tx, depth=0)

    async def build_tree_from_address(self, address: str, max_depth: int = 10) -> Dict:
        """Xây dựng cây giao dịch bắt đầu từ một địa chỉ.
        Chọn transaction đầu tiên mà địa chỉ xuất hiện ở input, nếu không có thì dùng transaction đầu tiên.
        """
        self.visited_transactions.clear()
        self.visited_addresses.clear()
        self.coinjoin_addresses.clear()
        self.coinjoin_transactions.clear()

        self.max_depth = min(int(max_depth or 10), 10)
        self.original_input_addresses = {address}

        txs = await self.fetch_address_transactions(address)
        if not txs:
            return {}

        # Prefer a tx where address appears in input
        start_tx = None
        for tx in txs:
            for vin in tx.get('vin', []) or []:
                if vin.get('prevout', {}).get('scriptpubkey_address') == address:
                    start_tx = tx
                    break
            if start_tx:
                break
        if start_tx is None:
            start_tx = txs[0]

        # Ensure we have full details (address list call may already be detailed, but normalize)
        txid = start_tx.get('txid') or start_tx.get('hash')
        if not txid:
            return {}
        full_tx = await self.fetch_transaction_details_async(txid)
        if not full_tx:
            # fallback to what we have
            full_tx = start_tx

        return await self._build_tree_recursive(full_tx, depth=0)

    async def _build_tree_recursive(self, tx_data: Dict, depth: int) -> Dict:
        """Đệ quy xây cây giao dịch theo dạng:
        { tx: {...}, out: [ { tx: {...}, out: [...] }, ... ] }
        """
        if depth >= self.max_depth:
            return { 'tx': self._compact_tx(tx_data), 'out': [] }

        txid = tx_data.get('txid') or tx_data.get('hash')
        if not txid:
            return { 'tx': self._compact_tx(tx_data), 'out': [] }

        if txid in self.visited_transactions:
            return { 'tx': self._compact_tx(tx_data), 'out': [] }
        self.visited_transactions.add(txid)

        # Collect child transactions per output address
        child_nodes = []
        out_addresses = [v.get('scriptpubkey_address') for v in tx_data.get('vout', []) if v.get('scriptpubkey_address')]

        for addr in out_addresses:
            # If output cluster intersects original input cluster, stop here
            if addr in self.original_input_addresses and depth > 0:
                # closure condition reached
                return { 'tx': self._compact_tx(tx_data), 'out': [] }

            # Find child txs that spend from this address
            address_txs = await self.fetch_address_transactions(addr)
            # Filter txs where addr appears in inputs (spent by)
            child_txids = []
            for t in address_txs or []:
                t_txid = t.get('txid') or t.get('hash')
                if not t_txid or t_txid == txid:
                    continue
                vins = t.get('vin', []) or []
                if any(v.get('prevout', {}).get('scriptpubkey_address') == addr for v in vins):
                    child_txids.append(t_txid)

            # For each child, recurse
            for c_txid in child_txids:
                child_full = await self.fetch_transaction_details_async(c_txid)
                if not child_full:
                    continue

                # Stop if child's outputs intersect original input cluster
                child_out_addrs = {
                    v.get('scriptpubkey_address') for v in child_full.get('vout', []) if v.get('scriptpubkey_address')
                }
                if child_out_addrs & self.original_input_addresses:
                    child_nodes.append({ 'tx': self._compact_tx(child_full), 'out': [] })
                    # Do not expand further on closure
                    continue

                subtree = await self._build_tree_recursive(child_full, depth + 1)
                child_nodes.append(subtree)

        return { 'tx': self._compact_tx(tx_data), 'out': child_nodes }

    def _compact_tx(self, tx_data: Dict) -> Dict:
        """Rút gọn thông tin tx để hiển thị trong cây."""
        return {
            'txid': tx_data.get('txid') or tx_data.get('hash'),
            'vin_count': len(tx_data.get('vin', []) or []),
            'vout_count': len(tx_data.get('vout', []) or []),
            'fee': tx_data.get('fee'),
            'size': tx_data.get('size'),
        }

    async def store_investigation_results(
        self, 
        original_txid: str, 
        original_tx_data: Dict, 
        coinjoin_analysis: Dict, 
        investigation_results: Dict
    ):
        """Lưu kết quả điều tra vào Neo4j"""
        try:
            # Prepare data for Neo4j
            neo4j_data = {
                'original_transaction': {
                    'txid': original_txid,
                    'timestamp': datetime.now().isoformat(),
                    'coinjoin_score': coinjoin_analysis.get('coinjoin_score', 0),
                    'detection_method': coinjoin_analysis.get('detection_method', 'unknown'),
                    'indicators': coinjoin_analysis.get('indicators', {}),
                    'fee': original_tx_data.get('fee', 0),
                    'size': original_tx_data.get('size', 0)
                },
                'coinjoin_addresses': list(self.coinjoin_addresses),
                'coinjoin_transactions': list(self.coinjoin_transactions),
                'related_addresses': list(investigation_results.get('related_addresses', set())),
                'related_transactions': list(investigation_results.get('related_transactions', set())),
                'investigation_stats': {
                    'depth_reached': investigation_results.get('depth', 0),
                    'addresses_processed': investigation_results.get('addresses_processed', 0),
                    'coinjoin_found': investigation_results.get('coinjoin_found', 0),
                    'normal_found': investigation_results.get('normal_found', 0)
                }
            }
            
            # Store to Neo4j
            await self.neo4j_storage.store_coinjoin_investigation(neo4j_data)
            
            logger.info(f"💾 Đã lưu kết quả điều tra vào Neo4j: {original_txid}")
            
        except Exception as e:
            logger.error(f"Error storing investigation results: {e}")
