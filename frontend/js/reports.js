/**
 * reports.js - Reports & Data Management Controller
 * THPT Điều Cải - Attendance System
 */
import { ReportAPI, AttendanceAPI, SystemAPI, showToast, API_BASE } from './api.js';

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

    // Zalo Type Selector
    const zaloSelect = document.getElementById('zaloTypeSelect');
    if (zaloSelect) zaloSelect.addEventListener('change', toggleZaloInputs);

    // Phone Tags Management
    initPhoneTags();

    // Reset Message Template
    const btnResetTemplate = document.getElementById('btnResetTemplate');
    if (btnResetTemplate) {
        btnResetTemplate.addEventListener('click', () => {
            const tpl = document.getElementById('zaloMessageTemplate');
            if (tpl) {
                tpl.value = DEFAULT_ZALO_TEMPLATE;
                showToast('Đã khôi phục mẫu tin nhắn mặc định', 'success');
                updateCharCount();
            }
        });
    }

    // Character counter for message template
    const messageTemplate = document.getElementById('zaloMessageTemplate');
    if (messageTemplate) {
        messageTemplate.addEventListener('input', updateCharCount);
        updateCharCount(); // Initial count
    }

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
            const phones = document.getElementById('zaloPhonesInput')?.value.trim();
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
                    phone: testPhone || phones || undefined
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

    // Save Zalo Config
    const btnSaveZalo = document.getElementById('btnSaveZaloConfig');
    if (btnSaveZalo) {
        btnSaveZalo.addEventListener('click', async () => {
            const targetType = document.getElementById('zaloTypeSelect')?.value;
            const webhookUrl = document.getElementById('zaloWebhookInput')?.value.trim();
            const token = document.getElementById('zaloTokenInput')?.value.trim();
            const userId = document.getElementById('zaloUserIdInput')?.value.trim();
            const botKey = document.getElementById('zaloBotKeyInput')?.value.trim();
            const botId = document.getElementById('zaloBotIdInput')?.value.trim();
            const botBaseUrl = document.getElementById('zaloBotBaseUrlInput')?.value.trim();
            const phones = document.getElementById('zaloPhonesInput')?.value.trim();

            try {
                const result = await ReportAPI.saveZaloConfig({
                    enabled: true,
                    notification_type: targetType,
                    webhook_url: webhookUrl,
                    access_token: token,
                    recipient_user_id: userId,
                    bot_api_key: botKey,
                    bot_id: botId,
                    bot_api_base_url: botBaseUrl,
                    recipient_phones: phones
                });
                if (typeof window.showSuccess === 'function') {
                    window.showSuccess(result.message, 'Lưu Cấu Hình Zalo');
                } else {
                    showToast(result.message, 'success');
                }
                loadZaloStatus();
            } catch (err) {
                if (typeof window.showError === 'function') {
                    window.showError('Lỗi lưu cấu hình Zalo: ' + (err.message || err));
                } else {
                    alert('Lỗi lưu cấu hình Zalo: ' + (err.message || err));
                }
            }
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
        if (badge && data.enabled) {
            badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Đang hoạt động';
            badge.style.background = '#e0f2fe';
            badge.style.color = '#0369a1';
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
        if (data.recipient_phones) {
            loadPhonesFromString(data.recipient_phones);
        }
        if (data.bot_api_key_masked) {
            const botKeyInput = document.getElementById('zaloBotKeyInput');
            if (botKeyInput) botKeyInput.placeholder = data.bot_api_key_masked;
        }
    } catch (err) {
        console.error("Lỗi nạp trạng thái Zalo:", err);
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

function updateCharCount() {
    const textarea = document.getElementById('zaloMessageTemplate');
    const counter = document.getElementById('charCount');
    if (textarea && counter) {
        const count = textarea.value.length;
        counter.textContent = count;
        if (count > 1000) {
            counter.style.color = '#dc2626';
            counter.style.fontWeight = '700';
        } else if (count > 800) {
            counter.style.color = '#f59e0b';
            counter.style.fontWeight = '600';
        } else {
            counter.style.color = '#9ca3af';
            counter.style.fontWeight = '400';
        }
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

// ===================== PHONE TAGS MANAGEMENT =====================
let phoneTags = [];

const DEFAULT_ZALO_TEMPLATE = `🔔 [THPT ĐIỀU CẢI] BÁO CÁO ĐIỂM DANH SĨ SỐ ĐẦU GIỜ SÁNG
📅 Ngày quét: Hôm nay | Giờ: 06:45:00
🏫 Tổng số lớp: 30 lớp | 👥 Sĩ số: 1,230/1,245 (Tỷ lệ: 98.8%)
✅ Có mặt: 1,230 | ❌ Vắng mặt: 15 em
⚠️ CÁC LỚP CÓ HỌC SINH VẮNG:
• Lớp 10A1 (P.101): Vắng 2 em (40/42)
• Lớp 11A4 (P.114): Vắng 1 em (39/40)
📁 Báo cáo chi tiết Excel và ảnh đối chứng AI đã lưu trên hệ thống.`;

function initPhoneTags() {
    const addInput = document.getElementById('phoneAddInput');
    const btnAdd = document.getElementById('btnAddPhone');

    if (addInput) {
        addInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addPhoneTag(addInput.value.trim());
                addInput.value = '';
            }
        });
    }
    if (btnAdd) {
        btnAdd.addEventListener('click', () => {
            addPhoneTag(addInput?.value.trim());
            if (addInput) addInput.value = '';
            addInput?.focus();
        });
    }
}

function addPhoneTag(phone) {
    if (!phone) return;
    // Normalize: remove spaces, keep digits and + only
    phone = phone.replace(/[^\d+]/g, '');
    if (phone.length < 9 || phone.length > 15) {
        showToast('SĐT không hợp lệ (9-15 ký tự số)', 'error');
        return;
    }
    if (phoneTags.includes(phone)) {
        showToast('SĐT này đã có trong danh sách', 'error');
        return;
    }
    if (phoneTags.length >= 10) {
        showToast('Đã đạt tối đa 10 SĐT', 'error');
        return;
    }
    phoneTags.push(phone);
    renderPhoneTags();
}

function removePhoneTag(phone) {
    phoneTags = phoneTags.filter(p => p !== phone);
    renderPhoneTags();
}

function renderPhoneTags() {
    const container = document.getElementById('phoneTagsContainer');
    const hiddenInput = document.getElementById('zaloPhonesInput');
    if (!container) return;

    if (phoneTags.length === 0) {
        container.innerHTML = '<span style="font-size: 0.85rem; color: #94a3b8; font-style: italic; display: flex; align-items: center; gap: 6px;"><i class="fa-solid fa-info-circle"></i> Chưa có SĐT nào. Thêm SĐT bên dưới để gửi tin nhắn.</span>';
    } else {
        container.innerHTML = phoneTags.map(p => `
            <span class="phone-tag" style="display: inline-flex; align-items: center; gap: 7px; background: linear-gradient(135deg, #dbeafe, #bfdbfe); color: #1e40af; padding: 7px 14px; border-radius: 24px; font-size: 0.88rem; font-weight: 700; border: 2px solid #60a5fa; transition: all 0.2s; box-shadow: 0 1px 3px rgba(59, 130, 246, 0.2); cursor: default;">
                <i class="fa-solid fa-phone" style="font-size: 0.75rem;"></i> ${p}
                <button type="button" data-phone="${p}" style="background: #dc2626; border: none; color: white; cursor: pointer; font-size: 0.7rem; padding: 2px 6px; line-height: 1; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; transition: all 0.15s;" title="Xóa SĐT" onmouseover="this.style.background='#b91c1c'" onmouseout="this.style.background='#dc2626'">&times;</button>
            </span>
        `).join('');

        container.querySelectorAll('button[data-phone]').forEach(btn => {
            btn.addEventListener('click', () => removePhoneTag(btn.dataset.phone));
        });
    }

    if (hiddenInput) hiddenInput.value = phoneTags.join(', ');
}

function loadPhonesFromString(str) {
    if (!str) return;
    const phones = str.split(',').map(s => s.trim()).filter(s => s.length >= 9);
    phoneTags = [...new Set(phones)];
    renderPhoneTags();
}

window.showImgModal = showImgModal;
window.initTabsNavigation = initTabsNavigation;
window.toggleZaloInputs = toggleZaloInputs;
window.updateCharCount = updateCharCount;
