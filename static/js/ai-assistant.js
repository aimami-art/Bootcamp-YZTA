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
    
    document.getElementById('patientTitle').textContent = `${currentPatientName} - AI Konsültasyon`;
    document.getElementById('specialtyInfo').textContent = `${currentSpecialty.charAt(0).toUpperCase() + currentSpecialty.slice(1)} dalı için AI destekli tanı ve öneriler`;
    
    addSpecialtyMessage();
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

// Örnek sorular fonksiyonu
function addSamplePrompts() {
    const samplePromptsContainer = document.getElementById('sample-prompts');
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


let recognizing = false;
let recognition;
let mediaRecorder;
let audioChunks = [];

// Gemini ile ses tanıma için yeni fonksiyon
async function startGeminiVoiceRecording() {
    try {
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

// Mikrofon butonuna tıklama olayı
document.getElementById('micBtn').addEventListener('click', function() {
    if (recognizing) {
        stopGeminiVoiceRecording();
    } else {
        startGeminiVoiceRecording();
    }
});

