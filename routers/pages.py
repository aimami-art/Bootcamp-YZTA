from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def ana_sayfa(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/register", response_class=HTMLResponse)
async def kayit_sayfasi(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/login", response_class=HTMLResponse)
async def giris_sayfasi(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/specialty", response_class=HTMLResponse)
async def meslek_secimi(request: Request):
    return templates.TemplateResponse("specialty.html", {"request": request})

@router.get("/patients", response_class=HTMLResponse)
async def hasta_islemleri(request: Request):
    return templates.TemplateResponse("patients.html", {"request": request})

@router.get("/ai-assistant", response_class=HTMLResponse)
async def ai_asistan(request: Request):
    return templates.TemplateResponse("ai-assistant.html", {"request": request})

@router.get("/patient-history", response_class=HTMLResponse)
async def hasta_gecmisi(request: Request):
    return templates.TemplateResponse("patient-history.html", {"request": request}) 