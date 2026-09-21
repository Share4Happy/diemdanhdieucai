/**
 * =====================================================
 * DASHBOARD REDESIGN - Table-based view
 * =====================================================
 */

import { AttendanceAPI, getMediaUrl, showToast } from './api.js';

let currentDetails = [];
let currentFilter = 'all';
let currentClassInfo = {
    classId: null,
    name: '',
    room: '',
    rawPath: '',
    annPath: '',
    standard: 40,
    present: 0,
    absent: 0
};

// Load data on page load
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
});

function initDashboard() {
    // Setup event listeners
    document.getElementById('btnTriggerScan')?.addEventListener('click', handleTriggerScan);
    document.getElementById('searchInput')?.addEventListener('input', debounce(renderTable, 300));
    document.getElementById('filterSelect')?.addEventListener('change', handleFilterChange);
    document.getElementById('btnRefresh')?.addEventListener('click', loadLatestAttendance);
    document.getElementById('modalClose')?.addEventListener('click', closeModal);
    document.getElementById('modalBtnRescan')?.addEventListener('click', handleRescanClass);

    // Load initial data
    loadLatestAttendance();

    // Auto-refresh every 30 seconds
    setInterval(loadLatestAttendance, 30000);
}

async function loadLatestAttendance() {
    try {
        const data = await AttendanceAPI.getLatest();
        
        if (!data || !data.session) {
            // Empty state
            document.getElementById('sessionBadge').innerText = 'Chưa có dữ liệu';
            document.getElementById('sessionMeta').innerText = 'Bấm nút "Quét Điểm Danh" để bắt đầu';
            updateKPIs(null);
            currentDetails = [];
            renderTable();
            return;
        }

        const s = data.session;
        currentDetails = data.details || [];

        // Update session info
        document.getElementById('sessionBadge').innerText = `Phiên: ${s.session_code || 'N/A'}`;
        document.getElementById('sessionMeta').innerText = `${s.scan_date || ''} • ${s.scan_time || ''} • ${s.status === 'COMPLETED' ? 'Hoàn tất' : s.status}`;

        // Update KPIs
        updateKPIs(s);

        // Update progress
        updateProgress(s);

        // Render table
        renderTable();

    } catch (err) {
        console.error("Lỗi tải dữ liệu:", err);
        showToast("Không thể tải dữ liệu điểm danh: " + err.message, "danger");
    }
}

function updateKPIs(session) {
    if (!session) {
        document.getElementById('kpiClasses').innerText = '--';
        document.getElementById('kpiStandard').innerText = '--';
        document.getElementById('kpiPresent').innerText = '--';
        document.getElementById('kpiAbsent').innerText = '--';
        document.getElementById('kpiRate').innerText = '--%';
        return;
    }

    document.getElementById('kpiClasses').innerText = session.total_classes || 0;
    document.getElementById('kpiStandard').innerText = session.total_standard || 0;
    document.getElementById('kpiPresent').innerText = session.total_present || 0;
    document.getElementById('kpiAbsent').innerText = session.total_absent || 0;

    const rate = session.total_standard > 0 
        ? ((session.total_present / session.total_standard) * 100).toFixed(1) 
        : 0;
    document.getElementById('kpiRate').innerText = `${rate}%`;
}

function updateProgress(session) {
    const total = session.total_classes || 0;
    const completed = currentDetails.filter(d => d.status === 'COMPLETED').length;
    const percentage = total > 0 ? (completed / total) * 100 : 0;

    document.getElementById('progressFill').style.width = `${percentage}%`;
    document.getElementById('progressText').innerText = `${completed}/${total} lớp`;
}

function renderTable() {
    const tbody = document.getElementById('classroomsTableBody');
    const searchVal = document.getElementById('searchInput')?.value.toLowerCase().trim() || '';

    // Filter data
    const filtered = currentDetails.filter(d => {
        const matchSearch = d.class_name.toLowerCase().includes(searchVal) || 
                          (d.room_number || '').toLowerCase().includes(searchVal);
        if (!matchSearch) return false;

        if (currentFilter === 'full') return d.absent_count === 0;
        if (currentFilter === 'absent') return d.absent_count > 0;
        return true;
    });

    // Empty state
    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" class="table-empty">
                    <div class="table-empty-icon"><i class="fa-solid fa-inbox"></i></div>
                    <div class="table-empty-title">Không có dữ liệu</div>
                    <div class="table-empty-text">
                        ${searchVal ? 'Không tìm thấy lớp học phù hợp với tìm kiếm' : 'Chưa có dữ liệu điểm danh'}
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    // Render rows
    tbody.innerHTML = filtered.map((d, index) => {
        const isFull = d.absent_count === 0;
        const rate = d.standard_count > 0 
            ? ((d.present_count / d.standard_count) * 100).toFixed(1) 
            : 0;
        
        const statusClass = isFull ? 'success' : (d.absent_count <= 2 ? 'warning' : 'danger');
        const thumbUrl = getMediaUrl(d.annotated_image_path || d.raw_image_path) || '';

        return `
            <tr>
                <td class="table-cell-center">${index + 1}</td>
                <td>
                    <div class="table-cell-primary">${d.class_name}</div>
                    <div class="table-cell-secondary">Mã: ${d.camera_id || 'N/A'}</div>
                </td>
                <td>${d.room_number || '-'}</td>
                <td class="table-cell-numeric table-cell-center">${d.standard_count || 0}</td>
                <td class="table-cell-numeric table-cell-center" style="color: var(--success); font-weight: var(--font-semibold);">
                    ${d.present_count || 0}
                </td>
                <td class="table-cell-numeric table-cell-center" style="color: var(--danger); font-weight: var(--font-semibold);">
                    ${d.absent_count || 0}
                </td>
                <td class="table-cell-center">
                    <span class="badge badge-${statusClass}">${rate}%</span>
                </td>
                <td class="table-cell-center">
                    <span class="status-badge online">
                        <span class="status-dot pulse"></span>
                        Online
                    </span>
                </td>
                <td class="table-cell-center">
                    <span class="badge badge-primary">
                        <i class="fa-solid fa-check"></i>
                    </span>
                </td>
                <td class="table-cell-center">
                    ${thumbUrl ? `<img src="${thumbUrl}" alt="Camera" class="class-thumbnail" onclick="openDetailModal(${index})" />` : '-'}
                </td>
                <td class="table-cell-center">
                    <div class="table-actions">
                        <button class="btn btn-icon btn-xs btn-secondary" onclick="openDetailModal(${index})" title="Xem chi tiết">
                            <i class="fa-solid fa-eye"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function handleFilterChange(e) {
    currentFilter = e.target.value;
    renderTable();
}

async function handleTriggerScan() {
    const btn = document.getElementById('btnTriggerScan');
    if (!btn) return;

    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang quét...';

    try {
        const result = await AttendanceAPI.triggerScan();
        showToast("Quét điểm danh thành công!", "success");
        
        // Wait a bit then reload
        setTimeout(() => {
            loadLatestAttendance();
        }, 2000);
    } catch (err) {
        console.error("Lỗi quét điểm danh:", err);
        showToast("Lỗi: " + err.message, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Modal functions
window.openDetailModal = function(index) {
    const filtered = getFilteredData();
    if (index < 0 || index >= filtered.length) return;

    const d = filtered[index];
    currentClassInfo = {
        classId: d.camera_id,
        name: d.class_name,
        room: d.room_number || 'N/A',
        rawPath: d.raw_image_path,
        annPath: d.annotated_image_path,
        standard: d.standard_count,
        present: d.present_count,
        absent: d.absent_count
    };

    // Update modal content
    document.getElementById('modalClassTitle').innerText = `Chi Tiết: ${d.class_name}`;
    document.getElementById('modalClassSub').innerText = 
        `${d.room_number || 'Phòng N/A'} • Sĩ số: ${d.standard_count} • Có mặt: ${d.present_count} • Vắng: ${d.absent_count}`;

    document.getElementById('modalRawImg').src = getMediaUrl(d.raw_image_path) || '';
    document.getElementById('modalAnnotatedImg').src = getMediaUrl(d.annotated_image_path) || '';

    // Update ROI link
    const roiLink = document.getElementById('modalBtnEditRoi');
    if (roiLink) {
        roiLink.href = `roi-config.html?class=${encodeURIComponent(d.camera_id || d.class_name)}`;
    }

    // Show modal
    document.getElementById('imageModal').classList.add('active');
};

function closeModal() {
    document.getElementById('imageModal').classList.remove('active');
}

async function handleRescanClass() {
    if (!currentClassInfo.classId) {
        showToast("Không xác định được lớp học", "warning");
        return;
    }

    const btn = document.getElementById('modalBtnRescan');
    if (!btn) return;

    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang quét...';

    try {
        // Trigger a new scan
        await AttendanceAPI.triggerScan();
        showToast(`Đang quét lại lớp ${currentClassInfo.name}...`, "success");
        
        setTimeout(() => {
            closeModal();
            loadLatestAttendance();
        }, 2000);
    } catch (err) {
        console.error("Lỗi quét lại:", err);
        showToast("Lỗi: " + err.message, "danger");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function getFilteredData() {
    const searchVal = document.getElementById('searchInput')?.value.toLowerCase().trim() || '';
    return currentDetails.filter(d => {
        const matchSearch = d.class_name.toLowerCase().includes(searchVal) || 
                          (d.room_number || '').toLowerCase().includes(searchVal);
        if (!matchSearch) return false;

        if (currentFilter === 'full') return d.absent_count === 0;
        if (currentFilter === 'absent') return d.absent_count > 0;
        return true;
    });
}

// Utility: debounce
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Close modal on ESC key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
    }
});

// Close modal on backdrop click
document.getElementById('imageModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'imageModal') {
        closeModal();
    }
});
