let currentPatientId = null;
let currentPatientData = null;
let currentSpecialty = null;

document.addEventListener('DOMContentLoaded', function() {
    initializePatientHistory();
});

function initializePatientHistory() {
    currentPatientId = localStorage.getItem('selectedPatientId');
    currentSpecialty = localStorage.getItem('selectedSpecialty');
    
    if (!currentPatientId || !currentSpecialty) {
        showAlert('Hasta seçimi eksik. Yönlendiriliyorsunuz...', 'error');
        setTimeout(() => {
            window.location.href = '/patients';
        }, 2000);
        return;
    }
    
    loadPatientData();
}

async function loadPatientData() {
    try {
        const token = getAuthToken();
        const response = await fetch('/api/patients/', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            const patients = data.patients || data;
            console.log('Hasta verileri:', patients);
            currentPatientData = patients.find(p => p.id == currentPatientId);
            console.log('Seçilen hasta:', currentPatientData);
            
            if (currentPatientData) {
                displayPatientInfo();
                displayPatientHistory();
            } else {
                showAlert('Hasta bulunamadı.', 'error');
                setTimeout(() => {
                    window.location.href = '/patients';
                }, 2000);
            }
        } else {
            throw new Error('Hasta bilgileri yüklenemedi');
        }
    } catch (error) {
        console.error('Patient data error:', error);
        showAlert('Hasta bilgileri yüklenirken bir hata oluştu.');
    }
}

function displayPatientInfo() {
    if (!currentPatientData) return;
    
    document.getElementById('patientTitle').textContent = `${currentPatientData.ad} ${currentPatientData.soyad} - Geçmiş`;
    document.getElementById('patientName').textContent = `${currentPatientData.ad} ${currentPatientData.soyad}`;
    document.getElementById('patientBirthDate').textContent = formatDate(currentPatientData.dogum_tarihi);
    document.getElementById('patientDate').textContent = formatDate(currentPatientData.kayit_tarihi);
}

async function displayPatientHistory() {
    const historyContainer = document.getElementById('historyContainer');
    
    try {
        
        const token = getAuthToken();
        console.log('Hasta ID:', currentPatientId);
        console.log('Token:', token ? 'Var' : 'Yok');
        
        const response = await fetch(`/api/ai/history/${currentPatientId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        console.log('Response status:', response.status);
        console.log('Response OK:', response.ok);
        
        if (response.ok) {
            const data = await response.json();
            console.log('API Response:', data);
            const history = data.history || [];
            console.log('History length:', history.length);
            
            if (history.length > 0) {
                let historyHtml = '';
                
                history.forEach((consultation, index) => {
                    historyHtml += `
                        <div class="history-dialog" style="margin-bottom: 20px; border: 1px solid #ddd; padding: 15px; border-radius: 8px;">
                            <div class="consultation-header">
                                <h4>🩺 Konsültasyon ${history.length - index}</h4>
                                <small>Uzmanlık: ${consultation.meslek_dali} | Tarih: ${formatDate(consultation.tarih)}</small>
                            </div>
                            
                            <div class="question-section" style="margin: 15px 0;">
                                <h5>❓ Sorulan Soru</h5>
                                <div class="question-content" style="background: #f8f9fa; padding: 10px; border-radius: 4px;">
                                    ${formatText(consultation.soru)}
                                </div>
                            </div>
                            
                            <div class="answer-section" style="margin: 15px 0;">
                                <h5>🤖 AI Yanıtı</h5>
                                <div class="answer-content" style="background: #e3f2fd; padding: 10px; border-radius: 4px;">
                                    ${formatText(consultation.cevap)}
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                historyContainer.innerHTML = historyHtml;
            } else {
                historyContainer.innerHTML = `
                    <div class="no-history">
                        <p>📝 Bu hasta için henüz konsültasyon geçmişi bulunmuyor.</p>
                        <p>AI konsültasyonu yapıldıktan sonra geçmiş burada görüntülenecektir.</p>
                    </div>
                `;
            }
        } else {
            console.error('API Error:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('Error details:', errorText);
            throw new Error(`API Error: ${response.status} - ${errorText}`);
        }
    } catch (error) {
        console.error('History error:', error);
        historyContainer.innerHTML = `
            <div class="error-message">
                <p>❌ Geçmiş yüklenirken bir hata oluştu.</p>
                <p>Hata: ${error.message}</p>
                <p>Browser console'u kontrol edin.</p>
            </div>
        `;
    }
}

function formatText(text) {
    if (!text) return '';
    
    return text
        // Önce bold ve italic işaretlerini işle
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Çift satır boşlukları paragraf ayırıcı yap
        .replace(/\n{2,}/g, '||PARAGRAPH||')
        // Tekli satır boşluklarını boşluk yap (cümleleri birleştir)
        .replace(/\n/g, ' ')
        // Paragraf ayırıcıları geri çevir
        .replace(/\|\|PARAGRAPH\|\|/g, '<br><br>')
        // "Değerlendirme:" dan sonra satır sonu
        .replace(/Değerlendirme:/g, '<strong>Değerlendirme:</strong><br>')
        // 1. 2. 3. ifadelerinden önce satır sonu ve kalın yap
        .replace(/(\d+\.\s+)(Olası\s+)/g, '<br><br><strong>$1$2</strong>')
        // Tanı adından sonra iki nokta üst üste varsa satır sonu
        .replace(/(<strong>.*?<\/strong>):\s/g, '$1:</strong><br>')
        // Fazla boşlukları ve fazla br'leri temizle
        .replace(/\s{2,}/g, ' ')
        .replace(/(<br>){3,}/g, '<br><br>')
        .trim();
}

function formatDate(dateString) {
    if (!dateString) return '-';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('tr-TR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return dateString;
    }
}

function goBack() {
    window.location.href = '/patients';
} 