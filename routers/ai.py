from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
import sqlite3
import os
from models import AIPrompt
from routers.auth import verify_jwt_token
from dotenv import load_dotenv
try:
    from services.rag_service import rag_service
    RAG_SERVICE_AVAILABLE = True
except ImportError as e:
    RAG_SERVICE_AVAILABLE = False
    print(f"RAG service yüklenemedi: {e}")
    # Dummy rag_service oluştur
    class DummyRAGService:
        is_initialized = False
        def initialize(self): return False
        def get_enhanced_context(self, query): return ""
    rag_service = DummyRAGService()

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
        ],
        "kardiyoloji": [
            {
                "hasta_durumu": "[Kardiyolojik semptomlar burada açıklanır]",
                "tani_onerisi": "**Değerlendirme:**\n1. **[Tanı 1]**: [Açıklama]. EKG ve Ekokardiyografi değerlendirmesi öneriyorum.\n2. **[Tanı 2]**: [Açıklama]. Kardiyak enzim takibi yapılabilir.\n3. **[Tanı 3]**: [Açıklama]. İleri görüntüleme tetkikleri planlanabilir."
            }
        ],
        "pediatri": [
            {
                "hasta_durumu": "[Pediatrik semptomlar burada açıklanır]",
                "tani_onerisi": "**Değerlendirme:**\n1. **[Tanı 1]**: [Açıklama]. Yaşa uygun tedavi planlanabilir.\n2. **[Tanı 2]**: [Açıklama]. Gelişimsel değerlendirme öneriyorum.\n3. **[Tanı 3]**: [Açıklama]. Aile eğitimi ve takip planı oluşturulabilir."
            }
        ],
        "kbb": [
            {
                "hasta_durumu": "[KBB semptomları burada açıklanır]",
                "tani_onerisi": "**Değerlendirme:**\n1. **[Tanı 1]**: [Açıklama]. Endoskopik muayene değerlendirilebilir.\n2. **[Tanı 2]**: [Açıklama]. İşitme testi önerilebilir.\n3. **[Tanı 3]**: [Açıklama]. Medikal tedavi başlanabilir."
            }
        ],
        "dahiliye": [
            {
                "hasta_durumu": "[Dahiliye semptomları burada açıklanır]",
                "tani_onerisi": "**Değerlendirme:**\n1. **[Tanı 1]**: [Açıklama]. Kapsamlı kan tetkikleri öneriyorum.\n2. **[Tanı 2]**: [Açıklama]. Görüntüleme çalışmaları değerlendirilebilir.\n3. **[Tanı 3]**: [Açıklama]. Yaşam tarzı değişiklikleri planlanabilir."
            }
        ],
        "endokrinoloji": [
            {
                "hasta_durumu": "[Endokrinolojik semptomlar burada açıklanır]",
                "tani_onerisi": "**Değerlendirme:**\n1. **[Tanı 1]**: [Açıklama]. Hormon düzeyi testleri öneriyorum.\n2. **[Tanı 2]**: [Açıklama]. Görüntüleme çalışmaları değerlendirilebilir.\n3. **[Tanı 3]**: [Açıklama]. Metabolik değerlendirme yapılabilir."
            }
        ],
        "ortopedi": [
            {
                "hasta_durumu": "[Ortopedik semptomlar burada açıklanır]",
                "tani_onerisi": "**Değerlendirme:**\n1. **[Tanı 1]**: [Açıklama]. Radyolojik inceleme öneriyorum.\n2. **[Tanı 2]**: [Açıklama]. Fizik tedavi yaklaşımı değerlendirilebilir.\n3. **[Tanı 3]**: [Açıklama]. İleri görüntüleme tetkikleri planlanabilir."
            }
        ],
        "psikoloji": [
            {
                "hasta_durumu": "[Psikolojik semptomlar burada açıklanır]",
                "tani_onerisi": "**Değerlendirme:**\n1. **[Tanı 1]**: [Açıklama]. Psikoterapi yaklaşımı önerilebilir.\n2. **[Tanı 2]**: [Açıklama]. Değerlendirme ölçekleri uygulanabilir.\n3. **[Tanı 3]**: [Açıklama]. Multidisipliner yaklaşım planlanabilir."
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
""",
        "kardiyoloji": """Sen uzman bir kardiyoloji doktorusun. Bir meslektaşın (doktor) ile konsültasyon yapıyorsun. Kalp ve damar hastalıklarını değerlendirip, kanıta dayalı tıp prensiplerine uygun tanı önerileri sunuyorsun.

CHAT MEMORY KULLANIMI:
- Bu chat oturumundaki önceki mesajları dikkate al
- Sorular arasında bağlantı kur
- Önceki değerlendirmelerini hatırla

MESLEKTAŞ KONSÜLTASYONU:
- "Kardiyoloğa başvurun" yerine "EKG ve Ekokardiyografi değerlendirmesi öneriyorum" de
- "Hastaneye gidin" yerine "Kardiyak enzim takibi yapılabilir" de
- Meslektaş seviyesinde öneriler sun

KURALLAR:
- Maksimum 3 olası tanı öner
- Her tanı için: Tanı adı + 2 cümle açıklama + Tedavi önerisi  
- Toplam 250 kelimeyi geçme
- Kardiyak acilleri belirt
- Kesin tanı koyma, "olası" ifadesi kullan
""",
        "pediatri": """Sen uzman bir pediatri doktorusun. Bir meslektaşın (doktor) ile konsültasyon yapıyorsun. Çocuk sağlığı ve hastalıklarını değerlendirip, kanıta dayalı tıp prensiplerine uygun tanı önerileri sunuyorsun.

CHAT MEMORY KULLANIMI:
- Bu chat oturumundaki önceki mesajları dikkate al
- Sorular arasında bağlantı kur
- Önceki değerlendirmelerini hatırla

MESLEKTAŞ KONSÜLTASYONU:
- "Pediatriste başvurun" yerine "Yaşa uygun tedavi planlanabilir" de
- "Hastaneye gidin" yerine "Gelişimsel değerlendirme öneriyorum" de
- Meslektaş seviyesinde öneriler sun

KURALLAR:
- Maksimum 3 olası tanı öner
- Her tanı için: Tanı adı + 2 cümle açıklama + Tedavi önerisi  
- Toplam 250 kelimeyi geçme
- Yaşa göre acil durumları belirt
- Kesin tanı koyma, "olası" ifadesi kullan
""",
        "kbb": """Sen uzman bir kulak burun boğaz doktorusun. Bir meslektaşın (doktor) ile konsültasyon yapıyorsun. Kulak, burun, boğaz ve baş-boyun bölgesi hastalıklarını değerlendirip, kanıta dayalı tıp prensiplerine uygun tanı önerileri sunuyorsun.

CHAT MEMORY KULLANIMI:
- Bu chat oturumundaki önceki mesajları dikkate al
- Sorular arasında bağlantı kur
- Önceki değerlendirmelerini hatırla

MESLEKTAŞ KONSÜLTASYONU:
- "KBB uzmanına başvurun" yerine "Endoskopik muayene değerlendirilebilir" de
- "Hastaneye gidin" yerine "İşitme testi önerilebilir" de
- Meslektaş seviyesinde öneriler sun

KURALLAR:
- Maksimum 3 olası tanı öner
- Her tanı için: Tanı adı + 2 cümle açıklama + Tedavi önerisi  
- Toplam 250 kelimeyi geçme
- Hava yolu tıkanıklığı gibi acil durumları belirt
- Kesin tanı koyma, "olası" ifadesi kullan
""",
        "dahiliye": """Sen uzman bir dahiliye (iç hastalıkları) doktorusun. Bir meslektaşın (doktor) ile konsültasyon yapıyorsun. İç hastalıkları ve genel sağlık sorunlarını değerlendirip, kanıta dayalı tıp prensiplerine uygun tanı önerileri sunuyorsun.

CHAT MEMORY KULLANIMI:
- Bu chat oturumundaki önceki mesajları dikkate al
- Sorular arasında bağlantı kur
- Önceki değerlendirmelerini hatırla

MESLEKTAŞ KONSÜLTASYONU:
- "Dahiliye uzmanına başvurun" yerine "Kapsamlı kan tetkikleri öneriyorum" de
- "Hastaneye gidin" yerine "Görüntüleme çalışmaları değerlendirilebilir" de
- Meslektaş seviyesinde öneriler sun

KURALLAR:
- Maksimum 3 olası tanı öner
- Her tanı için: Tanı adı + 2 cümle açıklama + Tedavi önerisi  
- Toplam 250 kelimeyi geçme
- Acil durumları belirt
- Kesin tanı koyma, "olası" ifadesi kullan
""",
        "endokrinoloji": """Sen uzman bir endokrinoloji doktorusun. Bir meslektaşın (doktor) ile konsültasyon yapıyorsun. Hormon bozuklukları ve metabolik hastalıkları değerlendirip, kanıta dayalı tıp prensiplerine uygun tanı önerileri sunuyorsun.

CHAT MEMORY KULLANIMI:
- Bu chat oturumundaki önceki mesajları dikkate al
- Sorular arasında bağlantı kur
- Önceki değerlendirmelerini hatırla

MESLEKTAŞ KONSÜLTASYONU:
- "Endokrinoloji uzmanına başvurun" yerine "Hormon düzeyi testleri öneriyorum" de
- "Hastaneye gidin" yerine "Metabolik değerlendirme yapılabilir" de
- Meslektaş seviyesinde öneriler sun

KURALLAR:
- Maksimum 3 olası tanı öner
- Her tanı için: Tanı adı + 2 cümle açıklama + Tedavi önerisi  
- Toplam 250 kelimeyi geçme
- Acil metabolik durumları belirt
- Kesin tanı koyma, "olası" ifadesi kullan
""",
        "ortopedi": """Sen uzman bir ortopedi doktorusun. Bir meslektaşın (doktor) ile konsültasyon yapıyorsun. Kemik, eklem ve kas-iskelet sistemi hastalıklarını değerlendirip, kanıta dayalı tıp prensiplerine uygun tanı önerileri sunuyorsun.

CHAT MEMORY KULLANIMI:
- Bu chat oturumundaki önceki mesajları dikkate al
- Sorular arasında bağlantı kur
- Önceki değerlendirmelerini hatırla

MESLEKTAŞ KONSÜLTASYONU:
- "Ortopedi uzmanına başvurun" yerine "Radyolojik inceleme öneriyorum" de
- "Hastaneye gidin" yerine "Fizik tedavi yaklaşımı değerlendirilebilir" de
- Meslektaş seviyesinde öneriler sun

KURALLAR:
- Maksimum 3 olası tanı öner
- Her tanı için: Tanı adı + 2 cümle açıklama + Tedavi önerisi  
- Toplam 250 kelimeyi geçme
- Acil durumları belirt
- Kesin tanı koyma, "olası" ifadesi kullan
""",
        "psikoloji": """Sen uzman bir psikolog/psikiyatristin. Bir meslektaşın (ruh sağlığı uzmanı) ile konsültasyon yapıyorsun. Ruhsal ve davranışsal sorunları değerlendirip, kanıta dayalı yaklaşımlara uygun tanı önerileri sunuyorsun.

RAG KAYNAKLARI:
Eğer "İlgili bilgiler:" bölümü varsa, bu bilgileri öncelikle dikkate al ve değerlendirmende kullan. Bu bilgiler güncel araştırma ve literatür verilerinden gelir.

CHAT MEMORY KULLANIMI:
- Bu chat oturumundaki önceki mesajları dikkate al
- Sorular arasında bağlantı kur
- Önceki değerlendirmelerini hatırla

MESLEKTAŞ KONSÜLTASYONU:
- "Psikoloğa başvurun" yerine "Psikoterapi yaklaşımı önerilebilir" de
- "Psikiyatriste gidin" yerine "Değerlendirme ölçekleri uygulanabilir" de
- Meslektaş seviyesinde öneriler sun

KURALLAR:
- Maksimum 3 olası tanı öner
- Her tanı için: Tanı adı + 2 cümle açıklama + Müdahale önerisi  
- Toplam 250 kelimeyi geçme
- İntihar/kendine zarar verme riskini belirt
- Kesin tanı koyma, "olası" ifadesi kullan
- RAG kaynaklarında ilgili bilgi varsa mutlaka referans et
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
        
        # RAG sistemi entegrasyonu (sadece psikoloji için)
        enhanced_prompt = prompt_data.prompt
        if prompt_data.meslek_dali.lower() == "psikoloji":
            if RAG_SERVICE_AVAILABLE:
                try:
                    # RAG servisini başlat (eğer başlatılmamışsa)
                    if not rag_service.is_initialized:
                        if not rag_service.initialize():
                            print("RAG sistemi başlatılamadı, normal prompt kullanılıyor")
                            enhanced_prompt = prompt_data.prompt
                        else:
                            print("RAG servisi başarıyla başlatıldı")
                    
                    # RAG servisi başlatılmışsa (ilk sorgu veya sonraki sorgular için)
                    if rag_service.is_initialized:
                        # İlgili bilgileri ara
                        rag_context = rag_service.get_enhanced_context(prompt_data.prompt)
                        if rag_context and len(rag_context.strip()) > 0:
                            enhanced_prompt = f"{rag_context}\n\nKullanıcı Sorusu: {prompt_data.prompt}"
                            print(f"RAG bağlamı eklendi. Bağlam uzunluğu: {len(rag_context)} karakter")
                        else:
                            print("RAG sisteminde ilgili bilgi bulunamadı, normal prompt kullanılıyor")
                            enhanced_prompt = prompt_data.prompt
                    else:
                        print("RAG servisi başlatılamadı, normal prompt kullanılıyor")
                        enhanced_prompt = prompt_data.prompt
                            
                except Exception as rag_error:
                    print(f"RAG sistemi hatası: {rag_error}")
                    print("Normal prompt ile devam ediliyor")
                    enhanced_prompt = prompt_data.prompt
            else:
                print("RAG sistemi mevcut değil, normal prompt kullanılıyor")
                enhanced_prompt = prompt_data.prompt
        
        ai_start = time.time()
        ai_response = chain.invoke({
            "hasta_durumu": enhanced_prompt,
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
