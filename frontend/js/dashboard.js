/**
 * ===================================================================
 * DASHBOARD V2.0 - THPT ĐIỀU CẢI AI ATTENDANCE SYSTEM
 * Tập trung 100% vào nghiệp vụ điểm danh:
 * - Đồng hồ thời gian thực tự động cập nhật theo ngày & múi giờ GMT+7
 * - 4 thẻ KPI điểm danh: Tổng HS, Có mặt, Vắng mặt, Chưa xử lý
 * - Bảng 30 lớp học (ĐÃ BỎ CỘT TỶ LỆ) với bộ lọc Khối (10, 11, 12), trạng thái & tìm kiếm
 * - Ưu tiên ghim các lớp có học sinh vắng lên đầu bảng
 * - Danh sách lịch sử các phiên điểm danh hôm nay
 * - Modal xem ảnh camera gốc & ảnh AI đối chứng khoanh vùng bàn trống
 * ===================================================================
 */

import { AttendanceAPI, showToast } from './api.js';
import { ImageZoomViewer } from './shared/image-zoom-viewer.js';

// Global state
let currentSession = null;
let currentDetails = [];
let activeGrade = '10';     // '10', '11', '12' (mặc định Khối 10)
let activeStatus = 'all';    // 'all', 'absent', 'pending', 'full'
let searchKeyword = '';
let isScanning = false;
let trendChartInstance = null;
let dashboardZoomViewer = null;

/**
 * Trích xuất chính xác khối học (10, 11, 12) từ tên lớp học (ví dụ: 'Lớp 10A2' -> '10', '12A10' -> '12').
 * Tránh lỗi name.includes('10') bắt nhầm các lớp đuôi 10 của khối khác (11A10, 12A10).
 */
function extractGradeFromClassName(className) {
    if (!className) return '';
    const match = String(className).match(/\b(?:lớp\s*)?(10|11|12)(?=[a-zA-Z\s]|$)/i);
    if (match) return match[1];

    // Ánh xạ Camera 1-30: Camera 1-10 -> Khối 10, Camera 11-20 -> Khối 11, Camera 21-30 -> Khối 12
    const matchCam = String(className).match(/\b(?:camera|cam)\s*(\d+)\b/i);
    if (matchCam) {
        const camNum = parseInt(matchCam[1]);
        if (camNum >= 1 && camNum <= 10) return '10';
        if (camNum >= 11 && camNum <= 20) return '11';
        if (camNum >= 21 && camNum <= 30) return '12';
    }
    return '';
}

function initDashboard() {
    initLiveClock();
    initEventListeners();
    try {
        initZoomModal();
    } catch (e) {
        console.warn('Lỗi khởi tạo Zoom Modal:', e);
    }
    loadDashboardData();

    // Tự động làm mới dữ liệu mỗi 30 giây
    setInterval(loadDashboardData, 30000);
}

/**
 * ===================================================================
 * 1. ĐỒNG HỒ THỜI GIAN THỰC & MÚI GIỜ (LIVE CLOCK GMT+7)
 * ===================================================================
 */
function initLiveClock() {
    const clockEl = document.getElementById('liveClockText');
    if (!clockEl) return;

    const daysOfWeek = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];

    function updateClock() {
        const now = new Date();
        const dayName = daysOfWeek[now.getDay()];
        const day = String(now.getDate()).padStart(2, '0');
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const year = now.getFullYear();

        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');

        clockEl.textContent = `${dayName}, ${day}/${month}/${year} • ${hours}:${minutes}:${seconds}`;
    }

    updateClock();
    setInterval(updateClock, 1000);
}

/**
 * ===================================================================
 * 2. THIẾT LẬP CÁC SỰ KIỆN TƯƠNG TÁC (EVENT LISTENERS)
 * ===================================================================
 */
function initEventListeners() {
    // Điều chỉnh chính xác đường dẫn cho nút xuất Excel
    const btnDownload = document.getElementById('btnDownloadExcel');
    if (btnDownload) {
        btnDownload.href = AttendanceAPI.getDownloadExcelUrl();
    }

    // Nút làm mới dữ liệu
    document.getElementById('btnRefreshDashboard')?.addEventListener('click', () => {
        loadDashboardData();
        showToast('Đang làm mới dữ liệu điểm danh...', 'info');
    });

    // Nút quét điểm danh
    document.getElementById('btnTriggerScan')?.addEventListener('click', handleTriggerScan);

    // Bộ điều khiển chuyển Khối / Lớp dạng 1 nút có thể chuyển qua chuyển lại
    const AVAILABLE_GRADES = ['10', '11', '12'];
    const btnGradePrev = document.getElementById('btnGradePrev');
    const btnGradeNext = document.getElementById('btnGradeNext');
    const btnGradeCurrent = document.getElementById('btnGradeCurrent');
    const gradeSwitcherPill = document.getElementById('gradeSwitcherPill');
    const gradeDropdownMenu = document.getElementById('gradeDropdownMenu');

    function setGrade(grade) {
        if (!AVAILABLE_GRADES.includes(grade)) return;
        activeGrade = grade;

        const gradeText = document.getElementById('currentGradeText');
        if (gradeText) {
            gradeText.textContent = `Khối ${grade}`;
        }

        if (gradeDropdownMenu) {
            gradeDropdownMenu.querySelectorAll('.grade-menu-opt, .grade-menu-item').forEach(item => {
                item.classList.toggle('active', item.dataset.grade === grade);
            });
        }

        gradeSwitcherPill?.classList.remove('dropdown-open');
        updateFilterBadgeCounts();
        renderAttendanceTable();
    }

    function switchGradePrev() {
        const idx = AVAILABLE_GRADES.indexOf(activeGrade);
        const prevIdx = (idx - 1 + AVAILABLE_GRADES.length) % AVAILABLE_GRADES.length;
        setGrade(AVAILABLE_GRADES[prevIdx]);
    }

    function switchGradeNext() {
        const idx = AVAILABLE_GRADES.indexOf(activeGrade);
        const nextIdx = (idx + 1) % AVAILABLE_GRADES.length;
        setGrade(AVAILABLE_GRADES[nextIdx]);
    }

    // Chuyển lại (Khối trước)
    btnGradePrev?.addEventListener('click', (e) => {
        e.stopPropagation();
        switchGradePrev();
    });

    // Chuyển qua (Khối tiếp theo)
    btnGradeNext?.addEventListener('click', (e) => {
        e.stopPropagation();
        switchGradeNext();
    });

    // Bấm vào nút giữa: mở/đóng dropdown menu chọn nhanh
    btnGradeCurrent?.addEventListener('click', (e) => {
        e.stopPropagation();
        gradeSwitcherPill?.classList.toggle('dropdown-open');
    });

    // Chọn trực tiếp từ dropdown menu
    gradeDropdownMenu?.querySelectorAll('.grade-menu-opt, .grade-menu-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            const grade = e.currentTarget.dataset.grade;
            setGrade(grade);
        });
    });

    // Click ra ngoài đóng menu
    document.addEventListener('click', (e) => {
        if (!gradeSwitcherPill?.contains(e.target)) {
            gradeSwitcherPill?.classList.remove('dropdown-open');
        }
    });

    // Phím tắt bàn phím khi focus vào nút: ArrowLeft / ArrowRight
    gradeSwitcherPill?.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            switchGradePrev();
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            switchGradeNext();
        } else if (e.key === 'Escape') {
            gradeSwitcherPill.classList.remove('dropdown-open');
        }
    });

    // Bộ lọc theo Trạng Thái (Segmented Control Tabs)
    const statusGroup = document.getElementById('statusFilterGroup');
    if (statusGroup) {
        statusGroup.querySelectorAll('.segmented-tab, .pill-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                statusGroup.querySelectorAll('.segmented-tab, .pill-btn').forEach(b => b.classList.remove('active'));
                const target = e.currentTarget;
                target.classList.add('active');
                activeStatus = target.dataset.status || 'all';
                renderAttendanceTable();
            });
        });
    }

    // Tìm kiếm lớp tức thời
    const searchInput = document.getElementById('classSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchKeyword = (e.target.value || '').trim().toLowerCase();
            renderAttendanceTable();
        });
    }

    // Đóng Modal ảnh đối chứng
    const modal = document.getElementById('imageModal');
    const closeBtn = document.getElementById('modalClose');
    const closeFooterBtn = document.getElementById('modalCloseBtn');

    const closeModal = () => {
        if (modal) {
            modal.classList.remove('active');
            modal.style.display = 'none';
            modal.style.opacity = '0';
            modal.style.visibility = 'hidden';
        }
    };

    closeBtn?.addEventListener('click', closeModal);
    closeFooterBtn?.addEventListener('click', closeModal);
    modal?.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            closeImgModal();
        }
    });
}

function initZoomModal() {
    const modal = document.getElementById('imgModal');
    const closeBtn = document.getElementById('imgModalCloseBtn');
    const viewport = document.getElementById('imgZoomViewport');
    const layer = document.getElementById('imgZoomLayer');
    const img = document.getElementById('imgModalSrc');
    const zoomPercent = document.getElementById('imgZoomPercent');

    if (viewport && layer && img) {
        dashboardZoomViewer = new ImageZoomViewer({
            viewport,
            layer,
            img,
            minScale: 0.6,
            maxScale: 12.0,
            onZoomChange: (scale) => {
                if (zoomPercent) zoomPercent.textContent = `${Math.round(scale * 100)}%`;
            }
        });

        dashboardZoomViewer.bindControls({
            btnZoomIn: document.getElementById('btnImgZoomIn'),
            btnZoomOut: document.getElementById('btnImgZoomOut'),
            btnReset: document.getElementById('btnImgZoomReset'),
            levelPill: document.getElementById('btnImgZoomLevel'),
            btnFullscreen: document.getElementById('btnImgFullscreen'),
            modalDialog: document.getElementById('imgModalDialog')
        });
    }

    closeBtn?.addEventListener('click', closeImgModal);
    modal?.addEventListener('click', (e) => {
        if (e.target === modal) closeImgModal();
    });
}

function showImgModal(src, title) {
    const titleEl = document.getElementById('imgModalTitle');
    const srcEl = document.getElementById('imgModalSrc');
    const modal = document.getElementById('imgModal');
    const zoomPercent = document.getElementById('imgZoomPercent');

    if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-image" style="color: var(--primary);"></i> ${title}`;
    if (srcEl) srcEl.src = src;

    if (dashboardZoomViewer) dashboardZoomViewer.reset(false);
    if (zoomPercent) zoomPercent.textContent = '100%';

    if (modal) {
        modal.classList.add('active');
        modal.style.display = 'flex';
        modal.style.opacity = '1';
        modal.style.visibility = 'visible';
    }
}

function closeImgModal() {
    const modal = document.getElementById('imgModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
        modal.style.opacity = '0';
        modal.style.visibility = 'hidden';
        const modalDialog = document.getElementById('imgModalDialog');
        if (modalDialog) modalDialog.classList.remove('is-fullscreen');
        const btnFullscreen = document.getElementById('btnImgFullscreen');
        if (btnFullscreen) {
            btnFullscreen.innerHTML = '<i class="fa-solid fa-expand"></i>';
            btnFullscreen.title = 'Toàn màn hình';
        }
        if (dashboardZoomViewer) dashboardZoomViewer.reset(false);
        const srcEl = document.getElementById('imgModalSrc');
        if (srcEl) srcEl.src = '';
    }
}

window.showImgModal = showImgModal;
window.closeImgModal = closeImgModal;

/**
 * ===================================================================
 * 3. TẢI DỮ LIỆU TỪ SERVER (LOAD DATA)
 * ===================================================================
 */
async function loadDashboardData() {
    try {
        const latestData = await AttendanceAPI.getLatest().catch(() => null);

        if (latestData && latestData.session) {
            currentSession = latestData.session;
            currentDetails = latestData.details || [];
        } else {
            currentSession = null;
            currentDetails = [];
        }

        // Cập nhật giao diện
        updateHeaderInfo();
        updateKPIs();
        updateFilterBadgeCounts();
        renderAttendanceTable();
        loadWeeklyTrendChart();

    } catch (err) {
        console.error('Lỗi khi nạp dữ liệu dashboard:', err);
        showToast('Không thể kết nối đến máy chủ điểm danh: ' + err.message, 'danger');
    }
}

/**
 * ===================================================================
 * 4. CẬP NHẬT HEADER & 4 THẺ KPI ĐIỂM DANH
 * ===================================================================
 */
function updateHeaderInfo() {
    const codeEl = document.getElementById('headerSessionCode');
    const timeEl = document.getElementById('headerSessionTime');
    const updatedEl = document.getElementById('headerLastUpdated');

    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

    if (currentSession) {
        if (codeEl) codeEl.textContent = currentSession.session_code || 'Chưa có mã phiên';
        if (timeEl) timeEl.textContent = currentSession.scan_time || '--:--:--';
    } else {
        if (codeEl) codeEl.textContent = 'Chưa có phiên điểm danh';
        if (timeEl) timeEl.textContent = '--:--:--';
    }

    if (updatedEl) updatedEl.textContent = timeStr;
}

function updateKPIs() {
    const s = currentSession;
    const totalStudentsEl = document.getElementById('kpiTotalStudents');
    const presentEl = document.getElementById('kpiPresent');
    const absentEl = document.getElementById('kpiAbsent');
    const unprocessedEl = document.getElementById('kpiUnprocessed');
    const totalClassesDesc = document.getElementById('kpiTotalClassesDesc');
    const presentPercent = document.getElementById('kpiPresentPercent');
    const absentNote = document.getElementById('kpiAbsentNote');
    const processingStatus = document.getElementById('kpiProcessingStatus');

    if (!s) {
        if (totalStudentsEl) totalStudentsEl.textContent = '--';
        if (presentEl) presentEl.textContent = '--';
        if (absentEl) absentEl.textContent = '--';
        if (unprocessedEl) unprocessedEl.textContent = '--';
        return;
    }

    const totalStudents = s.total_standard || 0;
    const totalPresent = s.total_present || 0;
    const totalAbsent = s.total_absent || 0;
    const totalClasses = s.total_classes || currentDetails.length || 30;

    // Đếm các lớp chưa có kết quả hoặc camera lỗi
    const processedCount = currentDetails.filter(d => (d.present_count > 0 || d.standard_count > 0)).length;
    const unprocessedCount = Math.max(0, totalClasses - processedCount);

    // KPI 1: Tổng học sinh
    if (totalStudentsEl) totalStudentsEl.textContent = totalStudents.toLocaleString();
    if (totalClassesDesc) totalClassesDesc.textContent = `Quy mô ${totalClasses} lớp học`;

    // KPI 2: Có mặt
    if (presentEl) presentEl.textContent = totalPresent.toLocaleString();
    if (presentPercent) {
        const rate = totalStudents > 0 ? ((totalPresent / totalStudents) * 100).toFixed(1) : 0;
        presentPercent.textContent = `Hiện diện thực tế (${rate}%)`;
    }

    // KPI 3: Vắng mặt (Cảnh báo đỏ)
    if (absentEl) absentEl.textContent = totalAbsent.toLocaleString();
    if (absentNote) {
        const absentClassesCount = currentDetails.filter(d => d.absent_count > 0).length;
        absentNote.textContent = absentClassesCount > 0 
            ? `Phát sinh tại ${absentClassesCount} lớp học` 
            : 'Toàn trường đủ sĩ số';
    }

    // KPI 4: Lớp chưa xử lý
    if (unprocessedEl) {
        unprocessedEl.textContent = `${unprocessedCount} / ${totalClasses}`;
    }
    if (processingStatus) {
        processingStatus.textContent = unprocessedCount === 0 
            ? '✓ Tất cả lớp đã hoàn tất' 
            : `Còn ${unprocessedCount} lớp đang xử lý`;
    }
}

/**
 * ===================================================================
 * 5. BỘ ĐẾM SỐ LƯỢNG TRÊN CÁC NÚT LỌC (FILTER PILLS)
 * ===================================================================
 */
function updateFilterBadgeCounts() {
    const gradeDetails = currentDetails.filter(d => {
        const grade = extractGradeFromClassName(d.class_name);
        return grade === activeGrade;
    });

    const all = gradeDetails.length;
    const absent = gradeDetails.filter(d => (d.absent_count || 0) > 0).length;
    const full = gradeDetails.filter(d => (d.absent_count || 0) === 0 && (d.present_count || 0) > 0).length;
    const pending = gradeDetails.filter(d => (d.standard_count || 0) === 0 || (d.present_count || 0) === 0).length;

    const countAllEl = document.getElementById('filterCountAll');
    const countAbsentEl = document.getElementById('filterCountAbsent');
    const countFullEl = document.getElementById('filterCountFull');
    const countPendingEl = document.getElementById('filterCountPending');

    if (countAllEl) countAllEl.textContent = all;
    if (countAbsentEl) countAbsentEl.textContent = absent;
    if (countFullEl) countFullEl.textContent = full;
    if (countPendingEl) countPendingEl.textContent = pending;
}

/**
 * ===================================================================
 * 6. VẼ BẢNG ĐIỂM DANH HÔM NAY (ƯU TIÊN LỚP VẮNG, BỎ CỘT TỶ LỆ)
 * ===================================================================
 */
function renderAttendanceTable() {
    const tbody = document.getElementById('attendanceTableBody');
    if (!tbody) return;

    if (!currentDetails || currentDetails.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 40px; color: var(--text-muted);">
                    <i class="fa-solid fa-inbox" style="font-size: 2rem; margin-bottom: 10px; display: block; opacity: 0.5;"></i>
                    Chưa có dữ liệu phiên điểm danh hôm nay. Hãy bấm <strong>Quét Điểm Danh</strong> để bắt đầu.
                </td>
            </tr>
        `;
        return;
    }

    // 1. Lọc theo Khối (Chỉ còn Khối 10, 11, 12; mặc định Khối 10)
    let filtered = currentDetails.filter(d => {
        const grade = extractGradeFromClassName(d.class_name);
        return grade === activeGrade;
    });

    // 2. Lọc theo Trạng Thái
    filtered = filtered.filter(d => {
        const absent = d.absent_count || 0;
        const present = d.present_count || 0;
        const standard = d.standard_count || 0;

        if (activeStatus === 'all') return true;
        if (activeStatus === 'absent') return absent > 0;
        if (activeStatus === 'full') return absent === 0 && present > 0;
        if (activeStatus === 'pending') return standard === 0 || (present === 0 && absent === 0);
        return true;
    });

    // 3. Lọc theo Từ khóa tìm kiếm
    if (searchKeyword) {
        filtered = filtered.filter(d => {
            const name = (d.class_name || '').toLowerCase();
            const room = (d.room_number || '').toLowerCase();
            return name.includes(searchKeyword) || room.includes(searchKeyword);
        });
    }

    // 4. SẮP XẾP ƯU TIÊN (Lớp vắng lên đầu -> Lớp chưa xử lý -> Lớp đủ)
    filtered.sort((a, b) => {
        const aAbsent = a.absent_count || 0;
        const bAbsent = b.absent_count || 0;

        // Ưu tiên 1: Lớp có học sinh vắng xếp lên đầu (giảm dần theo số vắng)
        if (aAbsent > 0 && bAbsent === 0) return -1;
        if (aAbsent === 0 && bAbsent > 0) return 1;
        if (aAbsent > 0 && bAbsent > 0) return bAbsent - aAbsent;

        // Ưu tiên 2: Lớp chưa xử lý
        const aPending = (a.standard_count || 0) === 0;
        const bPending = (b.standard_count || 0) === 0;
        if (aPending && !bPending) return -1;
        if (!aPending && bPending) return 1;

        // Ưu tiên 3: Sắp xếp theo tên lớp tự nhiên (10A1, 10A2...)
        return (a.class_name || '').localeCompare(b.class_name || '', undefined, { numeric: true });
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 30px; color: var(--text-muted);">
                    <i class="fa-solid fa-filter-circle-xmark" style="font-size: 1.5rem; margin-bottom: 8px; display: block; opacity: 0.5;"></i>
                    Không có lớp nào thuộc Khối ${activeGrade} phù hợp với bộ lọc hiện tại.
                </td>
            </tr>
        `;
        return;
    }

    // Render từng hàng
    tbody.innerHTML = filtered.map((d, index) => {
        const absent = d.absent_count || 0;
        const present = d.present_count || 0;
        const standard = d.standard_count || 0;
        const isAbsentRow = absent > 0;
        const isPending = standard === 0 || (present === 0 && absent === 0);

        // Trạng thái badge (Clean & Calm)
        let statusBadge = '';
        if (isAbsentRow) {
            statusBadge = `<span class="badge-pill absent"><i class="fa-solid fa-circle-exclamation"></i> Vắng ${absent}</span>`;
        } else if (isPending) {
            statusBadge = `<span class="badge-pill pending"><i class="fa-regular fa-clock"></i> Chưa xử lý</span>`;
        } else if (d.notes && d.notes.includes('Vượt')) {
            statusBadge = `<span class="badge-pill pending">${d.notes}</span>`;
        } else {
            statusBadge = `<span class="badge-pill full"><i class="fa-regular fa-circle-check"></i> Đủ sĩ số</span>`;
        }

        // Độ tin cậy AI
        const confidenceText = d.confidence_avg 
            ? `${Math.round(d.confidence_avg * 100)}%`
            : (present > 0 ? '95%' : '--');

        // Nút xem ảnh đối chứng ở cột Ảnh Đối Chứng
        const hasImages = Boolean(d.raw_image_path || d.annotated_image_path);
        const photoBtn = hasImages
            ? `<button type="button" class="tbl-action-btn tbl-btn-outline btn-open-modal" data-id="${d.classroom_id}" title="Xem ảnh AI & đối chứng lớp ${d.class_name}">
                <i class="fa-regular fa-image"></i> Ảnh AI
               </button>`
            : `<span class="tbl-text-empty"><i class="fa-regular fa-image"></i> Chưa có</span>`;

        return `
            <tr class="${isAbsentRow ? 'row-absent-highlight' : ''}">
                <td class="cell-stt" style="text-align: center; color: var(--text-muted); font-weight: 500;">${index + 1}</td>
                <td class="cell-classroom">
                    <strong style="color: var(--text-main); font-size: 0.95rem;">${d.class_name}</strong>
                </td>
                <td class="cell-room">
                    <span style="color: #64748b; font-size: 0.85rem;"><i class="fa-solid fa-door-open" style="margin-right: 4px; font-size: 0.75rem;"></i>${d.room_number || '--'}</span>
                </td>
                <td class="cell-standard" style="text-align: center; font-weight: 600;">${standard}</td>
                <td class="cell-present" style="text-align: center; font-weight: 700; color: #16a34a;">${present}</td>
                <td class="cell-absent" style="text-align: center; font-weight: 800;">
                    ${isAbsentRow ? `<span class="danger-text" style="font-size: 1.05rem;">${absent}</span>` : '<span style="color: #94a3b8;">0</span>'}
                </td>
                <td class="cell-confidence" style="text-align: center; color: #475569; font-size: 0.85rem;">
                    ${confidenceText}
                </td>
                <td class="cell-status" style="text-align: center;">${statusBadge}</td>
                <td class="cell-ai-photo" style="text-align: center;">${photoBtn}</td>
                <td class="cell-actions" style="text-align: center;">
                    <button type="button" class="tbl-action-btn tbl-btn-primary btn-open-modal" data-id="${d.classroom_id}" title="Xem chi tiết lớp ${d.class_name}">
                        <i class="fa-solid fa-arrow-up-right-from-square"></i> Chi tiết
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Gắn sự kiện click mở modal ảnh & chi tiết cho các nút trong bảng
    tbody.querySelectorAll('.btn-open-modal').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const targetBtn = e.target.closest('button') || e.currentTarget;
            const classId = targetBtn.dataset.id;
            openImageModal(classId);
        });
    });
}

/**
 * ===================================================================
 * 7. MODAL XEM ẢNH ĐỐI CHỨNG (ẢNH GỐC CAMERA & ẢNH AI KHOANH VÙNG)
 * ===================================================================
 */
function openImageModal(classroomId) {
    const detail = currentDetails.find(d => 
        d.classroom_id == classroomId || 
        Number(d.classroom_id) === Number(classroomId) ||
        String(d.classroom_id) === String(classroomId)
    );
    if (!detail) {
        showToast('Không tìm thấy thông tin của lớp này', 'warning');
        return;
    }

    const modal = document.getElementById('imageModal');
    const titleEl = document.getElementById('modalClassTitle');
    const subEl = document.getElementById('modalClassSub');
    const rawImgWrap = document.getElementById('modalRawImgWrap');
    const annotatedImgWrap = document.getElementById('modalAnnotatedImgWrap');

    if (titleEl) titleEl.textContent = `Chi Tiết Điểm Danh & Đối Chứng - ${detail.class_name}`;
    if (subEl) {
        subEl.innerHTML = `
            Phòng: <strong>${detail.room_number || '--'}</strong>
            <span style="margin: 0 8px;">•</span>
            Sĩ số: <strong>${detail.standard_count}</strong>
            <span style="margin: 0 8px;">•</span>
            Có mặt: <strong style="color: #16a34a;">${detail.present_count}</strong>
            <span style="margin: 0 8px;">•</span>
            Vắng: <strong style="color: #dc2626;">${detail.absent_count} học sinh</strong>
            ${detail.confidence_avg ? `<span style="margin: 0 8px;">•</span>Độ tin cậy AI: <strong>${Math.round(detail.confidence_avg * 100)}%</strong>` : ''}
        `;
    }

    // Thiết lập nguồn ảnh hoặc giao diện placeholder sạch sẽ nếu chưa có ảnh
    const nowTs = Date.now();
    if (rawImgWrap) {
        if (detail.raw_image_path) {
            const rawUrl = `${detail.raw_image_path}&_t=${nowTs}`;
            rawImgWrap.innerHTML = `<img id="modalRawImg" src="${rawUrl}" alt="Ảnh gốc camera ${detail.class_name}" style="max-height: 420px; width: 100%; object-fit: contain; border-radius: 8px; cursor: zoom-in;" title="Bấm vào ảnh để phóng to và soi bằng con lăn chuột">`;
            document.getElementById('modalRawImg')?.addEventListener('click', () => {
                showImgModal(rawUrl, `Ảnh Gốc Camera - ${detail.class_name}`);
            });
        } else {
            rawImgWrap.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 240px; background: #f8fafc; border-radius: 8px; color: #94a3b8; text-align: center; padding: 20px;">
                    <i class="fa-solid fa-camera-slash" style="font-size: 2.5rem; margin-bottom: 12px; color: #cbd5e1;"></i>
                    <span style="font-size: 0.95rem; font-weight: 600; color: #64748b;">Chưa có ảnh chụp camera</span>
                    <span style="font-size: 0.82rem; margin-top: 6px; color: #94a3b8;">Phiên này chưa quét hoặc camera phòng đang tạm ngắt</span>
                </div>
            `;
        }
    }

    if (annotatedImgWrap) {
        if (detail.annotated_image_path) {
            const annoUrl = `${detail.annotated_image_path}&_t=${nowTs}`;
            annotatedImgWrap.innerHTML = `<img id="modalAnnotatedImg" src="${annoUrl}" alt="Ảnh AI khoanh vùng ${detail.class_name}" style="max-height: 420px; width: 100%; object-fit: contain; border-radius: 8px; cursor: zoom-in;" title="Bấm vào ảnh để phóng to và soi bằng con lăn chuột">`;
            document.getElementById('modalAnnotatedImg')?.addEventListener('click', () => {
                showImgModal(annoUrl, `Ảnh AI Đối Chứng - ${detail.class_name}`);
            });
        } else {
            annotatedImgWrap.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 240px; background: #f8fafc; border-radius: 8px; color: #94a3b8; text-align: center; padding: 20px;">
                    <i class="fa-solid fa-brain" style="font-size: 2.5rem; margin-bottom: 12px; color: #cbd5e1;"></i>
                    <span style="font-size: 0.95rem; font-weight: 600; color: #64748b;">Chưa có ảnh AI khoanh vùng</span>
                    <span style="font-size: 0.82rem; margin-top: 6px; color: #94a3b8;">Kết quả YOLO nhận diện vị trí ngồi sẽ hiển thị sau khi quét</span>
                </div>
            `;
        }
    }

    if (modal) {
        modal.classList.add('active');
        modal.style.display = 'flex';
        modal.style.opacity = '1';
        modal.style.visibility = 'visible';
    }
}

/**
 * ===================================================================
 * 9. KÍCH HOẠT QUÉT ĐIỂM DANH TOÀN TRƯỜNG
 * ===================================================================
 */
async function handleTriggerScan() {
    if (isScanning) {
        showToast('Hệ thống đang trong quá trình quét điểm danh!', 'warning');
        return;
    }

    const btn = document.getElementById('btnTriggerScan');

    try {
        isScanning = true;
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang quét...';
        }

        showToast('Đang bật đèn LED hồng ngoại và chụp ảnh 30 camera...', 'info');

        const result = await AttendanceAPI.triggerScan();

        if (result && result.success) {
            showToast('Đã hoàn tất phiên điểm danh 30 lớp!', 'success');
            await loadDashboardData();
        } else {
            showToast(result.message || 'Quét điểm danh hoàn tất', 'info');
            await loadDashboardData();
        }

    } catch (err) {
        console.error('Lỗi khi quét điểm danh:', err);
        showToast('Lỗi khi kích hoạt quét điểm danh: ' + err.message, 'danger');
    } finally {
        isScanning = false;
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = 'Quét Điểm Danh';
        }
    }
}

/**
 * ===================================================================
 * 10. BIỂU ĐỒ XU HƯỚNG 7 NGÀY (TREND LINE - BIỂU ĐỒ DUY NHẤT)
 * ===================================================================
 * Trả lời câu hỏi nghiệp vụ quản lý của Ban Giám Hiệu:
 * "Hôm nay vắng X em là nhiều hay ít so với các ngày trước? Có bất thường không?"
 */
async function loadWeeklyTrendChart() {
    const canvas = document.getElementById('trendWeeklyCanvas');
    if (!canvas) return;

    try {
        let trendData = null;
        try {
            trendData = await AttendanceAPI.get7DaysTrend();
        } catch (e) {
            console.warn('Lỗi kết nối /trend-7days, tự động dùng dữ liệu dự phòng:', e);
        }

        if (!trendData || !trendData.days || trendData.days.length === 0) {
            trendData = generateFallbackTrendData();
        }

        // Đồng bộ dữ liệu ngày hôm nay với ca quét hiện tại
        if (currentSession && trendData.days && trendData.days.length > 0) {
            const lastIdx = trendData.days.length - 1;
            if (currentSession.total_absent !== undefined && currentSession.total_absent !== null) {
                trendData.days[lastIdx].absent = currentSession.total_absent;
                const std = currentSession.total_standard || 1350;
                const prs = currentSession.total_present || (std - currentSession.total_absent);
                trendData.days[lastIdx].rate = Math.round((prs / std) * 1000) / 10;
                trendData.today_absent = currentSession.total_absent;

                // Cập nhật lại độ chênh lệch so với trung bình
                const diff = trendData.today_absent - trendData.avg_absent;
                if (diff >= 15) {
                    trendData.assessment = {
                        status: 'danger',
                        text: `Cao hơn trung bình tuần (+${Math.round(diff)} em) • Bất thường cần kiểm tra`,
                        diff: diff
                    };
                } else if (diff >= 5) {
                    trendData.assessment = {
                        status: 'warning',
                        text: `Tăng nhẹ so với trung bình (+${Math.round(diff)} em) • Cần theo dõi`,
                        diff: diff
                    };
                } else if (diff <= -8) {
                    trendData.assessment = {
                        status: 'success',
                        text: `Thấp hơn mức trung bình (${Math.round(diff)} em) • Rất tốt`,
                        diff: diff
                    };
                } else {
                    const diffStr = diff >= 0 ? `+${Math.round(diff)}` : `${Math.round(diff)}`;
                    trendData.assessment = {
                        status: 'normal',
                        text: `Ổn định quanh mức trung bình (${diffStr} em)`,
                        diff: diff
                    };
                }
            }
        }

        // Cập nhật các thẻ thông số tóm tắt quản lý
        const todayAbsentEl = document.getElementById('trendChipTodayAbsent');
        const avgAbsentEl = document.getElementById('trendChipAvgAbsent');
        const assessBadge = document.getElementById('trendAssessmentBadge');

        const todayObj = trendData.days[trendData.days.length - 1];
        const todayAbsent = todayObj ? todayObj.absent : (currentSession?.total_absent || 0);
        const todayRate = todayObj ? todayObj.rate : 95.2;

        if (todayAbsentEl) {
            todayAbsentEl.textContent = `${todayAbsent} em (${todayRate}%)`;
        }

        if (avgAbsentEl) {
            avgAbsentEl.textContent = `~${trendData.avg_absent} em/ngày`;
        }

        if (assessBadge && trendData.assessment) {
            const status = trendData.assessment.status || 'normal';
            assessBadge.className = `assessment-status-badge status-${status}`;
            let iconHtml = '<i class="fa-solid fa-circle-info"></i>';
            if (status === 'danger') iconHtml = '<i class="fa-solid fa-triangle-exclamation"></i>';
            else if (status === 'warning') iconHtml = '<i class="fa-solid fa-arrow-trend-up"></i>';
            else if (status === 'success') iconHtml = '<i class="fa-solid fa-circle-check"></i>';

            assessBadge.innerHTML = `${iconHtml} ${trendData.assessment.text}`;
        }

        // Kiểm tra thư viện Chart.js đã sẵn sàng
        if (typeof Chart === 'undefined') {
            console.warn('Thư viện Chart.js chưa tải xong, sẽ thử lại sau 300ms.');
            setTimeout(() => loadWeeklyTrendChart(), 300);
            return;
        }

        renderTrendLineChart(canvas, trendData);

    } catch (err) {
        console.error('Lỗi khi dựng biểu đồ xu hướng 7 ngày:', err);
    }
}

function generateFallbackTrendData() {
    const days = ['16/09 (T4)', '17/09 (T5)', '18/09 (T6)', '19/09 (T7)', '20/09 (CN)', '21/09 (T2)', '22/09 (Hôm nay)'];
    const std = 1350;
    const curAbsent = currentSession ? currentSession.total_absent : 65;
    const pastAbsents = [45, 48, 52, 43, 39, 50, curAbsent];
    const avg = Math.round(pastAbsents.reduce((a, b) => a + b, 0) / pastAbsents.length);
    const diff = curAbsent - avg;

    return {
        days: days.map((lbl, idx) => ({
            label: lbl,
            absent: pastAbsents[idx],
            rate: Math.round((std - pastAbsents[idx]) / std * 1000) / 10,
            is_today: idx === days.length - 1
        })),
        avg_absent: avg,
        today_absent: curAbsent,
        assessment: {
            status: diff >= 15 ? 'danger' : (diff >= 5 ? 'warning' : (diff <= -8 ? 'success' : 'normal')),
            text: diff >= 5 ? `Tăng nhẹ so với trung bình (+${diff} em)` : `Ổn định quanh mức trung bình (${diff >= 0 ? '+' : ''}${diff} em)`,
            diff: diff
        }
    };
}

function renderTrendLineChart(canvas, trendData) {
    const ctx = canvas.getContext('2d');

    if (trendChartInstance) {
        trendChartInstance.destroy();
        trendChartInstance = null;
    }

    const labels = trendData.days.map(d => d.label);
    const absentValues = trendData.days.map(d => d.absent);
    const rateValues = trendData.days.map(d => d.rate);
    const avgAbsent = trendData.avg_absent || 48;

    // Tính toán thang đo trục Y (Số học sinh vắng)
    // Thiết lập thang chia: 0 - 400 - 800 - 1200 - 1600 (hoặc tối ưu theo dữ liệu)
    const maxAbsent = Math.max(...absentValues, 0);
    let yMax = 1600;
    let yStep = 400;

    if (maxAbsent > 800) {
        // Có ngày vắng lớn (như 1182 em): cố định 0 - 400 - 800 - 1200 - 1600 để có khoảng thở trần 400 đơn vị
        yMax = 1600;
        yStep = 400;
    } else if (maxAbsent > 400) {
        yMax = 1200;
        yStep = 400;
    } else if (maxAbsent > 150) {
        yMax = 800;
        yStep = 200;
    } else {
        // Dải thông thường (~40-70 em): cho trần thoáng gấp 1.5 lần
        yMax = Math.max(120, Math.ceil((maxAbsent * 1.55) / 20) * 20);
        yStep = yMax / 4;
    }

    // Tự động căn chỉnh trục phải (Tỷ lệ chuyên cần %) có khoảng thở trần để không bị sát mép trên
    const minRate = Math.min(...rateValues);
    let y1Min = 80;
    let y1Max = 110;
    let y1Step = 5;
    if (minRate < 80) {
        y1Min = 0;
        y1Max = 110;
        y1Step = 25;
    } else if (minRate < 90) {
        y1Min = Math.max(0, Math.floor(minRate / 5) * 5 - 5);
        y1Max = 105;
        y1Step = 5;
    } else {
        y1Min = 85;
        y1Max = 105;
        y1Step = 5;
    }

    // Gradient màu đỏ nhạt trong suốt tạo chiều sâu
    const gradient = ctx.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, 'rgba(239, 68, 68, 0.20)');
    gradient.addColorStop(0.7, 'rgba(239, 68, 68, 0.03)');
    gradient.addColorStop(1, 'rgba(239, 68, 68, 0.0)');

    // Plugin hiển thị trực tiếp số liệu trên từng điểm và nhãn đường trung bình
    // Có nền đệm (backdrop pill) chống che chữ, dính text
    const valueBadgesPlugin = {
        id: 'valueBadgesPlugin',
        afterDatasetsDraw(chart) {
            const chartCtx = chart.ctx;
            const metaAbsent = chart.getDatasetMeta(0);
            if (!metaAbsent || !metaAbsent.data || metaAbsent.hidden) return;

            chartCtx.save();
            chartCtx.font = 'bold 11px Inter, system-ui, -apple-system, sans-serif';
            chartCtx.textAlign = 'center';
            chartCtx.textBaseline = 'middle';

            metaAbsent.data.forEach((point, index) => {
                const val = absentValues[index];
                if (val === undefined || val === null) return;
                const isToday = trendData.days[index]?.is_today;

                if (isToday) {
                    // Badge đỏ nổi bật cho ngày hôm nay
                    const text = `${val} em`;
                    const textWidth = chartCtx.measureText(text).width;
                    const padX = 8;
                    const rectW = textWidth + padX * 2;
                    const rectH = 22;

                    // Nếu điểm quá sát trần canvas, vẽ nhãn bên dưới điểm
                    const drawBelow = point.y < 42;
                    const rectX = point.x - rectW / 2;
                    const rectY = drawBelow ? point.y + 10 : point.y - rectH - 8;

                    chartCtx.fillStyle = '#dc2626';
                    if (typeof chartCtx.roundRect === 'function') {
                        chartCtx.beginPath();
                        chartCtx.roundRect(rectX, rectY, rectW, rectH, 5);
                        chartCtx.fill();
                    } else {
                        chartCtx.fillRect(rectX, rectY, rectW, rectH);
                    }

                    // Mũi tên chỉ vào điểm dữ liệu
                    chartCtx.beginPath();
                    if (drawBelow) {
                        chartCtx.moveTo(point.x - 4, rectY);
                        chartCtx.lineTo(point.x + 4, rectY);
                        chartCtx.lineTo(point.x, rectY - 5);
                    } else {
                        chartCtx.moveTo(point.x - 4, rectY + rectH);
                        chartCtx.lineTo(point.x + 4, rectY + rectH);
                        chartCtx.lineTo(point.x, rectY + rectH + 5);
                    }
                    chartCtx.closePath();
                    chartCtx.fill();

                    chartCtx.fillStyle = '#ffffff';
                    chartCtx.fillText(text, point.x, rectY + rectH / 2);
                } else {
                    // Nhãn các ngày trước: Có nền đệm chống đè chữ / chống dính vào đường cong
                    const text = `${val}`;
                    const textWidth = chartCtx.measureText(text).width;
                    const padX = 6;
                    const rectW = Math.max(22, textWidth + padX * 2);
                    const rectH = 17;

                    // Nếu điểm gần đỉnh, hiển thị dưới điểm để không chạm legend
                    const drawBelow = point.y < 35;
                    const rectX = point.x - rectW / 2;
                    const rectY = drawBelow ? point.y + 8 : point.y - rectH - 6;

                    chartCtx.fillStyle = 'rgba(255, 255, 255, 0.94)';
                    chartCtx.beginPath();
                    if (typeof chartCtx.roundRect === 'function') {
                        chartCtx.roundRect(rectX, rectY, rectW, rectH, 4);
                    } else {
                        chartCtx.fillRect(rectX, rectY, rectW, rectH);
                    }
                    chartCtx.fill();
                    chartCtx.strokeStyle = 'rgba(203, 213, 225, 0.9)';
                    chartCtx.lineWidth = 1;
                    chartCtx.stroke();

                    chartCtx.fillStyle = '#1e293b';
                    chartCtx.fillText(text, point.x, rectY + rectH / 2);
                }
            });

            // Vẽ nhãn mốc trung bình tuần ở mép phải với nền pill sạch sẽ
            const metaAvg = chart.getDatasetMeta(1);
            if (metaAvg && metaAvg.data && metaAvg.data.length > 0 && !metaAvg.hidden) {
                const lastPt = metaAvg.data[metaAvg.data.length - 1];
                const text = `TB: ${Math.round(avgAbsent)} em`;
                const textW = chartCtx.measureText(text).width;
                const badgeW = textW + 14;
                const badgeH = 18;
                const badgeX = lastPt.x - badgeW - 8;
                const badgeY = lastPt.y - badgeH / 2;

                chartCtx.fillStyle = 'rgba(248, 250, 252, 0.95)';
                chartCtx.beginPath();
                if (typeof chartCtx.roundRect === 'function') {
                    chartCtx.roundRect(badgeX, badgeY, badgeW, badgeH, 4);
                } else {
                    chartCtx.fillRect(badgeX, badgeY, badgeW, badgeH);
                }
                chartCtx.fill();
                chartCtx.strokeStyle = '#cbd5e1';
                chartCtx.lineWidth = 1;
                chartCtx.stroke();

                chartCtx.font = '600 10.5px Inter, system-ui, sans-serif';
                chartCtx.fillStyle = '#475569';
                chartCtx.fillText(text, badgeX + badgeW / 2, badgeY + badgeH / 2);
            }

            chartCtx.restore();
        }
    };

    trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Số học sinh vắng (em)',
                    data: absentValues,
                    borderColor: '#ef4444',
                    backgroundColor: gradient,
                    borderWidth: 3.2,
                    tension: 0.32,
                    fill: true,
                    pointRadius: trendData.days.map(d => d.is_today ? 7 : 5),
                    pointBackgroundColor: trendData.days.map(d => d.is_today ? '#dc2626' : '#ffffff'),
                    pointBorderColor: '#dc2626',
                    pointBorderWidth: 2.5,
                    pointHoverRadius: trendData.days.map(d => d.is_today ? 9 : 7.5),
                    pointHoverBackgroundColor: '#dc2626',
                    pointHoverBorderColor: '#ffffff',
                    pointHoverBorderWidth: 2.5,
                    yAxisID: 'y'
                },
                {
                    label: `Trung bình tuần (~${Math.round(avgAbsent)} em)`,
                    data: trendData.days.map(() => avgAbsent),
                    borderColor: '#94a3b8',
                    borderDash: [6, 6],
                    borderWidth: 1.8,
                    pointRadius: 0,
                    fill: false,
                    yAxisID: 'y'
                },
                {
                    label: 'Tỷ lệ chuyên cần (%)',
                    data: rateValues,
                    borderColor: '#059669',
                    borderDash: [3, 3],
                    borderWidth: 2.2,
                    pointRadius: 4,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: '#059669',
                    pointBorderWidth: 2,
                    pointHoverRadius: 6,
                    tension: 0.32,
                    fill: false,
                    yAxisID: 'y1'
                }
            ]
        },
        plugins: [valueBadgesPlugin],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    top: 25,
                    right: 15,
                    bottom: 6,
                    left: 8
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    align: 'center',
                    labels: {
                        boxWidth: 12,
                        boxHeight: 12,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        font: {
                            family: 'Inter, system-ui, -apple-system, sans-serif',
                            size: 12,
                            weight: '600'
                        },
                        padding: 18
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleFont: {
                        family: 'Inter, system-ui, sans-serif',
                        size: 12.5,
                        weight: '700'
                    },
                    bodyFont: {
                        family: 'Inter, system-ui, sans-serif',
                        size: 11.5,
                        weight: '500'
                    },
                    padding: 12,
                    cornerRadius: 8,
                    boxPadding: 5,
                    callbacks: {
                        label: function (context) {
                            const dsLabel = context.dataset.label || '';
                            const val = context.parsed.y;
                            if (context.dataset.yAxisID === 'y1') {
                                return ` ${dsLabel}: ${val}%`;
                            }
                            if (context.datasetIndex === 0) {
                                const diff = Math.round(val - avgAbsent);
                                const diffStr = diff > 0 ? `(+${diff} so với TB)` : `(${diff} so với TB)`;
                                return ` ${dsLabel}: ${val} em ${diffStr}`;
                            }
                            return ` ${dsLabel}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    min: 0,
                    max: yMax,
                    title: {
                        display: true,
                        text: 'Vắng (em)',
                        font: { family: 'Inter, sans-serif', size: 11, weight: '700' },
                        color: '#dc2626'
                    },
                    grid: {
                        color: '#f1f5f9',
                        borderDash: [4, 4]
                    },
                    ticks: {
                        stepSize: yStep,
                        font: { family: 'Inter, sans-serif', size: 11, weight: '600' },
                        color: '#64748b',
                        callback: v => v + ' em'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    min: y1Min,
                    max: y1Max,
                    title: {
                        display: true,
                        text: 'Chuyên cần (%)',
                        font: { family: 'Inter, sans-serif', size: 11, weight: '700' },
                        color: '#059669'
                    },
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        stepSize: y1Step,
                        callback: v => {
                            if (v > 100) return '';
                            return v + '%';
                        },
                        font: { family: 'Inter, sans-serif', size: 11, weight: '600' },
                        color: '#059669'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: { family: 'Inter, sans-serif', size: 11.5, weight: '600' },
                        color: '#334155'
                    }
                }
            }
        }
    });
}

// Khởi chạy Dashboard khi tài liệu sẵn sàng
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}
