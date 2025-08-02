import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL bağlantısı
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database modelleri
class Kullanicilar(Base):
    __tablename__ = "kullanicilar"
    
    id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    soyad = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    sifre_hash = Column(String, nullable=False)
    meslek_dali = Column(String)
    kayit_tarihi = Column(DateTime(timezone=True), server_default=func.now())
    
    # İlişkiler
    hastalar = relationship("Hastalar", back_populates="doktor")
    consultations = relationship("ConsultationHistory", back_populates="doktor")

class Hastalar(Base):
    __tablename__ = "hastalar"
    
    id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    soyad = Column(String, nullable=False)
    dogum_tarihi = Column(Date)
    email = Column(String)
    doktor_id = Column(Integer, ForeignKey("kullanicilar.id"), nullable=False)
    tani_bilgileri = Column(Text)
    ai_onerileri = Column(Text)
    kayit_tarihi = Column(DateTime(timezone=True), server_default=func.now())
    son_guncelleme = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # İlişkiler
    doktor = relationship("Kullanicilar", back_populates="hastalar")
    consultations = relationship("ConsultationHistory", back_populates="hasta")

class ConsultationHistory(Base):
    __tablename__ = "consultation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    hasta_id = Column(Integer, ForeignKey("hastalar.id"), nullable=False)
    doktor_id = Column(Integer, ForeignKey("kullanicilar.id"), nullable=False)
    meslek_dali = Column(String, nullable=False)
    soru = Column(Text, nullable=False)
    cevap = Column(Text, nullable=False)
    tarih = Column(DateTime(timezone=True), server_default=func.now())
    
    # İlişkiler
    hasta = relationship("Hastalar", back_populates="consultations")
    doktor = relationship("Kullanicilar", back_populates="consultations")

class TreatmentPlans(Base):
    __tablename__ = "treatment_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    hasta_id = Column(Integer, ForeignKey("hastalar.id"), nullable=False)
    doktor_id = Column(Integer, ForeignKey("kullanicilar.id"), nullable=False)
    meslek_dali = Column(String(100), nullable=False)
    tani_bilgisi = Column(Text)
    tedavi_adimlari = Column(Text)
    onay_durumu = Column(String(20), default='beklemede')
    email_gonderildi = Column(Integer, default=0)  # Boolean yerine Integer (SQLite uyumluluk için)
    olusturma_tarihi = Column(DateTime(timezone=True), server_default=func.now())
    onay_tarihi = Column(DateTime(timezone=True))
    
    # İlişkiler
    hasta = relationship("Hastalar", foreign_keys=[hasta_id])
    doktor = relationship("Kullanicilar", foreign_keys=[doktor_id])

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Veritabanı tablolarını oluştur"""
    Base.metadata.create_all(bind=engine) 