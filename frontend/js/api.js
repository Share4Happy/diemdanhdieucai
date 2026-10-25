/**
 * API Client tập trung cho Hệ Thống Điểm Danh AI - THPT Điều Cải
 * Tự động nhận diện môi trường (Port 8000 hay độc lập qua CORS / Live Server)
 */

export const API_BASE = (function () {
    if (typeof window === 'undefined') return '';
    if (window.location.protocol === 'file:') return 'http://localhost:8000';
    if (window.location.port && ['5500', '5501', '5502', '3001'].includes(window.location.port)) {
        return `http://${window.location.hostname || 'localhost'}:8000`;
    }
    return '';
})();

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
        localStorage.removeItem('currentUser');
        localStorage.removeItem('currentUserRole');
    } catch (e) { }

    const filename = path.split('/').pop() || 'index.html';
    const redirectUrl = (filename && filename !== 'login.html')
        ? `login.html?redirect=${encodeURIComponent(filename + window.location.search)}`
        : 'login.html';
    window.location.href = redirectUrl;
}

async function fetchAPI(endpoint, options = {}) {
    const { skipAuthRedirect, suppressAuthRedirect = false, ...fetchOptions } = options;
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const defaultHeaders = {
        'Accept': 'application/json',
    };

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
        // Poll nền (suppressAuthRedirect=true) được phép bỏ qua 401 để không đá người dùng
        // đang xem dashboard sang login giữa chừng; chỉ auth-guard / thao tác chủ động mới redirect.
        if (response.status === 401 && !skipAuthRedirect && !suppressAuthRedirect) {
            redirectToLogin();
        }
        if (!response.ok) {
            let errorMsg = `Lỗi máy chủ (${response.status})`;
            if (response.status === 413) {
                errorMsg = 'Tệp tin tải lên quá lớn (Vượt quá dung lượng cho phép của máy chủ, tối đa 500MB).';
            } else if (response.status === 504) {
                errorMsg = 'Máy chủ phản hồi quá lâu (Gateway Timeout). Vui lòng thử lại với video ngắn hơn.';
            }
            try {
                const errData = await response.json();
                if (errData.detail) errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
            } catch (e) { }
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
        if (res && res.user) {
            try {
                localStorage.setItem('currentUserRole', res.user.role || 'staff');
                localStorage.setItem('currentUser', JSON.stringify(res.user));
            } catch (e) { }
        }
        return res;
    },
    logout: async () => {
        try {
            return await fetchAPI('/api/auth/logout', { method: 'POST', skipAuthRedirect: true });
        } finally {
            try {
                localStorage.removeItem('currentUser');
                localStorage.removeItem('currentUserRole');
            } catch (e) { }
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
    getLatest: (options = {}) => fetchAPI('/api/attendance/latest', options),
    getLatestSession: (options = {}) => fetchAPI('/api/attendance/latest', options),
    getTodaySessions: (options = {}) => fetchAPI('/api/attendance/today-sessions', options),
    get7DaysTrend: (options = {}) => fetchAPI('/api/attendance/trend-7days', options),
    triggerScan: () => fetchAPI('/api/attendance/trigger', { method: 'POST' }),
    getProgress: () => fetchAPI('/api/attendance/progress', { suppressAuthRedirect: true }),
    getHistory: (limit = 150) => fetchAPI(`/api/attendance/history?limit=${limit}`),
    clearHistory: () => fetchAPI('/api/attendance/clear-history', { method: 'DELETE' }),
    overrideDetail: (detailId, data) => fetchAPI(`/api/attendance/details/${detailId}/override`, { method: 'PUT', body: data }),
    getSessionById: (sessionId) => fetchAPI(`/api/attendance/sessions/${sessionId}`),
    rescanSingle: (classroomId) => fetchAPI(`/api/attendance/classrooms/${classroomId}/rescan`, { method: 'POST' }),
    getDownloadExcelUrl: () => `${API_BASE}/api/attendance/download-excel`
};

// === CAMERA APIs ===
export const CameraAPI = {
    getAll: () => fetchAPI('/api/cameras'),
    getRawRtsp: (id) => fetchAPI(`/api/cameras/${id}/raw`),
    create: (data) => fetchAPI('/api/cameras', { method: 'POST', body: data }),
    update: (id, data) => fetchAPI(`/api/cameras/${id}`, { method: 'PUT', body: data }),
    delete: (id) => fetchAPI(`/api/cameras/${id}`, { method: 'DELETE' }),
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
    getNVRChannels: (nvrId = null) => fetchAPI(`/api/cameras/nvr/channels${nvrId ? `?nvr_id=${nvrId}` : ''}`),
    getSourceStatus: (folder = '') => fetchAPI(`/api/cameras/source-status${folder ? `?folder=${encodeURIComponent(folder)}` : ''}`),
    inspectFolder: (folderPath) => fetchAPI('/api/cameras/inspect-folder', { method: 'POST', body: { folder_path: folderPath } }),
    switchSourceMode: (data) => fetchAPI('/api/cameras/switch-source-mode', { method: 'POST', body: data }),
    cleanupTestImages: (folder = 'camera') => fetchAPI(`/api/cameras/cleanup-test-images?folder=${encodeURIComponent(folder)}`, { method: 'POST' }),
    refreshAllSnapshots: () => fetchAPI('/api/cameras/refresh-all-snapshots', { method: 'POST' }),
    refreshClassroomSnapshot: (id) => fetchAPI(`/api/cameras/${id}/refresh-snapshot`, { method: 'POST' }),
    getProgress: () => fetchAPI('/api/cameras/progress', { suppressAuthRedirect: true }),
    getAutoSchedule: () => fetchAPI('/api/cameras/auto-schedule'),
    saveAutoSchedule: (data) => fetchAPI('/api/cameras/auto-schedule', { method: 'POST', body: data }),
    triggerAutoSchedule: () => fetchAPI('/api/cameras/auto-schedule/trigger', { method: 'POST' }),
    getStreamProfiles: () => fetchAPI('/api/cameras/stream-profiles'),
    switchCameraStream: (id, streamType) => fetchAPI(`/api/cameras/${id}/switch-stream`, {
        method: 'POST',
        body: { stream_type: streamType }
    }),
    batchSwitchStream: (streamType, classroomIds = null) => fetchAPI('/api/cameras/batch-switch-stream', {
        method: 'POST',
        body: { stream_type: streamType, classroom_ids: classroomIds }
    }),
    compareStreams: (id) => fetchAPI(`/api/cameras/${id}/compare-streams`),
    simulateCaptureTest: (data = {}) => fetchAPI('/api/cameras/simulate-capture-test', { method: 'POST', body: data }),
    getStreamPolicy: () => fetchAPI('/api/cameras/stream-policy'),
    updateStreamPolicy: (data) => fetchAPI('/api/cameras/stream-policy', { method: 'POST', body: data })
};

// === ROI APIs ===
export const ROIAPI = {
    getROI: (classroomId, refresh = false) => fetchAPI(`/api/roi/${classroomId}?refresh=${refresh}`),
    refreshSnapshot: (classroomId) => fetchAPI(`/api/roi/${classroomId}/refresh-snapshot`, { method: 'POST' }),
    saveROI: (classroomId, data) => fetchAPI(`/api/roi/${classroomId}`, { method: 'POST', body: data }),
    applyAll: (data) => fetchAPI('/api/roi/apply-all', { method: 'POST', body: data })
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
    getDatabaseInfo: () => fetchAPI('/api/database/info'),
    getHealth: () => fetchAPI('/api/health'),
    getAiInfo: () => fetchAPI('/api/system/ai/info'),
    getSampleFrames: () => fetchAPI('/api/system/sample-frames'),
    getSamplePreviewUrl: (path) => `${API_BASE}/api/system/sample-frame-preview?path=${encodeURIComponent(path)}`,
    getClassroomsRoi: () => fetchAPI('/api/system/classrooms-roi'),
    testRawAI: (formData) => fetchAPI('/api/system/test-raw-ai', { method: 'POST', body: formData }),
    getAiEndpoint: () => fetchAPI('/api/system/ai-endpoint'),
    pingAiEndpoint: (apiUrl) => fetchAPI('/api/system/ai-ping', {
        method: 'POST',
        body: typeof apiUrl === 'string' ? { api_url: apiUrl } : (apiUrl || {})
    }),
    updateAiEndpoint: (payloadOrUrl) => fetchAPI('/api/system/ai-endpoint', {
        method: 'POST',
        body: typeof payloadOrUrl === 'string' ? { api_url: payloadOrUrl } : payloadOrUrl
    }),
    saveBatchTest: (batchData) => fetchAPI('/api/system/test-batches/save', { method: 'POST', body: batchData }),
    listBatchTests: () => fetchAPI('/api/system/test-batches'),
    getBatchTest: (batchId) => fetchAPI(`/api/system/test-batches/${batchId}`),
    getBatchZipUrl: (batchId) => `${API_BASE}/api/system/test-batches/${batchId}/export-zip`,
    getBatchExcelUrl: (batchId) => `${API_BASE}/api/system/test-batches/${batchId}/export-excel`,
    getBatchImageUrl: (batchId, type, filename) => `${API_BASE}/api/system/test-batches/${batchId}/image/${type}/${filename}`
};

export const PredictAPI = {
    predict: (formData, endpoint = '/api/predict') => fetchAPI(endpoint, { method: 'POST', body: formData, skipAuthRedirect: true })
};


// Chuẩn hóa URL cho ảnh tĩnh
export function getMediaUrl(path) {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    return `${API_BASE}${path}`;
}

// Kiểm tra xem người dùng hiện tại có phải quản trị viên không
function currentRole() {
    const u = window.currentUser;
    if (u && u.role) return u.role;
    try {
        return localStorage.getItem('currentUserRole') || 'staff';
    } catch (e) {
        return 'staff';
    }
}

export function isAdmin() {
    return currentRole() === 'admin';
}

// Escape nội dung chèn vào HTML an toàn (chống stored/reflected XSS)
export function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
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

    toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span></span>`;
    toast.querySelector('span').textContent = String(message ?? '');
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
    },
    gdriveStatus: () => fetchAPI('/api/backup/gdrive/status'),
    gdriveAuthUrl: (redirectUri = '') => {
        const q = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : '';
        return fetchAPI(`/api/backup/gdrive/auth-url${q}`);
    },
    gdriveConnect: (code, redirectUri = '') => fetchAPI('/api/backup/gdrive/connect', {
        method: 'POST',
        body: { code, redirect_uri: redirectUri }
    }),
    gdriveDisconnect: () => fetchAPI('/api/backup/gdrive/disconnect', { method: 'POST' })
};

// === CLASSROOMS MANAGEMENT APIs ===
export const ClassroomsAPI = {
    getAll: (params = {}) => {
        const query = new URLSearchParams();
        if (params.search) query.append('search', params.search);
        if (params.grade) query.append('grade', params.grade);
        if (params.has_camera !== undefined && params.has_camera !== null) {
            query.append('has_camera', params.has_camera);
        }
        const qs = query.toString() ? `?${query.toString()}` : '';
        return fetchAPI(`/api/classrooms${qs}`);
    },
    getDetail: (id) => fetchAPI(`/api/classrooms/${id}`),
    create: (data) => fetchAPI('/api/classrooms', { method: 'POST', body: data }),
    update: (id, data) => fetchAPI(`/api/classrooms/${id}`, { method: 'PUT', body: data }),
    quickUpdateCount: (id, count) => fetchAPI(`/api/classrooms/${id}/count`, {
        method: 'PATCH',
        body: { standard_count: count }
    }),
    delete: (id) => fetchAPI(`/api/classrooms/${id}`, { method: 'DELETE' }),
    getAvailableCameras: () => fetchAPI('/api/classrooms/available-cameras'),
    importPreview: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return fetchAPI('/api/classrooms/import-preview', {
            method: 'POST',
            body: formData
        });
    },
    batchImport: (data) => fetchAPI('/api/classrooms/batch-import', {
        method: 'POST',
        body: data
    }),
    getTemplateUrl: (format = 'xlsx') => `${API_BASE}/api/classrooms/template?format=${format}`,
    getExportUrl: () => `${API_BASE}/api/classrooms/export`
};

// Luôn gắn các API lên window để đảm bảo tương thích toàn diện kể cả khi có cache cũ
if (typeof window !== 'undefined') {
    window.API_BASE = API_BASE;
    window.CameraAPI = CameraAPI;
    window.AttendanceAPI = AttendanceAPI;
    window.ClassroomsAPI = ClassroomsAPI;
    window.ROIAPI = ROIAPI;
    window.AuthAPI = AuthAPI;
    window.ReportAPI = ReportAPI;
    window.BackupAPI = BackupAPI;
    window.SystemAPI = SystemAPI;
    window.PredictAPI = PredictAPI;
    window.showToast = showToast;
    window.getMediaUrl = getMediaUrl;
    window.escapeHtml = escapeHtml;
}

