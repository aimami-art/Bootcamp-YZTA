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
        const response = await fetch(`${window.location.protocol}//${window.location.host}/api/patients/`, {
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
    document.getElementById('patientEmail').textContent = currentPatientData.email || 'Belirtilmemiş';
    document.getElementById('patientDate').textContent = formatDate(currentPatientData.kayit_tarihi);
}

let consultationHistory = [];

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
            consultationHistory = data.history || [];
            console.log('History length:', consultationHistory.length);
            
            if (consultationHistory.length > 0) {
                populateQuestionSelector();
                hideHistoryContainer();
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

function populateQuestionSelector() {
    console.log('populateQuestionSelector çağrıldı');
    const questionSelect = document.getElementById('questionSelect');
    const questionSelectorContainer = document.getElementById('questionSelectorContainer');
    
    if (!questionSelect || !questionSelectorContainer) {
        console.error('Soru seçici elementler bulunamadı');
        return;
    }
    
    // Select'i temizle
    questionSelect.innerHTML = '<option value="">-- Bir soru seçin --</option>';
    
    // Soruları ekle
    consultationHistory.forEach((consultation, index) => {
        const questionPreview = consultation.soru.length > 80 
            ? consultation.soru.substring(0, 80) + '...'
            : consultation.soru;
        
        const option = document.createElement('option');
        option.value = index;
        option.textContent = `Konsültasyon ${consultationHistory.length - index}: ${questionPreview}`;
        questionSelect.appendChild(option);
    });
    
    // Soru seçici container'ı göster
    questionSelectorContainer.style.display = 'block';
    console.log('Soru seçici görünür hale getirildi');
}

function hideHistoryContainer() {
    const historyContainer = document.getElementById('historyContainer');
    historyContainer.innerHTML = `
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center;">
            <p style="color: #666; margin: 0;">Yukarıdaki dropdown menüden bir soru seçerek cevabını görüntüleyebilirsiniz.</p>
        </div>
    `;
}

function showSelectedAnswer() {
    console.log('showSelectedAnswer fonksiyonu çağrıldı');
    const selectElement = document.getElementById('questionSelect');
    const selectedIndex = selectElement.value;
    const answerContainer = document.getElementById('selectedAnswerContainer');
    
    console.log('Seçilen index:', selectedIndex);
    
    if (!selectElement || !answerContainer) {
        console.error('Gerekli elementler bulunamadı');
        return;
    }
    
    if (selectedIndex === '') {
        answerContainer.style.display = 'none';
        hideHistoryContainer();
        return;
    }
    
    const consultation = consultationHistory[selectedIndex];
    if (!consultation) {
        console.error('Konsültasyon bulunamadı:', selectedIndex);
        return;
    }
    
    const selectedQuestionEl = document.getElementById('selectedQuestion');
    const selectedAnswerEl = document.getElementById('selectedAnswer');
    const consultationMetaEl = document.getElementById('consultationMeta');
    
    if (selectedQuestionEl && selectedAnswerEl && consultationMetaEl) {
        selectedQuestionEl.innerHTML = formatText(consultation.soru);
        selectedAnswerEl.innerHTML = formatText(consultation.cevap);
        consultationMetaEl.innerHTML = 
            `🩺 Uzmanlık: ${consultation.meslek_dali} | 📅 Tarih: ${formatDate(consultation.tarih)}`;
        
        answerContainer.style.display = 'block';
        console.log('Seçilen cevap gösterildi');
        
        // Alt kısımdaki history container'ı gizle
        const historyContainer = document.getElementById('historyContainer');
        if (historyContainer) {
            historyContainer.style.display = 'none';
        }
        
        // Smooth scroll to the answer
        setTimeout(() => {
            answerContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    } else {
        console.error('Cevap gösterme elementleri bulunamadı');
    }
}



function formatText(text) {
    if (!text) return '';
    
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n{2,}/g, '||PARAGRAPH||')
        .replace(/\n/g, ' ')
        .replace(/\|\|PARAGRAPH\|\|/g, '<br><br>')
        .replace(/Değerlendirme:/g, '<strong>Değerlendirme:</strong><br>')
        .replace(/(\d+\.\s+)(Olası\s+)/g, '<br><br><strong>$1$2</strong>')
        .replace(/(<strong>.*?<\/strong>):\s/g, '$1:</strong><br>')
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