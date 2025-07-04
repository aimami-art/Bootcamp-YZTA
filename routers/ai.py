from fastapi import APIRouter, HTTPException, Depends
import sqlite3
import os
from models import AIPrompt
from routers.auth import verify_jwt_token
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

router = APIRouter()

def get_ai_model():
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY bulunamadı")
    
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.1  
    )

def get_examples(specialty):
    examples = {
        "noroloji": [
            {
                "hasta_durumu": "55 yaşında erkek hasta, 3 gündür şiddetli baş ağrısı, bulantı ve ışık hassasiyeti",
                "tani_onerisi": "**Olası Tanılar:**\n1. **Migren Atağı**: Şiddetli baş ağrısı, bulantı ve fotofobia klasik migren belirtileri. Triptan grubu ilaçlar ve karanlık ortam önerilir.\n2. **Sinüzit**: Baş ağrısı sinüs kaynaklı olabilir. Antibiyotik tedavi ve dekonjestan kullanımı değerlendirilebilir.\n3. **İntrakranyal Basınç Artışı**: Acil BT çekilmeli. Şiddetli baş ağrısı ve bulantı ciddi bir patolojiyi işaret edebilir."
            }
        ],
        "dermatoloji": [
            {
                "hasta_durumu": "25 yaşında kadın hasta, yüzünde kızarık döküntü, kaşıntı ve yanma hissi",
                "tani_onerisi": "**Olası Tanılar:**\n1. **Seboreik Dermatit**: Yüz bölgesinde kızarık ve kaşıntı tipik belirtiler. Antifungal krem ve nemlendirici önerilir.\n2. **Kontakt Dermatit**: Yeni kozmetik ürün kullanımı sorgulanmalı. Steroid krem ve allerjen tespiti gerekli.\n3. **Rozasea**: Yüz orta bölgesinde kalıcı kızarık. Metronidazol jel ve güneş korunması önemli."
            }
        ]
    }
    return examples.get(specialty, [])

def create_prompt_template(specialty):
    examples = get_examples(specialty)
    
    example_prompt = ChatPromptTemplate.from_messages([
        ("human", "Hasta Durumu: {hasta_durumu}"),
        ("ai", "{tani_onerisi}")
    ])
    
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=examples,
    )
    
    system_prompts = {
        "noroloji": """Sen uzman bir nöroloji doktorusun. Hasta durumlarını değerlendirip, kanıta dayalı tıp prensiplerine uygun tanı önerileri sunuyorsun.

KURALLAR:
- Maksimum 3 olası tanı öner
- Her tanı için: Tanı adı + 2 cümle açıklama + Tedavi önerisi
- Toplam 250 kelimeyi geçme  
- Acil durumları belirt
- Kesin tanı koyma, "olası" ifadesi kullan
""",
        "dermatoloji": """Sen uzman bir dermatoloji doktorusun. Cilt problemlerini değerlendirip, kanıta dayalı tıp prensiplerine uygun tanı önerileri sunuyorsun.

KURALLAR:
- Maksimum 3 olası tanı öner
- Her tanı için: Tanı adı + 2 cümle açıklama + Tedavi önerisi  
- Toplam 250 kelimeyi geçme
- Cilt kanserine dikkat çek
- Kesin tanı koyma, "olası" ifadesi kullan
"""
    }
    
    final_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompts.get(specialty, "Sen bir tıp uzmanısın.")),
        few_shot_prompt,
        ("human", "Hasta Durumu: {hasta_durumu}\n\nLütfen yukarıdaki format ve kurallara uyarak değerlendirme yap.")
    ])
    
    return final_prompt

@router.post("/consultation")
async def ai_konsultasyon(prompt_data: AIPrompt, current_user: dict = Depends(verify_jwt_token)):
    try:
        model = get_ai_model()
        prompt_template = create_prompt_template(prompt_data.meslek_dali.lower())
        
        output_parser = StrOutputParser()
        
        chain = prompt_template | model | output_parser
        
        ai_response = chain.invoke({
            "hasta_durumu": prompt_data.prompt
        })
        
        print(f"LangChain AI yanıtı: {len(ai_response)} karakter")
        
        with sqlite3.connect('medical_ai.db') as conn:
            conn.execute('''
                UPDATE hastalar 
                SET tani_bilgileri = ?, ai_onerileri = ?, son_guncelleme = CURRENT_TIMESTAMP
                WHERE id = ? AND doktor_id = ?
            ''', (prompt_data.prompt, ai_response, prompt_data.hasta_id, current_user["user_id"]))
        
        return {"ai_response": ai_response}
    
    except Exception as e:
        print(f"AI konsültasyon hatası: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI konsültasyon hatası: {str(e)}") 