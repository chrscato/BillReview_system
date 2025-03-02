import os
from pathlib import Path

class Config:
    # Base directory
    BASE_DIR = Path(__file__).parent

    # Logs directory
    LOGS_DIR = BASE_DIR / 'logs'
    LOGS_DIR.mkdir(exist_ok=True)

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', True)

    # CORS settings
    CORS_ORIGINS = ['http://localhost:3000']  # Add production URLs as needed

    # Validation settings
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'json'} 