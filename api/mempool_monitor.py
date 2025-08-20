"""
Mempool Monitor - Giám sát mempool để phát hiện CoinJoin transactions
"""

import requests
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
import aiohttp

from api.blockchain_api import BlockstreamAPI
from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

class MempoolMonitor:
    """
    Giám sát mempool để phát hiện CoinJoin transactions real-time
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.blockstream_api = BlockstreamAPI(config)
        self.mempool_url = "https://blockstream.info/api/mempool/recent"
        self.rate_limit_delay = config.get('mempool_rate_limit', 1.0)  # 1 giây
        self.session = None
        self.processed_txids = set()
        
    async def start_monitoring(self):
        """Bắt đầu giám sát mempool"""
        logger.info("Bắt đầu giám sát mempool...")
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            while True:
                try:
                    # Fetch mempool transactions
                    transactions = await self.fetch_mempool_transactions()
                    
                    if transactions:
                        logger.info(f"Fetched {len(transactions)} transactions from mempool")
                        
                        # Process each transaction
                        for tx_data in transactions:
                            txid = tx_data.get('txid')
                            if txid and txid not in self.processed_txids:
                                await self.process_transaction(tx_data)
                                self.processed_txids.add(txid)
                    
                    # Rate limiting
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.error(f"Error in mempool monitoring: {e}")
                    await asyncio.sleep(5)  # Wait longer on error
    
    async def fetch_mempool_transactions(self) -> List[Dict]:
        """Fetch transactions từ mempool"""
        try:
            async with self.session.get(self.mempool_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data if isinstance(data, list) else []
                else:
                    logger.warning(f"Failed to fetch mempool: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching mempool: {e}")
            return []
    
    async def process_transaction(self, tx_data: Dict):
        """Xử lý một transaction từ mempool"""
        txid = tx_data.get('txid')
        if not txid:
            return
        
        try:
            # Fetch full transaction details
            full_tx = await self.fetch_transaction_details(txid)
            if not full_tx:
                return
            
            # Analyze for CoinJoin
            coinjoin_analysis = await self.analyze_coinjoin(full_tx)
            
            if coinjoin_analysis.get('is_coinjoin', False):
                logger.info(f"🚨 CoinJoin detected in mempool: {txid}")
                
                # Trigger investigation
                await self.trigger_investigation(txid, full_tx, coinjoin_analysis)
            
        except Exception as e:
            logger.error(f"Error processing transaction {txid}: {e}")
    
    async def fetch_transaction_details(self, txid: str) -> Optional[Dict]:
        """Fetch chi tiết transaction"""
        try:
            url = f"https://blockstream.info/api/tx/{txid}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Error fetching transaction {txid}: {e}")
            return None
    
    async def analyze_coinjoin(self, tx_data: Dict) -> Dict:
        """Phân tích CoinJoin cho transaction bằng heuristic adapter"""
        from api.detector_adapter import detect_coinjoin
        return detect_coinjoin(tx_data)
    
    async def trigger_investigation(self, txid: str, tx_data: Dict, coinjoin_analysis: Dict):
        """Kích hoạt điều tra sâu cho CoinJoin transaction"""
        from api.coinjoin_investigator import CoinJoinInvestigator
        
        investigator = CoinJoinInvestigator(self.config)
        await investigator.investigate_coinjoin(txid, tx_data, coinjoin_analysis)
    
    async def close(self):
        """Đóng kết nối và dọn dẹp"""
        logger.info("Đóng MempoolMonitor")
        self.is_monitoring = False
        if self.session:
            await self.session.close()
