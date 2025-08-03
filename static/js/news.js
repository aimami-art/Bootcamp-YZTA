// Haberleri yükleyen fonksiyon
async function loadAIHealthNews() {
    try {
        const response = await fetch(`${window.location.protocol}//${window.location.host}/api/news/ai-health`);
        const data = await response.json();
        
        if (data.success && data.news) {
            displayNews(data.news);
        } else {
            console.error('Haberler yüklenemedi');
            showFallbackNews();
        }
    } catch (error) {
        console.error('Haber yükleme hatası:', error);
        showFallbackNews();
    }
}

// Haberleri görüntüleyen fonksiyon
function displayNews(news) {
    const newsContainer = document.querySelector('.news-container');
    if (!newsContainer) return;
    
    // Mevcut haberleri temizle
    newsContainer.innerHTML = '';
    
    // Her haber için kart oluştur
    news.forEach((item, index) => {
        const newsCard = createNewsCard(item, index);
        newsContainer.appendChild(newsCard);
    });
}

// Haber kartı oluşturan fonksiyon
function createNewsCard(newsItem, index) {
    const card = document.createElement('div');
    card.className = 'news-card';
    
    // Varsayılan resim seçimi - sadece mevcut dosyaları kullan
    const availableImages = ['photo2.jpg', 'photo6.jpg'];
    const imageIndex = index % availableImages.length;
    const imageSrc = `/static/imagess/${availableImages[imageIndex]}`;
    
    // Tarih formatını düzenle
    const publishedDate = formatDate(newsItem.published);
    
    // Dil etiketi
    const languageLabel = newsItem.language === 'tr' ? '🇹🇷 Türkçe' : '🇺🇸 English';
    
    card.innerHTML = `
        <img src="${imageSrc}" alt="${newsItem.title}" class="news-image" onerror="this.src='/static/imagess/photo6.jpg'">
        <div class="news-content">
            <div class="news-header">
                <h3>${newsItem.title}</h3>
                <span class="language-badge">${languageLabel}</span>
            </div>
            <p>${newsItem.summary}</p>
            <div class="news-meta">
                <span class="news-source">${newsItem.source}</span>
                <span class="news-date">${publishedDate}</span>
            </div>
            <a href="${newsItem.link}" target="_blank" class="btn btn-outline">Devamını Oku</a>
        </div>
    `;
    
    return card;
}

// Tarih formatını düzenleyen fonksiyon
function formatDate(dateString) {
    if (!dateString) return 'Güncel';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('tr-TR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    } catch (error) {
        return 'Güncel';
    }
}

    // Varsayılan haberleri gösteren fonksiyon
    function showFallbackNews() {
        const fallbackNews = [
            {
                title: 'Yapay Zeka Sağlık Teknolojilerinde Devrim',
                summary: 'AI destekli sağlık teknolojileri, hastalık teşhisi ve tedavi süreçlerinde devrim yaratıyor. Makine öğrenmesi algoritmaları, doktorların daha hızlı ve doğru kararlar almasına yardımcı oluyor.',
                source: 'MedIntel Haberleri',
                published: '2024-01-20',
                language: 'tr'
            },
            {
                title: 'AI-Powered Healthcare Revolution',
                summary: 'Artificial intelligence healthcare technologies are revolutionizing disease diagnosis and treatment processes. Machine learning algorithms help doctors make faster and more accurate decisions.',
                source: 'Healthcare Technology News',
                published: '2024-01-18',
                language: 'en'
            }
        ];
        
        displayNews(fallbackNews);
    }

// Haberleri yenileme fonksiyonu
async function refreshNews() {
    try {
        const response = await fetch(`${window.location.protocol}//${window.location.host}/api/news/refresh`);
        const data = await response.json();
        
        if (data.success) {
            // Haberleri yeniden yükle
            await loadAIHealthNews();
            showNotification('Haberler başarıyla yenilendi!', 'success');
        } else {
            showNotification('Haberler yenilenirken hata oluştu!', 'error');
        }
    } catch (error) {
        console.error('Haber yenileme hatası:', error);
        showNotification('Haberler yenilenirken hata oluştu!', 'error');
    }
}

// Bildirim gösteren fonksiyon
function showNotification(message, type = 'info') {
    // Mevcut bildirimi kaldır
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Yeni bildirim oluştur
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Stil ekle
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    // Tip'e göre renk
    if (type === 'success') {
        notification.style.backgroundColor = '#4CAF50';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#f44336';
    } else {
        notification.style.backgroundColor = '#2196F3';
    }
    
    document.body.appendChild(notification);
    
    // 3 saniye sonra kaldır
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, 3000);
}

// CSS animasyonları ekle
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .news-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        font-size: 0.9rem;
        color: #666;
        margin-top: auto;
    }
    
    .news-source {
        font-weight: bold;
        color: #00796b;
    }
    
    .news-date {
        color: #999;
    }
    
    .news-refresh-btn {
        background: #009688;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        cursor: pointer;
        margin-bottom: 20px;
        font-weight: bold;
        transition: background 0.3s ease;
    }
    
    .news-refresh-btn:hover {
        background: #00796b;
    }
`;
document.head.appendChild(style);

// Sayfa yüklendiğinde haberleri yükle
document.addEventListener('DOMContentLoaded', function() {
    loadAIHealthNews();
    
    // Haber yenileme butonu ekle
    const newsSection = document.querySelector('.news-section');
    if (newsSection) {
        const refreshBtn = document.createElement('button');
        refreshBtn.className = 'news-refresh-btn';
        refreshBtn.textContent = '🔄 Haberleri Yenile';
        refreshBtn.onclick = refreshNews;
        
        // Butonu başlığın altına ekle
        const newsTitle = newsSection.querySelector('.news-title');
        if (newsTitle) {
            newsTitle.parentNode.insertBefore(refreshBtn, newsTitle.nextSibling);
        }
    }
}); 