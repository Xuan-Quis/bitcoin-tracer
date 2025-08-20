"""
Detector Adapter - Heuristic CoinJoin detection (Wasabi / Samourai / Custom)
"""

from typing import Dict, List
from collections import defaultdict

SATOSHI_IN_BTC = 100_000_000

# Wasabi constants
WASABI_APPROX_BASE_DENOM = int(0.1 * SATOSHI_IN_BTC)
WASABI_MAX_PRECISION = int(0.02 * SATOSHI_IN_BTC)
WASABI_COORD_ADDRESSES = {
	'bc1qs604c7jv6amk4cxqlnvuxv26hv3e48cds4m0ew',
	'bc1qa24tsgchvuxsaccp8vrnkfd85hrcpafg20kmjw'
}

# Samourai constants
SAMOURAI_WHIRLPOOL_SIZES = [
	int(0.001 * SATOSHI_IN_BTC),
	int(0.01 * SATOSHI_IN_BTC),
	int(0.05 * SATOSHI_IN_BTC),
	int(0.5 * SATOSHI_IN_BTC)
]
SAMOURAI_MAX_POOL_FEE = int(0.0011 * SATOSHI_IN_BTC)

# Custom thresholds
OUR_MIN_INPUTS = 5
OUR_MIN_OUTPUTS = 5
OUR_UNIFORMITY_THRESHOLD = 0.8
OUR_DIVERSITY_THRESHOLD = 0.7


def detect_coinjoin(tx: Dict) -> Dict:
	"""Detect CoinJoin on a raw tx dict from Blockstream /tx/{txid}.
	Returns a dict with keys: is_coinjoin, detection_method, score, reasons, indicators.
	"""
	vin = tx.get('vin', []) or []
	vout = tx.get('vout', []) or []

	input_addresses: List[str] = []
	output_addresses: List[str] = []
	input_values: List[int] = []
	output_values: List[int] = []

	for item in vin:
		prev = item.get('prevout') or {}
		addr = prev.get('scriptpubkey_address')
		if addr:
			input_addresses.append(addr)
		val = prev.get('value')
		if isinstance(val, int):
			input_values.append(val)

	for item in vout:
		addr = item.get('scriptpubkey_address')
		if addr:
			output_addresses.append(addr)
		val = item.get('value')
		if isinstance(val, int):
			output_values.append(val)

	input_count = len(input_addresses)
	output_count = len(output_values)

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

	# Wasabi detection
	value_counts = defaultdict(int)
	for v in output_values:
		value_counts[v] += 1

	wasabi_detected = False
	wasabi_reasons: List[str] = []
	if value_counts:
		most_val, most_cnt = max(value_counts.items(), key=lambda x: x[1])
		has_wasabi_coord = any(addr in WASABI_COORD_ADDRESSES for addr in output_addresses)
		wasabi_heuristic = (
			input_count >= most_cnt >= 10 and
			abs(WASABI_APPROX_BASE_DENOM - most_val) <= WASABI_MAX_PRECISION
		)
		wasabi_static = has_wasabi_coord and any(cnt > 2 for cnt in value_counts.values())
		if wasabi_heuristic or wasabi_static:
			wasabi_detected = True
			if wasabi_static:
				wasabi_reasons.append("Wasabi static (coordinator + equal outputs)")
			if wasabi_heuristic:
				wasabi_reasons.append("Wasabi heuristic (0.1 BTC pattern)")

	# Samourai detection
	samourai_detected = False
	samourai_reasons: List[str] = []
	if input_count == 5 and output_count == 5 and len(set(output_values)) == 1 and output_values:
		ov = output_values[0]
		for size in SAMOURAI_WHIRLPOOL_SIZES:
			if abs(ov - size) <= int(0.01 * SATOSHI_IN_BTC) or abs(ov - size) <= SAMOURAI_MAX_POOL_FEE:
				samourai_detected = True
				samourai_reasons.append(f"Samourai Whirlpool ({size / SATOSHI_IN_BTC} BTC)")
				break

	# Our custom detection
	uniformity_score = (max(value_counts.values()) / len(output_values)) if output_values else 0.0
	diversity_score = (unique_input_addresses / len(input_addresses)) if input_addresses else 0.0

	our_score = 0.0
	our_reasons: List[str] = []
	if input_count >= OUR_MIN_INPUTS:
		our_score += 0.15
		our_reasons.append(f"Sufficient inputs ({input_count})")
	if output_count >= OUR_MIN_OUTPUTS:
		our_score += 0.15
		our_reasons.append(f"Sufficient outputs ({output_count})")
	if uniformity_score >= OUR_UNIFORMITY_THRESHOLD:
		our_score += 0.25
		our_reasons.append(f"High output uniformity ({uniformity_score:.2f})")
	if diversity_score >= OUR_DIVERSITY_THRESHOLD:
		our_score += 0.20
		our_reasons.append(f"High input diversity ({diversity_score:.2f})")
	if indicators['transaction_size'] > 200:
		our_score -= 0.10
		our_reasons.append("Very large transaction (possible exchange)")
	if (uniformity_score >= 0.9 and diversity_score >= 0.8 and input_count >= 10 and output_count >= 10):
		our_score += 0.15
		our_reasons.append("Perfect CoinJoin pattern")
	our_score = max(0.0, min(our_score, 1.0))

	# Final decision priority
	is_coinjoin = False
	detection_method = 'none'
	final_reasons: List[str] = []
	if wasabi_detected:
		is_coinjoin = True
		detection_method = 'wasabi'
		final_reasons.extend(wasabi_reasons)
	elif samourai_detected:
		is_coinjoin = True
		detection_method = 'samourai'
		final_reasons.extend(samourai_reasons)
	elif our_score >= 0.7:
		is_coinjoin = True
		detection_method = 'our_custom'
		final_reasons.extend(our_reasons)

	return {
		'is_coinjoin': is_coinjoin,
		'detection_method': detection_method,
		'score': our_score,
		'reasons': final_reasons,
		'indicators': indicators,
		'uniformity_score': uniformity_score,
		'diversity_score': diversity_score,
		'wasabi_detected': wasabi_detected,
		'samourai_detected': samourai_detected
	}
