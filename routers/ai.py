from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
from models import AIPrompt
from routers.auth import verify_jwt_token
from database import get_db, Hastalar, ConsultationHistory, TreatmentPlans, SessionLocal
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
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

import tempfile
import os as os_path
import io

load_dotenv()

router = APIRouter()

patient_memories = {}


def get_patient_memory(patient_id: int) -> ConversationBufferWindowMemory:
    """Hasta için memory alır veya oluşturur - sadece mevcut chat oturumu için"""
    if patient_id not in patient_memories:
        patient_memories[patient_id] = ConversationBufferWindowMemory(
            k=3,  # Optimal seviye: 3 mesaj sakla
            return_messages=True,
            memory_key="chat_history"
        )
    return patient_memories[patient_id]

def get_ai_model():
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY bulunamadı")
    
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",  # En güçlü model
        google_api_key=GEMINI_API_KEY,
        temperature=0.3,  # Daha yaratıcı yanıtlar
        max_tokens=800,   # Daha uzun yanıtlar için
        convert_system_message_to_human=True  
    )

def generate_treatment_steps(diagnosis_response: str, specialty: str, patient_info: str) -> str:
    """AI'dan gelen tanı yanıtına göre tedavi adımları listesi oluşturur"""
    try:
        model = get_ai_model()
        
        treatment_prompt = f"""
Sen bir {specialty} uzmanısın. {patient_info} için detaylı tedavi planı hazırla.

TANI DEĞERLENDİRMESİ:
{diagnosis_response[:300]}...

TEDAVİ PLANI FORMAT:

### 1. İlaçlı Tedavi Adımları:
* **İlaç Adı:** Doz, kullanım şekli ve süresi
* **İlaç 2:** Doz, kullanım şekli ve süresi

### 2. İlaçsız Tedavi Adımları:
* **Yaşam Tarzı:** Spesifik öneriler
* **Beslenme:** Detaylı rehber
* **Takip:** Kontrol zamanları

### 3. Önemli Uyarılar:
* Yan etkiler ve dikkat edilecek durumlar
* Acil başvuru koşulları

KURAL: Toplam 180-220 kelime, net ve uygulanabilir öneriler ver.
"""
        
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "Sen deneyimli bir tıp uzmanısın. Hasta tedavi planları hazırlıyorsun."),
            ("human", treatment_prompt)
        ])
        
        output_parser = StrOutputParser()
        chain = prompt_template | model | output_parser
        
        treatment_response = chain.invoke({})
        
        return treatment_response
        
    except Exception as e:
        print(f"Tedavi adımları oluşturma hatası: {e}")
        return "Tedavi adımları oluşturulamadı. Lütfen tekrar deneyiniz."

def format_treatment_for_email(treatment_text: str) -> str:
    """Tedavi metnini email için basit ve temiz formata çevirir"""
    if not treatment_text:
        return ""
    
    # Basit HTML formatlaması
    formatted = treatment_text
    
    # Markdown işaretlerini temizle
    formatted = formatted.replace("**", "")
    formatted = formatted.replace("###", "")
    formatted = formatted.replace("####", "")
    
    # Satır sonlarını HTML br ile değiştir
    formatted = formatted.replace("\n", "<br>")
    
    # Sadece ana başlıkları vurgula (basit)
    formatted = formatted.replace("TEDAVİ PLANI", '<h3>TEDAVİ PLANI</h3>')
    formatted = formatted.replace("1. İlaçlı Tedavi Adımları:", '<h4>1. İlaçlı Tedavi Adımları:</h4>')
    formatted = formatted.replace("2. İlaçsız Tedavi Adımları:", '<h4>2. İlaçsız Tedavi Adımları:</h4>')
    formatted = formatted.replace("3. Önemli Uyarılar:", '<h4>3. Önemli Uyarılar:</h4>')
    
    # Sadece ilaç isimlerini kalın yap
    import re
    formatted = re.sub(r'([A-Z][a-zA-ZğüşıöçĞÜŞİÖÇ]+\s+[%\d]+\s+(mg|krem|Krem|tablet|Tablet))', 
                      r'<strong>\1</strong>', formatted)
    
    # Liste öğelerini basit bullet point yap
    formatted = re.sub(r'\* (.*?):', r'<br>• <strong>\1:</strong>', formatted)
    
    # Çoklu br'leri temizle
    formatted = re.sub(r'(<br>\s*){3,}', '<br><br>', formatted)
    
    return formatted

def send_treatment_email(patient_email: str, patient_name: str, doctor_name: str, specialty: str, treatment_steps: str):
    """Tedavi adımlarını hasta mailine gönderir"""
    try:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("FROM_EMAIL")
        
        if not all([smtp_username, smtp_password, from_email]):
            raise ValueError("Email ayarları eksik")
        
        # Email içeriği
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; background: #fff; border-radius: 10px; }}
                .header {{ background: #2c5530; color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
                .content {{ padding: 30px; }}
                .treatment-section {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; }}
                h1, h2, h3 {{ color: #2c5530; }}
                .logo {{ font-size: 24px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🏥 MedIntelligence</div>
                    <h2>Tedavi Planınız Hazır</h2>
                </div>
                
                <div class="content">
                    <h3>Sayın {patient_name},</h3>
                    <p>Dr. {doctor_name} ({specialty.title()} Uzmanı) tarafından hazırlanan tedavi planınız aşağıdadır:</p>
                    
                    <div class="treatment-section">
                        <h3>📋 Tedavi Adımları</h3>
                        <div style="line-height: 1.8; font-size: 14px;">{format_treatment_for_email(treatment_steps)}</div>
                    </div>
                    
                    <div class="warning">
                        <h4>⚠️ Önemli Uyarılar:</h4>
                        <ul>
                            <li>Bu tedavi planı genel önerilerdir, kişisel durumunuza göre değişiklik gösterebilir</li>
                            <li>İlaçları kullanmadan önce mutlaka kontrole gelin</li>
                            <li>Herhangi bir yan etki durumunda derhal başvurun</li>
                            <li>Tedaviye uyum için düzenli kontrolleri aksatmayın</li>
                        </ul>
                    </div>
                    
                    <p><strong>Tarih:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
                    <p><strong>Sorumlu Doktor:</strong> Dr. {doctor_name}</p>
                    <p><strong>Uzmanlık Dalı:</strong> {specialty.title()}</p>
                </div>
                
                <div class="footer">
                    <p>Bu e-posta Dr. {doctor_name} tarafından gönderilmiştir.</p>
                    <p>Sağlıklı günler dileriz! 🌟</p>
                    <p style="font-size: 12px; color: #666;">
                        MedIntelligence AI Destekli Tıbbi Konsültasyon Sistemi
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Email oluştur
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Tedavi Planınız - Dr. {doctor_name}"
        msg['From'] = from_email
        msg['To'] = patient_email
        
        # HTML kısmını ekle
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Email gönder
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"Email gönderme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Email gönderilemedi: {str(e)}")

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
        "noroloji": """Sen nöroloji uzmanısın. Meslektaşına konsültasyon veriyorsun.

KURAL: Maksimum 3 tanı, her tanı için 3-4 cümle açıklama, toplam 200-250 kelime.
FORMAT: 
1. **Olası Tanı**: Klinik bulgular ve neden bu tanıyı düşündüğün. Önerilen tetkikler. Tedavi yaklaşımı.

Önceki mesajları hatırla. Meslektaş seviyesinde detaylı ama öz bilgi ver.""",
        "dermatoloji": """Sen dermatoloji uzmanısın. Meslektaşına konsültasyon veriyorsun.

KURAL: Maksimum 3 tanı, her tanı için 3-4 cümle açıklama, toplam 200-250 kelime.
FORMAT: 
1. **Olası Tanı**: Cilt bulguları ve neden bu tanıyı düşündüğün. Önerilen tetkikler. Tedavi yaklaşımı.

Önceki mesajları hatırla. Meslektaş seviyesinde detaylı ama öz bilgi ver.""",
        "kardiyoloji": """Sen kardiyoloji uzmanısın. Meslektaşına konsültasyon veriyorsun.

KURAL: Maksimum 3 tanı, her tanı için 3-4 cümle açıklama, toplam 200-250 kelime.
FORMAT: 
1. **Olası Tanı**: Kardiyak bulgular ve neden bu tanıyı düşündüğün. Önerilen tetkikler. Tedavi yaklaşımı.

Önceki mesajları hatırla. Meslektaş seviyesinde detaylı ama öz bilgi ver.""",
        "pediatri": """Sen pediatri uzmanısın. Meslektaşına konsültasyon veriyorsun.

KURAL: Maksimum 3 tanı, her tanı için 3-4 cümle açıklama, toplam 200-250 kelime.
FORMAT: 
1. **Olası Tanı**: Çocuk yaşına özgü bulgular ve neden bu tanıyı düşündüğün. Önerilen tetkikler. Tedavi yaklaşımı.

Önceki mesajları hatırla. Meslektaş seviyesinde detaylı ama öz bilgi ver.""",
        "kbb": """Sen KBB uzmanısın. Meslektaşına konsültasyon veriyorsun.

KURAL: Maksimum 3 tanı, her tanı için 3-4 cümle açıklama, toplam 200-250 kelime.
FORMAT: 
1. **Olası Tanı**: KBB bulguları ve neden bu tanıyı düşündüğün. Önerilen tetkikler. Tedavi yaklaşımı.

Önceki mesajları hatırla. Meslektaş seviyesinde detaylı ama öz bilgi ver.""",
        "dahiliye": """Sen dahiliye uzmanısın. Meslektaşına konsültasyon veriyorsun.

KURAL: Maksimum 3 tanı, her tanı için 3-4 cümle açıklama, toplam 200-250 kelime.
FORMAT: 
1. **Olası Tanı**: İç hastalık bulguları ve neden bu tanıyı düşündüğün. Önerilen tetkikler. Tedavi yaklaşımı.

Önceki mesajları hatırla. Meslektaş seviyesinde detaylı ama öz bilgi ver.""",
        "endokrinoloji": """Sen endokrinoloji uzmanısın. Meslektaşına konsültasyon veriyorsun.

KURAL: Maksimum 3 tanı, her tanı için 3-4 cümle açıklama, toplam 200-250 kelime.
FORMAT: 
1. **Olası Tanı**: Hormon bulguları ve neden bu tanıyı düşündüğün. Önerilen tetkikler. Tedavi yaklaşımı.

Önceki mesajları hatırla. Meslektaş seviyesinde detaylı ama öz bilgi ver.""",
        "ortopedi": """Sen ortopedi uzmanısın. Meslektaşına konsültasyon veriyorsun.

KURAL: Maksimum 3 tanı, her tanı için 3-4 cümle açıklama, toplam 200-250 kelime.
FORMAT: 
1. **Olası Tanı**: Ortopedik bulgular ve neden bu tanıyı düşündüğün. Önerilen tetkikler. Tedavi yaklaşımı.

Önceki mesajları hatırla. Meslektaş seviyesinde detaylı ama öz bilgi ver.""",
        "psikoloji": """Sen psikoloji uzmanısın. Meslektaşına konsültasyon veriyorsun.

RAG: "İlgili bilgiler:" varsa kullan.
KURAL: Maksimum 3 tanı, her tanı için 3-4 cümle açıklama, toplam 200-250 kelime.
FORMAT: 
1. **Olası Tanı**: Psikolojik bulgular ve neden bu tanıyı düşündüğün. Önerilen değerlendirmeler. Tedavi yaklaşımı.

Önceki mesajları hatırla. Meslektaş seviyesinde detaylı ama öz bilgi ver."""
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
        
        # Hasta bilgilerini önceden al
        db = SessionLocal()
        try:
            patient_result = db.query(Hastalar).filter(
                Hastalar.id == prompt_data.hasta_id,
                Hastalar.doktor_id == current_user["user_id"]
            ).first()
            
            if patient_result:
                patient_info = f"Hasta: {patient_result.ad} {patient_result.soyad}, Doğum Tarihi: {patient_result.dogum_tarihi or 'Belirtilmemiş'}, Email: {patient_result.email or 'Belirtilmemiş'}"
            else:
                patient_info = "Hasta bilgileri bulunamadı"
        finally:
            db.close()
        
        # Paralel işleme için asyncio kullan
        import asyncio
        import concurrent.futures
        
        ai_start = time.time()
        
        # Ana tanı yanıtı
        ai_response = chain.invoke({
            "hasta_durumu": enhanced_prompt,
            "chat_history": chat_history
        })
        
        # Memory'e ekle
        memory.chat_memory.add_user_message(f"Soru: {prompt_data.prompt}")
        memory.chat_memory.add_ai_message(f"Cevap: {ai_response}")
        
        # Tedavi adımlarını paralel oluştur
        treatment_steps = generate_treatment_steps(ai_response, prompt_data.meslek_dali, patient_info)
        
        ai_end = time.time()
        print(f"Toplam AI işlem süresi: {ai_end - ai_start:.2f} saniye")
        print(f"LangChain AI yanıtı: {len(ai_response)} karakter")
        print(f"Chat Memory'de {len(memory.chat_memory.messages)} mesaj var")
        
        # Veritabanına kaydet
        db = SessionLocal()
        try:
            # Hasta tablosunu güncelle
            patient = db.query(Hastalar).filter(
                Hastalar.id == prompt_data.hasta_id,
                Hastalar.doktor_id == current_user["user_id"]
            ).first()
            
            if patient:
                patient.tani_bilgileri = prompt_data.prompt
                patient.ai_onerileri = ai_response
                # son_guncelleme otomatik güncellenecek (onupdate=func.now())
            
            # Konsültasyon geçmişini kaydet
            consultation = ConsultationHistory(
                hasta_id=prompt_data.hasta_id,
                doktor_id=current_user["user_id"],
                meslek_dali=prompt_data.meslek_dali,
                soru=prompt_data.prompt,
                cevap=ai_response
            )
            db.add(consultation)
            
            # Tedavi planını kaydet
            try:
                treatment_plan = TreatmentPlans(
                    hasta_id=prompt_data.hasta_id,
                    doktor_id=current_user["user_id"],
                    meslek_dali=prompt_data.meslek_dali,
                    tani_bilgisi=ai_response,
                    tedavi_adimlari=treatment_steps
                )
                db.add(treatment_plan)
                
            except Exception as db_error:
                print(f"Tedavi planı kaydetme hatası: {db_error}")
            
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Veritabanı kaydetme hatası: {e}")
        finally:
            db.close()
        
        return {
            "ai_response": ai_response,
            "treatment_steps": treatment_steps,
            "memory_messages_count": len(memory.chat_memory.messages),
            "is_first_message": len(memory.chat_memory.messages) == 2,  # İlk soru-cevap çifti
            "patient_info": patient_info
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
    """Gemini modeli ile ses dosyasını metne çevirir."""
    try:
        import google.generativeai as genai
        import base64
        
        # Gemini API key'ini al
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY bulunamadı")
        
        # Gemini'yi yapılandır
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Ses dosyasını oku
        audio_data = await audio.read()
        
        # Ses dosyasını base64'e çevir
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # MIME type'ı belirle
        mime_type = "audio/wav"  # Varsayılan
        if audio.filename.lower().endswith('.mp3'):
            mime_type = "audio/mpeg"
        elif audio.filename.lower().endswith('.m4a'):
            mime_type = "audio/mp4"
        elif audio.filename.lower().endswith('.ogg'):
            mime_type = "audio/ogg"
        
        try:
            # Gemini'ye ses dosyasını gönder
            response = model.generate_content([
                "Bu ses dosyasını Türkçe olarak metne çevir. Sadece çevrilen metni döndür, başka açıklama ekleme.",
                {
                    "mime_type": mime_type,
                    "data": audio_base64
                }
            ])
            
            transcript = response.text.strip()
            
            if not transcript or transcript.strip() == "":
                raise HTTPException(status_code=400, detail="Ses tanınamadı veya boş ses dosyası.")
            
            return {
                "transcript": transcript,
                "success": True,
                "message": "Gemini ile ses başarıyla metne çevrildi."
            }
            
        except Exception as gemini_error:
            print(f"Gemini ses tanıma hatası: {gemini_error}")
            raise HTTPException(status_code=500, detail="Gemini AI ile ses tanıma başarısız oldu. Lütfen daha net konuşun veya daha sonra tekrar deneyin.")
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"Speech-to-Text genel hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Ses işleme sırasında beklenmeyen bir hata oluştu: {str(e)}")

@router.get("/treatment-plans/{patient_id}")
async def get_treatment_plans(patient_id: int, current_user: dict = Depends(verify_jwt_token)):
    """Hasta için bekleyen tedavi planlarını listeler"""
    try:
        with sqlite3.connect('medical_ai.db') as conn:
            conn.row_factory = sqlite3.Row
            
            # Tedavi planlarını al
            plans = conn.execute('''
                SELECT tp.*, h.ad, h.soyad, h.email
                FROM treatment_plans tp
                LEFT JOIN hastalar h ON tp.hasta_id = h.id
                WHERE tp.hasta_id = ? AND tp.doktor_id = ?
                ORDER BY tp.olusturma_tarihi DESC
            ''', (patient_id, current_user["user_id"])).fetchall()
            
            return {
                "treatment_plans": [dict(plan) for plan in plans]
            }
    
    except Exception as e:
        print(f"Tedavi planları listeleme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Tedavi planları yüklenemedi: {str(e)}")

@router.post("/approve-treatment/{plan_id}")
async def approve_and_send_treatment(plan_id: int, current_user: dict = Depends(verify_jwt_token)):
    """Tedavi planını onaylar ve hasta mailine gönderir"""
    try:
        with sqlite3.connect('medical_ai.db') as conn:
            conn.row_factory = sqlite3.Row
            
            # Tedavi planını ve hasta bilgilerini al
            plan_data = conn.execute('''
                SELECT tp.*, h.ad, h.soyad, h.email, k.ad as doktor_ad, k.soyad as doktor_soyad
                FROM treatment_plans tp
                LEFT JOIN hastalar h ON tp.hasta_id = h.id
                LEFT JOIN kullanicilar k ON tp.doktor_id = k.id
                WHERE tp.id = ? AND tp.doktor_id = ?
            ''', (plan_id, current_user["user_id"])).fetchone()
            
            if not plan_data:
                raise HTTPException(status_code=404, detail="Tedavi planı bulunamadı")
            
            if not plan_data['email']:
                raise HTTPException(status_code=400, detail="Hasta email adresi bulunamadı")
            
            # Doktor adını birleştir
            doctor_name = f"{plan_data['doktor_ad']} {plan_data['doktor_soyad']}"
            patient_name = f"{plan_data['ad']} {plan_data['soyad']}"
            
            # Email gönder
            send_treatment_email(
                patient_email=plan_data['email'],
                patient_name=patient_name,
                doctor_name=doctor_name,
                specialty=plan_data['meslek_dali'],
                treatment_steps=plan_data['tedavi_adimlari']
            )
            
            # Tedavi planını onaylandı olarak işaretle
            conn.execute('''
                UPDATE treatment_plans 
                SET onay_durumu = 'onaylandi', 
                    email_gonderildi = TRUE, 
                    onay_tarihi = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (plan_id,))
            
            return {
                "success": True,
                "message": f"Tedavi planı onaylandı ve {plan_data['email']} adresine gönderildi",
                "patient_email": plan_data['email'],
                "patient_name": patient_name
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Tedavi planı onaylama hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Tedavi planı onaylanamadı: {str(e)}")

@router.delete("/treatment-plan/{plan_id}")
async def reject_treatment_plan(plan_id: int, current_user: dict = Depends(verify_jwt_token)):
    """Tedavi planını reddeder"""
    try:
        with sqlite3.connect('medical_ai.db') as conn:
            result = conn.execute('''
                UPDATE treatment_plans 
                SET onay_durumu = 'reddedildi'
                WHERE id = ? AND doktor_id = ?
            ''', (plan_id, current_user["user_id"]))
            
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Tedavi planı bulunamadı")
            
            return {
                "success": True,
                "message": "Tedavi planı reddedildi"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Tedavi planı reddetme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Tedavi planı reddedilemedi: {str(e)}")
