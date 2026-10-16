/**
 * ===================================================================
 * NVR WIZARD MODULE - THPT ĐIỀU CẢI AI CAMERA
 * Quản lý Modal Dò Quét & Nhập Hàng Loạt 30 Kênh Camera NVR (Hikvision/Dahua)
 * ===================================================================
 */

import { CameraAPI, showToast, escapeHtml } from '../../api.js';

const esc = (v) => escapeHtml(v);

let probedChannels = [];

export function openNvrModal() {
    const modal = document.getElementById('nvrModal');
    if (!modal) {
        console.error('Không tìm thấy element #nvrModal');
        return;
    }
    const probeResults = document.getElementById('nvrProbeResults');
    if (probeResults) probeResults.style.display = 'none';
    const probeLoading = document.getElementById('nvrProbeLoading');
    if (probeLoading) probeLoading.style.display = 'none';
    const btnSave = document.getElementById('btnSaveNvrImport');
    if (btnSave) btnSave.disabled = true;
    modal.classList.add('active');
}

export function closeNvrModal() {
    const modal = document.getElementById('nvrModal');
    if (modal) modal.classList.remove('active');
}

export function fillSchoolPreset() {
    const ip = document.getElementById('nvrIp');
    const port = document.getElementById('nvrPort');
    const user = document.getElementById('nvrUsername');
    const pass = document.getElementById('nvrPassword');
    const brand = document.getElementById('nvrBrand');
    const chCount = document.getElementById('nvrChannelsCount');
    const naming = document.getElementById('nvrNamingMode');

    if (ip) ip.value = '192.168.1.200';
    if (port) port.value = '554';
    if (user) user.value = 'admin';
    if (pass) pass.value = 'Lhu@2025';
    if (brand) brand.value = 'HIKVISION';
    if (chCount) chCount.value = '30';
    if (naming) naming.value = 'DEFAULT_30_CLASSES';

    const patternBox = document.getElementById('nvrCustomPatternBox');
    if (patternBox) patternBox.style.display = 'none';
    showToast('Đã điền cấu hình chuẩn Hikvision THPT Điều Cải (192.168.1.200)!', 'info');
}

export async function probeNVRChannels() {
    const ip_address = document.getElementById('nvrIp')?.value.trim();
    const rtsp_port = parseInt(document.getElementById('nvrPort')?.value) || 554;
    const username = document.getElementById('nvrUsername')?.value.trim() || 'admin';
    const password = document.getElementById('nvrPassword')?.value.trim() || '';
    const brand = document.getElementById('nvrBrand')?.value || 'HIKVISION';
    const start_channel = parseInt(document.getElementById('nvrStartChannel')?.value) || 1;
    const channels_count = parseInt(document.getElementById('nvrChannelsCount')?.value) || 30;
    const naming_mode = document.getElementById('nvrNamingMode')?.value || 'DEFAULT_30_CLASSES';
    const custom_pattern = document.getElementById('nvrCustomPattern')?.value.trim() || '';

    if (!ip_address) {
        alert('Vui lòng nhập địa chỉ IP đầu ghi NVR!');
        return;
    }

    const loadingEl = document.getElementById('nvrProbeLoading');
    const resultsEl = document.getElementById('nvrProbeResults');
    const btnProbe = document.getElementById('btnProbeNVR');
    const btnSave = document.getElementById('btnSaveNvrImport');

    if (loadingEl) loadingEl.style.display = 'block';
    if (resultsEl) resultsEl.style.display = 'none';
    if (btnProbe) {
        btnProbe.disabled = true;
        btnProbe.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang quét...';
    }

    try {
        const payload = {
            ip_address,
            rtsp_port,
            username,
            password,
            brand,
            channels_count,
            start_channel,
            naming_mode,
            custom_pattern
        };

        const res = await CameraAPI.probeNVR(payload);
        if (!res.success) {
            throw new Error(res.message || 'Quét NVR không thành công');
        }

        probedChannels = res.channels || [];
        renderNvrPreviewCards(probedChannels, res.online_channels);

        const summaryEl = document.getElementById('nvrProbeSummary');
        if (summaryEl) {
            summaryEl.innerText = `${res.online_channels}/${res.total_channels} Kênh Online (${res.elapsed_seconds}s)`;
            if (res.online_channels === 0) {
                summaryEl.className = 'status-pill status-pill-danger';
                summaryEl.style.background = '#fef2f2';
                summaryEl.style.color = '#dc2626';
            } else {
                summaryEl.className = 'status-pill status-pill-success';
                summaryEl.style.background = '';
                summaryEl.style.color = '';
            }
        }

        if (resultsEl) resultsEl.style.display = 'block';
        if (btnSave) btnSave.disabled = false;

        if (res.online_channels === 0) {
            showToast('⚠️ Không kết nối được kênh nào từ đầu ghi! Đang hiển thị ảnh mô phỏng. Vui lòng kiểm tra dây mạng LAN và mật khẩu.', 'warning');
        } else {
            showToast(`Quét thành công ${res.online_channels}/${probedChannels.length} kênh camera trực tiếp!`, 'success');
        }
    } catch (err) {
        console.error('Lỗi khi thăm dò đầu ghi:', err);
        alert('Lỗi quét đầu ghi NVR: ' + (err.message || err));
    } finally {
        if (loadingEl) loadingEl.style.display = 'none';
        if (btnProbe) {
            btnProbe.disabled = false;
            btnProbe.innerHTML = 'Quét kênh camera';
        }
    }
}

export function renderNvrPreviewCards(channels, onlineCount = 0) {
    const container = document.getElementById('nvrChannelList');
    if (!container) return;
    container.innerHTML = '';

    if (onlineCount === 0) {
        const alertBox = document.createElement('div');
        alertBox.style.cssText = 'grid-column: 1 / -1; background: #fffbeb; border: 1.5px solid #fde68a; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; font-size: 0.85rem; color: #92400e; display: flex; align-items: flex-start; gap: 10px;';
        alertBox.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation" style="font-size: 1.2rem; margin-top: 2px; color: #d97706;"></i>
            <div>
                <strong>Chưa nhận được tín hiệu hình ảnh trực tiếp từ đầu ghi (0/30 kênh online):</strong>
                <ul style="margin: 4px 0 0 18px; padding: 0; line-height: 1.45;">
                    <li>Máy tính cần cắm dây mạng LAN của trường (cùng dải mạng <code>192.168.1.x</code> với đầu ghi).</li>
                    <li>Đảm bảo chọn đúng Hãng Đầu Ghi: <strong>Hikvision / Ezviz</strong>.</li>
                    <li>Kiểm tra chính xác Mật khẩu tài khoản admin của đầu ghi Hikvision.</li>
                    <li><em>Các hình ảnh bên dưới hiện tại là ảnh mô phỏng (dự phòng). Khi kết nối thành công, hệ thống sẽ hiện ảnh camera thật từ các phòng học.</em></li>
                </ul>
            </div>
        `;
        container.appendChild(alertBox);
    }

    channels.forEach((ch) => {
        const card = document.createElement('div');
        card.className = `nvr-ch-card ${ch.is_selected ? 'selected' : ''}`;
        card.id = `nvr_preview_card_${ch.channel}`;

        const isLive = ch.is_online === true;
        const liveBadge = isLive
            ? `<span style="position: absolute; top: 4px; left: 4px; background: rgba(16, 185, 129, 0.95); color: #fff; font-size: 0.65rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; z-index: 2;"><i class="fa-solid fa-circle" style="font-size: 6px; vertical-align: middle;"></i> LIVE</span>`
            : `<span style="position: absolute; top: 4px; left: 4px; background: rgba(220, 38, 38, 0.9); color: #fff; font-size: 0.62rem; font-weight: 600; padding: 2px 5px; border-radius: 4px; z-index: 2;"><i class="fa-solid fa-image"></i> ẢNH MẪU</span>`;

        const thumbHtml = ch.thumbnail
            ? `<img src="${ch.thumbnail}" alt="CH${ch.channel}">`
            : `<div style="text-align: center; color: #64748b; line-height: 65px;"><i class="fa-solid fa-video"></i></div>`;

        card.innerHTML = `
            <div style="display: flex; align-items: center;">
                <input type="checkbox" class="nvr-ch-select" data-ch="${ch.channel}" ${ch.is_selected ? 'checked' : ''} style="width: 17px; height: 17px; cursor: pointer;">
            </div>
            <div class="nvr-ch-thumb" style="position: relative;">
                ${liveBadge}
                ${thumbHtml}
                <span class="nvr-ch-badge">CH${String(ch.channel).padStart(2, '0')}</span>
            </div>
            <div class="nvr-ch-fields">
                <input type="text" class="nvr-ch-name" data-ch="${ch.channel}" value="${esc(ch.name)}" placeholder="Tên lớp (VD: Lớp 10A1)" title="Tên lớp học">
                <div style="display: flex; gap: 6px;">
                    <input type="text" class="nvr-ch-room" data-ch="${ch.channel}" value="${esc(ch.room_number || '')}" placeholder="Phòng" style="width: 55%;" title="Số phòng học">
                    <input type="number" class="nvr-ch-std" data-ch="${ch.channel}" value="${ch.standard_count || 40}" min="1" max="60" style="width: 45%; font-weight: 700;" title="Sĩ số chuẩn">
                </div>
            </div>
        `;
        container.appendChild(card);
    });

    container.querySelectorAll('.nvr-ch-select').forEach(cb => {
        cb.addEventListener('change', () => {
            const ch = cb.getAttribute('data-ch');
            const card = document.getElementById(`nvr_preview_card_${ch}`);
            if (card) {
                if (cb.checked) card.classList.add('selected');
                else card.classList.remove('selected');
            }
        });
    });
}

export function toggleAllNvrChannels(isSelected) {
    const container = document.getElementById('nvrChannelList');
    if (!container) return;
    container.querySelectorAll('.nvr-ch-select').forEach(cb => {
        cb.checked = isSelected;
        const ch = cb.getAttribute('data-ch');
        const card = document.getElementById(`nvr_preview_card_${ch}`);
        if (card) {
            if (isSelected) card.classList.add('selected');
            else card.classList.remove('selected');
        }
    });
}

export async function saveNvrImport(onSuccessCallback = null) {
    const container = document.getElementById('nvrChannelList');
    if (!container || probedChannels.length === 0) return;

    const selectedChannels = [];
    probedChannels.forEach(ch => {
        const chNum = ch.channel;
        const cb = container.querySelector(`.nvr-ch-select[data-ch="${chNum}"]`);
        if (cb && cb.checked) {
            const nameInput = container.querySelector(`.nvr-ch-name[data-ch="${chNum}"]`);
            const roomInput = container.querySelector(`.nvr-ch-room[data-ch="${chNum}"]`);
            const stdInput = container.querySelector(`.nvr-ch-std[data-ch="${chNum}"]`);

            selectedChannels.push({
                channel: ch.channel,
                code: ch.code,
                name: nameInput ? nameInput.value.trim() : ch.name,
                room_number: roomInput ? roomInput.value.trim() : ch.room_number,
                standard_count: stdInput ? parseInt(stdInput.value) || 40 : ch.standard_count,
                rtsp_url: ch.rtsp_url,
                thumbnail: ch.thumbnail || '',
                is_selected: true
            });
        }
    });

    if (selectedChannels.length === 0) {
        alert('Vui lòng chọn ít nhất một kênh camera để lưu!');
        return;
    }

    const btnSave = document.getElementById('btnSaveNvrImport');
    if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
    }

    try {
        const payload = {
            ip_address: document.getElementById('nvrIp')?.value.trim() || '192.168.1.200',
            rtsp_port: parseInt(document.getElementById('nvrPort')?.value) || 554,
            username: document.getElementById('nvrUsername')?.value.trim() || 'admin',
            password: document.getElementById('nvrPassword')?.value.trim() || '',
            brand: document.getElementById('nvrBrand')?.value || 'HIKVISION',
            channels_count: parseInt(document.getElementById('nvrChannelsCount')?.value) || 30,
            start_channel: parseInt(document.getElementById('nvrStartChannel')?.value) || 1,
            channels: selectedChannels
        };

        const res = await CameraAPI.batchImportNVR(payload);
        if (res.success) {
            showToast(`Đã nhập thành công ${res.imported_count || selectedChannels.length} camera vào CSDL!`, 'success');
            closeNvrModal();
            if (onSuccessCallback) onSuccessCallback();
        } else {
            alert('Lỗi nhập camera: ' + (res.message || 'Không xác định'));
        }
    } catch (err) {
        console.error('Lỗi khi lưu NVR batch:', err);
        alert('Lỗi khi lưu danh sách camera: ' + (err.message || err));
    } finally {
        if (btnSave) {
            btnSave.disabled = false;
            btnSave.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu trữ';
        }
    }
}

export function initNvrWizardEvents(onSaved = null) {
    const btnOpenNvr = document.getElementById('btnAddNVR');
    if (btnOpenNvr) btnOpenNvr.addEventListener('click', openNvrModal);

    const btnCloseNvr = document.getElementById('nvrModalCloseBtn');
    if (btnCloseNvr) btnCloseNvr.addEventListener('click', closeNvrModal);

    const btnCancelNvr = document.getElementById('btnCancelNvrModal');
    if (btnCancelNvr) btnCancelNvr.addEventListener('click', closeNvrModal);

    const btnFillPreset = document.getElementById('btnFillSchoolPreset');
    if (btnFillPreset) btnFillPreset.addEventListener('click', fillSchoolPreset);

    const selectBrand = document.getElementById('nvrBrand');
    if (selectBrand) {
        selectBrand.addEventListener('change', () => {
            const patternBox = document.getElementById('nvrCustomPatternBox');
            if (patternBox) {
                patternBox.style.display = (selectBrand.value === 'CUSTOM') ? 'block' : 'none';
            }
        });
    }

    const btnProbe = document.getElementById('btnProbeNVR');
    if (btnProbe) btnProbe.addEventListener('click', probeNVRChannels);

    const btnSelectAll = document.getElementById('btnSelectAllNvr');
    if (btnSelectAll) btnSelectAll.addEventListener('click', () => toggleAllNvrChannels(true));

    const btnUnselectAll = document.getElementById('btnUnselectAllNvr');
    if (btnUnselectAll) btnUnselectAll.addEventListener('click', () => toggleAllNvrChannels(false));

    const btnSaveNvr = document.getElementById('btnSaveNvrImport');
    if (btnSaveNvr) btnSaveNvr.addEventListener('click', () => saveNvrImport(onSaved));
}
