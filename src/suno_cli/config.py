"""
Configuration file management for suno-cli
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional

import yaml


class ConfigError(Exception):
    """Base exception for config errors"""
    pass


class Config:
    """Configuration manager for suno-cli"""

    DEFAULT_CONFIG_PATH = Path.home() / ".suno-cli" / "config.yaml"

    # Default values
    DEFAULTS = {
        "default_model": "V4_5ALL",
        "default_gender": "male",
        "default_output_dir": None,
        "default_artist": "Suno AI",
        "default_album": None,
        "api_key": None,
        "callback_url": None,
        "poll_interval": 10,
        "max_wait": 600,
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config manager

        Args:
            config_path: Path to config file (default: ~/.suno-cli/config.yaml)
        """
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self.config_data = {}

        if self.config_path.exists():
            self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f) or {}

            # Substitute environment variables
            self.config_data = self._substitute_env_vars(raw_config)

        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}")

    def _substitute_env_vars(self, data: Any) -> Any:
        """
        Recursively substitute environment variables in config

        Supports ${VAR_NAME} syntax
        """
        if isinstance(data, dict):
            return {k: self._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Replace ${VAR} with environment variable value
            def replace_env(match):
                var_name = match.group(1)
                return os.getenv(var_name, match.group(0))

            return re.sub(r'\$\{([^}]+)\}', replace_env, data)
        else:
            return data

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get config value with fallback to defaults

        Priority: config file > DEFAULTS > provided default

        Args:
            key: Config key
            default: Fallback value if not in config or DEFAULTS

        Returns:
            Config value
        """
        if key in self.config_data:
            return self.config_data[key]
        elif key in self.DEFAULTS:
            return self.DEFAULTS[key]
        else:
            return default

    def get_all(self) -> Dict[str, Any]:
        """
        Get all config values merged with defaults

        Returns:
            Dict with all config values
        """
        merged = self.DEFAULTS.copy()
        merged.update(self.config_data)
        return merged

    @classmethod
    def create_default_config(cls, path: Optional[Path] = None) -> None:
        """
        Create a default config file

        Args:
            path: Path to create config (default: ~/.suno-cli/config.yaml)
        """
        config_path = path or cls.DEFAULT_CONFIG_PATH

        # Create directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Default config template
        default_config = """# suno-cli configuration file
# Place this at ~/.suno-cli/config.yaml

# Default AI model to use
# Options: V5, V4_5PLUS, V4_5ALL, V4_5, V4
default_model: V4_5ALL

# Default vocal gender
# Options: male, female
default_gender: male

# Default output directory (optional)
# If not set, you must specify -o/--output for each command
# default_output_dir: ~/Music/generated

# Default artist name for ID3 tags
default_artist: Suno AI

# Default album name for ID3 tags (optional)
# default_album: My Album

# API key (use environment variable substitution)
# You can also set SUNO_API_KEY environment variable directly
api_key: ${SUNO_API_KEY}

# Optional callback URL for async notifications
# callback_url: https://example.com/callback

# Polling settings
poll_interval: 10  # seconds between status checks
max_wait: 600      # maximum wait time in seconds
"""

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(default_config)
