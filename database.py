import sqlite3

def init_db():
    with sqlite3.connect('medical_ai.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS kullanicilar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL,
                soyad TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                sifre_hash TEXT NOT NULL,
                meslek_dali TEXT,
                kayit_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS hastalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL,
                soyad TEXT NOT NULL,
                dogum_tarihi DATE,
                email TEXT,
                doktor_id INTEGER NOT NULL,
                tani_bilgileri TEXT,
                ai_onerileri TEXT,
                kayit_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
                son_guncelleme DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doktor_id) REFERENCES kullanicilar (id)
            )
        ''')
        
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS consultation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hasta_id INTEGER NOT NULL,
                doktor_id INTEGER NOT NULL,
                meslek_dali TEXT NOT NULL,
                soru TEXT NOT NULL,
                cevap TEXT NOT NULL,
                tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hasta_id) REFERENCES hastalar (id),
                FOREIGN KEY (doktor_id) REFERENCES kullanicilar (id)
            )
        ''') 