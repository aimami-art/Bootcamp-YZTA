from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
import sqlite3
import hashlib
import jwt
import os
import secrets
import requests
from datetime import datetime, timedelta
from models import UserRegister, UserLogin
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Google OAuth için bilgileri .env dosyasından al
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")

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

@router.get("/auth/google/url")
async def google_login_url():
    # Debug bilgisi yazdır
    print(f"Google OAuth URL endpoint'i çağrıldı")
    print(f"GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")
    print(f"GOOGLE_REDIRECT_URI: {GOOGLE_REDIRECT_URI}")
    
    # Google OAuth için state değeri oluştur (CSRF koruması için)
    state = secrets.token_urlsafe(16)
    
    # Google OAuth URL'sini oluştur
    auth_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20email%20profile&state={state}"
    
    # Debug için URL'yi yazdır
    print(f"Oluşturulan Google OAuth URL: {auth_url}")
    
    # Doğrudan yönlendirme yap
    return RedirectResponse(url=auth_url)

@router.get("/auth/google/callback")
async def google_auth_callback(code: str, state: str, request: Request):
    try:
        print(f"Google OAuth callback çağrıldı. Code: {code[:10]}...")
        
        # Google'dan token al
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        token_json = token_response.json()
        
        # Google'dan kullanıcı bilgilerini al
        user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {"Authorization": f"Bearer {token_json['access_token']}"}
        
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
        
        # Kullanıcı bilgilerini al
        email = user_info.get("email")
        given_name = user_info.get("given_name", "")
        family_name = user_info.get("family_name", "")
        
        print(f"Kullanıcı bilgileri alındı. Email: {email}")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email bilgisi alınamadı")
        
        # Kullanıcı veritabanında var mı kontrol et, yoksa kaydet
        with sqlite3.connect('medical_ai.db') as conn:
            result = conn.execute("SELECT id FROM kullanicilar WHERE email = ?", (email,)).fetchone()
            
            if result:
                # Kullanıcı zaten var, ID'sini al
                user_id = result[0]
                print(f"Mevcut kullanıcı bulundu. ID: {user_id}")
            else:
                # Kullanıcı yok, yeni kayıt oluştur
                random_password = secrets.token_urlsafe(16)
                hashed_password = hash_password(random_password)
                
                db = conn.execute('''
                    INSERT INTO kullanicilar (ad, soyad, email, sifre_hash, meslek_dali)
                    VALUES (?, ?, ?, ?, ?)
                ''', (given_name, family_name, email, hashed_password, None))
                
                user_id = db.lastrowid
                print(f"Yeni kullanıcı oluşturuldu. ID: {user_id}")
        
        # JWT token oluştur
        token = create_jwt_token(user_id, email)
        
        # Yönlendirme URL'sini oluştur
        redirect_url = f"/specialty?token={token}&user_id={user_id}"
        print(f"Yönlendirme URL'si: {redirect_url}")
        
        # Kullanıcıyı yönlendir
        return RedirectResponse(url=redirect_url)
        
    except requests.RequestException as e:
        print(f"Google API hatası: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Google API hatası: {str(e)}")
    except Exception as e:
        print(f"Beklenmeyen hata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 