#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Neo4j connectivity check.
Priority for credentials:
1) CLI args
2) docker-compose.yml (NEO4J_AUTH)
3) config/api_config.yaml

Usage examples:
  python neo4j_ping.py
  python neo4j_ping.py --uri bolt://192.168.100.128:7687 --user neo4j --password password123
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional, Tuple

import yaml
from neo4j import GraphDatabase


def load_api_config() -> Tuple[Optional[str], Optional[str], Optional[str]]:
	cfg_path = Path("config/api_config.yaml")
	if not cfg_path.exists():
		return None, None, None
	try:
		data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
		neo4j_cfg = (data or {}).get("neo4j", {}) or {}
		return (
			neo4j_cfg.get("uri"),
			neo4j_cfg.get("user"),
			neo4j_cfg.get("password"),
		)
	except Exception:
		return None, None, None


def load_password_from_docker_compose() -> Optional[str]:
	"""Try to read NEO4J_AUTH=neo4j/password from docker-compose.yml; return password part."""
	for rel in ("docker-compose.yml", "./docker-compose.yml", "../docker-compose.yml"):
		p = Path(rel)
		if not p.exists():
			continue
		try:
			doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
			services = doc.get("services", {}) or {}
			for name, cfg in services.items():
				if "neo4j" in str(name).lower():
					envs = cfg.get("environment", {})
					if isinstance(envs, dict):
						auth = envs.get("NEO4J_AUTH") or envs.get("neo4j_auth")
						if isinstance(auth, str) and "/" in auth:
							return auth.split("/", 1)[1]
					elif isinstance(envs, list):
						for item in envs:
							if isinstance(item, str) and item.startswith("NEO4J_AUTH="):
								val = item.split("=", 1)[1]
								if "/" in val:
									return val.split("/", 1)[1]
		except Exception:
			continue
	return None


def main() -> int:
	parser = argparse.ArgumentParser(description="Neo4j connectivity check")
	parser.add_argument("--uri", default=None, help="Bolt URI, e.g. bolt://192.168.100.128:7687")
	parser.add_argument("--user", default=None, help="Username, e.g. neo4j")
	parser.add_argument("--password", default=None, help="Password")
	args = parser.parse_args()

	# Load from config as fallback
	cfg_uri, cfg_user, cfg_pass = load_api_config()

	# Docker compose password override
	dc_pass = load_password_from_docker_compose()

	uri = args.uri or cfg_uri or os.getenv("NEO4J_URI", "bolt://192.168.100.128:7687")
	user = args.user or cfg_user or os.getenv("NEO4J_USER", "neo4j")
	password = args.password or dc_pass or cfg_pass or os.getenv("NEO4J_PASSWORD") or "password"

	print(f"Connecting to Neo4j: uri={uri}, user={user}")
	try:
		driver = GraphDatabase.driver(uri, auth=(user, password))
		with driver.session() as session:
			res = session.run("RETURN 1 AS ok")
			rec = res.single()
			ok = rec and rec.get("ok") == 1
			print("✅ Connected" if ok else "⚠️ Query failed")
			return 0 if ok else 2
	except Exception as e:
		print(f"❌ Connection failed: {e}")
		return 1


if __name__ == "__main__":
	sys.exit(main())
