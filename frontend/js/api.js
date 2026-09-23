/**
 * API Client tập trung cho Hệ Thống Điểm Danh AI - THPT Điều Cải
 * Tự động nhận diện môi trường (Port 8000 hay độc lập qua CORS / Live Server)
 */

export const API_BASE = (window.location.protocol === 'file:' || (!window.location.origin.includes(':8000') && !window.location.origin.includes(':80')))
    ? 'http://localhost:8000'
    : '';

/**
 * Hàm gửi request chuẩn hóa
 */
/**
 * Hàm gửi request chuẩn hóa
 */
function redirectToLogin() {
    const path = window.location.pathname || '';
    if (path.includes('login') || path.includes('forgot-password') || path.includes('reset-password')) {
        return;
    }
    if (window._isRedirectingToLogin) return;
    window._isRedirectingToLogin = true;

    try {
        localStorage.removeItem('authToken');
        localStorage.removeItem('currentUser');
        localStorage.removeItem('currentUserRole');
    } catch (e) {}

    const filename = path.split('/').pop() || 'index.html';
    const redirectUrl = (filename && filename !== 'login.html') 
        ? `login.html?redirect=${encodeURIComponent(filename + window.location.search)}` 
        : 'login.html';
    window.location.href = redirectUrl;
}

async function fetchAPI(endpoint, options = {}) {
    const { skipAuthRedirect, ...fetchOptions } = options;
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const defaultHeaders = {
        'Accept': 'application/json',
    };

    // Tự động đính kèm Bearer Token dự phòng cho cookie Lax/cross-port
    try {
        const storedToken = localStorage.getItem('authToken');
        if (storedToken) {
            defaultHeaders['Authorization'] = `Bearer ${storedToken}`;
        }
    } catch (e) {}

    if (fetchOptions.body && typeof fetchOptions.body === 'object' && !(fetchOptions.body instanceof FormData)) {
        defaultHeaders['Content-Type'] = 'application/json';
        fetchOptions.body = JSON.stringify(fetchOptions.body);
    }

    fetchOptions.credentials = 'include';
    fetchOptions.headers = {
        ...defaultHeaders,
        ...(fetchOptions.headers || {})
    };

    try {
        const response = await fetch(url, fetchOptions);
        if (response.status === 401 && !skipAuthRedirect) {
            redirectToLogin();
        }
        if (!response.ok) {
            let errorMsg = `Lỗi máy chủ (${response.status})`;
            try {
                const errData = await response.json();
                if (errData.detail) errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
            } catch (e) {}
            const err = new Error(errorMsg);
            err.status = response.status;
            throw err;
        }
        const text = await response.text();
        return text ? JSON.parse(text) : {};
    } catch (err) {
        console.error(`[API Error] ${endpoint}:`, err);
        throw err;
    }
}

export const AuthAPI = {
    login: async (data) => {
        const res = await fetchAPI('/api/auth/login', { method: 'POST', body: data, skipAuthRedirect: true });
        if (res && res.token) {
            try { localStorage.setItem('authToken', res.token); } catch (e) {}
        }
        if (res && res.user) {
            try {
                localStorage.setItem('currentUserRole', res.user.role || 'staff');
                localStorage.setItem('currentUser', JSON.stringify(res.user));
            } catch (e) {}
        }
        return res;
    },
    logout: async () => {
        try {
            return await fetchAPI('/api/auth/logout', { method: 'POST', skipAuthRedirect: true });
        } finally {
            try {
                localStorage.removeItem('authToken');
                localStorage.removeItem('currentUser');
                localStorage.removeItem('currentUserRole');
            } catch (e) {}
        }
    },
    me: () => fetchAPI('/api/auth/me', { skipAuthRedirect: true }),
    forgotPassword: (email) => fetchAPI('/api/auth/forgot-password', { method: 'POST', body: { email }, skipAuthRedirect: true }),
    resetPassword: (data) => fetchAPI('/api/auth/reset-password', { method: 'POST', body: data, skipAuthRedirect: true }),
    listUsers: () => fetchAPI('/api/auth/users'),
    createUser: (data) => fetchAPI('/api/auth/users', { method: 'POST', body: data }),
    updateUser: (id, data) => fetchAPI(`/api/auth/users/${id}`, { method: 'PUT', body: data }),
    setUserStatus: (id, is_active) => fetchAPI(`/api/auth/users/${id}/status`, { method: 'PATCH', body: { is_active } })
};

// === ATTENDANCE APIs ===
export const AttendanceAPI = {
    getLatest: () => fetchAPI('/api/attendance/latest'),
    getTodaySessions: () => fetchAPI('/api/attendance/today-sessions'),
    get7DaysTrend: () => fetchAPI('/api/attendance/trend-7days'),
    triggerScan: () => fetchAPI('/api/attendance/trigger', { method: 'POST' }),
    getHistory: (limit = 150) => fetchAPI(`/api/attendance/history?limit=${limit}`),
    clearHistory: () => fetchAPI('/api/attendance/clear-history', { method: 'DELETE' }),
    getDownloadExcelUrl: () => `${API_BASE}/api/attendance/download-excel`
};

// === CAMERA APIs ===
export const CameraAPI = {
    getAll: () => fetchAPI('/api/cameras'),
    create: (data) => fetchAPI('/api/cameras', { method: 'POST', body: data }),
    update: (id, data) => fetchAPI(`/api/cameras/${id}`, { method: 'PUT', body: data }),
    delete: (id) => fetchAPI(`/api/cameras/${id}`, { method: 'DELETE' }),
    getWebcams: (refresh = false) => fetchAPI(`/api/cameras/available-webcams?refresh=${refresh}`),
    testConnection: (sourceUrl, triggerSignal = false, relayIp = "") => fetchAPI('/api/cameras/test-connection', {
        method: 'POST',
        body: { source_url: sourceUrl, trigger_signal: triggerSignal, relay_ip: relayIp }
    }),
    testIRByUrl: (sourceUrl, relayIp = "") => fetchAPI('/api/cameras/test-ir-by-url', {
        method: 'POST',
        body: { source_url: sourceUrl, relay_ip: relayIp }
    }),
    testClassroomIR: (classroomId, durationSeconds = 4, mode = "IR_ON") => fetchAPI(`/api/cameras/${classroomId}/test-ir`, {
        method: 'POST',
        body: { duration_seconds: durationSeconds, mode: mode }
    }),
    testAllIR: (durationSeconds = 3) => fetchAPI('/api/cameras/test-all-ir', {
        method: 'POST',
        body: { duration_seconds: durationSeconds, mode: "IR_ON" }
    }),
    resetDefaults: () => fetchAPI('/api/cameras/reset-defaults', { method: 'POST' }),
    probeNVR: (data) => fetchAPI('/api/cameras/nvr/probe', { method: 'POST', body: data }),
    batchImportNVR: (data) => fetchAPI('/api/cameras/nvr/batch-import', { method: 'POST', body: data }),
    getMatrixWall: () => fetchAPI('/api/cameras/matrix-wall'),
    listNVRs: () => fetchAPI('/api/cameras/nvr/list'),
    deleteNVR: (id, deleteCameras = false) => fetchAPI(`/api/cameras/nvr/${id}?delete_cameras=${deleteCameras}`, { method: 'DELETE' })
};

// === ROI APIs ===
export const ROIAPI = {
    getROI: (classroomId, refresh = false) => fetchAPI(`/api/roi/${classroomId}?refresh=${refresh}`),
    refreshSnapshot: (classroomId) => fetchAPI(`/api/roi/${classroomId}/refresh-snapshot`, { method: 'POST' }),
    saveROI: (classroomId, data) => fetchAPI(`/api/roi/${classroomId}`, { method: 'POST', body: data })
};

// === REPORTS & NOTIFICATIONS APIs ===
export const ReportAPI = {
    list: () => fetchAPI('/api/reports/list'),
    getList: () => fetchAPI('/api/reports/list'),
    exportExcel: () => fetchAPI('/api/reports/export-now', { method: 'POST' }),
    exportNow: () => fetchAPI('/api/reports/export-now', { method: 'POST' }),
    sendEmail: (email) => fetchAPI('/api/reports/send-email', { method: 'POST', body: { email } }),
    saveEmailConfig: (data) => fetchAPI('/api/reports/save-email-config', { method: 'POST', body: data }),
    getDistributionStatus: () => fetchAPI('/api/reports/distribution-status'),
    sendZalo: (data) => fetchAPI('/api/reports/send-zalo', { method: 'POST', body: data }),
    getZaloStatus: () => fetchAPI('/api/reports/zalo-status'),
    getZaloConfig: () => fetchAPI('/api/reports/zalo-config'),
    saveZaloConfig: (data) => fetchAPI('/api/reports/save-zalo-config', { method: 'POST', body: data }),
    getNotificationSettings: () => fetchAPI('/api/reports/notification-settings'),
    getLatestSummary: () => fetchAPI('/api/reports/latest-summary'),
    saveNotificationSettings: (data) => fetchAPI('/api/reports/notification-settings', { method: 'POST', body: data }),
    getRetentionSettings: () => fetchAPI('/api/reports/retention-settings'),
    saveRetentionSettings: (data) => fetchAPI('/api/reports/retention-settings', { method: 'POST', body: data }),
    cleanupExpired: (days) => fetchAPI('/api/reports/cleanup-expired', { method: 'POST', body: { days } })
};

// === SYSTEM APIs ===
export const SystemAPI = {
    getDbInfo: () => fetchAPI('/api/database/info'),
    getDatabaseInfo: () => fetchAPI('/api/database/info'),
    getHealth: () => fetchAPI('/api/health')
};

// Chuẩn hóa URL cho ảnh tĩnh
export function getMediaUrl(path) {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    return `${API_BASE}${path}`;
}

// Hiển thị Toast thông báo đẹp mắt
export function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '99999';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '10px';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgColors = {
        success: '#10b981',
        danger: '#ef4444',
        warning: '#f59e0b',
        info: '#2563eb'
    };
    const icons = {
        success: 'fa-check-circle',
        danger: 'fa-circle-exclamation',
        warning: 'fa-triangle-exclamation',
        info: 'fa-circle-info'
    };

    toast.style.background = bgColors[type] || bgColors.info;
    toast.style.color = '#ffffff';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '8px';
    toast.style.fontSize = '0.9rem';
    toast.style.fontWeight = '600';
    toast.style.boxShadow = '0 10px 15px -3px rgba(0,0,0,0.2)';
    toast.style.display = 'flex';
    toast.style.alignItems = 'center';
    toast.style.gap = '10px';
    toast.style.transition = 'all 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';

    toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 10);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// === BACKUP & RESTORE APIs ===
export const BackupAPI = {
    list: () => fetchAPI('/api/backup/list'),
    create: (data = {}) => fetchAPI('/api/backup/create', { method: 'POST', body: data }),
    restore: (filename) => fetchAPI(`/api/backup/restore/${encodeURIComponent(filename)}`, { method: 'POST' }),
    delete: (filename) => fetchAPI(`/api/backup/${encodeURIComponent(filename)}`, { method: 'DELETE' }),
    getDownloadUrl: (filename) => `${API_BASE}/api/backup/download/${encodeURIComponent(filename)}`,
    uploadAndRestore: async (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return fetchAPI('/api/backup/upload-restore', {
            method: 'POST',
            body: formData
        });
    }
};

// Luôn gắn các API lên window để đảm bảo tương thích toàn diện kể cả khi có cache cũ
if (typeof window !== 'undefined') {
    window.API_BASE = API_BASE;
    window.CameraAPI = CameraAPI;
    window.AttendanceAPI = AttendanceAPI;
    window.ROIAPI = ROIAPI;
    window.AuthAPI = AuthAPI;
    window.ReportAPI = ReportAPI;
    window.BackupAPI = BackupAPI;
    window.SystemAPI = SystemAPI;
    window.showToast = showToast;
    window.getMediaUrl = getMediaUrl;
}

