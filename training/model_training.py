#!/usr/bin/env python3
"""
Model Training Script for CoinJoin Detection
Train các model khác nhau để phát hiện CoinJoin
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import logging
import argparse
from typing import Dict, List, Tuple, Any
import yaml
from datetime import datetime

# ML imports
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import lightgbm as lgb

# Deep Learning imports
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow not available, skipping neural network training")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoinJoinModelTrainer:
    """Trainer cho các model phát hiện CoinJoin"""
    
    def __init__(self, data_dir: str, model_dir: str, config_path: str = None):
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Load config
        if config_path:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self._get_default_config()
        
        # Load data
        self.X_train, self.X_test, self.y_train, self.y_test = self._load_data()
        self.feature_names = self._load_feature_names()
        
        # Initialize models
        self.models = {}
        self.results = {}
        
    def _get_default_config(self) -> Dict:
        """Config mặc định cho training"""
        return {
            'test_size': 0.2,
            'random_state': 42,
            'cv_folds': 5,
            'models': {
                'random_forest': {
                    'n_estimators': 100,
                    'max_depth': 10,
                    'random_state': 42
                },
                'xgboost': {
                    'n_estimators': 100,
                    'max_depth': 6,
                    'learning_rate': 0.1,
                    'random_state': 42
                },
                'lightgbm': {
                    'n_estimators': 100,
                    'max_depth': 6,
                    'learning_rate': 0.1,
                    'random_state': 42
                },
                'logistic_regression': {
                    'C': 1.0,
                    'random_state': 42
                }
            }
        }
    
    def _load_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Load dữ liệu training"""
        logger.info("Loading training data...")
        
        # Load processed data
        X = np.load(self.data_dir / 'processed' / 'X_train.npy')
        y = np.load(self.data_dir / 'processed' / 'y_train.npy')
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=self.config['test_size'],
            random_state=self.config['random_state'],
            stratify=y
        )
        
        logger.info(f"Training set: {X_train.shape}")
        logger.info(f"Test set: {X_test.shape}")
        logger.info(f"Positive samples in train: {np.sum(y_train == 1)}")
        logger.info(f"Positive samples in test: {np.sum(y_test == 1)}")
        
        return X_train, X_test, y_train, y_test
    
    def _load_feature_names(self) -> List[str]:
        """Load tên các features"""
        with open(self.data_dir / 'processed' / 'feature_names.pkl', 'rb') as f:
            return pickle.load(f)
    
    def train_random_forest(self) -> RandomForestClassifier:
        """Train Random Forest model"""
        logger.info("Training Random Forest...")
        
        rf_config = self.config['models']['random_forest']
        rf = RandomForestClassifier(**rf_config)
        
        # Cross validation
        cv_scores = cross_val_score(rf, self.X_train, self.y_train, cv=self.config['cv_folds'])
        logger.info(f"CV scores: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        # Train on full training set
        rf.fit(self.X_train, self.y_train)
        
        # Evaluate
        y_pred = rf.predict(self.X_test)
        y_pred_proba = rf.predict_proba(self.X_test)[:, 1]
        
        self._evaluate_model('random_forest', rf, y_pred, y_pred_proba)
        
        return rf
    
    def train_xgboost(self) -> xgb.XGBClassifier:
        """Train XGBoost model"""
        logger.info("Training XGBoost...")
        
        xgb_config = self.config['models']['xgboost']
        xgb_model = xgb.XGBClassifier(**xgb_config)
        
        # Cross validation
        cv_scores = cross_val_score(xgb_model, self.X_train, self.y_train, cv=self.config['cv_folds'])
        logger.info(f"CV scores: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        # Train on full training set
        xgb_model.fit(self.X_train, self.y_train)
        
        # Evaluate
        y_pred = xgb_model.predict(self.X_test)
        y_pred_proba = xgb_model.predict_proba(self.X_test)[:, 1]
        
        self._evaluate_model('xgboost', xgb_model, y_pred, y_pred_proba)
        
        return xgb_model
    
    def train_lightgbm(self) -> lgb.LGBMClassifier:
        """Train LightGBM model"""
        logger.info("Training LightGBM...")
        
        lgb_config = self.config['models']['lightgbm']
        lgb_model = lgb.LGBMClassifier(**lgb_config)
        
        # Cross validation
        cv_scores = cross_val_score(lgb_model, self.X_train, self.y_train, cv=self.config['cv_folds'])
        logger.info(f"CV scores: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        # Train on full training set
        lgb_model.fit(self.X_train, self.y_train)
        
        # Evaluate
        y_pred = lgb_model.predict(self.X_test)
        y_pred_proba = lgb_model.predict_proba(self.X_test)[:, 1]
        
        self._evaluate_model('lightgbm', lgb_model, y_pred, y_pred_proba)
        
        return lgb_model
    
    def train_logistic_regression(self) -> LogisticRegression:
        """Train Logistic Regression model"""
        logger.info("Training Logistic Regression...")
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(self.X_train)
        X_test_scaled = scaler.transform(self.X_test)
        
        lr_config = self.config['models']['logistic_regression']
        lr = LogisticRegression(**lr_config)
        
        # Cross validation
        cv_scores = cross_val_score(lr, X_train_scaled, self.y_train, cv=self.config['cv_folds'])
        logger.info(f"CV scores: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        # Train on full training set
        lr.fit(X_train_scaled, self.y_train)
        
        # Evaluate
        y_pred = lr.predict(X_test_scaled)
        y_pred_proba = lr.predict_proba(X_test_scaled)[:, 1]
        
        self._evaluate_model('logistic_regression', lr, y_pred, y_pred_proba, scaler=scaler)
        
        return lr
    
    def train_neural_network(self) -> keras.Model:
        """Train Neural Network model"""
        if not TENSORFLOW_AVAILABLE:
            logger.warning("TensorFlow not available, skipping neural network")
            return None
        
        logger.info("Training Neural Network...")
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(self.X_train)
        X_test_scaled = scaler.transform(self.X_test)
        
        # Build model
        model = keras.Sequential([
            layers.Dense(128, activation='relu', input_shape=(X_train_scaled.shape[1],)),
            layers.Dropout(0.3),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(32, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy', 'precision', 'recall']
        )
        
        # Train
        history = model.fit(
            X_train_scaled, self.y_train,
            validation_split=0.2,
            epochs=50,
            batch_size=32,
            verbose=1
        )
        
        # Evaluate
        y_pred_proba = model.predict(X_test_scaled).flatten()
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        self._evaluate_model('neural_network', model, y_pred, y_pred_proba, scaler=scaler)
        
        return model
    
    def _evaluate_model(self, model_name: str, model: Any, y_pred: np.ndarray, 
                       y_pred_proba: np.ndarray, scaler: Any = None):
        """Đánh giá model"""
        logger.info(f"Evaluating {model_name}...")
        
        # Calculate metrics
        report = classification_report(self.y_test, y_pred, output_dict=True)
        auc_score = roc_auc_score(self.y_test, y_pred_proba)
        
        # Store results
        self.results[model_name] = {
            'precision': report['1']['precision'],
            'recall': report['1']['recall'],
            'f1_score': report['1']['f1-score'],
            'accuracy': report['accuracy'],
            'auc': auc_score,
            'confusion_matrix': confusion_matrix(self.y_test, y_pred).tolist()
        }
        
        logger.info(f"{model_name} - Precision: {report['1']['precision']:.3f}")
        logger.info(f"{model_name} - Recall: {report['1']['recall']:.3f}")
        logger.info(f"{model_name} - F1-Score: {report['1']['f1-score']:.3f}")
        logger.info(f"{model_name} - AUC: {auc_score:.3f}")
        
        # Store model
        self.models[model_name] = {
            'model': model,
            'scaler': scaler,
            'feature_names': self.feature_names
        }
    
    def train_all_models(self):
        """Train tất cả các model"""
        logger.info("Starting training of all models...")
        
        # Train traditional ML models
        self.models['random_forest'] = self.train_random_forest()
        self.models['xgboost'] = self.train_xgboost()
        self.models['lightgbm'] = self.train_lightgbm()
        self.models['logistic_regression'] = self.train_logistic_regression()
        
        # Train neural network if available
        if TENSORFLOW_AVAILABLE:
            self.models['neural_network'] = self.train_neural_network()
        
        # Save models and results
        self._save_models()
        self._save_results()
        
        # Print summary
        self._print_summary()
    
    def _save_models(self):
        """Lưu các model đã train"""
        logger.info("Saving models...")
        
        for model_name, model_data in self.models.items():
            model_path = self.model_dir / model_name
            model_path.mkdir(exist_ok=True)
            
            # Save model
            if model_name == 'neural_network':
                model_data['model'].save(model_path / 'model.h5')
            else:
                with open(model_path / 'model.pkl', 'wb') as f:
                    pickle.dump(model_data['model'], f)
            
            # Save scaler if exists
            if model_data.get('scaler'):
                with open(model_path / 'scaler.pkl', 'wb') as f:
                    pickle.dump(model_data['scaler'], f)
            
            # Save feature names
            with open(model_path / 'feature_names.pkl', 'wb') as f:
                pickle.dump(model_data['feature_names'], f)
            
            # Save metadata
            metadata = {
                'model_name': model_name,
                'training_date': datetime.now().isoformat(),
                'feature_count': len(model_data['feature_names']),
                'has_scaler': model_data.get('scaler') is not None
            }
            
            with open(model_path / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)
    
    def _save_results(self):
        """Lưu kết quả đánh giá"""
        logger.info("Saving evaluation results...")
        
        results_path = self.model_dir / 'evaluation_results.json'
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Create summary table
        summary_data = []
        for model_name, metrics in self.results.items():
            summary_data.append({
                'Model': model_name,
                'Precision': f"{metrics['precision']:.3f}",
                'Recall': f"{metrics['recall']:.3f}",
                'F1-Score': f"{metrics['f1_score']:.3f}",
                'Accuracy': f"{metrics['accuracy']:.3f}",
                'AUC': f"{metrics['auc']:.3f}"
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_path = self.model_dir / 'model_comparison.csv'
        summary_df.to_csv(summary_path, index=False)
        
        logger.info(f"Results saved to {results_path}")
        logger.info(f"Summary saved to {summary_path}")
    
    def _print_summary(self):
        """In tóm tắt kết quả"""
        logger.info("\n" + "="*50)
        logger.info("TRAINING SUMMARY")
        logger.info("="*50)
        
        for model_name, metrics in self.results.items():
            logger.info(f"\n{model_name.upper()}:")
            logger.info(f"  Precision: {metrics['precision']:.3f}")
            logger.info(f"  Recall: {metrics['recall']:.3f}")
            logger.info(f"  F1-Score: {metrics['f1_score']:.3f}")
            logger.info(f"  AUC: {metrics['auc']:.3f}")
        
        # Find best model
        best_model = max(self.results.items(), key=lambda x: x[1]['f1_score'])
        logger.info(f"\nBEST MODEL: {best_model[0]} (F1: {best_model[1]['f1_score']:.3f})")

def main():
    parser = argparse.ArgumentParser(description='Train CoinJoin detection models')
    parser.add_argument('--data-dir', default='data', help='Thư mục chứa dữ liệu')
    parser.add_argument('--model-dir', default='models', help='Thư mục lưu model')
    parser.add_argument('--config', help='File config training')
    
    args = parser.parse_args()
    
    # Khởi tạo trainer
    trainer = CoinJoinModelTrainer(args.data_dir, args.model_dir, args.config)
    
    # Train tất cả models
    trainer.train_all_models()
    
    logger.info("Training completed!")

if __name__ == '__main__':
    main()
