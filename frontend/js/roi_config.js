/**
 * roi_config.js - ROI Polygon Setup Page Controller
 * THPT Điều Cải - Attendance System
 */
import { CameraAPI, ROIAPI, showToast, API_BASE } from './api.js';

let editor = null;

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

    if (classSelect) {
        classSelect.innerHTML = classrooms.map(c => `
            <option value="${c.id}">${c.name} (${c.room_number || 'Phòng ' + c.id}) - Chuẩn: ${c.standard_count || 40} HS</option>
        `).join('');

        if (targetClassId) {
            classSelect.value = targetClassId;
        }

        // Change classroom
        classSelect.addEventListener('change', (e) => {
            editor.loadClassroomROI(e.target.value, false);
        });
    }

    // Initial load
    if (classrooms.length > 0) {
        const initialId = (targetClassId && classrooms.some(c => String(c.id) === String(targetClassId))) 
            ? targetClassId 
            : (classSelect ? classSelect.value : classrooms[0].id);
        
        if (btnModeGreen) btnModeGreen.click();
        editor.loadClassroomROI(initialId, forceRefresh);
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
