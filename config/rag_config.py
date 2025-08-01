import os
from typing import Optional
try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    print("Pinecone kütüphanesi bulunamadı. RAG sistemi devre dışı.")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Sentence-transformers kütüphanesi bulunamadı. RAG sistemi devre dışı.")

class RAGConfig:
    """RAG sistemi için konfigürasyon sınıfı"""
    
    def __init__(self):
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
        self.index_name = "medintel-rag"
        self.embedding_model_name = "sentence-transformers/paraphrase-MiniLM-L6-v2"
        self.embedding_dimension = 384  # paraphrase-MiniLM-L6-v2 için
        
        # Pinecone client'ı başlat
        self.pinecone_client: Optional[Pinecone] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        
        # RAG sistemi aktif mi kontrolü
        self.is_rag_enabled = bool(self.pinecone_api_key and PINECONE_AVAILABLE and SENTENCE_TRANSFORMERS_AVAILABLE)
    
    def initialize_clients(self):
        """Pinecone ve embedding model'lerini başlat"""
        if not self.is_rag_enabled:
            return False
            
        try:
            if not PINECONE_AVAILABLE:
                print("Pinecone kütüphanesi mevcut değil")
                return False
                
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                print("Sentence-transformers kütüphanesi mevcut değil")
                return False
            
            # Pinecone client'ı başlat
            self.pinecone_client = Pinecone(api_key=self.pinecone_api_key)
            
            # Embedding model'i yükle - hata yakalama ile
            try:
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                print(f"Embedding model '{self.embedding_model_name}' başarıyla yüklendi")
            except Exception as model_error:
                print(f"Embedding model yüklenirken hata: {model_error}")
                # Alternatif model dene
                try:
                    self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                    print("Alternatif embedding model 'all-MiniLM-L6-v2' yüklendi")
                except Exception as alt_error:
                    print(f"Alternatif model de yüklenemedi: {alt_error}")
                    return False
            
            # Index'in var olup olmadığını kontrol et
            self._ensure_index_exists()
            
            return True
        except Exception as e:
            print(f"RAG sistemi başlatılamadı: {e}")
            self.is_rag_enabled = False
            return False
    
    def _ensure_index_exists(self):
        """Index'in var olduğundan emin ol, yoksa oluştur"""
        if not self.pinecone_client:
            return
            
        try:
            # Mevcut index'leri listele
            existing_indexes = [index.name for index in self.pinecone_client.list_indexes()]
            print(f"Mevcut Pinecone index'leri: {existing_indexes}")
            
            if self.index_name not in existing_indexes:
                print(f"Index '{self.index_name}' bulunamadı, oluşturuluyor...")
                
                # Index'i oluştur - basit format
                try:
                    self.pinecone_client.create_index(
                        name=self.index_name,
                        dimension=self.embedding_dimension,
                        metric="cosine"
                    )
                    print(f"Pinecone index '{self.index_name}' başarıyla oluşturuldu")
                except Exception as create_error:
                    print(f"Index oluşturma hatası: {create_error}")
                    # Alternatif yöntem dene
                    try:
                        self.pinecone_client.create_index(
                            name=self.index_name,
                            dimension=self.embedding_dimension,
                            metric="cosine",
                            spec=dict(
                                serverless=dict(
                                    cloud="aws",
                                    region=self.pinecone_environment
                                )
                            )
                        )
                        print(f"Pinecone index '{self.index_name}' alternatif yöntemle oluşturuldu")
                    except Exception as alt_error:
                        print(f"Alternatif index oluşturma da başarısız: {alt_error}")
                        raise alt_error
            else:
                print(f"Pinecone index '{self.index_name}' zaten mevcut")
                
        except Exception as e:
            print(f"Index kontrolü/oluşturulması sırasında hata: {e}")
            # Hata detaylarını yazdır
            import traceback
            traceback.print_exc()
    
    def get_index(self):
        """Pinecone index'ini döndür"""
        if not self.pinecone_client:
            return None
        return self.pinecone_client.Index(self.index_name)

# Global config instance
rag_config = RAGConfig()