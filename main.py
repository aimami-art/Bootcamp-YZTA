from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import pages, auth, patients, ai, rag, news
import os

app = FastAPI(title="Yapay Zeka Asistanı - Tıbbi Tanı Sistemi", version="1.0.0")

# CORS ayarları - Production için güncellendi
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000", 
        "http://34.77.9.250:8000",
        "https://34.77.9.250:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router, tags=["Pages"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG System"])
app.include_router(news.router, tags=["News"])

@app.on_event("startup")
async def startup():
    init_db()
    print("Veritabanı başlatıldı")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 