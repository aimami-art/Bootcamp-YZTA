import os
from typing import Optional, List
from config.rag_config import RAGConfig

class RAGService:
    """RAG (Retrieval-Augmented Generation) servisi"""
    
    def __init__(self):
        self.config = RAGConfig()
        self.is_initialized = False
        
    def initialize(self) -> bool:
        """RAG servisini başlat"""
        try:
            if not self.config.is_rag_enabled:
                print("RAG sistemi devre dışı")
                return False
                
            success = self.config.initialize_clients()
            if success:
                self.is_initialized = True
                print("RAG servisi başarıyla başlatıldı")
            else:
                print("RAG servisi başlatılamadı")
                
            return success
            
        except Exception as e:
            print(f"RAG servisi başlatma hatası: {e}")
            return False
    
    def get_enhanced_context(self, query: str) -> str:
        """Sorgu için geliştirilmiş bağlam getir"""
        if not self.is_initialized:
            print("RAG servisi başlatılmamış")
            return ""
            
        try:
            # Sorguyu vektöre çevir
            query_embedding = self.config.embedding_model.encode(query).tolist()
            
            # Pinecone'da benzer vektörleri ara
            index = self.config.pinecone_client.Index(self.config.index_name)
            results = index.query(
                vector=query_embedding,
                top_k=5,  # Daha fazla sonuç al, sonra filtrele
                include_metadata=True
            )
            
            # Benzerlik skoru eşiği (0.5 = %50 benzerlik)
            similarity_threshold = 0.5
            
            # Sonuçları filtrele ve birleştir
            context_parts = []
            for match in results.matches:
                # Benzerlik skorunu kontrol et
                if match.score >= similarity_threshold:
                    if match.metadata and 'text' in match.metadata:
                        context_parts.append(f"İlgili Bilgi (Benzerlik: {match.score:.2f}): {match.metadata['text']}")
                        print(f"RAG sonucu bulundu - Benzerlik skoru: {match.score:.2f}")
                else:
                    print(f"Düşük benzerlik skoru: {match.score:.2f} - Bu sonuç kullanılmıyor")
            
            if context_parts:
                return "\n\n".join(context_parts)
            else:
                print("Benzerlik eşiğini geçen sonuç bulunamadı")
                return ""
                
        except Exception as e:
            print(f"RAG bağlam getirme hatası: {e}")
            return ""
    
    def process_pdf_and_upload(self, file_content: bytes, filename: str, description: str = None) -> bool:
        """PDF dosyasını işle ve Pinecone'a yükle"""
        if not self.is_initialized:
            print("RAG servisi başlatılmamış")
            return False
            
        try:
            # PyPDF2 ile PDF'den metin çıkar
            import PyPDF2
            import io
            
            # PDF dosyasını oku
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            
            # Tüm sayfalardan metin çıkar
            text_content = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text() + "\n"
            
            # Eğer açıklama varsa ekle
            if description:
                text_content = f"Açıklama: {description}\n\n" + text_content
            
            # PDF'den metin çıkarılamadıysa fallback
            if not text_content.strip():
                text_content = f"PDF içeriği: {filename}"
                if description:
                    text_content += f"\nAçıklama: {description}"
            
            # Metni vektöre çevir
            embedding = self.config.embedding_model.encode(text_content).tolist()
            
            # Pinecone'a yükle
            index = self.config.pinecone_client.Index(self.config.index_name)
            index.upsert(
                vectors=[{
                    'id': f"doc_{filename}_{hash(text_content)}",
                    'values': embedding,
                    'metadata': {
                        'text': text_content,
                        'filename': filename,
                        'description': description or ""
                    }
                }]
            )
            
            print(f"PDF '{filename}' başarıyla RAG sistemine yüklendi")
            return True
            
        except Exception as e:
            print(f"PDF yükleme hatası: {e}")
            return False

# Global RAG servisi instance'ı
rag_service = RAGService() 