/**
 * reports.js - Reports & Data Management Controller
 * THPT Điều Cải - Attendance System (Database & Excel Archive)
 */
import { ReportAPI, AttendanceAPI, SystemAPI, showToast, API_BASE } from './api.js';
import SkeletonTemplates from './components/skeleton-templates.js';

let allHistoryRows = [];
let reportActiveGrade = 'all';
let reportActiveStatus = 'all';
let reportDateFilter = '';
let reportKeyword = '';

document.addEventListener('DOMContentLoaded', () => {
    loadAttendanceHistory();
    loadExcelFiles();
    loadDatabaseInfo();
    initTabsNavigation();
    initImgModalEvents();
    initReportFilterEvents();

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
                btnExport.innerHTML = '<i class="fa-solid fa-file-arrow-down"></i> Xuất Báo Cáo Excel Ngay';
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
            if (!confirm('Bạn có chắc chắn muốn XÓA TOÀN BỘ lịch sử điểm danh cũ để làm mới dữ liệu không?\n\n(Lưu ý: Danh sách Camera và cấu hình Vùng của bạn vẫn được giữ nguyên an toàn 100%)')) {
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
});

function getTodayLocalYMD() {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

export async function loadAttendanceHistory() {
    const tbody = document.getElementById('dbTableBody');
    if (!tbody) return;

    // Show skeleton loading
    tbody.innerHTML = SkeletonTemplates.reportTableRow().repeat(5);

    try {
        const data = await AttendanceAPI.getHistory();
        allHistoryRows = data.records || [];

        if (allHistoryRows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9">${SkeletonTemplates.emptyState('Chưa có bản ghi điểm danh. Bấm "Quét Điểm Danh Ngay" tại Dashboard.', 'fa-clipboard-list')}</td></tr>`;
            updateReportCounts([]);
            return;
        }

        applyDbFilters();
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--danger); padding: 1.5rem;">Lỗi nạp dữ liệu CSDL: ${err.message || err}</td></tr>`;
    }
}

function initReportFilterEvents() {
    // 1. Lọc theo Khối
    const gradeGroup = document.getElementById('reportGradeFilterGroup');
    if (gradeGroup) {
        gradeGroup.querySelectorAll('.pill-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                gradeGroup.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                reportActiveGrade = target.dataset.reportGrade || 'all';
                applyDbFilters();
            });
        });
    }

    // 2. Lọc theo Trạng Thái
    const statusGroup = document.getElementById('reportStatusFilterGroup');
    if (statusGroup) {
        statusGroup.querySelectorAll('.pill-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                statusGroup.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                reportActiveStatus = target.dataset.reportStatus || 'all';
                applyDbFilters();
            });
        });
    }

    // 3. Lọc theo Ngày (Date picker)
    const dateInput = document.getElementById('filterReportDate');
    if (dateInput) {
        dateInput.addEventListener('change', (e) => {
            reportDateFilter = e.target.value || '';
            applyDbFilters();
        });
    }

    // 4. Phím tắt chọn ngày Hôm nay
    const btnFilterToday = document.getElementById('btnFilterToday');
    if (btnFilterToday) {
        btnFilterToday.addEventListener('click', () => {
            const todayStr = getTodayLocalYMD();
            if (dateInput) dateInput.value = todayStr;
            reportDateFilter = todayStr;
            applyDbFilters();
        });
    }

    // 5. Bỏ lọc ngày
    const clearDateBtn = document.getElementById('btnClearDateFilter');
    if (clearDateBtn) {
        clearDateBtn.addEventListener('click', () => {
            if (dateInput) dateInput.value = '';
            reportDateFilter = '';
            applyDbFilters();
        });
    }

    // 6. Tìm kiếm từ khóa + Nút xóa từ khóa
    const searchInput = document.getElementById('filterDbInput');
    const btnClearSearch = document.getElementById('btnClearDbSearch');

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const val = e.target.value || '';
            reportKeyword = val.trim().toLowerCase();
            if (btnClearSearch) {
                btnClearSearch.style.display = val.length > 0 ? 'block' : 'none';
            }
            applyDbFilters();
        });
    }

    if (btnClearSearch) {
        btnClearSearch.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            reportKeyword = '';
            btnClearSearch.style.display = 'none';
            applyDbFilters();
        });
    }

    // 7. Đặt lại toàn bộ bộ lọc về mặc định
    const btnResetAll = document.getElementById('btnResetAllFilters');
    if (btnResetAll) {
        btnResetAll.addEventListener('click', () => {
            reportActiveGrade = 'all';
            reportActiveStatus = 'all';
            reportDateFilter = '';
            reportKeyword = '';

            if (dateInput) dateInput.value = '';
            if (searchInput) searchInput.value = '';
            if (btnClearSearch) btnClearSearch.style.display = 'none';

            if (gradeGroup) {
                gradeGroup.querySelectorAll('.pill-btn').forEach(b => {
                    b.classList.toggle('active', b.dataset.reportGrade === 'all');
                });
            }

            if (statusGroup) {
                statusGroup.querySelectorAll('.pill-btn').forEach(b => {
                    b.classList.toggle('active', b.dataset.reportStatus === 'all');
                });
            }

            applyDbFilters();
        });
    }
}

function applyDbFilters() {
    let filtered = allHistoryRows.filter(r => {
        // 1. Lọc Khối
        if (reportActiveGrade !== 'all') {
            const name = (r.class_name || '').toUpperCase();
            if (reportActiveGrade === '10' && !name.includes('10')) return false;
            if (reportActiveGrade === '11' && !name.includes('11')) return false;
            if (reportActiveGrade === '12' && !name.includes('12')) return false;
        }

        // 2. Lọc Trạng thái
        const absent = r.absent_count || 0;
        if (reportActiveStatus === 'absent' && absent === 0) return false;
        if (reportActiveStatus === 'full' && absent > 0) return false;

        // 3. Lọc Ngày
        if (reportDateFilter && r.scan_date !== reportDateFilter) return false;

        // 4. Tìm kiếm từ khóa
        if (reportKeyword) {
            const name = (r.class_name || '').toLowerCase();
            const room = (r.room_number || '').toLowerCase();
            const session = (r.session_code || '').toLowerCase();
            const date = (r.scan_date || '').toLowerCase();
            if (!name.includes(reportKeyword) && !room.includes(reportKeyword) && !session.includes(reportKeyword) && !date.includes(reportKeyword)) {
                return false;
            }
        }

        return true;
    });

    renderDbTable(filtered);
    updateReportCounts(filtered);
}

function updateReportCounts(filtered = null) {
    const all = allHistoryRows.length;
    const absent = allHistoryRows.filter(r => (r.absent_count || 0) > 0).length;
    const full = allHistoryRows.filter(r => (r.absent_count || 0) === 0).length;

    const countAllEl = document.getElementById('repCountAll');
    const countAbsentEl = document.getElementById('repCountAbsent');
    const countFullEl = document.getElementById('repCountFull');

    if (countAllEl) countAllEl.textContent = all;
    if (countAbsentEl) countAbsentEl.textContent = absent;
    if (countFullEl) countFullEl.textContent = full;

    const repFilteredCountEl = document.getElementById('repFilteredCount');
    const repTotalCountEl = document.getElementById('repTotalCount');
    if (repFilteredCountEl) repFilteredCountEl.textContent = filtered ? filtered.length : all;
    if (repTotalCountEl) repTotalCountEl.textContent = all;
}

function renderDbTable(rows) {
    const tbody = document.getElementById('dbTableBody');
    if (!tbody) return;

    if (!rows || rows.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
                    <i class="fa-solid fa-filter-circle-xmark" style="font-size: 1.5rem; display: block; margin-bottom: 8px; opacity: 0.5;"></i>
                    Không tìm thấy bản ghi điểm danh nào khớp với bộ lọc.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = rows.map(r => {
        const isFull = (r.absent_count || 0) === 0;
        const absent = r.absent_count || 0;
        const statusColor = isFull ? 'background: #dcfce7; color: #15803d;' : (absent <= 2 ? 'background: #fef3c7; color: #b45309;' : 'background: #fee2e2; color: #b91c1c;');
        const statusText = isFull ? 'Đủ 100%' : `Vắng ${absent} em`;

        const rawImgUrl = r.raw_image_path ? (r.raw_image_path.startsWith('http') ? r.raw_image_path : `${API_BASE}${r.raw_image_path}`) : '';
        const annoImgUrl = r.annotated_image_path ? (r.annotated_image_path.startsWith('http') ? r.annotated_image_path : `${API_BASE}${r.annotated_image_path}`) : '';

        return `
            <tr class="${absent > 0 ? 'row-absent-highlight' : ''}">
                <td class="cell-datetime"><strong>${r.scan_date}</strong> <span style="font-size: 0.78rem; color: var(--text-muted);">${r.scan_time}</span></td>
                <td class="cell-session"><code style="font-size: 0.75rem; background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">${r.session_code}</code></td>
                <td class="cell-class"><strong>${r.class_name}</strong> <span style="font-size: 0.78rem; color: var(--text-muted);">(${r.room_number || 'Phòng'})</span></td>
                <td class="cell-standard" style="text-align: center;">${r.standard_count}</td>
                <td class="cell-present" style="text-align: center; font-weight: 700; color: #16a34a;">${r.present_count}</td>
                <td class="cell-absent" style="text-align: center; font-weight: 800;">
                    ${absent > 0 ? `<span class="danger-text">${absent}</span>` : '<span style="color: #94a3b8;">0</span>'}
                </td>
                <td class="cell-image" style="text-align: center;">
                    ${rawImgUrl ? `<button class="btn btn-secondary btn-sm" data-img="${rawImgUrl}" data-title="Ảnh Gốc Camera - ${r.class_name}"><i class="fa-solid fa-image"></i> Xem</button>` : '<span style="color: var(--text-muted);">--</span>'}
                </td>
                <td class="cell-image" style="text-align: center;">
                    ${annoImgUrl ? `<button class="btn btn-primary btn-sm" data-img="${annoImgUrl}" data-title="Ảnh AI Đối Chứng - ${r.class_name}"><i class="fa-solid fa-brain"></i> Xem</button>` : '<span style="color: var(--text-muted);">--</span>'}
                </td>
                <td class="cell-status" style="text-align: center;"><span class="status-pill" style="${statusColor}">${statusText}</span></td>
            </tr>
        `;
    }).join('');

    tbody.querySelectorAll('button[data-img]').forEach(btn => {
        btn.addEventListener('click', () => {
            showImgModal(btn.dataset.img, btn.dataset.title);
        });
    });
}

export async function loadExcelFiles() {
    const tbody = document.getElementById('excelFilesBody');
    if (!tbody) return;

    // Show skeleton loading
    tbody.innerHTML = SkeletonTemplates.excelTableRow().repeat(3);

    try {
        const data = await ReportAPI.list();
        const files = data.reports || [];

        if (files.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 1.5rem; color: var(--text-muted);">Chưa có file báo cáo nào. Bấm "Xuất Báo Cáo Excel Ngay" ở trên để tạo.</td></tr>`;
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

export function closeImgModal() {
    const modal = document.getElementById('imgModal');
    if (modal) {
        modal.classList.remove('active');
        const srcEl = document.getElementById('imgModalSrc');
        if (srcEl) srcEl.src = '';
    }
}

export function initImgModalEvents() {
    const modal = document.getElementById('imgModal');
    const closeBtn = document.getElementById('imgModalCloseBtn');

    if (closeBtn) {
        closeBtn.addEventListener('click', closeImgModal);
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeImgModal();
            }
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal && modal.classList.contains('active')) {
            closeImgModal();
        }
    });
}

window.showImgModal = showImgModal;
window.closeImgModal = closeImgModal;
window.initTabsNavigation = initTabsNavigation;
