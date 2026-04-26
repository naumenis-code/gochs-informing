# Configuration settings for the application

# Load environment variables
import os

class Config:
    DEBUG = os.environ.get('DEBUG', False)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('SECRET_KEY')
