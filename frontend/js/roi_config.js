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

    // =========================================================
    // TÍNH NĂNG: ÁP DỤNG TỌA ĐỘ ROI CHO TẤT CẢ CÁC LỚP HỌC
    // =========================================================
    const btnApplyAllROI = document.getElementById('btnApplyAllROI');
    const modalApplyAllRoi = document.getElementById('modalApplyAllRoi');
    const modalApplyAllCloseBtn = document.getElementById('modalApplyAllCloseBtn');
    const btnCancelApplyAllModal = document.getElementById('btnCancelApplyAllModal');
    const btnConfirmApplyAll = document.getElementById('btnConfirmApplyAll');
    const applyAllSourceClass = document.getElementById('applyAllSourceClass');
    const applyAllPointCount = document.getElementById('applyAllPointCount');
    const applyAllResolution = document.getElementById('applyAllResolution');
    const applyTotalCount = document.getElementById('applyTotalCount');
    const scopeAllClasses = document.getElementById('scopeAllClasses');
    const scopeCustomClasses = document.getElementById('scopeCustomClasses');
    const applyCustomClassListWrap = document.getElementById('applyCustomClassListWrap');
    const applyTargetClassCheckboxes = document.getElementById('applyTargetClassCheckboxes');
    const checkSelectAllTargetClasses = document.getElementById('checkSelectAllTargetClasses');
    const selectedTargetCountBadge = document.getElementById('selectedTargetCountBadge');

    const updateTargetCountBadge = () => {
        if (!applyTargetClassCheckboxes || !selectedTargetCountBadge) return;
        const total = applyTargetClassCheckboxes.querySelectorAll('input[type="checkbox"]').length;
        const checked = applyTargetClassCheckboxes.querySelectorAll('input[type="checkbox"]:checked').length;
        selectedTargetCountBadge.textContent = `${checked}/${total}`;
        if (checkSelectAllTargetClasses) {
            checkSelectAllTargetClasses.checked = (checked === total && total > 0);
            checkSelectAllTargetClasses.indeterminate = (checked > 0 && checked < total);
        }
    };

    const renderTargetClassCheckboxes = (sourceClassId) => {
        if (!applyTargetClassCheckboxes) return;
        applyTargetClassCheckboxes.innerHTML = classrooms.map(c => {
            const isSource = String(c.id) === String(sourceClassId);
            return `
                <label style="display: flex; align-items: center; gap: 5px; font-size: 0.82rem; padding: 3px 6px; border-radius: 4px; background: ${isSource ? '#eff6ff' : '#f8fafc'}; border: 1px solid ${isSource ? '#bfdbfe' : '#e2e8f0'}; cursor: pointer;">
                    <input type="checkbox" class="target-cls-item" value="${c.id}" checked>
                    <span style="font-weight: ${isSource ? '700' : '500'}; color: ${isSource ? '#1d4ed8' : '#334155'};">
                        ${esc(c.name)} ${isSource ? '<span style="font-size: 0.72rem; color: #2563eb;">(mẫu)</span>' : ''}
                    </span>
                </label>
            `;
        }).join('');

        applyTargetClassCheckboxes.querySelectorAll('.target-cls-item').forEach(cb => {
            cb.addEventListener('change', updateTargetCountBadge);
        });
        updateTargetCountBadge();
    };

    const closeApplyAllModal = () => {
        if (modalApplyAllRoi) {
            modalApplyAllRoi.classList.remove('active');
        }
    };

    if (btnApplyAllROI) {
        btnApplyAllROI.addEventListener('click', () => {
            const greenPts = editor ? (editor.greenZone || []) : [];
            const redPts = editor ? (editor.redZone || []) : [];

            if (greenPts.length === 0 && redPts.length === 0) {
                showToast('Chưa có vùng ROI nào được vẽ! Vui lòng vẽ vùng nhận diện (bàn học) trước khi áp dụng cho tất cả.', 'warning');
                return;
            }

            const currentId = String(classSelect ? classSelect.value : (editor ? editor.currentClassId : 1));
            const currentClass = classrooms.find(c => String(c.id) === currentId) || { id: currentId, name: `Lớp ${currentId}` };

            if (applyAllSourceClass) {
                applyAllSourceClass.textContent = `${currentClass.name} (${currentClass.room_number || 'Phòng ' + currentClass.id})`;
            }
            if (applyAllPointCount) {
                applyAllPointCount.textContent = `${greenPts.length}`;
            }
            if (applyAllResolution) {
                const w = (editor && editor.canvas) ? editor.canvas.width : 1920;
                const h = (editor && editor.canvas) ? editor.canvas.height : 1080;
                applyAllResolution.textContent = `${w} × ${h}`;
            }
            if (applyTotalCount) {
                applyTotalCount.textContent = `${classrooms.length}`;
            }

            if (scopeAllClasses) scopeAllClasses.checked = true;
            if (scopeCustomClasses) scopeCustomClasses.checked = false;
            if (applyCustomClassListWrap) applyCustomClassListWrap.style.display = 'none';

            renderTargetClassCheckboxes(currentId);

            if (modalApplyAllRoi) {
                modalApplyAllRoi.classList.add('active');
            }
        });
    }

    if (modalApplyAllCloseBtn) modalApplyAllCloseBtn.addEventListener('click', closeApplyAllModal);
    if (btnCancelApplyAllModal) btnCancelApplyAllModal.addEventListener('click', closeApplyAllModal);

    if (modalApplyAllRoi) {
        modalApplyAllRoi.addEventListener('click', (e) => {
            if (e.target === modalApplyAllRoi) closeApplyAllModal();
        });
    }

    if (scopeAllClasses) {
        scopeAllClasses.addEventListener('change', () => {
            if (applyCustomClassListWrap) applyCustomClassListWrap.style.display = 'none';
        });
    }
    if (scopeCustomClasses) {
        scopeCustomClasses.addEventListener('change', () => {
            if (applyCustomClassListWrap) applyCustomClassListWrap.style.display = 'block';
        });
    }

    if (checkSelectAllTargetClasses) {
        checkSelectAllTargetClasses.addEventListener('change', (e) => {
            const checked = e.target.checked;
            if (applyTargetClassCheckboxes) {
                applyTargetClassCheckboxes.querySelectorAll('.target-cls-item').forEach(cb => {
                    cb.checked = checked;
                });
            }
            updateTargetCountBadge();
        });
    }

    // Xác nhận áp dụng hàng loạt
    if (btnConfirmApplyAll) {
        btnConfirmApplyAll.addEventListener('click', async () => {
            const greenPts = editor ? (editor.greenZone || []) : [];
            const redPts = editor ? (editor.redZone || []) : [];
            const currentId = parseInt(classSelect ? classSelect.value : (editor ? editor.currentClassId : 1), 10);

            let targetClassIds = null;
            if (scopeCustomClasses && scopeCustomClasses.checked) {
                const checkedBoxes = applyTargetClassCheckboxes.querySelectorAll('.target-cls-item:checked');
                if (checkedBoxes.length === 0) {
                    showToast('Vui lòng chọn ít nhất 1 phòng học để áp dụng!', 'warning');
                    return;
                }
                targetClassIds = Array.from(checkedBoxes).map(cb => parseInt(cb.value, 10));
            }

            const originalBtnHtml = btnConfirmApplyAll.innerHTML;
            btnConfirmApplyAll.disabled = true;
            btnConfirmApplyAll.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang Áp Dụng CSDL...';

            try {
                const apiObj = window.ROIAPI || ROIAPI;
                const payload = {
                    source_classroom_id: currentId,
                    green_zone: greenPts,
                    red_zone: redPts,
                    image_width: (editor && editor.canvas) ? editor.canvas.width : 1920,
                    image_height: (editor && editor.canvas) ? editor.canvas.height : 1080,
                    target_classroom_ids: targetClassIds
                };

                const res = await apiObj.applyAll(payload);

                if (res && res.success) {
                    closeApplyAllModal();
                    const count = res.updated_count || (targetClassIds ? targetClassIds.length : classrooms.length);
                    showToast(`✓ Đã áp dụng thành công tọa độ ROI cho ${count} lớp học!`, 'success');

                    // Hiệu ứng hoàn tất trên nút bấm chính
                    if (btnApplyAllROI) {
                        const prevHtml = btnApplyAllROI.innerHTML;
                        btnApplyAllROI.classList.remove('btn-apply-all');
                        btnApplyAllROI.classList.add('btn-success', 'pulse-success');
                        btnApplyAllROI.innerHTML = `<i class="fa-solid fa-check"></i> ĐÃ ÁP DỤNG (${count} LỚP)`;
                        setTimeout(() => {
                            btnApplyAllROI.classList.remove('btn-success', 'pulse-success');
                            btnApplyAllROI.classList.add('btn-apply-all');
                            btnApplyAllROI.innerHTML = prevHtml;
                        }, 3500);
                    }
                } else {
                    throw new Error(res.error || res.detail || 'Lỗi không thể lưu đồng loạt');
                }
            } catch (err) {
                console.error('Lỗi khi áp dụng ROI cho tất cả:', err);
                showToast('Lỗi khi áp dụng ROI: ' + (err.message || err), 'error');
            } finally {
                btnConfirmApplyAll.disabled = false;
                btnConfirmApplyAll.innerHTML = originalBtnHtml;
            }
        });
    }
});
