from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3
import hashlib
import jwt
import os
from datetime import datetime, timedelta
from models import UserRegister, UserLogin
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_jwt_token(user_id: int, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token süresi dolmuş")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token")

@router.post("/register")
async def kullanici_kayit(user: UserRegister):
    try:
        with sqlite3.connect('medical_ai.db') as conn:
            result = conn.execute("SELECT id FROM kullanicilar WHERE email = ?", (user.email,)).fetchone()
            if result:
                raise HTTPException(status_code=400, detail="Bu email zaten kayıtlı")
            
            hashed_password = hash_password(user.sifre)
            db = conn.execute('''
                INSERT INTO kullanicilar (ad, soyad, email, sifre_hash, meslek_dali)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.ad, user.soyad, user.email, hashed_password, None))
            
            user_id = db.lastrowid
            
            token = create_jwt_token(user_id, user.email)
            
            return {"message": "Kayıt başarılı", "token": token, "user_id": user_id}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
async def kullanici_giris(user: UserLogin):
    with sqlite3.connect('medical_ai.db') as conn:
        result = conn.execute("SELECT id, sifre_hash FROM kullanicilar WHERE email = ?", (user.email,)).fetchone()
        
        if not result or not verify_password(user.sifre, result[1]):
            raise HTTPException(status_code=401, detail="Email veya şifre hatalı")
        
        token = create_jwt_token(result[0], user.email)
        
        return {"message": "Giriş başarılı", "token": token, "user_id": result[0]} 