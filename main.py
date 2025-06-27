from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db
from routers import pages, auth, patients, ai

app = FastAPI(title="Yapay Zeka Asistanı - Tıbbi Tanı Sistemi", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router, tags=["Pages"])
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])

@app.on_event("startup")
async def startup():
    init_db()
    print("Veritabanı başlatıldı")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 