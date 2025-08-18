#!/usr/bin/env python3
"""
Script chính để chạy CoinJoin Investigation Pipeline
Sử dụng: python run_investigation.py --addresses addr1,addr2,addr3 --api-source blockstream
"""

import argparse
import json
import sys
import os
from typing import List, Dict
from datetime import datetime

# Add AI directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from investigation.coinjoin_investigator import CoinJoinInvestigator
from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

def load_config(config_path: str = None) -> Config:
    """Load configuration"""
    if config_path and os.path.exists(config_path):
        return Config.from_file(config_path)
    else:
        # Default config
        return Config({
            'max_investigation_depth': 10,
            'max_consecutive_non_coinjoin': 10,
            'min_coinjoin_score': 4.0,
            'cluster_similarity_threshold': 0.8,
            'api_rate_limit_delay': 0.1,
            'api_sources': ['blockstream', 'mempool'],
            'blockstream_base_url': 'https://blockstream.info/api',
            'mempool_base_url': 'https://mempool.space/api',
            'output_dir': './investigation_results',
            'save_only_coinjoin': True
        })

def load_addresses_from_file(file_path: str) -> List[str]:
    """Load addresses từ file"""
    addresses = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    addresses.append(line)
        logger.info(f"Loaded {len(addresses)} addresses from {file_path}")
    except Exception as e:
        logger.error(f"Error loading addresses from {file_path}: {str(e)}")
    
    return addresses

def save_investigation_results(results: Dict, output_dir: str):
    """Lưu kết quả investigation"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save full results
    results_file = os.path.join(output_dir, f"investigation_results_{timestamp}.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Save summary
    summary_file = os.path.join(output_dir, f"investigation_summary_{timestamp}.json")
    summary = {
        'investigation_summary': results.get('investigation_summary', {}),
        'config_used': results.get('config_used', {}),
        'coinjoin_transactions_count': len(results.get('coinjoin_transactions', [])),
        'clusters_count': len(results.get('clusters', [])),
        'timestamp': timestamp
    }
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    # Save CoinJoin transactions only
    coinjoin_file = os.path.join(output_dir, f"coinjoin_transactions_{timestamp}.json")
    coinjoin_txs = results.get('coinjoin_transactions', [])
    with open(coinjoin_file, 'w') as f:
        json.dump(coinjoin_txs, f, indent=2, default=str)
    
    logger.info(f"Results saved to {output_dir}")
    logger.info(f"  - Full results: {results_file}")
    logger.info(f"  - Summary: {summary_file}")
    logger.info(f"  - CoinJoin transactions: {coinjoin_file}")

def print_investigation_summary(results: Dict):
    """In summary của investigation"""
    summary = results.get('investigation_summary', {})
    
    print("\n" + "="*60)
    print("COINJOIN INVESTIGATION SUMMARY")
    print("="*60)
    
    print(f"Initial Addresses: {summary.get('initial_addresses', 0)}")
    print(f"Investigated Addresses: {summary.get('investigated_addresses', 0)}")
    print(f"CoinJoin Transactions Found: {summary.get('coinjoin_transactions', 0)}")
    print(f"Clusters Found: {summary.get('clusters_found', 0)}")
    print(f"Investigation Depth: {summary.get('investigation_depth', 0)}")
    print(f"Total Related Transactions: {summary.get('total_related_transactions', 0)}")
    print(f"Duration: {summary.get('duration_seconds', 0):.2f} seconds")
    print(f"Consecutive Non-CoinJoin: {summary.get('consecutive_non_coinjoin', 0)}")
    
    print("\n" + "-"*60)
    print("TOP COINJOIN TRANSACTIONS")
    print("-"*60)
    
    coinjoin_txs = results.get('coinjoin_transactions', [])
    if coinjoin_txs:
        # Sort by score
        sorted_txs = sorted(coinjoin_txs, key=lambda x: x.get('coinjoin_score', 0), reverse=True)
        
        for i, tx in enumerate(sorted_txs[:10]):  # Top 10
            print(f"{i+1:2d}. {tx.get('hash', '')[:16]}... (Score: {tx.get('coinjoin_score', 0):.2f})")
            print(f"     Input Clusters: {tx.get('input_clusters', 0)}, Output Clusters: {tx.get('output_clusters', 0)}")
    
    print("\n" + "-"*60)
    print("CLUSTER SUMMARY")
    print("-"*60)
    
    clusters = results.get('clusters', [])
    if clusters:
        for i, cluster in enumerate(clusters[:5]):  # Top 5
            print(f"{i+1:2d}. {cluster.get('cluster_id', '')} - {cluster.get('address_count', 0)} addresses")
            print(f"     Total Value: {cluster.get('total_value', 0):,} satoshis")
            print(f"     CoinJoin Count: {cluster.get('coinjoin_count', 0)}")

def main():
    parser = argparse.ArgumentParser(description='CoinJoin Investigation Pipeline')
    parser.add_argument('--addresses', type=str, help='Comma-separated list of addresses to investigate')
    parser.add_argument('--address-file', type=str, help='File containing addresses (one per line)')
    parser.add_argument('--api-source', type=str, default='blockstream', 
                       choices=['blockstream', 'mempool', 'bitcoin_core'],
                       help='API source to use for fetching transactions')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--output-dir', type=str, default='./investigation_results',
                       help='Output directory for results')
    parser.add_argument('--max-depth', type=int, default=10,
                       help='Maximum investigation depth')
    parser.add_argument('--min-score', type=float, default=4.0,
                       help='Minimum CoinJoin score threshold')
    parser.add_argument('--save-only-coinjoin', action='store_true', default=True,
                       help='Save only CoinJoin-related transactions')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.addresses and not args.address_file:
        print("Error: Must provide either --addresses or --address-file")
        sys.exit(1)
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command line arguments
    if args.max_depth:
        config.set('max_investigation_depth', args.max_depth)
    if args.min_score:
        config.set('min_coinjoin_score', args.min_score)
    if args.output_dir:
        config.set('output_dir', args.output_dir)
    if args.save_only_coinjoin:
        config.set('save_only_coinjoin', args.save_only_coinjoin)
    
    # Load addresses
    addresses = []
    if args.addresses:
        addresses = [addr.strip() for addr in args.addresses.split(',') if addr.strip()]
    elif args.address_file:
        addresses = load_addresses_from_file(args.address_file)
    
    if not addresses:
        print("Error: No valid addresses found")
        sys.exit(1)
    
    print(f"Starting CoinJoin investigation for {len(addresses)} addresses")
    print(f"API Source: {args.api_source}")
    print(f"Max Depth: {config.get('max_investigation_depth')}")
    print(f"Min Score: {config.get('min_coinjoin_score')}")
    print(f"Output Directory: {config.get('output_dir')}")
    print("-" * 60)
    
    try:
        # Initialize investigator
        investigator = CoinJoinInvestigator(config)
        
        # Run investigation
        results = investigator.investigate_addresses(addresses, args.api_source)
        
        # Save results
        save_investigation_results(results, config.get('output_dir'))
        
        # Print summary
        print_investigation_summary(results)
        
        print("\n" + "="*60)
        print("INVESTIGATION COMPLETED SUCCESSFULLY")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\nInvestigation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Investigation failed: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
