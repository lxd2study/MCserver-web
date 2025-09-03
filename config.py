import os

class Config:
    SECRET_KEY = '200421lxd'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join('static', 'uploads', 'packs')
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 10240MB max file size
