from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import hashlib
import jwt
import os
import secrets
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from models import UserRegister, UserLogin, ForgotPassword, ResetPassword, ChangePassword, DeleteAccount
from database import get_db, Kullanicilar, SessionLocal
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

# Email ayarları
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)

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

def create_reset_token(email: str) -> str:
    payload = {
        "email": email,
        "type": "password_reset",
        "exp": datetime.utcnow() + timedelta(hours=1)  # 1 saat geçerli
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_reset_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Geçersiz token türü")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Token süresi dolmuş")
    except jwt.JWTError:
        raise HTTPException(status_code=400, detail="Geçersiz token")

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token süresi dolmuş")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token")

def send_reset_email(email: str, reset_token: str):
    """Şifre sıfırlama e-postası gönder"""
    try:
        # E-posta içeriği
        reset_url = f"http://localhost:8000/reset-password?token={reset_token}"
        
        subject = "MedIntel - Şifre Sıfırlama"
        body = f"""
        Merhaba,
        
        MedIntel hesabınız için şifre sıfırlama talebinde bulundunuz.
        
        Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın:
        {reset_url}
        
        Bu bağlantı 1 saat süreyle geçerlidir.
        
        Eğer bu talebi siz yapmadıysanız, bu e-postayı görmezden gelebilirsiniz.
        
        Saygılarımızla,
        MedIntel Ekibi
        """
        
        # E-posta oluştur
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # E-postayı gönder
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(FROM_EMAIL, email, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"E-posta gönderme hatası: {str(e)}")
        return False

@router.post("/register")
async def kullanici_kayit(user: UserRegister, db: Session = Depends(get_db)):
    try:
        # Email kontrolü
        existing_user = db.query(Kullanicilar).filter(Kullanicilar.email == user.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Bu email zaten kayıtlı")
        
        # Yeni kullanıcı oluştur
        hashed_password = hash_password(user.sifre)
        db_user = Kullanicilar(
            ad=user.ad,
            soyad=user.soyad,
            email=user.email,
            sifre_hash=hashed_password,
            meslek_dali=None
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        token = create_jwt_token(db_user.id, db_user.email)
        
        return {"message": "Kayıt başarılı", "token": token, "user_id": db_user.id}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
async def kullanici_giris(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(Kullanicilar).filter(Kullanicilar.email == user.email).first()
    
    if not db_user or not verify_password(user.sifre, db_user.sifre_hash):
        raise HTTPException(status_code=401, detail="Email veya şifre hatalı")
    
    token = create_jwt_token(db_user.id, db_user.email)
    
    return {"message": "Giriş başarılı", "token": token, "user_id": db_user.id}

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
        db = SessionLocal()
        try:
            existing_user = db.query(Kullanicilar).filter(Kullanicilar.email == email).first()
            
            if existing_user:
                # Kullanıcı zaten var, ID'sini al
                user_id = existing_user.id
                print(f"Mevcut kullanıcı bulundu. ID: {user_id}")
            else:
                # Kullanıcı yok, yeni kayıt oluştur
                random_password = secrets.token_urlsafe(16)
                hashed_password = hash_password(random_password)
                
                new_user = Kullanicilar(
                    ad=given_name,
                    soyad=family_name,
                    email=email,
                    sifre_hash=hashed_password,
                    meslek_dali=None
                )
                
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                
                user_id = new_user.id
                print(f"Yeni kullanıcı oluşturuldu. ID: {user_id}")
        finally:
            db.close()
        
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

@router.post("/forgot-password")
async def forgot_password(request: ForgotPassword, db: Session = Depends(get_db)):
    """Şifre sıfırlama e-postası gönder"""
    try:
        # Kullanıcının var olup olmadığını kontrol et
        user = db.query(Kullanicilar).filter(Kullanicilar.email == request.email).first()
        
        if not user:
            # Güvenlik için kullanıcı var olmasa bile başarılı mesajı döndür
            return {"message": "Şifre sıfırlama bağlantısı gönderildi"}
        
        # Reset token oluştur
        reset_token = create_reset_token(request.email)
        
        # E-posta gönder
        if send_reset_email(request.email, reset_token):
            return {"message": "Şifre sıfırlama bağlantısı gönderildi"}
        else:
            raise HTTPException(status_code=500, detail="E-posta gönderilemedi")
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-password")
async def reset_password(request: ResetPassword, db: Session = Depends(get_db)):
    """Şifreyi sıfırla"""
    try:
        # Token'ı doğrula
        payload = verify_reset_token(request.token)
        email = payload.get("email")
        
        if not email:
            raise HTTPException(status_code=400, detail="Geçersiz token")
        
        # Kullanıcıyı bul ve şifreyi güncelle
        user = db.query(Kullanicilar).filter(Kullanicilar.email == email).first()
        if not user:
            raise HTTPException(status_code=400, detail="Kullanıcı bulunamadı")
        
        hashed_password = hash_password(request.password)
        user.sifre_hash = hashed_password
        db.commit()
        
        return {"message": "Şifre başarıyla güncellendi"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/change-password")
async def change_password(request: ChangePassword, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Kullanıcı şifresini değiştir"""
    try:
        # Token'dan kullanıcı bilgilerini al
        payload = verify_jwt_token(credentials)
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(status_code=400, detail="Geçersiz token")
        
        # Mevcut şifreyi doğrula
        db = SessionLocal()
        try:
            user = db.query(Kullanicilar).filter(
                Kullanicilar.id == user_id, 
                Kullanicilar.email == email
            ).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
            
            # Mevcut şifreyi kontrol et
            if not verify_password(request.current_password, user.sifre_hash):
                raise HTTPException(status_code=400, detail="Mevcut şifre hatalı")
            
            # Yeni şifreyi hash'le ve güncelle
            new_hash = hash_password(request.new_password)
            user.sifre_hash = new_hash
            db.commit()
            
            return {"message": "Şifre başarıyla değiştirildi"}
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-account")
async def delete_account(request: DeleteAccount, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Kullanıcı hesabını ve tüm verilerini sil"""
    try:
        # Token'dan kullanıcı bilgilerini al
        payload = verify_jwt_token(credentials)
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(status_code=400, detail="Geçersiz token")
        
        db = SessionLocal()
        try:
            # Kullanıcının var olup olmadığını ve şifresini kontrol et
            user = db.query(Kullanicilar).filter(
                Kullanicilar.id == user_id, 
                Kullanicilar.email == email
            ).first()
            
            if not user:
                raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
            
            # Şifreyi kontrol et
            if not verify_password(request.password, user.sifre_hash):
                raise HTTPException(status_code=400, detail="Şifre hatalı")
            
            # Kullanıcıya ait tüm verileri sil
            # Önce consultation_history kayıtlarını sil
            db.execute(text("DELETE FROM consultation_history WHERE doktor_id = :user_id"), {"user_id": user_id})
            
            # Hasta kayıtlarını sil
            db.execute(text("DELETE FROM hastalar WHERE doktor_id = :user_id"), {"user_id": user_id})
            
            # Son olarak kullanıcı hesabını sil
            db.delete(user)
            
            # Değişiklikleri kaydet
            db.commit()
            
            return {"message": "Hesabınız ve tüm verileriniz başarıyla silindi"}
            
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            print(f"Veritabanı hatası: {e}")
            raise HTTPException(status_code=500, detail=f"Veritabanı hatası: {str(e)}")
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 