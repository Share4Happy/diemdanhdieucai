/**
 * ===================================================================
 * CAMERA CRUD MODULE - THPT ĐIỀU CẢI AI CAMERA
 * Quản lý Thêm/Sửa/Xóa Camera, Dò Webcam USB, Kiểm Tra Nguồn Stream & Wizard
 * ===================================================================
 */

import { CameraAPI, showToast, escapeHtml } from '../../api.js?v=9.2';

const esc = (v) => escapeHtml(v);

let currentSourceType = 'NVR';
let crudCameras = [];
let externalCallbacks = {
    onRefreshCameras: null
};

export function setCrudCallbacks(callbacks) {
    externalCallbacks = { ...externalCallbacks, ...callbacks };
}

export function setCrudCameras(cams) {
    crudCameras = cams || [];
}

let nvrChannelsList = [];

export async function loadNvrDevicesAndChannels(selectedChannelNumber = null) {
    const selNvr = document.getElementById('selectNvrDevice');
    const selCh = document.getElementById('selectNvrChannel');
    if (!selCh) return;

    try {
        if (selNvr) {
            try {
                let nvrData = null;
                if (CameraAPI && typeof CameraAPI.listNVRs === 'function') {
                    nvrData = await CameraAPI.listNVRs();
                } else {
                    const res = await fetch('/api/cameras/nvr/list');
                    if (res.ok) nvrData = await res.json();
                }
                if (nvrData && nvrData.nvrs && nvrData.nvrs.length > 0) {
                    selNvr.innerHTML = nvrData.nvrs.map(n => 
                        `<option value="${n.id}">${esc(n.name)} (${esc(n.ip_address)} - ${esc(n.brand)})</option>`
                    ).join('');
                } else {
                    selNvr.innerHTML = `<option value="default">Đầu Ghi NVR THPT Điều Cải (192.168.1.200 - HIKVISION)</option>`;
                }
            } catch (e) {
                selNvr.innerHTML = `<option value="default">Đầu Ghi NVR THPT Điều Cải (192.168.1.200 - HIKVISION)</option>`;
            }
        }

        const nvrId = (selNvr && selNvr.value !== 'default') ? selNvr.value : null;
        selCh.innerHTML = '<option value="">-- Đang nạp danh sách 30 kênh NVR... --</option>';
        
        let data = null;
        if (CameraAPI && typeof CameraAPI.getNVRChannels === 'function') {
            data = await CameraAPI.getNVRChannels(nvrId);
        } else if (window.CameraAPI && typeof window.CameraAPI.getNVRChannels === 'function') {
            data = await window.CameraAPI.getNVRChannels(nvrId);
        } else {
            const url = nvrId ? `/api/cameras/nvr/channels?nvr_id=${nvrId}` : '/api/cameras/nvr/channels';
            const res = await fetch(url);
            if (res.ok) data = await res.json();
        }

        if (data && data.channels && data.channels.length > 0) {
            nvrChannelsList = data.channels;
            renderNvrChannelSelectOptions(selectedChannelNumber);
        } else {
            selCh.innerHTML = '<option value="">-- Không tìm thấy kênh nào từ đầu ghi --</option>';
        }
    } catch (err) {
        console.error('Lỗi nạp danh sách kênh NVR:', err);
        if (selCh) {
            selCh.innerHTML = '<option value="">-- Lỗi kết nối nạp kênh NVR --</option>';
        }
    }
}

export function renderNvrChannelSelectOptions(selectedChannelNumber = null) {
    const selCh = document.getElementById('selectNvrChannel');
    if (!selCh || !nvrChannelsList.length) return;

    let targetCh = selectedChannelNumber;
    if (!targetCh) {
        const firstUnassigned = nvrChannelsList.find(c => !c.is_assigned);
        targetCh = firstUnassigned ? firstUnassigned.channel_number : nvrChannelsList[0].channel_number;
    }

    selCh.innerHTML = '<option value="">-- Chọn 1 kênh camera từ đầu ghi --</option>' +
        nvrChannelsList.map(c => {
            const isSel = String(c.channel_number) === String(targetCh);
            const statusLabel = c.is_assigned ? ` [Đã gán: ${esc(c.assigned_classroom_name || c.name)}]` : ' [Chưa gán]';
            return `<option value="${c.channel_number}" ${isSel ? 'selected' : ''}>Kênh ${String(c.channel_number).padStart(2, '0')} - ${esc(c.name)} (${esc(c.room_number)})${statusLabel}</option>`;
        }).join('');

    if (targetCh) {
        applySelectedNvrChannel(targetCh);
    }
}

export function applySelectedNvrChannel(channelNumber) {
    const ch = nvrChannelsList.find(c => String(c.channel_number) === String(channelNumber));
    if (!ch) return;

    syncManualUrl(ch.rtsp_url);
    const rInput = document.getElementById('inputRtsp');
    if (rInput) rInput.value = ch.rtsp_url;

    const isEdit = !!document.getElementById('formCamId')?.value;
    if (!isEdit) {
        const codeInput = document.getElementById('formCode');
        const nameInput = document.getElementById('formName');
        const roomInput = document.getElementById('formRoom');
        const stdInput = document.getElementById('formStandard');

        if (codeInput && (!codeInput.value || codeInput.value.startsWith('LOP_') || codeInput.value.startsWith('CAM_'))) {
            codeInput.value = ch.code;
        }
        if (nameInput && (!nameInput.value || nameInput.value.startsWith('Lớp ') || nameInput.value.startsWith('Camera '))) {
            nameInput.value = ch.name;
        }
        if (roomInput && (!roomInput.value || roomInput.value.startsWith('Phòng '))) {
            roomInput.value = ch.room_number;
        }
        if (stdInput) {
            stdInput.value = ch.standard_count || 40;
        }
    }

    const hintBox = document.getElementById('nvrSelectedChannelHint');
    const hintText = document.getElementById('nvrSelectedChannelText');
    if (hintBox && hintText) {
        hintBox.style.display = 'block';
        hintText.innerHTML = `<strong>Kênh ${ch.channel_number}:</strong> ${esc(ch.name)} (${esc(ch.room_number)}) &bull; Luồng: <code style="font-size: 0.8rem;">${esc(ch.rtsp_url)}</code>`;
    }
}

export function switchSourceTab(type = 'NVR') {
    currentSourceType = type;
    const tabNvr = document.getElementById('tabBtnNvrSelect');
    const tabRtsp = document.getElementById('tabBtnRtsp');

    if (tabNvr) tabNvr.classList.toggle('active', type === 'NVR');
    if (tabRtsp) tabRtsp.classList.toggle('active', type === 'RTSP');

    const pNvr = document.getElementById('panelNvrSelect');
    const pRtsp = document.getElementById('panelRtsp');

    if (pNvr) pNvr.style.display = (type === 'NVR') ? 'block' : 'none';
    if (pRtsp) pRtsp.style.display = (type === 'RTSP') ? 'block' : 'none';

    const rtspInput = document.getElementById('formRtspUrl');
    if (type === 'RTSP') {
        const val = (document.getElementById('inputRtsp')?.value || '').trim();
        if (rtspInput) rtspInput.value = val;
    } else if (type === 'NVR') {
        const selCh = document.getElementById('selectNvrChannel');
        if (selCh && selCh.value) {
            applySelectedNvrChannel(selCh.value);
        }
    }
}

export function syncManualUrl(val) {
    const target = document.getElementById('formRtspUrl');
    if (target) target.value = (val || '').trim();
}

export function toggleAdvancedInput() {
    const box = document.getElementById('advancedUrlBox');
    if (box) box.style.display = (box.style.display === 'none') ? 'block' : 'none';
}

export function openModal(camera = null) {
    const formCamId = document.getElementById('formCamId');
    if (formCamId) formCamId.value = camera ? camera.id : '';

    const modalTitle = document.getElementById('modalTitle');
    if (modalTitle) modalTitle.innerText = camera ? `Chỉnh Sửa Camera: ${camera.name}` : 'Thêm Camera Mới';

    const codeInput = document.getElementById('formCode');
    if (codeInput) {
        codeInput.value = camera ? camera.code : '';
        codeInput.disabled = !!camera;
    }

    const formName = document.getElementById('formName');
    if (formName) formName.value = camera ? camera.name : '';

    const formRoom = document.getElementById('formRoom');
    if (formRoom) formRoom.value = camera ? camera.room_number : '';

    const formStd = document.getElementById('formStandard');
    if (formStd) formStd.value = camera ? camera.standard_count : 40;

    const formRelay = document.getElementById('formRelayIp');
    if (formRelay) formRelay.value = camera ? (camera.relay_ip || '') : '';

    const formActive = document.getElementById('formActive');
    if (formActive) formActive.checked = camera ? camera.is_active : true;

    const previewImg = document.getElementById('testPreviewImg');
    if (previewImg) {
        previewImg.style.display = 'none';
        previewImg.src = '';
    }
    const statusMsg = document.getElementById('testStatusMsg');
    if (statusMsg) statusMsg.innerHTML = 'Bấm "Bắt Ảnh Xem Trước" để kiểm tra tín hiệu và thu nhận khung hình thực tế từ nguồn camera trên.';

    const url = camera ? (camera.rtsp_url || '').trim() : '';
    const rInput = document.getElementById('inputRtsp');
    if (rInput) rInput.value = url;
    syncManualUrl(url);

    if (camera) {
        loadNvrDevicesAndChannels(camera.channel_number).then(() => {
            if (camera.channel_number || (url && (url.includes('/Streaming/Channels/') || url.includes('/cam/realmonitor')))) {
                switchSourceTab('NVR');
            } else {
                switchSourceTab('RTSP');
            }
        });
    } else {
        switchSourceTab('NVR');
        loadNvrDevicesAndChannels();
    }

    document.getElementById('cameraModal')?.classList.add('active');
}

export function closeModal() {
    document.getElementById('cameraModal')?.classList.remove('active');
}

export async function editCamera(id) {
    const cam = crudCameras.find(c => c.id === id);
    if (cam) {
        try {
            const raw = await CameraAPI.getRawRtsp(id);
            if (raw && raw.success && typeof raw.rtsp_url === 'string' && raw.rtsp_url !== '') {
                openModal({ ...cam, rtsp_url: raw.rtsp_url });
                return;
            }
        } catch (e) {
            // Dùng URL đã che nếu không lấy được URL raw
        }
        openModal(cam);
    }
}

export async function testCurrentInputSource() {
    const url = document.getElementById('formRtspUrl')?.value.trim();
    if (!url) {
        alert('Vui lòng nhập Đường dẫn nguồn Camera trước khi test!');
        return;
    }

    const btn = document.getElementById('btnTestStream');
    const msg = document.getElementById('testStatusMsg');
    const img = document.getElementById('testPreviewImg');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kết nối...';
    }
    if (msg) msg.innerHTML = '<span style="color: var(--primary);">Đang kiểm tra tín hiệu từ camera...</span>';
    if (img) img.style.display = 'none';

    try {
        const data = await CameraAPI.testConnection(url);
        if (data.success) {
            if (msg) msg.innerHTML = `<span style="color: #10b981; font-weight: 700;"><i class="fa-solid fa-circle-check"></i> ${esc(data.message)}</span>`;
            if (data.preview_url && img) {
                img.src = data.preview_url;
                img.style.display = 'inline-block';
            }
            showToast('Kết nối thành công', 'success');
        } else {
            if (msg) msg.innerHTML = `<span style="color: #ef4444; font-weight: 600;"><i class="fa-solid fa-circle-xmark"></i> ${esc(data.message)}</span>`;
            showToast(data.message || 'Kết nối thất bại', 'error');
        }
    } catch (err) {
        if (msg) msg.innerHTML = `<span style="color: #ef4444;">Lỗi khi gửi yêu cầu kiểm tra: ${esc(err.message || err)}</span>`;
        showToast('Lỗi kết nối kiểm tra camera', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-play"></i> Bắt Ảnh Xem Trước';
        }
    }
}

export async function testCameraIRNow() {
    const url = document.getElementById('formRtspUrl')?.value.trim();
    const relayIp = document.getElementById('formRelayIp')?.value?.trim() || '';
    const camId = document.getElementById('formCamId')?.value;
    const btn = document.getElementById('btnTestCameraIR');
    const msg = document.getElementById('irStatusMsg');

    if (!url && !camId) {
        alert('Vui lòng chọn hoặc nhập nguồn Camera trước khi thử đèn!');
        return;
    }

    const originalText = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang bật đèn...';
    }
    if (msg) msg.innerHTML = '<span style="color: #ef4444; font-weight: 700;"><i class="fa-solid fa-lightbulb"></i> Đang kích hoạt đèn hồng ngoại camera (sáng đỏ 4 giây)...</span>';

    try {
        let res;
        if (camId) {
            res = await CameraAPI.testClassroomIR(camId, 4, 'IR_ON');
        } else {
            res = await CameraAPI.testIRByUrl(url, relayIp);
        }
        
        if (res && res.success) {
            if (msg) {
                msg.innerHTML = `<span style="color: #10b981; font-weight: 700;"><i class="fa-solid fa-circle-check"></i> ${esc(res.message || 'Đèn hồng ngoại đã kích hoạt thành công (tự động tắt sau 4s)!')}</span>`;
            }
            showToast(res.message || 'Đã kích hoạt đèn hồng ngoại camera!', 'success');
        } else {
            const errMsg = (res && res.message) ? res.message : 'Không thể gửi lệnh điều khiển tới camera!';
            if (msg) {
                msg.innerHTML = `<span style="color: #ef4444; font-weight: 700;"><i class="fa-solid fa-triangle-exclamation"></i> ${esc(errMsg)}</span>`;
            }
            showToast(errMsg, 'warning');
        }
    } catch (err) {
        if (msg) msg.innerHTML = `<span style="color: #ef4444;"><i class="fa-solid fa-triangle-exclamation"></i> Lỗi: ${esc(err.message || err)}</span>`;
        showToast('Không thể kích hoạt đèn camera: ' + (err.message || err), 'warning');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}


export async function testCameraDirectly(url, name) {
    const titleEl = document.getElementById('liveViewTitle');
    const subEl = document.getElementById('liveViewSubtitle');
    const imgEl = document.getElementById('liveViewImg');

    if (titleEl) titleEl.innerText = `Xem Thử Trực Tiếp: ${name}`;
    if (subEl) subEl.innerText = `Nguồn: ${url}`;
    if (imgEl) imgEl.src = '';
    document.getElementById('liveViewModal')?.classList.add('active');

    try {
        const data = await CameraAPI.testConnection(url);
        if (data.success && data.preview_url) {
            if (imgEl) imgEl.src = data.preview_url;
            if (subEl) subEl.innerText = `${data.message}`;
            showToast(`Đã lấy khung hình ${name}`, 'success');
        } else {
            alert(`Không thể kết nối camera: ${data.message}`);
            document.getElementById('liveViewModal')?.classList.remove('active');
        }
    } catch (err) {
        alert('Lỗi kết nối kiểm tra camera: ' + (err.message || err));
        document.getElementById('liveViewModal')?.classList.remove('active');
    }
}

export async function saveCamera() {
    const id = document.getElementById('formCamId')?.value;
    const code = document.getElementById('formCode')?.value.trim();
    const name = document.getElementById('formName')?.value.trim();
    const room_number = document.getElementById('formRoom')?.value.trim();
    const standard_count = parseInt(document.getElementById('formStandard')?.value) || 40;
    const rtsp_url = document.getElementById('formRtspUrl')?.value.trim();
    const relay_ip = document.getElementById('formRelayIp')?.value?.trim() || '';
    const is_active = document.getElementById('formActive')?.checked ?? true;

    if (!name || !rtsp_url) {
        alert('Vui lòng nhập đầy đủ Tên lớp và Đường dẫn camera!');
        return;
    }

    try {
        let result;
        if (id) {
            result = await CameraAPI.update(id, {
                name, room_number, standard_count, rtsp_url, relay_ip, is_active
            });
        } else {
            if (!code) {
                alert('Vui lòng nhập Mã lớp!');
                return;
            }
            result = await CameraAPI.create({
                code, name, room_number, standard_count, rtsp_url, relay_ip, is_active
            });
        }

        if (result.success) {
            closeModal();
            if (typeof externalCallbacks.onRefreshCameras === 'function') {
                await externalCallbacks.onRefreshCameras();
            }
            showToast(result.message || 'Lưu thành công', 'success');
        } else {
            alert('Lỗi: ' + (result.detail || result.message || 'Không thể lưu camera.'));
        }
    } catch (err) {
        alert('Lỗi kết nối máy chủ: ' + (err.message || err));
    }
}

export async function deleteCamera(id, name) {
    let confirmed = false;
    if (window.ConfirmationDialog && typeof window.ConfirmationDialog.delete === 'function') {
        confirmed = await window.ConfirmationDialog.delete(name);
    } else {
        confirmed = window.confirm(`Bạn có chắc chắn muốn xóa camera ${name}?`);
    }
    if (!confirmed) return;

    try {
        const result = await CameraAPI.delete(id);
        if (typeof externalCallbacks.onRefreshCameras === 'function') {
            await externalCallbacks.onRefreshCameras();
        }
        showToast(result.message || 'Đã xóa camera thành công', 'success');
    } catch (err) {
        showToast('Lỗi khi xóa camera: ' + (err.message || err), 'danger');
    }
}

export function openDeleteModal() {
    const modal = document.getElementById('deleteCameraModal');
    const selectQuick = document.getElementById('deleteModalSelectQuick');
    const checklist = document.getElementById('deleteModalChecklist');

    if (!modal) return;

    if (selectQuick) {
        selectQuick.innerHTML = '<option value="">-- Bấm vào đây để chọn camera --</option>' +
            crudCameras.map(c => `
                <option value="${c.id}">${esc(c.name)} (${esc(c.room_number || 'Phòng ' + c.id)}) - Mã: ${esc(c.code)}</option>
            `).join('');
    }

    if (checklist) {
        if (!crudCameras || crudCameras.length === 0) {
            checklist.innerHTML = '<div style="text-align: center; color: #94a3b8; padding: 16px; font-size: 0.85rem;"><i class="fa-solid fa-circle-info"></i> Hiện không có camera nào trong danh sách</div>';
        } else {
            checklist.innerHTML = crudCameras.map(c => `
                <label class="delete-cam-item">
                    <input type="checkbox" value="${c.id}" class="cam-del-cb" data-name="${encodeURIComponent(c.name)}">
                    <span style="flex: 1; font-weight: 500;">
                        <strong style="color: #0f172a;">${esc(c.code)}</strong> - ${esc(c.name)} 
                        <span style="color: #64748b; font-size: 0.8rem;">(${esc(c.room_number || '--')})</span>
                    </span>
                    <span class="badge ${c.source_type === 'WEBCAM' ? 'badge-warning' : (c.source_type === 'FILE' ? 'badge-primary' : 'badge-success')}" style="font-size: 0.72rem;">
                        ${c.source_type || 'RTSP'}
                    </span>
                </label>
            `).join('');

            checklist.querySelectorAll('.cam-del-cb').forEach(cb => {
                cb.addEventListener('change', () => {
                    const checked = checklist.querySelectorAll('.cam-del-cb:checked');
                    if (checked.length === 1 && selectQuick) {
                        selectQuick.value = checked[0].value;
                    } else if (selectQuick) {
                        selectQuick.value = '';
                    }
                });
            });
        }
    }

    if (selectQuick) {
        selectQuick.onchange = () => {
            const val = selectQuick.value;
            if (checklist) {
                checklist.querySelectorAll('.cam-del-cb').forEach(cb => {
                    cb.checked = (String(cb.value) === String(val));
                });
            }
        };
    }

    modal.classList.add('active');
}

export function closeDeleteModal() {
    const modal = document.getElementById('deleteCameraModal');
    if (modal) modal.classList.remove('active');
}

export async function confirmBatchDelete() {
    const checklist = document.getElementById('deleteModalChecklist');
    const checkedBoxes = checklist ? Array.from(checklist.querySelectorAll('.cam-del-cb:checked')) : [];

    if (checkedBoxes.length === 0) {
        alert('Vui lòng chọn ít nhất 1 camera bạn muốn xóa.');
        return;
    }

    const count = checkedBoxes.length;
    const names = checkedBoxes.slice(0, 3).map(cb => decodeURIComponent(cb.dataset.name)).join(', ') + (count > 3 ? ` và ${count - 3} camera khác` : '');

    if (!confirm(`Bạn có chắc chắn muốn xóa ${count} camera (${names}) khỏi hệ thống? Dữ liệu vùng của các lớp này cũng sẽ bị xóa.`)) {
        return;
    }

    const btnConfirm = document.getElementById('btnConfirmDeleteBatch');
    if (btnConfirm) {
        btnConfirm.disabled = true;
        btnConfirm.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xóa...';
    }

    let successCount = 0;
    let failCount = 0;

    for (const cb of checkedBoxes) {
        const id = parseInt(cb.value);
        try {
            const res = await CameraAPI.delete(id);
            if (res.success) successCount++;
            else failCount++;
        } catch (err) {
            console.error('Lỗi xóa camera ID', id, err);
            failCount++;
        }
    }

    if (btnConfirm) {
        btnConfirm.disabled = false;
        btnConfirm.innerHTML = '<i class="fa-solid fa-trash-can"></i> Xác Nhận Xóa';
    }

    closeDeleteModal();
    if (typeof externalCallbacks.onRefreshCameras === 'function') {
        await externalCallbacks.onRefreshCameras();
    }

    if (failCount === 0) {
        showToast(`Đã xóa thành công ${successCount} camera đã chọn!`, 'info');
    } else {
        showToast(`Đã xóa ${successCount} camera, thất bại ${failCount} camera.`, 'warning');
    }
}

export async function resetDefaults() {
    if (!confirm('Khôi phục danh sách 30 lớp học chuẩn của trường THPT Điều Cải? Các camera test bạn vừa thêm có thể sẽ bị đặt lại.')) {
        return;
    }

    try {
        const result = await CameraAPI.resetDefaults();
        if (typeof externalCallbacks.onRefreshCameras === 'function') {
            await externalCallbacks.onRefreshCameras();
        }
        showToast(result.message || 'Đã khôi phục mặc định', 'success');
    } catch (err) {
        alert('Lỗi kết nối máy chủ: ' + (err.message || err));
    }
}
