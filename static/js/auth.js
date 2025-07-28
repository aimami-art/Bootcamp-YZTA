function showAlert(message, type = 'error') {
    const alertContainer = document.getElementById('alert-container');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function setLoading(buttonId, loading = true) {
    const button = document.getElementById(buttonId);
    if (loading) {
        button.disabled = true;
        button.textContent = 'İşleniyor...';
    } else {
        button.disabled = false;
        button.textContent = button.id === 'loginBtn' ? 'Giriş Yap' : 'Kayıt Ol';
    }
}

function saveAuthData(token, userId) {
    localStorage.setItem('authToken', token);
    localStorage.setItem('userId', userId);
}

function getAuthToken() {
    return localStorage.getItem('authToken');
}

function isAuthenticated() {
    return !!getAuthToken();
}

function logout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    window.location.href = '/';
}

if (document.getElementById('loginForm')) {
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        if (!email || !password) {
            showAlert('Lütfen tüm alanları doldurunuz.');
            return;
        }
        
        setLoading('loginBtn', true);
        
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: email,
                    sifre: password
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                saveAuthData(data.token, data.user_id);
                showAlert('Giriş başarılı! Yönlendiriliyorsunuz...', 'success');
                setTimeout(() => {
                    window.location.href = '/specialty';
                }, 1500);
            } else {
                showAlert(data.detail || 'Giriş başarısız!');
            }
        } catch (error) {
            console.error('Login error:', error);
            showAlert('Bir hata oluştu. Lütfen tekrar deneyiniz.');
        } finally {
            setLoading('loginBtn', false);
        }
    });
}

if (document.getElementById('registerForm')) {
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const ad = document.getElementById('ad').value;
        const soyad = document.getElementById('soyad').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        if (!ad || !soyad || !email || !password) {
            showAlert('Lütfen tüm alanları doldurunuz.');
            return;
        }
        
        if (password.length < 6) {
            showAlert('Şifre en az 6 karakter olmalıdır.');
            return;
        }
        
        setLoading('registerBtn', true);
        
        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ad: ad,
                    soyad: soyad,
                    email: email,
                    sifre: password
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                saveAuthData(data.token, data.user_id);
                showAlert('Kayıt başarılı! Yönlendiriliyorsunuz...', 'success');
                setTimeout(() => {
                    window.location.href = '/specialty';
                }, 1500);
            } else {
                showAlert(data.detail || 'Kayıt başarısız!');
            }
        } catch (error) {
            console.error('Register error:', error);
            showAlert('Bir hata oluştu. Lütfen tekrar deneyiniz.');
        } finally {
            setLoading('registerBtn', false);
        }
    });
}

function checkAuth() {
    const protectedPages = ['/specialty', '/patients', '/ai-assistant'];
    const currentPath = window.location.pathname;
    
    if (protectedPages.includes(currentPath) && !isAuthenticated()) {
        window.location.href = '/login';
        return false;
    }
    
    return true;
}

function autoRedirect() {
    const authPages = ['/login', '/register'];
    const currentPath = window.location.pathname;
    
    if (authPages.includes(currentPath) && isAuthenticated()) {
        window.location.href = '/specialty';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    autoRedirect();
    checkAuth();
    
    // Google ile giriş butonu işlevselliği
    const googleLoginBtn = document.getElementById('googleLoginBtn');
    if (googleLoginBtn) {
        console.log("Google login button found");
        
        googleLoginBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("Google login button clicked");
            showAlert("Google ile giriş başlatılıyor...", "info");
            
            // Doğrudan URL'ye git (fetch kullanmadan)
            window.location.href = '/api/auth/google/url';
        });
    }
}); 