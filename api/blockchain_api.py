"""
Generic Blockchain API Interface
Hỗ trợ nhiều nguồn API khác nhau để fetch transaction data
"""

import requests
import json
import time
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod
import logging

from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

class BlockchainAPI(ABC):
    """Abstract base class cho blockchain API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CoinJoin-Investigator/1.0'
        })
    
    @abstractmethod
    def fetch_address_transactions(self, address: str) -> List[Dict]:
        """Fetch tất cả transactions của một địa chỉ"""
        pass
    
    @abstractmethod
    def fetch_transaction_details(self, tx_hash: str) -> Dict:
        """Fetch chi tiết của một transaction"""
        pass
    
    @abstractmethod
    def get_api_name(self) -> str:
        """Trả về tên của API"""
        pass

class BlockstreamAPI(BlockchainAPI):
    """Blockstream API implementation"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.base_url = config.get('blockstream_base_url', 'https://blockstream.info/api')
        self.rate_limit_delay = config.get('blockstream_rate_limit', 0.1)
    
    def get_api_name(self) -> str:
        return "blockstream"
    
    def fetch_address_transactions(self, address: str) -> List[Dict]:
        """
        Fetch tất cả transactions của một địa chỉ từ Blockstream API
        """
        try:
            # Fetch address info
            url = f"{self.base_url}/address/{address}"
            response = self.session.get(url)
            response.raise_for_status()
            
            address_info = response.json()
            
            # Fetch transactions
            url = f"{self.base_url}/address/{address}/txs"
            response = self.session.get(url)
            response.raise_for_status()
            
            transactions = response.json()
            
            # Process và format transactions
            formatted_transactions = []
            for tx in transactions:
                formatted_tx = self._format_transaction(tx, address)
                if formatted_tx:
                    formatted_transactions.append(formatted_tx)
            
            logger.info(f"Fetched {len(formatted_transactions)} transactions for address {address[:10]}...")
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return formatted_transactions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching transactions for {address}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error for {address}: {str(e)}")
            return []
    
    def fetch_transaction_details(self, tx_hash: str) -> Dict:
        """
        Fetch chi tiết của một transaction
        """
        try:
            url = f"{self.base_url}/tx/{tx_hash}"
            response = self.session.get(url)
            response.raise_for_status()
            
            tx_data = response.json()
            return self._format_transaction(tx_data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching transaction {tx_hash}: {str(e)}")
            return {}
    
    def _format_transaction(self, tx_data: Dict, target_address: str = None) -> Optional[Dict]:
        """
        Format transaction data từ Blockstream API
        """
        try:
            formatted_tx = {
                'hash': tx_data.get('txid', ''),
                'block_height': tx_data.get('status', {}).get('block_height'),
                'time': tx_data.get('status', {}).get('block_time'),
                'fee': tx_data.get('fee', 0),
                'vin_sz': len(tx_data.get('vin', [])),
                'vout_sz': len(tx_data.get('vout', [])),
                'size': tx_data.get('size', 0),
                'weight': tx_data.get('weight', 0),
                'inputs': [],
                'outputs': []
            }
            
            # Process inputs
            for vin in tx_data.get('vin', []):
                input_data = {
                    'prev_tx_hash': vin.get('txid', ''),
                    'prev_output_index': vin.get('vout', 0),
                    'address': vin.get('prevout', {}).get('scriptpubkey_address', ''),
                    'value': vin.get('prevout', {}).get('value', 0)
                }
                formatted_tx['inputs'].append(input_data)
            
            # Process outputs
            for vout in tx_data.get('vout', []):
                output_data = {
                    'value': vout.get('value', 0),
                    'address': vout.get('scriptpubkey_address', ''),
                    'script_pubkey': vout.get('scriptpubkey', ''),
                    'output_index': vout.get('vout', 0)
                }
                formatted_tx['outputs'].append(output_data)
            
            return formatted_tx
            
        except Exception as e:
            logger.error(f"Error formatting transaction: {str(e)}")
            return None

class MempoolAPI(BlockchainAPI):
    """Mempool.space API implementation"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.base_url = config.get('mempool_base_url', 'https://mempool.space/api')
        self.rate_limit_delay = config.get('mempool_rate_limit', 0.1)
    
    def get_api_name(self) -> str:
        return "mempool"
    
    def fetch_address_transactions(self, address: str) -> List[Dict]:
        """
        Fetch tất cả transactions của một địa chỉ từ Mempool API
        """
        try:
            # Fetch address transactions
            url = f"{self.base_url}/address/{address}/txs"
            response = self.session.get(url)
            response.raise_for_status()
            
            transactions = response.json()
            
            # Process và format transactions
            formatted_transactions = []
            for tx in transactions:
                formatted_tx = self._format_transaction(tx, address)
                if formatted_tx:
                    formatted_transactions.append(formatted_tx)
            
            logger.info(f"Fetched {len(formatted_transactions)} transactions for address {address[:10]}...")
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return formatted_transactions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching transactions for {address}: {str(e)}")
            return []
    
    def fetch_transaction_details(self, tx_hash: str) -> Dict:
        """
        Fetch chi tiết của một transaction
        """
        try:
            url = f"{self.base_url}/tx/{tx_hash}"
            response = self.session.get(url)
            response.raise_for_status()
            
            tx_data = response.json()
            return self._format_transaction(tx_data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching transaction {tx_hash}: {str(e)}")
            return {}
    
    def _format_transaction(self, tx_data: Dict, target_address: str = None) -> Optional[Dict]:
        """
        Format transaction data từ Mempool API
        """
        try:
            formatted_tx = {
                'hash': tx_data.get('txid', ''),
                'block_height': tx_data.get('status', {}).get('block_height'),
                'time': tx_data.get('status', {}).get('block_time'),
                'fee': tx_data.get('fee', 0),
                'vin_sz': len(tx_data.get('vin', [])),
                'vout_sz': len(tx_data.get('vout', [])),
                'size': tx_data.get('size', 0),
                'weight': tx_data.get('weight', 0),
                'inputs': [],
                'outputs': []
            }
            
            # Process inputs
            for vin in tx_data.get('vin', []):
                input_data = {
                    'prev_tx_hash': vin.get('txid', ''),
                    'prev_output_index': vin.get('vout', 0),
                    'address': vin.get('prevout', {}).get('scriptpubkey_address', ''),
                    'value': vin.get('prevout', {}).get('value', 0)
                }
                formatted_tx['inputs'].append(input_data)
            
            # Process outputs
            for vout in tx_data.get('vout', []):
                output_data = {
                    'value': vout.get('value', 0),
                    'address': vout.get('scriptpubkey_address', ''),
                    'script_pubkey': vout.get('scriptpubkey', ''),
                    'output_index': vout.get('vout', 0)
                }
                formatted_tx['outputs'].append(output_data)
            
            return formatted_tx
            
        except Exception as e:
            logger.error(f"Error formatting transaction: {str(e)}")
            return None

class BitcoinCoreAPI(BlockchainAPI):
    """Bitcoin Core RPC API implementation"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.rpc_url = config.get('bitcoin_core_rpc_url', 'http://localhost:8332')
        self.rpc_user = config.get('bitcoin_core_rpc_user', '')
        self.rpc_password = config.get('bitcoin_core_rpc_password', '')
        self.rate_limit_delay = config.get('bitcoin_core_rate_limit', 0.1)
    
    def get_api_name(self) -> str:
        return "bitcoin_core"
    
    def fetch_address_transactions(self, address: str) -> List[Dict]:
        """
        Fetch tất cả transactions của một địa chỉ từ Bitcoin Core RPC
        """
        try:
            # Get address info
            address_info = self._rpc_call('getaddressinfo', [address])
            
            # Get address transactions
            transactions = self._rpc_call('getaddresstxids', [address])
            
            # Fetch transaction details
            formatted_transactions = []
            for tx_hash in transactions:
                tx_data = self._rpc_call('getrawtransaction', [tx_hash, True])
                if tx_data:
                    formatted_tx = self._format_transaction(tx_data, address)
                    if formatted_tx:
                        formatted_transactions.append(formatted_tx)
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
            
            logger.info(f"Fetched {len(formatted_transactions)} transactions for address {address[:10]}...")
            return formatted_transactions
            
        except Exception as e:
            logger.error(f"Error fetching transactions for {address}: {str(e)}")
            return []
    
    def fetch_transaction_details(self, tx_hash: str) -> Dict:
        """
        Fetch chi tiết của một transaction
        """
        try:
            tx_data = self._rpc_call('getrawtransaction', [tx_hash, True])
            return self._format_transaction(tx_data) if tx_data else {}
            
        except Exception as e:
            logger.error(f"Error fetching transaction {tx_hash}: {str(e)}")
            return {}
    
    def _rpc_call(self, method: str, params: List[Any]) -> Any:
        """
        Thực hiện RPC call đến Bitcoin Core
        """
        try:
            payload = {
                'jsonrpc': '2.0',
                'method': method,
                'params': params,
                'id': 1
            }
            
            response = self.session.post(
                self.rpc_url,
                json=payload,
                auth=(self.rpc_user, self.rpc_password),
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            result = response.json()
            if 'error' in result and result['error'] is not None:
                raise Exception(f"RPC Error: {result['error']}")
            
            return result.get('result')
            
        except Exception as e:
            logger.error(f"RPC call failed for {method}: {str(e)}")
            return None
    
    def _format_transaction(self, tx_data: Dict, target_address: str = None) -> Optional[Dict]:
        """
        Format transaction data từ Bitcoin Core RPC
        """
        try:
            formatted_tx = {
                'hash': tx_data.get('txid', ''),
                'block_height': tx_data.get('blockheight'),
                'time': tx_data.get('time'),
                'fee': 0,  # Fee cần tính toán riêng
                'vin_sz': len(tx_data.get('vin', [])),
                'vout_sz': len(tx_data.get('vout', [])),
                'size': tx_data.get('size', 0),
                'weight': tx_data.get('weight', 0),
                'inputs': [],
                'outputs': []
            }
            
            # Process inputs
            for vin in tx_data.get('vin', []):
                input_data = {
                    'prev_tx_hash': vin.get('txid', ''),
                    'prev_output_index': vin.get('vout', 0),
                    'address': '',  # Cần fetch từ prevout
                    'value': 0     # Cần fetch từ prevout
                }
                formatted_tx['inputs'].append(input_data)
            
            # Process outputs
            for vout in tx_data.get('vout', []):
                output_data = {
                    'value': vout.get('value', 0),
                    'address': vout.get('scriptPubKey', {}).get('addresses', [''])[0] if vout.get('scriptPubKey', {}).get('addresses') else '',
                    'script_pubkey': vout.get('scriptPubKey', {}).get('hex', ''),
                    'output_index': vout.get('n', 0)
                }
                formatted_tx['outputs'].append(output_data)
            
            return formatted_tx
            
        except Exception as e:
            logger.error(f"Error formatting transaction: {str(e)}")
            return None

class BlockchainAPIFactory:
    """Factory class để tạo API instances"""
    
    @staticmethod
    def create_api(api_name: str, config: Config) -> BlockchainAPI:
        """
        Tạo API instance dựa trên tên
        
        Args:
            api_name: Tên API ('blockstream', 'mempool', 'bitcoin_core')
            config: Configuration object
            
        Returns:
            BlockchainAPI instance
        """
        if api_name.lower() == 'blockstream':
            return BlockstreamAPI(config)
        elif api_name.lower() == 'mempool':
            return MempoolAPI(config)
        elif api_name.lower() == 'bitcoin_core':
            return BitcoinCoreAPI(config)
        else:
            raise ValueError(f"Unsupported API: {api_name}")

class MultiSourceAPI:
    """Multi-source API wrapper để fallback giữa các nguồn"""
    
    def __init__(self, config: Config):
        self.config = config
        self.apis = {}
        self._initialize_apis()
    
    def _initialize_apis(self):
        """Khởi tạo các API sources"""
        api_sources = self.config.get('api_sources', ['blockstream', 'mempool'])
        
        for api_name in api_sources:
            try:
                self.apis[api_name] = BlockchainAPIFactory.create_api(api_name, self.config)
                logger.info(f"Initialized {api_name} API")
            except Exception as e:
                logger.warning(f"Failed to initialize {api_name} API: {str(e)}")
    
    def fetch_address_transactions(self, address: str, preferred_source: str = None) -> List[Dict]:
        """
        Fetch transactions với fallback giữa các sources
        """
        sources = [preferred_source] if preferred_source else list(self.apis.keys())
        
        for source in sources:
            if source not in self.apis:
                continue
                
            try:
                transactions = self.apis[source].fetch_address_transactions(address)
                if transactions:
                    logger.info(f"Successfully fetched transactions from {source}")
                    return transactions
            except Exception as e:
                logger.warning(f"Failed to fetch from {source}: {str(e)}")
                continue
        
        logger.error(f"Failed to fetch transactions from all sources for {address}")
        return []
    
    def fetch_transaction_details(self, tx_hash: str, preferred_source: str = None) -> Dict:
        """
        Fetch transaction details với fallback
        """
        sources = [preferred_source] if preferred_source else list(self.apis.keys())
        
        for source in sources:
            if source not in self.apis:
                continue
                
            try:
                tx_data = self.apis[source].fetch_transaction_details(tx_hash)
                if tx_data:
                    return tx_data
            except Exception as e:
                logger.warning(f"Failed to fetch transaction details from {source}: {str(e)}")
                continue
        
        return {}
