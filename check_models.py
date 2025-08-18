#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Saved Models
Kiểm tra các model đã lưu
"""

import os
import json
from datetime import datetime

def check_models():
    print("🔍 CHECKING SAVED MODELS")
    print("=" * 60)
    
    models_dir = 'data/models'
    if not os.path.exists(models_dir):
        print("❌ No models directory found")
        return
    
    model_files = [f for f in os.listdir(models_dir) if f.startswith('coinjoin_model_') and f.endswith('.json')]
    
    if not model_files:
        print("❌ No model files found")
        return
    
    print(f"Found {len(model_files)} model files:")
    print()
    
    # Sort by timestamp
    model_files.sort()
    
    for i, model_file in enumerate(model_files, 1):
        model_path = os.path.join(models_dir, model_file)
        
        try:
            with open(model_path, 'r') as f:
                model_data = json.load(f)
            
            info = model_data['model_info']
            params = model_data['detection_parameters']
            stats = model_data['statistics']
            
            print(f"📊 MODEL {i}: {model_file}")
            print("-" * 50)
            print(f"   • Transactions processed: {info['tx_count']:,}")
            print(f"   • CoinJoin detected: {info['total_coinjoin']:,}")
            print(f"   • Normal transactions: {info['total_normal']:,}")
            print(f"   • Errors: {info['errors']}")
            print(f"   • Detection rate: {info['detection_rate']:.2%}")
            print(f"   • Model version: {info['model_version']}")
            print(f"   • Timestamp: {info['timestamp']}")
            
            # Calculate time since creation
            try:
                created_time = datetime.strptime(info['timestamp'], '%Y%m%d_%H%M%S')
                now = datetime.now()
                time_diff = now - created_time
                print(f"   • Age: {time_diff}")
            except:
                pass
            
            print()
            
        except Exception as e:
            print(f"❌ Error reading {model_file}: {e}")
            print()

def check_latest_model():
    print("🔄 LATEST MODEL DETAILS")
    print("=" * 60)
    
    models_dir = 'data/models'
    if not os.path.exists(models_dir):
        print("❌ No models directory found")
        return
    
    model_files = [f for f in os.listdir(models_dir) if f.startswith('coinjoin_model_') and f.endswith('.json')]
    
    if not model_files:
        print("❌ No model files found")
        return
    
    # Get the latest model
    model_files.sort(reverse=True)
    latest_model = model_files[0]
    model_path = os.path.join(models_dir, latest_model)
    
    try:
        with open(model_path, 'r') as f:
            model_data = json.load(f)
        
        info = model_data['model_info']
        params = model_data['detection_parameters']
        stats = model_data['statistics']
        
        print(f"✅ Latest Model: {latest_model}")
        print(f"📊 Summary:")
        print(f"   • Transactions: {info['tx_count']:,}")
        print(f"   • CoinJoin detected: {info['total_coinjoin']:,}")
        print(f"   • Detection rate: {info['detection_rate']:.2%}")
        print(f"   • Model version: {info['model_version']}")
        print(f"   • Created: {info['timestamp']}")
        
        print(f"\n⚙️ Detection Parameters:")
        print(f"   • Wasabi base denomination: {params['wasabi_approx_base_denom']} BTC")
        print(f"   • Wasabi max precision: {params['wasabi_max_precision']} BTC")
        print(f"   • Samourai Whirlpool sizes: {params['samourai_whirlpool_sizes']}")
        print(f"   • Our min inputs: {params['our_min_inputs']}")
        print(f"   • Our min outputs: {params['our_min_outputs']}")
        print(f"   • Our uniformity threshold: {params['our_uniformity_threshold']}")
        print(f"   • Our diversity threshold: {params['our_diversity_threshold']}")
        print(f"   • Our score threshold: {params['our_score_threshold']}")
        
        print(f"\n📈 Statistics:")
        print(f"   • Total processed transactions: {len(stats['processed_transactions'])}")
        print(f"   • CoinJoin transactions: {len(stats['coinjoin_transactions'])}")
        print(f"   • Normal transactions: {len(stats['normal_transactions'])}")
        
        if 'detection_methods' in stats:
            methods = stats['detection_methods']
            print(f"   • Detection methods breakdown:")
            print(f"     - Wasabi: {methods['wasabi']}")
            print(f"     - Samourai: {methods['samourai']}")
            print(f"     - Our Custom: {methods['our_custom']}")
        
        # Calculate time since creation
        try:
            created_time = datetime.strptime(info['timestamp'], '%Y%m%d_%H%M%S')
            now = datetime.now()
            time_diff = now - created_time
            print(f"\n⏰ Model Age: {time_diff}")
        except:
            pass
        
    except Exception as e:
        print(f"❌ Error reading latest model: {e}")

def check_training_progress():
    print("📈 TRAINING PROGRESS")
    print("=" * 60)
    
    checkpoint_file = 'data/training_results/progress_checkpoint.json'
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            checkpoint_info = checkpoint_data['checkpoint_info']
            progress = checkpoint_data['progress']
            
            print(f"✅ Checkpoint found:")
            print(f"   • Current batch: {checkpoint_info['current_batch']}")
            print(f"   • Total batches: {checkpoint_info['total_batches']}")
            print(f"   • Progress: {progress['percentage']:.1f}%")
            print(f"   • Remaining batches: {progress['remaining_batches']}")
            print(f"   • Total processed: {checkpoint_info['total_processed']}")
            print(f"   • CoinJoin detected: {checkpoint_info['total_coinjoin']}")
            print(f"   • Errors: {checkpoint_info['errors']}")
            print(f"   • Start time: {checkpoint_info['start_time']}")
            print(f"   • Checkpoint time: {checkpoint_info['checkpoint_time']}")
            
        except Exception as e:
            print(f"❌ Error reading checkpoint: {e}")
    else:
        print("❌ No checkpoint file found")

if __name__ == "__main__":
    check_models()
    print()
    check_latest_model()
    print()
    check_training_progress()
