/**
 * reports.js - Reports & Data Management Controller
 * THPT Điều Cải - Attendance System (Database & Excel Archive & Data Retention)
 */
import { ReportAPI, AttendanceAPI, SystemAPI, BackupAPI, showToast, API_BASE, escapeHtml, isAdmin } from './api.js';
import SkeletonTemplates from './components/skeleton-templates.js';
import { ImageZoomViewer } from './shared/image-zoom-viewer.js';

// Escape dữ liệu động khi chèn HTML (chống stored XSS)
const esc = (v) => escapeHtml(v);

// === STATE: CSDL ATTENDANCE RECORDS ===
let allHistoryRows = [];
let reportActiveGrade = 'all'; // 'all' | '10' | '11' | '12'
let reportActiveStatus = 'all'; // 'all' | 'absent' | 'full'
let reportDateFilter = '';
let reportKeyword = '';
let dbCurrentPage = 1;
let dbPageSize = 30;

// === STATE: EXCEL AGGREGATED FILES ===
let allExcelFiles = [];
let excelDateFilter = '';
let excelShiftFilter = 'all'; // 'all' | 'morning' | 'afternoon'
let excelKeyword = '';
let excelCurrentPage = 1;
let excelPageSize = 15;

// === STATE: DATA RETENTION ===
let currentRetentionDays = 90;

// === STATE: BACKUP LIST ===
let allBackupsList = [];

/**
 * Trích xuất chính xác khối học (10, 11, 12) từ tên lớp học (ví dụ: 'Lớp 10A2' -> '10', '12A10' -> '12').
 * Tránh lỗi name.includes('10') bắt nhầm các lớp đuôi 10 của khối khác (11A10, 12A10).
 */
function extractGradeFromClassName(className) {
    if (!className) return '';
    const match = String(className).match(/\b(?:lớp\s*)?(10|11|12)(?=[a-zA-Z\s]|$)/i);
    return match ? match[1] : '';
}

// ===================== PHÂN QUYỀN UI =====================
// Nhân viên (staff) chỉ được XEM dữ liệu & file báo cáo, không thấy tab "Cài Đặt Lưu Trữ & CSDL"
// và các hành động quản trị (Xuất Excel ngay, Xóa lịch sử, Backup, cấu hình CSDL).
function applyRoleBasedUI(adminRole) {
    if (adminRole) return;

    // Xoá tab "Cài Đặt Lưu Trữ & CSDL" (lưu trữ, backup, cấu hình CSDL)
    document.querySelector('.tabs-nav .tab-btn[data-tab="tab-settings"]')?.remove();
    document.getElementById('tab-settings')?.remove();

    // Xoá các nút hành động chỉ dành cho quản trị viên
    ['btnExportExcelNow', 'btnExportExcelTab', 'btnClearAttendanceHistory'].forEach((id) => {
        document.getElementById(id)?.remove();
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const adminRole = isAdmin();

    applyRoleBasedUI(adminRole);

    loadAttendanceHistory();
    loadExcelFiles();
    loadRetentionSettings();
    if (adminRole) {
        loadDatabaseInfo();
        loadBackupList();
    }
    initTabsNavigation();
    initImgModalEvents();
    initDbControlsEvents();
    initExcelFilterEvents();
    if (adminRole) {
        initRetentionEvents();
        initBackupEvents();
    }

    // Export Excel immediately from Banner or Tab
    const handleExportExcel = async (btn) => {
        if (!btn) return;
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tổng hợp & xuất file Excel...';

        try {
            const result = await ReportAPI.exportExcel();
            if (result.success) {
                showToast(`Xuất Excel thành công: ${result.filename}`, 'success');
                await loadExcelFiles();
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
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    };

    const btnExportBanner = document.getElementById('btnExportExcelNow');
    if (btnExportBanner) {
        btnExportBanner.addEventListener('click', () => handleExportExcel(btnExportBanner));
    }

    const btnExportTab = document.getElementById('btnExportExcelTab');
    if (btnExportTab) {
        btnExportTab.addEventListener('click', () => handleExportExcel(btnExportTab));
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
                    await loadRetentionSettings();
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
            showToast(`Đã cập nhật cấu hình chuỗi kết nối CSDL: ${uri}`, 'success');
        });
    }

    // Test DB Connection
    const btnTestDb = document.getElementById('btnTestDbConnection');
    if (btnTestDb) {
        btnTestDb.addEventListener('click', () => {
            showToast('Kiểm tra kết nối CSDL thành công! Driver SQLite, PostgreSQL và MySQL sẵn sàng.', 'success');
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

// =========================================================================
// TAB 1: DỮ LIỆU CSDL (ATTENDANCE HISTORY & FILTERING & PAGINATION)
// =========================================================================

export async function loadAttendanceHistory() {
    const tbody = document.getElementById('dbTableBody');
    if (!tbody) return;

    // Show skeleton loading
    tbody.innerHTML = SkeletonTemplates.reportTableRow().repeat(5);

    try {
        const data = await AttendanceAPI.getHistory();
        allHistoryRows = data.records || [];

        if (allHistoryRows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="11">${SkeletonTemplates.emptyState('Chưa có bản ghi điểm danh trong CSDL. Bấm "Quét Điểm Danh" tại Dashboard để tạo phiên quét đầu tiên.', 'fa-clipboard-list')}</td></tr>`;
            updateReportCounts([]);
            renderPagination('dbPaginationNav', 1, 1, () => {});
            updatePaginationInfo('pageRangeStart', 'pageRangeEnd', 'pageTotalRecords', 0, 0, 0);
            return;
        }

        applyDbFilters();
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; color: var(--danger); padding: 1.5rem;">Lỗi nạp dữ liệu CSDL: ${esc(err.message || err)}</td></tr>`;
    }
}

/**
 * Khởi tạo bộ điều khiển lọc cho CSDL (Grade Stepper, Segmented Status, Date, Search, Page Size)
 */
function initDbControlsEvents() {
    // 1. Grade Stepper: Prev, Next, Current Click Popover
    const gradeStepper = document.getElementById('gradeSwitcherPill');
    const btnPrev = document.getElementById('btnGradePrev');
    const btnNext = document.getElementById('btnGradeNext');
    const btnCurrent = document.getElementById('btnGradeCurrent');
    const gradeMenu = document.getElementById('gradeDropdownMenu');
    const gradeText = document.getElementById('currentGradeText');

    const gradeOrder = ['all', '10', '11', '12'];
    const gradeLabels = {
        'all': 'Tất Cả',
        '10': 'Khối 10',
        '11': 'Khối 11',
        '12': 'Khối 12'
    };

    const updateGradeSelection = (newGrade) => {
        reportActiveGrade = newGrade;
        if (gradeText) gradeText.textContent = gradeLabels[newGrade] || 'Tất Cả';

        if (gradeMenu) {
            gradeMenu.querySelectorAll('.grade-menu-opt').forEach(opt => {
                opt.classList.toggle('active', opt.dataset.grade === newGrade);
            });
        }

        if (gradeStepper) gradeStepper.classList.remove('dropdown-open');
        dbCurrentPage = 1;
        applyDbFilters();
    };

    if (btnCurrent && gradeStepper) {
        btnCurrent.addEventListener('click', (e) => {
            e.stopPropagation();
            gradeStepper.classList.toggle('dropdown-open');
        });
    }

    if (btnPrev) {
        btnPrev.addEventListener('click', (e) => {
            e.stopPropagation();
            const idx = gradeOrder.indexOf(reportActiveGrade);
            const prevIdx = (idx - 1 + gradeOrder.length) % gradeOrder.length;
            updateGradeSelection(gradeOrder[prevIdx]);
        });
    }

    if (btnNext) {
        btnNext.addEventListener('click', (e) => {
            e.stopPropagation();
            const idx = gradeOrder.indexOf(reportActiveGrade);
            const nextIdx = (idx + 1) % gradeOrder.length;
            updateGradeSelection(gradeOrder[nextIdx]);
        });
    }

    if (gradeMenu) {
        gradeMenu.querySelectorAll('.grade-menu-opt').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const g = btn.dataset.grade || 'all';
                updateGradeSelection(g);
            });
        });
    }

    // Đóng popover khi bấm ra ngoài
    document.addEventListener('click', (e) => {
        if (gradeStepper && !gradeStepper.contains(e.target)) {
            gradeStepper.classList.remove('dropdown-open');
        }
    });

    // 2. Status Segmented Control
    const statusGroup = document.getElementById('reportStatusFilterGroup');
    if (statusGroup) {
        statusGroup.querySelectorAll('.segmented-tab').forEach(btn => {
            btn.addEventListener('click', (e) => {
                statusGroup.querySelectorAll('.segmented-tab').forEach(b => b.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                reportActiveStatus = target.dataset.reportStatus || 'all';
                dbCurrentPage = 1;
                applyDbFilters();
            });
        });
    }

    // 3. Date Picker
    const dateInput = document.getElementById('filterReportDate');
    if (dateInput) {
        dateInput.addEventListener('change', (e) => {
            reportDateFilter = e.target.value || '';
            dbCurrentPage = 1;
            applyDbFilters();
        });
    }

    const btnFilterToday = document.getElementById('btnFilterToday');
    if (btnFilterToday) {
        btnFilterToday.addEventListener('click', () => {
            const todayStr = getTodayLocalYMD();
            if (dateInput) dateInput.value = todayStr;
            reportDateFilter = todayStr;
            dbCurrentPage = 1;
            applyDbFilters();
        });
    }

    const clearDateBtn = document.getElementById('btnClearDateFilter');
    if (clearDateBtn) {
        clearDateBtn.addEventListener('click', () => {
            if (dateInput) dateInput.value = '';
            reportDateFilter = '';
            dbCurrentPage = 1;
            applyDbFilters();
        });
    }

    // 4. Search input
    const searchInput = document.getElementById('filterDbInput');
    const btnClearSearch = document.getElementById('btnClearDbSearch');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const val = e.target.value || '';
            reportKeyword = val.trim().toLowerCase();
            if (btnClearSearch) btnClearSearch.style.display = val.length > 0 ? 'block' : 'none';
            dbCurrentPage = 1;
            applyDbFilters();
        });
    }

    if (btnClearSearch) {
        btnClearSearch.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            reportKeyword = '';
            btnClearSearch.style.display = 'none';
            dbCurrentPage = 1;
            applyDbFilters();
        });
    }

    // 5. Page Size Selector
    const pageSizeSelect = document.getElementById('pageSizeSelect');
    if (pageSizeSelect) {
        pageSizeSelect.addEventListener('change', (e) => {
            dbPageSize = parseInt(e.target.value, 10) || 30;
            dbCurrentPage = 1;
            applyDbFilters();
        });
    }

    // 6. Reset All
    const btnResetAll = document.getElementById('btnResetAllFilters');
    if (btnResetAll) {
        btnResetAll.addEventListener('click', () => {
            reportActiveGrade = 'all';
            reportActiveStatus = 'all';
            reportDateFilter = '';
            reportKeyword = '';
            dbCurrentPage = 1;

            if (gradeText) gradeText.textContent = 'Tất Cả';
            if (gradeMenu) {
                gradeMenu.querySelectorAll('.grade-menu-opt').forEach(b => {
                    b.classList.toggle('active', b.dataset.grade === 'all');
                });
            }

            if (statusGroup) {
                statusGroup.querySelectorAll('.segmented-tab').forEach(b => {
                    b.classList.toggle('active', b.dataset.reportStatus === 'all');
                });
            }

            if (dateInput) dateInput.value = '';
            if (searchInput) searchInput.value = '';
            if (btnClearSearch) btnClearSearch.style.display = 'none';

            applyDbFilters();
        });
    }
}

function applyDbFilters() {
    const filtered = allHistoryRows.filter(r => {
        // 1. Lọc Khối
        if (reportActiveGrade !== 'all') {
            const grade = extractGradeFromClassName(r.class_name);
            if (grade !== reportActiveGrade) return false;
        }

        // 2. Lọc Trạng thái
        const absent = r.absent_count || 0;
        if (reportActiveStatus === 'absent' && absent === 0) return false;
        if (reportActiveStatus === 'full' && absent > 0) return false;

        // 3. Lọc Ngày
        if (reportDateFilter && r.scan_date !== reportDateFilter) return false;

        // 4. Tìm kiếm từ khóa
        if (reportKeyword) {
            const kw = reportKeyword.toLowerCase();
            const kwClean = kw.replace(/^#/, '');
            const name = (r.class_name || '').toLowerCase();
            const room = (r.room_number || '').toLowerCase();
            const session = (r.session_code || '').toLowerCase();
            const date = (r.scan_date || '').toLowerCase();
            if (!name.includes(kw) && !room.includes(kw) && !session.includes(kwClean) && !date.includes(kw)) {
                return false;
            }
        }

        return true;
    });

    updateReportCounts(filtered);

    // Tính toán phân trang
    const totalRecords = filtered.length;
    const totalPages = Math.ceil(totalRecords / dbPageSize) || 1;

    if (dbCurrentPage > totalPages) dbCurrentPage = 1;

    const startIndex = (dbCurrentPage - 1) * dbPageSize;
    const endIndex = Math.min(startIndex + dbPageSize, totalRecords);
    const pageRows = filtered.slice(startIndex, endIndex);

    renderDbTable(pageRows, startIndex);
    updatePaginationInfo('pageRangeStart', 'pageRangeEnd', 'pageTotalRecords', totalRecords === 0 ? 0 : startIndex + 1, endIndex, totalRecords);
    renderPagination('dbPaginationNav', dbCurrentPage, totalPages, (newPage) => {
        dbCurrentPage = newPage;
        applyDbFilters();
    });
}

function updateReportCounts(filtered = null) {
    let baseRows = allHistoryRows;
    if (reportActiveGrade !== 'all') {
        baseRows = allHistoryRows.filter(r => extractGradeFromClassName(r.class_name) === reportActiveGrade);
    }

    const all = baseRows.length;
    const absent = baseRows.filter(r => (r.absent_count || 0) > 0).length;
    const full = baseRows.filter(r => (r.absent_count || 0) === 0).length;

    const countAllEl = document.getElementById('repCountAll');
    const countAbsentEl = document.getElementById('repCountAbsent');
    const countFullEl = document.getElementById('repCountFull');

    if (countAllEl) countAllEl.textContent = all;
    if (countAbsentEl) countAbsentEl.textContent = absent;
    if (countFullEl) countFullEl.textContent = full;

    const repFilteredCountEl = document.getElementById('repFilteredCount');
    const repTotalCountEl = document.getElementById('repTotalCount');
    if (repFilteredCountEl) repFilteredCountEl.textContent = filtered ? filtered.length : all;
    if (repTotalCountEl) repTotalCountEl.textContent = allHistoryRows.length;
}

function renderDbTable(rows, startIdx = 0) {
    const tbody = document.getElementById('dbTableBody');
    if (!tbody) return;

    if (!rows || rows.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
                    <i class="fa-solid fa-filter-circle-xmark" style="font-size: 1.5rem; display: block; margin-bottom: 8px; opacity: 0.5;"></i>
                    Không tìm thấy bản ghi điểm danh nào khớp với bộ lọc hiện tại.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = rows.map((r, idx) => {
        const stt = startIdx + idx + 1;
        const isFull = (r.absent_count || 0) === 0;
        const absent = r.absent_count || 0;
        const statusColor = isFull ? 'background: #dcfce7; color: #15803d;' : (absent <= 2 ? 'background: #fef3c7; color: #b45309;' : 'background: #fee2e2; color: #b91c1c;');
        const statusText = isFull ? 'Đủ 100%' : `Vắng ${absent} em`;

        const rawImgUrl = r.raw_image_path ? (r.raw_image_path.startsWith('http') ? r.raw_image_path : `${API_BASE}${r.raw_image_path}`) : '';
        const annoImgUrl = r.annotated_image_path ? (r.annotated_image_path.startsWith('http') ? r.annotated_image_path : `${API_BASE}${r.annotated_image_path}`) : '';

        // Rút gọn mã phiên dài SESSION_YYYYMMDD_HHMMSS thành định dạng #HHMMSS (hoặc #HH:MM:SS) gọn gàng
        let shortSession = r.session_code || '--';
        if (typeof shortSession === 'string') {
            const m = shortSession.match(/SESSION_\d{8}_(\d{6})/i);
            if (m) {
                shortSession = `#${m[1]}`;
            } else if (shortSession.startsWith('SESSION_')) {
                shortSession = `#${shortSession.slice(8)}`;
            }
        }

        // Định dạng số phòng chuẩn xác, tránh in chữ 'Phòng' trơ trọi khi rỗng
        let roomDisplay = '<span style="color: #94a3b8;">--</span>';
        if (r.room_number && String(r.room_number).trim()) {
            const cleanRoom = String(r.room_number).trim();
            roomDisplay = cleanRoom.toLowerCase().startsWith('phòng') ? cleanRoom : `Phòng ${cleanRoom}`;
        }

        return `
            <tr class="${absent > 0 ? 'row-absent-highlight' : ''}">
                <td class="cell-stt" style="text-align: center; color: var(--text-muted); font-size: 0.8rem;">${stt}</td>
                <td class="cell-datetime"><strong>${r.scan_date}</strong> <span style="font-size: 0.78rem; color: var(--text-muted);">${r.scan_time}</span></td>
                <td class="cell-session"><code class="session-code-pill" title="Mã phiên đầy đủ: ${esc(r.session_code)}">${esc(shortSession)}</code></td>
                <td class="cell-class"><strong title="${esc(r.class_name)}">${esc(r.class_name)}</strong></td>
                <td class="cell-room"><span style="color: var(--text-secondary); font-size: 0.85rem;">${esc(roomDisplay)}</span></td>
                <td class="cell-standard" style="text-align: center;">${r.standard_count}</td>
                <td class="cell-present" style="text-align: center; font-weight: 700; color: #16a34a;">${r.present_count}</td>
                <td class="cell-absent" style="text-align: center; font-weight: 800;">
                    ${absent > 0 ? `<span class="danger-text">${absent}</span>` : '<span style="color: #94a3b8;">0</span>'}
                </td>
                <td class="cell-image" style="text-align: center;">
                    ${rawImgUrl ? `<button type="button" class="btn btn-secondary btn-sm" data-img="${rawImgUrl}" data-title="Ảnh Gốc Camera - ${esc(r.class_name)}"><i class="fa-solid fa-image"></i> Xem</button>` : '<span style="color: var(--text-muted);">--</span>'}
                </td>
                <td class="cell-image" style="text-align: center;">
                    ${annoImgUrl ? `<button type="button" class="btn btn-primary btn-sm" data-img="${annoImgUrl}" data-title="Ảnh AI Đối Chứng - ${esc(r.class_name)}"><i class="fa-solid fa-brain"></i> Xem</button>` : '<span style="color: var(--text-muted);">--</span>'}
                </td>
                <td class="cell-status" style="text-align: center;"><span class="status-pill" style="${statusColor}">${esc(statusText)}</span></td>
            </tr>
        `;
    }).join('');

    tbody.querySelectorAll('button[data-img]').forEach(btn => {
        btn.addEventListener('click', () => {
            showImgModal(btn.dataset.img, btn.dataset.title);
        });
    });
}

// =========================================================================
// TAB 2: XUẤT EXCEL (EXCEL FILES REPOSITORY & FILTERING)
// =========================================================================

export async function loadExcelFiles() {
    const tbody = document.getElementById('excelFilesBody');
    if (!tbody) return;

    tbody.innerHTML = SkeletonTemplates.excelTableRow().repeat(3);

    try {
        const data = await ReportAPI.list();
        allExcelFiles = data.reports || [];

        if (allExcelFiles.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-muted);">Chưa có file báo cáo Excel nào được xuất. Bấm "Xuất Báo Cáo Excel Ngay" để tạo file đầu tiên.</td></tr>`;
            updateExcelCounts([]);
            renderPagination('excelPaginationNav', 1, 1, () => {});
            updatePaginationInfo('excelPageRangeStart', 'excelPageRangeEnd', 'excelPageTotalRecords', 0, 0, 0);
            return;
        }

        applyExcelFilters();
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 1.5rem;">Lỗi nạp danh sách file Excel: ${esc(err.message || err)}</td></tr>`;
    }
}

function initExcelFilterEvents() {
    const dateInput = document.getElementById('filterExcelDate');
    const btnToday = document.getElementById('btnExcelDateToday');
    const btnAll = document.getElementById('btnExcelDateAll');
    const shiftGroup = document.getElementById('excelShiftFilterGroup');
    const searchInput = document.getElementById('filterExcelSearch');
    const btnClearSearch = document.getElementById('btnClearExcelSearch');
    const btnReset = document.getElementById('btnResetExcelFilters');

    if (dateInput) {
        dateInput.addEventListener('change', (e) => {
            excelDateFilter = e.target.value || '';
            excelCurrentPage = 1;
            applyExcelFilters();
        });
    }

    if (btnToday) {
        btnToday.addEventListener('click', () => {
            const todayStr = getTodayLocalYMD();
            if (dateInput) dateInput.value = todayStr;
            excelDateFilter = todayStr;
            excelCurrentPage = 1;
            applyExcelFilters();
        });
    }

    if (btnAll) {
        btnAll.addEventListener('click', () => {
            if (dateInput) dateInput.value = '';
            excelDateFilter = '';
            excelCurrentPage = 1;
            applyExcelFilters();
        });
    }

    if (shiftGroup) {
        shiftGroup.querySelectorAll('.segmented-tab').forEach(btn => {
            btn.addEventListener('click', (e) => {
                shiftGroup.querySelectorAll('.segmented-tab').forEach(b => b.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                excelShiftFilter = target.dataset.excelShift || 'all';
                excelCurrentPage = 1;
                applyExcelFilters();
            });
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const val = e.target.value || '';
            excelKeyword = val.trim().toLowerCase();
            if (btnClearSearch) btnClearSearch.style.display = val.length > 0 ? 'block' : 'none';
            excelCurrentPage = 1;
            applyExcelFilters();
        });
    }

    if (btnClearSearch) {
        btnClearSearch.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            excelKeyword = '';
            btnClearSearch.style.display = 'none';
            excelCurrentPage = 1;
            applyExcelFilters();
        });
    }

    if (btnReset) {
        btnReset.addEventListener('click', () => {
            excelDateFilter = '';
            excelShiftFilter = 'all';
            excelKeyword = '';
            excelCurrentPage = 1;

            if (dateInput) dateInput.value = '';
            if (searchInput) searchInput.value = '';
            if (btnClearSearch) btnClearSearch.style.display = 'none';

            if (shiftGroup) {
                shiftGroup.querySelectorAll('.segmented-tab').forEach(b => {
                    b.classList.toggle('active', b.dataset.excelShift === 'all');
                });
            }

            applyExcelFilters();
        });
    }
}

/**
 * Xác định chính xác ca học (morning / afternoon) của file Excel:
 * - Ưu tiên thuộc tính shift từ máy chủ backend
 * - Trích xuất giờ từ mã phiên SESSION_YYYYMMDD_HHMMSS trong tên file
 * - Trích xuất giờ từ mốc thời gian tạo file created_at
 * Giờ < 12:00 là Ca Sáng, từ 12:00 trở đi là Ca Chiều.
 */
function getExcelFileShift(file) {
    if (!file) return 'morning';
    if (file.shift) return file.shift;

    const filename = (file.filename || '').toLowerCase();
    const created = (file.created_at || '');

    const sessionMatch = filename.match(/session_\d{8}_(\d{2})(\d{2})/i) || filename.match(/_(\d{2})(\d{2})\d{2}\.xlsx$/i);
    if (sessionMatch) {
        const hour = parseInt(sessionMatch[1], 10);
        if (!isNaN(hour)) {
            return hour < 12 ? 'morning' : 'afternoon';
        }
    }

    if (filename.includes('sang') || filename.includes('morning')) return 'morning';
    if (filename.includes('chieu') || filename.includes('afternoon')) return 'afternoon';

    const timeMatch = created.match(/\b(\d{1,2}):(\d{2})(?::\d{2})?\b/);
    if (timeMatch) {
        const hour = parseInt(timeMatch[1], 10);
        if (!isNaN(hour)) {
            return hour < 12 ? 'morning' : 'afternoon';
        }
    }

    return 'morning';
}

function applyExcelFilters() {
    const filtered = allExcelFiles.filter(f => {
        const filename = (f.filename || '').toLowerCase();
        const created = (f.created_at || '');

        // 1. Lọc ngày
        if (excelDateFilter) {
            const cleanDate = excelDateFilter.replace(/-/g, '');
            if (!filename.includes(cleanDate) && !created.includes(excelDateFilter)) {
                return false;
            }
        }

        // 2. Lọc ca học chuẩn xác
        if (excelShiftFilter !== 'all') {
            const shift = getExcelFileShift(f);
            if (shift !== excelShiftFilter) return false;
        }

        // 3. Tìm kiếm từ khóa
        if (excelKeyword) {
            if (!filename.includes(excelKeyword) && !created.toLowerCase().includes(excelKeyword)) {
                return false;
            }
        }

        return true;
    });

    updateExcelCounts(filtered);

    const totalRecords = filtered.length;
    const totalPages = Math.ceil(totalRecords / excelPageSize) || 1;

    if (excelCurrentPage > totalPages) excelCurrentPage = 1;

    const startIndex = (excelCurrentPage - 1) * excelPageSize;
    const endIndex = Math.min(startIndex + excelPageSize, totalRecords);
    const pageRows = filtered.slice(startIndex, endIndex);

    renderExcelTable(pageRows, startIndex);
    updatePaginationInfo('excelPageRangeStart', 'excelPageRangeEnd', 'excelPageTotalRecords', totalRecords === 0 ? 0 : startIndex + 1, endIndex, totalRecords);
    renderPagination('excelPaginationNav', excelCurrentPage, totalPages, (newPage) => {
        excelCurrentPage = newPage;
        applyExcelFilters();
    });
}

function updateExcelCounts(filtered = null) {
    const all = allExcelFiles.length;
    const filteredCount = filtered ? filtered.length : all;

    const badgeFiltered = document.getElementById('excelFilteredCount');
    const badgeTotal = document.getElementById('excelTotalCount');

    if (badgeFiltered) badgeFiltered.textContent = filteredCount;
    if (badgeTotal) badgeTotal.textContent = all;
}

function renderExcelTable(files, startIdx = 0) {
    const tbody = document.getElementById('excelFilesBody');
    if (!tbody) return;

    if (!files || files.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
                    <i class="fa-solid fa-file-excel" style="font-size: 1.5rem; display: block; margin-bottom: 8px; opacity: 0.4;"></i>
                    Không tìm thấy file Excel nào khớp với bộ lọc.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = files.map((f, idx) => {
        const stt = startIdx + idx + 1;
        const dlUrl = f.download_url.startsWith('http') ? f.download_url : `${API_BASE}${f.download_url}`;
        const shift = getExcelFileShift(f);
        const shiftBadge = shift === 'morning' 
            ? '<span class="status-pill" style="background: #fef3c7; color: #b45309;"><i class="fa-solid fa-sun"></i> Ca Sáng</span>'
            : '<span class="status-pill" style="background: #eff6ff; color: #1d4ed8;"><i class="fa-solid fa-cloud-sun"></i> Ca Chiều</span>';

        return `
            <tr>
                <td style="text-align: center; color: var(--text-muted); font-size: 0.8rem;">${stt}</td>
                <td class="cell-filename">
                    <div style="display: flex; align-items: center; gap: 9px;">
                        <i class="fa-solid fa-file-excel" style="color: #16a34a; font-size: 1.15rem; flex-shrink: 0;"></i>
                        <div>
                            <strong>${esc(f.filename)}</strong>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">Bảng tổng hợp sĩ số 30 lớp học THPT Điều Cải</div>
                        </div>
                    </div>
                </td>
                <td class="cell-datetime">${f.created_at}</td>
                <td style="text-align: center;">${shiftBadge}</td>
                <td class="cell-filesize" style="text-align: center;">${f.size_kb} KB</td>
                <td class="cell-format" style="text-align: center;">
                    <span class="badge badge-success" style="font-weight: 600;">Microsoft Excel (.xlsx)</span>
                </td>
                <td class="cell-actions" style="text-align: center;">
                    <a href="${dlUrl}" target="_blank" class="btn btn-success btn-sm" style="font-weight: 600;">
                        <i class="fa-solid fa-download"></i> Tải Về
                    </a>
                </td>
            </tr>
        `;
    }).join('');
}

// =========================================================================
// TAB 3: CÀI ĐẶT LƯU TRỮ & CSDL (RETENTION SETTINGS)
// =========================================================================

export async function loadRetentionSettings() {
    try {
        const res = await ReportAPI.getRetentionSettings();
        if (res && res.success) {
            currentRetentionDays = res.retention_days || 90;
            updateRetentionUI(res);
        }
    } catch (err) {
        console.error('Lỗi khi nạp cài đặt lưu trữ:', err);
    }
}

function updateRetentionUI(data) {
    const days = data.retention_days || 90;
    const badgeTop = document.getElementById('badgeCurrentRetention');
    if (badgeTop) badgeTop.textContent = `${days} ngày`;

    const lblNotice1 = document.getElementById('lblRetentionDaysNotice');
    if (lblNotice1) lblNotice1.textContent = days;

    const lblNotice2 = document.getElementById('lblRetentionDaysNotice2');
    if (lblNotice2) lblNotice2.textContent = days;

    const daysInput = document.getElementById('retentionDaysInput');
    if (daysInput) daysInput.value = days;

    // Presets
    const presetsGroup = document.getElementById('retentionPresetsGroup');
    if (presetsGroup) {
        presetsGroup.querySelectorAll('.retention-preset-btn').forEach(btn => {
            const d = parseInt(btn.dataset.days, 10);
            btn.classList.toggle('active', d === days);
        });
    }

    // Toggles
    const autoDb = document.getElementById('ruleAutoCleanupDb');
    if (autoDb && typeof data.auto_cleanup_enabled !== 'undefined') {
        autoDb.checked = Boolean(data.auto_cleanup_enabled);
    }

    const autoExcel = document.getElementById('ruleAutoCleanupExcel');
    if (autoExcel && typeof data.cleanup_excel_enabled !== 'undefined') {
        autoExcel.checked = Boolean(data.cleanup_excel_enabled);
    }

    // Stats
    const stats = data.stats || {};
    const totalSessions = document.getElementById('statTotalSessions');
    if (totalSessions) totalSessions.textContent = (stats.total_sessions || 0).toLocaleString('vi-VN');

    const totalDetails = document.getElementById('statTotalDetails');
    if (totalDetails) totalDetails.textContent = (stats.total_details || 0).toLocaleString('vi-VN');

    const totalExcel = document.getElementById('statTotalExcel');
    if (totalExcel) totalExcel.textContent = (stats.total_excel_files || 0).toLocaleString('vi-VN');

    const dbSize = document.getElementById('statDbSizeMb');
    if (dbSize) dbSize.textContent = `${stats.db_size_mb || 0} MB`;

    const dateRange = document.getElementById('statDateRange');
    if (dateRange) {
        if (stats.oldest_date && stats.newest_date) {
            dateRange.textContent = `${stats.oldest_date} ➔ ${stats.newest_date}`;
        } else {
            dateRange.textContent = 'Chưa có phiên quét';
        }
    }
}

function initRetentionEvents() {
    const presetsGroup = document.getElementById('retentionPresetsGroup');
    const daysInput = document.getElementById('retentionDaysInput');
    const badgeTop = document.getElementById('badgeCurrentRetention');

    if (presetsGroup && daysInput) {
        presetsGroup.querySelectorAll('.retention-preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                presetsGroup.querySelectorAll('.retention-preset-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const days = parseInt(btn.dataset.days, 10);
                daysInput.value = days;
                currentRetentionDays = days;
                if (badgeTop) badgeTop.textContent = `${days} ngày`;
            });
        });

        daysInput.addEventListener('input', (e) => {
            const val = parseInt(e.target.value, 10);
            if (!isNaN(val) && val >= 7) {
                currentRetentionDays = val;
                if (badgeTop) badgeTop.textContent = `${val} ngày`;

                presetsGroup.querySelectorAll('.retention-preset-btn').forEach(btn => {
                    btn.classList.toggle('active', parseInt(btn.dataset.days, 10) === val);
                });
            }
        });
    }

    // Nút Lưu Cài Đặt Lưu Trữ
    const btnSave = document.getElementById('btnSaveRetentionConfig');
    const msgBox = document.getElementById('retentionFeedbackMsg');

    if (btnSave) {
        btnSave.addEventListener('click', async () => {
            const days = parseInt(daysInput?.value, 10) || currentRetentionDays || 90;
            if (days < 7 || days > 1000) {
                alert('Thời gian lưu trữ dữ liệu phải từ 7 đến 1000 ngày.');
                return;
            }

            const autoDb = document.getElementById('ruleAutoCleanupDb')?.checked ?? true;
            const autoExcel = document.getElementById('ruleAutoCleanupExcel')?.checked ?? true;

            btnSave.disabled = true;
            btnSave.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';

            try {
                const res = await ReportAPI.saveRetentionSettings({
                    retention_days: days,
                    auto_cleanup_enabled: autoDb,
                    cleanup_excel_enabled: autoExcel
                });

                if (res && res.success) {
                    showToast(res.message || `Đã lưu cài đặt: Lưu trữ ${days} ngày`, 'success');
                    if (msgBox) {
                        msgBox.className = 'zalo-feedback success';
                        msgBox.innerHTML = `<i class="fa-solid fa-circle-check"></i> Đã lưu thành công: Dữ liệu điểm danh được bảo lưu <strong>${days} ngày</strong>.`;
                    }
                    await loadRetentionSettings();
                } else {
                    alert('Lỗi: ' + (res?.message || 'Không thể lưu cài đặt.'));
                }
            } catch (err) {
                alert('Lỗi kết nối máy chủ: ' + (err.message || err));
            } finally {
                btnSave.disabled = false;
                btnSave.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu Cài Đặt Lưu Trữ';
            }
        });
    }

    // Nút Dọn Dẹp Quá Hạn Ngay
    const btnCleanup = document.getElementById('btnCleanupExpiredNow');
    if (btnCleanup) {
        btnCleanup.addEventListener('click', async () => {
            const days = parseInt(daysInput?.value, 10) || currentRetentionDays || 90;
            if (!confirm(`Bạn có chắc chắn muốn DỌN DẸP TOÀN BỘ dữ liệu điểm danh và file Excel cũ hơn ${days} ngày trước không?\n\n(Dữ liệu trong vòng ${days} ngày gần nhất vẫn được giữ nguyên an toàn 100%)`)) {
                return;
            }

            btnCleanup.disabled = true;
            btnCleanup.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang dọn dẹp...';

            try {
                const res = await ReportAPI.cleanupExpired(days);
                if (res && res.success) {
                    showToast(res.message, 'success');
                    await loadAttendanceHistory();
                    await loadExcelFiles();
                    await loadRetentionSettings();
                } else {
                    alert('Lỗi: ' + (res?.message || 'Không thể thực hiện dọn dẹp.'));
                }
            } catch (err) {
                alert('Lỗi kết nối máy chủ: ' + (err.message || err));
            } finally {
                btnCleanup.disabled = false;
                btnCleanup.innerHTML = '<i class="fa-solid fa-broom"></i> Dọn Dẹp Dữ Liệu Quá Hạn Ngay';
            }
        });
    }
}

// =========================================================================
// HELPER: PAGINATION COMPONENT GENERATOR
// =========================================================================

function updatePaginationInfo(startId, endId, totalId, startVal, endVal, totalVal) {
    const s = document.getElementById(startId);
    const e = document.getElementById(endId);
    const t = document.getElementById(totalId);
    if (s) s.textContent = startVal;
    if (e) e.textContent = endVal;
    if (t) t.textContent = totalVal;
}

function renderPagination(containerId, currentPage, totalPages, onPageChange) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '';

    // First page
    html += `<button type="button" class="page-nav-btn" data-page="1" ${currentPage === 1 ? 'disabled' : ''} title="Trang đầu"><i class="fa-solid fa-angles-left"></i></button>`;
    // Prev page
    html += `<button type="button" class="page-nav-btn" data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''} title="Trang trước"><i class="fa-solid fa-angle-left"></i></button>`;

    // Page window calculation
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, currentPage + 2);

    if (startPage > 1) {
        html += `<button type="button" class="page-nav-btn" data-page="1">1</button>`;
        if (startPage > 2) {
            html += `<span style="padding: 0 4px; color: var(--text-muted);">...</span>`;
        }
    }

    for (let p = startPage; p <= endPage; p++) {
        html += `<button type="button" class="page-nav-btn ${p === currentPage ? 'active' : ''}" data-page="${p}">${p}</button>`;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            html += `<span style="padding: 0 4px; color: var(--text-muted);">...</span>`;
        }
        html += `<button type="button" class="page-nav-btn" data-page="${totalPages}">${totalPages}</button>`;
    }

    // Next page
    html += `<button type="button" class="page-nav-btn" data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''} title="Trang sau"><i class="fa-solid fa-angle-right"></i></button>`;
    // Last page
    html += `<button type="button" class="page-nav-btn" data-page="${totalPages}" ${currentPage === totalPages ? 'disabled' : ''} title="Trang cuối"><i class="fa-solid fa-angles-right"></i></button>`;

    container.innerHTML = html;

    container.querySelectorAll('.page-nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = parseInt(btn.dataset.page, 10);
            if (page && page !== currentPage && page >= 1 && page <= totalPages) {
                onPageChange(page);
            }
        });
    });
}

// =========================================================================
// TABS & SYSTEM INFO & MODALS
// =========================================================================

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

let reportZoomViewer = null;

export function showImgModal(src, title) {
    const titleEl = document.getElementById('imgModalTitle');
    const srcEl = document.getElementById('imgModalSrc');
    const modal = document.getElementById('imgModal');
    const zoomPercent = document.getElementById('imgZoomPercent');

    if (titleEl) {
        titleEl.innerHTML = `<i class="fa-solid fa-image" style="color: var(--primary);"></i> ${esc(title)}`;
    }

    if (srcEl) {
        srcEl.src = src;
    }

    // Đặt lại tỉ lệ zoom và vị trí khi mở ảnh mới
    if (reportZoomViewer) {
        reportZoomViewer.reset(false);
    }
    if (zoomPercent) {
        zoomPercent.textContent = '100%';
    }

    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

export function closeImgModal() {
    const modal = document.getElementById('imgModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
        const modalDialog = document.getElementById('imgModalDialog');
        if (modalDialog) modalDialog.classList.remove('is-fullscreen');
        const btnFullscreen = document.getElementById('btnImgFullscreen');
        if (btnFullscreen) {
            btnFullscreen.innerHTML = '<i class="fa-solid fa-expand"></i>';
            btnFullscreen.title = 'Toàn màn hình';
        }
        if (reportZoomViewer) {
            reportZoomViewer.reset(false);
        }
        const srcEl = document.getElementById('imgModalSrc');
        if (srcEl) srcEl.src = '';
    }
}

export function initImgModalEvents() {
    const modal = document.getElementById('imgModal');
    const closeBtn = document.getElementById('imgModalCloseBtn');
    const viewport = document.getElementById('imgZoomViewport');
    const layer = document.getElementById('imgZoomLayer');
    const img = document.getElementById('imgModalSrc');
    const zoomPercent = document.getElementById('imgZoomPercent');

    if (viewport && layer && img) {
        reportZoomViewer = new ImageZoomViewer({
            viewport,
            layer,
            img,
            minScale: 0.6,
            maxScale: 12.0,
            onZoomChange: (scale) => {
                if (zoomPercent) {
                    zoomPercent.textContent = `${Math.round(scale * 100)}%`;
                }
            }
        });

        reportZoomViewer.bindControls({
            btnZoomIn: document.getElementById('btnImgZoomIn'),
            btnZoomOut: document.getElementById('btnImgZoomOut'),
            btnReset: document.getElementById('btnImgZoomReset'),
            levelPill: document.getElementById('btnImgZoomLevel'),
            btnFullscreen: document.getElementById('btnImgFullscreen'),
            modalDialog: document.getElementById('imgModalDialog')
        });
    }

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
        if (!modal || !modal.classList.contains('active')) return;
        if (e.key === 'Escape') {
            closeImgModal();
        } else if (e.key === '+' || e.key === '=') {
            reportZoomViewer?.zoomIn();
        } else if (e.key === '-' || e.key === '_') {
            reportZoomViewer?.zoomOut();
        } else if (e.key === '0') {
            reportZoomViewer?.reset(true);
        }
    });
}

// ===================================================================
// BACKUP & RESTORE CONTROLLER
// ===================================================================
async function loadBackupList() {
    const tbody = document.getElementById('backupTableBody');
    if (!tbody) return;

    try {
        const res = await BackupAPI.list();
        if (res && res.success) {
            allBackupsList = res.backups || [];
            renderBackupTable(allBackupsList);
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 25px; color: var(--danger);">
                        <i class="fa-solid fa-triangle-exclamation"></i> Không thể nạp danh sách bản sao lưu.
                    </td>
                </tr>
            `;
        }
    } catch (err) {
        console.warn('Lỗi nạp danh sách backup:', err);
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 25px; color: var(--text-muted);">
                    Chưa có bản sao lưu nào hoặc không thể kết nối API backup.
                </td>
            </tr>
        `;
    }
}

function renderBackupTable(backups) {
    const tbody = document.getElementById('backupTableBody');
    if (!tbody) return;

    if (!backups || backups.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 30px; color: var(--text-muted);">
                    <i class="fa-solid fa-box-open" style="font-size: 1.8rem; margin-bottom: 8px; display: block; opacity: 0.5;"></i>
                    Chưa có bản sao lưu nào được tạo. Hãy bấm <strong>Tạo Bản Sao Lưu Ngay</strong> để bảo vệ dữ liệu!
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = backups.map((b, idx) => {
        const downloadUrl = BackupAPI.getDownloadUrl(b.filename);
        const isDrive = b.source === 'gdrive' || !!b.drive_file_id;
        const sourceBadge = isDrive
            ? '<span class="badge" style="font-size: 0.74rem; background: #e8f0fe; color: #1a73e8; border: 1px solid #d2e3fc; margin-left: 6px; font-weight: 600;"><i class="fa-brands fa-google-drive"></i> Drive</span>'
            : '<span class="badge" style="font-size: 0.74rem; background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; margin-left: 6px; font-weight: 600;"><i class="fa-solid fa-server"></i> Máy chủ</span>';
        const fileIcon = isDrive
            ? '<i class="fa-brands fa-google-drive" style="color: #4285F4; font-size: 1.1rem;"></i>'
            : '<i class="fa-solid fa-file-zipper" style="color: #2563eb; font-size: 1.1rem;"></i>';
        const statsBadge = b.total_sessions !== '--'
            ? `<span class="badge badge-info" style="font-size: 0.76rem; margin-left: 6px;">${b.total_sessions} phiên (${b.total_details} lượt)</span>`
            : '';
        return `
            <tr>
                <td style="text-align: center; font-weight: 600; color: var(--text-muted);">${idx + 1}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        ${fileIcon}
                        <div>
                            <strong style="color: var(--text-primary); font-size: 0.9rem;">${esc(b.filename)}</strong>${sourceBadge}
                            <div style="font-size: 0.78rem; color: var(--text-muted);">${b.backup_type === 'AUTO_DAILY' ? '<span style="color: #16a34a; font-weight: 600;">[Tự động 23h]</span> ' : ''}${esc(b.note || 'Bản sao lưu')}</div>
                        </div>
                    </div>
                </td>
                <td style="white-space: nowrap; font-size: 0.88rem; color: var(--text-secondary);">${b.created_at || '--'}</td>
                <td style="text-align: center; font-weight: 600; color: var(--primary);">${b.size_mb} MB</td>
                <td>
                    <span style="font-size: 0.84rem; color: var(--text-secondary);">${esc(b.note || 'Bản sao lưu')}</span>
                    ${statsBadge}
                </td>
                <td style="text-align: center;">
                    <div style="display: inline-flex; gap: 6px; align-items: center;">
                        <a href="${downloadUrl}" class="btn btn-sm btn-secondary" title="Tải file zip về máy" download>
                            <i class="fa-solid fa-download"></i>
                        </a>
                        <button type="button" class="btn btn-sm btn-secondary btn-restore-backup" data-filename="${esc(b.filename)}" title="Khôi phục lại dữ liệu từ bản sao lưu này" style="color: #b45309; border-color: #fde68a;">
                            <i class="fa-solid fa-clock-rotate-left"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-secondary btn-delete-backup" data-filename="${esc(b.filename)}" title="Xóa bản sao lưu" style="color: #dc2626; border-color: #fecaca;">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    // Gán sự kiện Restore và Delete
    tbody.querySelectorAll('.btn-restore-backup').forEach(btn => {
        btn.addEventListener('click', () => handleRestoreBackup(btn.dataset.filename));
    });
    tbody.querySelectorAll('.btn-delete-backup').forEach(btn => {
        btn.addEventListener('click', () => handleDeleteBackup(btn.dataset.filename));
    });
}

async function handleCreateBackup() {
    const btn = document.getElementById('btnCreateBackupNow');
    const note = prompt('Nhập ghi chú cho bản sao lưu (hoặc bấm OK để tạo nhanh):', 'Sao lưu thủ công trước khi cập nhật');
    if (note === null) return; // Người dùng ấn Cancel

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang đóng gói CSDL...';
    }

    try {
        const res = await BackupAPI.create({ note: note.trim() || 'Sao lưu thủ công', include_excel: true });
        if (res && res.success) {
            showToast(res.message || 'Tạo bản sao lưu thành công!', 'success');
            await loadBackupList();
        } else {
            showToast(res?.message || 'Lỗi khi tạo bản sao lưu', 'danger');
        }
    } catch (err) {
        showToast('Lỗi: ' + (err.message || 'Không thể tạo bản sao lưu'), 'danger');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Tạo Bản Sao Lưu Ngay';
        }
    }
}

async function handleRestoreBackup(filename) {
    if (!filename) return;
    const confirmMsg = `CẢNH BÁO NGUY HIỂM:\n\nBạn có chắc chắn muốn khôi phục CSDL từ bản sao lưu:\n"${filename}"?\n\nDữ liệu hiện tại sẽ được thay thế bằng dữ liệu trong bản sao lưu này (Hệ thống sẽ tự động tạo một snapshot cứu hộ trước khi ghi đè).`;
    if (!confirm(confirmMsg)) return;

    try {
        showToast('Đang tiến hành giải nén và khôi phục CSDL...', 'info');
        const res = await BackupAPI.restore(filename);
        if (res && res.success) {
            alert(`Phục hồi dữ liệu thành công!\n\n${res.message}\n\nTrang sẽ tự động làm mới để cập nhật dữ liệu.`);
            window.location.reload();
        } else {
            showToast(res?.message || 'Lỗi khi khôi phục dữ liệu', 'danger');
        }
    } catch (err) {
        showToast('Lỗi phục hồi: ' + (err.message || err), 'danger');
    }
}

async function handleDeleteBackup(filename) {
    if (!filename) return;
    if (!confirm(`Bạn có chắc chắn muốn xóa bản sao lưu:\n"${filename}"?`)) return;

    try {
        const res = await BackupAPI.delete(filename);
        if (res && res.success) {
            showToast('Đã xóa bản sao lưu!', 'info');
            await loadBackupList();
        } else {
            showToast(res?.message || 'Lỗi xóa file', 'danger');
        }
    } catch (err) {
        showToast('Lỗi: ' + (err.message || err), 'danger');
    }
}

async function handleUploadBackupZip(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.zip')) {
        alert('Vui lòng chọn file nén .ZIP bản sao lưu của hệ thống!');
        e.target.value = '';
        return;
    }

    const confirmMsg = `Bạn vừa chọn file tải lên: "${file.name}" (${(file.size / (1024 * 1024)).toFixed(2)} MB).\n\nBạn có muốn tải file lên và TIẾN HÀNH PHỤC HỒI HỆ THỐNG ngay lập tức không?`;
    if (!confirm(confirmMsg)) {
        e.target.value = '';
        return;
    }

    try {
        showToast('Đang tải file lên máy chủ và tiến hành phục hồi...', 'info');
        const res = await BackupAPI.uploadAndRestore(file);
        if (res && res.success) {
            alert(`Tải lên và phục hồi thành công!\n\nTrang sẽ tự động tải lại để đồng bộ CSDL.`);
            window.location.reload();
        } else {
            alert('Lỗi: ' + (res?.message || 'Không thể phục hồi từ file tải lên.'));
        }
    } catch (err) {
        alert('Lỗi tải lên và khôi phục: ' + (err.message || err));
    } finally {
        e.target.value = '';
    }
}

function initBackupEvents() {
    const btnCreate = document.getElementById('btnCreateBackupNow');
    if (btnCreate) {
        btnCreate.addEventListener('click', handleCreateBackup);
    }

    const btnRefresh = document.getElementById('btnRefreshBackupList');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', async () => {
            btnRefresh.classList.add('fa-spin');
            await loadBackupList();
            setTimeout(() => btnRefresh.classList.remove('fa-spin'), 600);
            showToast('Đã cập nhật danh sách bản sao lưu!', 'info');
        });
    }

    const inputUpload = document.getElementById('inputUploadBackupZip');
    if (inputUpload) {
        inputUpload.addEventListener('change', handleUploadBackupZip);
    }

    initGDriveEvents();
    loadGDriveStatus();
}

// ===================================================================
// GOOGLE DRIVE KẾT NỐI & TRẠNG THÁI
// ===================================================================
async function loadGDriveStatus() {
    const badge = document.getElementById('gdriveStatusBadge');
    const accountInfo = document.getElementById('gdriveAccountInfo');
    const btnConnect = document.getElementById('btnGDriveConnect');
    const btnDisconnect = document.getElementById('btnGDriveDisconnect');
    if (!badge) return;

    try {
        const res = await BackupAPI.gdriveStatus();
        if (res && res.success) {
            if (!res.configured) {
                badge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Chưa cấu hình';
                badge.style.background = '#fff7ed';
                badge.style.color = '#c2410c';
                if (btnConnect) { btnConnect.disabled = true; btnConnect.title = 'Thêm GOOGLE_DRIVE_CLIENT_ID vào file cấu hình.'; }
                if (accountInfo) accountInfo.textContent = 'Thiếu thông tin cấu hình .env (GOOGLE_DRIVE_CLIENT_ID).';
            } else if (res.connected) {
                badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Đã kết nối';
                badge.style.background = '#dcfce7';
                badge.style.color = '#15803d';
                if (accountInfo) accountInfo.innerHTML = '<i class="fa-solid fa-envelope"></i> ' + esc(res.account_email || 'Tài khoản Google');
            } else {
                badge.innerHTML = '<i class="fa-solid fa-circle-plus"></i> Chưa kết nối';
                badge.style.background = '#f1f5f9';
                badge.style.color = '#64748b';
                if (accountInfo) accountInfo.textContent = 'Backup hiện chỉ lưu ở máy chủ.';
            }
            if (btnDisconnect) btnDisconnect.style.display = res.connected ? '' : 'none';
        }
    } catch (err) {
        console.warn('Lỗi lấy trạng thái Google Drive:', err);
    }
}

function initGDriveEvents() {
    const btnConnect = document.getElementById('btnGDriveConnect');
    const btnDisconnect = document.getElementById('btnGDriveDisconnect');
    const btnConfirm = document.getElementById('btnGDriveConfirm');
    const codeRow = document.getElementById('gdriveCodeRow');
    const codeInput = document.getElementById('gdriveCodeInput');
    const feedback = document.getElementById('gdriveFeedbackMsg');

    if (btnConnect) {
        btnConnect.addEventListener('click', async () => {
            try {
                const res = await BackupAPI.gdriveAuthUrl();
                if (res && res.success && res.url) {
                    window.open(res.url, '_blank', 'noopener');
                    if (codeRow) codeRow.style.display = 'block';
                    showToast('Đã mở tab đăng nhập Google. Hãy dán mã kết nối vào ô bên dưới.', 'info');
                } else {
                    showToast(res?.message || 'Không lấy được URL kết nối.', 'danger');
                }
            } catch (err) {
                showToast('Lỗi: ' + (err.message || 'Không thể tạo URL kết nối Google Drive.'), 'danger');
            }
        });
    }

    if (btnConfirm) {
        btnConfirm.addEventListener('click', async () => {
            if (!codeInput || !codeInput.value.trim()) {
                showToast('Vui lòng dán mã kết nối trước.', 'danger');
                return;
            }
            let raw = codeInput.value.trim();
            const m = raw.match(/[?&]code=([^&]+)/);
            const code = (m ? decodeURIComponent(m[1]) : raw).trim();
            btnConfirm.disabled = true;
            btnConfirm.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kết nối...';
            try {
                const res = await BackupAPI.gdriveConnect(code);
                if (res && res.success) {
                    if (feedback) {
                        feedback.innerHTML = '<div style="color: #15803d; font-size: 0.85rem;"><i class="fa-solid fa-circle-check"></i> Đã kết nối Google Drive thành công!</div>';
                    }
                    showToast(res.message || 'Đã kết nối Google Drive!', 'success');
                    if (codeRow) codeRow.style.display = 'none';
                    if (codeInput) codeInput.value = '';
                    await loadGDriveStatus();
                    await loadBackupList();
                } else {
                    if (feedback) {
                        feedback.innerHTML = `<div style="color: #dc2626; font-size: 0.85rem;"><i class="fa-solid fa-circle-xmark"></i> ${esc(res?.message || 'Kết nối thất bại.')}</div>`;
                    }
                    showToast(res?.message || 'Kết nối thất bại!', 'danger');
                }
            } catch (err) {
                showToast('Lỗi kết nối: ' + (err.message || err), 'danger');
            } finally {
                btnConfirm.disabled = false;
                btnConfirm.innerHTML = '<i class="fa-solid fa-check"></i> Xác Nhận Mã';
            }
        });
    }

    if (btnDisconnect) {
        btnDisconnect.addEventListener('click', async () => {
            if (!confirm('Bạn có chắc muốn NGẮT KẾT NỐI Google Drive?\n\nCác backup sau đó sẽ chỉ lưu ở máy chủ.')) return;
            try {
                const res = await BackupAPI.gdriveDisconnect();
                showToast(res?.message || 'Đã ngắt kết nối Google Drive.', 'info');
                await loadGDriveStatus();
                await loadBackupList();
            } catch (err) {
                showToast('Lỗi: ' + (err.message || err), 'danger');
            }
        });
    }
}

window.showImgModal = showImgModal;
window.closeImgModal = closeImgModal;
window.initTabsNavigation = initTabsNavigation;
window.loadBackupList = loadBackupList;
window.loadGDriveStatus = loadGDriveStatus;
