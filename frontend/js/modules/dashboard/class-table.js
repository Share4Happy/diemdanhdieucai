/**
 * ===================================================================
 * CLASS TABLE MODULE - THPT ĐIỀU CẢI DASHBOARD
 * Quản lý Bảng Điểm Danh 30 Lớp Học, Lọc Trạng Thái, Modal Ảnh Đối Chứng & Sửa Tay
 * ===================================================================
 */

import { AttendanceAPI, showToast, escapeHtml } from '../../api.js';

const esc = (v) => escapeHtml(v);

export function extractGradeFromClassName(className) {
    if (!className) return null;
    const clean = String(className).trim();
    if (clean.startsWith('10')) return '10';
    if (clean.startsWith('11')) return '11';
    if (clean.startsWith('12')) return '12';
    const match = clean.match(/^(1[0-2])/);
    return match ? match[1] : null;
}

export function updateFilterBadgeCounts(currentDetails = [], activeGrade = 'all') {
    const gradeDetails = currentDetails.filter(d => {
        if (activeGrade === 'all') return true;
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

export function renderAttendanceTable(currentDetails = [], activeGrade = 'all', activeStatus = 'all', searchKeyword = '', onOpenModal = null) {
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

    // 1. Lọc theo Khối (all, 10, 11, 12)
    let filtered = currentDetails.filter(d => {
        if (activeGrade === 'all') return true;
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
        const gradeMsg = activeGrade === 'all' ? 'nào' : `thuộc Khối ${activeGrade}`;
        tbody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 30px; color: var(--text-muted);">
                    <i class="fa-solid fa-filter-circle-xmark" style="font-size: 1.5rem; margin-bottom: 8px; display: block; opacity: 0.5;"></i>
                    Không có lớp ${gradeMsg} phù hợp với bộ lọc hiện tại.
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

        // Trạng thái badge
        let statusBadge = '';
        if (d.status === 'NO_SIGNAL') {
            statusBadge = `<span class="badge-pill" style="background: rgba(239, 68, 68, 0.12); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); font-weight: 600;"><i class="fa-solid fa-triangle-exclamation"></i> Mất tín hiệu</span>`;
        } else if (d.status === 'CAN_KIEM_TRA') {
            statusBadge = `<span class="badge-pill" style="background: rgba(245, 158, 11, 0.12); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.3); font-weight: 600;"><i class="fa-solid fa-circle-question"></i> Cần kiểm tra</span>`;
        } else if (d.is_manual_override) {
            statusBadge = `<span class="badge-pill" style="background: rgba(59, 130, 246, 0.12); color: #2563eb; border: 1px solid rgba(59, 130, 246, 0.3); font-weight: 600;" title="Đã sửa bởi ${esc(d.override_by || '')}: ${esc(d.override_reason || '')}"><i class="fa-solid fa-user-pen"></i> Đã sửa tay</span>`;
        } else if (isAbsentRow) {
            statusBadge = `<span class="badge-pill absent"><i class="fa-solid fa-circle-exclamation"></i> Vắng ${absent}</span>`;
        } else if (isPending) {
            statusBadge = `<span class="badge-pill pending"><i class="fa-regular fa-clock"></i> Chưa xử lý</span>`;
        } else if (d.notes && d.notes.includes('Vượt')) {
            statusBadge = `<span class="badge-pill pending">${esc(d.notes)}</span>`;
        } else {
            statusBadge = `<span class="badge-pill full"><i class="fa-regular fa-circle-check"></i> Đủ sĩ số</span>`;
        }

        const confidenceText = d.confidence_avg 
            ? `${Math.round(d.confidence_avg * 100)}%`
            : (present > 0 ? '95%' : '--');

        const hasImages = Boolean(d.raw_image_path || d.annotated_image_path);
        const photoBtn = hasImages
            ? `<button type="button" class="tbl-action-btn tbl-btn-outline btn-open-modal" data-id="${d.classroom_id}" title="Xem ảnh AI & đối chứng lớp ${esc(d.class_name)}">
                <i class="fa-regular fa-image"></i> Ảnh AI
               </button>`
            : `<span class="tbl-text-empty"><i class="fa-regular fa-image"></i> Chưa có</span>`;

        return `
            <tr class="${isAbsentRow ? 'row-absent-highlight' : ''}">
                <td class="cell-stt" style="text-align: center; color: var(--text-muted); font-weight: 500;">${index + 1}</td>
                <td class="cell-classroom">
                    <strong style="color: var(--text-main); font-size: 0.95rem;">${esc(d.class_name)}</strong>
                </td>
                <td class="cell-room">
                    <span style="color: #64748b; font-size: 0.85rem;"><i class="fa-solid fa-door-open" style="margin-right: 4px; font-size: 0.75rem;"></i>${esc(d.room_number || '--')}</span>
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
                    <button type="button" class="tbl-action-btn tbl-btn-primary btn-open-modal" data-id="${d.classroom_id}" title="Xem chi tiết lớp ${esc(d.class_name)}">
                        <i class="fa-solid fa-arrow-up-right-from-square"></i> Chi tiết
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    tbody.querySelectorAll('.btn-open-modal').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const targetBtn = e.target.closest('button') || e.currentTarget;
            const classId = targetBtn.dataset.id;
            if (typeof onOpenModal === 'function') {
                onOpenModal(classId);
            }
        });
    });
}

export function openImageModal(classroomId, currentDetails = [], onRefreshRequested = null) {
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
            Phòng: <strong>${esc(detail.room_number || '--')}</strong>
            <span style="margin: 0 8px;">•</span>
            Sĩ số: <strong>${detail.standard_count}</strong>
            <span style="margin: 0 8px;">•</span>
            Có mặt: <strong style="color: #16a34a;">${detail.present_count}</strong>
            <span style="margin: 0 8px;">•</span>
            Vắng: <strong style="color: #dc2626;">${detail.absent_count} học sinh</strong>
            ${detail.confidence_avg ? `<span style="margin: 0 8px;">•</span>Độ tin cậy AI: <strong>${Math.round(detail.confidence_avg * 100)}%</strong>` : ''}
        `;
    }

    const overrideBox = document.getElementById('overrideBox');
    const modalAuditInfo = document.getElementById('modalAuditInfo');
    const overridePresentInput = document.getElementById('overridePresentInput');
    const overrideReasonInput = document.getElementById('overrideReasonInput');
    const btnModalOverride = document.getElementById('btnModalOverride');
    const btnSaveOverride = document.getElementById('btnSaveOverride');

    if (overrideBox) overrideBox.style.display = 'none';
    if (overridePresentInput) overridePresentInput.value = detail.present_count;
    if (overrideReasonInput) overrideReasonInput.value = '';

    if (modalAuditInfo) {
        if (detail.is_manual_override) {
            const timeStr = detail.override_at ? new Date(detail.override_at).toLocaleTimeString('vi-VN') : '';
            modalAuditInfo.innerHTML = `<span style="color: #2563eb; font-weight: 500;"><i class="fa-solid fa-user-check"></i> Đã sửa bởi <strong>${esc(detail.override_by || 'Admin')}</strong> lúc ${timeStr}: <em>"${esc(detail.override_reason || '')}"</em></span>`;
        } else if (detail.status === 'NO_SIGNAL') {
            modalAuditInfo.innerHTML = `<span style="color: #ef4444; font-weight: 500;"><i class="fa-solid fa-triangle-exclamation"></i> Camera mất tín hiệu - Hệ thống KHÔNG tính vắng khống.</span>`;
        } else if (detail.status === 'CAN_KIEM_TRA') {
            modalAuditInfo.innerHTML = `<span style="color: #d97706; font-weight: 500;"><i class="fa-solid fa-triangle-exclamation"></i> ${esc(detail.notes || 'Chất lượng ảnh camera kém (quá tối hoặc mờ)')}</span>`;
        } else {
            modalAuditInfo.innerHTML = `<span style="color: #16a34a;"><i class="fa-solid fa-circle-check"></i> Dữ liệu AI nhận diện tự động nguyên bản.</span>`;
        }
    }

    if (btnModalOverride) {
        btnModalOverride.onclick = () => {
            if (overrideBox) {
                overrideBox.style.display = overrideBox.style.display === 'none' ? 'block' : 'none';
            }
        };
    }

    if (btnSaveOverride) {
        btnSaveOverride.onclick = async () => {
            if (!detail.id) {
                showToast('Chưa có bản ghi điểm danh chính thức để điều chỉnh', 'warning');
                return;
            }
            const newPrs = parseInt(overridePresentInput.value, 10);
            const reason = (overrideReasonInput.value || '').trim();
            if (isNaN(newPrs) || newPrs < 0) {
                showToast('Vui lòng nhập sĩ số có mặt hợp lệ (>= 0)', 'warning');
                return;
            }
            if (!reason || reason.length < 2) {
                showToast('Vui lòng nhập lý do điều chỉnh để lưu vết kiểm toán', 'warning');
                return;
            }

            try {
                btnSaveOverride.disabled = true;
                btnSaveOverride.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
                const res = await AttendanceAPI.overrideDetail(detail.id, {
                    present_count: newPrs,
                    reason: reason
                });
                if (res && res.success) {
                    showToast(`Đã cập nhật sĩ số lớp ${detail.class_name}: ${newPrs}/${detail.standard_count}`, 'success');
                    detail.present_count = newPrs;
                    detail.absent_count = Math.max(0, detail.standard_count - newPrs);
                    detail.is_manual_override = true;
                    detail.override_by = res.detail?.override_by || 'Admin';
                    detail.override_reason = reason;
                    detail.override_at = res.detail?.override_at || new Date().toISOString();
                    detail.status = 'OK';

                    if (typeof onRefreshRequested === 'function') {
                        await onRefreshRequested();
                    }
                    openImageModal(classroomId, currentDetails, onRefreshRequested);
                } else {
                    showToast(res?.detail || 'Không thể lưu điều chỉnh', 'error');
                }
            } catch (err) {
                showToast(`Lỗi điều chỉnh sĩ số: ${err.message}`, 'error');
            } finally {
                btnSaveOverride.disabled = false;
                btnSaveOverride.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu Thay Đổi';
            }
        };
    }

    const nowTs = Date.now();
    if (rawImgWrap) {
        if (detail.raw_image_path) {
            const rawUrl = `${detail.raw_image_path}&_t=${nowTs}`;
            rawImgWrap.innerHTML = `<img id="modalRawImg" src="${rawUrl}" alt="Ảnh gốc camera ${esc(detail.class_name)}" style="max-height: 420px; width: 100%; object-fit: contain; border-radius: 8px; cursor: zoom-in;" title="Bấm vào ảnh để phóng to và soi bằng con lăn chuột">`;
            document.getElementById('modalRawImg')?.addEventListener('click', () => {
                if (typeof window.showImgModal === 'function') {
                    window.showImgModal(rawUrl, `Ảnh Gốc Camera - ${esc(detail.class_name)}`);
                }
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
            annotatedImgWrap.innerHTML = `<img id="modalAnnotatedImg" src="${annoUrl}" alt="Ảnh AI khoanh vùng ${esc(detail.class_name)}" style="max-height: 420px; width: 100%; object-fit: contain; border-radius: 8px; cursor: zoom-in;" title="Bấm vào ảnh để phóng to và soi bằng con lăn chuột">`;
            document.getElementById('modalAnnotatedImg')?.addEventListener('click', () => {
                if (typeof window.showImgModal === 'function') {
                    window.showImgModal(annoUrl, `Ảnh AI Đối Chứng - ${esc(detail.class_name)}`);
                }
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
