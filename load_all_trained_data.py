#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aggregate all trained model data
Tổng hợp toàn bộ dữ liệu đã train trong data/models và data/training_results
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Set


def read_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def scan_models_dir(models_dir: str):
    snapshots = []
    if not os.path.exists(models_dir):
        return snapshots
    for name in os.listdir(models_dir):
        if name.startswith('coinjoin_model_') and name.endswith('.json'):
            snapshots.append(os.path.join(models_dir, name))
    snapshots.sort()
    return snapshots


def scan_results_dir(results_dir: str):
    results = []
    if not os.path.exists(results_dir):
        return results
    for name in os.listdir(results_dir):
        if name.startswith('advanced_results_') and name.endswith('.json'):
            results.append(os.path.join(results_dir, name))
    results.sort()
    return results


def aggregate_all_data(base_dir: str = '.'):
    models_dir = os.path.join(base_dir, 'data', 'models')
    results_dir = os.path.join(base_dir, 'data', 'training_results')

    snapshot_files = scan_models_dir(models_dir)
    result_files = scan_results_dir(results_dir)

    total_snapshots = len(snapshot_files)
    total_results = len(result_files)

    all_processed: Set[str] = set()
    all_coinjoin: Set[str] = set()
    all_normal: Set[str] = set()

    latest_snapshot_info: Dict = {}
    latest_snapshot_path = snapshot_files[-1] if snapshot_files else None

    # Aggregate snapshots (preferred source)
    for path in snapshot_files:
        try:
            data = read_json(path)
            stats = data.get('statistics', {})
            processed = stats.get('processed_transactions', []) or []
            coinjoin = stats.get('coinjoin_transactions', []) or []
            normal = stats.get('normal_transactions', []) or []
            all_processed.update(processed)
            all_coinjoin.update(coinjoin)
            all_normal.update(normal)
        except Exception:
            pass

    # Aggregate results (smaller batches) as fallback/complement
    for path in result_files:
        try:
            data = read_json(path)
            if isinstance(data, list):
                for item in data:
                    txid = item.get('txid') or item.get('tx_hash')
                    if not txid:
                        continue
                    all_processed.add(txid)
                    if item.get('is_coinjoin') or item.get('label') == 'coinjoin':
                        all_coinjoin.add(txid)
                    elif item.get('label') == 'normal':
                        all_normal.add(txid)
        except Exception:
            pass

    # Build summary
    summary = {
        'counts': {
            'snapshots': total_snapshots,
            'results_files': total_results,
            'unique_processed': len(all_processed),
            'unique_coinjoin': len(all_coinjoin),
            'unique_normal': len(all_normal),
        },
        'latest_snapshot': None,
        'generated_at': datetime.now().isoformat(),
    }

    if latest_snapshot_path:
        try:
            latest = read_json(latest_snapshot_path)
            info = latest.get('model_info', {})
            stats = latest.get('statistics', {})
            summary['latest_snapshot'] = {
                'path': latest_snapshot_path.replace('\\', '/'),
                'tx_count': info.get('tx_count'),
                'total_processed': info.get('total_processed'),
                'total_coinjoin': info.get('total_coinjoin'),
                'total_normal': info.get('total_normal'),
                'errors': info.get('errors'),
                'detection_rate': info.get('detection_rate'),
                'timestamp': info.get('timestamp'),
                'model_version': info.get('model_version'),
                'stats_processed_list_len': len(stats.get('processed_transactions', []) or []),
                'stats_coinjoin_list_len': len(stats.get('coinjoin_transactions', []) or []),
            }
        except Exception:
            pass

    # Save aggregate index
    os.makedirs(os.path.join(base_dir, 'data'), exist_ok=True)
    out_path = os.path.join(base_dir, 'data', 'aggregate_index.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(
            {
                'summary': summary,
                'processed_transactions': sorted(all_processed),
                'coinjoin_transactions': sorted(all_coinjoin),
                'normal_transactions': sorted(all_normal),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    return summary, out_path


def load_best_model(base_dir: str = '.') -> Dict:
    """
    Load model tốt nhất theo detection_rate cao nhất
    Returns: Dict chứa model data và metadata
    """
    models_dir = os.path.join(base_dir, 'data', 'models')
    snapshot_files = scan_models_dir(models_dir)
    
    if not snapshot_files:
        raise FileNotFoundError('Không tìm thấy model nào trong data/models')
    
    best_model = None
    best_rate = -1.0
    
    for path in snapshot_files:
        try:
            data = read_json(path)
            rate = data.get('model_info', {}).get('detection_rate', 0.0)
            if rate > best_rate:
                best_rate = rate
                best_model = {
                    'path': path,
                    'data': data,
                    'detection_rate': rate
                }
        except Exception:
            continue
    
    if not best_model:
        raise ValueError('Không thể load model nào')
    
    return best_model


def load_all_models(base_dir: str = '.') -> List[Dict]:
    """
    Load tất cả models dạng JSON objects
    Returns: List[Dict] chứa tất cả model data
    """
    models_dir = os.path.join(base_dir, 'data', 'models')
    snapshot_files = scan_models_dir(models_dir)
    
    models = []
    for path in snapshot_files:
        try:
            data = read_json(path)
            models.append({
                'path': path,
                'filename': os.path.basename(path),
                'data': data,
                'detection_rate': data.get('model_info', {}).get('detection_rate', 0.0),
                'total_processed': data.get('model_info', {}).get('total_processed', 0),
                'timestamp': data.get('model_info', {}).get('timestamp', ''),
                'model_version': data.get('model_info', {}).get('model_version', '')
            })
        except Exception:
            continue
    
    # Sắp xếp theo detection_rate giảm dần
    models.sort(key=lambda x: x['detection_rate'], reverse=True)
    return models


def load_model_by_name(model_name: str, base_dir: str = '.') -> Dict:
    """
    Load model theo tên file
    Args:
        model_name: Tên file (VD: 'coinjoin_model_000600_20250818_144717.json')
    Returns: Dict chứa model data
    """
    models_dir = os.path.join(base_dir, 'data', 'models')
    model_path = os.path.join(models_dir, model_name)
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f'Không tìm thấy model: {model_path}')
    
    data = read_json(model_path)
    return {
        'path': model_path,
        'filename': model_name,
        'data': data,
        'detection_rate': data.get('model_info', {}).get('detection_rate', 0.0),
        'total_processed': data.get('model_info', {}).get('total_processed', 0),
        'timestamp': data.get('model_info', {}).get('timestamp', ''),
        'model_version': data.get('model_info', {}).get('model_version', '')
    }


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summary, out_path = aggregate_all_data(base_dir)

    # Plain ASCII output for PowerShell compatibility
    print("ALL TRAINED DATA SUMMARY")
    print("=" * 60)
    print(f"Snapshots: {summary['counts']['snapshots']}")
    print(f"Result files: {summary['counts']['results_files']}")
    print(f"Unique processed txs: {summary['counts']['unique_processed']}")
    print(f"Unique coinjoin txs: {summary['counts']['unique_coinjoin']}")
    print(f"Unique normal txs: {summary['counts']['unique_normal']}")
    if summary['latest_snapshot']:
        s = summary['latest_snapshot']
        print("- Latest snapshot:")
        print(f"  path: {s['path']}")
        print(f"  detection_rate: {s['detection_rate']}")
        print(f"  total_processed: {s['total_processed']}")
        print(f"  coinjoin: {s['total_coinjoin']}, normal: {s['total_normal']}")
        print(f"  timestamp: {s['timestamp']} version: {s['model_version']}")
        print(f"  stats.proccessed_list_len: {s['stats_processed_list_len']}")
        print(f"  stats.coinjoin_list_len: {s['stats_coinjoin_list_len']}")
    print("- Aggregate index saved:", out_path)
    
    # Thêm thông tin model tốt nhất
    try:
        best_model = load_best_model(base_dir)
        print(f"\n🏆 MODEL TỐT NHẤT:")
        print(f"  File: {os.path.basename(best_model['path'])}")
        print(f"  Detection rate: {best_model['detection_rate']:.4f}")
        print(f"  Total processed: {best_model['data']['model_info'].get('total_processed', 0)}")
    except Exception as e:
        print(f"\n⚠️ Không thể load model tốt nhất: {e}")


if __name__ == '__main__':
    main()


if __name__ == '__main__':
    main()


