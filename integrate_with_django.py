#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django Integration for Trained AI Model
Tích hợp model đã train vào hệ thống Django
"""

import os
import sys
import django
from pathlib import Path

# Add Django project to path
django_project_path = Path(__file__).parent.parent
sys.path.append(str(django_project_path))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blockchain.settings')
django.setup()

from load_trained_model import TrainedCoinJoinModel
from blockchain.bitcoin.models import Transaction, Address
import json
from datetime import datetime

class DjangoCoinJoinAnalyzer:
    def __init__(self):
        """Initialize AI model for Django integration"""
        self.model = TrainedCoinJoinModel()
        if not self.model.model_data:
            raise Exception("Không thể load AI model!")
        
        print(f"✅ AI Model loaded: {len(self.model.model_data)} training samples")
    
    def analyze_transaction_from_db(self, tx_hash: str) -> dict:
        """Phân tích transaction từ database Django"""
        try:
            # Tìm transaction trong database
            tx = Transaction.objects.filter(txid=tx_hash).first()
            if not tx:
                return {
                    'txid': tx_hash,
                    'error': 'Transaction not found in database',
                    'is_coinjoin': False,
                    'score': 0.0
                }
            
            # Sử dụng AI model để phân tích
            result = self.model.predict_coinjoin(tx_hash)
            
            # Thêm thông tin từ database
            result['db_info'] = {
                'block_height': tx.block_height,
                'timestamp': tx.timestamp.isoformat() if tx.timestamp else None,
                'fee': tx.fee,
                'size': tx.size
            }
            
            return result
            
        except Exception as e:
            return {
                'txid': tx_hash,
                'error': str(e),
                'is_coinjoin': False,
                'score': 0.0
            }
    
    def analyze_address_transactions(self, address: str, limit: int = 10) -> dict:
        """Phân tích tất cả transactions của một address"""
        try:
            # Tìm address trong database
            addr = Address.objects.filter(address=address).first()
            if not addr:
                return {
                    'address': address,
                    'error': 'Address not found in database',
                    'transactions': []
                }
            
            # Lấy transactions của address
            transactions = addr.transactions.all()[:limit]
            
            results = []
            coinjoin_count = 0
            
            for tx in transactions:
                result = self.analyze_transaction_from_db(tx.txid)
                results.append(result)
                
                if result.get('is_coinjoin', False):
                    coinjoin_count += 1
            
            return {
                'address': address,
                'total_transactions': len(results),
                'coinjoin_transactions': coinjoin_count,
                'coinjoin_rate': coinjoin_count / len(results) if results else 0,
                'transactions': results
            }
            
        except Exception as e:
            return {
                'address': address,
                'error': str(e),
                'transactions': []
            }
    
    def batch_analyze_transactions(self, tx_hashes: list) -> dict:
        """Phân tích hàng loạt transactions"""
        results = []
        coinjoin_count = 0
        
        for tx_hash in tx_hashes:
            result = self.analyze_transaction_from_db(tx_hash)
            results.append(result)
            
            if result.get('is_coinjoin', False):
                coinjoin_count += 1
        
        return {
            'total_transactions': len(results),
            'coinjoin_transactions': coinjoin_count,
            'coinjoin_rate': coinjoin_count / len(results) if results else 0,
            'results': results
        }
    
    def save_analysis_to_db(self, analysis_result: dict, analysis_type: str = 'ai_analysis'):
        """Lưu kết quả phân tích vào database (có thể mở rộng)"""
        timestamp = datetime.now()
        
        # Tạo file log
        log_data = {
            'analysis_type': analysis_type,
            'timestamp': timestamp.isoformat(),
            'model_info': self.model.get_model_info(),
            'result': analysis_result
        }
        
        # Lưu vào file
        os.makedirs('data/django_analysis', exist_ok=True)
        filename = f'data/django_analysis/{analysis_type}_{timestamp.strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(filename, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"Analysis saved to: {filename}")
        return filename
    
    def get_model_performance_stats(self) -> dict:
        """Lấy thống kê hiệu suất model"""
        model_info = self.model.get_model_info()
        
        # Có thể thêm thống kê từ database
        total_txs_in_db = Transaction.objects.count()
        total_addresses_in_db = Address.objects.count()
        
        return {
            'model_info': model_info,
            'database_stats': {
                'total_transactions': total_txs_in_db,
                'total_addresses': total_addresses_in_db
            },
            'integration_status': 'active'
        }

def main():
    print("🔗 DJANGO AI MODEL INTEGRATION")
    print("=" * 50)
    
    try:
        # Initialize analyzer
        analyzer = DjangoCoinJoinAnalyzer()
        
        print("✅ Django integration ready!")
        
        # Test với một số transactions từ database
        print("\n🔍 Testing with database transactions...")
        
        # Lấy 5 transactions đầu tiên từ database
        sample_txs = Transaction.objects.all()[:5]
        
        if sample_txs:
            tx_hashes = [tx.txid for tx in sample_txs]
            print(f"Found {len(tx_hashes)} transactions in database")
            
            # Phân tích
            results = analyzer.batch_analyze_transactions(tx_hashes)
            
            print(f"\n📊 ANALYSIS RESULTS:")
            print(f"Total transactions: {results['total_transactions']}")
            print(f"CoinJoin detected: {results['coinjoin_transactions']}")
            print(f"Detection rate: {results['coinjoin_rate']:.2%}")
            
            # Lưu kết quả
            analyzer.save_analysis_to_db(results, 'django_integration_test')
            
        else:
            print("❌ No transactions found in database")
        
        # Hiển thị thống kê
        stats = analyzer.get_model_performance_stats()
        print(f"\n📈 PERFORMANCE STATS:")
        print(f"Database transactions: {stats['database_stats']['total_transactions']}")
        print(f"Database addresses: {stats['database_stats']['total_addresses']}")
        print(f"Model training data: {stats['model_info']['model_data_count']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
