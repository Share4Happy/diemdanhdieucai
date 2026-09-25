/**
 * ROICanvasEditor - Canvas vẽ đa giác Red Zone & Green Zone tương tác
 * Hỗ trợ kéo thả các điểm neo, hút nam châm mép ảnh, undo (Ctrl+Z), đổi độ phân giải.
 */

const API_BASE = (window.location.protocol === 'file:' || (!window.location.origin.includes(':8000') && !window.location.origin.includes(':80')))
    ? 'http://localhost:8000'
    : '';

function getAuthHeaders(extra = {}) {
    return { 'Accept': 'application/json', ...extra };
}

class ROICanvasEditor {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.container = this.canvas.parentElement;
        this.currentClassId = 1;
        this.currentMode = 'green'; // 'green' (phần lấy) hoặc 'red' (phần bỏ đi)

        this.redZone = [];
        this.greenZone = [];
        this.history = [];

        this.image = new Image();
        this.imageLoaded = false;

        this.draggingPointIndex = -1;
        this.draggingZone = null;
        this.hoveredPointIndex = -1;
        this.hoveredZone = null;

        // Chế độ độ phân giải: mặc định auto để giữ chuẩn tỉ lệ camera không méo ảnh
        this.resMode = 'auto'; 
        this.targetWidth = 1920;
        this.targetHeight = 1080;
        this.storedRoiDims = null;
        this.fallbackMode = false;

        if (this.canvas) {
            this.canvas.width = 1280;
            this.canvas.height = 720;
        }

        this.boundWindowMouseMove = (e) => this.onWindowMouseMove(e);
        this.boundWindowMouseUp = (e) => this.onWindowMouseUp(e);

        this.initEvents();
        setTimeout(() => this.render(), 50);
    }

    initEvents() {
        // Sự kiện chuột trên Canvas
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onCanvasMouseMove(e));
        this.canvas.addEventListener('mouseleave', () => this.onCanvasMouseLeave());
        this.canvas.addEventListener('contextmenu', (e) => this.onContextMenu(e));

        // Bắt sự kiện trên container bao quanh
        const outerWrapper = this.canvas.closest('.canvas-outer-wrapper') || this.container;
        if (outerWrapper) {
            outerWrapper.addEventListener('mousedown', (e) => {
                if (e.target !== this.canvas && e.button === 0) {
                    this.onMouseDown(e);
                }
            });
            outerWrapper.addEventListener('contextmenu', (e) => {
                if (e.target !== this.canvas) {
                    this.onContextMenu(e);
                }
            });
        }

        // Bắt sự kiện thay đổi kích thước cửa sổ trình duyệt (Responsive auto-realign)
        window.addEventListener('resize', () => {
            this.resetContainerScroll();
            this.render();
        });

        // Bắt phím tắt bàn phím
        window.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
                e.preventDefault();
                this.undo();
            } else if (e.key === 'Delete' || e.key === 'Backspace') {
                e.preventDefault();
                this.deleteLastPoint();
            } else if (e.key === 'Escape') {
                if (this.draggingPointIndex !== -1) {
                    this.stopDragging();
                }
            }
        });
    }

    resetContainerScroll() {
        const outerWrapper = this.canvas?.closest('.canvas-outer-wrapper');
        if (outerWrapper) {
            outerWrapper.scrollLeft = 0;
            outerWrapper.scrollTop = 0;
        }
    }

    showToast(title, message, isError = false) {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast ${isError ? 'toast-error' : ''}`;
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fa-solid ${isError ? 'fa-circle-exclamation' : 'fa-circle-check'}"></i>
            </div>
            <div class="toast-content">
                <h4>${title}</h4>
                <p>${message}</p>
            </div>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(60px)';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    saveState() {
        this.history.push(JSON.parse(JSON.stringify(this.greenZone)));
        if (this.history.length > 20) {
            this.history.shift();
        }
    }

    undo() {
        if (this.history.length === 0) {
            this.showToast("Thông báo", "Không có thao tác nào trước đó để hoàn tác");
            return;
        }
        this.greenZone = this.history.pop() || [];
        this.redZone = [];
        this.render();
        this.updateStatsBar();
        this.showToast("Đã hoàn tác", "Đã quay lại bước trước đó");
    }

    deleteLastPoint() {
        if (this.greenZone.length > 0) {
            this.saveState();
            const removed = this.greenZone.pop();
            this.render();
            this.updateStatsBar();
            this.showToast("Đã xóa điểm", `Đã xóa điểm cuối cùng (${removed[0]}, ${removed[1]})`);
        }
    }

    updateStatsBar(savedTime = null, aiResult = null) {
        const statsElem = document.getElementById('saveStatusBar');
        if (!statsElem) return;

        const greenCount = this.greenZone.length;

        let statusHtml = `
            <span><i class="fa-solid fa-draw-polygon" style="color: #059669;"></i> Vùng Nhận Diện: <strong>${greenCount} điểm</strong> (Bàn học)</span>
            <span style="color: #64748b;"><i class="fa-solid fa-ban"></i> Ngoài vùng: Tự động bỏ qua</span>
        `;

        if (aiResult && aiResult.present_count !== undefined) {
            statusHtml += `<span style="color: #047857; font-weight: 700;"><i class="fa-solid fa-brain"></i> AI: Có mặt ${aiResult.present_count}/${aiResult.standard_count || 40} HS (Vắng ${aiResult.absent_count} HS) • Lúc ${savedTime || 'vừa xong'}</span>`;
        } else if (savedTime) {
            statusHtml += `<span style="color: #047857; font-weight: 600;"><i class="fa-solid fa-circle-check"></i> Đã lưu CSDL lúc ${savedTime}</span>`;
        } else {
            statusHtml += `<span style="color: #64748b;"><i class="fa-solid fa-database"></i> Sẵn sàng ghi CSDL & Phân tích AI</span>`;
        }

        statsElem.innerHTML = statusHtml;
    }

    updateResolutionDisplay() {
        const resElem = document.getElementById('canvasCoords');
        if (resElem) {
            resElem.innerHTML = `<i class="fa-solid fa-expand"></i> Độ phân giải: <strong>${this.canvas.width} × ${this.canvas.height}</strong>`;
        }
    }

    setResolutionMode(mode) {
        this.resMode = mode;
        const oldW = this.canvas.width || 1080;
        const oldH = this.canvas.height || 1024;

        if (mode === '1080x1024') {
            this.targetWidth = 1080;
            this.targetHeight = 1024;
        } else if (mode === '1920x1080') {
            this.targetWidth = 1920;
            this.targetHeight = 1080;
        } else if (mode === '1280x1024') {
            this.targetWidth = 1280;
            this.targetHeight = 1024;
        } else if (mode === 'auto') {
            if (this.imageLoaded && this.image.naturalWidth) {
                this.targetWidth = this.image.naturalWidth;
                this.targetHeight = this.image.naturalHeight;
            } else {
                this.targetWidth = 1080;
                this.targetHeight = 1024;
            }
        }

        const newW = this.targetWidth;
        const newH = this.targetHeight;

        if (oldW > 0 && oldH > 0 && (oldW !== newW || oldH !== newH)) {
            const sx = newW / oldW;
            const sy = newH / oldH;
            this.redZone = [];
            this.greenZone = this.greenZone.map(([x, y]) => [
                Math.max(0, Math.min(newW, Math.round(x * sx))),
                Math.max(0, Math.min(newH, Math.round(y * sy)))
            ]);
        }

        this.canvas.width = newW;
        this.canvas.height = newH;
        this.storedRoiDims = { width: newW, height: newH };

        this.render();
        this.updateResolutionDisplay();
        this.showToast("Cập nhật độ phân giải", `Đã chuyển sang ${this.canvas.width} × ${this.canvas.height}`);
    }

    loadImage(src, retryCount = 0) {
        this.imageLoaded = false;
        const skeletonOverlay = document.getElementById('canvasSkeletonOverlay');
        if (skeletonOverlay && retryCount === 0) {
            skeletonOverlay.classList.remove('hidden');
        }

        this.image = new Image();
        if (retryCount === 0) {
            this.image.crossOrigin = "anonymous";
        }

        this.image.onload = () => {
            this.imageLoaded = true;
            this.fallbackMode = false;
            if (skeletonOverlay) {
                skeletonOverlay.classList.add('hidden');
            }
            let targetW, targetH;

            if (this.resMode === 'auto') {
                targetW = this.image.naturalWidth || 1280;
                targetH = this.image.naturalHeight || 720;
            } else {
                targetW = this.targetWidth || 1280;
                targetH = this.targetHeight || 720;
            }

            if (this.storedRoiDims && this.storedRoiDims.width > 0 && this.storedRoiDims.height > 0) {
                const sx = targetW / this.storedRoiDims.width;
                const sy = targetH / this.storedRoiDims.height;
                if (Math.abs(sx - 1.0) > 0.005 || Math.abs(sy - 1.0) > 0.005) {
                    this.redZone = [];
                    this.greenZone = this.greenZone.map(([x, y]) => [
                        Math.max(0, Math.min(targetW, Math.round(x * sx))),
                        Math.max(0, Math.min(targetH, Math.round(y * sy)))
                    ]);
                }
            }
            this.storedRoiDims = { width: targetW, height: targetH };

            this.canvas.width = targetW;
            this.canvas.height = targetH;
            this.render();
            this.updateStatsBar();
            this.updateResolutionDisplay();
        };

        this.image.onerror = (err) => {
            console.warn(`[ROICanvas] Lỗi nạp ảnh (thử lần ${retryCount}):`, src, err);
            // 1. Thử lại không có crossOrigin nếu lần 1 có crossOrigin
            if (retryCount === 0) {
                this.loadImage(src, 1);
                return;
            }
            // 2. Thử fallback sang ảnh mẫu lớp học
            if (retryCount === 1 && !src.includes('classroom_sample_1.jpg')) {
                const sampleUrl = `${API_BASE}/dataset/samples/classroom_sample_1.jpg`;
                this.loadImage(sampleUrl, 2);
                return;
            }
            // 3. Fallback sang lưới Blueprint Grid giả lập
            this.imageLoaded = true;
            this.fallbackMode = true;
            if (skeletonOverlay) {
                skeletonOverlay.classList.add('hidden');
            }
            this.canvas.width = this.targetWidth || 1280;
            this.canvas.height = this.targetHeight || 720;
            this.render();
            this.updateStatsBar();
            this.updateResolutionDisplay();
        };

        this.image.src = src;
    }

    setMode(mode) {
        this.currentMode = 'green';
        this.render();
    }

    getCanvasCoords(e) {
        const rect = this.canvas.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return [0, 0];

        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;

        const rawX = Math.round((e.clientX - rect.left) * scaleX);
        const rawY = Math.round((e.clientY - rect.top) * scaleY);

        let clampedX = Math.max(0, Math.min(this.canvas.width, rawX));
        let clampedY = Math.max(0, Math.min(this.canvas.height, rawY));

        const snapDist = 16;
        if (clampedX <= snapDist) clampedX = 0;
        if (clampedX >= this.canvas.width - snapDist) clampedX = this.canvas.width;
        if (clampedY <= snapDist) clampedY = 0;
        if (clampedY >= this.canvas.height - snapDist) clampedY = this.canvas.height;

        return [clampedX, clampedY];
    }

    findPointNear(clientX, clientY, zone) {
        if (!zone || zone.length === 0) return -1;
        const rect = this.canvas.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return -1;

        const screenThreshold = 26;

        for (let i = 0; i < zone.length; i++) {
            const [cx, cy] = zone[i];
            const handleRadius = 10;
            const drawX = Math.max(handleRadius + 2, Math.min(this.canvas.width - handleRadius - 2, cx));
            const drawY = Math.max(handleRadius + 2, Math.min(this.canvas.height - handleRadius - 2, cy));

            const sx = rect.left + (drawX / this.canvas.width) * rect.width;
            const sy = rect.top + (drawY / this.canvas.height) * rect.height;
            if (Math.hypot(sx - clientX, sy - clientY) <= screenThreshold) {
                return i;
            }

            const rx = rect.left + (cx / this.canvas.width) * rect.width;
            const ry = rect.top + (cy / this.canvas.height) * rect.height;
            if (Math.hypot(rx - clientX, ry - clientY) <= screenThreshold) {
                return i;
            }
        }
        return -1;
    }

    onMouseDown(e) {
        if (!this.imageLoaded) return;
        if (e.button !== 0) return;

        let nearIdx = this.findPointNear(e.clientX, e.clientY, this.greenZone);
        if (nearIdx !== -1) {
            this.startDragging(nearIdx, 'green');
            return;
        }

        this.saveState();
        const coords = this.getCanvasCoords(e);
        this.greenZone.push(coords);
        this.render();
        this.updateStatsBar();

        this.startDragging(this.greenZone.length - 1, 'green');
    }

    startDragging(pointIndex, zoneMode) {
        this.draggingPointIndex = pointIndex;
        this.draggingZone = 'green';

        window.addEventListener('mousemove', this.boundWindowMouseMove);
        window.addEventListener('mouseup', this.boundWindowMouseUp);

        document.body.style.userSelect = 'none';
        document.body.style.cursor = 'grabbing';
        this.canvas.style.cursor = 'grabbing';
    }

    onWindowMouseMove(e) {
        if (this.draggingPointIndex === -1) return;
        if (!this.greenZone || this.draggingPointIndex >= this.greenZone.length) return;

        const coords = this.getCanvasCoords(e);
        this.greenZone[this.draggingPointIndex] = coords;
        this.render();
    }

    onWindowMouseUp(e) {
        this.stopDragging();
    }

    stopDragging() {
        this.draggingPointIndex = -1;
        this.draggingZone = null;

        window.removeEventListener('mousemove', this.boundWindowMouseMove);
        window.removeEventListener('mouseup', this.boundWindowMouseUp);

        document.body.style.userSelect = '';
        document.body.style.cursor = '';
        this.canvas.style.cursor = 'crosshair';

        this.render();
        this.updateStatsBar();
    }

    onCanvasMouseMove(e) {
        if (this.draggingPointIndex !== -1) return;

        const nearIdx = this.findPointNear(e.clientX, e.clientY, this.greenZone);

        if (nearIdx !== this.hoveredPointIndex) {
            this.hoveredPointIndex = nearIdx;
            this.hoveredZone = nearIdx !== -1 ? 'green' : null;
            this.canvas.style.cursor = nearIdx !== -1 ? 'grab' : 'crosshair';
            this.render();
        }
    }

    onCanvasMouseLeave() {
        if (this.draggingPointIndex === -1 && this.hoveredPointIndex !== -1) {
            this.hoveredPointIndex = -1;
            this.hoveredZone = null;
            this.render();
        }
    }

    onContextMenu(e) {
        e.preventDefault();
        let nearIdx = this.findPointNear(e.clientX, e.clientY, this.greenZone);

        if (nearIdx !== -1) {
            this.saveState();
            this.greenZone.splice(nearIdx, 1);
            this.hoveredPointIndex = -1;
            this.hoveredZone = null;
            this.render();
            this.updateStatsBar();
            this.showToast("Đã xóa điểm", `Đã xóa điểm #${nearIdx + 1} của Vùng Nhận Diện`);
        }
    }

    updateModeButtons() {
        const btnGreen = document.getElementById('btnModeGreen');
        if (btnGreen) {
            btnGreen.classList.add('active');
        }
    }

    addFourCorners() {
        this.saveState();
        const w = this.canvas.width;
        const h = this.canvas.height;
        
        this.greenZone = [
            [0, 0],
            [w, 0],
            [w, h],
            [0, h]
        ];

        this.render();
        this.updateStatsBar();
        this.showToast("Bắt 4 góc hoàn tất", `Đã gán 4 góc chuẩn biên ảnh (${w}×${h}) cho Vùng Nhận Diện`);
    }

    clearCurrentZone() {
        this.saveState();
        this.greenZone = [];
        this.render();
        this.updateStatsBar();
        this.showToast("Đã xóa vùng", "Đã xóa toàn bộ các điểm của Vùng Nhận Diện");
    }

    render() {
        this.resetContainerScroll();
        const ctx = this.ctx;
        if (!ctx || !this.canvas) return;
        const w = this.canvas.width || 1280;
        const h = this.canvas.height || 720;

        ctx.clearRect(0, 0, w, h);

        if (this.imageLoaded && !this.fallbackMode && this.image.naturalWidth > 0) {
            ctx.drawImage(this.image, 0, 0, w, h);
        } else {
            // Vẽ nền Blueprint Grid kỹ thuật sắc nét, chuyên nghiệp khi không có ảnh camera
            ctx.fillStyle = '#0f172a';
            ctx.fillRect(0, 0, w, h);

            // Lưới ô vuông 60px
            ctx.strokeStyle = 'rgba(51, 65, 85, 0.45)';
            ctx.lineWidth = 1;
            for (let x = 0; x < w; x += 60) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, h);
                ctx.stroke();
            }
            for (let y = 0; y < h; y += 60) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(w, y);
                ctx.stroke();
            }

            // Text thông báo chính giữa
            ctx.fillStyle = '#94a3b8';
            ctx.font = '600 15px Inter, system-ui, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('📷 Khung hình Camera đang kết nối / Ngoại tuyến', w / 2, h / 2 - 12);
            ctx.fillStyle = '#64748b';
            ctx.font = '400 13px Inter, system-ui, sans-serif';
            ctx.fillText('Bạn vẫn có thể vẽ và điều chỉnh tọa độ đa giác ROI trực tiếp trên không gian này', w / 2, h / 2 + 14);
            ctx.textAlign = 'left';
        }

        // Vẽ Vùng Nhận Diện (Green Zone - Bàn học sinh)
        this.drawPolygon(this.greenZone, 'rgba(16, 185, 129, 0.35)', '#059669', 'VÙNG NHẬN DIỆN (BÀN HỌC)', 'green');
    }

    drawPolygon(points, fillColor, strokeColor, label, zoneType) {
        if (!points || points.length === 0) return;
        const ctx = this.ctx;

        ctx.beginPath();
        ctx.moveTo(points[0][0], points[0][1]);
        for (let i = 1; i < points.length; i++) {
            ctx.lineTo(points[i][0], points[i][1]);
        }
        if (points.length >= 3) {
            ctx.closePath();
            ctx.fillStyle = fillColor;
            ctx.fill();
        }

        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 3;
        ctx.stroke();

        points.forEach(([x, y], idx) => {
            const isHovered = (this.hoveredZone === zoneType && this.hoveredPointIndex === idx);
            const isDragging = (this.draggingZone === zoneType && this.draggingPointIndex === idx);
            const handleRadius = (isHovered || isDragging) ? 10 : 8;

            const drawX = Math.max(handleRadius + 2, Math.min(this.canvas.width - handleRadius - 2, x));
            const drawY = Math.max(handleRadius + 2, Math.min(this.canvas.height - handleRadius - 2, y));

            ctx.save();
            ctx.beginPath();
            ctx.arc(drawX, drawY, handleRadius, 0, 2 * Math.PI);
            ctx.fillStyle = (isHovered || isDragging) ? '#ffedd5' : '#ffffff';
            ctx.fill();
            ctx.strokeStyle = (isHovered || isDragging) ? '#ea580c' : strokeColor;
            ctx.lineWidth = (isHovered || isDragging) ? 4 : 3;
            ctx.stroke();

            if (isHovered || isDragging) {
                ctx.beginPath();
                ctx.arc(drawX, drawY, handleRadius + 5, 0, 2 * Math.PI);
                ctx.strokeStyle = 'rgba(234, 88, 12, 0.5)';
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            ctx.font = 'bold 13px Inter, sans-serif';
            ctx.fillStyle = '#0f172a';
            const textX = drawX < this.canvas.width - 45 ? drawX + 12 : drawX - 25;
            const textY = drawY > 25 ? drawY - 10 : drawY + 22;
            ctx.fillText(`${idx + 1}`, textX, textY);

            if (isDragging) {
                ctx.font = '600 11px Inter, sans-serif';
                ctx.fillStyle = '#dc2626';
                ctx.fillText(`(${x}, ${y})`, textX, textY + 14);
            }
            ctx.restore();
        });

        if (points.length >= 1) {
            ctx.save();
            ctx.font = 'bold 14px Inter, sans-serif';
            ctx.fillStyle = strokeColor;
            const lx = Math.max(10, Math.min(this.canvas.width - 250, points[0][0] + 10));
            const ly = Math.max(25, Math.min(this.canvas.height - 10, points[0][1] - 15));
            ctx.fillText(label, lx, ly);
            ctx.restore();
        }
    }

    async loadClassroomROI(classId, forceRefresh = false) {
        this.currentClassId = classId;
        try {
            const url = `${API_BASE}/api/roi/${classId}${forceRefresh ? '?refresh=true' : ''}`;
            const res = await fetch(url, {
                credentials: 'include',
                headers: getAuthHeaders()
            });
            const data = await res.json();
            
            const dbW = data.image_width || 1080;
            const dbH = data.image_height || 1024;
            this.storedRoiDims = { width: dbW, height: dbH };
            this.redZone = [];
            this.greenZone = data.green_zone || [];
            this.history = [];
            
            let snapshotUrl = data.snapshot_url || `/dataset/samples/classroom_sample_1.jpg`;
            if (!snapshotUrl.startsWith('http')) {
                snapshotUrl = `${API_BASE}${snapshotUrl}`;
            }
            snapshotUrl += (snapshotUrl.includes('?') ? '&' : '?') + '_t=' + Date.now();
            this.loadImage(snapshotUrl);
            this.updateStatsBar("gần nhất");
        } catch (err) {
            console.error("Lỗi nạp ROI lớp:", err);
            this.showToast("Lỗi kết nối", "Không thể nạp dữ liệu ROI cho lớp này", true);
        }
    }

    async refreshSnapshot() {
        const classSelect = document.getElementById('classSelect');
        const classId = classSelect ? classSelect.value : this.currentClassId;
        const btn = document.getElementById('btnRefreshSnapshot');
        const btnHeader = document.getElementById('btnHeaderSnapshot');
        const oldHtml = btn ? btn.innerHTML : '';
        const oldHeaderHtml = btnHeader ? btnHeader.innerHTML : '';
        
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang chụp từ camera...';
        }
        if (btnHeader) {
            btnHeader.disabled = true;
            btnHeader.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang chụp...';
        }

        try {
            const res = await fetch(`${API_BASE}/api/roi/${classId}/refresh-snapshot`, {
                method: 'POST',
                credentials: 'include',
                headers: getAuthHeaders()
            });
            const data = await res.json();
            if (data.snapshot_url) {
                let snap = data.snapshot_url;
                if (!snap.startsWith('http')) {
                    snap = `${API_BASE}${snap}`;
                }
                const bustUrl = snap + (snap.includes('?') ? '&' : '?') + '_t=' + Date.now();
                this.loadImage(bustUrl);
                this.showToast("✓ Đã Cập Nhật Khung Hình!", data.message || "Ảnh chụp mới nhất từ camera đã được tải lên canvas.");
            } else {
                this.showToast("Cảnh báo", data.message || "Không thể chụp từ camera", true);
            }
        } catch (err) {
            this.showToast("Lỗi chụp ảnh", "Không thể chụp khung hình mới: " + err, true);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = oldHtml || '<i class="fa-solid fa-camera-rotate"></i> Chụp Lại Khung Hình Camera';
            }
            if (btnHeader) {
                btnHeader.disabled = false;
                btnHeader.innerHTML = oldHeaderHtml || '<i class="fa-solid fa-camera"></i> Chụp Lại Ảnh Camera';
            }
        }
    }

    async saveROI() {
        const classSelect = document.getElementById('classSelect');
        const classId = classSelect ? classSelect.value : this.currentClassId;
        const className = classSelect && classSelect.options[classSelect.selectedIndex] 
            ? classSelect.options[classSelect.selectedIndex].text 
            : `Lớp ${classId}`;

        const btnSave = document.getElementById('btnSaveROI');
        const originalBtnHtml = btnSave ? btnSave.innerHTML : '';

        if (btnSave) {
            btnSave.disabled = true;
            btnSave.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang Lưu CSDL...';
        }

        try {
            const res = await fetch(`${API_BASE}/api/roi/${classId}`, {
                method: 'POST',
                credentials: 'include',
                headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({
                    red_zone: this.redZone,
                    green_zone: this.greenZone,
                    image_width: this.canvas.width || 1080,
                    image_height: this.canvas.height || 1024
                })
            });

            const result = await res.json();
            const nowTime = new Date().toLocaleTimeString('vi-VN');

            if (res.ok && result.success) {
                if (btnSave) {
                    btnSave.className = 'btn btn-success pulse-success';
                    btnSave.innerHTML = '<i class="fa-solid fa-check"></i> ĐÃ LƯU & ĐỒNG BỘ AI!';
                }

                this.updateStatsBar(nowTime, result);

                setTimeout(() => {
                    if (btnSave) {
                        btnSave.disabled = false;
                        btnSave.className = 'btn btn-save';
                        btnSave.innerHTML = originalBtnHtml || '<i class="fa-solid fa-floppy-disk"></i> Lưu Tọa Độ Vùng';
                    }
                }, 2500);

            } else {
                throw new Error(result.error || result.detail || 'Lỗi không xác định từ máy chủ');
            }
        } catch (err) {
            console.error("Lỗi lưu tọa độ:", err);
            if (btnSave) {
                btnSave.disabled = false;
                btnSave.style.background = '#fee2e2';
                btnSave.style.border = '2px solid #ef4444';
                btnSave.style.color = '#dc2626';
                btnSave.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Thử Lại';
            }
            this.showToast("Lỗi Lưu CSDL", err.message, true);
        }
    }
}

window.ROICanvasEditor = ROICanvasEditor;
