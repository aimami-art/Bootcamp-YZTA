from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
import sqlite3
import os
from models import AIPrompt
from routers.auth import verify_jwt_token
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage

import speech_recognition as sr
import tempfile
import os as os_path
from pydub import AudioSegment
import io

load_dotenv()

router = APIRouter()

patient_memories = {}


def get_patient_memory(patient_id: int) -> ConversationBufferWindowMemory:
    """Hasta için memory alır veya oluşturur - sadece mevcut chat oturumu için"""
    if patient_id not in patient_memories:
        patient_memories[patient_id] = ConversationBufferWindowMemory(
            k=4,  
            return_messages=True,
            memory_key="chat_history"
        )
    return patient_memories[patient_id]

def get_ai_model():
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY bulunamadı")
    
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
        convert_system_message_to_human=True  
    )

def get_examples(specialty):
    examples = {
        "noroloji": [
            {
                "hasta_durumu": "[Nörolojik semptomlar burada açıklanır]",
                "tani_onerisi": "**Değerlendirme:**\n1. **[Tanı 1]**: [Açıklama]. Ayrıntılı muayene öneriyorum.\n2. **[Tanı 2]**: [Açıklama]. Görüntüleme çalışmaları değerlendirilebilir.\n3. **[Tanı 3]**: [Açıklama]. Laboratuvar testleri destekleyici olabilir."
            }
        ],
        "dermatoloji": [
            {
                "hasta_durumu": "[Dermatolojik bulgular burada açıklanır]",
                "tani_onerisi": "**Değerlendirme:**\n1. **[Tanı 1]**: [Açıklama]. Topikal tedavi önerebilirim.\n2. **[Tanı 2]**: [Açıklama]. Biopsi değerlendirilebilir.\n3. **[Tanı 3]**: [Açıklama]. Sistemik yaklaşım gerekebilir."
            }
        ]
    }
    return examples.get(specialty, [])

def create_prompt_template_with_memory(specialty):
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
        "noroloji": """Sen uzman bir nöroloji doktorusun. Bir meslektaşın (doktor) ile konsültasyon yapıyorsun. Hasta durumlarını değerlendirip, kanıta dayalı tıp prensiplerine uygun tanı önerileri sunuyorsun.

CHAT MEMORY KULLANIMI:
- Bu chat oturumundaki önceki mesajları dikkate al
- Sorular arasında bağlantı kur
- Önceki değerlendirmelerini hatırla

MESLEKTAŞ KONSÜLTASYONU:
- "Hastaneye başvurun" yerine "Ayrıntılı muayene öneriyorum" de
- "Doktora gidin" yerine "Görüntüleme çalışmaları değerlendirilebilir" de
- Meslektaş seviyesinde öneriler sun

KURALLAR:
- Maksimum 3 olası tanı öner
- Her tanı için: Tanı adı + 2 cümle açıklama + Tedavi önerisi
- Toplam 250 kelimeyi geçme  
- Acil durumları belirt
- Kesin tanı koyma, "olası" ifadesi kullan
""",
        "dermatoloji": """Sen uzman bir dermatoloji doktorusun. Bir meslektaşın (doktor) ile konsültasyon yapıyorsun. Cilt problemlerini değerlendirip, kanıta dayalı tıp prensiplerine uygun tanı önerileri sunuyorsun.

CHAT MEMORY KULLANIMI:
- Bu chat oturumundaki önceki mesajları dikkate al
- Sorular arasında bağlantı kur
- Önceki değerlendirmelerini hatırla

MESLEKTAŞ KONSÜLTASYONU:
- "Dermatolog başvurun" yerine "Topikal tedavi önerebilirim" de
- "Hastaneye gidin" yerine "Biopsi değerlendirilebilir" de
- Meslektaş seviyesinde öneriler sun

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
        ("human", "Chat Geçmişi: {chat_history}\n\nHasta Durumu: {hasta_durumu}\n\nLütfen yukarıdaki format ve kurallara uyarak değerlendirme yap.")
    ])
    
    return final_prompt

@router.post("/consultation")
async def ai_konsultasyon(prompt_data: AIPrompt, current_user: dict = Depends(verify_jwt_token)):
    import time
    start_time = time.time()
    
    try:
        
        model = get_ai_model()
        memory = get_patient_memory(prompt_data.hasta_id)
        prompt_template = create_prompt_template_with_memory(prompt_data.meslek_dali.lower())
        
        output_parser = StrOutputParser()
        chain = prompt_template | model | output_parser
        
        chat_history = memory.chat_memory.messages
        print(f"Chat history uzunluğu: {len(chat_history)} mesaj")
        
        ai_start = time.time()
        ai_response = chain.invoke({
            "hasta_durumu": prompt_data.prompt,
            "chat_history": chat_history
        })
        ai_end = time.time()
        
        memory.chat_memory.add_user_message(f"Soru: {prompt_data.prompt}")
        memory.chat_memory.add_ai_message(f"Cevap: {ai_response}")
        
        print(f"AI yanıt süresi: {ai_end - ai_start:.2f} saniye")
        print(f"LangChain AI yanıtı: {len(ai_response)} karakter")
        print(f"Chat Memory'de {len(memory.chat_memory.messages)} mesaj var")
        
        
        with sqlite3.connect('medical_ai.db') as conn:
            
            conn.execute('''
                UPDATE hastalar 
                SET tani_bilgileri = ?, ai_onerileri = ?, son_guncelleme = CURRENT_TIMESTAMP
                WHERE id = ? AND doktor_id = ?
            ''', (prompt_data.prompt, ai_response, prompt_data.hasta_id, current_user["user_id"]))
            
           
            conn.execute('''
                INSERT INTO consultation_history (hasta_id, doktor_id, meslek_dali, soru, cevap)
                VALUES (?, ?, ?, ?, ?)
            ''', (prompt_data.hasta_id, current_user["user_id"], prompt_data.meslek_dali, prompt_data.prompt, ai_response))
        
        return {
            "ai_response": ai_response,
            "memory_messages_count": len(memory.chat_memory.messages),
            "is_first_message": len(memory.chat_memory.messages) == 2  # İlk soru-cevap çifti
        }
    
    except Exception as e:
        print(f"AI konsültasyon hatası: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI konsültasyon hatası: {str(e)}")


@router.get("/history/{patient_id}")
async def get_patient_consultation_history(patient_id: int, current_user: dict = Depends(verify_jwt_token)):
    try:
        print(f"DEBUG: Hasta ID: {patient_id}, Doktor ID: {current_user['user_id']}")
        
        with sqlite3.connect('medical_ai.db') as conn:
            conn.row_factory = sqlite3.Row
            
            
            results = conn.execute('''
                SELECT soru, cevap, meslek_dali, tarih
                FROM consultation_history 
                WHERE hasta_id = ? AND doktor_id = ?
                ORDER BY tarih DESC
            ''', (patient_id, current_user["user_id"])).fetchall()
            
            history = [dict(row) for row in results]
            print(f"DEBUG: Bulunan kayıt sayısı: {len(history)}")
            
            return {"history": history}
    
    except Exception as e:
        print(f"DEBUG: Hata oluştu: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Geçmiş yüklenirken hata: {str(e)}")

@router.delete("/clear-memory/{patient_id}")
async def clear_patient_memory(patient_id: int, current_user: dict = Depends(verify_jwt_token)):
    """Hasta memory'sini temizler"""
    try:
        if patient_id in patient_memories:
            del patient_memories[patient_id]
            return {"message": f"Hasta {patient_id} memory'si temizlendi"}
        else:
            return {"message": f"Hasta {patient_id} için memory bulunamadı"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory temizleme hatası: {str(e)}")

@router.get("/memory-status/{patient_id}")
async def get_memory_status(patient_id: int, current_user: dict = Depends(verify_jwt_token)):
    """Hasta memory durumunu gösterir"""
    try:
        if patient_id in patient_memories:
            memory = patient_memories[patient_id]
            return {
                "patient_id": patient_id,
                "message_count": len(memory.chat_memory.messages),
                "memory_exists": True,
                "last_messages": [msg.content for msg in memory.chat_memory.messages[-4:]] if memory.chat_memory.messages else []
            }
        else:
            return {
                "patient_id": patient_id,
                "message_count": 0,
                "memory_exists": False,
                "last_messages": []
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory durumu alınamadı: {str(e)}") 
    

@router.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """SpeechRecognition kütüphanesi ile ses dosyasını metne çevirir."""
    try:
        recognizer = sr.Recognizer()
        
        audio_data = await audio.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            
            with sr.AudioFile(temp_file_path) as source:
                
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_recorded = recognizer.record(source)
            
            try:
                transcript = recognizer.recognize_google(audio_recorded, language='tr-TR')
                
                if not transcript or transcript.strip() == "":
                    raise HTTPException(status_code=400, detail="Ses tanınamadı veya boş ses dosyası.")
                
                return {
                    "transcript": transcript.strip(),
                    "success": True,
                    "message": "Ses başarıyla metne çevrildi."
                }
                
            except sr.UnknownValueError:
                raise HTTPException(status_code=400, detail="Ses anlaşılamadı. Lütfen daha net konuşun veya ses kalitesini artırın.")
            
            except sr.RequestError as e:
                print(f"Google Speech API hatası: {e}")
                raise HTTPException(status_code=503, detail="Ses tanıma servisi şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyin.")
        
        finally:
            if os_path.exists(temp_file_path):
                os_path.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"Speech-to-Text genel hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Ses işleme sırasında beklenmeyen bir hata oluştu: {str(e)}")
