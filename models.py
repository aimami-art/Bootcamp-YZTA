from pydantic import BaseModel

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
    tc_kimlik: str

class AIPrompt(BaseModel):
    hasta_id: int
    prompt: str
    meslek_dali: str 