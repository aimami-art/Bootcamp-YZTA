let currentPatientId = null;
let currentPatientName = null;
let currentSpecialty = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeAIAssistant();
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
    
    document.getElementById('patientTitle').textContent = `${currentPatientName} - AI Konsültasyon`;
    document.getElementById('specialtyInfo').textContent = `${currentSpecialty.charAt(0).toUpperCase() + currentSpecialty.slice(1)} dalı için AI destekli tanı ve öneriler`;
    
    addSpecialtyMessage();
}

function addSpecialtyMessage() {
    const specialtyText = currentSpecialty === 'noroloji' ? 
        'Nöroloji uzmanı olarak çalışıyorum. Sinir sistemi, beyin ve omurilik ile ilgili sorunları değerlendireceğim.' :
        'Dermatoloji uzmanı olarak çalışıyorum. Cilt hastalıkları ve deri sorunlarını değerlendireceğim.';
    
    const chatContainer = document.getElementById('chatContainer');
    const specialtyMessage = document.createElement('div');
    specialtyMessage.className = 'message ai';
    specialtyMessage.innerHTML = `
        <div class="message-header">🏥 ${currentSpecialty.charAt(0).toUpperCase() + currentSpecialty.slice(1)} Uzmanı</div>
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
            
            showAlert('AI yanıtı alındı ve hasta dosyasına kaydedildi.', 'success');
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

function addSamplePrompts() {
    const samplePrompts = {
        'noroloji': [
            'Hasta baş ağrısı ve görme bulanıklığı şikayeti ile geldi.',
            'Hastada tremor ve yürüme güçlüğü gözleniyor.',
            'Hasta uyuşma ve karıncalanma hissi yaşıyor.'
        ],
        'dermatoloji': [
            'Hastada kızarık ve kaşıntılı döküntü var.',
            'Ciltte renk değişikliği ve leke oluşumu gözleniyor.',
            'Hasta saç dökülmesi problemi yaşıyor.'
        ]
    };
    
    const samples = samplePrompts[currentSpecialty] || [];
    
    if (samples.length > 0) {
        const chatContainer = document.getElementById('chatContainer');
        const samplesDiv = document.createElement('div');
        samplesDiv.className = 'message ai';
        samplesDiv.innerHTML = `
            <div class="message-header">💡 Örnek Sorular</div>
            <div class="message-content">
                <p>İşte ${currentSpecialty} alanında sık karşılaşılan durumlar:</p>
                ${samples.map(sample => `
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

setTimeout(addSamplePrompts, 1000); 


let recognizing = false;
let recognition;

if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'tr-TR';

    recognition.onstart = function() {
        recognizing = true;
        document.getElementById('micBtn').classList.add('recording');
        document.getElementById('micBtn').innerText = '🛑';
    };
    recognition.onend = function() {
        recognizing = false;
        document.getElementById('micBtn').classList.remove('recording');
        document.getElementById('micBtn').innerText = '🎤';
    };
    recognition.onerror = function(event) {
        recognizing = false;
        document.getElementById('micBtn').classList.remove('recording');
        document.getElementById('micBtn').innerText = '🎤';
        showAlert('Ses tanıma hatası: ' + event.error);
    };
    recognition.onresult = function(event) {
        if (event.results.length > 0) {
            const transcript = event.results[0][0].transcript;
            const promptInput = document.getElementById('promptInput');
            promptInput.value += (promptInput.value ? ' ' : '') + transcript;
            promptInput.focus();
        }
    };

    document.getElementById('micBtn').addEventListener('click', function() {
        if (recognizing) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });
} else {
    document.getElementById('micBtn').addEventListener('click', function() {
        showAlert('Tarayıcınızda sesle yazma desteklenmiyor.');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const audioFileInput = document.getElementById('audioFile');
    if (audioFileInput) {
        audioFileInput.addEventListener('change', async function(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            if (!file.type.startsWith('audio/')) {
                showAlert('Lütfen geçerli bir ses dosyası seçin (MP3, WAV, M4A vb.).');
                this.value = '';
                return;
            }
            
            if (file.size > 10 * 1024 * 1024) {
                showAlert('Ses dosyası çok büyük. Lütfen 10MB altında bir dosya seçin.');
                this.value = '';
                return;
            }
            
            const uploadBtn = document.getElementById('uploadAudioBtn');
            uploadBtn.disabled = true;
            uploadBtn.innerHTML = '⏳ Çevriliyor...';
            
            try {
                const formData = new FormData();
                formData.append('audio', file);
                
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
                    showAlert(data.message || 'Ses başarıyla metne çevrildi!', 'success');
                } else {
                    showAlert(data.detail || 'Ses çevrilirken hata oluştu.');
                }
            } catch (error) {
                console.error('Speech-to-text upload error:', error);
                showAlert('Ses dosyası yüklenirken bir hata oluştu. İnternet bağlantınızı kontrol edin.');
            } finally {
                uploadBtn.disabled = false;
                uploadBtn.innerHTML = '📁🎤';
                this.value = ''; // Input'u temizle
            }
        });
    }
});