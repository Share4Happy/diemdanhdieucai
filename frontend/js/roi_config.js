/**
 * roi_config.js - ROI Polygon Setup Page Controller
 * THPT Điều Cải - Attendance System
 */
import { CameraAPI, ROIAPI, showToast, API_BASE, escapeHtml } from './api.js';

let editor = null;

const esc = (v) => escapeHtml(v);

document.addEventListener('DOMContentLoaded', async () => {
    // Instantiate ROI Canvas Editor
    if (typeof window.ROICanvasEditor === 'function') {
        editor = new window.ROICanvasEditor('roiCanvas');
        window.roiEditor = editor;
    } else {
        console.error('ROICanvasEditor not found on window');
        return;
    }

    const classSelect = document.getElementById('classSelect');
    const btnCanvasPrevClass = document.getElementById('btnCanvasPrevClass');
    const btnCanvasNextClass = document.getElementById('btnCanvasNextClass');
    const canvasNavPrevTooltip = document.getElementById('canvasNavPrevTooltip');
    const canvasNavNextTooltip = document.getElementById('canvasNavNextTooltip');
    const canvasFloatingClassName = document.getElementById('canvasFloatingClassName');
    const btnModeGreen = document.getElementById('btnModeGreen');
    const btnClearZone = document.getElementById('btnClearZone');
    const btnSaveROI = document.getElementById('btnSaveROI');
    const btnRefreshSnapshot = document.getElementById('btnRefreshSnapshot');
    const btnHeaderSnapshot = document.getElementById('btnHeaderSnapshot');
    const resSelect = document.getElementById('resSelect');
    const btnUndoPoint = document.getElementById('btnUndoPoint');
    const btnFourCorners = document.getElementById('btnFourCorners');

    // Read URL query parameters (?class_id=1&refresh=true)
    const urlParams = new URLSearchParams(window.location.search);
    const targetClassId = urlParams.get('class_id');
    const forceRefresh = urlParams.get('refresh') === 'true';

    // Load classrooms list
    let classrooms = [];
    try {
        const apiObj = window.CameraAPI || CameraAPI;
        const camData = await apiObj.getAll();
        classrooms = camData.cameras || [];
    } catch (err) {
        console.warn('Không thể kết nối Backend API để nạp danh sách camera:', err);
        showToast('Chưa kết nối Backend (Port 8000). Đang sử dụng danh sách 30 lớp học chuẩn.', 'warning');
        
        // Danh sách 30 lớp học chuẩn dự phòng khi backend chưa bật
        const grades = ['10A', '11A', '12A'];
        let idCounter = 1;
        grades.forEach(g => {
            for (let i = 1; i <= 10; i++) {
                classrooms.push({
                    id: idCounter,
                    name: `Lớp ${g}${i}`,
                    room_number: `Phòng ${100 + idCounter}`,
                    standard_count: 40
                });
                idCounter++;
            }
        });
    }

    // Helper: Cập nhật giao diện Stepper (tooltips & huy hiệu nổi góc ảnh)
    const updateClassStepperUI = () => {
        if (!classrooms || classrooms.length === 0 || !classSelect) return;
        const currentId = String(classSelect.value);
        const currentIndex = classrooms.findIndex(c => String(c.id) === currentId);
        const currentClass = classrooms[currentIndex] || classrooms[0];
        const displayIdx = currentIndex >= 0 ? currentIndex + 1 : 1;

        if (canvasFloatingClassName && currentClass) {
            canvasFloatingClassName.textContent = `${currentClass.name} (${currentClass.room_number || 'Phòng ' + currentClass.id}) • ${displayIdx}/${classrooms.length}`;
        }

        const prevIdx = (currentIndex - 1 + classrooms.length) % classrooms.length;
        const prevClass = classrooms[prevIdx];
        if (btnCanvasPrevClass && prevClass) {
            btnCanvasPrevClass.title = `Chuyển về phòng trước: ${prevClass.name} (Phím tắt: ← hoặc [)`;
        }
        if (canvasNavPrevTooltip && prevClass) {
            canvasNavPrevTooltip.textContent = `← ${prevClass.name}`;
        }

        const nextIdx = (currentIndex + 1) % classrooms.length;
        const nextClass = classrooms[nextIdx];
        if (btnCanvasNextClass && nextClass) {
            btnCanvasNextClass.title = `Chuyển sang phòng tiếp: ${nextClass.name} (Phím tắt: → hoặc ])`;
        }
        if (canvasNavNextTooltip && nextClass) {
            canvasNavNextTooltip.textContent = `${nextClass.name} →`;
        }
    };

    // Helper: Chuyển tiến / lùi một lớp học
    const stepClassroom = (delta) => {
        if (!classrooms || classrooms.length === 0 || !classSelect) return;
        const currentId = String(classSelect.value);
        let currentIndex = classrooms.findIndex(c => String(c.id) === currentId);
        if (currentIndex === -1) currentIndex = 0;

        const newIndex = (currentIndex + delta + classrooms.length) % classrooms.length;
        const targetClass = classrooms[newIndex];
        if (targetClass) {
            classSelect.value = String(targetClass.id);
            editor.loadClassroomROI(targetClass.id, false);
            updateClassStepperUI();
            showToast(`Đã chuyển: ${targetClass.name} (${targetClass.room_number || 'Phòng ' + targetClass.id})`, 'info');
        }
    };

    if (classSelect) {
        classSelect.innerHTML = classrooms.map(c => `
            <option value="${c.id}">${esc(c.name)} (${esc(c.room_number || 'Phòng ' + c.id)}) - Chuẩn: ${c.standard_count || 40} HS</option>
        `).join('');

        if (targetClassId) {
            classSelect.value = targetClassId;
        }

        // Change classroom via dropdown
        classSelect.addEventListener('change', (e) => {
            editor.loadClassroomROI(e.target.value, false);
            updateClassStepperUI();
        });
    }

    // Sự kiện 2 nút chuyển phòng nổi trên ảnh
    if (btnCanvasPrevClass) {
        btnCanvasPrevClass.addEventListener('click', (e) => {
            e.stopPropagation();
            stepClassroom(-1);
        });
    }
    if (btnCanvasNextClass) {
        btnCanvasNextClass.addEventListener('click', (e) => {
            e.stopPropagation();
            stepClassroom(1);
        });
    }

    // Phím tắt bàn phím: ← / → hoặc [ / ] để duyệt phòng siêu nhanh
    document.addEventListener('keydown', (e) => {
        const tag = (e.target.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

        if (e.key === 'ArrowLeft' || e.key === '[') {
            e.preventDefault();
            stepClassroom(-1);
        } else if (e.key === 'ArrowRight' || e.key === ']') {
            e.preventDefault();
            stepClassroom(1);
        }
    });

    // Initial load
    if (classrooms.length > 0) {
        const initialId = (targetClassId && classrooms.some(c => String(c.id) === String(targetClassId))) 
            ? targetClassId 
            : (classSelect ? classSelect.value : classrooms[0].id);
        
        if (btnModeGreen) btnModeGreen.click();
        editor.loadClassroomROI(initialId, forceRefresh);
        updateClassStepperUI();
    }

    // Refresh snapshot
    if (btnRefreshSnapshot) {
        btnRefreshSnapshot.addEventListener('click', () => editor.refreshSnapshot());
    }
    if (btnHeaderSnapshot) {
        btnHeaderSnapshot.addEventListener('click', () => editor.refreshSnapshot());
    }

    // Mode Green Zone (Vùng Nhận Diện)
    if (btnModeGreen) {
        btnModeGreen.addEventListener('click', () => {
            editor.setMode('green');
            btnModeGreen.classList.add('active');
        });
    }

    // Resolution mode
    if (resSelect) {
        resSelect.addEventListener('change', (e) => {
            editor.setResolutionMode(e.target.value);
        });
    }

    // Undo
    if (btnUndoPoint) {
        btnUndoPoint.addEventListener('click', () => {
            editor.undo();
        });
    }

    // Four corners
    if (btnFourCorners) {
        btnFourCorners.addEventListener('click', () => {
            editor.addFourCorners();
        });
    }

    // Clear zone
    if (btnClearZone) {
        btnClearZone.addEventListener('click', () => {
            if (confirm("Bạn có chắc chắn muốn xóa đa giác đang chọn không?")) {
                editor.clearCurrentZone();
            }
        });
    }

    // Save ROI
    if (btnSaveROI) {
        btnSaveROI.addEventListener('click', () => {
            editor.saveROI();
        });
    }
});
