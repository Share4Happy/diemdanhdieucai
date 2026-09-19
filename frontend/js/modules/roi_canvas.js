class ROICanvasEditor {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.currentClassId = 1;
        this.currentMode = 'red'; // 'red' hoặc 'green'

        this.redZone = [];
        this.greenZone = [];

        this.image = new Image();
        this.imageLoaded = false;

        this.draggingPointIndex = -1;
        this.draggingZone = null;
        this.scale = 1.0;

        this.initEvents();
    }

    initEvents() {
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', () => this.onMouseUp());

        // Hỗ trợ cảm ứng trên điện thoại & máy tính bảng
        this.canvas.addEventListener('touchstart', (e) => {
            if (e.touches && e.touches.length === 1) {
                e.preventDefault();
                const touch = e.touches[0];
                this.onMouseDown({ clientX: touch.clientX, clientY: touch.clientY });
            }
        }, { passive: false });

        this.canvas.addEventListener('touchmove', (e) => {
            if (e.touches && e.touches.length === 1) {
                e.preventDefault();
                const touch = e.touches[0];
                this.onMouseMove({ clientX: touch.clientX, clientY: touch.clientY });
            }
        }, { passive: false });

        this.canvas.addEventListener('touchend', () => {
            this.onMouseUp();
        });
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

    updateStatsBar(savedTime = null) {
        const statsElem = document.getElementById('saveStatusBar');
        if (!statsElem) return;

        const redCount = this.redZone.length;
        const greenCount = this.greenZone.length;

        let statusHtml = `
            <span><i class="fa-solid fa-draw-polygon" style="color: #dc2626;"></i> Red Zone: <strong>${redCount} điểm</strong></span>
            <span><i class="fa-solid fa-shield-halved" style="color: #059669;"></i> Green Zone: <strong>${greenCount} điểm</strong></span>
        `;

        if (savedTime) {
            statusHtml += `<span style="color: var(--success); font-weight: 600;"><i class="fa-solid fa-cloud-arrow-up"></i> Đã lưu vào CSDL lúc ${savedTime}</span>`;
        } else {
            statusHtml += `<span style="color: var(--text-muted);"><i class="fa-solid fa-pen-ruler"></i> Đang chỉnh sửa...</span>`;
        }

        statsElem.innerHTML = statusHtml;
    }

    loadImage(src) {
        this.imageLoaded = false;
        this.image.crossOrigin = "anonymous";
        this.image.onload = () => {
            this.imageLoaded = true;
            this.canvas.width = this.image.naturalWidth || 1920;
            this.canvas.height = this.image.naturalHeight || 1080;
            this.render();
            this.updateStatsBar();
        };
        this.image.src = src;
    }

    setMode(mode) {
        this.currentMode = mode;
        this.render();
    }

    getCanvasCoords(e) {
        const rect = this.canvas.getBoundingClientRect();
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;
        return [
            Math.round((e.clientX - rect.left) * scaleX),
            Math.round((e.clientY - rect.top) * scaleY)
        ];
    }

    findPointNear(coords, zone) {
        const threshold = 22;
        const [x, y] = coords;
        for (let i = 0; i < zone.length; i++) {
            const [px, py] = zone[i];
            const dist = Math.hypot(px - x, py - y);
            if (dist < threshold) {
                return i;
            }
        }
        return -1;
    }

    onMouseDown(e) {
        if (!this.imageLoaded) return;
        const coords = this.getCanvasCoords(e);
        const activeZone = this.currentMode === 'red' ? this.redZone : this.greenZone;

        // Kiểm tra xem có đang bấm vào điểm đã có để kéo hay không
        const nearIdx = this.findPointNear(coords, activeZone);
        if (nearIdx !== -1) {
            this.draggingPointIndex = nearIdx;
            this.draggingZone = this.currentMode;
            return;
        }

        // Thêm điểm mới vào đa giác
        activeZone.push(coords);
        this.render();
        this.updateStatsBar();
    }

    onMouseMove(e) {
        if (this.draggingPointIndex !== -1 && this.draggingZone) {
            const coords = this.getCanvasCoords(e);
            const activeZone = this.draggingZone === 'red' ? this.redZone : this.greenZone;
            activeZone[this.draggingPointIndex] = coords;
            this.render();
            this.updateStatsBar();
        }
    }

    onMouseUp() {
        this.draggingPointIndex = -1;
        this.draggingZone = null;
    }

    clearCurrentZone() {
        if (this.currentMode === 'red') {
            this.redZone = [];
        } else {
            this.greenZone = [];
        }
        this.render();
        this.updateStatsBar();
    }

    render() {
        if (!this.imageLoaded) return;
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;

        ctx.clearRect(0, 0, w, h);
        ctx.drawImage(this.image, 0, 0, w, h);

        // 1. Vẽ Red Zone (Bàn học)
        this.drawPolygon(this.redZone, 'rgba(239, 68, 68, 0.35)', '#dc2626', 'RED ZONE (BÀN HỌC)');

        // 2. Vẽ Green Zone (Bục giảng)
        this.drawPolygon(this.greenZone, 'rgba(16, 185, 129, 0.35)', '#059669', 'GREEN ZONE (BỤC GIẢNG - LOẠI TRỪ)');
    }

    drawPolygon(points, fillColor, strokeColor, label) {
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

        // Vẽ các điểm neo (vertex handles)
        points.forEach(([x, y], idx) => {
            ctx.beginPath();
            ctx.arc(x, y, 7, 0, 2 * Math.PI);
            ctx.fillStyle = '#ffffff';
            ctx.fill();
            ctx.strokeStyle = strokeColor;
            ctx.lineWidth = 3;
            ctx.stroke();

            // Số thứ tự đỉnh
            ctx.font = 'bold 12px Inter, sans-serif';
            ctx.fillStyle = '#0f172a';
            ctx.fillText(`${idx + 1}`, x + 10, y - 10);
        });

        // Vẽ nhãn vùng
        if (points.length >= 1) {
            ctx.font = 'bold 14px Inter, sans-serif';
            ctx.fillStyle = strokeColor;
            ctx.fillText(label, points[0][0] + 10, points[0][1] - 15);
        }
    }

    async loadClassroomROI(classId, forceRefresh = false) {
        this.currentClassId = classId;
        try {
            const url = `/api/roi/${classId}${forceRefresh ? '?refresh=true' : ''}`;
            const res = await fetch(url);
            const data = await res.json();
            this.redZone = data.red_zone || [];
            this.greenZone = data.green_zone || [];
            
            let snapshotUrl = data.snapshot_url || `/dataset/samples/classroom_sample_1.jpg`;
            // Luôn thêm timestamp chống dính cache trình duyệt
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
            const res = await fetch(`/api/roi/${classId}/refresh-snapshot`, { method: 'POST' });
            const data = await res.json();
            if (data.snapshot_url) {
                const bustUrl = data.snapshot_url + (data.snapshot_url.includes('?') ? '&' : '?') + '_t=' + Date.now();
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
            const res = await fetch(`/api/roi/${classId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    red_zone: this.redZone,
                    green_zone: this.greenZone,
                    image_width: this.canvas.width || 1920,
                    image_height: this.canvas.height || 1080
                })
            });

            const result = await res.json();
            const nowTime = new Date().toLocaleTimeString('vi-VN');

            if (res.ok && result.success) {
                if (btnSave) {
                    btnSave.className = 'btn btn-success pulse-success';
                    btnSave.innerHTML = '<i class="fa-solid fa-check"></i> ĐÃ LƯU THÀNH CÔNG!';
                }

                this.showToast(
                    "✓ Đã Lưu Thành Công!",
                    `Tọa độ Red Zone (${this.redZone.length} điểm) & Green Zone (${this.greenZone.length} điểm) cho ${className} đã được lưu vào CSDL lúc ${nowTime}.`
                );

                this.updateStatsBar(nowTime);

                // Khôi phục nút sau 2.5 giây
                setTimeout(() => {
                    if (btnSave) {
                        btnSave.disabled = false;
                        btnSave.className = 'btn btn-primary';
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
                btnSave.className = 'btn btn-secondary';
                btnSave.style.border = '2px solid #ef4444';
                btnSave.style.color = '#dc2626';
                btnSave.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Thử Lại';
            }
            this.showToast("Lỗi Lưu CSDL", err.message, true);
        }
    }
}

window.ROICanvasEditor = ROICanvasEditor;
