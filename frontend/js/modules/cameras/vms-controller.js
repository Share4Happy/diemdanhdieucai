/**
 * ===================================================================
 * VMS CONTROLLER - THPT ĐIỀU CẢI SURVEILLANCE MATRIX
 * Quản lý Ma Trận Video Giám Sát, Danh Sách Phẳng Camera và Phân Trang Mũi Tên
 * ===================================================================
 */

import { CameraAPI, showToast } from '../../api.js';

export class VmsSurveillanceController {
    constructor() {
        this.cameras = [];
        this.slots = [];
        this.currentLayout = '2x2'; // Mặc định 4 khung hình (2x2)
        this.currentPageIndex = 0;
        this.activeSlotIndex = 0;
        this.searchQuery = '';
        this.expandedSlotIndex = null;
        this.clockInterval = null;

        this.init();
    }

    init() {
        this.bindEvents();
        this.initPagination();
        this.startClock();
        this.initSlots(4); // 2x2 = 4 slots
    }

    /**
     * Hủy kết nối HTTP video stream tức thời để giải phóng socket TCP của trình duyệt
     */
    abortSlotStream(slotEl) {
        if (!slotEl) return;
        const img = slotEl.querySelector('img.vms-slot-video-feed');
        if (img) {
            img.onload = null;
            img.onerror = null;
            // Gán data URI rỗng và huỷ thuộc tính src để trình duyệt ngắt ngay luồng MJPEG
            img.src = 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=';
            img.removeAttribute('src');
        }
    }

    /**
     * Giải phóng tất cả các luồng camera đang chạy trên ma trận hiện tại
     */
    releaseActiveStreams() {
        const grid = document.getElementById('vmsMatrixGrid');
        if (!grid) return;
        const slots = grid.querySelectorAll('.vms-slot');
        slots.forEach(slotEl => this.abortSlotStream(slotEl));
    }

    getPageSize() {
        return this.currentLayout === '1x1' ? 1 : 4;
    }

    getTotalPages() {
        if (!this.cameras || this.cameras.length === 0) return 1;
        return Math.max(1, Math.ceil(this.cameras.length / this.getPageSize()));
    }

    initPagination() {
        const btnPrev = document.getElementById('btnVmsPrevPage');
        if (btnPrev) {
            btnPrev.addEventListener('click', () => this.prevPage());
        }

        const btnNext = document.getElementById('btnVmsNextPage');
        if (btnNext) {
            btnNext.addEventListener('click', () => this.nextPage());
        }
    }

    prevPage() {
        if (this.currentPageIndex > 0) {
            this.goToPage(this.currentPageIndex - 1);
        }
    }

    nextPage() {
        const total = this.getTotalPages();
        if (this.currentPageIndex < total - 1) {
            this.goToPage(this.currentPageIndex + 1);
        }
    }

    goToPage(pageIdx) {
        const total = this.getTotalPages();
        if (pageIdx < 0) pageIdx = 0;
        if (pageIdx >= total) pageIdx = total - 1;
        this.currentPageIndex = pageIdx;

        // BƯỚC QUAN TRỌNG: Giải phóng ngay lập tức toàn bộ các luồng stream cũ trước khi nạp trang mới
        this.releaseActiveStreams();

        const pageSize = this.getPageSize();
        const start = this.currentPageIndex * pageSize;

        // Nạp loạt camera tương ứng vào các khung hình
        for (let i = 0; i < pageSize; i++) {
            const camIdx = start + i;
            if (this.cameras && camIdx < this.cameras.length) {
                const cam = this.cameras[camIdx];
                const ts = Date.now();
                this.slots[i].camera = cam;
                this.slots[i].streamUrl = `/api/cameras/${cam.id}/stream`;
                this.slots[i].snapshotUrl = `/storage/captures/latest/Lop_${cam.id}.jpg?t=${ts}`;
                this.slots[i].isLive = Boolean(cam.is_active && cam.rtsp_url);
            } else {
                this.slots[i].camera = null;
                this.slots[i].streamUrl = '';
                this.slots[i].snapshotUrl = '';
                this.slots[i].isLive = false;
            }
        }

        this.renderMatrixGrid();
        this.updatePaginationUI();
    }

    updatePaginationUI() {
        const totalPages = this.getTotalPages();

        const btnPrev = document.getElementById('btnVmsPrevPage');
        if (btnPrev) {
            btnPrev.disabled = (this.currentPageIndex <= 0);
        }

        const btnNext = document.getElementById('btnVmsNextPage');
        if (btnNext) {
            btnNext.disabled = (this.currentPageIndex >= totalPages - 1);
        }

        const pageInfo = document.getElementById('vmsPageInfo');
        if (pageInfo) {
            const pageSize = this.getPageSize();
            const start = this.currentPageIndex * pageSize + 1;
            const end = Math.min(this.cameras.length, (this.currentPageIndex + 1) * pageSize);
            if (this.cameras.length > 0) {
                pageInfo.textContent = `Trang ${this.currentPageIndex + 1} / ${totalPages} (Lớp ${start} - ${end})`;
            } else {
                pageInfo.textContent = `Trang 1 / 1`;
            }
        }
    }

    setCameras(cams) {
        this.cameras = cams || [];
        this.renderFlatList();

        // Kiểm tra xem URL có yêu cầu mở camera cụ thể không (VD: ?cam=1)
        const urlParams = new URLSearchParams(window.location.search);
        const camParam = urlParams.get('cam');
        if (camParam) {
            const camIdx = this.cameras.findIndex(c => String(c.id) === String(camParam));
            if (camIdx !== -1) {
                const targetPage = Math.floor(camIdx / this.getPageSize());
                this.goToPage(targetPage);
                return;
            }
        }

        // Mặc định nạp trang đầu tiên
        this.goToPage(0);
    }

    initSlots(count) {
        this.slots = [];
        for (let i = 0; i < count; i++) {
            this.slots.push({
                index: i,
                camera: null,
                streamUrl: '',
                snapshotUrl: '',
                isLive: true
            });
        }
    }

    bindEvents() {
        // Nút chuyển layout ma trận (1x1, 2x2, 3x3, 4x4)
        document.querySelectorAll('.vms-grid-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.vms-grid-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const layout = btn.dataset.layout;
                this.switchLayout(layout);
            });
        });

        // Tìm kiếm trên danh sách camera phẳng
        const searchInput = document.getElementById('vmsTreeSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value.trim().toLowerCase();
                this.renderFlatList();
            });
        }

        // Nút toàn màn hình
        const btnFullscreen = document.getElementById('btnVmsFullscreen');
        if (btnFullscreen) {
            btnFullscreen.addEventListener('click', () => this.toggleFullscreen());
        }

        // Nút đóng tất cả ô
        const btnCloseAll = document.getElementById('btnVmsCloseAll');
        if (btnCloseAll) {
            btnCloseAll.addEventListener('click', () => this.closeAllSlots());
        }

        // Nút chụp tất cả ô
        const btnSnapAll = document.getElementById('btnVmsSnapshotAll');
        if (btnSnapAll) {
            btnSnapAll.addEventListener('click', () => {
                if (window.triggerCaptureAll) {
                    window.triggerCaptureAll();
                } else if (window.ProgressModal && window.ProgressModal.startCaptureAll) {
                    window.ProgressModal.startCaptureAll();
                }
            });
        }
    }

    switchLayout(layout) {
        if (layout !== '1x1' && layout !== '2x2') {
            layout = '2x2';
        }
        this.releaseActiveStreams();
        this.currentLayout = layout;
        const grid = document.getElementById('vmsMatrixGrid');
        if (!grid) return;

        grid.className = `vms-matrix-grid grid-${layout}`;
        const targetCount = this.getPageSize();
        this.initSlots(targetCount);

        // Reset về trang 0 và hiển thị các camera của layout mới
        this.currentPageIndex = 0;
        this.goToPage(0);
    }

    startClock() {
        if (this.clockInterval) clearInterval(this.clockInterval);
        this.clockInterval = setInterval(() => {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('vi-VN');
            const dateStr = now.toLocaleDateString('vi-VN');

            // Cập nhật đồng hồ OSD trên từng ô video
            document.querySelectorAll('.vms-osd-clock').forEach(el => {
                el.textContent = `${dateStr} ${timeStr}`;
            });

            // Cập nhật đồng hồ thời gian thực tự động ở thanh bên trái
            const liveClockEl = document.getElementById('vmsLiveClock');
            if (liveClockEl) {
                liveClockEl.textContent = `${timeStr} ${dateStr}`;
            }
        }, 1000);
    }

    /**
     * Hiển thị phẳng toàn bộ 30 camera trực tiếp ra danh sách không cần lồng thư mục
     */
    renderFlatList() {
        const container = document.getElementById('vmsTreeContainer');
        if (!container) return;

        if (this.cameras.length === 0) {
            container.innerHTML = `
                <div style="padding: 1.5rem 1rem; text-align: center; color: #64748b; font-size: 0.8rem;">
                    <i class="fa-solid fa-spinner fa-spin" style="margin-bottom: 8px; display: block; font-size: 1.3rem; color: #38bdf8;"></i>
                    Đang nạp danh sách camera...
                </div>
            `;
            return;
        }

        const filtered = this.cameras.filter(cam => {
            if (!this.searchQuery) return true;
            const searchStr = `${cam.code} ${cam.name} ${cam.room_number || ''}`.toLowerCase();
            return searchStr.includes(this.searchQuery);
        });

        const totalActive = this.cameras.filter(c => c.is_active).length;
        const badge = document.getElementById('vmsTotalCountBadge');
        if (badge) {
            badge.textContent = `${totalActive}/${this.cameras.length} Online`;
        }

        if (filtered.length === 0) {
            container.innerHTML = `
                <div style="padding: 1.5rem 1rem; text-align: center; color: #64748b; font-size: 0.8rem;">
                    <i class="fa-solid fa-magnifying-glass" style="margin-bottom: 6px; display: block; font-size: 1.2rem; color: #475569;"></i>
                    Không tìm thấy camera phù hợp
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="vms-flat-list" style="display: flex; flex-direction: column; gap: 3px; overflow-y: auto; max-height: calc(100vh - 320px); padding-right: 2px;">
                ${filtered.map(cam => {
                    const isOnline = Boolean(cam.is_active && cam.rtsp_url);
                    const dotClass = isOnline ? 'vms-dot-online' : 'vms-dot-offline';
                    const chNum = cam.id < 10 ? '0' + cam.id : cam.id;
                    return `
                        <div class="vms-camera-item"
                             data-cam-id="${cam.id}"
                             title="Click đúp để mở khung hình ${cam.name}"
                             ondblclick="window.vmsSurveillance.onCameraDoubleClick(${cam.id})"
                             onclick="window.vmsSurveillance.onCameraClick(this, ${cam.id})">
                            <div class="vms-cam-info">
                                <span class="vms-dot ${dotClass}"></span>
                                <i class="fa-solid fa-video" style="color: #64748b; font-size: 0.72rem;"></i>
                                <span class="vms-cam-name">CH${chNum}: ${cam.name} ${cam.room_number ? `(${cam.room_number})` : ''}</span>
                            </div>
                            <div class="vms-cam-actions">
                                <button type="button" class="vms-cam-btn-icon" title="Mở lên ô đang chọn" onclick="event.stopPropagation(); window.vmsSurveillance.onCameraDoubleClick(${cam.id})">
                                    <i class="fa-solid fa-play"></i>
                                </button>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }

    onCameraClick(element, camId) {
        document.querySelectorAll('.vms-camera-item').forEach(el => el.classList.remove('is-selected'));
        if (element) element.classList.add('is-selected');
    }

    onCameraDoubleClick(camId) {
        const cam = this.cameras.find(c => c.id === camId);
        if (!cam) return;

        // Tải vào active slot hiện tại hoặc ô trống đầu tiên
        let targetSlotIndex = this.activeSlotIndex;
        const emptySlotIndex = this.slots.findIndex(s => !s.camera);
        if (this.slots[this.activeSlotIndex] && this.slots[this.activeSlotIndex].camera && emptySlotIndex !== -1) {
            targetSlotIndex = emptySlotIndex;
        }

        this.loadCameraIntoSlot(cam, targetSlotIndex, true);
        showToast(`Đã mở luồng giám sát: ${cam.name} (Khung hình ${targetSlotIndex + 1})`, 'success');
    }

    loadCameraIntoSlot(cam, slotIndex, reRender = true) {
        if (!this.slots[slotIndex]) return;

        const slotEl = document.getElementById(`vmsSlot_${slotIndex}`);
        if (slotEl) {
            this.abortSlotStream(slotEl);
        }

        const ts = Date.now();
        const snapUrl = `/storage/captures/latest/Lop_${cam.id}.jpg?t=${ts}`;
        const streamUrl = `/api/cameras/${cam.id}/stream`;

        this.slots[slotIndex].camera = cam;
        this.slots[slotIndex].streamUrl = streamUrl;
        this.slots[slotIndex].snapshotUrl = snapUrl;
        this.slots[slotIndex].isLive = Boolean(cam.is_active && cam.rtsp_url);

        if (reRender) {
            this.renderSingleSlot(slotIndex);
        }
    }

    toggleSlotLive(slotIndex) {
        const slot = this.slots[slotIndex];
        if (!slot || !slot.camera) return;
        slot.isLive = !slot.isLive;
        this.renderSingleSlot(slotIndex);
    }

    renderMatrixGrid() {
        const grid = document.getElementById('vmsMatrixGrid');
        if (!grid) return;

        // Giải phóng các luồng stream cũ trên DOM trước khi dọn sạch innerHTML
        this.releaseActiveStreams();

        grid.innerHTML = '';
        this.slots.forEach((slot, idx) => {
            const slotEl = document.createElement('div');
            slotEl.className = `vms-slot ${idx === this.activeSlotIndex ? 'is-active-slot' : ''}`;
            slotEl.id = `vmsSlot_${idx}`;
            slotEl.onclick = () => this.setActiveSlot(idx);

            slotEl.innerHTML = this.getSlotContentHtml(slot);
            grid.appendChild(slotEl);
        });
    }

    renderSingleSlot(slotIndex) {
        const slotEl = document.getElementById(`vmsSlot_${slotIndex}`);
        if (!slotEl) return;

        this.abortSlotStream(slotEl);
        const slot = this.slots[slotIndex];
        slotEl.innerHTML = this.getSlotContentHtml(slot);
    }

    getSlotContentHtml(slot) {
        const idx = slot.index;
        const cam = slot.camera;

        if (!cam) {
            // Ô TRỐNG (EMPTY SLOT PLACEHOLDER) - Tinh gọn, bỏ dòng mô tả dài, nút Chọn nhỏ gọn
            return `
                <div class="vms-slot-osd-top">
                    <div class="vms-slot-title-group">
                        <i class="fa-solid fa-desktop" style="color: #64748b;"></i>
                        <span>Khung Hình ${idx + 1}</span>
                    </div>
                </div>
                <div class="vms-slot-empty">
                    <i class="fa-solid fa-video-slash"></i>
                    <div class="vms-slot-empty-title">Khung Hình ${idx + 1} (Trống)</div>
                </div>
            `;
        }

        // Ô ĐANG CÓ CAMERA ĐƯỢC GÁN
        const ts = Date.now();
        const now = new Date();
        const timeStr = `${now.toLocaleDateString('vi-VN')} ${now.toLocaleTimeString('vi-VN')}`;

        const isStreaming = Boolean(slot.isLive && cam.is_active && cam.rtsp_url);
        const feedUrl = isStreaming ? `/api/cameras/${cam.id}/stream` : `${slot.snapshotUrl}`;
        const liveBadgeClass = isStreaming ? 'vms-live-badge' : 'vms-live-badge is-paused';
        const liveBadgeText = isStreaming ? 'LIVE' : 'ẢNH CHỤP';

        return `
            <!-- Header OSD Bar -->
            <div class="vms-slot-osd-top">
                <div class="vms-slot-title-group">
                    <span class="${liveBadgeClass}">${liveBadgeText}</span>
                    <span>${cam.room_number ? `${cam.room_number} - ` : ''}${cam.name}</span>
                </div>
                <div class="vms-slot-controls">
                    <button type="button" class="vms-slot-ctrl-btn" title="${isStreaming ? 'Tạm dừng luồng video trực tiếp' : 'Phát lại luồng trực tiếp'}" onclick="event.stopPropagation(); window.vmsSurveillance.toggleSlotLive(${idx})">
                        <i class="fa-solid ${isStreaming ? 'fa-pause' : 'fa-play'}"></i>
                    </button>
                    <button type="button" class="vms-slot-ctrl-btn" title="Phóng to khung hình này" onclick="event.stopPropagation(); window.vmsSurveillance.maximizeSlot(${idx})">
                        <i class="fa-solid fa-expand"></i>
                    </button>
                    <button type="button" class="vms-slot-ctrl-btn btn-close-slot" title="Đóng khung hình này" onclick="event.stopPropagation(); window.vmsSurveillance.closeSlot(${idx})">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            </div>

            <!-- Video / Image Display Area -->
            <div class="vms-slot-video-wrap">
                <img src="${feedUrl}"
                     id="vmsSlotImg_${idx}"
                     class="vms-slot-video-feed"
                     alt="${cam.name}"
                     onerror="if(this.dataset.fallbackTried !== 'true'){ this.dataset.fallbackTried = 'true'; this.src='${slot.snapshotUrl}'; } else { this.onerror=null; this.src='data:image/svg+xml;charset=UTF-8,%3Csvg%20width%3D%22400%22%20height%3D%22225%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Crect%20fill%3D%22%230f172a%22%20width%3D%22400%22%20height%3D%22225%22%2F%3E%3Ctext%20fill%3D%22%2364748b%22%20font-family%3D%22sans-serif%22%20font-size%3D%2214%22%20x%3D%2250%25%22%20y%3D%2250%25%22%20text-anchor%3D%22middle%22%3ENo%20Signal%20(Ch%C6%B0a%20c%C3%B3%20khung%20h%C3%ACnh)%3C%2Ftext%3E%3C%2Fsvg%3E'; }" />
            </div>

            <!-- Footer OSD Bar -->
            <div class="vms-slot-osd-bottom">
                <div>
                    <i class="fa-solid fa-wifi" style="color: #10b981; margin-right: 4px;"></i>
                    <span>1080p | 25 FPS | 1.8 Mbps</span>
                </div>
                <div class="vms-osd-clock">${timeStr}</div>
            </div>
        `;
    }

    setActiveSlot(idx) {
        this.activeSlotIndex = idx;
        document.querySelectorAll('.vms-slot').forEach((el, i) => {
            if (i === idx) el.classList.add('is-active-slot');
            else el.classList.remove('is-active-slot');
        });
    }

    async captureSlot(slotIndex) {
        const slot = this.slots[slotIndex];
        if (!slot || !slot.camera) return;

        try {
            showToast(`Đang bắt hình từ ${slot.camera.name}...`, 'info');
            const token = localStorage.getItem('access_token');
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const res = await fetch(`/api/cameras/${slot.camera.id}/refresh-snapshot`, {
                method: 'POST',
                headers
            });
            const d = await res.json();
            if (d.success && d.snapshot_url) {
                slot.snapshotUrl = d.snapshot_url;
                const img = document.getElementById(`vmsSlotImg_${slotIndex}`);
                if (img) img.src = d.snapshot_url;
                showToast(`Đã bắt hình mới thành công cho ${slot.camera.name}!`, 'success');
            } else {
                showToast(d.message || 'Không thể bắt hình từ camera', 'warning');
            }
        } catch (err) {
            showToast('Lỗi bắt hình: ' + err.message, 'error');
        }
    }

    maximizeSlot(slotIndex) {
        const targetLayout = this.currentLayout === '1x1' ? '2x2' : '1x1';
        let targetCam = null;
        if (targetLayout === '1x1') {
            const slot = this.slots[slotIndex];
            if (slot && slot.camera) {
                targetCam = slot.camera;
            }
        }

        // Cập nhật trạng thái active trên các nút layout
        document.querySelectorAll('.vms-grid-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.layout === targetLayout);
        });

        this.switchLayout(targetLayout);
        if (targetCam) {
            this.loadCameraIntoSlot(targetCam, 0, true);
        }
    }

    closeSlot(slotIndex) {
        if (this.slots[slotIndex]) {
            const slotEl = document.getElementById(`vmsSlot_${slotIndex}`);
            if (slotEl) {
                this.abortSlotStream(slotEl);
            }
            this.slots[slotIndex].camera = null;
            this.slots[slotIndex].snapshotUrl = '';
            this.slots[slotIndex].streamUrl = '';
            this.slots[slotIndex].isLive = false;
            this.renderSingleSlot(slotIndex);
        }
    }

    closeAllSlots() {
        this.releaseActiveStreams();
        this.slots.forEach(s => {
            s.camera = null;
            s.snapshotUrl = '';
            s.streamUrl = '';
            s.isLive = false;
        });
        this.renderMatrixGrid();
        showToast('Đã đóng tất cả khung hình video', 'info');
    }

    toggleFullscreen() {
        const grid = document.querySelector('.vms-workspace');
        if (!grid) return;

        if (!document.fullscreenElement) {
            if (grid.requestFullscreen) grid.requestFullscreen();
            else if (grid.webkitRequestFullscreen) grid.webkitRequestFullscreen();
            else if (grid.msRequestFullscreen) grid.msRequestFullscreen();
        } else {
            if (document.exitFullscreen) document.exitFullscreen();
        }
    }

    openQuickSelectModal(slotIndex) {
        this.setActiveSlot(slotIndex);
        showToast(`Vui lòng click đúp chuột vào camera trên danh sách bên trái để mở lên ô ${slotIndex + 1}`, 'info');
        const search = document.getElementById('vmsTreeSearch');
        if (search) search.focus();
    }
}
