#!/usr/bin/env python3
"""
Example Usage của AI CoinJoin Investigation System
Demo cách sử dụng hệ thống để điều tra CoinJoin
"""

import sys
import os
from typing import List, Dict

# Add AI directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from investigation.coinjoin_investigator import CoinJoinInvestigator
from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

def example_basic_investigation():
    """Example cơ bản về investigation"""
    print("=" * 60)
    print("EXAMPLE: Basic CoinJoin Investigation")
    print("=" * 60)
    
    # Sample addresses (thay thế bằng địa chỉ thực)
    sample_addresses = [
        "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",  # Example address 1
        "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",  # Example address 2
        "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"   # Example address 3
    ]
    
    # Configuration
    config = Config({
        'max_investigation_depth': 5,
        'max_consecutive_non_coinjoin': 5,
        'min_coinjoin_score': 3.5,
        'cluster_similarity_threshold': 0.8,
        'api_rate_limit_delay': 0.2,
        'api_sources': ['blockstream'],
        'blockstream_base_url': 'https://blockstream.info/api',
        'output_dir': './example_results',
        'save_only_coinjoin': True
    })
    
    # Initialize investigator
    investigator = CoinJoinInvestigator(config)
    
    # Run investigation
    print(f"Starting investigation for {len(sample_addresses)} addresses...")
    results = investigator.investigate_addresses(sample_addresses, 'blockstream')
    
    # Print results
    print_investigation_results(results)
    
    return results

def example_advanced_investigation():
    """Example nâng cao với nhiều tùy chọn"""
    print("\n" + "=" * 60)
    print("EXAMPLE: Advanced CoinJoin Investigation")
    print("=" * 60)
    
    # Load addresses from file (nếu có)
    addresses_file = "sample_addresses.txt"
    addresses = []
    
    if os.path.exists(addresses_file):
        with open(addresses_file, 'r') as f:
            addresses = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    else:
        # Fallback to sample addresses
        addresses = [
            "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        ]
    
    # Advanced configuration
    config = Config({
        'max_investigation_depth': 10,
        'max_consecutive_non_coinjoin': 8,
        'min_coinjoin_score': 4.0,
        'cluster_similarity_threshold': 0.7,
        'api_rate_limit_delay': 0.1,
        'api_sources': ['blockstream', 'mempool'],
        'blockstream_base_url': 'https://blockstream.info/api',
        'mempool_base_url': 'https://mempool.space/api',
        'output_dir': './advanced_results',
        'save_only_coinjoin': True,
        'storage_dir': './advanced_storage'
    })
    
    # Initialize investigator
    investigator = CoinJoinInvestigator(config)
    
    # Run investigation with monitoring
    print(f"Starting advanced investigation for {len(addresses)} addresses...")
    
    # Monitor progress
    def progress_callback(status):
        print(f"Progress: {status['investigated_count']}/{len(addresses)} addresses processed")
        print(f"CoinJoin found: {status['coinjoin_found']}")
        print(f"Queue size: {status['queue_size']}")
        print("-" * 40)
    
    # Run investigation
    results = investigator.investigate_addresses(addresses, 'blockstream')
    
    # Print detailed results
    print_detailed_results(results)
    
    return results

def example_clustering_analysis():
    """Example phân tích clustering"""
    print("\n" + "=" * 60)
    print("EXAMPLE: Clustering Analysis")
    print("=" * 60)
    
    from investigation.cluster_analyzer import ClusterAnalyzer
    
    # Sample transaction data (thay thế bằng data thực)
    sample_transactions = [
        {
            'hash': 'abc123...',
            'inputs': [
                {'address': 'addr1', 'value': 1000000},
                {'address': 'addr2', 'value': 1000000},
                {'address': 'addr3', 'value': 1000000}
            ],
            'outputs': [
                {'address': 'addr4', 'value': 950000},
                {'address': 'addr5', 'value': 950000},
                {'address': 'addr6', 'value': 950000}
            ]
        }
    ]
    
    # Configuration
    config = Config({
        'cluster_similarity_threshold': 0.8,
        'min_cluster_size': 2,
        'max_cluster_size': 100
    })
    
    # Initialize cluster analyzer
    analyzer = ClusterAnalyzer(config)
    
    # Analyze clusters
    print("Analyzing transaction clusters...")
    clusters = analyzer.analyze_transaction_clusters(sample_transactions)
    
    # Print cluster analysis
    print_cluster_analysis(clusters)
    
    return clusters

def example_coinjoin_detection():
    """Example phát hiện CoinJoin"""
    print("\n" + "=" * 60)
    print("EXAMPLE: CoinJoin Detection")
    print("=" * 60)
    
    from investigation.coinjoin_detector import CoinJoinDetector
    
    # Sample transaction data
    sample_transactions = [
        {
            'hash': 'coinjoin_tx_1',
            'vin_sz': 5,
            'vout_sz': 5,
            'inputs': [
                {'address': 'addr1', 'value': 1000000},
                {'address': 'addr2', 'value': 1000000},
                {'address': 'addr3', 'value': 1000000},
                {'address': 'addr4', 'value': 1000000},
                {'address': 'addr5', 'value': 1000000}
            ],
            'outputs': [
                {'address': 'addr6', 'value': 950000},
                {'address': 'addr7', 'value': 950000},
                {'address': 'addr8', 'value': 950000},
                {'address': 'addr9', 'value': 950000},
                {'address': 'addr10', 'value': 950000}
            ]
        }
    ]
    
    # Sample clusters
    sample_clusters = {
        'input_clusters': {
            'cluster_1': {'addresses': ['addr1', 'addr2'], 'total_value': 2000000},
            'cluster_2': {'addresses': ['addr3', 'addr4'], 'total_value': 2000000},
            'cluster_3': {'addresses': ['addr5'], 'total_value': 1000000}
        },
        'output_clusters': {
            'cluster_1': {'addresses': ['addr6', 'addr7', 'addr8', 'addr9'], 'total_value': 3800000},
            'cluster_2': {'addresses': ['addr10'], 'total_value': 950000}
        },
        'cross_cluster_connections': []
    }
    
    # Configuration
    config = Config({
        'min_coinjoin_score': 4.0,
        'output_uniformity_threshold': 0.8,
        'input_diversity_threshold': 3,
        'min_transaction_size': 5
    })
    
    # Initialize detector
    detector = CoinJoinDetector(config)
    
    # Detect CoinJoin
    print("Detecting CoinJoin transactions...")
    coinjoin_txs = detector.detect_coinjoin_with_clusters(sample_transactions, sample_clusters)
    
    # Print detection results
    print_coinjoin_detection_results(coinjoin_txs)
    
    return coinjoin_txs

def print_investigation_results(results: Dict):
    """In kết quả investigation cơ bản"""
    summary = results.get('investigation_summary', {})
    
    print(f"\nInvestigation Summary:")
    print(f"  Initial Addresses: {summary.get('initial_addresses', 0)}")
    print(f"  Investigated Addresses: {summary.get('investigated_addresses', 0)}")
    print(f"  CoinJoin Transactions: {summary.get('coinjoin_transactions', 0)}")
    print(f"  Clusters Found: {summary.get('clusters_found', 0)}")
    print(f"  Duration: {summary.get('duration_seconds', 0):.2f} seconds")

def print_detailed_results(results: Dict):
    """In kết quả chi tiết"""
    print("\nDetailed Investigation Results:")
    
    # CoinJoin transactions
    coinjoin_txs = results.get('coinjoin_transactions', [])
    if coinjoin_txs:
        print(f"\nTop CoinJoin Transactions:")
        for i, tx in enumerate(coinjoin_txs[:5]):
            print(f"  {i+1}. {tx.get('hash', '')[:16]}... (Score: {tx.get('coinjoin_score', 0):.2f})")
            indicators = tx.get('coinjoin_indicators', {})
            print(f"     Indicators: {indicators}")
    
    # Clusters
    clusters = results.get('clusters', [])
    if clusters:
        print(f"\nClusters Found:")
        for i, cluster in enumerate(clusters[:3]):
            print(f"  {i+1}. {cluster.get('cluster_id', '')} - {cluster.get('address_count', 0)} addresses")
            print(f"     Total Value: {cluster.get('total_value', 0):,} satoshis")

def print_cluster_analysis(clusters: Dict):
    """In kết quả phân tích clustering"""
    print(f"\nCluster Analysis Results:")
    print(f"  Input Clusters: {len(clusters.get('input_clusters', {}))}")
    print(f"  Output Clusters: {len(clusters.get('output_clusters', {}))}")
    print(f"  Cross Connections: {len(clusters.get('cross_cluster_connections', []))}")
    
    # Input clusters
    input_clusters = clusters.get('input_clusters', {})
    if input_clusters:
        print(f"\nInput Clusters:")
        for cluster_id, cluster_data in input_clusters.items():
            print(f"  {cluster_id}: {cluster_data.get('address_count', 0)} addresses")
    
    # Output clusters
    output_clusters = clusters.get('output_clusters', {})
    if output_clusters:
        print(f"\nOutput Clusters:")
        for cluster_id, cluster_data in output_clusters.items():
            print(f"  {cluster_id}: {cluster_data.get('address_count', 0)} addresses")

def print_coinjoin_detection_results(coinjoin_txs: List[Dict]):
    """In kết quả phát hiện CoinJoin"""
    print(f"\nCoinJoin Detection Results:")
    print(f"  Total Transactions Analyzed: {len(coinjoin_txs)}")
    
    if coinjoin_txs:
        print(f"\nDetected CoinJoin Transactions:")
        for i, tx in enumerate(coinjoin_txs):
            print(f"  {i+1}. {tx.get('hash', '')[:16]}...")
            print(f"     Score: {tx.get('coinjoin_score', 0):.2f}")
            print(f"     Indicators: {tx.get('coinjoin_indicators', {})}")
    else:
        print("  No CoinJoin transactions detected")

def main():
    """Main function để chạy examples"""
    print("AI CoinJoin Investigation System - Examples")
    print("=" * 60)
    
    try:
        # Run examples
        example_basic_investigation()
        example_advanced_investigation()
        example_clustering_analysis()
        example_coinjoin_detection()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Error running examples: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
