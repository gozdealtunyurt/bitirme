import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "gözde",       
    "database": "mahalle_score",
    "charset": "utf8mb4",
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)
