#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Model Usage Script
Sử dụng model đã train một cách đơn giản
"""

from load_trained_model import TrainedCoinJoinModel

def main():
    print("🤖 AI COINJOIN MODEL - QUICK USAGE")
    print("=" * 50)
    
    # Load model
    print("Loading trained model...")
    model = TrainedCoinJoinModel()
    
    if not model.model_data:
        print("❌ Không thể load model! Hãy chạy training trước.")
        return
    
    print("✅ Model loaded successfully!")
    
    # Interactive usage
    while True:
        print("\n" + "="*50)
        print("📋 OPTIONS:")
        print("1. Analyze single transaction")
        print("2. Batch analyze transactions")
        print("3. Show model info")
        print("4. Exit")
        
        choice = input("\nChọn option (1-4): ").strip()
        
        if choice == "1":
            txid = input("Nhập transaction ID: ").strip()
            if txid:
                result = model.predict_coinjoin(txid)
                print(f"\n🔍 RESULT:")
                print(f"Transaction: {result['txid']}")
                print(f"CoinJoin: {'✅ YES' if result['is_coinjoin'] else '❌ NO'}")
                print(f"Score: {result.get('score', 0):.2f}")
                print(f"Confidence: {result.get('confidence', 'unknown')}")
                if 'reasons' in result and result['reasons']:
                    print(f"Reasons: {', '.join(result['reasons'])}")
        
        elif choice == "2":
            print("Nhập transaction IDs (mỗi dòng một ID, nhấn Enter 2 lần để kết thúc):")
            txids = []
            while True:
                txid = input().strip()
                if not txid:
                    break
                txids.append(txid)
            
            if txids:
                print(f"\nAnalyzing {len(txids)} transactions...")
                results = model.batch_predict(txids)
                
                print(f"\n📊 BATCH RESULTS:")
                coinjoin_count = 0
                for result in results:
                    if result.get('is_coinjoin'):
                        coinjoin_count += 1
                        print(f"✅ {result['txid'][:16]}... - COINJOIN (Score: {result.get('score', 0):.2f})")
                    else:
                        print(f"❌ {result['txid'][:16]}... - NORMAL (Score: {result.get('score', 0):.2f})")
                
                print(f"\nSummary: {coinjoin_count}/{len(results)} CoinJoin detected")
                
                # Save results
                save = input("Lưu kết quả? (y/n): ").strip().lower()
                if save == 'y':
                    model.save_predictions(results)
        
        elif choice == "3":
            info = model.get_model_info()
            print(f"\n📊 MODEL INFO:")
            print(f"Training data: {info['model_data_count']} transactions")
            print(f"CoinJoin patterns: {info['coinjoin_patterns_count']}")
            print(f"Detection threshold: {info['threshold']}")
            print(f"Features: {', '.join(info['model_features'])}")
            if info['training_stats']:
                print(f"Training detection rate: {info['training_stats'].get('detection_rate', 0):.2%}")
        
        elif choice == "4":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice!")

if __name__ == "__main__":
    main()
