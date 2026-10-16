/**
 * ===================================================================
 * MATRIX WALL MODULE - THPT ĐIỀU CẢI AI CAMERA
 * Quản lý Hiển thị Grid 30 Kênh, Menu Thao Tác, Live View & Batch Actions
 * ===================================================================
 */

import { CameraAPI, showToast, escapeHtml } from '../../api.js';
import { progressModal } from '../../components/progress_modal.js';

const esc = (v) => escapeHtml(v);

let matrixCameras = [];
let matrixSelectedIds = new Set();
let currentZoom = 1;

// Callbacks hooks injected from cameras.js or camera-crud.js
let externalHandlers = {
    onEditCamera: null,
    onDeleteCamera: null,
    onRefreshCameras: null
};

export function setMatrixCallbacks(handlers) {
    externalHandlers = { ...externalHandlers, ...handlers };
}

export function setMatrixCameras(cams) {
    matrixCameras = cams || [];
}

export function getMatrixSelectedIds() {
    return matrixSelectedIds;
}

export function clearMatrixSelection() {
    matrixSelectedIds.clear();
    updateBatchActionBar();
}

/**
 * Hiển thị Ma Trận Phòng Học (TV Wall 30 Camera)
 */
export function renderMatrixWall(cameras = null) {
    if (cameras) {
        matrixCameras = cameras;
    }
    const container = document.getElementById('matrixGrid');
    if (!container) return;
    container.innerHTML = '';

    if (!matrixCameras || matrixCameras.length === 0) {
        container.innerHTML = `
            <div class="camera-empty-state" style="grid-column: 1 / -1; text-align: center; padding: 3.5rem 1.5rem; color: var(--text-muted, #64748b);">
                <div style="width: 60px; height: 60px; border-radius: 50%; background: rgba(14, 165, 233, 0.08); color: var(--primary, #0284c7); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 1rem;">
                    <i class="fa-solid fa-video-slash" style="font-size: 1.6rem;"></i>
                </div>
                <h3 style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary, #0f172a); margin: 0 0 0.5rem 0;">Chưa có camera nào trong hệ thống</h3>
                <p style="font-size: 0.875rem; color: var(--text-muted, #64748b); max-width: 480px; margin: 0 auto 1.5rem auto; line-height: 1.5;">
                    Hệ thống chưa ghi nhận camera nào. Bạn có thể thêm camera từ máy tính/Webcam, camera IP RTSP của từng lớp học hoặc quét tự động từ đầu ghi NVR.
                </p>
                <div style="display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap;">
                    <button type="button" class="btn btn-primary btn-sm" id="btnEmptyAddCam">
                        <i class="fa-solid fa-plus"></i> Thêm Camera
                    </button>
                    <button type="button" class="btn btn-success btn-sm" id="btnEmptyAddNvr">
                        <i class="fa-solid fa-server"></i> Thêm Đầu Ghi (NVR)
                    </button>
                </div>
            </div>`;
        const btnAdd = container.querySelector('#btnEmptyAddCam');
        if (btnAdd) btnAdd.onclick = () => document.getElementById('btnAddCamera')?.click();
        const btnNvr = container.querySelector('#btnEmptyAddNvr');
        if (btnNvr) btnNvr.onclick = () => document.getElementById('btnAddNVR')?.click();
        return;
    }

    const badge = document.getElementById('matrixOnlineBadge') || document.getElementById('matrixStatus');
    if (badge) {
        const activeCams = matrixCameras.filter(c => c.is_active).length;
        badge.innerText = `${activeCams}/${matrixCameras.length} Camera Sẵn Sàng`;
    }

    matrixCameras.forEach((cam, idx) => {
        const chNum = cam.channel_number || (idx + 1);
        const card = document.createElement('div');
        const isSelected = matrixSelectedIds.has(cam.id);
        card.className = `matrix-card ${isSelected ? 'selected' : ''}`;
        card.id = `matrix_card_${cam.id}`;
        card.setAttribute('data-id', cam.id);

        const snapUrl = `/storage/captures/latest/Lop_${cam.id}.jpg?t=${Date.now()}`;
        const isOnline = cam.is_active;

        const standardCount = cam.standard_count || 40;
        const hasScanned = Boolean(cam.has_scanned);
        const presentCount = typeof cam.present_count === 'number' ? cam.present_count : 0;
        const absentCount = typeof cam.absent_count === 'number' ? cam.absent_count : (hasScanned ? Math.max(0, standardCount - presentCount) : 0);

        // Chuỗi hiển thị thời gian quét gần nhất
        let scanTimeDisplay = 'Chưa quét';
        if (cam.scan_time) {
            scanTimeDisplay = cam.scan_time;
            if (cam.scan_date) {
                scanTimeDisplay += ` • ${cam.scan_date}`;
            }
        }

        // Huy hiệu sĩ số & học sinh có mặt
        let attBadgeHtml = '';
        let absentBadgeHtml = '';
        if (hasScanned) {
            const attendanceRate = standardCount > 0 ? (presentCount / standardCount) : 1;
            let attClass = 'att-badge-full';
            if (absentCount > 2 || attendanceRate < 0.9) {
                attClass = 'att-badge-danger';
            } else if (absentCount > 0) {
                attClass = 'att-badge-warning';
            }

            attBadgeHtml = `<span class="matrix-att-pill ${attClass}" title="Có mặt ${presentCount}/${standardCount} HS (Vắng ${absentCount} HS)">` +
                           `<i class="fa-solid fa-user-check"></i> Có mặt: <strong>${presentCount}/${standardCount}</strong> HS</span>`;

            if (absentCount > 0) {
                absentBadgeHtml = `<span class="matrix-absent-chip warning" title="Vắng ${absentCount} học sinh">Vắng ${absentCount} HS</span>`;
            } else {
                absentBadgeHtml = '';
            }
        } else {
            attBadgeHtml = `<span class="matrix-att-pill att-badge-pending" title="Chưa có dữ liệu phiên quét hôm nay • Sĩ số: ${standardCount} HS">` +
                           `<i class="fa-solid fa-users"></i> Sĩ số: <strong>${standardCount}</strong> HS</span>`;
            absentBadgeHtml = `<span class="matrix-absent-chip pending" title="Đang chờ phiên quét">Chờ quét</span>`;
        }

        const fallbackSvg = `data:image/svg+xml;charset=UTF-8,%3Csvg%20width%3D%22400%22%20height%3D%22225%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Crect%20fill%3D%22%231e293b%22%20width%3D%22400%22%20height%3D%22225%22%2F%3E%3Ctext%20fill%3D%22%2394a3b8%22%20font-family%3D%22sans-serif%22%20font-size%3D%2214%22%20x%3D%2250%25%22%20y%3D%2250%25%22%20text-anchor%3D%22middle%22%3E${encodeURIComponent(cam.name)}%20(Ch%C6%B0a%20c%C3%B3%20%E1%BA%A3nh)%3C%2Ftext%3E%3C%2Fsvg%3E`;

        card.innerHTML = `
            <div class="matrix-card-screen">
                <img src="${snapUrl}" class="matrix-thumb-img" alt="${esc(cam.name)}" loading="lazy" 
                     onerror="this.onerror=null; this.src='${fallbackSvg}';">
                
                <!-- Ô chọn phòng -->
                <div class="matrix-card-select" title="Chọn phòng này để thao tác">
                    <input type="checkbox" class="matrix-card-checkbox" data-id="${cam.id}" ${isSelected ? 'checked' : ''}>
                </div>

                <!-- OSD số kênh & trạng thái -->
                <div class="matrix-osd-top" style="left: 36px; right: 42px;">
                    <span class="matrix-ch-badge">CH${String(chNum).padStart(2, '0')}</span>
                    <span class="matrix-status-dot ${isOnline ? '' : 'offline'}" title="${isOnline ? 'Đang kích hoạt' : 'Tạm dừng'}"></span>
                </div>

                <!-- OSD thời gian quét gần nhất -->
                <div class="matrix-osd-bottom-time" title="Thời gian quét điểm danh gần nhất">
                    <i class="fa-regular fa-clock"></i> ${cam.scan_time || 'Chưa quét'}
                </div>

                <!-- Nút 3 chấm góc phải trên cùng thẻ phòng -->
                <div class="matrix-card-menu">
                    <button type="button" class="card-menu-btn" title="Tùy chọn phòng ${esc(cam.name)}" data-id="${cam.id}">
                        <i class="fa-solid fa-ellipsis-vertical"></i>
                    </button>
                    <div class="card-dropdown-menu" id="card_menu_${cam.id}">
                        <button type="button" class="card-dropdown-item menu-item-view" data-id="${cam.id}" data-name="${encodeURIComponent(cam.name)}">
                            <i class="fa-solid fa-expand" style="color: #0284c7;"></i> Xem trực tiếp
                        </button>
                        <button type="button" class="card-dropdown-item menu-item-refresh-snap" data-id="${cam.id}">
                            <i class="fa-solid fa-camera" style="color: #10b981;"></i> Chụp lại ảnh phòng này
                        </button>
                        <button type="button" class="card-dropdown-item menu-item-edit" data-id="${cam.id}">
                            <i class="fa-solid fa-pen-to-square" style="color: #f59e0b;"></i> Chỉnh sửa thông tin
                        </button>
                        <button type="button" class="card-dropdown-item menu-item-roi" data-id="${cam.id}">
                            <i class="fa-solid fa-draw-polygon" style="color: #8b5cf6;"></i> Cấu hình vùng ROI
                        </button>
                        <div class="card-dropdown-divider"></div>
                        <button type="button" class="card-dropdown-item text-danger menu-item-delete" data-id="${cam.id}" data-name="${encodeURIComponent(cam.name)}">
                            <i class="fa-solid fa-trash-can"></i> Xóa phòng này
                        </button>
                    </div>
                </div>
            </div>
            <div class="matrix-card-footer">
                <div class="matrix-footer-top-row">
                    <div class="matrix-footer-meta">
                        <div class="matrix-class-title" title="${esc(cam.name)}">${esc(cam.name)}</div>
                        <div class="matrix-class-room">${esc(cam.room_number || `Phòng ${100 + chNum}`)}</div>
                    </div>
                    ${attBadgeHtml}
                </div>
                <div class="matrix-footer-bottom-row">
                    <div class="matrix-scan-meta" title="Lần quét gần nhất: ${scanTimeDisplay}">
                        <i class="fa-solid fa-clock"></i> <span>Quét: ${cam.scan_time || 'Chưa quét'}</span>
                    </div>
                    ${absentBadgeHtml}
                </div>
            </div>
        `;
        container.appendChild(card);
    });

    // Checkbox chọn / bỏ chọn phòng
    container.querySelectorAll('.matrix-card-checkbox').forEach(cb => {
        cb.addEventListener('change', (e) => {
            e.stopPropagation();
            const id = parseInt(cb.getAttribute('data-id'));
            const card = document.getElementById(`matrix_card_${id}`);
            if (cb.checked) {
                matrixSelectedIds.add(id);
                if (card) card.classList.add('selected');
            } else {
                matrixSelectedIds.delete(id);
                if (card) card.classList.remove('selected');
            }
            updateBatchActionBar();
        });

        cb.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    });

    // Nút 3 chấm mở menu
    container.querySelectorAll('.card-menu-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = btn.getAttribute('data-id');
            const targetMenu = document.getElementById(`card_menu_${id}`);
            const isCurrentlyOpen = targetMenu && targetMenu.classList.contains('show');

            closeAllCardMenus();

            if (!isCurrentlyOpen && targetMenu) {
                targetMenu.classList.add('show');
                btn.classList.add('active');
                const card = btn.closest('.matrix-card');
                if (card) card.style.zIndex = '99';
            }
        });
    });

    // Hành động Xem trực tiếp từ menu 3 chấm
    container.querySelectorAll('.menu-item-view').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeAllCardMenus();
            const id = btn.getAttribute('data-id');
            const name = decodeURIComponent(btn.getAttribute('data-name'));
            openLiveModal(id, name);
        });
    });

    // Hành động Chụp lại ảnh phòng này từ menu 3 chấm
    container.querySelectorAll('.menu-item-refresh-snap').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            closeAllCardMenus();
            const id = parseInt(btn.getAttribute('data-id'));
            const card = document.getElementById(`matrix_card_${id}`);
            const camName = card?.querySelector('.matrix-cam-title')?.textContent?.trim() || `Phòng ${id}`;
            try {
                const res = await progressModal.startCaptureSingle(id, camName, {
                    onComplete: () => {
                        const img = card?.querySelector('.matrix-thumb-img');
                        if (img) {
                            img.src = `/storage/captures/latest/Lop_${id}.jpg?t=${Date.now()}`;
                        }
                    }
                });
                if (res && res.success) {
                    showToast(res.message || 'Chụp ảnh thành công!', 'success');
                    const img = card?.querySelector('.matrix-thumb-img');
                    if (img) {
                        img.src = `/storage/captures/latest/Lop_${id}.jpg?t=${Date.now()}`;
                    }
                }
            } catch (err) {
                showToast('Lỗi chụp ảnh: ' + (err.message || err), 'danger');
            }
        });
    });

    // Hành động Chỉnh sửa từ menu 3 chấm
    container.querySelectorAll('.menu-item-edit').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeAllCardMenus();
            const id = parseInt(btn.getAttribute('data-id'));
            if (typeof externalHandlers.onEditCamera === 'function') {
                externalHandlers.onEditCamera(id);
            }
        });
    });

    // Hành động Cấu hình vùng ROI từ menu 3 chấm (Mở popup trực tiếp trên trang)
    container.querySelectorAll('.menu-item-roi').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeAllCardMenus();
            const id = btn.getAttribute('data-id');
            const card = document.getElementById(`matrix_card_${id}`);
            const camName = card?.querySelector('.matrix-class-title')?.textContent?.trim() || `Phòng ${id}`;
            openRoiModal(id, camName);
        });
    });

    // Hành động Xóa riêng phòng này từ menu 3 chấm
    container.querySelectorAll('.menu-item-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeAllCardMenus();
            const id = parseInt(btn.getAttribute('data-id'));
            const name = decodeURIComponent(btn.getAttribute('data-name'));
            if (typeof externalHandlers.onDeleteCamera === 'function') {
                externalHandlers.onDeleteCamera(id, name);
            }
        });
    });

    // Click vào thẻ phòng để xem trực tiếp (nếu không bấm vào checkbox hay menu)
    container.querySelectorAll('.matrix-card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (e.target.closest('.matrix-card-select') || e.target.closest('.matrix-card-menu')) {
                return;
            }
            const id = card.getAttribute('data-id');
            const cam = matrixCameras.find(c => c.id === parseInt(id));
            if (cam) {
                openLiveModal(cam.id, cam.name);
            }
        });
    });

    updateBatchActionBar();
}

/**
 * Đóng tất cả dropdown 3 chấm trên các thẻ phòng
 */
export function closeAllCardMenus() {
    document.querySelectorAll('.card-dropdown-menu.show').forEach(m => m.classList.remove('show'));
    document.querySelectorAll('.card-menu-btn.active').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.matrix-card').forEach(c => {
        if (!c.classList.contains('selected')) {
            c.style.zIndex = '';
        }
    });
}

/**
 * Cập nhật thanh thao tác xoá nhỏ khi chọn nhiều phòng
 */
export function updateBatchActionBar() {
    const bar = document.getElementById('batchActionBar');
    const countEl = document.getElementById('batchSelectedCount');
    const count = matrixSelectedIds.size;

    if (countEl) countEl.innerText = count;

    if (bar) {
        if (count > 0) {
            bar.classList.add('show');
        } else {
            bar.classList.remove('show');
        }
    }
}

/**
 * Xóa nhanh tất cả camera đã chọn qua checkbox
 */
export async function deleteSelectedCameras() {
    const count = matrixSelectedIds.size;
    if (count === 0) {
        showToast('Vui lòng chọn ít nhất 1 phòng để xóa.', 'warning');
        return;
    }

    const selectedCams = matrixCameras.filter(c => matrixSelectedIds.has(c.id));
    const names = selectedCams.slice(0, 3).map(c => c.name).join(', ') + (count > 3 ? ` và ${count - 3} phòng khác` : '');

    let confirmed = false;
    if (window.ConfirmationDialog && typeof window.ConfirmationDialog.confirm === 'function') {
        confirmed = await window.ConfirmationDialog.confirm({
            title: `Xóa ${count} phòng học đã chọn`,
            message: `Bạn có chắc chắn muốn xóa ${count} phòng học (${names})? Toàn bộ cấu hình camera và vùng nhận diện ROI của các phòng này cũng sẽ bị xóa. Thao tác này không thể hoàn tác!`,
            confirmText: `Xác nhận xóa (${count})`,
            cancelText: 'Hủy bỏ',
            type: 'danger'
        });
    } else {
        confirmed = window.confirm(`Bạn có chắc chắn muốn xóa ${count} phòng học (${names})?`);
    }

    if (!confirmed) return;

    const btnDelete = document.getElementById('btnBatchDeleteSelected');
    if (btnDelete) {
        btnDelete.disabled = true;
        btnDelete.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xóa...';
    }

    let successCount = 0;
    let failCount = 0;

    for (const id of Array.from(matrixSelectedIds)) {
        try {
            const res = await CameraAPI.delete(id);
            if (res.success) {
                successCount++;
                matrixSelectedIds.delete(id);
            } else {
                failCount++;
            }
        } catch (err) {
            console.error('Lỗi khi xóa camera ID', id, err);
            failCount++;
        }
    }

    if (btnDelete) {
        btnDelete.disabled = false;
        btnDelete.innerHTML = '<i class="fa-solid fa-trash-can"></i> Xóa đã chọn';
    }

    if (typeof externalHandlers.onRefreshCameras === 'function') {
        await externalHandlers.onRefreshCameras();
    }
    updateBatchActionBar();

    if (failCount === 0) {
        showToast(`Đã xóa thành công ${successCount} phòng học đã chọn!`, 'info');
    } else {
        showToast(`Đã xóa ${successCount} phòng, thất bại ${failCount} phòng.`, 'warning');
    }
}

/**
 * Bật hoặc tắt kích hoạt hàng loạt các camera đã chọn
 */
export async function batchToggleCameraStatus(isActive) {
    const ids = Array.from(matrixSelectedIds);
    if (ids.length === 0) {
        showToast('Vui lòng chọn ít nhất 1 phòng học để thay đổi trạng thái.', 'warning');
        return;
    }

    const actionText = isActive ? 'Kích hoạt' : 'Tạm ngưng';
    try {
        const res = await CameraAPI.batchToggleStatus({
            camera_ids: ids,
            is_active: isActive
        });
        if (res && res.success) {
            showToast(res.message || `Đã ${actionText.toLowerCase()} thành công!`, 'success');
            if (typeof externalHandlers.onRefreshCameras === 'function') {
                await externalHandlers.onRefreshCameras();
            }
            updateBatchActionBar();
        } else {
            showToast((res && res.message) || `Không thể ${actionText.toLowerCase()} camera`, 'danger');
        }
    } catch (err) {
        console.error('Lỗi batch toggle status:', err);
        showToast(`Lỗi khi ${actionText.toLowerCase()}: ` + (err.message || err), 'danger');
    }
}

export function openLiveModal(id, name) {
    const cam = matrixCameras.find(c => c.id === parseInt(id));
    const titleEl = document.getElementById('liveViewTitle');
    const subEl = document.getElementById('liveViewSubtitle');
    const playerEl = document.getElementById('liveVideoPlayer') || document.getElementById('liveViewImg');
    const modal = document.getElementById('liveViewModal');

    if (titleEl) titleEl.innerText = `${name}`;
    if (subEl) {
        const info = cam ? `${cam.room_number || 'Phòng N/A'} • Sĩ số: ${cam.standard_count} HS • ${cam.is_active ? 'Đang kích hoạt' : 'Tạm dừng'}` : `ID: ${id}`;
        subEl.innerText = info;
    }

    if (playerEl) {
        // Luồng video trực tiếp thời gian thực
        const streamUrl = `/api/cameras/${id}/stream?_t=${Date.now()}`;
        playerEl.src = streamUrl;
        playerEl.dataset.cameraId = id;
        playerEl.dataset.cameraName = name;
        playerEl.dataset.streamUrl = streamUrl;
        playerEl.dataset.isPlaying = 'true';

        playerEl.onerror = () => {
            // Fallback sang snapshot nếu camera offline
            playerEl.onerror = null;
            playerEl.src = `/storage/captures/latest/Lop_${id}.jpg?_t=${Date.now()}`;
        };
    }

    if (modal) modal.classList.add('active');
}

export function closeLiveModal() {
    const modal = document.getElementById('liveViewModal');
    if (modal) modal.classList.remove('active');

    const playerEl = document.getElementById('liveVideoPlayer') || document.getElementById('liveViewImg');
    if (playerEl) {
        // Ngắt kết nối luồng video trực tiếp ngay lập tức
        playerEl.src = '';
        playerEl.dataset.isPlaying = 'false';
    }
}

export function initImageControls() {
    const btnClose = document.getElementById('liveViewCloseBtn');
    if (btnClose) btnClose.addEventListener('click', closeLiveModal);

    // Tạm dừng / Tiếp tục phát luồng trực tiếp
    const btnTogglePlay = document.getElementById('btnLiveTogglePlay');
    if (btnTogglePlay) {
        btnTogglePlay.onclick = () => {
            const playerEl = document.getElementById('liveVideoPlayer') || document.getElementById('liveViewImg');
            if (!playerEl) return;
            const camId = playerEl.dataset.cameraId;
            if (!camId) return;

            if (playerEl.dataset.isPlaying === 'true') {
                playerEl.src = '';
                playerEl.dataset.isPlaying = 'false';
                btnTogglePlay.innerHTML = '<i class="fa-solid fa-play"></i>';
                btnTogglePlay.title = 'Tiếp tục phát luồng';
            } else {
                playerEl.src = `/api/cameras/${camId}/stream?_t=${Date.now()}`;
                playerEl.dataset.isPlaying = 'true';
                btnTogglePlay.innerHTML = '<i class="fa-solid fa-pause"></i>';
                btnTogglePlay.title = 'Tạm dừng luồng';
            }
        };
    }

    // Chụp ảnh nhanh từ luồng camera
    const btnSnapshot = document.getElementById('btnLiveSnapshot') || document.getElementById('btnRefreshImage');
    if (btnSnapshot) {
        btnSnapshot.onclick = async () => {
            const playerEl = document.getElementById('liveVideoPlayer') || document.getElementById('liveViewImg');
            const camId = playerEl?.dataset.cameraId;
            if (!camId) return;
            showToast('Đang chụp khung hình camera...', 'info');
            try {
                const res = await CameraAPI.refreshClassroomSnapshot(camId);
                showToast(res?.message || 'Chụp ảnh từ camera thành công!', 'success');
            } catch (err) {
                showToast('Lỗi chụp ảnh: ' + (err.message || err), 'danger');
            }
        };
    }

    // Phóng to toàn màn hình
    const btnFullscreen = document.getElementById('btnLiveFullscreen');
    if (btnFullscreen) {
        btnFullscreen.onclick = () => {
            const container = document.querySelector('.live-player-container') || document.getElementById('liveViewModal');
            if (!document.fullscreenElement) {
                container?.requestFullscreen?.().catch(() => {});
            } else {
                document.exitFullscreen?.().catch(() => {});
            }
        };
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modal = document.getElementById('liveViewModal');
            if (modal && modal.classList.contains('active')) {
                closeLiveModal();
            }
            const roiModal = document.getElementById('roiConfigModal');
            if (roiModal && (roiModal.classList.contains('active') || roiModal.style.display !== 'none')) {
                closeRoiModal();
            }
        }
    });

    const modal = document.getElementById('liveViewModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target.id === 'liveViewModal') {
                closeLiveModal();
            }
        });
    }
}

// =========================================================================
// POPUP CẤU HÌNH VÙNG ROI TRỰC TIẾP TRÊN TRANG (IN-PAGE ROI CONFIG MODAL)
// =========================================================================
let modalRoiEditor = null;
let currentRoiCameraId = null;

export function openRoiModal(camId, camName) {
    const modal = document.getElementById('roiConfigModal');
    if (!modal) {
        console.error('Không tìm thấy modal #roiConfigModal trên trang');
        return;
    }

    currentRoiCameraId = parseInt(camId);
    const cam = matrixCameras.find(c => c.id === currentRoiCameraId);
    const titleEl = document.getElementById('roiModalTitle');
    const subEl = document.getElementById('roiModalSubtitle');
    if (titleEl) titleEl.innerText = `Thiết Lập Vùng Nhận Diện ROI - ${camName}`;
    if (subEl && cam) {
        subEl.innerText = `${cam.room_number || 'Phòng N/A'} • Sĩ số: ${cam.standard_count} HS • Vẽ đa giác quanh khu vực bàn học sinh`;
    }

    modal.style.display = 'flex';
    modal.style.alignItems = 'center';
    modal.style.justifyContent = 'center';
    modal.classList.add('active');

    // Khởi tạo Canvas Editor nếu chưa có
    const canvas = document.getElementById('roiModalCanvas');
    if (canvas && typeof window.ROICanvasEditor === 'function') {
        if (!modalRoiEditor) {
            modalRoiEditor = new window.ROICanvasEditor('roiModalCanvas');
            bindRoiModalControls();
        }
        modalRoiEditor.loadClassroomROI(currentRoiCameraId, false);
        
        // Kích hoạt tính toán lại kích thước canvas chuẩn xác sau khi modal bung rộng
        setTimeout(() => {
            if (modalRoiEditor && typeof modalRoiEditor.fitCanvasToWrapper === 'function') {
                modalRoiEditor.fitCanvasToWrapper();
                modalRoiEditor.render();
            }
        }, 60);
    }
}

export function closeRoiModal() {
    const modal = document.getElementById('roiConfigModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}

function bindRoiModalControls() {
    const btnClose = document.getElementById('roiModalCloseBtn');
    const btnCancel = document.getElementById('btnModalCancelRoi');
    if (btnClose) btnClose.onclick = closeRoiModal;
    if (btnCancel) btnCancel.onclick = closeRoiModal;

    const btnGreen = document.getElementById('btnModalModeGreen');
    if (btnGreen) {
        btnGreen.onclick = () => {
            if (modalRoiEditor && typeof modalRoiEditor.setMode === 'function') {
                modalRoiEditor.setMode('green');
            }
        };
    }

    const btnFourCorners = document.getElementById('btnModalFourCorners');
    if (btnFourCorners) {
        btnFourCorners.onclick = () => {
            if (modalRoiEditor && typeof modalRoiEditor.setFourCorners === 'function') {
                modalRoiEditor.setFourCorners();
            }
        };
    }

    const btnUndo = document.getElementById('btnModalUndo');
    if (btnUndo) {
        btnUndo.onclick = () => {
            if (modalRoiEditor && typeof modalRoiEditor.undo === 'function') {
                modalRoiEditor.undo();
            }
        };
    }

    const btnClear = document.getElementById('btnModalClear');
    if (btnClear) {
        btnClear.onclick = () => {
            if (modalRoiEditor && typeof modalRoiEditor.clearZone === 'function') {
                modalRoiEditor.clearZone();
            }
        };
    }

    const btnSnapshot = document.getElementById('btnModalSnapshot');
    if (btnSnapshot) {
        btnSnapshot.onclick = async () => {
            if (modalRoiEditor && typeof modalRoiEditor.refreshSnapshot === 'function') {
                await modalRoiEditor.refreshSnapshot();
            }
        };
    }

    const btnSave = document.getElementById('btnModalSaveROI');
    if (btnSave) {
        btnSave.onclick = async () => {
            if (!modalRoiEditor || !currentRoiCameraId) return;
            btnSave.disabled = true;
            btnSave.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
            try {
                await modalRoiEditor.saveROI();
                showToast(`Đã lưu tọa độ vùng ROI thành công!`, 'success');
                setTimeout(() => {
                    closeRoiModal();
                }, 500);
            } catch (err) {
                showToast('Lỗi lưu tọa độ ROI: ' + (err.message || err), 'danger');
            } finally {
                btnSave.disabled = false;
                btnSave.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu Tọa Độ Vùng';
            }
        };
    }
}
