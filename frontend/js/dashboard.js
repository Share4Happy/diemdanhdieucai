/**
 * ===================================================================
 * dashboard.js - Trang Tổng Quan & Giám Sát Điểm Danh AI (Modular ES6)
 * THPT Điều Cải - Attendance System
 * ===================================================================
 */

import { AttendanceAPI, showToast, escapeHtml } from './api.js';
import { progressModal } from './components/progress_modal.js';

// Import các sub-modules độc lập theo chuẩn ES6
import {
    updateHeaderInfo,
    updateKPIs
} from './modules/dashboard/kpi-cards.js';

import {
    extractGradeFromClassName,
    updateFilterBadgeCounts,
    renderAttendanceTable,
    openImageModal
} from './modules/dashboard/class-table.js';

import {
    loadWeeklyTrendChart,
    resizeTrendChart
} from './modules/dashboard/trend-chart.js';

const esc = (v) => escapeHtml(v);

// ==================== TRẠNG THÁI TOÀN TRANG ====================
let currentSession = null;
let currentDetails = [];
let activeGrade = 'all';       // 'all' | '10' | '11' | '12'
let activeStatus = 'all';      // 'all' | 'absent' | 'full' | 'pending'
let searchKeyword = '';
let isScanning = false;

/**
 * Khởi động ứng dụng Dashboard
 */
function initDashboard() {
    initLiveClock();
    initEventListeners();
    initZoomModal();
    loadDashboardData();
    loadWeeklyTrendChart({}, currentSession);
}

/**
 * Đồng hồ trực quan thời gian thực trên Header
 */
function initLiveClock() {
    const clockEl = document.getElementById('liveClockTime');
    const dateEl = document.getElementById('liveClockDate');
    if (!clockEl && !dateEl) return;

    function updateClock() {
        const now = new Date();
        if (clockEl) {
            clockEl.textContent = now.toLocaleTimeString('vi-VN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
        if (dateEl) {
            dateEl.textContent = now.toLocaleDateString('vi-VN', {
                weekday: 'long',
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });
        }
    }
    updateClock();
    setInterval(updateClock, 1000);
}

/**
 * Gắn các sự kiện click, filter pills, search bar
 */
function initEventListeners() {
    // 1. Quét điểm danh nhanh
    const btnScan = document.getElementById('btnTriggerScan');
    if (btnScan) {
        btnScan.addEventListener('click', handleTriggerScan);
    }

    // 2. Làm mới dữ liệu
    const btnRefresh = document.getElementById('btnRefreshDashboard');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', async () => {
            btnRefresh.classList.add('fa-spin');
            await loadDashboardData();
            await loadWeeklyTrendChart({}, currentSession);
            btnRefresh.classList.remove('fa-spin');
            showToast('Đã làm mới dữ liệu điểm danh', 'info');
        });
    }

    // 3. Tab Chuyển Khối (Tất cả, Khối 10, Khối 11, Khối 12)
    const gradeTabs = document.querySelectorAll('.grade-tab');
    gradeTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            const grade = e.currentTarget.dataset.grade || 'all';
            setGrade(grade);
        });
    });

    function setGrade(grade) {
        activeGrade = grade;
        gradeTabs.forEach(t => {
            if (t.dataset.grade === grade) {
                t.classList.add('active');
            } else {
                t.classList.remove('active');
            }
        });
        updateFilterBadgeCounts(currentDetails, activeGrade);
        renderAttendanceTable(currentDetails, activeGrade, activeStatus, searchKeyword, (id) => {
            openImageModal(id, currentDetails, async () => {
                await loadDashboardData(true);
            });
        });
    }

    // Phím tắt bàn phím chuyển nhanh Khối
    const gradesList = ['all', '10', '11', '12'];
    function switchGradePrev() {
        const idx = gradesList.indexOf(activeGrade);
        const prev = idx > 0 ? gradesList[idx - 1] : gradesList[gradesList.length - 1];
        setGrade(prev);
    }
    function switchGradeNext() {
        const idx = gradesList.indexOf(activeGrade);
        const next = idx < gradesList.length - 1 ? gradesList[idx + 1] : gradesList[0];
        setGrade(next);
    }

    const btnGradePrev = document.getElementById('btnGradePrev');
    const btnGradeNext = document.getElementById('btnGradeNext');
    if (btnGradePrev) btnGradePrev.addEventListener('click', switchGradePrev);
    if (btnGradeNext) btnGradeNext.addEventListener('click', switchGradeNext);

    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === 'ArrowLeft') switchGradePrev();
        else if (e.key === 'ArrowRight') switchGradeNext();
    });

    // 4. Các nút lọc trạng thái (Tất cả, Lớp Vắng, Đủ Sĩ Số, Chưa Xử Lý)
    const filterPills = document.querySelectorAll('.filter-pill');
    filterPills.forEach(pill => {
        pill.addEventListener('click', (e) => {
            filterPills.forEach(p => p.classList.remove('active'));
            const target = e.currentTarget;
            target.classList.add('active');
            activeStatus = target.dataset.status || 'all';
            renderAttendanceTable(currentDetails, activeGrade, activeStatus, searchKeyword, (id) => {
                openImageModal(id, currentDetails, async () => {
                    await loadDashboardData(true);
                });
            });
        });
    });

    // 5. Ô tìm kiếm lớp học
    const searchInput = document.getElementById('searchClassInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchKeyword = e.target.value.trim().toLowerCase();
            renderAttendanceTable(currentDetails, activeGrade, activeStatus, searchKeyword, (id) => {
                openImageModal(id, currentDetails, async () => {
                    await loadDashboardData(true);
                });
            });
        });
    }

    // 6. Đóng modal xem ảnh lớp
    const btnCloseModal = document.getElementById('modalCloseBtn');
    const imgModal = document.getElementById('imageModal');
    if (btnCloseModal && imgModal) {
        btnCloseModal.addEventListener('click', () => {
            imgModal.classList.remove('active');
            imgModal.style.display = 'none';
        });
    }
    if (imgModal) {
        imgModal.addEventListener('click', (e) => {
            if (e.target === imgModal) {
                imgModal.classList.remove('active');
                imgModal.style.display = 'none';
            }
        });
    }

    // 7. Nút xem toàn màn hình
    const btnFullscreen = document.getElementById('btnFullscreenToggle');
    if (btnFullscreen) {
        btnFullscreen.addEventListener('click', () => {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(err => {
                    console.warn('Lỗi bật Fullscreen:', err);
                });
                btnFullscreen.innerHTML = '<i class="fa-solid fa-compress"></i> Thu nhỏ';
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                }
                btnFullscreen.innerHTML = '<i class="fa-solid fa-expand"></i> Toàn màn hình';
            }
        });
    }

    // 8. Tự động kiểm tra cập nhật mỗi 30 giây (nếu không đang quét)
    setInterval(() => {
        if (!isScanning && document.visibilityState === 'visible') {
            loadDashboardData(true);
        }
    }, 30000);
}

/**
 * Modal soi ảnh kính lúp
 */
let currentZoomScale = 1;
function initZoomModal() {
    const modal = document.getElementById('modalZoomPreview');
    const btnClose = document.getElementById('btnZoomClose');
    const btnIn = document.getElementById('btnZoomIn');
    const btnOut = document.getElementById('btnZoomOut');
    const btnReset = document.getElementById('btnZoomReset');
    const img = document.getElementById('zoomPreviewImg');

    if (!modal) return;

    function applyScale() {
        if (img) img.style.transform = `scale(${currentZoomScale})`;
    }

    if (btnIn) btnIn.onclick = () => {
        currentZoomScale = Math.min(3.5, currentZoomScale + 0.25);
        applyScale();
    };
    if (btnOut) btnOut.onclick = () => {
        currentZoomScale = Math.max(0.5, currentZoomScale - 0.25);
        applyScale();
    };
    if (btnReset) btnReset.onclick = () => {
        currentZoomScale = 1;
        applyScale();
    };

    if (btnClose) btnClose.onclick = closeImgModal;

    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeImgModal();
    });

    if (img) {
        img.addEventListener('wheel', (e) => {
            e.preventDefault();
            if (e.deltaY < 0) {
                currentZoomScale = Math.min(3.5, currentZoomScale + 0.15);
            } else {
                currentZoomScale = Math.max(0.5, currentZoomScale - 0.15);
            }
            applyScale();
        }, { passive: false });
    }
}

export function showImgModal(src, title) {
    const modal = document.getElementById('modalZoomPreview');
    const img = document.getElementById('zoomPreviewImg');
    const titleEl = document.getElementById('zoomModalTitle');

    if (!modal || !img) return;

    img.src = src;
    if (titleEl) titleEl.textContent = title || 'Ảnh Đối Chứng';
    currentZoomScale = 1;
    img.style.transform = 'scale(1)';

    modal.classList.add('active');
    modal.style.display = 'flex';
}

export function closeImgModal() {
    const modal = document.getElementById('modalZoomPreview');
    const img = document.getElementById('zoomPreviewImg');
    if (!modal) return;
    modal.classList.remove('active');
    modal.style.display = 'none';
    if (img) img.src = '';
    currentZoomScale = 1;
}

window.showImgModal = showImgModal;
window.closeImgModal = closeImgModal;

/**
 * Tải dữ liệu phiên điểm danh mới nhất
 */
async function loadDashboardData(suppressRedirect = false) {
    try {
        const res = await AttendanceAPI.getLatestSession();

        if (res && res.session) {
            currentSession = res.session;
            currentDetails = res.details || [];
        } else {
            currentSession = null;
            currentDetails = [];
        }

        updateHeaderInfo(currentSession);
        updateKPIs(currentSession, currentDetails);
        updateFilterBadgeCounts(currentDetails, activeGrade);
        renderAttendanceTable(currentDetails, activeGrade, activeStatus, searchKeyword, (id) => {
            openImageModal(id, currentDetails, async () => {
                await loadDashboardData(true);
            });
        });

    } catch (err) {
        console.error('Lỗi khi tải dữ liệu dashboard:', err);
    }
}

/**
 * Kích hoạt quét điểm danh toàn trường
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

        const result = await progressModal.startAttendanceScan({
            onComplete: async () => {
                await loadDashboardData();
                await loadWeeklyTrendChart({}, currentSession);
            },
            onError: (err) => {
                showToast('Lỗi khi kích hoạt quét điểm danh: ' + (err.message || err), 'danger');
            }
        });

        if (result && result.success) {
            showToast('Đã hoàn tất phiên điểm danh 30 lớp!', 'success');
            await loadDashboardData();
            await loadWeeklyTrendChart({}, currentSession);
        } else if (result) {
            showToast(result.message || 'Quét điểm danh hoàn tất', 'info');
            await loadDashboardData();
            await loadWeeklyTrendChart({}, currentSession);
        }

    } catch (err) {
        console.error('Lỗi khi quét điểm danh:', err);
    } finally {
        isScanning = false;
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = 'Quét Điểm Danh';
        }
    }
}

if (typeof window !== 'undefined') {
    window.handleTriggerScan = handleTriggerScan;
    window.triggerAttendanceScan = handleTriggerScan;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}

let dashboardWindowResizeTimer = null;
window.addEventListener('resize', () => {
    if (dashboardWindowResizeTimer) clearTimeout(dashboardWindowResizeTimer);
    dashboardWindowResizeTimer = setTimeout(() => {
        resizeTrendChart();
    }, 150);
});
