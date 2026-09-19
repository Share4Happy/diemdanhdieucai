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
async function fetchAPI(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const defaultHeaders = {
        'Accept': 'application/json',
    };

    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
        defaultHeaders['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
    }

    options.headers = {
        ...defaultHeaders,
        ...(options.headers || {})
    };

    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            let errorMsg = `Lỗi máy chủ (${response.status})`;
            try {
                const errData = await response.json();
                if (errData.detail) errorMsg = errData.detail;
            } catch (e) {}
            throw new Error(errorMsg);
        }
        return await response.json();
    } catch (err) {
        console.error(`[API Error] ${endpoint}:`, err);
        throw err;
    }
}

// === ATTENDANCE APIs ===
export const AttendanceAPI = {
    getLatest: () => fetchAPI('/api/attendance/latest'),
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
    getAvailableWebcams: (refresh = false) => fetchAPI(`/api/cameras/available-webcams?refresh=${refresh}`),
    testConnection: (sourceUrl) => fetchAPI('/api/cameras/test-connection', { method: 'POST', body: { source_url: sourceUrl } }),
    resetDefaults: () => fetchAPI('/api/cameras/reset-defaults', { method: 'POST' })
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
    getDistributionStatus: () => fetchAPI('/api/reports/distribution-status'),
    sendZalo: (data) => fetchAPI('/api/reports/send-zalo', { method: 'POST', body: data }),
    getZaloStatus: () => fetchAPI('/api/reports/zalo-status'),
    saveZaloConfig: (data) => fetchAPI('/api/reports/save-zalo-config', { method: 'POST', body: data })
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

// Luôn gắn các API lên window để đảm bảo tương thích toàn diện kể cả khi có cache cũ
if (typeof window !== 'undefined') {
    window.API_BASE = API_BASE;
    window.CameraAPI = CameraAPI;
    window.AttendanceAPI = AttendanceAPI;
    window.ROIAPI = ROIAPI;
    window.ReportAPI = ReportAPI;
    window.SystemAPI = SystemAPI;
    window.showToast = showToast;
    window.getMediaUrl = getMediaUrl;
}

