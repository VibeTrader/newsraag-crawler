"""
Configuration loader for NewsRagnarok Crawler.
"""
import os
import yaml
from loguru import logger

def load_sources_config(config_path: str) -> list:

    """Loads the sources configuration from the YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if config and 'sources' in config and isinstance(config['sources'], list):
                logger.info(f"Loaded {len(config['sources'])} sources from {config_path}")
                return config['sources']
            else:
                logger.warning(f"Invalid or empty configuration format in {config_path}")
                return []
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        return []
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration file {config_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred loading configuration: {e}")
        return []
