"""
ML Detector adapter – optional model-based CoinJoin detection.
Tries to load a trained model from inference layer. If unavailable, returns None.
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import os
import glob
import json

_PREDICTOR = None
_LOAD_ERROR = None
_JSON_MODEL = None


def _try_load_predictor() -> Optional[Any]:
    global _PREDICTOR, _LOAD_ERROR
    if _PREDICTOR is not None or _LOAD_ERROR is not None:
        return _PREDICTOR
    # Try real Python predictor first
    try:
        from inference.coinjoin_predictor import CoinJoinPredictor
        _PREDICTOR = CoinJoinPredictor(model_dir="data/models")
        return _PREDICTOR
    except Exception as e:
        _LOAD_ERROR = e
    # Fallback: JSON snapshot predictor
    try:
        model = _try_load_json_model()
        if model is not None:
            _PREDICTOR = JsonPredictor(model)
            _LOAD_ERROR = None
            return _PREDICTOR
    except Exception as je:
        _LOAD_ERROR = _LOAD_ERROR or je
    return None


def _try_load_json_model() -> Optional[Dict[str, Any]]:
    global _JSON_MODEL
    if _JSON_MODEL is not None:
        return _JSON_MODEL
    patterns = [
        os.path.join("data", "models", "coinjoin_model_*.json"),
        os.path.join("data", "models", "coinjoin_model_merged_*.json"),
    ]
    files: list[str] = []
    for pat in patterns:
        files.extend(glob.glob(pat))
    if not files:
        return None
    files.sort()
    latest = files[-1]
    with open(latest, "r", encoding="utf-8") as f:
        _JSON_MODEL = json.load(f)
    return _JSON_MODEL


class JsonPredictor:
    """Lightweight predictor backed by JSON snapshot parameters.
    Not a trained ML model; derives probability from heuristic scores
    and thresholds contained in the JSON.
    """
    def __init__(self, model: Dict[str, Any]):
        self.model = model or {}
        self.params = self.model.get("detection_parameters", {}) or {}
        self.info = self.model.get("model_info", {}) or {}
        self.stats = self.model.get("statistics", {}) or {}

    def predict_from_tx(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        # Import here to avoid circular deps at module import time
        from api.detector_adapter import detect_coinjoin
        h = detect_coinjoin(tx) or {}
        wasabi = bool(h.get("wasabi_detected"))
        samourai = bool(h.get("samourai_detected"))
        score = float(h.get("score", 0.0) or 0.0)
        uni = float(h.get("uniformity_score", 0.0) or 0.0)
        div = float(h.get("diversity_score", 0.0) or 0.0)

        # Base probability rules
        if wasabi or samourai:
            proba = 0.97
        else:
            thr = float(self.params.get("our_score_threshold", 0.7) or 0.7)
            if thr > 0:
                proba = min(0.99, score / thr)
            else:
                proba = min(0.99, 0.5 * uni + 0.5 * div)

        # Optional calibration by detection rate
        det_rate = None
        try:
            det_rate = float(self.info.get("detection_rate"))
        except Exception:
            det_rate = None
        if det_rate is not None and 0.05 <= det_rate <= 0.95:
            proba = float(0.5 * proba + 0.5 * det_rate)

        return {
            "prob": proba,
            "probability": proba,
            "score": score,
            "wasabi": wasabi,
            "samourai": samourai,
            "model": "json_snapshot",
        }


def predict_with_model(tx: Dict, threshold: float = 0.7) -> Optional[Dict]:
    """Run ML prediction on a raw tx dict.

    Returns a dict with keys: is_coinjoin, probability, model_name
    or None if model not available.
    """
    predictor = _try_load_predictor()
    if predictor is None:
        return None

    # The predictor API may vary; we try a few common patterns.
    proba = None
    model_name = getattr(predictor, "model_name", "ml_model")

    try:
        # Prefer dedicated method if exposed
        if hasattr(predictor, "predict_from_tx"):
            res = predictor.predict_from_tx(tx)
            # res could be dict with 'prob' or 'probability'
            proba = res.get("prob") or res.get("probability") or res.get("score")
        elif hasattr(predictor, "predict_dict"):
            res = predictor.predict_dict(tx)
            proba = res.get("prob") or res.get("probability") or res.get("score")
        elif hasattr(predictor, "predict"):
            # Some predictors return dict directly
            res = predictor.predict(tx)
            if isinstance(res, dict):
                proba = res.get("prob") or res.get("probability") or res.get("score")
            else:
                # Fallback: treat non-dict as probability if numeric
                try:
                    proba = float(res)
                except Exception:
                    proba = None
        elif isinstance(predictor, JsonPredictor):
            res = predictor.predict_from_tx(tx)
            proba = res.get("prob") or res.get("probability") or res.get("score")
            model_name = "json_snapshot"
    except Exception:
        proba = None

    if proba is None:
        return None

    is_cj = bool(proba >= threshold)
    return {
        "is_coinjoin": is_cj,
        "probability": float(proba),
        "model_name": model_name,
        "threshold": float(threshold),
    }


def preload_model() -> bool:
    """Force-load the predictor at API startup. Returns True if loaded."""
    return _try_load_predictor() is not None


def is_model_loaded() -> bool:
    """Check whether the predictor is currently loaded in memory."""
    return _PREDICTOR is not None


def last_model_error() -> Optional[str]:
    """Get the last model loading error (string) if any."""
    return str(_LOAD_ERROR) if _LOAD_ERROR else None

