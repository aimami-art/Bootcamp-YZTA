from pydantic import BaseModel
from datetime import date

class UserRegister(BaseModel):
    ad: str
    soyad: str
    email: str
    sifre: str

class UserLogin(BaseModel):
    email: str
    sifre: str

class PatientCreate(BaseModel):
    ad: str
    soyad: str
    dogum_tarihi: date

class AIPrompt(BaseModel):
    hasta_id: int
    prompt: str
    meslek_dali: str 