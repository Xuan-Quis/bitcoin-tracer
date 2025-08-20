#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export/Đóng gói model sang định dạng phổ biến:

- ML models (scikit-learn/xgboost/lightgbm): ONNX (nếu có thư viện), hoặc joblib/pickle.
- Rule-based snapshot (data/models/coinjoin_model_*.json): tạo bundle .zip kèm metadata.

Ví dụ:
  python AI/export_model.py ml --model-dir AI/models --model-name xgboost --out AI/exports
  python AI/export_model.py snapshot --snapshot AI/data/models/coinjoin_model_000600_*.json --out AI/exports
"""

import os
import sys
import json
import argparse
import shutil
from pathlib import Path
from typing import Any, Dict


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def export_snapshot(snapshot_path: Path, out_dir: Path) -> Path:
    ensure_dir(out_dir)
    data = json.loads(Path(snapshot_path).read_text(encoding='utf-8'))

    # Chuẩn hóa metadata tối thiểu
    bundle = {
        'schema_version': 1,
        'type': 'coinjoin_rule_snapshot',
        'model_info': data.get('model_info', {}),
        'detection_parameters': data.get('detection_parameters', {}),
        # Không nhất thiết cần toàn bộ transactions để triển khai
        # nhưng vẫn gói kèm để tái lập kết quả
        'statistics': {
            'processed_transactions': data.get('statistics', {}).get('processed_transactions', []),
            'coinjoin_transactions': data.get('statistics', {}).get('coinjoin_transactions', []),
            'normal_transactions': data.get('statistics', {}).get('normal_transactions', []),
        }
    }

    # Lưu thành file .json và .zip đơn giản
    out_dir = out_dir / 'snapshots'
    ensure_dir(out_dir)
    stem = snapshot_path.stem + '_bundle'
    out_json = out_dir / f'{stem}.json'
    out_zip = out_dir / f'{stem}.zip'
    out_json.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
    # zip chỉ gồm 1 file json để tiện phân phối
    if out_zip.exists():
        out_zip.unlink()
    shutil.make_archive(str(out_zip.with_suffix('')), 'zip', root_dir=out_dir, base_dir=out_json.name)
    return out_zip


def try_import(name: str):
    try:
        return __import__(name)
    except Exception:
        return None


def export_ml(model_dir: Path, model_name: str, out_dir: Path) -> Dict[str, Any]:
    ensure_dir(out_dir)
    model_path = model_dir / model_name / 'model.pkl'
    scaler_path = model_dir / model_name / 'scaler.pkl'
    feature_path = model_dir / model_name / 'feature_names.pkl'
    metadata_path = model_dir / model_name / 'metadata.json'

    if not model_path.exists():
        raise FileNotFoundError(f'Không tìm thấy model tại {model_path}')

    import pickle
    model = pickle.load(open(model_path, 'rb'))
    scaler = None
    features = None
    metadata = {}
    if scaler_path.exists():
        scaler = pickle.load(open(scaler_path, 'rb'))
    if feature_path.exists():
        features = pickle.load(open(feature_path, 'rb'))
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())

    exports = {}

    # 1) Luôn lưu bản sao joblib/pickle đóng gói
    pkg_dir = out_dir / 'ml_packages' / model_name
    ensure_dir(pkg_dir)
    shutil.copy2(model_path, pkg_dir / 'model.pkl')
    if scaler_path.exists():
        shutil.copy2(scaler_path, pkg_dir / 'scaler.pkl')
    if feature_path.exists():
        shutil.copy2(feature_path, pkg_dir / 'feature_names.pkl')
    if metadata_path.exists():
        shutil.copy2(metadata_path, pkg_dir / 'metadata.json')
    exports['pickle_bundle'] = str(pkg_dir)

    # 2) Thử ONNX nếu có thư viện
    skl2onnx = try_import('skl2onnx')
    onnxmltools = try_import('onnxmltools')
    onnx = try_import('onnx')
    numpy = try_import('numpy')

    if numpy is None:
        return exports  # Không thể export ONNX nếu thiếu numpy

    onnx_out_dir = out_dir / 'onnx' / model_name
    ensure_dir(onnx_out_dir)

    X_dummy = None
    if features is not None:
        import numpy as np
        X_dummy = np.zeros((1, len(features)), dtype=float)
    else:
        import numpy as np
        X_dummy = np.zeros((1, 32), dtype=float)  # Fallback

    try:
        # sklearn path
        if skl2onnx is not None:
            from skl2onnx import convert_sklearn
            from skl2onnx.common.data_types import FloatTensorType
            initial_types = [('input', FloatTensorType([None, X_dummy.shape[1]]))]
            onnx_model = convert_sklearn(model, initial_types=initial_types)
            out_path = onnx_out_dir / f'{model_name}.onnx'
            with open(out_path, 'wb') as f:
                f.write(onnx_model.SerializeToString())
            exports['onnx'] = str(out_path)
        # xgboost/lightgbm path via onnxmltools
        elif onnxmltools is not None:
            import onnxmltools
            onnx_model = onnxmltools.convert_lightgbm(model)  # sẽ lỗi nếu không phải lightgbm
            out_path = onnx_out_dir / f'{model_name}.onnx'
            with open(out_path, 'wb') as f:
                f.write(onnx_model.SerializeToString())
            exports['onnx'] = str(out_path)
    except Exception as e:
        exports['onnx_error'] = str(e)

    return exports


def main():
    parser = argparse.ArgumentParser(description='Export/Đóng gói model')
    sub = parser.add_subparsers(dest='mode', required=True)

    p_ml = sub.add_parser('ml', help='Export ML model (sklearn/xgboost/lightgbm)')
    p_ml.add_argument('--model-dir', required=True, help='Thư mục chứa các model (VD: AI/models)')
    p_ml.add_argument('--model-name', required=True, help='Tên model (VD: xgboost)')
    p_ml.add_argument('--out', default='AI/exports', help='Thư mục xuất kết quả')

    p_snap = sub.add_parser('snapshot', help='Đóng gói rule-based snapshot')
    p_snap.add_argument('--snapshot', required=True, help='Đường dẫn file snapshot JSON')
    p_snap.add_argument('--out', default='AI/exports', help='Thư mục xuất kết quả')

    args = parser.parse_args()

    if args.mode == 'ml':
        exports = export_ml(Path(args.model_dir), args.model_name, Path(args.out))
        print(json.dumps({'status': 'ok', 'exports': exports}, indent=2, ensure_ascii=False))
    elif args.mode == 'snapshot':
        out_zip = export_snapshot(Path(args.snapshot), Path(args.out))
        print(json.dumps({'status': 'ok', 'bundle': str(out_zip)}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()


