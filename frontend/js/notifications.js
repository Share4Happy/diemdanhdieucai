/**
 * notifications.js - Central Notifications & Distribution Controller
 * THPT Điều Cải - Attendance System (Zalo & Email)
 */
import { ReportAPI, CameraAPI, showToast, API_BASE } from './api.js';

let zaloRecipients = [];
let zaloSaveTimer = null;
let allClassrooms = [];

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadClassrooms();
    loadZaloConfig();
    loadEmailConfig();
    loadAdjustSettings();
    setupEventListeners();
});

// ===================== TABS NAVIGATION =====================
function initTabs() {
    const tabBtns = document.querySelectorAll('.tabs-nav .tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));

            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            const targetContent = document.getElementById(targetId);
            if (targetContent) targetContent.classList.add('active');
        });
    });
}

// ===================== SETUP LISTENERS =====================
function setupEventListeners() {
    // Refresh button
    const btnRefresh = document.getElementById('btnRefreshNotifications');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', () => {
            loadZaloConfig();
            loadEmailConfig();
            loadAdjustSettings();
            showToast('Đã làm mới thông tin cấu hình', 'success');
        });
    }

    const btnEmail = document.getElementById('btnSendTestEmail');
    if (btnEmail) {
        btnEmail.addEventListener('click', handleSendTestEmail);
    }

    // Save Email button
    const btnSaveEmail = document.getElementById('btnSaveEmailConfig');
    if (btnSaveEmail) {
        btnSaveEmail.addEventListener('click', handleSavePrincipalEmail);
    }

    // Open folder button
    const btnFolder = document.getElementById('btnOpenFolder');
    if (btnFolder) {
        btnFolder.addEventListener('click', () => {
            const path = document.getElementById('internalPathInput')?.value || 'storage/reports/latest/';
            alert(`Thư mục lưu trữ báo cáo bản sao: ${path}\nBạn có thể truy cập thư mục này trên máy chủ hệ thống.`);
        });
    }

    // Zalo Type Selector
    const zaloSelect = document.getElementById('zaloTypeSelect');
    if (zaloSelect) {
        zaloSelect.addEventListener('change', () => {
            toggleZaloInputs();
            scheduleZaloAutoSave();
        });
    }

    // Auto-save Zalo inputs
    ['zaloWebhookInput', 'zaloTokenInput', 'zaloUserIdInput', 'zaloBotKeyInput', 'zaloBotIdInput', 'zaloBotBaseUrlInput'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', scheduleZaloAutoSave);
    });

    // Send Test Zalo
    const btnZalo = document.getElementById('btnSendTestZalo');
    if (btnZalo) {
        btnZalo.addEventListener('click', handleSendTestZalo);
    }

    // Save Zalo button
    const btnSaveZalo = document.getElementById('btnSaveZaloConfig');
    if (btnSaveZalo) {
        btnSaveZalo.addEventListener('click', () => {
            clearTimeout(zaloSaveTimer);
            persistZaloConfig(true);
        });
    }

    // Send All Test
    const btnSendAll = document.getElementById('btnSendAllTest');
    if (btnSendAll) {
        btnSendAll.addEventListener('click', async () => {
            btnSendAll.disabled = true;
            btnSendAll.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi toàn bộ...';
            try {
                await handleSendTestZalo();
                await handleSendTestEmail();
                showToast('Đã kích hoạt gửi thử Zalo và Email!', 'success');
            } catch (err) {
                console.error(err);
            } finally {
                btnSendAll.disabled = false;
                btnSendAll.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Gửi Thử Zalo & Email';
            }
        });
    }

    // Recipient controls
    initRecipientControls();

    // Adjust notification controls
    initAdjustControls();

    // Schedule tab controls
    initScheduleControls();
}

// ===================== CLASSROOMS =====================
async function loadClassrooms() {
    try {
        const data = await CameraAPI.getAll();
        allClassrooms = data.cameras || [];
        const classSelect = document.getElementById('recipientClassSelect');
        if (classSelect) {
            classSelect.innerHTML = '<option value="">-- Chọn lớp chủ nhiệm --</option>' +
                allClassrooms.map(c => `<option value="${c.id}">${c.name} (${c.room_number || 'Phòng'})</option>`).join('');
        }
    } catch (err) {
        console.warn('Lỗi nạp danh sách lớp học:', err);
    }
}

// ===================== EMAIL CONFIG =====================
async function loadEmailConfig() {
    try {
        const data = await ReportAPI.getDistributionStatus();
        const input = document.getElementById('principalEmailInput');
        if (input && data.principal_email) {
            input.value = data.principal_email;
        }
        const badge = document.getElementById('emailStatusBadge');
        if (badge) {
            badge.className = 'status-pill';
            if (data.smtp_configured) {
                badge.style.background = '#dcfce7';
                badge.style.color = '#15803d';
                badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Sẵn sàng phân phối';
            } else {
                badge.style.background = '#fef3c7';
                badge.style.color = '#b45309';
                badge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Chờ mật khẩu SMTP';
            }
        }
    } catch (err) {
        console.error('Lỗi nạp trạng thái email:', err);
    }
}

async function handleSavePrincipalEmail() {
    const input = document.getElementById('principalEmailInput');
    const email = input?.value.trim();
    if (!email) {
        showToast('Vui lòng nhập địa chỉ email Hiệu Trưởng!', 'warning');
        return;
    }
    const btn = document.getElementById('btnSaveEmailConfig');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
    }
    try {
        const res = await ReportAPI.saveEmailConfig({ principal_email: email });
        showToast(res.message || 'Đã lưu email Hiệu Trưởng thành công!', 'success');
        if (typeof window.showSuccess === 'function') {
            window.showSuccess(res.message, 'Lưu Email Hiệu Trưởng');
        }
    } catch (err) {
        const msg = err.message || err;
        showToast('Lỗi lưu email: ' + msg, 'danger');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu Email Người Nhận';
        }
    }
}

async function handleSendTestEmail() {
    const targetEmail = document.getElementById('principalEmailInput')?.value;
    const btnEmail = document.getElementById('btnSendTestEmail');
    if (!btnEmail) return;

    btnEmail.disabled = true;
    btnEmail.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi email...';

    try {
        const result = await ReportAPI.sendEmail(targetEmail);
        showToast(result.message || 'Gửi email thành công', 'success');
        if (typeof window.showSuccess === 'function') {
            window.showSuccess(result.message, 'Gửi Email Báo Cáo');
        } else {
            alert(result.message);
        }
    } catch (err) {
        const msg = err.message || err;
        if (typeof window.showError === 'function') {
            window.showError(`Lỗi gửi email: ${msg}`, 'Lỗi Gửi Email');
        } else {
            alert('Lỗi gửi email: ' + msg);
        }
    } finally {
        btnEmail.disabled = false;
        btnEmail.innerHTML = '<i class="fa-solid fa-envelope"></i> Gửi Thử Email Báo Cáo Cho Hiệu Trưởng';
    }
}

// ===================== ZALO CONFIG =====================
async function loadZaloConfig() {
    try {
        const data = await ReportAPI.getZaloConfig();
        const cfg = data.config || {};

        const select = document.getElementById('zaloTypeSelect');
        if (select && cfg.notification_type) {
            select.value = cfg.notification_type;
        }

        const wb = document.getElementById('zaloWebhookInput');
        if (wb && cfg.webhook_url) wb.value = cfg.webhook_url;

        const tk = document.getElementById('zaloTokenInput');
        if (tk && cfg.access_token) tk.value = cfg.access_token;

        const uid = document.getElementById('zaloUserIdInput');
        if (uid && cfg.recipient_user_id) uid.value = cfg.recipient_user_id;

        const bk = document.getElementById('zaloBotKeyInput');
        if (bk && cfg.bot_api_key) bk.value = cfg.bot_api_key;

        const bi = document.getElementById('zaloBotIdInput');
        if (bi && cfg.bot_id) bi.value = cfg.bot_id;

        const bu = document.getElementById('zaloBotBaseUrlInput');
        if (bu && cfg.bot_api_base_url) bu.value = cfg.bot_api_base_url;

        let loadedRecipients = [];
        if (cfg.recipients_json) {
            try {
                loadedRecipients = JSON.parse(cfg.recipients_json);
                if (!Array.isArray(loadedRecipients)) loadedRecipients = [];
            } catch (e) {
                loadedRecipients = [];
            }
        }
        if (loadedRecipients.length === 0 && cfg.recipient_phones) {
            loadedRecipients = cfg.recipient_phones
                .split(',')
                .map(p => p.trim())
                .filter(p => p)
                .map(p => ({ role: 'school', phone: p, label: 'Ban Giám Hiệu' }));
        }
        zaloRecipients = loadedRecipients;

        renderRecipients();
        toggleZaloInputs();

        const badge = document.getElementById('zaloStatusBadge');
        if (badge) {
            const hasTarget = cfg.bot_id || cfg.recipient_user_id || cfg.webhook_url || (zaloRecipients.length > 0);
            badge.style.background = hasTarget ? '#dcfce7' : '#fef3c7';
            badge.style.color = hasTarget ? '#15803d' : '#b45309';
            badge.innerHTML = hasTarget ? '<i class="fa-solid fa-circle-check"></i> Đang hoạt động' : '<i class="fa-solid fa-circle-info"></i> Chưa cấu hình';
        }
    } catch (err) {
        console.error('Lỗi nạp cấu hình Zalo:', err);
    }
}

function toggleZaloInputs() {
    const targetType = document.getElementById('zaloTypeSelect')?.value || 'BOT_API';
    const rowWebhook = document.getElementById('zaloWebhookGroup');
    const rowOa = document.getElementById('zaloOaRow');
    const rowBot = document.getElementById('zaloBotRow');

    if (rowWebhook) rowWebhook.style.display = (targetType === 'WEBHOOK') ? 'block' : 'none';
    if (rowOa) rowOa.style.display = (targetType === 'OA_API') ? 'block' : 'none';
    if (rowBot) rowBot.style.display = (targetType === 'BOT_API') ? 'block' : 'none';
}

function getZaloConfigPayload() {
    const targetType = document.getElementById('zaloTypeSelect')?.value || 'BOT_API';
    const webhookUrl = document.getElementById('zaloWebhookInput')?.value.trim() || '';
    const token = document.getElementById('zaloTokenInput')?.value.trim() || '';
    const userId = document.getElementById('zaloUserIdInput')?.value.trim() || '';
    const botKey = document.getElementById('zaloBotKeyInput')?.value.trim() || '';
    const botId = document.getElementById('zaloBotIdInput')?.value.trim() || '';
    const botBaseUrl = document.getElementById('zaloBotBaseUrlInput')?.value.trim() || '';
    const schoolPhones = zaloRecipients
        .filter(r => r.role !== 'class')
        .map(r => r.phone)
        .join(', ');

    return {
        enabled: true,
        notification_type: targetType,
        webhook_url: webhookUrl,
        access_token: token,
        recipient_user_id: userId,
        bot_api_key: botKey,
        bot_id: botId,
        bot_api_base_url: botBaseUrl,
        recipient_phones: schoolPhones,
        recipients_json: JSON.stringify(zaloRecipients)
    };
}

async function persistZaloConfig(showFeedback = false) {
    try {
        const result = await ReportAPI.saveZaloConfig(getZaloConfigPayload());
        if (showFeedback) {
            if (typeof window.showSuccess === 'function') {
                window.showSuccess(result.message, 'Lưu Cấu Hình Zalo');
            } else {
                showToast(result.message, 'success');
            }
        }
    } catch (err) {
        if (showFeedback) {
            const msg = err.message || err;
            if (typeof window.showError === 'function') {
                window.showError('Lỗi lưu cấu hình Zalo: ' + msg, 'Lỗi');
            } else {
                alert('Lỗi lưu cấu hình Zalo: ' + msg);
            }
        }
    }
}

function scheduleZaloAutoSave() {
    clearTimeout(zaloSaveTimer);
    zaloSaveTimer = setTimeout(() => persistZaloConfig(false), 800);
}

async function handleSendTestZalo() {
    const btnZalo = document.getElementById('btnSendTestZalo');
    const feedbackEl = document.getElementById('zaloFeedbackMsg');
    const targetType = document.getElementById('zaloTypeSelect')?.value || 'BOT_API';
    const webhookUrl = document.getElementById('zaloWebhookInput')?.value.trim() || '';
    const token = document.getElementById('zaloTokenInput')?.value.trim() || '';
    const userId = document.getElementById('zaloUserIdInput')?.value.trim() || '';
    const botKey = document.getElementById('zaloBotKeyInput')?.value.trim() || '';
    const botId = document.getElementById('zaloBotIdInput')?.value.trim() || '';
    const botBaseUrl = document.getElementById('zaloBotBaseUrlInput')?.value.trim() || '';
    const testPhone = document.getElementById('zaloTestPhoneInput')?.value.trim() || '';

    // Frontend validation based on chosen channel
    if (targetType === 'BOT_API') {
        if (!botKey || !botId) {
            const warnMsg = 'Vui lòng nhập đầy đủ Bot ID và API Key của Zalo Bot Gateway trước khi gửi!';
            showToast(warnMsg, 'warning');
            if (feedbackEl) {
                feedbackEl.className = 'zalo-feedback zalo-feedback--error';
                feedbackEl.style.display = 'block';
                feedbackEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${warnMsg}`;
            }
            return;
        }
        if (!testPhone && zaloRecipients.length === 0) {
            const warnMsg = 'Vui lòng nhập 1 SĐT nhận tin thử nghiệm (hoặc thêm SĐT Ban Giám Hiệu vào danh sách) trước khi gửi!';
            showToast(warnMsg, 'warning');
            if (feedbackEl) {
                feedbackEl.className = 'zalo-feedback zalo-feedback--error';
                feedbackEl.style.display = 'block';
                feedbackEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${warnMsg}`;
            }
            return;
        }
    } else if (targetType === 'WEBHOOK' && !webhookUrl) {
        const warnMsg = 'Vui lòng nhập URL Webhook trước khi gửi!';
        showToast(warnMsg, 'warning');
        return;
    } else if (targetType === 'OA_API' && (!token || !userId)) {
        const warnMsg = 'Vui lòng nhập Access Token và User ID Zalo OA trước khi gửi!';
        showToast(warnMsg, 'warning');
        return;
    }

    if (btnZalo) {
        btnZalo.disabled = true;
        btnZalo.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi Zalo...';
    }

    if (feedbackEl) {
        feedbackEl.className = 'zalo-feedback';
        feedbackEl.style.display = 'block';
        feedbackEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kết nối Zalo API Gateway...';
    }

    try {
        const payload = {
            target_type: targetType,
            notification_type: targetType,
            webhook_url: webhookUrl,
            access_token: token,
            user_id: userId,
            recipient_user_id: userId,
            api_key: botKey,
            bot_api_key: botKey,
            bot_id: botId,
            api_base_url: botBaseUrl,
            bot_api_base_url: botBaseUrl,
            phone: testPhone,
            test_phone: testPhone,
            recipients: zaloRecipients
        };

        const result = await ReportAPI.sendZalo(payload);

        if (feedbackEl) {
            if (result.success) {
                feedbackEl.className = 'zalo-feedback zalo-feedback--success';
                feedbackEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${result.message}`;
                if (typeof window.showSuccess === 'function') {
                    window.showSuccess(result.message, 'Gửi Tin Nhắn Zalo Thành Công');
                } else {
                    showToast(result.message, 'success');
                }
            } else {
                feedbackEl.className = 'zalo-feedback zalo-feedback--error';
                feedbackEl.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> ${result.message}`;
                if (typeof window.showError === 'function') {
                    window.showError(result.message, 'Lỗi Gửi Zalo');
                } else {
                    showToast(result.message, 'danger');
                }
            }
        }
    } catch (err) {
        const msg = err.message || err;
        if (feedbackEl) {
            feedbackEl.className = 'zalo-feedback zalo-feedback--error';
            feedbackEl.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> Lỗi: ${msg}`;
        }
        showToast('Lỗi gửi tin Zalo: ' + msg, 'danger');
    } finally {
        if (btnZalo) {
            btnZalo.disabled = false;
            btnZalo.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Gửi Thử Tin Nhắn Qua Zalo';
        }
    }
}

// ===================== RECIPIENT MANAGEMENT =====================
function initRecipientControls() {
    const roleSelect = document.getElementById('recipientRoleSelect');
    const classGroup = document.getElementById('recipientClassGroup');
    const phoneInput = document.getElementById('phoneAddInput');
    const btnAdd = document.getElementById('btnAddPhone');

    if (roleSelect && classGroup) {
        roleSelect.addEventListener('change', () => {
            classGroup.style.display = (roleSelect.value === 'class') ? 'block' : 'none';
        });
    }

    if (btnAdd && phoneInput) {
        const addFn = () => {
            const phone = phoneInput.value.trim();
            if (!phone) return;
            const role = roleSelect?.value || 'school';
            let classId = null;
            let className = '';

            if (role === 'class') {
                const cs = document.getElementById('recipientClassSelect');
                classId = cs ? cs.value : null;
                className = cs && cs.selectedIndex > 0 ? cs.options[cs.selectedIndex].text : '';
                if (!classId) {
                    alert('Vui lòng chọn lớp học cho Giáo Viên Chủ Nhiệm!');
                    return;
                }
            }

            const cleanPhone = phone.replace(/[^0-9+]/g, '');
            if (cleanPhone.length < 9) {
                alert('Số điện thoại không hợp lệ!');
                return;
            }

            const exists = zaloRecipients.some(r => r.phone === cleanPhone && r.role === role && r.class_id === classId);
            if (exists) {
                alert('Người nhận này đã có trong danh sách!');
                return;
            }

            zaloRecipients.push({
                role,
                phone: cleanPhone,
                class_id: classId,
                class_name: className,
                label: role === 'school' ? 'Ban Giám Hiệu' : `GVCN ${className}`
            });

            phoneInput.value = '';
            renderRecipients();
            scheduleZaloAutoSave();
        };

        btnAdd.addEventListener('click', addFn);
        phoneInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addFn();
            }
        });
    }
}

function renderRecipients() {
    const container = document.getElementById('recipientsContainer');
    const hiddenInput = document.getElementById('zaloRecipientsInput');
    if (!container) return;

    container.innerHTML = '';
    if (zaloRecipients.length === 0) {
        container.innerHTML = '<span style="color: var(--text-muted); font-size: 0.85rem; font-style: italic;">Chưa có số điện thoại nào trong danh sách. Hãy thêm ít nhất 1 SĐT của Ban Giám Hiệu để nhận tin tóm tắt toàn trường.</span>';
        if (hiddenInput) hiddenInput.value = '';
        return;
    }

    zaloRecipients.forEach((rec, idx) => {
        const tag = document.createElement('div');
        tag.className = `phone-tag ${rec.role === 'class' ? 'phone-tag--class' : 'phone-tag--school'}`;
        const roleIcon = rec.role === 'class' ? 'fa-chalkboard-user' : 'fa-building-columns';
        const roleLabel = rec.role === 'class' ? (rec.class_name ? `GVCN ${rec.class_name}` : 'GVCN') : 'Ban Giám Hiệu';

        tag.innerHTML = `
            <i class="fa-solid ${roleIcon}"></i>
            <span class="phone-tag-role">${roleLabel}:</span>
            <span class="phone-tag-num">${rec.phone}</span>
            <button type="button" class="phone-tag-del" title="Xóa người nhận" data-idx="${idx}">&times;</button>
        `;
        container.appendChild(tag);
    });

    container.querySelectorAll('.phone-tag-del').forEach(btn => {
        btn.addEventListener('click', () => {
            const idx = parseInt(btn.getAttribute('data-idx'));
            zaloRecipients.splice(idx, 1);
            renderRecipients();
            scheduleZaloAutoSave();
        });
    });

    if (hiddenInput) {
        hiddenInput.value = JSON.stringify(zaloRecipients);
    }
}

// ===================== ADJUST NOTIFICATION SETTINGS =====================
let notificationSettings = {
    enable_zalo: true,
    enable_email: false,
    send_condition: 'always',
    alert_threshold_percent: 10,
    alert_class_absent_count: 3,
    scan_time_morning: '06:45',
    scan_time_afternoon: '12:45',
    auto_scan_enabled: true,
    zalo_school_template: '',
    zalo_class_template: '',
    email_subject_template: '',
    email_body_template: '',
    defaults: {}
};
let activeTemplateType = 'school'; // 'school' | 'class' | 'email'

async function loadAdjustSettings() {
    try {
        const data = await ReportAPI.getNotificationSettings();
        if (data) {
            notificationSettings = { ...notificationSettings, ...data };

            const zActive = document.getElementById('ruleZaloActive');
            if (zActive) zActive.checked = !!notificationSettings.enable_zalo;

            const eActive = document.getElementById('ruleEmailActive');
            if (eActive) eActive.checked = !!notificationSettings.enable_email;

            const sCond = document.getElementById('ruleSendCondition');
            if (sCond) sCond.value = notificationSettings.send_condition || 'always';

            const thPct = document.getElementById('ruleThresholdPercent');
            if (thPct) thPct.value = notificationSettings.alert_threshold_percent ?? 10;

            const clAbs = document.getElementById('ruleClassAbsentCount');
            if (clAbs) clAbs.value = notificationSettings.alert_class_absent_count ?? 3;

            const aScan = document.getElementById('ruleAutoScanActive');
            if (aScan) aScan.checked = !!notificationSettings.auto_scan_enabled;

            const mTime = document.getElementById('ruleMorningTime');
            if (mTime) mTime.value = notificationSettings.scan_time_morning || '06:45';

            const aTime = document.getElementById('ruleAfternoonTime');
            if (aTime) aTime.value = notificationSettings.scan_time_afternoon || '12:45';

            updateScheduleTabTimes(
                notificationSettings.scan_time_morning,
                notificationSettings.scan_time_afternoon,
                notificationSettings.auto_scan_enabled
            );

            const emSubj = document.getElementById('emailSubjectInput');
            if (emSubj) emSubj.value = notificationSettings.email_subject_template || '';

            syncEditorWithActiveTemplate();
        }
    } catch (err) {
        console.warn('Lỗi nạp cấu hình điều chỉnh thông báo:', err);
    }
}

function updateScheduleTabTimes(morningTime, afternoonTime, isEnabled = true) {
    const elMorning = document.getElementById('scheduleCardMorningTime');
    const elAfternoon = document.getElementById('scheduleCardAfternoonTime');
    const badgeM = document.getElementById('badgeMorningTime');
    const badgeA = document.getElementById('badgeAfternoonTime');
    const statusBadge = document.getElementById('scheduleStatusBadge');
    const engineBadge = document.getElementById('badgeEngineStatus');

    if (elMorning && morningTime) elMorning.textContent = `Ca Quét 1: ${morningTime} Sáng`;
    if (elAfternoon && afternoonTime) elAfternoon.textContent = `Ca Quét 2: ${afternoonTime} Trưa`;
    if (badgeM && morningTime) badgeM.textContent = morningTime;
    if (badgeA && afternoonTime) badgeA.textContent = afternoonTime;

    if (statusBadge) {
        statusBadge.style.background = isEnabled ? '#dcfce7' : '#f1f5f9';
        statusBadge.style.color = isEnabled ? '#15803d' : '#64748b';
        statusBadge.innerHTML = isEnabled 
            ? '<i class="fa-solid fa-circle-check"></i> Đang Kích Hoạt' 
            : '<i class="fa-solid fa-circle-pause"></i> Đã Tạm Dừng';
    }

    if (engineBadge) {
        engineBadge.style.background = isEnabled ? '#dcfce7' : '#f1f5f9';
        engineBadge.style.color = isEnabled ? '#15803d' : '#64748b';
        engineBadge.innerHTML = isEnabled 
            ? '<i class="fa-solid fa-circle-check"></i> Đang Kích Hoạt' 
            : '<i class="fa-solid fa-circle-pause"></i> Đã Tạm Dừng';
    }
}

function syncEditorWithActiveTemplate() {
    const editor = document.getElementById('templateEditor');
    const subjRow = document.getElementById('emailSubjectRow');
    if (!editor) return;

    if (activeTemplateType === 'school') {
        editor.value = notificationSettings.zalo_school_template || '';
        if (subjRow) subjRow.style.display = 'none';
    } else if (activeTemplateType === 'class') {
        editor.value = notificationSettings.zalo_class_template || '';
        if (subjRow) subjRow.style.display = 'none';
    } else if (activeTemplateType === 'email') {
        editor.value = notificationSettings.email_body_template || '';
        if (subjRow) subjRow.style.display = 'block';
    }
    updateLivePreview();
}

function initAdjustControls() {
    // Template Selector Tabs
    const tplBtns = document.querySelectorAll('.template-selector-tabs .tpl-btn');
    tplBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            saveCurrentEditorToMemory();
            tplBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeTemplateType = btn.getAttribute('data-tpl') || 'school';
            syncEditorWithActiveTemplate();
        });
    });

    // Token Pills click -> insert into editor cursor
    const tokenBtns = document.querySelectorAll('#tokenPillsContainer .token-pill');
    tokenBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const token = btn.getAttribute('data-token');
            const editor = document.getElementById('templateEditor');
            if (!token || !editor) return;

            const start = editor.selectionStart;
            const end = editor.selectionEnd;
            const text = editor.value;
            editor.value = text.substring(0, start) + token + text.substring(end);
            editor.focus();
            editor.selectionStart = editor.selectionEnd = start + token.length;

            saveCurrentEditorToMemory();
            updateLivePreview();
        });
    });

    // Textarea input event -> live update
    const editor = document.getElementById('templateEditor');
    if (editor) {
        editor.addEventListener('input', () => {
            saveCurrentEditorToMemory();
            updateLivePreview();
        });
    }

    const emailSubj = document.getElementById('emailSubjectInput');
    if (emailSubj) {
        emailSubj.addEventListener('input', () => {
            notificationSettings.email_subject_template = emailSubj.value;
            updateLivePreview();
        });
    }

    // Save button
    const btnSave = document.getElementById('btnSaveNotificationAdjust');
    if (btnSave) {
        btnSave.addEventListener('click', handleSaveAdjustSettings);
    }

    // Reset default button
    const btnReset = document.getElementById('btnResetDefaultTemplates');
    if (btnReset) {
        btnReset.addEventListener('click', handleResetDefaultTemplates);
    }
}

function saveCurrentEditorToMemory() {
    const editor = document.getElementById('templateEditor');
    if (!editor) return;
    if (activeTemplateType === 'school') {
        notificationSettings.zalo_school_template = editor.value;
    } else if (activeTemplateType === 'class') {
        notificationSettings.zalo_class_template = editor.value;
    } else if (activeTemplateType === 'email') {
        notificationSettings.email_body_template = editor.value;
    }
}

function updateLivePreview() {
    const bubble = document.getElementById('previewBubble');
    const senderName = document.getElementById('previewSenderName');
    const recipientRole = document.getElementById('previewRecipientRole');
    const previewTime = document.getElementById('previewTime');
    const editor = document.getElementById('templateEditor');
    if (!bubble || !editor) return;

    const rawTpl = editor.value || '';
    const now = new Date();
    const dateStr = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`;
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    if (previewTime) previewTime.textContent = timeStr;

    // Simulated data
    const sampleData = {
        '{ngay}': dateStr,
        '{gio}': timeStr,
        '{tong_lop}': '30',
        '{si_so}': '1275',
        '{co_mat}': '1253',
        '{vang_mat}': '22',
        '{ty_le}': '98.3%',
        '{danh_sach_vang}': '⚠️ DANH SÁCH LỚP CÓ HỌC SINH VẮNG:\n• Lớp 10A1 (P.101): Vắng 2 em (Hiện diện: 40/42)\n• Lớp 11B3 (P.205): Vắng 1 em (Hiện diện: 41/42)',
        '{lop}': 'Lớp 10A1',
        '{phong}': '(P.101)'
    };

    let rendered = rawTpl;
    for (const [k, v] of Object.entries(sampleData)) {
        rendered = rendered.split(k).join(v);
    }

    if (activeTemplateType === 'school') {
        if (senderName) senderName.textContent = 'Zalo Bot THPT Điều Cải';
        if (recipientRole) recipientRole.textContent = 'Gửi tới: Ban Giám Hiệu';
    } else if (activeTemplateType === 'class') {
        if (senderName) senderName.textContent = 'Zalo Bot THPT Điều Cải';
        if (recipientRole) recipientRole.textContent = 'Gửi tới: Giáo Viên Chủ Nhiệm (Lớp 10A1)';
    } else if (activeTemplateType === 'email') {
        const rawSubj = document.getElementById('emailSubjectInput')?.value || '[ĐIỂM DANH SĨ SỐ] Báo cáo ngày {ngay} lúc {gio} - THPT Điều Cải';
        const subj = rawSubj.replace('{ngay}', dateStr).replace('{gio}', timeStr);
        if (senderName) senderName.textContent = 'Email Server (SMTP)';
        if (recipientRole) recipientRole.textContent = `Tiêu đề: ${subj}`;
    }

    bubble.textContent = rendered || '(Mẫu tin nhắn đang trống)';
}

async function handleSaveAdjustSettings() {
    saveCurrentEditorToMemory();
    const btnSave = document.getElementById('btnSaveNotificationAdjust');
    const feedback = document.getElementById('adjustFeedbackMsg');
    if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
    }

    const payload = {
        enable_zalo: document.getElementById('ruleZaloActive')?.checked ?? true,
        enable_email: document.getElementById('ruleEmailActive')?.checked ?? false,
        send_condition: document.getElementById('ruleSendCondition')?.value || 'always',
        alert_threshold_percent: parseFloat(document.getElementById('ruleThresholdPercent')?.value) || 10.0,
        alert_class_absent_count: parseInt(document.getElementById('ruleClassAbsentCount')?.value) || 3,
        scan_time_morning: document.getElementById('ruleMorningTime')?.value || '06:45',
        scan_time_afternoon: document.getElementById('ruleAfternoonTime')?.value || '12:45',
        auto_scan_enabled: document.getElementById('ruleAutoScanActive')?.checked ?? true,
        zalo_school_template: notificationSettings.zalo_school_template,
        zalo_class_template: notificationSettings.zalo_class_template,
        email_subject_template: document.getElementById('emailSubjectInput')?.value || notificationSettings.email_subject_template,
        email_body_template: notificationSettings.email_body_template
    };

    try {
        const res = await ReportAPI.saveNotificationSettings(payload);
        updateScheduleTabTimes(payload.scan_time_morning, payload.scan_time_afternoon);
        showToast(res.message || 'Đã lưu cấu hình điều chỉnh thành công!', 'success');
        if (feedback) {
            feedback.style.color = '#059669';
            feedback.innerHTML = '<i class="fa-solid fa-circle-check"></i> Đã lưu các quy tắc và mẫu thông báo thành công!';
            setTimeout(() => { feedback.innerHTML = ''; }, 4000);
        }
    } catch (err) {
        console.error('Lỗi lưu cấu hình điều chỉnh:', err);
        showToast('Lỗi lưu cấu hình điều chỉnh', 'error');
        if (feedback) {
            feedback.style.color = '#dc2626';
            feedback.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> Lỗi: ${err.message || err}`;
        }
    } finally {
        if (btnSave) {
            btnSave.disabled = false;
            btnSave.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu Cấu Hình Điều Chỉnh';
        }
    }
}

function handleResetDefaultTemplates() {
    if (!confirm('Bạn có chắc chắn muốn khôi phục tất cả mẫu tin nhắn về trạng thái mặc định của hệ thống?')) return;
    const defs = notificationSettings.defaults || {};
    if (defs.ZALO_SCHOOL_TEMPLATE) notificationSettings.zalo_school_template = defs.ZALO_SCHOOL_TEMPLATE;
    if (defs.ZALO_CLASS_TEMPLATE) notificationSettings.zalo_class_template = defs.ZALO_CLASS_TEMPLATE;
    if (defs.EMAIL_BODY_TEMPLATE) notificationSettings.email_body_template = defs.EMAIL_BODY_TEMPLATE;
    if (defs.EMAIL_SUBJECT_TEMPLATE) {
        notificationSettings.email_subject_template = defs.EMAIL_SUBJECT_TEMPLATE;
        const subjInput = document.getElementById('emailSubjectInput');
        if (subjInput) subjInput.value = defs.EMAIL_SUBJECT_TEMPLATE;
    }
    syncEditorWithActiveTemplate();
    showToast('Đã khôi phục các mẫu tin nhắn mặc định!', 'info');
}

// ===================== SCHEDULE CONTROLS =====================
function initScheduleControls() {
    const btnSave = document.getElementById('btnSaveScheduleConfig');
    if (btnSave) {
        btnSave.addEventListener('click', handleSaveScheduleConfig);
    }

    const btnReset = document.getElementById('btnResetScheduleTimes');
    if (btnReset) {
        btnReset.addEventListener('click', handleResetScheduleTimes);
    }

    const btnToggle = document.getElementById('btnToggleEditSchedule');
    if (btnToggle) {
        btnToggle.addEventListener('click', () => {
            const panel = document.getElementById('scheduleEditPanel');
            const morningInput = document.getElementById('ruleMorningTime');
            if (panel) {
                panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
                panel.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.35)';
                setTimeout(() => {
                    panel.style.boxShadow = '';
                    if (morningInput) morningInput.focus();
                }, 700);
            }
        });
    }

    // Live update badges
    const mInput = document.getElementById('ruleMorningTime');
    if (mInput) {
        mInput.addEventListener('input', () => {
            const b = document.getElementById('badgeMorningTime');
            if (b && mInput.value) b.textContent = mInput.value;
            notificationSettings.scan_time_morning = mInput.value;
        });
    }

    const aInput = document.getElementById('ruleAfternoonTime');
    if (aInput) {
        aInput.addEventListener('input', () => {
            const b = document.getElementById('badgeAfternoonTime');
            if (b && aInput.value) b.textContent = aInput.value;
            notificationSettings.scan_time_afternoon = aInput.value;
        });
    }

    const autoSwitch = document.getElementById('ruleAutoScanActive');
    if (autoSwitch) {
        autoSwitch.addEventListener('change', () => {
            const isEnabled = autoSwitch.checked;
            notificationSettings.auto_scan_enabled = isEnabled;
            updateScheduleTabTimes(
                document.getElementById('ruleMorningTime')?.value || '06:45',
                document.getElementById('ruleAfternoonTime')?.value || '12:45',
                isEnabled
            );
        });
    }
}

async function handleSaveScheduleConfig() {
    const btnSave = document.getElementById('btnSaveScheduleConfig');
    const feedback = document.getElementById('scheduleFeedbackMsg');
    const morningTime = document.getElementById('ruleMorningTime')?.value || '06:45';
    const afternoonTime = document.getElementById('ruleAfternoonTime')?.value || '12:45';
    const autoScanActive = document.getElementById('ruleAutoScanActive')?.checked ?? true;

    if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu lịch trình...';
    }

    const payload = {
        enable_zalo: notificationSettings.enable_zalo,
        enable_email: notificationSettings.enable_email,
        send_condition: notificationSettings.send_condition,
        alert_threshold_percent: notificationSettings.alert_threshold_percent,
        alert_class_absent_count: notificationSettings.alert_class_absent_count,
        scan_time_morning: morningTime,
        scan_time_afternoon: afternoonTime,
        auto_scan_enabled: autoScanActive,
        zalo_school_template: notificationSettings.zalo_school_template,
        zalo_class_template: notificationSettings.zalo_class_template,
        email_subject_template: notificationSettings.email_subject_template,
        email_body_template: notificationSettings.email_body_template
    };

    try {
        const res = await ReportAPI.saveNotificationSettings(payload);
        notificationSettings.scan_time_morning = morningTime;
        notificationSettings.scan_time_afternoon = afternoonTime;
        notificationSettings.auto_scan_enabled = autoScanActive;

        updateScheduleTabTimes(morningTime, afternoonTime, autoScanActive);
        showToast(res.message || 'Đã lưu cài đặt lịch trình quét thành công!', 'success');
        if (feedback) {
            feedback.style.display = 'block';
            feedback.className = 'zalo-feedback zalo-feedback--success';
            feedback.innerHTML = '<i class="fa-solid fa-circle-check"></i> Đã cập nhật giờ quét và đồng bộ vào bộ lập lịch APScheduler thành công!';
            setTimeout(() => { feedback.style.display = 'none'; }, 4000);
        }
    } catch (err) {
        const msg = err.message || err;
        showToast('Lỗi lưu lịch trình: ' + msg, 'danger');
        if (feedback) {
            feedback.style.display = 'block';
            feedback.className = 'zalo-feedback zalo-feedback--error';
            feedback.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> Lỗi: ${msg}`;
        }
    } finally {
        if (btnSave) {
            btnSave.disabled = false;
            btnSave.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu Cài Đặt Lịch Trình';
        }
    }
}

function handleResetScheduleTimes() {
    const mInput = document.getElementById('ruleMorningTime');
    const aInput = document.getElementById('ruleAfternoonTime');
    const autoSwitch = document.getElementById('ruleAutoScanActive');
    if (mInput) mInput.value = '06:45';
    if (aInput) aInput.value = '12:45';
    if (autoSwitch) autoSwitch.checked = true;

    updateScheduleTabTimes('06:45', '12:45', true);
    showToast('Đã khôi phục giờ quét mặc định: 06:45 & 12:45 (Vui lòng bấm Lưu Cài Đặt để áp dụng)', 'info');
}
