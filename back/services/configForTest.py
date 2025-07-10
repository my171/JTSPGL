# -*- coding: utf-8 -*-
class Config:

    DB_HOST = '172.0.0.1'
    DB_PORT = '3306'
    DB_NAME = 'mysqldemo'
    DB_USER = 'root'
    DB_PASSWORD = 'DSds178200++'
    client_encoding='utf8'
    
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?client_encoding=utf8'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key-here' 