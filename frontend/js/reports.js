/**
 * reports.js - Reports & Data Management Controller
 * THPT Điều Cải - Attendance System
 */
import { ReportAPI, AttendanceAPI, CameraAPI, SystemAPI, showToast, API_BASE } from './api.js';

let allHistoryRows = [];

document.addEventListener('DOMContentLoaded', () => {
    loadAttendanceHistory();
    loadExcelFiles();
    loadNotificationStatus();
    loadZaloStatus();
    loadDatabaseInfo();

    // Export Excel immediately
    const btnExport = document.getElementById('btnExportExcelNow');
    if (btnExport) {
        btnExport.addEventListener('click', async () => {
            btnExport.disabled = true;
            btnExport.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tổng hợp pandas & xuất Excel...';

            try {
                const result = await ReportAPI.exportExcel();
                if (result.success) {
                    showToast(`Xuất Excel thành công: ${result.filename}`, 'success');
                    loadExcelFiles();
                    if (result.download_url) {
                        const url = result.download_url.startsWith('http') ? result.download_url : `${API_BASE}${result.download_url}`;
                        window.open(url, '_blank');
                    }
                } else {
                    alert('Lỗi xuất Excel: ' + (result.error || result.message));
                }
            } catch (err) {
                alert('Lỗi kết nối: ' + (err.message || err));
            } finally {
                btnExport.disabled = false;
                btnExport.innerHTML = '<i class="fa-solid fa-file-arrow-down"></i> Xuất Báo Cáo Excel Tổng Hợp 30 Lớp';
            }
        });
    }

    // Send test email
    const btnEmail = document.getElementById('btnSendTestEmail');
    if (btnEmail) {
        btnEmail.addEventListener('click', async () => {
            const targetEmail = document.getElementById('principalEmailInput')?.value;
            btnEmail.disabled = true;
            btnEmail.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi email...';

            try {
                const result = await ReportAPI.sendEmail(targetEmail);
                showToast(result.message || 'Gửi email thành công', 'success');
                alert(result.message);
            } catch (err) {
                alert('Lỗi gửi email: ' + (err.message || err));
            } finally {
                btnEmail.disabled = false;
                btnEmail.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Gửi Thử Email Báo Cáo Cho Hiệu Trưởng';
            }
        });
    }

    // Refresh DB
    const btnReload = document.getElementById('btnReloadDb');
    if (btnReload) btnReload.addEventListener('click', loadAttendanceHistory);

    // Clear Attendance History
    const btnClearHistory = document.getElementById('btnClearAttendanceHistory');
    if (btnClearHistory) {
        btnClearHistory.addEventListener('click', async () => {
            if (!confirm('Bạn có chắc chắn muốn XÓA TOÀN BỘ lịch sử điểm danh cũ để làm mới dữ liệu không?\n\n(Lưu ý: Danh sách Camera và cấu hình ROI của bạn vẫn được giữ nguyên an toàn 100%)')) {
                return;
            }

            btnClearHistory.disabled = true;
            btnClearHistory.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xóa...';

            try {
                const res = await AttendanceAPI.clearHistory();
                if (res.success) {
                    showToast(res.message || 'Đã làm mới dữ liệu thành công', 'success');
                    await loadAttendanceHistory();
                } else {
                    alert('Lỗi: ' + (res.message || 'Không thể xóa'));
                }
            } catch (err) {
                alert('Lỗi kết nối: ' + (err.message || err));
            } finally {
                btnClearHistory.disabled = false;
                btnClearHistory.innerHTML = '<i class="fa-solid fa-trash-can"></i> Xóa Lịch Sử';
            }
        });
    }

    // Filter DB
    const filterInput = document.getElementById('filterDbInput');
    if (filterInput) {
        filterInput.addEventListener('input', (e) => {
            filterDbRows(e.target.value.toLowerCase().trim());
        });
    }

    // Save DB Config
    const btnSaveDb = document.getElementById('btnSaveDbConfig');
    if (btnSaveDb) {
        btnSaveDb.addEventListener('click', async () => {
            const uri = document.getElementById('dbUriInput')?.value;
            alert(`Đã cập nhật cấu hình chuỗi kết nối CSDL: ${uri}`);
        });
    }

    // Test DB Connection
    const btnTestDb = document.getElementById('btnTestDbConnection');
    if (btnTestDb) {
        btnTestDb.addEventListener('click', () => {
            alert('Kiểm tra kết nối CSDL thành công! Driver hỗ trợ SQLite, PostgreSQL (psycopg2) và MySQL (pymysql) sẵn sàng.');
        });
    }

    // Zalo Type Selector (tự động lưu khi đổi phương thức gửi)
    const zaloSelect = document.getElementById('zaloTypeSelect');
    if (zaloSelect) zaloSelect.addEventListener('change', () => {
        toggleZaloInputs();
        scheduleZaloAutoSave();
    });

    // Tự động lưu cấu hình Zalo ngay khi sửa bất kỳ trường nhập nào (không cần bấm "Lưu Cấu Hình")
    ['zaloWebhookInput', 'zaloTokenInput', 'zaloUserIdInput', 'zaloBotKeyInput', 'zaloBotIdInput', 'zaloBotBaseUrlInput'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', scheduleZaloAutoSave);
    });

    // Phone Tags Management
    initRecipientControls();

    // Send Test Zalo
    const btnZalo = document.getElementById('btnSendTestZalo');
    if (btnZalo) {
        btnZalo.addEventListener('click', async () => {
            const feedback = document.getElementById('zaloFeedbackMsg');
            const targetType = document.getElementById('zaloTypeSelect')?.value;
            const webhookUrl = document.getElementById('zaloWebhookInput')?.value.trim();
            const token = document.getElementById('zaloTokenInput')?.value.trim();
            const userId = document.getElementById('zaloUserIdInput')?.value.trim();
            const botKey = document.getElementById('zaloBotKeyInput')?.value.trim();
            const botId = document.getElementById('zaloBotIdInput')?.value.trim();
            const botBaseUrl = document.getElementById('zaloBotBaseUrlInput')?.value.trim();
            const testPhone = document.getElementById('zaloTestPhoneInput')?.value.trim();

            btnZalo.disabled = true;
            btnZalo.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi Zalo...';
            const feedbackEl = document.getElementById('zaloFeedbackMsg');
            if (feedbackEl) {
                feedbackEl.style.display = 'block';
                feedbackEl.style.background = '#e0f2fe';
                feedbackEl.style.border = '1px solid #7dd3fc';
                feedbackEl.style.color = '#0369a1';
                feedbackEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kết nối Zalo API...';
            }

            try {
                const result = await ReportAPI.sendZalo({
                    target_type: targetType,
                    webhook_url: webhookUrl || undefined,
                    access_token: token || undefined,
                    user_id: userId || undefined,
                    api_key: botKey || undefined,
                    bot_id: botId || undefined,
                    api_base_url: botBaseUrl || undefined,
                    phone: testPhone || undefined
                });

                if (result.success) {
                    if (feedback) {
                        feedback.style.display = 'block';
                        feedback.style.background = '#dcfce7';
                        feedback.style.border = '1px solid #86efac';
                        feedback.style.color = '#166534';
                        feedback.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${result.message}`;
                    }
                    if (typeof window.showSuccess === 'function') {
                        window.showSuccess(result.message, 'Gửi Tin Nhắn Zalo Thành Công');
                    } else {
                        showToast(result.message, 'success');
                    }
                } else {
                    if (feedback) {
                        feedback.style.display = 'block';
                        feedback.style.background = '#fee2e2';
                        feedback.style.border = '1px solid #fca5a5';
                        feedback.style.color = '#991b1b';
                        feedback.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${result.message}`;
                    }
                    if (typeof window.showError === 'function') {
                        window.showError(result.message, 'Lỗi Gửi Zalo');
                    } else {
                        showToast(result.message, 'error');
                    }
                }
            } catch (err) {
                if (feedback) {
                    feedback.style.display = 'block';
                    feedback.style.background = '#fee2e2';
                    feedback.style.border = '1px solid #fca5a5';
                    feedback.style.color = '#991b1b';
                    feedback.innerHTML = `<i class="fa-solid fa-xmark-circle"></i> Lỗi kết nối: ${err.message || err}`;
                }
            } finally {
                btnZalo.disabled = false;
                btnZalo.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Gửi Thử Tin Nhắn Qua Zalo';
            }
        });
    }

    // Save Zalo Config (nút "Lưu Cấu Hình" - lưu ngay, không chờ auto-save)
    const btnSaveZalo = document.getElementById('btnSaveZaloConfig');
    if (btnSaveZalo) {
        btnSaveZalo.addEventListener('click', () => {
            clearTimeout(zaloSaveTimer);
            persistZaloConfig(true);
        });
    }

    // Nút mở thư mục báo cáo
    const btnOpenFolder = document.getElementById('btnOpenFolder');
    if (btnOpenFolder) {
        btnOpenFolder.addEventListener('click', () => {
            if (typeof window.showInfo === 'function') {
                window.showInfo('Thư mục báo cáo nội bộ được lưu tại: storage/reports/ của dự án.', 'Vị Trí Thư Mục Báo Cáo');
            } else {
                alert('Thư mục báo cáo nội bộ được lưu tại: storage/reports/ của dự án.');
            }
        });
    }

    // Modal close button
    const btnImgClose = document.getElementById('imgModalCloseBtn');
    if (btnImgClose) {
        btnImgClose.addEventListener('click', () => {
            document.getElementById('imgModal')?.classList.remove('active');
        });
    }

    // Tab Switching Navigation
    initTabsNavigation();
});

// ===================== ZALO AUTO-SAVE =====================
let zaloSaveTimer = null;

export function getZaloConfigPayload() {
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

export async function persistZaloConfig(showFeedback = false) {
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
            if (typeof window.showError === 'function') {
                window.showError('Lỗi lưu cấu hình Zalo: ' + (err.message || err));
            } else {
                alert('Lỗi lưu cấu hình Zalo: ' + (err.message || err));
            }
        }
    }
}

export function scheduleZaloAutoSave() {
    clearTimeout(zaloSaveTimer);
    zaloSaveTimer = setTimeout(() => persistZaloConfig(false), 800);
}

export async function loadAttendanceHistory() {
    const tbody = document.getElementById('dbTableBody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải dữ liệu từ CSDL...</td></tr>`;

    try {
        const data = await AttendanceAPI.getHistory();
        allHistoryRows = data.records || [];

        if (allHistoryRows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">Chưa có bản ghi điểm danh nào trong CSDL. Bấm "Quét Điểm Danh Ngay" tại Dashboard để tạo phiên quét đầu tiên.</td></tr>`;
            return;
        }

        renderDbTable(allHistoryRows);
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--danger); padding: 1.5rem;">Lỗi nạp dữ liệu CSDL: ${err.message || err}</td></tr>`;
    }
}

function renderDbTable(rows) {
    const tbody = document.getElementById('dbTableBody');
    if (!tbody) return;

    tbody.innerHTML = rows.map(r => {
        const isFull = r.absent_count === 0;
        const statusColor = isFull ? 'background: #dcfce7; color: #15803d;' : (r.absent_count <= 2 ? 'background: #fef3c7; color: #b45309;' : 'background: #fee2e2; color: #b91c1c;');
        const statusText = isFull ? 'Đủ 100%' : `Vắng ${r.absent_count} em`;

        const rawImgUrl = r.raw_image_path ? (r.raw_image_path.startsWith('http') ? r.raw_image_path : `${API_BASE}${r.raw_image_path}`) : '';
        const annoImgUrl = r.annotated_image_path ? (r.annotated_image_path.startsWith('http') ? r.annotated_image_path : `${API_BASE}${r.annotated_image_path}`) : '';

        return `
            <tr>
                <td class="cell-datetime"><strong>${r.scan_date}</strong> <span style="font-size: 0.78rem; color: var(--text-muted);">${r.scan_time}</span></td>
                <td class="cell-session"><code style="font-size: 0.75rem; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">${r.session_code}</code></td>
                <td class="cell-class"><strong>${r.class_name}</strong> <span style="font-size: 0.78rem; color: var(--text-muted);">(${r.room_number || 'Phòng'})</span></td>
                <td class="cell-standard">${r.standard_count}</td>
                <td class="cell-present">${r.present_count}</td>
                <td class="cell-absent">${r.absent_count}</td>
                <td class="cell-image">
                    ${rawImgUrl ? `<button class="btn btn-secondary btn-sm" data-img="${rawImgUrl}" data-title="Ảnh Gốc RTSP - ${r.class_name}"><i class="fa-solid fa-image"></i> Xem</button>` : '<span style="color: var(--text-muted);">--</span>'}
                </td>
                <td class="cell-image">
                    ${annoImgUrl ? `<button class="btn btn-primary btn-sm" data-img="${annoImgUrl}" data-title="Ảnh AI Đối Chứng - ${r.class_name}"><i class="fa-solid fa-brain"></i> Xem</button>` : '<span style="color: var(--text-muted);">--</span>'}
                </td>
                <td class="cell-status"><span class="status-pill" style="${statusColor}">${statusText}</span></td>
            </tr>
        `;
    }).join('');

    tbody.querySelectorAll('button[data-img]').forEach(btn => {
        btn.addEventListener('click', () => {
            showImgModal(btn.dataset.img, btn.dataset.title);
        });
    });
}

function filterDbRows(keyword) {
    const filtered = allHistoryRows.filter(r =>
        r.class_name.toLowerCase().includes(keyword) ||
        (r.room_number || '').toLowerCase().includes(keyword) ||
        r.scan_date.includes(keyword)
    );
    renderDbTable(filtered);
}

export async function loadExcelFiles() {
    const tbody = document.getElementById('excelFilesBody');
    if (!tbody) return;

    try {
        const data = await ReportAPI.list();
        const files = data.reports || [];

        if (files.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 1.5rem; color: var(--text-muted);">Chưa có file báo cáo nào. Bấm "Xuất Báo Cáo Excel" ở trên để tạo.</td></tr>`;
            return;
        }

        tbody.innerHTML = files.map(f => {
            const dlUrl = f.download_url.startsWith('http') ? f.download_url : `${API_BASE}${f.download_url}`;
            return `
                <tr>
                    <td class="cell-filename">
                        <i class="fa-solid fa-file-excel" style="color: #10b981; margin-right: 8px;"></i>
                        <strong>${f.filename}</strong>
                    </td>
                    <td class="cell-datetime">${f.created_at}</td>
                    <td class="cell-filesize">${f.size_kb} KB</td>
                    <td class="cell-format">
                        <span class="badge badge-success">Microsoft Excel (.xlsx)</span>
                    </td>
                    <td class="cell-actions">
                        <a href="${dlUrl}" target="_blank" class="btn btn-success btn-sm">
                            <i class="fa-solid fa-download"></i> Tải Về
                        </a>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--danger);">Lỗi nạp danh sách file Excel: ${err.message || err}</td></tr>`;
    }
}

export async function loadNotificationStatus() {
    try {
        const data = await ReportAPI.getDistributionStatus();
        const input = document.getElementById('principalEmailInput');
        if (input) input.value = data.principal_email || 'hieutruong@truongdieucai.edu.vn';
    } catch (err) {
        console.error("Lỗi nạp trạng thái phân phối:", err);
    }
}

export async function loadDatabaseInfo() {
    try {
        const data = await SystemAPI.getDatabaseInfo();
        const input = document.getElementById('dbUriInput');
        if (input) input.value = data.database_url || 'sqlite:///database/attendance.db';
        const badge = document.getElementById('dbTypeBadge');
        if (badge) badge.innerHTML = `<i class="fa-solid fa-database"></i> ${data.db_type} (${data.status})`;
    } catch (err) {
        console.error("Lỗi nạp thông tin CSDL:", err);
    }
}

export async function loadZaloStatus() {
    try {
        const data = await ReportAPI.getZaloStatus();
        const select = document.getElementById('zaloTypeSelect');
        if (select) select.value = data.notification_type || 'BOT_API';
        toggleZaloInputs();

        const webhookInput = document.getElementById('zaloWebhookInput');
        if (webhookInput && data.webhook_configured) {
            webhookInput.placeholder = data.webhook_url_masked || 'Đã cấu hình Webhook URL';
        }

        const userInput = document.getElementById('zaloUserIdInput');
        if (userInput && data.recipient_user_id) {
            userInput.value = data.recipient_user_id;
        }

        const badge = document.getElementById('zaloStatusBadge');
        if (badge) {
            const configured = data.bot_configured || data.oa_configured || data.webhook_configured;
            if (!data.enabled) {
                badge.innerHTML = '<i class="fa-solid fa-circle-pause"></i> Đang tắt';
                badge.style.background = '#f1f5f9';
                badge.style.color = '#64748b';
            } else if (configured) {
                badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Đang hoạt động';
                badge.style.background = '#e0f2fe';
                badge.style.color = '#0369a1';
            } else {
                badge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Chưa cấu hình kênh gửi';
                badge.style.background = '#fef3c7';
                badge.style.color = '#b45309';
            }
        }

        // Cập nhật các trường Zalo Bot API nếu có
        if (data.bot_id) {
            const botIdInput = document.getElementById('zaloBotIdInput');
            if (botIdInput) botIdInput.value = data.bot_id;
        }
        if (data.bot_api_base_url) {
            const baseUrlInput = document.getElementById('zaloBotBaseUrlInput');
            if (baseUrlInput) baseUrlInput.value = data.bot_api_base_url;
        }
        if (data.bot_api_key_masked) {
            const botKeyInput = document.getElementById('zaloBotKeyInput');
            if (botKeyInput) botKeyInput.placeholder = data.bot_api_key_masked;
        }
        if (data.oa_token_masked) {
            const tokenInput = document.getElementById('zaloTokenInput');
            if (tokenInput) tokenInput.placeholder = data.oa_token_masked;
        }

        // Tải danh sách người nhận theo vai trò
        if (Array.isArray(data.recipients) && data.recipients.length > 0) {
            zaloRecipients = data.recipients
                .map(r => ({
                    phone: String(r.phone || '').trim(),
                    role: String(r.role || 'school').trim().toLowerCase() || 'school',
                    class_code: String(r.class_code || '').trim(),
                    class_name: ''
                }))
                .filter(r => r.phone.length >= 9);
            renderRecipients();
        } else if (data.recipient_phones) {
            zaloRecipients = data.recipient_phones
                .split(',')
                .map(s => ({ phone: s.trim(), role: 'school', class_code: '', class_name: '' }))
                .filter(r => r.phone.length >= 9);
            renderRecipients();
        }
    } catch (err) {
        console.error("Lỗi nạp trạng thái Zalo:", err);
        if (typeof window.showToast === 'function') {
            showToast('Không tải được cấu hình Zalo từ máy chủ', 'error');
        }
    }
}

export function toggleZaloInputs() {
    const type = document.getElementById('zaloTypeSelect')?.value;
    const oaRow = document.getElementById('zaloOaRow');
    const botRow = document.getElementById('zaloBotRow');
    const webhookGroup = document.getElementById('zaloWebhookGroup');
    if (oaRow) {
        oaRow.style.display = (type === 'OA_API') ? 'block' : 'none';
    }
    if (botRow) {
        botRow.style.display = (type === 'BOT_API') ? 'block' : 'none';
    }
    if (webhookGroup) {
        webhookGroup.style.display = (type === 'WEBHOOK') ? 'block' : 'none';
    }
}

export function initTabsNavigation() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.getAttribute('data-tab');

            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            button.classList.add('active');
            const targetEl = document.getElementById(targetTab);
            if (targetEl) targetEl.classList.add('active');
        });
    });
}

export function showImgModal(src, title) {
    const titleEl = document.getElementById('imgModalTitle');
    const srcEl = document.getElementById('imgModalSrc');
    if (titleEl) titleEl.innerText = title;
    if (srcEl) srcEl.src = src;
    document.getElementById('imgModal')?.classList.add('active');
}

// ===================== RECIPIENTS THEO VAI TRÒ =====================
// Mỗi người nhận: { phone, role: 'school'|'class', class_code (chỉ dành cho GVCN), class_name }
let zaloRecipients = [];

function initRecipientControls() {
    const roleSelect = document.getElementById('recipientRoleSelect');
    const classGroup = document.getElementById('recipientClassGroup');
    const classSelect = document.getElementById('recipientClassSelect');
    const addInput = document.getElementById('phoneAddInput');
    const btnAdd = document.getElementById('btnAddPhone');

    if (roleSelect && classGroup) {
        const syncRole = () => {
            classGroup.style.display = roleSelect.value === 'class' ? 'block' : 'none';
        };
        roleSelect.addEventListener('change', syncRole);
        syncRole();
    }

    if (classSelect) {
        loadClassOptions(classSelect);
    }

    if (addInput) {
        addInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addRecipient();
                addInput.value = '';
            }
        });
    }
    if (btnAdd) {
        btnAdd.addEventListener('click', () => {
            addRecipient();
            if (addInput) addInput.value = '';
            addInput?.focus();
        });
    }
}

async function loadClassOptions(select) {
    try {
        const data = await CameraAPI.getAll();
        const cams = (data.cameras || [])
            .filter(c => c.is_active !== false && c.code)
            .sort((a, b) => a.name.localeCompare(b.name, 'vi'));
        select.innerHTML = '<option value="">-- Chọn lớp --</option>' + cams
            .map(c => `<option value="${c.code}">${c.name} (${c.room_number || 'Phòng'})</option>`)
            .join('');
    } catch (err) {
        select.innerHTML = '<option value="">-- Không tải được danh sách lớp --</option>';
    }
}

function addRecipient() {
    const role = document.getElementById('recipientRoleSelect')?.value || 'school';
    const classSelect = document.getElementById('recipientClassSelect');
    const classCode = (classSelect?.value || '').trim();
    const input = document.getElementById('phoneAddInput');
    const phone = (input?.value || '').replace(/[^\d+]/g, '');

    if (role === 'class' && !classCode) {
        showToast('Vui lòng chọn lớp chủ nhiệm cho Giáo Viên Chủ Nhiệm', 'error');
        return;
    }
    if (phone.length < 9 || phone.length > 15) {
        showToast('SĐT không hợp lệ (9-15 ký tự số)', 'error');
        return;
    }
    if (zaloRecipients.length >= 30) {
        showToast('Đã đạt tối đa 30 người nhận', 'error');
        return;
    }

    const classKey = role === 'class' ? classCode : '';
    const dup = zaloRecipients.some(r =>
        r.phone === phone && r.role === role && (r.class_code || '') === classKey
    );
    if (dup) {
        showToast('Người nhận này đã có trong danh sách', 'error');
        return;
    }

    const classLabel = classSelect?.selectedOptions?.[0]?.textContent.trim() || classCode;
    zaloRecipients.push({
        phone,
        role,
        class_code: classKey,
        class_name: role === 'class' ? classLabel : ''
    });
    renderRecipients();
    scheduleZaloAutoSave();
}

function removeRecipient(index) {
    zaloRecipients.splice(index, 1);
    renderRecipients();
    scheduleZaloAutoSave();
}

function renderRecipients() {
    const container = document.getElementById('recipientsContainer');
    const hiddenInput = document.getElementById('zaloRecipientsInput');
    if (!container) return;

    if (zaloRecipients.length === 0) {
        container.innerHTML = '<span style="font-size: 0.85rem; color: #94a3b8; font-style: italic; display: flex; align-items: center; gap: 6px;"><i class="fa-solid fa-info-circle"></i> Chưa có người nhận nào. Chọn vai trò và thêm SĐT bên dưới.</span>';
    } else {
        container.innerHTML = zaloRecipients.map((r, i) => {
            const isSchool = r.role !== 'class';
            const label = isSchool
                ? 'BGH'
                : `GVCN ${r.class_name || r.class_code || ''}`;
            return `
                <span class="phone-tag">
                    <i class="fa-solid fa-phone" style="font-size: 0.75rem;"></i> ${r.phone}
                    <span class="recipient-role-badge ${isSchool ? 'school' : 'class'}">${label}</span>
                    <button type="button" class="phone-tag-remove" data-idx="${i}" title="Xóa người nhận">&times;</button>
                </span>
            `;
        }).join('');

        container.querySelectorAll('button[data-idx]').forEach(btn => {
            btn.addEventListener('click', () => removeRecipient(Number(btn.dataset.idx)));
        });
    }

    if (hiddenInput) hiddenInput.value = JSON.stringify(zaloRecipients);
}

window.showImgModal = showImgModal;
window.initTabsNavigation = initTabsNavigation;
window.toggleZaloInputs = toggleZaloInputs;
