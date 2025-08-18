#!/usr/bin/env python3
"""
CoinJoin Predictor - Inference Script
Sử dụng model đã train để dự đoán CoinJoin
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional, Any
import argparse
from datetime import datetime

# Django imports
import sys
sys.path.append('../blockchain')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blockchain.settings')
import django
django.setup()

from bitcoin.models import Transaction, TxInput, TxOutput, Address
from django.db.models import Q

# ML imports
from sklearn.preprocessing import StandardScaler
try:
    import tensorflow as tf
    from tensorflow import keras
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoinJoinPredictor:
    """Predictor cho CoinJoin detection"""
    
    def __init__(self, model_dir: str, model_name: str = 'xgboost'):
        self.model_dir = Path(model_dir)
        self.model_name = model_name
        self.model_path = self.model_dir / model_name
        
        # Load model và metadata
        self.model = self._load_model()
        self.scaler = self._load_scaler()
        self.feature_names = self._load_feature_names()
        self.metadata = self._load_metadata()
        
        logger.info(f"Loaded {model_name} model with {len(self.feature_names)} features")
    
    def _load_model(self) -> Any:
        """Load model từ file"""
        if self.model_name == 'neural_network':
            if not TENSORFLOW_AVAILABLE:
                raise ImportError("TensorFlow required for neural network model")
            return keras.models.load_model(self.model_path / 'model.h5')
        else:
            with open(self.model_path / 'model.pkl', 'rb') as f:
                return pickle.load(f)
    
    def _load_scaler(self) -> Optional[StandardScaler]:
        """Load scaler nếu có"""
        scaler_path = self.model_path / 'scaler.pkl'
        if scaler_path.exists():
            with open(scaler_path, 'rb') as f:
                return pickle.load(f)
        return None
    
    def _load_feature_names(self) -> List[str]:
        """Load tên các features"""
        with open(self.model_path / 'feature_names.pkl', 'rb') as f:
            return pickle.load(f)
    
    def _load_metadata(self) -> Dict:
        """Load metadata của model"""
        with open(self.model_path / 'metadata.json', 'r') as f:
            return json.load(f)
    
    def extract_features(self, tx: Transaction) -> np.ndarray:
        """Trích xuất features từ transaction"""
        inputs = list(tx.inputs.all())
        outputs = list(tx.outputs.all())
        
        # Basic features
        features = {
            'input_count': len(inputs),
            'output_count': len(outputs),
            'total_input_value': sum(inp.value for inp in inputs),
            'total_output_value': sum(out.value for out in outputs),
            'fee': float(tx.fee) if tx.fee else 0,
            'fee_per_byte': float(tx.fee) / tx.size if tx.size > 0 else 0,
            'tx_size': tx.size,
            'anomaly_score': float(tx.anomaly_score) if tx.anomaly_score else 0,
        }
        
        # Value distribution features
        output_values = [float(out.value) for out in outputs]
        input_values = [float(inp.value) for inp in inputs]
        
        if output_values:
            features.update({
                'output_mean': np.mean(output_values),
                'output_std': np.std(output_values),
                'output_cv': np.std(output_values) / np.mean(output_values) if np.mean(output_values) > 0 else 0,
                'output_variance': np.var(output_values),
                'output_uniformity': 1.0 - (np.var(output_values) / (np.mean(output_values) ** 2)) if np.mean(output_values) > 0 else 0,
                'output_min': min(output_values),
                'output_max': max(output_values),
                'output_range': max(output_values) - min(output_values),
            })
            
            # Percentile features
            percentiles = [25, 50, 75, 90, 95]
            output_percentiles = np.percentile(output_values, percentiles)
            for i, p in enumerate(percentiles):
                features[f'output_percentiles_{p}'] = output_percentiles[i]
        else:
            # Default values if no outputs
            for p in [25, 50, 75, 90, 95]:
                features[f'output_percentiles_{p}'] = 0
            features.update({
                'output_mean': 0, 'output_std': 0, 'output_cv': 0,
                'output_variance': 0, 'output_uniformity': 0,
                'output_min': 0, 'output_max': 0, 'output_range': 0
            })
        
        # Input features
        if input_values:
            features.update({
                'input_mean': np.mean(input_values),
                'input_std': np.std(input_values),
                'input_variance': np.var(input_values),
            })
        else:
            features.update({
                'input_mean': 0, 'input_std': 0, 'input_variance': 0
            })
        
        # Address features
        input_addresses = [inp.address.address if inp.address else None for inp in inputs]
        output_addresses = [out.address.address if out.address else None for out in outputs]
        
        features.update({
            'unique_input_addresses': len(set(input_addresses) - {None}),
            'unique_output_addresses': len(set(output_addresses) - {None}),
            'input_address_diversity': len(set(input_addresses) - {None}) / len(input_values) if input_values else 0,
            'output_address_diversity': len(set(output_addresses) - {None}) / len(output_values) if output_values else 0,
        })
        
        # Convert to feature vector
        feature_vector = []
        for feature_name in self.feature_names:
            feature_vector.append(features.get(feature_name, 0))
        
        return np.array(feature_vector).reshape(1, -1)
    
    def predict(self, tx: Transaction) -> Dict:
        """Dự đoán CoinJoin cho một transaction"""
        try:
            # Extract features
            features = self.extract_features(tx)
            
            # Scale features if needed
            if self.scaler:
                features = self.scaler.transform(features)
            
            # Make prediction
            if self.model_name == 'neural_network':
                prediction_proba = self.model.predict(features)[0][0]
            else:
                prediction_proba = self.model.predict_proba(features)[0][1]
            
            prediction = 1 if prediction_proba > 0.5 else 0
            
            return {
                'tx_hash': tx.hash,
                'prediction': prediction,
                'confidence': prediction_proba,
                'is_coinjoin': bool(prediction),
                'model_name': self.model_name,
                'prediction_time': datetime.now().isoformat(),
                'features_used': len(self.feature_names)
            }
            
        except Exception as e:
            logger.error(f"Error predicting for tx {tx.hash}: {str(e)}")
            return {
                'tx_hash': tx.hash,
                'prediction': 0,
                'confidence': 0.0,
                'is_coinjoin': False,
                'error': str(e),
                'model_name': self.model_name,
                'prediction_time': datetime.now().isoformat()
            }
    
    def predict_batch(self, transactions: List[Transaction]) -> List[Dict]:
        """Dự đoán hàng loạt"""
        logger.info(f"Predicting {len(transactions)} transactions...")
        
        results = []
        for i, tx in enumerate(transactions):
            if i % 100 == 0:
                logger.info(f"Processed {i}/{len(transactions)} transactions")
            
            result = self.predict(tx)
            results.append(result)
        
        return results
    
    def evaluate_on_database(self, limit: int = 1000) -> Dict:
        """Đánh giá model trên database"""
        logger.info(f"Evaluating model on {limit} transactions...")
        
        # Lấy transactions có tag coinjoin
        coinjoin_txs = Transaction.objects.filter(
            tags__icontains='coinjoin'
        ).prefetch_related('inputs', 'outputs')[:limit//2]
        
        # Lấy transactions không có tag coinjoin
        non_coinjoin_txs = Transaction.objects.filter(
            ~Q(tags__icontains='coinjoin')
        ).prefetch_related('inputs', 'outputs')[:limit//2]
        
        # Combine và predict
        all_txs = list(coinjoin_txs) + list(non_coinjoin_txs)
        predictions = self.predict_batch(all_txs)
        
        # Calculate metrics
        true_labels = []
        pred_labels = []
        confidences = []
        
        for i, tx in enumerate(all_txs):
            true_label = 1 if 'coinjoin' in (tx.tags or '') else 0
            pred = predictions[i]
            
            true_labels.append(true_label)
            pred_labels.append(pred['prediction'])
            confidences.append(pred['confidence'])
        
        # Calculate metrics
        from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
        
        precision = precision_score(true_labels, pred_labels)
        recall = recall_score(true_labels, pred_labels)
        f1 = f1_score(true_labels, pred_labels)
        accuracy = accuracy_score(true_labels, pred_labels)
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'accuracy': accuracy,
            'total_transactions': len(all_txs),
            'coinjoin_transactions': len(coinjoin_txs),
            'non_coinjoin_transactions': len(non_coinjoin_txs),
            'model_name': self.model_name,
            'evaluation_time': datetime.now().isoformat()
        }

class RealTimeCoinJoinDetector:
    """Real-time CoinJoin detector với ZMQ integration"""
    
    def __init__(self, model_dir: str, model_name: str = 'xgboost'):
        self.predictor = CoinJoinPredictor(model_dir, model_name)
        self.detected_coinjoins = []
        
    def process_new_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Xử lý transaction mới từ ZMQ"""
        try:
            # Lấy transaction từ database
            tx = Transaction.objects.get(hash=tx_hash)
            
            # Predict
            result = self.predictor.predict(tx)
            
            # Nếu là CoinJoin, thêm vào danh sách
            if result['is_coinjoin']:
                self.detected_coinjoins.append(result)
                logger.info(f"Detected CoinJoin: {tx_hash} (confidence: {result['confidence']:.3f})")
            
            return result
            
        except Transaction.DoesNotExist:
            logger.warning(f"Transaction {tx_hash} not found in database")
            return None
        except Exception as e:
            logger.error(f"Error processing transaction {tx_hash}: {str(e)}")
            return None
    
    def get_recent_detections(self, limit: int = 10) -> List[Dict]:
        """Lấy các phát hiện gần đây"""
        return self.detected_coinjoins[-limit:]
    
    def get_statistics(self) -> Dict:
        """Thống kê phát hiện"""
        if not self.detected_coinjoins:
            return {'total_detections': 0}
        
        confidences = [d['confidence'] for d in self.detected_coinjoins]
        return {
            'total_detections': len(self.detected_coinjoins),
            'avg_confidence': np.mean(confidences),
            'min_confidence': np.min(confidences),
            'max_confidence': np.max(confidences),
            'last_detection': self.detected_coinjoins[-1]['prediction_time']
        }

def main():
    parser = argparse.ArgumentParser(description='CoinJoin Prediction')
    parser.add_argument('--model-dir', default='models', help='Thư mục chứa model')
    parser.add_argument('--model-name', default='xgboost', help='Tên model sử dụng')
    parser.add_argument('--tx-hash', help='Hash của transaction cần predict')
    parser.add_argument('--evaluate', action='store_true', help='Đánh giá model trên database')
    parser.add_argument('--limit', type=int, default=1000, help='Số lượng transactions để evaluate')
    
    args = parser.parse_args()
    
    # Khởi tạo predictor
    predictor = CoinJoinPredictor(args.model_dir, args.model_name)
    
    if args.tx_hash:
        # Predict single transaction
        try:
            tx = Transaction.objects.get(hash=args.tx_hash)
            result = predictor.predict(tx)
            print(json.dumps(result, indent=2))
        except Transaction.DoesNotExist:
            print(f"Transaction {args.tx_hash} not found")
    
    elif args.evaluate:
        # Evaluate model
        results = predictor.evaluate_on_database(args.limit)
        print(json.dumps(results, indent=2))
    
    else:
        print("Please specify --tx-hash or --evaluate")

if __name__ == '__main__':
    main()
