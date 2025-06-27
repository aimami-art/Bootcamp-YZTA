from fastapi import APIRouter, HTTPException, Depends
import sqlite3
import os
from models import AIPrompt
from routers.auth import verify_jwt_token
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

@router.post("/consultation")
async def ai_konsultasyon(prompt_data: AIPrompt, current_user: dict = Depends(verify_jwt_token)):
    try:
        specialty_prompts = {
            "noroloji": "Sen bir nöroloji uzmanısın. Aşağıdaki semptomları değerlendir ve nörolojik açıdan KISA tanı önerileri sun. Maksimum 3 tanı ve her biri için maksimum 2 cümle kullan. Toplam 200 kelimeyi geçme:",
            "dermatoloji": "Sen bir dermatoloji uzmanısın. Aşağıdaki cilt problemini değerlendir ve dermatolojik açıdan KISA tanı önerileri sun. Maksimum 3 tanı ve her biri için maksimum 2 cümle kullan. Toplam 200 kelimeyi geçme:"
        }
        
        base_prompt = specialty_prompts.get(prompt_data.meslek_dali.lower(), "Sen bir tıp uzmanısın.")
        full_prompt = f"{base_prompt}\n\nHasta durumu: {prompt_data.prompt}"
        
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        
        if not GEMINI_API_KEY or not GEMINI_API_KEY.strip():
            raise HTTPException(
                status_code=400, 
                detail="AI hizmeti kullanabilmek için GEMINI_API_KEY ayarlanmalıdır. Lütfen .env dosyasını kontrol edin."
            )
        
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(full_prompt)
        ai_response = response.text
        print(f"Gemini API başarılı: {len(ai_response)} karakter yanıt alındı")
        
        with sqlite3.connect('medical_ai.db') as conn:
            conn.execute('''
                UPDATE hastalar 
                SET tani_bilgileri = ?, ai_onerileri = ?, son_guncelleme = CURRENT_TIMESTAMP
                WHERE id = ? AND doktor_id = ?
            ''', (prompt_data.prompt, ai_response, prompt_data.hasta_id, current_user["user_id"]))
        
        return {"ai_response": ai_response}
    
    except Exception as e:
        print(f"AI konsültasyon hatası: {e}")
        print(f"Hata türü: {type(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI konsültasyon hatası: {str(e)}") 