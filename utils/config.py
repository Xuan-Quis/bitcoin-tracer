"""
Configuration management cho AI Investigation
"""

import yaml
import os
from typing import Any, Dict, Optional

class Config:
    """Configuration management class"""
    
    def __init__(self, config_dict: Dict[str, Any] = None):
        self._config = config_dict or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self._config[key] = value
    
    def update(self, config_dict: Dict[str, Any]):
        """Update configuration with dictionary"""
        self._config.update(config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self._config.copy()
    
    @classmethod
    def from_file(cls, file_path: str) -> 'Config':
        """Load configuration from YAML file"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        return cls(config_dict)
    
    def save_to_file(self, file_path: str):
        """Save configuration to YAML file"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False, indent=2)
    
    def __str__(self) -> str:
        return f"Config({self._config})"
    
    def __repr__(self) -> str:
        return self.__str__()
