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

    // Send test email
    const btnEmail = document.getElementById('btnSendTestEmail');
    if (btnEmail) {
        btnEmail.addEventListener('click', handleSendTestEmail);
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
            badge.style.background = '#dcfce7';
            badge.style.color = '#15803d';
            badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Sẵn sàng phân phối';
        }
    } catch (err) {
        console.error('Lỗi nạp trạng thái email:', err);
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

        if (cfg.recipients_json) {
            try {
                zaloRecipients = JSON.parse(cfg.recipients_json);
            } catch (e) {
                zaloRecipients = [];
            }
        } else if (cfg.recipient_phones) {
            zaloRecipients = cfg.recipient_phones
                .split(',')
                .map(p => p.trim())
                .filter(p => p)
                .map(p => ({ role: 'school', phone: p, label: 'Ban Giám Hiệu' }));
        }

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

    if (btnZalo) {
        btnZalo.disabled = true;
        btnZalo.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi Zalo...';
    }

    if (feedbackEl) {
        feedbackEl.className = 'zalo-feedback';
        feedbackEl.style.display = 'block';
        feedbackEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kết nối Zalo API...';
    }

    try {
        const result = await ReportAPI.sendZalo({
            notification_type: targetType,
            webhook_url: webhookUrl,
            access_token: token,
            recipient_user_id: userId,
            bot_api_key: botKey,
            bot_id: botId,
            bot_api_base_url: botBaseUrl,
            test_phone: testPhone,
            recipients: zaloRecipients
        });

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

            const emSubj = document.getElementById('emailSubjectInput');
            if (emSubj) emSubj.value = notificationSettings.email_subject_template || '';

            syncEditorWithActiveTemplate();
        }
    } catch (err) {
        console.warn('Lỗi nạp cấu hình điều chỉnh thông báo:', err);
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
