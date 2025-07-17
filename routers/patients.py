from fastapi import APIRouter, HTTPException, Depends
import sqlite3
from models import PatientCreate
from routers.auth import verify_jwt_token

router = APIRouter()

@router.post("/")
async def hasta_ekle(patient: PatientCreate, current_user: dict = Depends(verify_jwt_token)):
    with sqlite3.connect('medical_ai.db') as conn:
        db = conn.execute('''
            INSERT INTO hastalar (ad, soyad, dogum_tarihi, doktor_id)
            VALUES (?, ?, ?, ?)
        ''', (patient.ad, patient.soyad, patient.dogum_tarihi, current_user["user_id"]))
        
        patient_id = db.lastrowid
        
        return {"message": "Hasta başarıyla eklendi", "patient_id": patient_id}

@router.get("/")
async def hasta_listesi(current_user: dict = Depends(verify_jwt_token)):
    with sqlite3.connect('medical_ai.db') as conn:
        conn.row_factory = sqlite3.Row
        
        results = conn.execute('''
            SELECT id, ad, soyad, dogum_tarihi, kayit_tarihi, tani_bilgileri, ai_onerileri, son_guncelleme
            FROM hastalar 
            WHERE doktor_id = ?
            ORDER BY kayit_tarihi DESC
        ''', (current_user["user_id"],)).fetchall()
        
        patients = [dict(row) for row in results]
        
        return {"patients": patients} 