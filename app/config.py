import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///users.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DA_SERVER = os.getenv('DA_SERVER')
    DA_USERNAME = os.getenv('DA_USERNAME')
    DA_PASSWORD = os.getenv('DA_PASSWORD')
    DA_DOMAIN = os.getenv('DA_DOMAIN')
