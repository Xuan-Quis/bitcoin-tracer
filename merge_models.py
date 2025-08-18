#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge multiple CoinJoin model snapshots into one consolidated snapshot.

Hợp nhất nhiều model snapshot thành một model tổng hợp bằng chiến lược
"majority vote" (bỏ phiếu đa số) trên từng giao dịch.

Đầu ra được lưu vào data/models/coinjoin_model_merged_<timestamp>.json
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Tuple


def read_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: str, data: dict):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def scan_model_files(models_dir: str) -> List[str]:
    files: List[str] = []
    if not os.path.exists(models_dir):
        return files
    for name in os.listdir(models_dir):
        if name.startswith('coinjoin_model_') and name.endswith('.json'):
            files.append(os.path.join(models_dir, name))
    files.sort()
    return files


def choose_detection_parameters(models: List[Tuple[str, dict]]) -> dict:
    """Chọn detection_parameters phổ biến nhất; nếu không, dùng bản mới nhất."""
    signature_to_params: Dict[str, Tuple[dict, int]] = {}
    for _, data in models:
        params = data.get('detection_parameters', {}) or {}
        # Tạo chữ ký ổn định cho dict
        signature = json.dumps(params, sort_keys=True)
        if signature not in signature_to_params:
            signature_to_params[signature] = (params, 0)
        signature_to_params[signature] = (signature_to_params[signature][0], signature_to_params[signature][1] + 1)

    if not signature_to_params:
        return {}

    # Lấy tham số xuất hiện nhiều nhất
    most_common_signature = max(signature_to_params.items(), key=lambda kv: kv[1][1])[0]
    chosen_params = signature_to_params[most_common_signature][0]
    return chosen_params


def merge_snapshots(base_dir: str = '.') -> Tuple[dict, str]:
    models_dir = os.path.join(base_dir, 'data', 'models')
    model_files = scan_model_files(models_dir)

    if not model_files:
        raise FileNotFoundError('Không tìm thấy file model nào trong data/models')

    # Đọc toàn bộ model
    models: List[Tuple[str, dict]] = []
    for path in model_files:
        try:
            models.append((path, read_json(path)))
        except Exception:
            # Bỏ qua file lỗi
            pass

    # Ghi nhận thứ tự (ưu tiên bản mới hơn khi hòa phiếu)
    file_to_rank: Dict[str, int] = {path: idx for idx, (path, _) in enumerate(models)}

    # Tổng hợp phiếu
    tx_votes: Dict[str, Dict[str, int]] = {}
    processed_union: set = set()

    for path, data in models:
        stats = data.get('statistics', {}) or {}
        processed = stats.get('processed_transactions', []) or []
        coinjoin_list = stats.get('coinjoin_transactions', []) or []
        normal_list = stats.get('normal_transactions', []) or []

        processed_union.update(processed)

        for txid in coinjoin_list:
            votes = tx_votes.setdefault(txid, {'coinjoin': 0, 'normal': 0, 'last_seen_rank': -1, 'last_seen_label': None, 'last_seen_file': None})
            votes['coinjoin'] += 1
            # ưu tiên nhãn của file mới hơn
            if file_to_rank[path] > votes['last_seen_rank']:
                votes['last_seen_rank'] = file_to_rank[path]
                votes['last_seen_label'] = 'coinjoin'
                votes['last_seen_file'] = path

        for txid in normal_list:
            votes = tx_votes.setdefault(txid, {'coinjoin': 0, 'normal': 0, 'last_seen_rank': -1, 'last_seen_label': None, 'last_seen_file': None})
            votes['normal'] += 1
            if file_to_rank[path] > votes['last_seen_rank']:
                votes['last_seen_rank'] = file_to_rank[path]
                votes['last_seen_label'] = 'normal'
                votes['last_seen_file'] = path

    # Quyết định nhãn cuối cùng theo majority vote, hòa thì lấy nhãn gần nhất (bản mới nhất)
    merged_coinjoin: List[str] = []
    merged_normal: List[str] = []

    for txid in processed_union:
        votes = tx_votes.get(txid, None)
        if not votes:
            # Nếu không có phiếu rõ ràng, mặc định là normal (bảo thủ)
            merged_normal.append(txid)
            continue

        if votes['coinjoin'] > votes['normal']:
            merged_coinjoin.append(txid)
        elif votes['normal'] > votes['coinjoin']:
            merged_normal.append(txid)
        else:
            # Hòa phiếu
            if votes['last_seen_label'] == 'coinjoin':
                merged_coinjoin.append(txid)
            else:
                merged_normal.append(txid)

    merged_coinjoin = sorted(set(merged_coinjoin))
    merged_normal = sorted(set(merged_normal))
    processed_sorted = sorted(processed_union)

    # Tham số phát hiện: chọn phổ biến nhất
    detection_parameters = choose_detection_parameters(models)

    # model_info hợp nhất
    total_processed = len(processed_sorted)
    total_coinjoin = len(merged_coinjoin)
    total_normal = len(merged_normal)
    detection_rate = (total_coinjoin / total_processed) if total_processed else 0.0

    now_tag = datetime.now().strftime('%Y%m%d_%H%M%S')
    merged_info = {
        'model_info': {
            'tx_count': total_processed,
            'total_processed': total_processed,
            'total_coinjoin': total_coinjoin,
            'total_normal': total_normal,
            'errors': 0,
            'detection_rate': detection_rate,
            'timestamp': now_tag,
            'model_version': 'merged_from_snapshots_v1',
        },
        'detection_parameters': detection_parameters,
        'statistics': {
            'processed_transactions': processed_sorted,
            'coinjoin_transactions': merged_coinjoin,
            'normal_transactions': merged_normal,
        },
        'merge_info': {
            'source_files': [path for path, _ in models],
            'strategy': 'majority_vote_then_latest_wins_on_tie',
        }
    }

    out_dir = os.path.join(base_dir, 'data', 'models')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'coinjoin_model_merged_{now_tag}.json')
    write_json(out_path, merged_info)

    return merged_info, out_path


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    merged, out_path = merge_snapshots(base_dir)

    # In tóm tắt (ASCII thân thiện PowerShell)
    print('MERGE MODELS SUMMARY')
    print('=' * 60)
    print(f"Snapshots merged: {len(merged['merge_info']['source_files'])}")
    print(f"Output: {out_path}")
    mi = merged['model_info']
    print(f"Total processed: {mi['total_processed']}")
    print(f"CoinJoin: {mi['total_coinjoin']}  Normal: {mi['total_normal']}")
    print(f"Detection rate: {mi['detection_rate']:.4f}")
    print(f"Version: {mi['model_version']}  Timestamp: {mi['timestamp']}")


if __name__ == '__main__':
    main()


