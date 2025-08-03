from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPAuthorizationCredentials
from routers.auth import verify_jwt_token, security
from typing import List
from database import SessionLocal, RAGUploads, Kullanicilar
from sqlalchemy.orm import Session

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
            db: Session = SessionLocal()
            try:
                # Yüklemeyi kaydet
                new_upload = RAGUploads(
                    filename=file.filename,
                    description=description,
                    uploaded_by=current_user["user_id"],
                    specialty="psikoloji"
                )
                db.add(new_upload)
                db.commit()
            finally:
                db.close()
            
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
        db: Session = SessionLocal()
        try:
            # Upload geçmişini al
            results = db.query(
                RAGUploads.id,
                RAGUploads.filename,
                RAGUploads.description,
                RAGUploads.upload_date,
                RAGUploads.specialty,
                Kullanicilar.email
            ).join(
                Kullanicilar, RAGUploads.uploaded_by == Kullanicilar.id, isouter=True
            ).order_by(RAGUploads.upload_date.desc()).all()
            
            uploads = []
            for row in results:
                uploads.append({
                    "id": row.id,
                    "filename": row.filename,
                    "description": row.description,
                    "upload_date": row.upload_date.isoformat() if row.upload_date else None,
                    "specialty": row.specialty,
                    "uploaded_by_email": row.email
                })
            
            return {"uploads": uploads}
        finally:
            db.close()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geçmiş getirme hatası: {str(e)}")

@router.delete("/delete-document/{upload_id}")
async def delete_document(upload_id: int, current_user: dict = Depends(verify_admin)):
    """RAG sisteminden döküman sil (Sadece admin)"""
    
    try:
        db: Session = SessionLocal()
        try:
            # Döküman bilgilerini al
            upload = db.query(RAGUploads).filter(RAGUploads.id == upload_id).first()
            
            if not upload:
                raise HTTPException(status_code=404, detail="Döküman bulunamadı")
            
            filename = upload.filename
            
            # Veritabanından sil
            db.delete(upload)
            db.commit()
            
            # Not: Pinecone'dan silme işlemi daha karmaşık olduğu için şimdilik sadece DB'den siliyoruz
            # Gelecekte filename bazlı Pinecone vector silme özelliği eklenebilir
            
            return {"message": f"'{filename}' dökümanı başarıyla silindi"}
        finally:
            db.close()
        
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