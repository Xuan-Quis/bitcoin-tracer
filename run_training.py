#!/usr/bin/env python3
"""
Main Training Pipeline for CoinJoin Detection AI
Chạy toàn bộ pipeline từ data preparation đến model training
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import subprocess
import time
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training_pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CoinJoinTrainingPipeline:
    """Pipeline chính cho training CoinJoin detection AI"""
    
    def __init__(self, base_dir: str = '.'):
        self.base_dir = Path(base_dir)
        self.ai_dir = self.base_dir / 'AI'
        self.data_dir = self.ai_dir / 'data'
        self.models_dir = self.ai_dir / 'models'
        
        # Tạo thư mục cần thiết
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Pipeline initialized in {self.base_dir}")
        logger.info(f"AI directory: {self.ai_dir}")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Models directory: {self.models_dir}")
    
    def step1_data_preparation(self, balance_ratio: float = 0.5, sample_size: int = 1000):
        """Bước 1: Chuẩn bị dữ liệu"""
        logger.info("="*50)
        logger.info("STEP 1: DATA PREPARATION")
        logger.info("="*50)
        
        start_time = time.time()
        
        try:
            # Chạy script data preparation
            cmd = [
                sys.executable,
                str(self.ai_dir / 'training' / 'data_preparation.py'),
                '--output-dir', str(self.data_dir),
                '--balance-ratio', str(balance_ratio),
                '--sample-size', str(sample_size)
            ]
            
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_dir)
            
            if result.returncode == 0:
                logger.info("Data preparation completed successfully!")
                logger.info(f"Output: {result.stdout}")
            else:
                logger.error(f"Data preparation failed!")
                logger.error(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error in data preparation: {str(e)}")
            return False
        
        elapsed_time = time.time() - start_time
        logger.info(f"Data preparation took {elapsed_time:.2f} seconds")
        return True
    
    def step2_model_training(self, config_path: str = None):
        """Bước 2: Training model"""
        logger.info("="*50)
        logger.info("STEP 2: MODEL TRAINING")
        logger.info("="*50)
        
        start_time = time.time()
        
        try:
            # Chạy script model training
            cmd = [
                sys.executable,
                str(self.ai_dir / 'training' / 'model_training.py'),
                '--data-dir', str(self.data_dir),
                '--model-dir', str(self.models_dir)
            ]
            
            if config_path:
                cmd.extend(['--config', config_path])
            
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_dir)
            
            if result.returncode == 0:
                logger.info("Model training completed successfully!")
                logger.info(f"Output: {result.stdout}")
            else:
                logger.error(f"Model training failed!")
                logger.error(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error in model training: {str(e)}")
            return False
        
        elapsed_time = time.time() - start_time
        logger.info(f"Model training took {elapsed_time:.2f} seconds")
        return True
    
    def step3_model_evaluation(self, model_name: str = 'xgboost'):
        """Bước 3: Đánh giá model"""
        logger.info("="*50)
        logger.info("STEP 3: MODEL EVALUATION")
        logger.info("="*50)
        
        start_time = time.time()
        
        try:
            # Chạy script evaluation
            cmd = [
                sys.executable,
                str(self.ai_dir / 'inference' / 'coinjoin_predictor.py'),
                '--model-dir', str(self.models_dir),
                '--model-name', model_name,
                '--evaluate',
                '--limit', '500'
            ]
            
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_dir)
            
            if result.returncode == 0:
                logger.info("Model evaluation completed successfully!")
                logger.info(f"Results: {result.stdout}")
            else:
                logger.error(f"Model evaluation failed!")
                logger.error(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error in model evaluation: {str(e)}")
            return False
        
        elapsed_time = time.time() - start_time
        logger.info(f"Model evaluation took {elapsed_time:.2f} seconds")
        return True
    
    def step4_generate_report(self):
        """Bước 4: Tạo báo cáo"""
        logger.info("="*50)
        logger.info("STEP 4: GENERATE REPORT")
        logger.info("="*50)
        
        try:
            # Tạo báo cáo tổng hợp
            report_path = self.models_dir / 'training_report.md'
            
            with open(report_path, 'w') as f:
                f.write("# CoinJoin Detection AI Training Report\n\n")
                f.write(f"**Training Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Model comparison
                comparison_path = self.models_dir / 'model_comparison.csv'
                if comparison_path.exists():
                    f.write("## Model Performance Comparison\n\n")
                    f.write("| Model | Precision | Recall | F1-Score | Accuracy | AUC |\n")
                    f.write("|-------|-----------|--------|----------|----------|-----|\n")
                    
                    import pandas as pd
                    df = pd.read_csv(comparison_path)
                    for _, row in df.iterrows():
                        f.write(f"| {row['Model']} | {row['Precision']} | {row['Recall']} | {row['F1-Score']} | {row['Accuracy']} | {row['AUC']} |\n")
                    f.write("\n")
                
                # Training summary
                f.write("## Training Summary\n\n")
                f.write("- **Data Source**: Heuristic-labeled transactions from Django database\n")
                f.write("- **Features**: Transaction, statistical, and address-based features\n")
                f.write("- **Models**: Random Forest, XGBoost, LightGBM, Logistic Regression, Neural Network\n")
                f.write("- **Evaluation**: Cross-validation with F1-score optimization\n\n")
                
                # Usage instructions
                f.write("## Usage Instructions\n\n")
                f.write("### 1. Single Transaction Prediction\n")
                f.write("```bash\n")
                f.write("python AI/inference/coinjoin_predictor.py --model-dir AI/models --model-name xgboost --tx-hash <tx_hash>\n")
                f.write("```\n\n")
                
                f.write("### 2. Batch Evaluation\n")
                f.write("```bash\n")
                f.write("python AI/inference/coinjoin_predictor.py --model-dir AI/models --model-name xgboost --evaluate --limit 1000\n")
                f.write("```\n\n")
                
                f.write("### 3. Real-time Detection\n")
                f.write("```python\n")
                f.write("from AI.inference.coinjoin_predictor import RealTimeCoinJoinDetector\n")
                f.write("detector = RealTimeCoinJoinDetector('AI/models', 'xgboost')\n")
                f.write("result = detector.process_new_transaction(tx_hash)\n")
                f.write("```\n\n")
            
            logger.info(f"Training report generated: {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return False
        
        return True
    
    def run_full_pipeline(self, balance_ratio: float = 0.5, sample_size: int = 1000, 
                         config_path: str = None, model_name: str = 'xgboost'):
        """Chạy toàn bộ pipeline"""
        logger.info("="*60)
        logger.info("STARTING COINJOIN DETECTION AI TRAINING PIPELINE")
        logger.info("="*60)
        
        start_time = time.time()
        
        # Step 1: Data Preparation
        if not self.step1_data_preparation(balance_ratio, sample_size):
            logger.error("Pipeline failed at Step 1")
            return False
        
        # Step 2: Model Training
        if not self.step2_model_training(config_path):
            logger.error("Pipeline failed at Step 2")
            return False
        
        # Step 3: Model Evaluation
        if not self.step3_model_evaluation(model_name):
            logger.error("Pipeline failed at Step 3")
            return False
        
        # Step 4: Generate Report
        if not self.step4_generate_report():
            logger.error("Pipeline failed at Step 4")
            return False
        
        total_time = time.time() - start_time
        logger.info("="*60)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info(f"Total time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
        logger.info("="*60)
        
        return True

def main():
    parser = argparse.ArgumentParser(description='CoinJoin Detection AI Training Pipeline')
    parser.add_argument('--base-dir', default='.', help='Base directory of the project')
    parser.add_argument('--balance-ratio', type=float, default=0.5, help='Ratio of negative to positive samples')
    parser.add_argument('--sample-size', type=int, default=1000, help='Number of negative samples')
    parser.add_argument('--config', help='Path to training config file')
    parser.add_argument('--model-name', default='xgboost', help='Model name for evaluation')
    parser.add_argument('--step', choices=['1', '2', '3', '4', 'all'], default='all', 
                       help='Which step to run (1=data_prep, 2=training, 3=evaluation, 4=report, all=full_pipeline)')
    
    args = parser.parse_args()
    
    # Khởi tạo pipeline
    pipeline = CoinJoinTrainingPipeline(args.base_dir)
    
    if args.step == '1':
        pipeline.step1_data_preparation(args.balance_ratio, args.sample_size)
    elif args.step == '2':
        pipeline.step2_model_training(args.config)
    elif args.step == '3':
        pipeline.step3_model_evaluation(args.model_name)
    elif args.step == '4':
        pipeline.step4_generate_report()
    else:
        # Run full pipeline
        success = pipeline.run_full_pipeline(
            balance_ratio=args.balance_ratio,
            sample_size=args.sample_size,
            config_path=args.config,
            model_name=args.model_name
        )
        
        if success:
            logger.info("🎉 Training pipeline completed successfully!")
            logger.info("📊 Check the results in AI/models/ directory")
            logger.info("📋 Read the report: AI/models/training_report.md")
        else:
            logger.error("❌ Training pipeline failed!")
            sys.exit(1)

if __name__ == '__main__':
    main()
