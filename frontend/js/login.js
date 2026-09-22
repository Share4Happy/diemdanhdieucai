import { AuthAPI, showToast } from './api.js';

function showAlert(el, message, type) {
    if (!el) return;
    el.textContent = message;
    el.className = `auth-alert visible ${type}`;
}

function getRedirectTarget() {
    try {
        const params = new URLSearchParams(window.location.search);
        const redirect = params.get('redirect');
        if (redirect) {
            const decoded = decodeURIComponent(redirect);
            if (!decoded.includes('login') && !decoded.includes('forgot') && !decoded.includes('reset')) {
                return decoded;
            }
        }
    } catch (e) {}
    return 'index.html';
}

async function tryRedirectIfLoggedIn() {
    try {
        await AuthAPI.me();
        window.location.href = getRedirectTarget();
    } catch (e) {
        /* chưa đăng nhập */
    }
}

function bindLogin() {
    const form = document.getElementById('loginForm');
    const alertEl = document.getElementById('authAlert');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email')?.value.trim();
        const password = document.getElementById('password')?.value;
        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true;
        try {
            await AuthAPI.login({ email, password });
            window.location.href = getRedirectTarget();
        } catch (err) {
            showAlert(alertEl, err.message || 'Đăng nhập thất bại', 'error');
        } finally {
            btn.disabled = false;
        }
    });
}

function bindForgot() {
    const form = document.getElementById('forgotForm');
    const alertEl = document.getElementById('authAlert');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email')?.value.trim();
        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true;
        try {
            const res = await AuthAPI.forgotPassword(email);
            showAlert(alertEl, res.message || 'Nếu email tồn tại, hướng dẫn đã được gửi.', 'success');
            showToast(res.message, 'success');
        } catch (err) {
            showAlert(alertEl, err.message || 'Không gửi được yêu cầu', 'error');
        } finally {
            btn.disabled = false;
        }
    });
}

function bindReset() {
    const form = document.getElementById('resetForm');
    const alertEl = document.getElementById('authAlert');
    if (!form) return;
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token') || '';
    if (!token) {
        showAlert(alertEl, 'Thiếu mã đặt lại mật khẩu. Hãy dùng liên kết trong email.', 'error');
    }
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const password = document.getElementById('password')?.value;
        const confirm = document.getElementById('confirmPassword')?.value;
        if (password !== confirm) {
            showAlert(alertEl, 'Mật khẩu xác nhận không khớp.', 'error');
            return;
        }
        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true;
        try {
            const res = await AuthAPI.resetPassword({ token, password });
            showAlert(alertEl, res.message, 'success');
            setTimeout(() => { window.location.href = 'login.html'; }, 1200);
        } catch (err) {
            showAlert(alertEl, err.message || 'Không đặt lại được mật khẩu', 'error');
        } finally {
            btn.disabled = false;
        }
    });
}

tryRedirectIfLoggedIn();
bindLogin();
bindForgot();
bindReset();
