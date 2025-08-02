from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from models import PatientCreate
from routers.auth import verify_jwt_token
from database import get_db, Hastalar

router = APIRouter()

@router.post("/")
async def hasta_ekle(patient: PatientCreate, current_user: dict = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        db_patient = Hastalar(
            ad=patient.ad,
            soyad=patient.soyad,
            dogum_tarihi=patient.dogum_tarihi,
            email=patient.email,
            doktor_id=current_user["user_id"]
        )
        
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        
        return {"message": "Hasta başarıyla eklendi", "patient_id": db_patient.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def hasta_listesi(current_user: dict = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        patients = db.query(Hastalar).filter(
            Hastalar.doktor_id == current_user["user_id"]
        ).order_by(Hastalar.kayit_tarihi.desc()).all()
        
        patients_list = []
        for patient in patients:
            patients_list.append({
                "id": patient.id,
                "ad": patient.ad,
                "soyad": patient.soyad,
                "dogum_tarihi": patient.dogum_tarihi,
                "email": patient.email,
                "kayit_tarihi": patient.kayit_tarihi,
                "tani_bilgileri": patient.tani_bilgileri,
                "ai_onerileri": patient.ai_onerileri,
                "son_guncelleme": patient.son_guncelleme
            })
        
        return {"patients": patients_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 