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

function cleanEmailInput(val) {
    if (!val) return '';
    return val.replace(/\s+/g, '').toLowerCase();
}

function bindLogin() {
    const form = document.getElementById('loginForm');
    const alertEl = document.getElementById('authAlert');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    if (!form) return;

    // Tự động làm sạch khoảng trắng khi người dùng gõ hoặc dán email
    if (emailInput) {
        const handleEmailClean = () => {
            const cleaned = cleanEmailInput(emailInput.value);
            if (emailInput.value !== cleaned) {
                const cursorPos = emailInput.selectionStart;
                emailInput.value = cleaned;
                try { emailInput.setSelectionRange(cursorPos, cursorPos); } catch (e) {}
            }
        };
        emailInput.addEventListener('input', handleEmailClean);
        emailInput.addEventListener('blur', handleEmailClean);
        emailInput.addEventListener('paste', () => setTimeout(handleEmailClean, 10));
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = cleanEmailInput(emailInput?.value || '');
        const password = (passwordInput?.value || '').trim();

        if (emailInput) emailInput.value = email;
        if (passwordInput) passwordInput.value = password;

        if (!email) {
            showAlert(alertEl, 'Vui lòng nhập địa chỉ email.', 'error');
            emailInput?.focus();
            return;
        }
        if (!password) {
            showAlert(alertEl, 'Vui lòng nhập mật khẩu.', 'error');
            passwordInput?.focus();
            return;
        }

        const btn = form.querySelector('button[type="submit"]');
        const origBtnContent = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Đang đăng nhập...</span>';
        }

        try {
            await AuthAPI.login({ email, password });
            window.location.href = getRedirectTarget();
        } catch (err) {
            showAlert(alertEl, err.message || 'Email hoặc mật khẩu không chính xác', 'error');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = origBtnContent;
            }
        }
    });
}

function bindForgot() {
    const form = document.getElementById('forgotForm');
    const alertEl = document.getElementById('authAlert');
    const emailInput = document.getElementById('email');
    if (!form) return;

    if (emailInput) {
        const handleEmailClean = () => {
            emailInput.value = cleanEmailInput(emailInput.value);
        };
        emailInput.addEventListener('blur', handleEmailClean);
        emailInput.addEventListener('paste', () => setTimeout(handleEmailClean, 10));
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = cleanEmailInput(emailInput?.value || '');
        if (emailInput) emailInput.value = email;

        if (!email) {
            showAlert(alertEl, 'Vui lòng nhập email hợp lệ.', 'error');
            return;
        }

        const btn = form.querySelector('button[type="submit"]');
        const origBtnContent = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Đang gửi...</span>';
        }

        try {
            const res = await AuthAPI.forgotPassword(email);
            showAlert(alertEl, res.message || 'Nếu email tồn tại, hướng dẫn đã được gửi.', 'success');
            showToast(res.message, 'success');
        } catch (err) {
            showAlert(alertEl, err.message || 'Không gửi được yêu cầu', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = origBtnContent;
            }
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
