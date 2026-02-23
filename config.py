import os
import json

CONFIG_FILE = "hoverdesk_config.json"

DEFAULT_CONFIG = {
    "mode": "safe",
    "idle_time": 3,
    "enabled": True,
    "fade_duration": 400
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            # Merge with defaults to ensure all keys exist
            config = DEFAULT_CONFIG.copy()
            config.update(data)
            return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config_dict):
    try:
        # Atomic write (mostly safe on Windows without temp files for simple configs)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_dict, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")
