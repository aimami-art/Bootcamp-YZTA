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

class ForgotPassword(BaseModel):
    email: str

class ResetPassword(BaseModel):
    token: str
    password: str

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

class PatientCreate(BaseModel):
    ad: str
    soyad: str
    dogum_tarihi: date
    email: str

class AIPrompt(BaseModel):
    hasta_id: int
    prompt: str
    meslek_dali: str 