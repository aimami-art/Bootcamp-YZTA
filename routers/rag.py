from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPAuthorizationCredentials
from routers.auth import verify_jwt_token, security
from typing import List
import sqlite3

try:
    from services.rag_service import rag_service
    RAG_SERVICE_AVAILABLE = True
except ImportError as e:
    RAG_SERVICE_AVAILABLE = False
    print(f"RAG service yüklenemedi: {e}")
    # Dummy rag_service oluştur
    class DummyRAGService:
        is_initialized = False
        def __init__(self):
            class DummyConfig:
                is_rag_enabled = False
                pinecone_api_key = None
                index_name = "dummy-index"
                embedding_model_name = "dummy-model"
            self.config = DummyConfig()
        def initialize(self): return False
        def process_pdf_and_upload(self, *args): return False
    rag_service = DummyRAGService()

router = APIRouter()

# Admin kullanıcıları (şimdilik email bazlı, daha sonra role tablosu eklenebilir)
ADMIN_EMAILS = ["uygurmuhammed35@gmail.com"]  # Uygulama sahibinin email'i

def verify_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Admin yetkisi kontrolü"""
    payload = verify_jwt_token(credentials)
    user_email = payload.get("email")
    
    if user_email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Bu işlem için admin yetkisi gereklidir")
    
    return payload

@router.post("/upload-pdf")
async def upload_pdf_to_rag(
    file: UploadFile = File(...),
    description: str = Form(None),
    current_user: dict = Depends(verify_admin)
):
    """PDF dosyası yükle ve RAG sistemine ekle (Sadece admin)"""
    
    # RAG servisinin kullanılabilir olup olmadığını kontrol et
    if not RAG_SERVICE_AVAILABLE:
        raise HTTPException(
            status_code=500, 
            detail="RAG sistemi mevcut değil. Gerekli kütüphaneleri yükleyin."
        )
    
    # RAG servisinin başlatılıp başlatılmadığını kontrol et
    if not rag_service.is_initialized:
        if not rag_service.initialize():
            raise HTTPException(
                status_code=500, 
                detail="RAG sistemi başlatılamadı. Pinecone ayarlarını kontrol edin."
            )
    
    # Dosya türü kontrolü
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları kabul edilir")
    
    try:
        # PDF içeriğini oku
        pdf_content = await file.read()
        
        if len(pdf_content) == 0:
            raise HTTPException(status_code=400, detail="Dosya boş")
        
        # PDF'i işle ve Pinecone'a yükle
        success = rag_service.process_pdf_and_upload(pdf_content, file.filename)
        
        if not success:
            raise HTTPException(status_code=500, detail="PDF işleme ve yükleme başarısız")
        
        # İsteğe bağlı: Yükleme geçmişini kaydet
        try:
            conn = sqlite3.connect("medical_ai.db")
            cursor = conn.cursor()
            
            # RAG uploads tablosunu oluştur (eğer yoksa)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rag_uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    description TEXT,
                    uploaded_by INTEGER,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    specialty TEXT DEFAULT 'psikoloji',
                    FOREIGN KEY (uploaded_by) REFERENCES kullanicilar (id)
                )
            ''')
            
            # Yüklemeyi kaydet
            cursor.execute('''
                INSERT INTO rag_uploads (filename, description, uploaded_by, specialty)
                VALUES (?, ?, ?, ?)
            ''', (file.filename, description, current_user["user_id"], "psikoloji"))
            
            conn.commit()
            conn.close()
            
        except Exception as db_error:
            print(f"Veritabanı kayıt hatası: {db_error}")
            # Veritabanı hatası olsa bile PDF yüklenmişse başarılı say
        
        return {
            "message": f"'{file.filename}' dosyası başarıyla RAG sistemine eklendi",
            "filename": file.filename,
            "description": description
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF yükleme hatası: {str(e)}")

@router.get("/upload-history")
async def get_upload_history(current_user: dict = Depends(verify_admin)):
    """RAG sistemi yükleme geçmişini getir (Sadece admin)"""
    
    try:
        conn = sqlite3.connect("medical_ai.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.id, r.filename, r.description, r.upload_date, r.specialty, k.email
            FROM rag_uploads r
            LEFT JOIN kullanicilar k ON r.uploaded_by = k.id
            ORDER BY r.upload_date DESC
        ''')
        
        uploads = []
        for row in cursor.fetchall():
            uploads.append({
                "id": row[0],
                "filename": row[1],
                "description": row[2],
                "upload_date": row[3],
                "specialty": row[4],
                "uploaded_by_email": row[5]
            })
        
        conn.close()
        return {"uploads": uploads}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geçmiş getirme hatası: {str(e)}")

@router.delete("/delete-document/{upload_id}")
async def delete_document(upload_id: int, current_user: dict = Depends(verify_admin)):
    """RAG sisteminden döküman sil (Sadece admin)"""
    
    try:
        conn = sqlite3.connect("medical_ai.db")
        cursor = conn.cursor()
        
        # Döküman bilgilerini al
        cursor.execute('SELECT filename FROM rag_uploads WHERE id = ?', (upload_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Döküman bulunamadı")
        
        filename = result[0]
        
        # Veritabanından sil
        cursor.execute('DELETE FROM rag_uploads WHERE id = ?', (upload_id,))
        conn.commit()
        conn.close()
        
        # Not: Pinecone'dan silme işlemi daha karmaşık olduğu için şimdilik sadece DB'den siliyoruz
        # Gelecekte filename bazlı Pinecone vector silme özelliği eklenebilir
        
        return {"message": f"'{filename}' dökümanı başarıyla silindi"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Döküman silme hatası: {str(e)}")

@router.get("/rag-status")
async def get_rag_status(current_user: dict = Depends(verify_admin)):
    """RAG sistemi durumunu kontrol et (Sadece admin)"""
    
    status = {
        "is_initialized": rag_service.is_initialized,
        "is_enabled": rag_service.config.is_rag_enabled,
        "pinecone_configured": bool(rag_service.config.pinecone_api_key),
        "index_name": rag_service.config.index_name,
        "embedding_model": rag_service.config.embedding_model_name
    }
    
    return status