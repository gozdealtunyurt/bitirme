import os
import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "gözde",       
    "database": "mahalle_score",
    "charset": "utf8mb4",
}

DB_CONFIG.update({
    "host": os.environ.get("DB_HOST", DB_CONFIG["host"]),
    "user": os.environ.get("DB_USER", DB_CONFIG["user"]),
    "password": os.environ.get("DB_PASSWORD", DB_CONFIG["password"]),
    "database": os.environ.get("DB_NAME", DB_CONFIG["database"]),
    "port": int(os.environ.get("DB_PORT", "3306")),
})

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)
