import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
if os.path.exists('.env'):
    load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Leaseweb Object Storage Configuration
LEASEWEB_CONFIG = {
    'endpoint_url': os.getenv('LEASEWEB_ENDPOINT_URL', 'https://nl.object-storage.io'),
    'bucket_name': os.getenv('LEASEWEB_BUCKET_NAME', 'private-bucket-nl'),
    'access_key': os.getenv('LEASEWEB_ACCESS_KEY'),
    'secret_key': os.getenv('LEASEWEB_SECRET_KEY'),
    'region': os.getenv('LEASEWEB_REGION', 'nl')
}

# Validate required configuration
if not LEASEWEB_CONFIG['access_key'] or not LEASEWEB_CONFIG['secret_key']:
    raise ValueError("Missing required environment variables: LEASEWEB_ACCESS_KEY and/or LEASEWEB_SECRET_KEY")

# Directory Configuration
INPUT_DIR = BASE_DIR / 'input'
OUTPUT_DIR = BASE_DIR / 'output'

# FFmpeg Configuration (optional in production)
FFMPEG_PATH = os.getenv('FFMPEG_PATH', r"C:\ffmpeg\ffmpeg.exe")
SEGMENT_DURATION = int(os.getenv('SEGMENT_DURATION', '6'))
KEY_LENGTH = int(os.getenv('KEY_LENGTH', '16'))  # 128-bit key 