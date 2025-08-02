# Python 3.10 slim imajını kullan
FROM python:3.10-slim

# Çalışma dizinini ayarla
WORKDIR /app

# Sistem bağımlılıklarını yükle
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala
COPY . .

# Static dosyalar için gerekli dizinleri oluştur
RUN mkdir -p static/imagess static/css static/js

# Port 8000'i expose et
EXPOSE 8000

# Uygulama başlatma scripti
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]