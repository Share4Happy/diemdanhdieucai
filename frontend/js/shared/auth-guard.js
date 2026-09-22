import { AuthAPI, showToast } from '../api.js';

function isPublicAuthPage() {
    const path = window.location.pathname || '';
    return path.includes('login') || path.includes('forgot-password') || path.includes('reset-password');
}

function updateAdminNav(isAdmin) {
    document.querySelectorAll('.nav-admin-only').forEach((el) => {
        el.hidden = !isAdmin;
        if (isAdmin) {
            el.classList.add('is-visible');
        } else {
            el.classList.remove('is-visible');
        }
    });
}

// 1. Phục hồi ngay thông tin tài khoản và quyền từ localStorage để hiển thị tức thời, triệt tiêu FOUC/nhấp nháy
try {
    const cachedRole = localStorage.getItem('currentUserRole');
    if (cachedRole) {
        updateAdminNav(cachedRole === 'admin');
    }
    const cachedUserStr = localStorage.getItem('currentUser');
    if (cachedUserStr) {
        window.currentUser = JSON.parse(cachedUserStr);
    }
} catch (e) {}

async function guardApp() {
    // Nếu đang ở trang public (login, forgot, reset), không cần guard
    if (isPublicAuthPage()) {
        return;
    }

    try {
        // Xác thực phiên làm việc thực tế với backend
        const user = await AuthAPI.me();

        window.currentUser = user;
        try {
            localStorage.setItem('currentUserRole', user.role || 'staff');
            localStorage.setItem('currentUser', JSON.stringify(user));
        } catch (e) {}

        // Cập nhật thông tin tài khoản trên sidebar navigation
        try {
            if (window.appShell && typeof window.appShell.displayUserInfo === 'function') {
                window.appShell.displayUserInfo();
            }
        } catch (e) {
            console.warn('[Auth Guard] Lỗi cập nhật giao diện người dùng:', e);
        }

        if (user.role === 'admin') {
            updateAdminNav(true);
        } else {
            updateAdminNav(false);
            if ((window.location.pathname || '').includes('users')) {
                showToast('Chỉ quản trị viên mới vào được trang Tài Khoản.', 'danger');
                window.location.href = 'index.html';
            }
        }
    } catch (err) {
        console.warn('[Auth Guard] Lỗi khi kiểm tra phiên làm việc:', err);
        
        // CHỈ chuyển hướng về login nếu server phản hồi mã 401 Unauthorized (phiên hết hạn thực sự)
        // Tuyệt đối không chuyển hướng khi gặp lỗi mạng tạm thời, lỗi 500, hay huỷ request do chuyển trang
        if (err && err.status === 401) {
            console.log('[Auth Guard] Phiên làm việc không hợp lệ (401), điều hướng về login');
            try {
                localStorage.removeItem('authToken');
                localStorage.removeItem('currentUserRole');
                localStorage.removeItem('currentUser');
            } catch (e) {}

            const path = window.location.pathname || '';
            const filename = path.split('/').pop() || 'index.html';
            const redirectUrl = (filename && filename !== 'login.html') 
                ? `login.html?redirect=${encodeURIComponent(filename + window.location.search)}` 
                : 'login.html';
            window.location.href = redirectUrl;
        } else {
            // Lỗi mạng hoặc server bận: Nếu đã có thông tin cached trước đó, giữ nguyên trạng thái
            console.warn('[Auth Guard] Bỏ qua lỗi kết nối mạng/máy chủ bận, duy trì giao diện hiện tại.');
        }
    }
}

guardApp();


