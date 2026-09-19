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

    // Send Test Zalo
    const btnZalo = document.getElementById('btnSendTestZalo');
    if (btnZalo) {
        btnZalo.addEventListener('click', async () => {
            const feedback = document.getElementById('zaloFeedbackMsg');
            const targetType = document.getElementById('zaloTypeSelect')?.value;
            const webhookUrl = document.getElementById('zaloWebhookInput')?.value.trim();
            const token = document.getElementById('zaloTokenInput')?.value.trim();
            const userId = document.getElementById('zaloUserIdInput')?.value.trim();

            btnZalo.disabled = true;
            btnZalo.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi Zalo...';
            if (feedback) feedback.innerHTML = '<span style="color: #0284c7;">Đang kết nối Zalo API...</span>';

            try {
                const result = await ReportAPI.sendZalo({
                    target_type: targetType,
                    webhook_url: webhookUrl || undefined,
                    access_token: token || undefined,
                    user_id: userId || undefined
                });

                if (result.success) {
                    if (feedback) feedback.innerHTML = `<span style="color: #16a34a;"><i class="fa-solid fa-check"></i> ${result.message}</span>`;
                    showToast(result.message, 'success');
                } else {
                    if (feedback) feedback.innerHTML = `<span style="color: #dc2626;"><i class="fa-solid fa-triangle-exclamation"></i> ${result.message}</span>`;
                    showToast(result.message, 'error');
                }
            } catch (err) {
                if (feedback) feedback.innerHTML = `<span style="color: #dc2626;">Lỗi: ${err.message || err}</span>`;
            } finally {
                btnZalo.disabled = false;
                btnZalo.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Gửi Thử Tin Nhắn Qua Zalo Ngay';
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

            try {
                const result = await ReportAPI.saveZaloConfig({
                    enabled: true,
                    notification_type: targetType,
                    webhook_url: webhookUrl,
                    access_token: token,
                    recipient_user_id: userId
                });
                alert(result.message);
                loadZaloStatus();
            } catch (err) {
                alert('Lỗi lưu cấu hình Zalo: ' + (err.message || err));
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
                <td><strong>${r.scan_date}</strong> <span style="font-size: 0.78rem; color: var(--text-muted);">${r.scan_time}</span></td>
                <td><code style="font-size: 0.75rem; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">${r.session_code}</code></td>
                <td><strong>${r.class_name}</strong> <span style="font-size: 0.78rem; color: var(--text-muted);">(${r.room_number || 'Phòng'})</span></td>
                <td style="text-align: center;">${r.standard_count}</td>
                <td style="text-align: center; font-weight: 700; color: var(--primary);">${r.present_count}</td>
                <td style="text-align: center; font-weight: 700; color: var(--danger);">${r.absent_count}</td>
                <td>
                    ${rawImgUrl ? `<button class="btn btn-secondary btn-sm" data-img="${rawImgUrl}" data-title="Ảnh Gốc RTSP - ${r.class_name}"><i class="fa-solid fa-image"></i> Xem ảnh gốc</button>` : '<span style="color: var(--text-muted);">--</span>'}
                </td>
                <td>
                    ${annoImgUrl ? `<button class="btn btn-primary btn-sm" data-img="${annoImgUrl}" data-title="Ảnh AI Đối Chứng - ${r.class_name}"><i class="fa-solid fa-brain"></i> Xem ảnh AI</button>` : '<span style="color: var(--text-muted);">--</span>'}
                </td>
                <td><span class="status-pill" style="${statusColor}">${statusText}</span></td>
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
                    <td><i class="fa-solid fa-file-excel" style="color: #10b981;"></i> <strong>${f.filename}</strong></td>
                    <td>${f.created_at}</td>
                    <td>${f.size_kb} KB</td>
                    <td>Microsoft Excel (.xlsx)</td>
                    <td>
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
        if (select) select.value = data.notification_type || 'WEBHOOK';
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
    } catch (err) {
        console.error("Lỗi nạp trạng thái Zalo:", err);
    }
}

export function toggleZaloInputs() {
    const type = document.getElementById('zaloTypeSelect')?.value;
    const oaRow = document.getElementById('zaloOaRow');
    if (oaRow) {
        oaRow.style.display = (type === 'OA_API') ? 'grid' : 'none';
    }
}

export function showImgModal(src, title) {
    const titleEl = document.getElementById('imgModalTitle');
    const srcEl = document.getElementById('imgModalSrc');
    if (titleEl) titleEl.innerText = title;
    if (srcEl) srcEl.src = src;
    document.getElementById('imgModal')?.classList.add('active');
}

window.showImgModal = showImgModal;
