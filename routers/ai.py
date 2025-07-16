from fastapi import APIRouter, HTTPException, Depends
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

load_dotenv()

router = APIRouter()

# Memory sistemi - Her hasta için ayrı memory
patient_memories = {}

def get_patient_memory(patient_id: int) -> ConversationBufferWindowMemory:
    """Hasta için memory alır veya oluşturur - sadece mevcut chat oturumu için"""
    if patient_id not in patient_memories:
        patient_memories[patient_id] = ConversationBufferWindowMemory(
            k=6,  # Son 6 mesajı hatırla (3 soru-cevap çifti)
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
        temperature=0.1  
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
    try:
        # AI model ve memory hazırla
        model = get_ai_model()
        memory = get_patient_memory(prompt_data.hasta_id)
        prompt_template = create_prompt_template_with_memory(prompt_data.meslek_dali.lower())
        
        # Output parser
        output_parser = StrOutputParser()
        
        # Chain oluştur
        chain = prompt_template | model | output_parser
        
        # Memory'den chat history al (sadece mevcut chat oturumu)
        chat_history = memory.chat_memory.messages
        
        # AI'dan cevap al
        ai_response = chain.invoke({
            "hasta_durumu": prompt_data.prompt,
            "chat_history": chat_history
        })
        
        # Yeni mesajları memory'ye ekle
        memory.chat_memory.add_user_message(f"Soru: {prompt_data.prompt}")
        memory.chat_memory.add_ai_message(f"Cevap: {ai_response}")
        
        print(f"LangChain AI yanıtı (Chat Memory ile): {len(ai_response)} karakter")
        print(f"Chat Memory'de {len(memory.chat_memory.messages)} mesaj var")
        
        # Veritabanını güncelle
        with sqlite3.connect('medical_ai.db') as conn:
            conn.execute('''
                UPDATE hastalar 
                SET tani_bilgileri = ?, ai_onerileri = ?, son_guncelleme = CURRENT_TIMESTAMP
                WHERE id = ? AND doktor_id = ?
            ''', (prompt_data.prompt, ai_response, prompt_data.hasta_id, current_user["user_id"]))
        
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