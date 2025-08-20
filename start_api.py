#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script khởi động CoinJoin Detection API
"""

import asyncio
import uvicorn
import yaml
import os
from pathlib import Path

from api.rest_api import app
from utils.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

def load_docker_compose_password():
    """Đọc password Neo4j từ docker-compose file"""
    try:
        # Tìm file docker-compose.yml
        docker_compose_path = None
        for path in ["./docker-compose.yml", "../docker-compose.yml", "../../docker-compose.yml"]:
            if os.path.exists(path):
                docker_compose_path = path
                break
        
        if docker_compose_path:
            with open(docker_compose_path, 'r') as f:
                docker_compose = yaml.safe_load(f)
                
            # Tìm Neo4j service và password
            if 'services' in docker_compose:
                for service_name, service_config in docker_compose['services'].items():
                    if 'neo4j' in service_name.lower():
                        if 'environment' in service_config:
                            envs = service_config['environment']
                            # envs có thể là list hoặc dict
                            if isinstance(envs, dict):
                                auth = envs.get('NEO4J_AUTH') or envs.get('neo4j_auth')
                                if auth and isinstance(auth, str) and '/' in auth:
                                    return auth.split('/', 1)[1]
                            elif isinstance(envs, list):
                                for env_var in envs:
                                    if isinstance(env_var, str) and env_var.startswith('NEO4J_AUTH='):
                                        auth_val = env_var.split('=', 1)[1]
                                        if '/' in auth_val:
                                            return auth_val.split('/', 1)[1]
        
        logger.warning("Không tìm thấy password Neo4j trong docker-compose, sử dụng default")
        return "password"
        
    except Exception as e:
        logger.error(f"Lỗi đọc docker-compose: {e}")
        return "password"

def update_config_with_password():
    """Cập nhật config với password từ docker-compose"""
    password = load_docker_compose_password()
    
    # Cập nhật config
    config = Config()
    config.set('neo4j_password', password)
    
    logger.info(f"Đã cập nhật Neo4j password: {password[:3]}***")

async def main():
    """Main function"""
    print("🚀 Khởi động CoinJoin Detection API...")
    
    # Cập nhật password Neo4j
    update_config_with_password()
    
    # Tạo thư mục logs nếu chưa có
    os.makedirs("logs", exist_ok=True)
    
    # Load config
    config = Config()
    
    # Start API server
    host = config.get('server_host', '0.0.0.0')
    port = config.get('server_port', 8000)
    debug = config.get('server_debug', True)
    
    print(f"📡 API sẽ chạy tại: http://{host}:{port}")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    print(f"🔍 Health Check: http://{host}:{port}/health")
    
    # Start server
    uvicorn.run(
        "api.rest_api:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )

if __name__ == "__main__":
    asyncio.run(main())
