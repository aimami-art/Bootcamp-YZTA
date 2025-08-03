let currentPatientId = null;
let currentPatientName = null;
let currentSpecialty = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeAIAssistant();
    
    // Örnek soruları eklemek için biraz gecikme ekleyelim
    setTimeout(function() {
        addSamplePrompts();
    }, 1000);
});

function initializeAIAssistant() {
    currentPatientId = localStorage.getItem('selectedPatientId');
    currentPatientName = localStorage.getItem('selectedPatientName');
    currentSpecialty = localStorage.getItem('selectedSpecialty');
    
    if (!currentPatientId || !currentPatientName || !currentSpecialty) {
        showAlert('Hasta veya meslek dalı seçimi eksik. Yönlendiriliyorsunuz...', 'error');
        setTimeout(() => {
            window.location.href = '/patients';
        }, 2000);
        return;
    }
    
    // DOM elementlerini güvenli şekilde güncelle
    const patientTitle = document.getElementById('patientTitle');
    const specialtyInfo = document.getElementById('specialtyInfo');
    
    if (patientTitle) {
        patientTitle.textContent = `${currentPatientName} - AI Konsültasyon`;
    }
    
    if (specialtyInfo) {
        specialtyInfo.textContent = `${currentSpecialty.charAt(0).toUpperCase() + currentSpecialty.slice(1)} dalı için AI destekli tanı ve öneriler`;
    }
    
    addSpecialtyMessage();
    
    // Mikrofon butonunu başlat
    initializeMicrophoneButton();
}

function addSpecialtyMessage() {
    let specialtyText = '';
    let specialtyEmoji = '';
    
    switch(currentSpecialty) {
        case 'noroloji':
            specialtyText = 'Nöroloji uzmanı olarak çalışıyorum. Sinir sistemi, beyin ve omurilik ile ilgili sorunları değerlendireceğim.';
            specialtyEmoji = '🧠';
            break;
        case 'dermatoloji':
            specialtyText = 'Dermatoloji uzmanı olarak çalışıyorum. Cilt hastalıkları ve dermatolojik sorunları değerlendireceğim.';
            specialtyEmoji = '🔬';
            break;
        case 'kardiyoloji':
            specialtyText = 'Kardiyoloji uzmanı olarak çalışıyorum. Kalp ve damar hastalıkları ile ilgili sorunları değerlendireceğim.';
            specialtyEmoji = '❤️';
            break;
        case 'pediatri':
            specialtyText = 'Pediatri uzmanı olarak çalışıyorum. Çocuk sağlığı ve hastalıkları ile ilgili sorunları değerlendireceğim.';
            specialtyEmoji = '👶';
            break;
        case 'kbb':
            specialtyText = 'Kulak Burun Boğaz uzmanı olarak çalışıyorum. KBB ve baş-boyun bölgesi ile ilgili sorunları değerlendireceğim.';
            specialtyEmoji = '👂';
            break;
        case 'dahiliye':
            specialtyText = 'Dahiliye uzmanı olarak çalışıyorum. İç hastalıkları ve genel sağlık sorunlarını değerlendireceğim.';
            specialtyEmoji = '🩺';
            break;
        case 'endokrinoloji':
            specialtyText = 'Endokrinoloji uzmanı olarak çalışıyorum. Hormon bozuklukları ve metabolik hastalıklar ile ilgili sorunları değerlendireceğim.';
            specialtyEmoji = '⚗️';
            break;
        case 'ortopedi':
            specialtyText = 'Ortopedi uzmanı olarak çalışıyorum. Kemik, eklem ve kas-iskelet sistemi hastalıkları ile ilgili sorunları değerlendireceğim.';
            specialtyEmoji = '🦴';
            break;
        case 'psikoloji':
            specialtyText = 'Psikoloji/Psikiyatri uzmanı olarak çalışıyorum. Ruhsal ve davranışsal sorunlar ile ilgili değerlendirme yapacağım.';
            specialtyEmoji = '🧩';
            break;
        default:
            specialtyText = `${currentSpecialty.charAt(0).toUpperCase() + currentSpecialty.slice(1)} uzmanı olarak çalışıyorum.`;
            specialtyEmoji = '🏥';
    }
    
    const chatContainer = document.getElementById('chatContainer');
    const specialtyMessage = document.createElement('div');
    specialtyMessage.className = 'message ai';
    specialtyMessage.innerHTML = `
        <div class="message-header">${specialtyEmoji} ${currentSpecialty.charAt(0).toUpperCase() + currentSpecialty.slice(1)} Uzmanı</div>
        <div class="message-content">${specialtyText}</div>
    `;
    
    chatContainer.appendChild(specialtyMessage);
    scrollToBottom();
}

function addMessage(content, isUser = false) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'ai'}`;
    
    const header = isUser ? '👤 Siz' : '🤖 AI Asistan';
    messageDiv.innerHTML = `
        <div class="message-header">${header}</div>
        <div class="message-content">${content}</div>
    `;
    
    chatContainer.appendChild(messageDiv);
    scrollToBottom();
}

function scrollToBottom() {
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function setLoading(loading = true) {
    const sendBtn = document.getElementById('sendBtn');
    const promptInput = document.getElementById('promptInput');
    
    if (loading) {
        sendBtn.disabled = true;
        sendBtn.innerHTML = '⏳ Gönderiliyor...';
        promptInput.disabled = true;
    } else {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '📤 Gönder';
        promptInput.disabled = false;
    }
}

function formatAIResponse(response) {
    if (!response) return '';

    return response
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

async function sendPrompt() {
    const promptInput = document.getElementById('promptInput');
    const prompt = promptInput.value.trim();
    
    if (!prompt) {
        showAlert('Lütfen bir mesaj yazın.');
        return;
    }
    
    addMessage(prompt, true);
    
    promptInput.value = '';
    
    setLoading(true);
    
    try {
        const token = getAuthToken();
        const response = await fetch('/api/ai/consultation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                hasta_id: parseInt(currentPatientId),
                prompt: prompt,
                meslek_dali: currentSpecialty
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            let formattedResponse = formatAIResponse(data.ai_response);
            
            addMessage(formattedResponse);
            
            // Tedavi adımları varsa göster
            if (data.treatment_steps) {
                addTreatmentStepsMessage(data.treatment_steps);
            }
            
            showAlert('AI yanıtı ve tedavi önerileri alındı!', 'success');
        } else {
            throw new Error(data.detail || 'AI yanıtı alınamadı');
        }
    } catch (error) {
        console.error('AI consultation error:', error);
        showAlert('AI yanıtı alınırken bir hata oluştu. Lütfen tekrar deneyiniz.');
    } finally {
        setLoading(false);
        promptInput.focus();
    }
}

document.getElementById('promptInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendPrompt();
    }
});

document.getElementById('promptInput').addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
});

// Örnek sorular fonksiyonu
function addSamplePrompts() {
    const samplePromptsContainer = document.getElementById('sample-prompts');
    
    // Element varsa devam et, yoksa çık
    if (!samplePromptsContainer) {
        console.warn('sample-prompts elementi bulunamadı');
        return;
    }
    
    samplePromptsContainer.innerHTML = '';
    
    let samplePrompts = [];
    
    switch(currentSpecialty) {
        case 'noroloji':
            samplePrompts = [
                'Baş ağrısı, bulantı ve ışığa hassasiyet şikayeti olan 35 yaşında kadın hasta',
                '60 yaşında erkek hasta, son 6 aydır artan titreme ve yavaşlık şikayeti var',
                'Ani başlayan konuşma güçlüğü ve sağ tarafta güçsüzlük olan 70 yaşında hasta'
            ];
            break;
        case 'dermatoloji':
            samplePrompts = [
                'Yüzde kızarıklık, pullanma ve kaşıntı şikayeti olan 25 yaşında hasta',
                'Vücutta yaygın kaşıntılı döküntüler olan 40 yaşında hasta',
                'El ve ayak parmaklarında şişlik, kızarıklık ve ağrı olan 50 yaşında hasta'
            ];
            break;
        case 'kardiyoloji':
            samplePrompts = [
                'Merdiven çıkarken nefes darlığı ve göğüs ağrısı olan 55 yaşında hasta',
                'Düzensiz kalp atışları ve çarpıntı şikayeti olan 45 yaşında hasta',
                'Ayaklarda şişlik ve egzersiz intoleransı olan 60 yaşında hasta'
            ];
            break;
        case 'pediatri':
            samplePrompts = [
                '3 yaşında çocuk, 3 gündür devam eden yüksek ateş ve döküntü şikayeti var',
                '8 aylık bebek, beslenme güçlüğü ve kilo alamama sorunu yaşıyor',
                '12 yaşında çocuk, karın ağrısı ve ishal şikayeti ile başvurdu'
            ];
            break;
        case 'kbb':
            samplePrompts = [
                'Kulakta ağrı, dolgunluk hissi ve işitme azalması olan 30 yaşında hasta',
                'Burun tıkanıklığı, geniz akıntısı ve baş ağrısı şikayeti olan 40 yaşında hasta',
                'Boğaz ağrısı, yutma güçlüğü ve ses kısıklığı olan 35 yaşında hasta'
            ];
            break;
        case 'dahiliye':
            samplePrompts = [
                'Halsizlik, yorgunluk ve kilo kaybı şikayeti olan 50 yaşında hasta',
                'Karın ağrısı, bulantı ve iştahsızlık şikayeti olan 45 yaşında hasta',
                'Eklem ağrıları, ateş ve döküntü şikayeti olan 35 yaşında hasta'
            ];
            break;
        case 'endokrinoloji':
            samplePrompts = [
                'Sürekli susama, sık idrara çıkma ve kilo kaybı şikayeti olan 40 yaşında hasta',
                'Boyun bölgesinde şişlik ve yutma güçlüğü olan 45 yaşında hasta',
                'Aşırı terleme, çarpıntı ve kilo kaybı şikayeti olan 35 yaşında hasta'
            ];
            break;
        case 'ortopedi':
            samplePrompts = [
                'Diz ağrısı, şişlik ve hareket kısıtlılığı olan 50 yaşında hasta',
                'Bel ağrısı ve bacağa yayılan ağrı şikayeti olan 45 yaşında hasta',
                'Omuz ağrısı ve kol kaldırma güçlüğü olan 55 yaşında hasta'
            ];
            break;
        case 'psikoloji':
            samplePrompts = [
                'Sürekli endişe, gerginlik ve uyku sorunları yaşayan 30 yaşında hasta',
                'Uzun süredir devam eden mutsuzluk, isteksizlik ve enerji kaybı olan 35 yaşında hasta',
                'Sosyal ortamlarda aşırı kaygı ve panik atak yaşayan 25 yaşında hasta'
            ];
            break;
        default:
            samplePrompts = [
                'Örnek soru 1',
                'Örnek soru 2',
                'Örnek soru 3'
            ];
    }
    
    if (samplePrompts.length > 0) {
        const chatContainer = document.getElementById('chatContainer');
        const samplesDiv = document.createElement('div');
        samplesDiv.className = 'message ai';
        samplesDiv.innerHTML = `
            <div class="message-header">💡 Örnek Sorular</div>
            <div class="message-content">
                <p>İşte ${currentSpecialty} alanında sık karşılaşılan durumlar:</p>
                ${samplePrompts.map(sample => `
                    <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; cursor: pointer; border: 1px solid #e9ecef;" 
                         onclick="document.getElementById('promptInput').value = '${sample}'; document.getElementById('promptInput').focus();">
                        "${sample}"
                    </div>
                `).join('')}
            </div>
        `;
        
        chatContainer.appendChild(samplesDiv);
        scrollToBottom();
    }
}

function addTreatmentStepsMessage(treatmentSteps) {
    const chatContainer = document.getElementById('chatContainer');
    const treatmentDiv = document.createElement('div');
    treatmentDiv.className = 'message ai treatment-message';
    
    // Tedavi adımlarını formatla
    const formattedTreatment = formatTreatmentSteps(treatmentSteps);
    
    treatmentDiv.innerHTML = `
        <div class="message-header">💊 Tedavi Önerileri</div>
        <div class="message-content">
            <div class="treatment-content">
                ${formattedTreatment}
            </div>
            <div class="treatment-actions" style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <p><strong>🩺 Doktor Onayı:</strong></p>
                <p style="margin: 10px 0; color: #6c757d;">Bu tedavi önerilerini inceleyip, hasta mailine göndermek için onaylayabilirsiniz.</p>
                <button id="approveTreatmentBtn" class="btn btn-success" onclick="loadTreatmentPlans()">
                    ✅ Tedavi Planlarını Görüntüle
                </button>
            </div>
        </div>
    `;
    
    chatContainer.appendChild(treatmentDiv);
    scrollToBottom();
}

function formatTreatmentSteps(treatmentSteps) {
    if (!treatmentSteps) return '';

    return treatmentSteps
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n{2,}/g, '||PARAGRAPH||')
        .replace(/\n/g, '<br>')
        .replace(/\|\|PARAGRAPH\|\|/g, '<br><br>')
        .replace(/(\d+\.\s+\*\*.*?\*\*)/g, '<br><br>$1')
        .replace(/(-\s+)/g, '<br>&nbsp;&nbsp;&nbsp;• ')
        .trim();
}



async function loadTreatmentPlans() {
    try {
        const token = getAuthToken();
        const response = await fetch(`/api/ai/treatment-plans/${currentPatientId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showTreatmentPlansModal(data.treatment_plans);
        } else {
            throw new Error(data.detail || 'Tedavi planları yüklenemedi');
        }
    } catch (error) {
        console.error('Tedavi planları yükleme hatası:', error);
        showAlert('Tedavi planları yüklenirken hata oluştu.');
    }
}

function showTreatmentPlansModal(treatmentPlans) {
    // Modal HTML'ini oluştur
    const modalHTML = `
        <div id="treatmentModal" class="modal" style="display: block; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
            <div class="modal-content" style="background-color: #fefefe; margin: 5% auto; padding: 20px; border-radius: 10px; width: 90%; max-width: 800px; max-height: 80vh; overflow-y: auto;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3>💊 Tedavi Planları - ${currentPatientName}</h3>
                    <span class="close" onclick="closeTreatmentModal()" style="font-size: 28px; font-weight: bold; cursor: pointer;">&times;</span>
                </div>
                
                <div class="modal-body">
                    ${treatmentPlans.length > 0 ? 
                        treatmentPlans.map((plan, index) => `
                            <div class="treatment-plan-card" style="border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px; background: ${plan.onay_durumu === 'onaylandi' ? '#d4edda' : plan.onay_durumu === 'reddedildi' ? '#f8d7da' : '#fff'};">
                                <div class="plan-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                    <div>
                                        <h5 style="margin: 0; color: #2c5530;">📋 Plan ${index + 1}</h5>
                                        <small style="color: #6c757d;">Oluşturulma: ${new Date(plan.olusturma_tarihi).toLocaleString('tr-TR')}</small>
                                    </div>
                                    <div>
                                        <span class="status-badge" style="padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; 
                                            background: ${plan.onay_durumu === 'onaylandi' ? '#28a745' : plan.onay_durumu === 'reddedildi' ? '#dc3545' : '#ffc107'}; 
                                            color: ${plan.onay_durumu === 'beklemede' ? '#000' : '#fff'};">
                                            ${plan.onay_durumu === 'onaylandi' ? '✅ Onaylandı' : plan.onay_durumu === 'reddedildi' ? '❌ Reddedildi' : '⏳ Beklemede'}
                                        </span>
                                    </div>
                                </div>
                                
                                <div class="plan-content" style="margin-bottom: 15px;">
                                    <h6>🎯 Tanı Bilgisi:</h6>
                                    <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px; max-height: 100px; overflow-y: auto;">
                                        ${plan.tani_bilgisi ? plan.tani_bilgisi.substring(0, 200) + '...' : 'Tanı bilgisi yok'}
                                    </div>
                                    
                                    <h6>💊 Tedavi Adımları:</h6>
                                    <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 15px; max-height: 150px; overflow-y: auto;">
                                        ${formatTreatmentSteps(plan.tedavi_adimlari)}
                                    </div>
                                </div>
                                
                                ${plan.onay_durumu === 'beklemede' ? `
                                    <div class="plan-actions" style="display: flex; gap: 10px;">
                                        <button class="btn btn-success" onclick="approveTreatmentPlan(${plan.id})" style="flex: 1;">
                                            ✅ Onayla ve Hasta Mailine Gönder
                                        </button>
                                        <button class="btn btn-danger" onclick="rejectTreatmentPlan(${plan.id})" style="flex: 1;">
                                            ❌ Reddet
                                        </button>
                                    </div>
                                ` : plan.onay_durumu === 'onaylandi' ? `
                                    <div style="color: #28a745; font-weight: bold;">
                                        📧 Email gönderildi: ${plan.email_gonderildi ? 'Evet' : 'Hayır'} 
                                        ${plan.onay_tarihi ? `(${new Date(plan.onay_tarihi).toLocaleString('tr-TR')})` : ''}
                                    </div>
                                ` : ''}
                            </div>
                        `).join('')
                        : '<p style="text-align: center; color: #6c757d; padding: 40px;">📝 Henüz tedavi planı oluşturulmamış.</p>'
                    }
                </div>
            </div>
        </div>
    `;
    
    // Modal'ı sayfaya ekle
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeTreatmentModal() {
    const modal = document.getElementById('treatmentModal');
    if (modal) {
        modal.remove();
    }
}

async function approveTreatmentPlan(planId) {
    if (!confirm('Bu tedavi planını onaylayıp hasta mailine göndermek istediğinizden emin misiniz?')) {
        return;
    }
    
    try {
        const token = getAuthToken();
        const response = await fetch(`/api/ai/approve-treatment/${planId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showAlert(`✅ Tedavi planı onaylandı ve ${data.patient_email} adresine gönderildi!`, 'success');
            closeTreatmentModal();
            // Tedavi planlarını yeniden yükle
            setTimeout(() => loadTreatmentPlans(), 1000);
        } else {
            throw new Error(data.detail || 'Tedavi planı onaylanamadı');
        }
    } catch (error) {
        console.error('Tedavi planı onaylama hatası:', error);
        showAlert('Tedavi planı onaylanırken hata oluştu: ' + error.message);
    }
}

async function rejectTreatmentPlan(planId) {
    if (!confirm('Bu tedavi planını reddetmek istediğinizden emin misiniz?')) {
        return;
    }
    
    try {
        const token = getAuthToken();
        const response = await fetch(`/api/ai/treatment-plan/${planId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showAlert('❌ Tedavi planı reddedildi.', 'warning');
            closeTreatmentModal();
            // Tedavi planlarını yeniden yükle
            setTimeout(() => loadTreatmentPlans(), 1000);
        } else {
            throw new Error(data.detail || 'Tedavi planı reddedilemedi');
        }
    } catch (error) {
        console.error('Tedavi planı reddetme hatası:', error);
        showAlert('Tedavi planı reddedilirken hata oluştu: ' + error.message);
    }
}



let recognizing = false;
let recognition;
let mediaRecorder;
let audioChunks = [];

// Gemini ile ses tanıma için yeni fonksiyon
async function startGeminiVoiceRecording() {
    try {
        // getUserMedia API'sinin varlığını kontrol et
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Bu tarayıcı mikrofon erişimini desteklemiyor');
        }
        
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = function(event) {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async function() {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            await processAudioWithGemini(audioBlob);
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        recognizing = true;
        document.getElementById('micBtn').classList.add('recording');
        document.getElementById('micBtn').innerText = '🛑';
        
    } catch (error) {
        console.error('Mikrofon erişim hatası:', error);
        showAlert('Mikrofon erişimi sağlanamadı. Lütfen tarayıcı izinlerini kontrol edin.');
    }
}

async function stopGeminiVoiceRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        recognizing = false;
        document.getElementById('micBtn').classList.remove('recording');
        document.getElementById('micBtn').innerText = '🎤';
    }
}

async function processAudioWithGemini(audioBlob) {
    try {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
        
        const token = getAuthToken();
        const response = await fetch('/api/ai/speech-to-text', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            const promptInput = document.getElementById('promptInput');
            promptInput.value += (promptInput.value ? ' ' : '') + data.transcript;
            promptInput.focus();
            showAlert('🎤 Gemini ile ses başarıyla metne çevrildi!', 'success');
        } else {
            showAlert(data.detail || 'Ses çevrilirken hata oluştu.');
        }
    } catch (error) {
        console.error('Gemini ses tanıma hatası:', error);
        showAlert('Ses işleme sırasında bir hata oluştu.');
    }
}

// Mikrofon butonuna tıklama olayı - DOMContentLoaded içinde eklenebilir
function initializeMicrophoneButton() {
    const micBtn = document.getElementById('micBtn');
    if (micBtn) {
        micBtn.addEventListener('click', function() {
            if (recognizing) {
                stopGeminiVoiceRecording();
            } else {
                startGeminiVoiceRecording();
            }
        });
    } else {
        console.warn('Mikrofon butonu bulunamadı');
    }
}

