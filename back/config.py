class Config:

    DB_HOST = '192.168.28.135'
    DB_PORT = '5432'
    DB_NAME = 'companylink'
    DB_USER = 'myuser'
    DB_PASSWORD = '123456abc.'
    client_encoding='utf8'
    

    
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?client_encoding=utf8'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key-here' 