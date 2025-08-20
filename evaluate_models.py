#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Đánh giá các snapshot (data/models/*.json) dựa trên dữ liệu đã gán nhãn
trong data/training_results/*.json.

Tính các chỉ số: accuracy, precision, recall, f1 cho từng snapshot.
"""

import os
import json
from typing import Dict, List, Tuple, Set
from datetime import datetime


def read_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def scan_models(models_dir: str) -> List[str]:
    files: List[str] = []
    if not os.path.exists(models_dir):
        return files
    for name in os.listdir(models_dir):
        if name.startswith('coinjoin_model_') and name.endswith('.json'):
            files.append(os.path.join(models_dir, name))
    files.sort()
    return files


def scan_labeled(results_dir: str) -> List[str]:
    files: List[str] = []
    if not os.path.exists(results_dir):
        return files
    for name in os.listdir(results_dir):
        if name.endswith('.json'):
            files.append(os.path.join(results_dir, name))
    files.sort()
    return files


def load_labeled_dataset(results_dir: str) -> Dict[str, int]:
    """
    Trả về dict: txid -> 1 nếu coinjoin, 0 nếu normal.
    Chấp nhận các trường: 'label' ('coinjoin'/'normal') hoặc 'is_coinjoin' (bool/int)
    """
    labeled: Dict[str, int] = {}
    for path in scan_labeled(results_dir):
        try:
            data = read_json(path)
        except Exception:
            continue

        if isinstance(data, list):
            for item in data:
                txid = item.get('txid') or item.get('tx_hash') or item.get('hash')
                if not txid:
                    continue
                if 'label' in item:
                    label = 1 if str(item['label']).lower() == 'coinjoin' else 0
                    labeled[txid] = label
                elif 'is_coinjoin' in item:
                    label = 1 if bool(item['is_coinjoin']) else 0
                    labeled[txid] = label
        elif isinstance(data, dict):
            # Cho phép format dict txid -> label
            for txid, val in data.items():
                if isinstance(val, str):
                    labeled[txid] = 1 if val.lower() == 'coinjoin' else 0
                else:
                    labeled[txid] = 1 if bool(val) else 0

    return labeled


def evaluate_snapshot(snapshot_path: str, labeled: Dict[str, int]) -> Dict:
    """
    Đánh giá một snapshot trên tập tx đã gán nhãn.
    Chỉ tính trên các tx có nhãn và có trong danh sách processed của snapshot.
    """
    try:
        snap = read_json(snapshot_path)
    except Exception:
        return {'snapshot': os.path.basename(snapshot_path), 'error': 'cannot_read'}

    stats = snap.get('statistics', {}) or {}
    processed: Set[str] = set(stats.get('processed_transactions', []) or [])
    coinjoin_pred: Set[str] = set(stats.get('coinjoin_transactions', []) or [])
    normal_pred: Set[str] = set(stats.get('normal_transactions', []) or [])

    # Giao tập với dữ liệu có nhãn
    eval_txids = [tx for tx in labeled.keys() if tx in processed]
    if not eval_txids:
        return {
            'snapshot': os.path.basename(snapshot_path),
            'evaluated': 0,
            'message': 'no_overlap_with_labeled'
        }

    tp = fp = tn = fn = 0
    for txid in eval_txids:
        y_true = labeled[txid]
        y_pred = 1 if txid in coinjoin_pred else 0 if txid in normal_pred else 0

        if y_true == 1 and y_pred == 1:
            tp += 1
        elif y_true == 0 and y_pred == 1:
            fp += 1
        elif y_true == 0 and y_pred == 0:
            tn += 1
        elif y_true == 1 and y_pred == 0:
            fn += 1

    total = tp + fp + tn + fn
    precision = (tp / (tp + fp)) if (tp + fp) else 0.0
    recall = (tp / (tp + fn)) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = ((tp + tn) / total) if total else 0.0

    return {
        'snapshot': os.path.basename(snapshot_path),
        'evaluated': total,
        'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'accuracy': accuracy,
    }


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(base_dir, 'data', 'models')
    results_dir = os.path.join(base_dir, 'data', 'training_results')

    print('🔎 ĐANG TẢI DỮ LIỆU GÁN NHÃN...')
    labeled = load_labeled_dataset(results_dir)
    print(f'- Tổng tx có nhãn: {len(labeled)}')

    print('\n🧪 ĐÁNH GIÁ TỪNG SNAPSHOT')
    print('=' * 60)
    rows: List[Dict] = []
    for snap_path in scan_models(models_dir):
        res = evaluate_snapshot(snap_path, labeled)
        rows.append(res)
        if 'error' in res:
            print(f"{os.path.basename(snap_path)} -> ERROR: {res['error']}")
        elif res.get('evaluated', 0) == 0:
            print(f"{os.path.basename(snap_path)} -> no labeled overlap")
        else:
            print(f"{os.path.basename(snap_path)} -> F1: {res['f1']:.3f} | P: {res['precision']:.3f} | R: {res['recall']:.3f} | Acc: {res['accuracy']:.3f} | n={res['evaluated']}")

    # Lưu kết quả tổng hợp
    out_path = os.path.join(base_dir, 'data', f'evaluation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'results': rows, 'generated_at': datetime.now().isoformat()}, f, indent=2, ensure_ascii=False)

    # Tìm snapshot tốt nhất theo F1
    scored = [r for r in rows if r.get('evaluated', 0) > 0]
    if scored:
        best = max(scored, key=lambda r: r['f1'])
        print('\n🏆 Snapshot tốt nhất theo F1:')
        print(f"- {best['snapshot']} | F1={best['f1']:.3f} P={best['precision']:.3f} R={best['recall']:.3f} Acc={best['accuracy']:.3f} n={best['evaluated']}")
        print(f"- Lưu chi tiết: {out_path}")
    else:
        print('\n⚠️ Không có snapshot nào giao với tập nhãn. Vui lòng đảm bảo training_results chứa nhãn phù hợp.')


if __name__ == '__main__':
    main()


