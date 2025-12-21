import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent

# Load configuration
def _deep_update(d, u):
    """Recursively update dictionary d with values from u."""
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = _deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

def load_config():
    """Load configuration with defaults."""
    # Default configuration
    default_config = {
        'model': 'gpt-4',
        'temperature': 0.7,
        'max_tokens': 2000,
        'boot_doc_path': str(PROJECT_ROOT / 'bootdocs' / 'clarity_os_boot_v1.txt')
        # Memory configuration is not included by default
    }
    
    config_path = PROJECT_ROOT / 'config' / 'config.json'
    
    try:
        if config_path.exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Deep merge user config with defaults
                _deep_update(default_config, user_config)
    except Exception as e:
        print(f"Warning: Error loading config file: {e}. Using defaults.")
    
    # Ensure boot_doc_path is absolute
    if not Path(default_config['boot_doc_path']).is_absolute():
        default_config['boot_doc_path'] = str(PROJECT_ROOT / default_config['boot_doc_path'])
    
    return default_config

# Get API key
def get_api_key():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key and os.path.exists(env_path):
        load_dotenv(env_path)
        api_key = os.getenv('OPENAI_API_KEY')
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError(
        "\nOPENAI_API_KEY not found in environment variables.\n"
        "Please check that:\n"
        "1. The .env file exists in the project root directory\n"
        "2. It contains a line like: OPENAI_API_KEY=your-key-here\n"
        "3. There are no spaces around the = sign\n"
        "4. The file is saved as plain text (not .env.txt or similar)"
    )
    return api_key

LOGS_DIR = PROJECT_ROOT / 'logs'
LOGS_DIR.mkdir(exist_ok=True)
(LOGS_DIR / '.gitkeep').touch(exist_ok=True)
