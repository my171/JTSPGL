# -*- coding: utf-8 -*-
class Config:

    DB_HOST = 'localhost'
    DB_PORT = '3306'
    DB_NAME = 'company'
    DB_USER = 'root'
    DB_PASSWORD = 'ab12AB!@'
    client_encoding='utf8'
    
    SQLALCHEMY_DATABASE_URI = f'mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?client_encoding=utf8'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key-here' 