import { AuthAPI, showToast } from '../api.js';

function isPublicAuthPage() {
    const path = window.location.pathname || '';
    return path.includes('login') || path.includes('forgot-password') || path.includes('reset-password');
}

function showAdminNav() {
    document.querySelectorAll('.nav-admin-only').forEach((el) => {
        el.hidden = false;
        el.classList.add('is-visible');
    });
}

async function guardApp() {
    // Nếu đang ở trang public (login, forgot, reset), không cần guard
    if (isPublicAuthPage()) {
        console.log('[Auth Guard] Trang công khai, bỏ qua kiểm tra');
        return;
    }

    try {
        console.log('[Auth Guard] Kiểm tra đăng nhập...');
        const user = await AuthAPI.me();
        console.log('[Auth Guard] Đã đăng nhập:', user.email);

        window.currentUser = user;

        // Cập nhật thông tin tài khoản trên sidebar navigation
        if (window.appShell && typeof window.appShell.displayUserInfo === 'function') {
            window.appShell.displayUserInfo();
        }

        if (user.role === 'admin') {
            showAdminNav();
        } else if ((window.location.pathname || '').includes('users')) {
            showToast('Chỉ quản trị viên mới vào được trang Tài Khoản.', 'danger');
            window.location.href = 'index.html';
        }
    } catch (err) {
        console.log('[Auth Guard] Chưa đăng nhập, redirect về login');
        console.error('[Auth Guard] Error:', err);
        window.location.href = 'login.html';
    }
}

guardApp();
