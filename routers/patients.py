from fastapi import APIRouter, HTTPException, Depends
import sqlite3
from models import PatientCreate
from routers.auth import verify_jwt_token

router = APIRouter()

@router.post("/")
async def hasta_ekle(patient: PatientCreate):
    with sqlite3.connect('medical_ai.db') as conn:
        db = conn.execute('''
            INSERT INTO hastalar (ad, soyad, dogum_tarihi, email, doktor_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (patient.ad, patient.soyad, patient.dogum_tarihi, patient.email, 1))
        patient_id = db.lastrowid
        return {"message": "Hasta başarıyla eklendi", "patient_id": patient_id}

@router.get("/")
async def hasta_listesi():
    with sqlite3.connect('medical_ai.db') as conn:
        conn.row_factory = sqlite3.Row
        results = conn.execute('''
            SELECT id, ad, soyad, dogum_tarihi, email, kayit_tarihi, tani_bilgileri, ai_onerileri, son_guncelleme
            FROM hastalar 
            ORDER BY kayit_tarihi DESC
        ''').fetchall()
        patients = [dict(row) for row in results]
        return {"patients": patients} 