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
    document.getElementById('patientTC').textContent = currentPatientData.tc_kimlik;
    document.getElementById('patientDate').textContent = formatDate(currentPatientData.kayit_tarihi);
}

function displayPatientHistory() {
    const historyContainer = document.getElementById('historyContainer');
    
    console.log('Hasta tanı bilgileri:', currentPatientData.tani_bilgileri);
    console.log('Hasta AI önerileri:', currentPatientData.ai_onerileri);
    
    const hasQuestion = currentPatientData.tani_bilgileri && currentPatientData.tani_bilgileri.trim();
    const hasAnswer = currentPatientData.ai_onerileri && currentPatientData.ai_onerileri.trim();
    
    if (hasQuestion || hasAnswer) {
        let historyHtml = '<div class="history-dialog">';
        
        if (hasQuestion) {
            historyHtml += `
                <div class="question-section">
                    <h4>❓ Sorulan Soru</h4>
                    <div class="question-content">
                        ${formatText(currentPatientData.tani_bilgileri)}
                    </div>
                </div>
            `;
        }
        
        if (hasAnswer) {
            historyHtml += `
                <div class="answer-section">
                    <h4>🤖 AI Yanıtı</h4>
                    <div class="answer-content">
                        ${formatText(currentPatientData.ai_onerileri)}
                    </div>
                </div>
            `;
        }
        
        historyHtml += `
            <div class="history-footer">
                <small>Son güncelleme: ${formatDate(currentPatientData.son_guncelleme || currentPatientData.kayit_tarihi)}</small>
            </div>
        `;
        
        historyHtml += '</div>';
        
        historyContainer.innerHTML = historyHtml;
    } else {
        historyContainer.innerHTML = `
            <div class="no-history">
                <p>📝 Bu hasta için henüz soru-cevap geçmişi bulunmuyor.</p>
                <p>AI konsültasyonu yapıldıktan sonra geçmiş burada görüntülenecektir.</p>
            </div>
        `;
    }
}

function formatText(text) {
    if (!text) return '';
    
    return text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/(\d+\.\s)/g, '<br><strong>$1</strong>'); // Numaralı listeleri vurgula
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