import json
import os
from pathlib import Path

CONFIG_FILE = 'config.json'

def load_config():
    """Load configuration from JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'AUDIOBOOKSHELF_URL': 'http://localhost:13378',
        'AUDIOBOOKSHELF_TOKEN': ''
    }

def save_config(config):
    """Save configuration to JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
