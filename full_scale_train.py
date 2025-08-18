#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Full Scale AI CoinJoin Training Script
"""

import os
import json
import time
import logging
import pandas as pd
import requests
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class FullScaleTrainer:
    def __init__(self):
        self.blockstream_api = 'https://blockstream.info/api'
        self.processed_txs = set()
        self.coinjoin_txs = set()
        self.normal_txs = set()
        
        self.total_processed = 0
        self.total_coinjoin = 0
        self.total_normal = 0
        self.errors = 0
        
        # Model saving parameters
        self.model_save_interval = 100  # Save model every 100 transactions
        self.last_model_save = 0
        
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data/training_results', exist_ok=True)
        os.makedirs('data/models', exist_ok=True)
        
    def load_all_datasets(self):
        logger.info('Loading all datasets...')
        
        coinjoins_df = pd.read_csv('dataset/CoinJoinsMain_20211221.csv')
        coinjoin_txs = coinjoins_df['tx_hash'].tolist()
        
        with open('dataset/wasabi_txs_02-2022.txt', 'r') as f:
            wasabi_txs = [line.strip() for line in f if line.strip()]
        
        all_txs = list(set(coinjoin_txs + wasabi_txs))
        
        logger.info(f'Loaded {len(coinjoin_txs)} CoinJoin + {len(wasabi_txs)} Wasabi transactions')
        logger.info(f'Total unique transactions: {len(all_txs)}')
        
        return all_txs
    
    def get_transaction_data(self, txid):
        try:
            url = f"{self.blockstream_api}/tx/{txid}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching tx {txid}: {e}")
            return None
    
    def analyze_coinjoin(self, tx_data):
        """Optimized CoinJoin detection based on Wasabi-Samourai with our unique signature"""
        
        # Constants từ Wasabi-Samourai analysis
        SATOSHI_IN_BTC = 100000000
        
        # Wasabi constants
        WASABI_APPROX_BASE_DENOM = 0.1 * SATOSHI_IN_BTC  # 0.1 BTC
        WASABI_MAX_PRECISION = 0.02 * SATOSHI_IN_BTC     # 0.02 BTC tolerance
        WASABI_COORD_ADDRESSES = [
            'bc1qs604c7jv6amk4cxqlnvuxv26hv3e48cds4m0ew',
            'bc1qa24tsgchvuxsaccp8vrnkfd85hrcpafg20kmjw'
        ]
        
        # Samourai constants  
        SAMOURAI_WHIRLPOOL_SIZES = [
            0.001 * SATOSHI_IN_BTC,  # 0.001 BTC
            0.01 * SATOSHI_IN_BTC,   # 0.01 BTC  
            0.05 * SATOSHI_IN_BTC,   # 0.05 BTC
            0.5 * SATOSHI_IN_BTC     # 0.5 BTC
        ]
        SAMOURAI_MAX_POOL_FEE = 0.0011 * SATOSHI_IN_BTC
        
        # Our custom constants - dấu ấn riêng
        OUR_MIN_INPUTS = 5
        OUR_MIN_OUTPUTS = 5
        OUR_UNIFORMITY_THRESHOLD = 0.8  # 80% outputs cùng giá trị
        OUR_DIVERSITY_THRESHOLD = 0.7   # 70% inputs từ địa chỉ khác nhau
        
        input_count = len(tx_data.get('vin', []))
        output_count = len(tx_data.get('vout', []))
        
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
        
        # Calculate indicators
        unique_input_addresses = len(set(input_addresses))
        unique_output_addresses = len(set(output_addresses))
        unique_output_values = len(set(output_values))
        
        indicators = {
            'input_count': input_count,
            'output_count': output_count,
            'unique_input_addresses': unique_input_addresses,
            'unique_output_addresses': unique_output_addresses,
            'output_uniformity': unique_output_values,
            'input_diversity': unique_input_addresses,
            'transaction_size': input_count + output_count
        }
        
        # 1. WASABI DETECTION
        wasabi_detected = False
        wasabi_reasons = []
        
        # Check for Wasabi coordinator addresses
        has_wasabi_coord = any(addr in WASABI_COORD_ADDRESSES for addr in output_addresses)
        
        # Count output value frequencies
        from collections import defaultdict
        value_counts = defaultdict(int)
        for value in output_values:
            value_counts[value] += 1
        
        # Find most frequent output value
        if value_counts:
            most_frequent_value, most_frequent_count = max(value_counts.items(), key=lambda x: x[1])
            
            # Wasabi heuristic: n_inputs >= most_frequent_output_count >= 10 AND value close to 0.1 BTC
            wasabi_heuristic = (
                input_count >= most_frequent_count >= 10 and
                abs(WASABI_APPROX_BASE_DENOM - most_frequent_value) <= WASABI_MAX_PRECISION
            )
            
            # Wasabi static: has coordinator address AND multiple equal outputs
            wasabi_static = has_wasabi_coord and any(count > 2 for count in value_counts.values())
            
            if wasabi_heuristic or wasabi_static:
                wasabi_detected = True
                if wasabi_static:
                    wasabi_reasons.append("Wasabi static detection (coordinator + equal outputs)")
                if wasabi_heuristic:
                    wasabi_reasons.append("Wasabi heuristic detection (0.1 BTC pattern)")
        
        # 2. SAMOURAI DETECTION
        samourai_detected = False
        samourai_reasons = []
        
        # Samourai pattern: 5 inputs, 5 outputs, all outputs equal
        if input_count == 5 and output_count == 5:
            if len(set(output_values)) == 1:  # All outputs have same value
                output_value = output_values[0]
                
                # Check if value matches Whirlpool sizes
                for whirlpool_size in SAMOURAI_WHIRLPOOL_SIZES:
                    # Standard tolerance
                    if abs(output_value - whirlpool_size) <= 0.01 * SATOSHI_IN_BTC:
                        samourai_detected = True
                        samourai_reasons.append(f"Samourai Whirlpool standard ({whirlpool_size/SATOSHI_IN_BTC} BTC)")
                        break
                    
                    # Fee tolerance
                    if abs(output_value - whirlpool_size) <= SAMOURAI_MAX_POOL_FEE:
                        samourai_detected = True
                        samourai_reasons.append(f"Samourai Whirlpool with fee ({whirlpool_size/SATOSHI_IN_BTC} BTC)")
                        break
        
        # 3. OUR CUSTOM DETECTION
        our_score = 0.0
        our_reasons = []
        
        # Calculate uniformity score (how many outputs have same value)
        if output_values:
            most_frequent_count = max(value_counts.values())
            uniformity_score = most_frequent_count / len(output_values)
        else:
            uniformity_score = 0
        
        # Calculate diversity score (how many unique input addresses)
        if input_addresses:
            diversity_score = unique_input_addresses / len(input_addresses)
        else:
            diversity_score = 0
        
        # Our custom scoring
        if input_count >= OUR_MIN_INPUTS:
            our_score += 0.15
            our_reasons.append(f"Sufficient inputs ({input_count})")
        
        if output_count >= OUR_MIN_OUTPUTS:
            our_score += 0.15
            our_reasons.append(f"Sufficient outputs ({output_count})")
        
        # Uniformity check (our signature)
        if uniformity_score >= OUR_UNIFORMITY_THRESHOLD:
            our_score += 0.25
            our_reasons.append(f"High output uniformity ({uniformity_score:.2f})")
        
        # Diversity check (our signature)
        if diversity_score >= OUR_DIVERSITY_THRESHOLD:
            our_score += 0.20
            our_reasons.append(f"High input diversity ({diversity_score:.2f})")
        
        # Size penalty for very large transactions (likely exchanges)
        if indicators['transaction_size'] > 200:
            our_score -= 0.10
            our_reasons.append("Very large transaction (possible exchange)")
        
        # Bonus for perfect CoinJoin patterns
        if (uniformity_score >= 0.9 and diversity_score >= 0.8 and 
            input_count >= 10 and output_count >= 10):
            our_score += 0.15
            our_reasons.append("Perfect CoinJoin pattern")
        
        our_score = min(our_score, 1.0)
        
        # 4. FINAL DETECTION DECISION
        is_coinjoin = False
        detection_method = "none"
        final_reasons = []
        
        # Priority order: Wasabi > Samourai > Our custom
        if wasabi_detected:
            is_coinjoin = True
            detection_method = "wasabi"
            final_reasons.extend(wasabi_reasons)
        elif samourai_detected:
            is_coinjoin = True
            detection_method = "samourai"
            final_reasons.extend(samourai_reasons)
        elif our_score >= 0.7:  # Our threshold
            is_coinjoin = True
            detection_method = "our_custom"
            final_reasons.extend(our_reasons)
        
        return {
            'is_coinjoin': is_coinjoin,
            'detection_method': detection_method,
            'score': our_score,
            'reasons': final_reasons,
            'indicators': indicators,
            'wasabi_detected': wasabi_detected,
            'samourai_detected': samourai_detected,
            'uniformity_score': uniformity_score,
            'diversity_score': diversity_score
        }
    
    def process_transaction(self, txid):
        if txid in self.processed_txs:
            return None
        
        self.processed_txs.add(txid)
        
        tx_data = self.get_transaction_data(txid)
        if not tx_data:
            self.errors += 1
            return None
        
        analysis = self.analyze_coinjoin(tx_data)
        
        result = {
            'txid': txid,
            'is_coinjoin': analysis['is_coinjoin'],
            'detection_method': analysis['detection_method'],
            'score': analysis['score'],
            'reasons': analysis['reasons'],
            'indicators': analysis['indicators'],
            'wasabi_detected': analysis['wasabi_detected'],
            'samourai_detected': analysis['samourai_detected'],
            'uniformity_score': analysis['uniformity_score'],
            'diversity_score': analysis['diversity_score'],
            'timestamp': datetime.now().isoformat()
        }
        
        self.total_processed += 1
        if result['is_coinjoin']:
            self.coinjoin_txs.add(txid)
            self.total_coinjoin += 1
        else:
            self.normal_txs.add(txid)
            self.total_normal += 1
        
        # Check if we should save the model
        if self.total_processed >= self.last_model_save + self.model_save_interval:
            self.save_model(self.total_processed)
            self.last_model_save = self.total_processed
        
        return result
    
    def save_model(self, tx_count):
        """Save the current model state"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            model_file = f'data/models/coinjoin_model_{tx_count:06d}_{timestamp}.json'
            
            # Collect model data
            model_data = {
                'model_info': {
                    'tx_count': tx_count,
                    'total_processed': self.total_processed,
                    'total_coinjoin': self.total_coinjoin,
                    'total_normal': self.total_normal,
                    'errors': self.errors,
                    'detection_rate': self.total_coinjoin / self.total_processed if self.total_processed > 0 else 0,
                    'timestamp': timestamp,
                    'model_version': 'optimized_v1.0'
                },
                'detection_parameters': {
                    'wasabi_coord_addresses': [
                        'bc1qs604c7jv6amk4cxqlnvuxv26hv3e48cds4m0ew',
                        'bc1qa24tsgchvuxsaccp8vrnkfd85hrcpafg20kmjw'
                    ],
                    'wasabi_approx_base_denom': 0.1,
                    'wasabi_max_precision': 0.02,
                    'samourai_whirlpool_sizes': [0.001, 0.01, 0.05, 0.5],
                    'samourai_max_pool_fee': 0.0011,
                    'our_min_inputs': 5,
                    'our_min_outputs': 5,
                    'our_uniformity_threshold': 0.8,
                    'our_diversity_threshold': 0.7,
                    'our_score_threshold': 0.7
                },
                'statistics': {
                    'processed_transactions': list(self.processed_txs),
                    'coinjoin_transactions': list(self.coinjoin_txs),
                    'normal_transactions': list(self.normal_txs),
                    'detection_methods': {
                        'wasabi': len([tx for tx in self.coinjoin_txs if self._get_detection_method(tx) == 'wasabi']),
                        'samourai': len([tx for tx in self.coinjoin_txs if self._get_detection_method(tx) == 'samourai']),
                        'our_custom': len([tx for tx in self.coinjoin_txs if self._get_detection_method(tx) == 'our_custom'])
                    }
                }
            }
            
            with open(model_file, 'w') as f:
                json.dump(model_data, f, indent=2)
            
            logger.info(f"✅ Model saved: {model_file}")
            logger.info(f"   • Transactions: {tx_count}")
            logger.info(f"   • CoinJoin detected: {self.total_coinjoin}")
            logger.info(f"   • Detection rate: {model_data['model_info']['detection_rate']:.2%}")
            
            return model_file
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return None
    
    def _get_detection_method(self, txid):
        """Get detection method for a specific transaction (placeholder)"""
        # This would need to be implemented based on stored results
        # For now, return a default value
        return "unknown"
    
    def load_latest_model(self):
        """Load the latest saved model"""
        try:
            models_dir = 'data/models'
            if not os.path.exists(models_dir):
                logger.info("No models directory found")
                return None
            
            model_files = [f for f in os.listdir(models_dir) if f.startswith('coinjoin_model_') and f.endswith('.json')]
            if not model_files:
                logger.info("No model files found")
                return None
            
            # Sort by timestamp and get the latest
            model_files.sort(reverse=True)
            latest_model = model_files[0]
            model_path = os.path.join(models_dir, latest_model)
            
            with open(model_path, 'r') as f:
                model_data = json.load(f)
            
            logger.info(f"✅ Loaded latest model: {latest_model}")
            logger.info(f"   • Transactions: {model_data['model_info']['tx_count']}")
            logger.info(f"   • CoinJoin detected: {model_data['model_info']['total_coinjoin']}")
            logger.info(f"   • Detection rate: {model_data['model_info']['detection_rate']:.2%}")
            
            return model_data
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return None
    
    def train_full_scale(self, sample_size=None, start_from_batch=1):
        logger.info("Starting FULL SCALE training...")
        start_time = datetime.now()
        
        all_txs = self.load_all_datasets()
        
        if sample_size:
            all_txs = all_txs[:sample_size]
            logger.info(f"Using sample size: {sample_size}")
        
        logger.info(f"Processing {len(all_txs)} transactions...")
        
        all_results = []
        batch_size = 50  # Giảm từ 100 xuống 50
        total_batches = (len(all_txs) + batch_size - 1) // batch_size
        
        # Load existing results if resuming
        if start_from_batch > 1:
            logger.info(f"Resuming from batch {start_from_batch}")
            all_results = self.load_existing_results()
        
        for i in range((start_from_batch - 1) * batch_size, len(all_txs), batch_size):
            batch = all_txs[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} transactions)")
            logger.info(f"Batch range: {i+1}-{min(i+batch_size, len(all_txs))} of {len(all_txs)}")
            
            batch_results = []
            for j, txid in enumerate(batch):
                try:
                    logger.info(f"Processing tx {i+j+1}/{len(all_txs)}: {txid[:16]}...")
                    result = self.process_transaction(txid)
                    if result:
                        batch_results.append(result)
                    time.sleep(0.2)
                except Exception as e:
                    logger.error(f"Error processing {txid}: {e}")
                    self.errors += 1
                    continue
            
            all_results.extend(batch_results)
            
            # Save batch with index information
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            batch_file = f'data/training_results/batch_{batch_num:04d}_{timestamp}.json'
            batch_data = {
                'batch_info': {
                    'batch_number': batch_num,
                    'total_batches': total_batches,
                    'start_index': i,
                    'end_index': min(i + batch_size, len(all_txs)),
                    'total_transactions': len(all_txs),
                    'batch_size': len(batch),
                    'timestamp': timestamp
                },
                'results': batch_results
            }
            with open(batch_file, 'w') as f:
                json.dump(batch_data, f, indent=2)
            
            # Save progress checkpoint
            self.save_progress_checkpoint(all_results, batch_num, total_batches, start_time)
            
            progress = (batch_num / total_batches) * 100
            logger.info(f"Progress: {progress:.1f}% - Processed: {self.total_processed}, CoinJoin: {self.total_coinjoin}, Normal: {self.total_normal}, Errors: {self.errors}")
            logger.info(f"Batch {batch_num} completed and saved to {batch_file}")
        
        self.save_final_results(all_results, start_time)
        logger.info("FULL SCALE training completed!")
    
    def load_existing_results(self):
        """Load existing results from previous runs"""
        existing_results = []
        results_dir = 'data/training_results'
        
        if os.path.exists(results_dir):
            batch_files = [f for f in os.listdir(results_dir) if f.startswith('batch_') and f.endswith('.json')]
            for batch_file in sorted(batch_files):
                try:
                    with open(os.path.join(results_dir, batch_file), 'r') as f:
                        batch_data = json.load(f)
                        if 'results' in batch_data:
                            existing_results.extend(batch_data['results'])
                except Exception as e:
                    logger.error(f"Error loading {batch_file}: {e}")
        
        logger.info(f"Loaded {len(existing_results)} existing results")
        return existing_results
    
    def save_progress_checkpoint(self, all_results, current_batch, total_batches, start_time):
        """Save progress checkpoint"""
        checkpoint_data = {
            'checkpoint_info': {
                'current_batch': current_batch,
                'total_batches': total_batches,
                'total_processed': self.total_processed,
                'total_coinjoin': self.total_coinjoin,
                'total_normal': self.total_normal,
                'errors': self.errors,
                'start_time': start_time.isoformat(),
                'checkpoint_time': datetime.now().isoformat()
            },
            'progress': {
                'percentage': (current_batch / total_batches) * 100,
                'remaining_batches': total_batches - current_batch
            }
        }
        
        checkpoint_file = 'data/training_results/progress_checkpoint.json'
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        logger.info(f"Progress checkpoint saved: {current_batch}/{total_batches} batches completed")
    
    def save_final_results(self, all_results, start_time):
        end_time = datetime.now()
        duration = end_time - start_time
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        all_results_file = f'data/training_results/full_scale_results_{timestamp}.json'
        with open(all_results_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        coinjoin_results = [r for r in all_results if r.get('is_coinjoin', False)]
        coinjoin_file = f'data/training_results/full_scale_coinjoin_{timestamp}.json'
        with open(coinjoin_file, 'w') as f:
            json.dump(coinjoin_results, f, indent=2)
        
        stats = {
            'total_transactions': len(all_results),
            'coinjoin_detected': self.total_coinjoin,
            'normal_transactions': self.total_normal,
            'errors': self.errors,
            'detection_rate': self.total_coinjoin / len(all_results) if all_results else 0,
            'processing_time_minutes': duration.total_seconds() / 60,
            'transactions_per_minute': len(all_results) / (duration.total_seconds() / 60) if duration.total_seconds() > 0 else 0,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration': str(duration)
        }
        
        stats_file = f'data/training_results/full_scale_stats_{timestamp}.json'
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info("=" * 60)
        logger.info("FULL SCALE TRAINING COMPLETED!")
        logger.info("=" * 60)
        logger.info(f"Total transactions processed: {len(all_results)}")
        logger.info(f"CoinJoin detected: {self.total_coinjoin}")
        logger.info(f"Normal transactions: {self.total_normal}")
        logger.info(f"Errors: {self.errors}")
        logger.info(f"Detection rate: {stats['detection_rate']:.2%}")
        logger.info(f"Processing time: {stats['processing_time_minutes']:.1f} minutes")
        logger.info(f"Speed: {stats['transactions_per_minute']:.1f} transactions/minute")

def main():
    print("=" * 60)
    print("OPTIMIZED FULL SCALE AI COINJOIN TRAINING")
    print("Based on Wasabi-Samourai with our unique signature")
    print("=" * 60)
    
    # Train toàn bộ dataset
    sample_size = None  # None = train toàn bộ dataset
    
    print(f"Configuration:")
    print(f"  • Sample size: {sample_size if sample_size else 'ALL (30,640 transactions)'}")
    print(f"  • Rate limiting: 0.2s per transaction")
    print(f"  • Batch size: 50 transactions")
    print(f"  • Estimated time: ~3-4 hours")
    print(f"  • Progress checkpoint: Enabled")
    print(f"  • Algorithm: Optimized (Wasabi + Samourai + Our Custom)")
    print()
    
    print("🎯 DETECTION METHODS:")
    print("  • Wasabi: Coordinator addresses + 0.1 BTC patterns")
    print("  • Samourai: 5x5 Whirlpool patterns (0.001, 0.01, 0.05, 0.5 BTC)")
    print("  • Our Custom: Uniformity/Diversity scoring with exchange filtering")
    print()
    
    print("💾 MODEL SAVING:")
    print("  • Save interval: Every 100 transactions")
    print("  • Save location: data/models/")
    print("  • Format: coinjoin_model_XXXXXX_YYYYMMDD_HHMMSS.json")
    print()
    
    # Check if resuming from checkpoint
    checkpoint_file = 'data/training_results/progress_checkpoint.json'
    start_from_batch = 1
    
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
                current_batch = checkpoint_data['checkpoint_info']['current_batch']
                total_batches = checkpoint_data['checkpoint_info']['total_batches']
                
                resume = input(f"Found checkpoint: batch {current_batch}/{total_batches} completed. Resume? (y/n): ").strip().lower()
                if resume == 'y':
                    start_from_batch = current_batch + 1
                    print(f"Resuming from batch {start_from_batch}")
                else:
                    print("Starting fresh training")
        except Exception as e:
            print(f"Error reading checkpoint: {e}")
            print("Starting fresh training")
    
    trainer = FullScaleTrainer()
    trainer.train_full_scale(sample_size=sample_size, start_from_batch=start_from_batch)

if __name__ == "__main__":
    main()
