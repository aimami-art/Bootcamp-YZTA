let currentPatients = [];

function showNewPatientForm() {
    document.getElementById('newPatientForm').style.display = 'block';
    document.getElementById('patientList').style.display = 'none';
}

function hideNewPatientForm() {
    document.getElementById('newPatientForm').style.display = 'none';
    document.getElementById('patientForm').reset();
}

function showPatientList() {
    document.getElementById('newPatientForm').style.display = 'none';
    document.getElementById('patientList').style.display = 'block';
    loadPatients();
}

function setPatientLoading(loading = true) {
    const button = document.getElementById('addPatientBtn');
    if (loading) {
        button.disabled = true;
        button.textContent = 'Kaydediliyor...';
    } else {
        button.disabled = false;
        button.textContent = 'Hasta Kaydet';
    }
}

async function loadPatients() {
    const container = document.getElementById('patients-container');
    container.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Hastalar yükleniyor...</p>
        </div>
    `;
    
    try {
        const token = getAuthToken();
        const response = await fetch('/api/patients', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            currentPatients = data.patients;
            displayPatients(data.patients);
        } else {
            throw new Error('Hastalar yüklenemedi');
        }
    } catch (error) {
        console.error('Load patients error:', error);
        container.innerHTML = `
            <div class="alert alert-error">
                Hastalar yüklenirken bir hata oluştu.
            </div>
        `;
    }
}

function displayPatients(patients) {
    const container = document.getElementById('patients-container');

    if (patients.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                Henüz kayıtlı hasta bulunmuyor.
            </div>
        `;
        return;
    }

    const patientsHtml = patients.map(patient => `
        <div class="patient-item">
            <div class="patient-info">
                <h4>${patient.ad} ${patient.soyad}</h4>
                <p>Doğum Tarihi: ${new Date(patient.dogum_tarihi).toLocaleDateString('tr-TR')}</p>
                <p>E-posta: ${patient.email || 'Belirtilmemiş'}</p>
                <p>Kayıt: ${new Date(patient.kayit_tarihi).toLocaleDateString('tr-TR')}</p>
            </div>
            <div class="patient-actions">
                <button class="btn btn-info" onclick="selectPatientForAI(${patient.id}, '${patient.ad} ${patient.soyad}')">
                    AI Konsültasyon
                </button>
                <button class="btn btn-secondary" onclick="viewPatientHistory(${patient.id})">
                    Geçmiş Görüntüle
                </button>
            </div>
        </div>
    `).join('');

    container.innerHTML = patientsHtml;
}

function selectPatientForAI(patientId, patientName) {
    localStorage.setItem('selectedPatientId', patientId);
    localStorage.setItem('selectedPatientName', patientName);
    window.location.href = '/ai-assistant';
}

function viewPatientHistory(patientId) {
    localStorage.setItem('selectedPatientId', patientId);
    window.location.href = '/patient-history';
}

function validateBirthDate(dateString) {
    const birthDate = new Date(dateString);
    const today = new Date();

    // Doğum tarihi bugünden ileri olamaz
    if (birthDate > today) {
        return false;
    }

    // Doğum tarihi çok eski olamaz (150 yıldan fazla)
    const maxAge = new Date();
    maxAge.setFullYear(maxAge.getFullYear() - 150);
    if (birthDate < maxAge) {
        return false;
    }

    return true;
}

function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

if (document.getElementById('patientForm')) {
    document.getElementById('patientForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const ad = document.getElementById('patient_ad').value.trim();
        const soyad = document.getElementById('patient_soyad').value.trim();
        const dogumTarihi = document.getElementById('patient_dogum_tarihi').value;
        const email = document.getElementById('patient_email').value.trim();

        if (!ad || !soyad || !dogumTarihi || !email) {
            showAlert('Lütfen tüm alanları doldurunuz.');
            return;
        }

        if (!validateBirthDate(dogumTarihi)) {
            showAlert('Geçerli bir doğum tarihi giriniz.');
            return;
        }

        if (!validateEmail(email)) {
            showAlert('Geçerli bir e-posta adresi giriniz.');
            return;
        }

        setPatientLoading(true);

        try {
            const token = getAuthToken();
            const response = await fetch('/api/patients', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    ad: ad,
                    soyad: soyad,
                    dogum_tarihi: dogumTarihi,
                    email: email
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showAlert('Hasta başarıyla kaydedildi!', 'success');
                document.getElementById('patientForm').reset();
                setTimeout(() => {
                    hideNewPatientForm();
                    showPatientList();
                }, 1500);
            } else {
                showAlert(data.detail || 'Hasta kaydedilemedi!');
            }
        } catch (error) {
            console.error('Add patient error:', error);
            showAlert('Bir hata oluştu. Lütfen tekrar deneyiniz.');
        } finally {
            setPatientLoading(false);
        }
    });
}

if (document.getElementById('patient_tc')) {
    document.getElementById('patient_tc').addEventListener('input', function(e) {
        this.value = this.value.replace(/[^0-9]/g, '');
        
        if (this.value.length > 11) {
            this.value = this.value.slice(0, 11);
        }
    });
} 