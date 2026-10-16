/**
 * ===================================================================
 * KPI CARDS MODULE - THPT ĐIỀU CẢI DASHBOARD
 * Quản lý Hiển thị Header Phiên & 4 Thẻ KPI Điểm Danh Toàn Trường
 * ===================================================================
 */

export function updateHeaderInfo(currentSession) {
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

export function updateKPIs(currentSession, currentDetails = []) {
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
