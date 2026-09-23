/**
 * ImageZoomViewer - Bộ điều khiển phóng to / thu nhỏ ảnh bằng con lăn chuột (Mouse Wheel Zoom)
 * và kéo thả di chuyển ảnh (Mouse Pan / Drag) mượt mà, hỗ trợ kiểm tra chi tiết học sinh trong lớp.
 */

export class ImageZoomViewer {
    constructor(options = {}) {
        this.viewport = typeof options.viewport === 'string' ? document.getElementById(options.viewport) : options.viewport;
        this.layer = typeof options.layer === 'string' ? document.getElementById(options.layer) : options.layer;
        this.img = typeof options.img === 'string' ? document.getElementById(options.img) : options.img;

        this.scale = 1.0;
        this.translateX = 0;
        this.translateY = 0;
        this.minScale = options.minScale || 0.6;
        this.maxScale = options.maxScale || 12.0;

        this.isDragging = false;
        this.startX = 0;
        this.startY = 0;

        this.onZoomChange = options.onZoomChange || null;

        this.boundWheel = (e) => this.onWheel(e);
        this.boundMouseDown = (e) => this.onMouseDown(e);
        this.boundMouseMove = (e) => this.onMouseMove(e);
        this.boundMouseUp = (e) => this.onMouseUp(e);
        this.boundDblClick = (e) => this.onDblClick(e);

        this.init();
    }

    init() {
        if (!this.viewport || !this.layer || !this.img) return;

        // Bắt sự kiện con lăn chuột trực tiếp trên khung nhìn viewport
        this.viewport.addEventListener('wheel', this.boundWheel, { passive: false });

        // Kéo thả chuột
        this.viewport.addEventListener('mousedown', this.boundMouseDown);
        window.addEventListener('mousemove', this.boundMouseMove);
        window.addEventListener('mouseup', this.boundMouseUp);

        // Nhấp đúp chuột để phóng to nhanh hoặc đặt lại
        this.viewport.addEventListener('dblclick', this.boundDblClick);

        // Chặn drag mặc định của thẻ img để kéo mượt mà
        this.img.addEventListener('dragstart', (e) => e.preventDefault());
    }

    destroy() {
        if (!this.viewport) return;
        this.viewport.removeEventListener('wheel', this.boundWheel);
        this.viewport.removeEventListener('mousedown', this.boundMouseDown);
        window.removeEventListener('mousemove', this.boundMouseMove);
        window.removeEventListener('mouseup', this.boundMouseUp);
        this.viewport.removeEventListener('dblclick', this.boundDblClick);
    }

    onWheel(e) {
        e.preventDefault();
        if (!this.viewport || !this.img) return;

        const rect = this.viewport.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // Tốc độ zoom mượt mà theo con lăn chuột
        const zoomFactor = e.deltaY < 0 ? 1.20 : (1 / 1.20);
        this.zoomAt(mouseX, mouseY, zoomFactor);
    }

    zoomAt(pivotX, pivotY, factor) {
        const newScale = Math.min(this.maxScale, Math.max(this.minScale, this.scale * factor));
        if (Math.abs(newScale - this.scale) < 0.001) return;

        // Giữ nguyên điểm dưới con trỏ chuột khi phóng to/thu nhỏ
        const contentX = (pivotX - this.translateX) / this.scale;
        const contentY = (pivotY - this.translateY) / this.scale;

        this.translateX = pivotX - contentX * newScale;
        this.translateY = pivotY - contentY * newScale;
        this.scale = newScale;

        this.applyTransform();
    }

    onMouseDown(e) {
        if (e.button !== 0) return; // Chỉ nhận chuột trái
        this.isDragging = true;
        this.startX = e.clientX - this.translateX;
        this.startY = e.clientY - this.translateY;
        if (this.viewport) this.viewport.classList.add('is-dragging');
    }

    onMouseMove(e) {
        if (!this.isDragging) return;
        this.translateX = e.clientX - this.startX;
        this.translateY = e.clientY - this.startY;
        this.applyTransform();
    }

    onMouseUp(e) {
        if (this.isDragging) {
            this.isDragging = false;
            if (this.viewport) this.viewport.classList.remove('is-dragging');
        }
    }

    onDblClick(e) {
        const rect = this.viewport.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        if (this.scale > 1.25) {
            this.reset(true);
        } else {
            // Phóng to nhanh 2.6x ngay tâm điểm nhấp đúp
            this.zoomAt(mouseX, mouseY, 2.6 / this.scale);
        }
    }

    zoomIn() {
        if (!this.viewport) return;
        const rect = this.viewport.getBoundingClientRect();
        this.zoomAt(rect.width / 2, rect.height / 2, 1.3);
    }

    zoomOut() {
        if (!this.viewport) return;
        const rect = this.viewport.getBoundingClientRect();
        this.zoomAt(rect.width / 2, rect.height / 2, 1 / 1.3);
    }

    reset(animated = false) {
        this.scale = 1.0;
        this.translateX = 0;
        this.translateY = 0;
        this.applyTransform(animated);
    }

    applyTransform(animated = false) {
        if (!this.layer) return;
        if (animated) {
            this.layer.style.transition = 'transform 0.25s cubic-bezier(0.16, 1, 0.3, 1)';
            setTimeout(() => {
                if (this.layer) this.layer.style.transition = '';
            }, 260);
        } else {
            this.layer.style.transition = '';
        }

        this.layer.style.transform = `translate3d(${Math.round(this.translateX)}px, ${Math.round(this.translateY)}px, 0) scale(${this.scale.toFixed(4)})`;

        if (typeof this.onZoomChange === 'function') {
            this.onZoomChange(this.scale);
        }
    }

    /**
     * Tự động liên kết các nút bấm điều khiển trên thanh công cụ
     */
    bindControls(controls = {}) {
        if (controls.btnZoomIn) {
            controls.btnZoomIn.addEventListener('click', () => this.zoomIn());
        }
        if (controls.btnZoomOut) {
            controls.btnZoomOut.addEventListener('click', () => this.zoomOut());
        }
        if (controls.btnReset) {
            controls.btnReset.addEventListener('click', () => this.reset(true));
        }
        if (controls.levelPill) {
            controls.levelPill.addEventListener('click', () => this.reset(true));
        }
        if (controls.btnFullscreen && controls.modalDialog) {
            controls.btnFullscreen.addEventListener('click', () => {
                const isFull = controls.modalDialog.classList.toggle('is-fullscreen');
                controls.btnFullscreen.innerHTML = isFull 
                    ? '<i class="fa-solid fa-compress"></i>' 
                    : '<i class="fa-solid fa-expand"></i>';
                controls.btnFullscreen.title = isFull ? 'Thu nhỏ cửa sổ' : 'Toàn màn hình';
                setTimeout(() => this.applyTransform(), 150);
            });
        }
    }
}

window.ImageZoomViewer = ImageZoomViewer;
