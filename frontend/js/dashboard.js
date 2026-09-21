/**
 * =====================================================
 * DASHBOARD - Redesigned with Table View
 * =====================================================
 */

import { AttendanceAPI, getMediaUrl, showToast } from './api.js';

let currentDetails = [];

// Load data on page load
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
});

function initDashboard() {
    // Setup event listeners
    document.getElementById('btnTriggerScan')?.addEventListener('click', handleTriggerScan);
    document.getElementById('btnRefresh')?.addEventListener('click', loadLatestAttendance);
    document.getElementById('modalClose')?.addEventListener('click', closeModal);

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

        // Render statistics widgets
        renderStatistics();

    } catch (err) {
        console.error("Lỗi tải dữ liệu:", err);
        showToast("Không thể tải dữ liệu điểm danh: " + err.message, "danger");
    }
}

function renderStatistics() {
    if (currentDetails.length === 0) return;

    // Calculate statistics
    const fullClasses = currentDetails.filter(d => d.absent_count === 0);
    const warningClasses = currentDetails.filter(d => d.absent_count >= 1 && d.absent_count <= 3);
    const dangerClasses = currentDetails.filter(d => d.absent_count > 3);
    const maxAbsent = Math.max(...currentDetails.map(d => d.absent_count), 0);
    const maxAbsentClass = currentDetails.find(d => d.absent_count === maxAbsent);

    // Update summary
    document.getElementById('statsFullClasses').textContent = fullClasses.length;
    document.getElementById('statsWarningClasses').textContent = warningClasses.length;
    document.getElementById('statsDangerClasses').textContent = dangerClasses.length;
    document.getElementById('statsMaxAbsent').textContent = maxAbsent > 0
        ? `${maxAbsent} (${maxAbsentClass?.class_name || 'N/A'})`
        : 'Không có';

    // Render top absent classes
    renderTopAbsent();

    // Render rate distribution
    renderRateDistribution();
}

function renderTopAbsent() {
    const container = document.getElementById('topAbsentList');
    const sorted = [...currentDetails].sort((a, b) => b.absent_count - a.absent_count);
    const top5 = sorted.slice(0, 5).filter(d => d.absent_count > 0);

    if (top5.length === 0) {
        container.innerHTML = `
            <div class="empty-state-mini">
                <i class="fa-solid fa-circle-check"></i>
                <p>Tất cả lớp đều đủ sĩ số!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = top5.map((d, index) => {
        const rankClass = index === 0 ? 'rank-1' : index === 1 ? 'rank-2' : index === 2 ? 'rank-3' : '';
        return `
            <div class="ranking-item">
                <div class="ranking-badge ${rankClass}">${index + 1}</div>
                <div class="ranking-info">
                    <div class="ranking-class">${d.class_name}</div>
                    <div class="ranking-room">${d.room_number || 'N/A'}</div>
                </div>
                <div class="ranking-count">
                    <i class="fa-solid fa-user-xmark"></i>
                    ${d.absent_count}
                </div>
            </div>
        `;
    }).join('');
}

function renderRateDistribution() {
    // Calculate distribution
    const rate100 = currentDetails.filter(d => d.absent_count === 0).length;
    const rate90 = currentDetails.filter(d => {
        const rate = (d.present_count / d.standard_count) * 100;
        return rate >= 90 && rate < 100;
    }).length;
    const rate80 = currentDetails.filter(d => {
        const rate = (d.present_count / d.standard_count) * 100;
        return rate >= 80 && rate < 90;
    }).length;
    const rate70 = currentDetails.filter(d => {
        const rate = (d.present_count / d.standard_count) * 100;
        return rate < 80;
    }).length;

    const total = currentDetails.length || 1;

    // Update bars
    document.getElementById('bar100').style.width = `${(rate100 / total) * 100}%`;
    document.getElementById('bar90').style.width = `${(rate90 / total) * 100}%`;
    document.getElementById('bar80').style.width = `${(rate80 / total) * 100}%`;
    document.getElementById('bar70').style.width = `${(rate70 / total) * 100}%`;

    document.getElementById('count100').textContent = rate100;
    document.getElementById('count90').textContent = rate90;
    document.getElementById('count80').textContent = rate80;
    document.getElementById('count70').textContent = rate70;
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

// Export for potential reuse
export { loadLatestAttendance };
