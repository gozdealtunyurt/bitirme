"""
Veritabanı ve tabloları oluşturur.
Çalıştır: python db_setup.py
"""
import mysql.connector
from db_config import DB_CONFIG


def create_database():
    config = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE DATABASE IF NOT EXISTS mahalle_score "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.close()
    conn.close()
    print("Veritabanı oluşturuldu: mahalle_score")


def create_tables():
    from db_config import get_connection
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Mahalleler — centroid + yaklasik_alan kolonları
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mahalleler (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            sehir         VARCHAR(100) NOT NULL,
            ilce          VARCHAR(100) NOT NULL,
            mahalle       VARCHAR(200) NOT NULL,
            centroid_lat  DOUBLE DEFAULT NULL,
            centroid_lon  DOUBLE DEFAULT NULL,
            yaklasik_alan TINYINT(1) DEFAULT 0,
            last_fetched  DATETIME DEFAULT NULL,
            UNIQUE KEY unique_mahalle (sehir, ilce, mahalle)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # Mevcut tabloya eksik kolonları ekle (zaten varsa hata vermez)
    yeni_kolonlar = [
        ("centroid_lat",  "DOUBLE DEFAULT NULL AFTER mahalle"),
        ("centroid_lon",  "DOUBLE DEFAULT NULL AFTER centroid_lat"),
        ("yaklasik_alan", "TINYINT(1) DEFAULT 0 AFTER centroid_lon"),
    ]
    for col, definition in yeni_kolonlar:
        try:
            cursor.execute(f"ALTER TABLE mahalleler ADD COLUMN {col} {definition}")
            print(f"  Kolon eklendi: {col}")
        except Exception:
            pass  # Zaten varsa geç

    # 2. Kategori verileri
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kategori_verileri (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            mahalle_id INT NOT NULL,
            kategori   ENUM('saglik','egitim','yesil_alan','ulasim','sosyal_imkanlar') NOT NULL,
            osm_id     BIGINT DEFAULT NULL,
            isim       VARCHAR(300) DEFAULT NULL,
            tip        VARCHAR(100) DEFAULT NULL,
            lat        DOUBLE DEFAULT NULL,
            lon        DOUBLE DEFAULT NULL,
            FOREIGN KEY (mahalle_id) REFERENCES mahalleler(id) ON DELETE CASCADE,
            INDEX idx_mahalle_kategori (mahalle_id, kategori)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # 3. Skor tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skorlar (
            id                     INT AUTO_INCREMENT PRIMARY KEY,
            mahalle_id             INT NOT NULL UNIQUE,
            saglik                 INT DEFAULT 0,
            egitim                 INT DEFAULT 0,
            yesil_alan             INT DEFAULT 0,
            ulasim                 INT DEFAULT 0,
            sosyal_imkanlar        INT DEFAULT 0,
            toplam_skor            INT DEFAULT 0,
            saglik_detay           JSON DEFAULT NULL,
            egitim_detay           JSON DEFAULT NULL,
            yesil_alan_detay       JSON DEFAULT NULL,
            ulasim_detay           JSON DEFAULT NULL,
            sosyal_imkanlar_detay  JSON DEFAULT NULL,
            FOREIGN KEY (mahalle_id) REFERENCES mahalleler(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # 4. Kullanıcı puanlamaları
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kullanici_puanlari (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            mahalle_id      INT NOT NULL,
            kullanici_adi   VARCHAR(100) NOT NULL,
            saglik_puan     TINYINT DEFAULT NULL CHECK (saglik_puan BETWEEN 1 AND 5),
            egitim_puan     TINYINT DEFAULT NULL CHECK (egitim_puan BETWEEN 1 AND 5),
            yesil_alan_puan TINYINT DEFAULT NULL CHECK (yesil_alan_puan BETWEEN 1 AND 5),
            ulasim_puan     TINYINT DEFAULT NULL CHECK (ulasim_puan BETWEEN 1 AND 5),
            sosyal_puan     TINYINT DEFAULT NULL CHECK (sosyal_puan BETWEEN 1 AND 5),
            genel_puan      TINYINT DEFAULT NULL CHECK (genel_puan BETWEEN 1 AND 5),
            yorum           TEXT DEFAULT NULL,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mahalle_id) REFERENCES mahalleler(id) ON DELETE CASCADE,
            INDEX idx_mahalle_puan (mahalle_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # 5. Location cache (geriye dönük uyumluluk)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_cache (
            anahtar  VARCHAR(300) PRIMARY KEY,
            deger    LONGTEXT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("Tablolar hazır.")


if __name__ == "__main__":
    create_database()
    create_tables()
    print("Veritabanı kurulumu tamamlandı.")