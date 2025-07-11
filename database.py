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
                tc_kimlik TEXT NOT NULL,
                doktor_id INTEGER NOT NULL,
                tani_bilgileri TEXT,
                ai_onerileri TEXT,
                kayit_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
                son_guncelleme DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doktor_id) REFERENCES kullanicilar (id)
            )
        ''') 