#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load and Use Trained AI CoinJoin Model
Tái sử dụng model đã được train
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class TrainedCoinJoinModel:
    def __init__(self, model_path: str = None):
        """
        Load trained model từ file JSON
        """
        self.blockstream_api = 'https://blockstream.info/api'
        self.model_data = {}
        self.training_stats = {}
        self.coinjoin_patterns = {}
        
        if model_path:
            self.load_model(model_path)
        else:
            self.load_latest_model()
    
    def load_latest_model(self):
        """Load model mới nhất từ thư mục training_results"""
        results_dir = 'data/training_results'
        if not os.path.exists(results_dir):
            logger.error(f"Thư mục {results_dir} không tồn tại!")
            return
        
        # Tìm file kết quả mới nhất
        result_files = [f for f in os.listdir(results_dir) if f.startswith('advanced_results_')]
        if not result_files:
            logger.error("Không tìm thấy file kết quả training!")
            return
        
        latest_file = max(result_files)
        model_path = os.path.join(results_dir, latest_file)
        self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """Load model từ file cụ thể"""
        try:
            logger.info(f"Loading model từ: {model_path}")
            
            with open(model_path, 'r') as f:
                self.model_data = json.load(f)
            
            # Load thống kê tương ứng
            stats_file = model_path.replace('advanced_results_', 'advanced_stats_')
            if os.path.exists(stats_file):
                with open(stats_file, 'r') as f:
                    self.training_stats = json.load(f)
            
            # Load file CoinJoin patterns
            coinjoin_file = model_path.replace('advanced_results_', 'advanced_coinjoin_')
            if os.path.exists(coinjoin_file):
                with open(coinjoin_file, 'r') as f:
                    coinjoin_data = json.load(f)
                    self.coinjoin_patterns = {tx['txid']: tx for tx in coinjoin_data}
            
            logger.info(f"Model loaded thành công!")
            logger.info(f"  • Total transactions: {len(self.model_data)}")
            logger.info(f"  • CoinJoin patterns: {len(self.coinjoin_patterns)}")
            if self.training_stats:
                logger.info(f"  • Detection rate: {self.training_stats.get('detection_rate', 0):.2%}")
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
    
    def get_transaction_data(self, txid: str) -> Optional[Dict]:
        """Lấy dữ liệu transaction từ API"""
        try:
            url = f"{self.blockstream_api}/tx/{txid}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching tx {txid}: {e}")
            return None
    
    def analyze_coinjoin(self, tx_data: Dict) -> Dict:
        """Phân tích CoinJoin sử dụng thuật toán đã train"""
        input_count = len(tx_data.get('vin', []))
        output_count = len(tx_data.get('vout', []))
        
        # Extract addresses and values
        input_addresses = []
        output_addresses = []
        input_values = []
        output_values = []
        
        for vin in tx_data.get('vin', []):
            if 'prevout' in vin:
                if 'scriptpubkey_address' in vin['prevout']:
                    input_addresses.append(vin['prevout']['scriptpubkey_address'])
                input_values.append(vin['prevout'].get('value', 0))
        
        for vout in tx_data.get('vout', []):
            if 'scriptpubkey_address' in vout:
                output_addresses.append(vout['scriptpubkey_address'])
            output_values.append(vout.get('value', 0))
        
        # Calculate indicators (giống như trong training)
        indicators = {
            'input_count': input_count,
            'output_count': output_count,
            'unique_input_addresses': len(set(input_addresses)),
            'unique_output_addresses': len(set(output_addresses)),
            'output_uniformity': len(set(output_values)),
            'input_diversity': len(set(input_addresses)),
            'transaction_size': input_count + output_count,
            'total_input_value': sum(input_values),
            'total_output_value': sum(output_values),
            'fee': sum(input_values) - sum(output_values)
        }
        
        # Calculate score (sử dụng thuật toán đã train)
        score = 0.0
        reasons = []
        
        if input_count > 5:
            score += 0.15
            reasons.append(f"Many inputs ({input_count})")
        if output_count > 5:
            score += 0.15
            reasons.append(f"Many outputs ({output_count})")
        
        if indicators['output_uniformity'] <= 5:
            score += 0.25
            reasons.append(f"Uniform outputs ({indicators['output_uniformity']} unique values)")
        
        if indicators['input_diversity'] > 3:
            score += 0.20
            reasons.append(f"Diverse inputs ({indicators['input_diversity']} unique addresses)")
        
        if indicators['transaction_size'] > 10:
            score += 0.10
            reasons.append(f"Large transaction ({indicators['transaction_size']} total)")
        
        if indicators['output_uniformity'] <= 3 and len(output_values) > 5:
            score += 0.15
            reasons.append("CoinJoin-like output pattern")
        
        is_coinjoin = score > 0.6
        
        return {
            'is_coinjoin': is_coinjoin,
            'score': min(score, 1.0),
            'reasons': reasons,
            'indicators': indicators,
            'input_addresses': input_addresses,
            'output_addresses': output_addresses,
            'input_values': input_values,
            'output_values': output_values,
            'confidence': 'high' if score > 0.8 else 'medium' if score > 0.6 else 'low'
        }
    
    def predict_coinjoin(self, txid: str) -> Dict:
        """Dự đoán một transaction có phải CoinJoin không"""
        logger.info(f"Analyzing transaction: {txid}")
        
        # Kiểm tra xem transaction này đã có trong training data chưa
        if txid in self.coinjoin_patterns:
            logger.info(f"Transaction {txid} found in training data!")
            return {
                'txid': txid,
                'is_coinjoin': True,
                'score': 1.0,
                'source': 'training_data',
                'confidence': 'high',
                'training_info': self.coinjoin_patterns[txid]
            }
        
        # Lấy dữ liệu transaction từ API
        tx_data = self.get_transaction_data(txid)
        if not tx_data:
            return {
                'txid': txid,
                'error': 'Could not fetch transaction data',
                'is_coinjoin': False,
                'score': 0.0
            }
        
        # Phân tích sử dụng model đã train
        analysis = self.analyze_coinjoin(tx_data)
        
        result = {
            'txid': txid,
            'is_coinjoin': analysis['is_coinjoin'],
            'score': analysis['score'],
            'reasons': analysis['reasons'],
            'indicators': analysis['indicators'],
            'confidence': analysis['confidence'],
            'source': 'model_prediction',
            'timestamp': datetime.now().isoformat()
        }
        
        return result
    
    def batch_predict(self, txids: List[str]) -> List[Dict]:
        """Dự đoán hàng loạt transactions"""
        logger.info(f"Batch predicting {len(txids)} transactions...")
        
        results = []
        for i, txid in enumerate(txids):
            try:
                result = self.predict_coinjoin(txid)
                results.append(result)
                
                # Progress update
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(txids)} transactions")
                
                # Rate limiting
                import time
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error predicting {txid}: {e}")
                results.append({
                    'txid': txid,
                    'error': str(e),
                    'is_coinjoin': False,
                    'score': 0.0
                })
        
        return results
    
    def get_model_info(self) -> Dict:
        """Lấy thông tin về model"""
        return {
            'model_data_count': len(self.model_data),
            'coinjoin_patterns_count': len(self.coinjoin_patterns),
            'training_stats': self.training_stats,
            'model_features': [
                'input_count', 'output_count', 'input_diversity',
                'output_uniformity', 'transaction_size', 'fee'
            ],
            'threshold': 0.6,
            'confidence_levels': {
                'high': 'score > 0.8',
                'medium': '0.6 < score <= 0.8',
                'low': 'score <= 0.6'
            }
        }
    
    def save_predictions(self, predictions: List[Dict], filename: str = None):
        """Lưu kết quả dự đoán"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'data/predictions_{timestamp}.json'
        
        os.makedirs('data', exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(predictions, f, indent=2)
        
        logger.info(f"Predictions saved to: {filename}")
        
        # Print summary
        coinjoin_count = sum(1 for p in predictions if p.get('is_coinjoin', False))
        total_count = len(predictions)
        
        logger.info(f"Prediction Summary:")
        logger.info(f"  • Total transactions: {total_count}")
        logger.info(f"  • CoinJoin detected: {coinjoin_count}")
        logger.info(f"  • Detection rate: {coinjoin_count/total_count:.2%}")

def main():
    print("=" * 60)
    print("LOAD AND USE TRAINED AI COINJOIN MODEL")
    print("=" * 60)
    
    # Load model
    model = TrainedCoinJoinModel()
    
    if not model.model_data:
        print("❌ Không thể load model!")
        return
    
    # Hiển thị thông tin model
    model_info = model.get_model_info()
    print(f"\n📊 Model Information:")
    print(f"  • Training data: {model_info['model_data_count']} transactions")
    print(f"  • CoinJoin patterns: {model_info['coinjoin_patterns_count']}")
    print(f"  • Detection threshold: {model_info['threshold']}")
    
    # Test với một số transactions
    test_txids = [
        "9701e6e66b33b22dd1cb9cd568a831f612768b6ab10f5a179086bebaf1c413cd",
        "277c7fd9618efa76141235dfb458289a6d989f526384341ca03fa26732711e30",
        "634660b011f02ee0479e309ff2182dd7e84e82cb78980cd6b8be732e1bc20961"
    ]
    
    print(f"\n🔍 Testing model với {len(test_txids)} transactions...")
    
    predictions = model.batch_predict(test_txids)
    
    # Hiển thị kết quả
    print(f"\n📈 Prediction Results:")
    for pred in predictions:
        status = "✅ COINJOIN" if pred.get('is_coinjoin') else "❌ NORMAL"
        score = pred.get('score', 0)
        confidence = pred.get('confidence', 'unknown')
        print(f"  • {pred['txid'][:16]}... - {status} (Score: {score:.2f}, Confidence: {confidence})")
    
    # Lưu kết quả
    model.save_predictions(predictions)
    
    print(f"\n✅ Model ready to use!")
    print(f"💡 Sử dụng: model.predict_coinjoin('txid')")

if __name__ == "__main__":
    main()
