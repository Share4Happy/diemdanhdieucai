import { AttendanceAPI, getMediaUrl, showToast, API_BASE } from './api.js';

let currentDetails = [];
let currentFilter = 'all';

let currentClassInfo = {
    classId: null,
    name: '',
    room: '',
    rawPath: '',
    annPath: '',
    standard: 40,
    present: 0,
    absent: 0
};

let lbZoom = {
    scale: 1,
    panX: 0,
    panY: 0,
    isDragging: false,
    startX: 0,
    startY: 0,
    currentType: 'annotated'
};

export async function loadLatestAttendance() {
    try {
        const data = await AttendanceAPI.getLatest();
        if (!data || !data.session) {
            document.getElementById('sessionTitle').innerText = 'Chưa có dữ liệu điểm danh';
            document.getElementById('sessionSubtitle').innerText = 'Bấm nút "Quét Điểm Danh" để bắt đầu quét dữ liệu mới.';
            document.getElementById('kpiClasses').innerText = '0';
            document.getElementById('kpiStandard').innerText = '0';
            document.getElementById('kpiPresent').innerText = '0';
            document.getElementById('kpiAbsent').innerText = '0';
            document.getElementById('kpiRate').innerText = '0%';
            currentDetails = [];
            renderClassGrid();
            return;
        }

        const s = data.session;
        currentDetails = data.details || [];

        document.getElementById('sessionTitle').innerText = `Phiên: ${s.session_code || ''} (${s.scan_date || ''} - ${s.scan_time || ''})`;
        document.getElementById('sessionSubtitle').innerText = `Trạng thái: ${s.status === 'COMPLETED' ? 'Đã hoàn tất điểm danh AI' : s.status}`;

        document.getElementById('kpiClasses').innerText = s.total_classes || 0;
        document.getElementById('kpiStandard').innerText = s.total_standard || 0;
        document.getElementById('kpiPresent').innerText = s.total_present || 0;
        document.getElementById('kpiAbsent').innerText = s.total_absent || 0;

        const rate = s.total_standard > 0 ? ((s.total_present / s.total_standard) * 100).toFixed(1) : 0;
        document.getElementById('kpiRate').innerText = `${rate}%`;

        // Cập nhật link tải excel
        const btnDownload = document.getElementById('btnDownloadExcel');
        if (btnDownload) {
            btnDownload.href = AttendanceAPI.getDownloadExcelUrl();
        }

        renderClassGrid();
    } catch (err) {
        console.error("Lỗi nạp dữ liệu:", err);
        showToast("Không thể tải kết quả điểm danh: " + err.message, "danger");
    }
}

export function renderClassGrid() {
    const container = document.getElementById('classroomsGrid');
    const searchVal = document.getElementById('searchInput').value.toLowerCase().trim();

    const filtered = currentDetails.filter(d => {
        const matchSearch = d.class_name.toLowerCase().includes(searchVal) || (d.room_number || '').toLowerCase().includes(searchVal);
        if (!matchSearch) return false;

        if (currentFilter === 'full') return d.absent_count === 0;
        if (currentFilter === 'absent') return d.absent_count > 0;
        return true;
    });

    if (filtered.length === 0) {
        container.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: var(--text-muted);">Không tìm thấy lớp học nào khớp với bộ lọc.</div>`;
        return;
    }

    container.innerHTML = filtered.map((d, index) => {
        const isFull = d.absent_count === 0;
        const badgeClass = isFull ? 'badge-success' : (d.absent_count <= 2 ? 'badge-warning' : 'badge-danger');
        const badgeText = isFull ? 'Đủ Sĩ Số' : `Vắng ${d.absent_count} Em`;
        const thumbUrl = getMediaUrl(d.annotated_image_path || d.raw_image_path) || '/dataset/samples/classroom_sample_1.jpg';

        return `
            <div class="class-card">
                <div class="card-header">
                    <div class="class-title">
                        <h3>${d.class_name}</h3>
                        <span>${d.room_number || 'Phòng học'}</span>
                    </div>
                    <span class="badge ${badgeClass}">${badgeText}</span>
                </div>
                <div class="card-body">
                    <div class="stats-row">
                        <div class="stat-item">
                            <div class="stat-label">Sĩ số</div>
                            <div class="stat-num">${d.standard_count}</div>
                        </div>
                        <div class="stat-item present">
                            <div class="stat-label">Có mặt</div>
                            <div class="stat-num">${d.present_count}</div>
                        </div>
                        <div class="stat-item absent">
                            <div class="stat-label">Vắng</div>
                            <div class="stat-num">${d.absent_count}</div>
                        </div>
                    </div>
                    <div class="card-thumb-container" data-index="${index}">
                        <img src="${thumbUrl}" alt="${d.class_name}" onerror="this.src='/dataset/samples/classroom_sample_1.jpg'">
                        <div class="card-thumb-overlay"><i class="fa-solid fa-magnifying-glass-plus"></i> &nbsp;Bấm để xem ảnh đối chứng</div>
                    </div>
                </div>
                <div class="card-footer">
                    <span style="font-size: 0.78rem; color: var(--text-muted);"><i class="fa-solid fa-circle-check" style="color: var(--success);"></i> ${d.notes || 'Khớp nhận diện'}</span>
                    <a class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;" href="roi-config.html?class_id=${d.classroom_id}">Cấu hình ROI</a>
                </div>
            </div>
        `;
    }).join('');

    // Gắn sự kiện click cho các thumbnail lớp
    container.querySelectorAll('.card-thumb-container').forEach(el => {
        el.addEventListener('click', () => {
            const idx = el.getAttribute('data-index');
            const d = filtered[idx];
            if (d) {
                openModal(d.class_name, d.room_number, d.raw_image_path, d.annotated_image_path, d.standard_count, d.present_count, d.absent_count, d.classroom_id);
            }
        });
    });
}

export function openModal(name, room, rawPath, annPath, std, pres, abs, classId = null) {
    let resolvedRaw = getMediaUrl(rawPath) || '/dataset/samples/classroom_sample_1.jpg';
    let resolvedAnn = getMediaUrl(annPath) || getMediaUrl(rawPath) || '/dataset/samples/classroom_sample_1.jpg';
    
    // Đảm bảo luôn có tham số chống cache ảnh mới nhất
    if (!resolvedAnn.includes('?t=') && !resolvedAnn.includes('&t=')) {
        resolvedAnn += (resolvedAnn.includes('?') ? '&' : '?') + 't=' + Date.now();
    }

    currentClassInfo = {
        classId: classId,
        name, room,
        rawPath: resolvedRaw,
        annPath: resolvedAnn,
        standard: std,
        present: pres,
        absent: abs
    };

    document.getElementById('modalClassTitle').innerText = `${name} (${room || 'Phòng học'})`;
    document.getElementById('modalClassSub').innerText = `Sĩ số chuẩn: ${std} | Hiện diện: ${pres} | Vắng mặt: ${abs} học sinh`;
    document.getElementById('modalRawImg').src = currentClassInfo.rawPath;
    document.getElementById('modalAnnotatedImg').src = currentClassInfo.annPath;

    const btnEditRoi = document.getElementById('modalBtnEditRoi');
    if (btnEditRoi && classId) {
        btnEditRoi.href = `roi-config.html?class_id=${classId}`;
    }

    document.getElementById('imageModal').classList.add('active');
}

export function openLightbox(type = 'annotated') {
    lbZoom.currentType = type;
    const titleEl = document.getElementById('lbClassTitle');
    const badgeEl = document.getElementById('lbClassBadge');

    const isAnn = type === 'annotated';
    titleEl.innerHTML = `<i class="fa-solid ${isAnn ? 'fa-brain' : 'fa-camera'}" style="color: ${isAnn ? '#60a5fa' : '#34d399'};"></i> ${currentClassInfo.name} (${currentClassInfo.room}) - ${isAnn ? 'Soi Chi Tiết Tracking AI' : 'Xem Ảnh Gốc Camera'}`;
    badgeEl.innerText = `Sĩ số: ${currentClassInfo.standard} | Hiện diện: ${currentClassInfo.present} em | Vắng: ${currentClassInfo.absent} em`;

    updateLightboxTabs(type);
    const imgEl = document.getElementById('lightboxImg');
    imgEl.src = isAnn ? currentClassInfo.annPath : currentClassInfo.rawPath;

    resetZoom();
    document.getElementById('lightboxModal').classList.add('active');
}

export function closeLightbox() {
    document.getElementById('lightboxModal').classList.remove('active');
}

export function switchLightboxTab(type) {
    lbZoom.currentType = type;
    updateLightboxTabs(type);

    const isAnn = type === 'annotated';
    const imgEl = document.getElementById('lightboxImg');
    imgEl.src = isAnn ? currentClassInfo.annPath : currentClassInfo.rawPath;

    const titleEl = document.getElementById('lbClassTitle');
    titleEl.innerHTML = `<i class="fa-solid ${isAnn ? 'fa-brain' : 'fa-camera'}" style="color: ${isAnn ? '#60a5fa' : '#34d399'};"></i> ${currentClassInfo.name} (${currentClassInfo.room}) - ${isAnn ? 'Soi Chi Tiết Tracking AI' : 'Xem Ảnh Gốc Camera'}`;
}

function updateLightboxTabs(type) {
    document.getElementById('lbTabAnnotated').classList.toggle('active', type === 'annotated');
    document.getElementById('lbTabRaw').classList.toggle('active', type === 'raw');
}

export function zoomImage(delta) {
    const newScale = Math.min(Math.max(0.6, lbZoom.scale + delta), 5.0);
    lbZoom.scale = newScale;
    updateCanvasTransform();
}

export function resetZoom() {
    lbZoom.scale = 1.0;
    lbZoom.panX = 0;
    lbZoom.panY = 0;
    updateCanvasTransform();
}

function updateCanvasTransform() {
    const container = document.getElementById('lightboxCanvasContainer');
    if (container) {
        container.style.transform = `translate(${lbZoom.panX}px, ${lbZoom.panY}px) scale(${lbZoom.scale})`;
    }
    const badge = document.getElementById('lbZoomLevel');
    if (badge) {
        badge.innerText = `${Math.round(lbZoom.scale * 100)}%`;
    }
}

// === KHỞI TẠO EVENT LISTENERS ===
document.addEventListener('DOMContentLoaded', () => {
    loadLatestAttendance();

    // Nút đóng modal so sánh
    const modalClose = document.getElementById('modalClose');
    if (modalClose) {
        modalClose.addEventListener('click', () => {
            document.getElementById('imageModal').classList.remove('active');
        });
    }

    const imageModal = document.getElementById('imageModal');
    if (imageModal) {
        imageModal.addEventListener('click', (e) => {
            if (e.target === imageModal) {
                imageModal.classList.remove('active');
            }
        });
    }

    // Các nút bấm trong modal so sánh để mở Lightbox
    const btnOpenLbRaw = document.getElementById('btnOpenLightboxRaw');
    if (btnOpenLbRaw) {
        btnOpenLbRaw.addEventListener('click', () => openLightbox('raw'));
    }

    const btnOpenLbAnn = document.getElementById('btnOpenLightboxAnnotated');
    if (btnOpenLbAnn) {
        btnOpenLbAnn.addEventListener('click', () => openLightbox('annotated'));
    }

    // Lightbox Controls
    const btnLbClose = document.getElementById('btnLightboxClose');
    if (btnLbClose) btnLbClose.addEventListener('click', closeLightbox);

    const btnZoomIn = document.getElementById('btnZoomIn');
    if (btnZoomIn) btnZoomIn.addEventListener('click', () => zoomImage(0.25));

    const btnZoomOut = document.getElementById('btnZoomOut');
    if (btnZoomOut) btnZoomOut.addEventListener('click', () => zoomImage(-0.25));

    const btnZoomReset = document.getElementById('btnZoomReset');
    if (btnZoomReset) btnZoomReset.addEventListener('click', resetZoom);

    const tabAnn = document.getElementById('lbTabAnnotated');
    if (tabAnn) tabAnn.addEventListener('click', () => switchLightboxTab('annotated'));

    const tabRaw = document.getElementById('lbTabRaw');
    if (tabRaw) tabRaw.addEventListener('click', () => switchLightboxTab('raw'));

    // Lightbox Pan & Zoom tương tác chuột
    const viewport = document.getElementById('lightboxViewport');
    if (viewport) {
        viewport.addEventListener('mousedown', (e) => {
            if (e.target.closest('.lightbox-tools') || e.target.closest('.lightbox-switch-tabs')) return;
            lbZoom.isDragging = true;
            lbZoom.startX = e.clientX - lbZoom.panX;
            lbZoom.startY = e.clientY - lbZoom.panY;
        });

        window.addEventListener('mousemove', (e) => {
            if (!lbZoom.isDragging) return;
            lbZoom.panX = e.clientX - lbZoom.startX;
            lbZoom.panY = e.clientY - lbZoom.startY;
            updateCanvasTransform();
        });

        window.addEventListener('mouseup', () => {
            lbZoom.isDragging = false;
        });

        viewport.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY < 0 ? 0.20 : -0.20;
            zoomImage(delta);
        }, { passive: false });

        viewport.addEventListener('dblclick', () => {
            if (lbZoom.scale > 1.2) {
                resetZoom();
            } else {
                lbZoom.scale = 2.0;
                updateCanvasTransform();
            }
        });
    }

    // Phím tắt bàn phím
    window.addEventListener('keydown', (e) => {
        const lb = document.getElementById('lightboxModal');
        if (!lb || !lb.classList.contains('active')) {
            if (e.key === 'Escape') {
                const im = document.getElementById('imageModal');
                if (im) im.classList.remove('active');
            }
            return;
        }

        if (e.key === 'Escape') {
            closeLightbox();
        } else if (e.key === '+' || e.key === '=') {
            zoomImage(0.25);
        } else if (e.key === '-' || e.key === '_') {
            zoomImage(-0.25);
        } else if (e.key === '0') {
            resetZoom();
        } else if (e.key === ' ' || e.key === 'Tab') {
            e.preventDefault();
            switchLightboxTab(lbZoom.currentType === 'annotated' ? 'raw' : 'annotated');
        }
    });

    // Nút bấm Quét Điểm Danh Ngay
    const btnTrigger = document.getElementById('btnTriggerScan');
    if (btnTrigger) {
        btnTrigger.addEventListener('click', async () => {
            btnTrigger.disabled = true;
            btnTrigger.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang quét 30 camera...';

            try {
                const result = await AttendanceAPI.triggerScan();
                if (result.success) {
                    showToast('✓ Hoàn thành quét điểm danh cho 30 lớp học! Đã tự động xuất file Excel.', 'success');
                    await loadLatestAttendance();
                } else {
                    showToast('Có lỗi xảy ra: ' + (result.error || 'Lỗi quét'), 'danger');
                }
            } catch (err) {
                showToast('Lỗi kết nối máy chủ: ' + err.message, 'danger');
            } finally {
                btnTrigger.disabled = false;
                btnTrigger.innerHTML = '<i class="fa-solid fa-bolt"></i> Quét Điểm Danh';
            }
        });
    }

    // Nút bấm Quét Lại Lớp Này trong Modal
    const btnModalRescan = document.getElementById('modalBtnRescan');
    if (btnModalRescan) {
        btnModalRescan.addEventListener('click', async () => {
            if (!currentClassInfo.classId) return;
            const originalHtml = btnModalRescan.innerHTML;
            btnModalRescan.disabled = true;
            btnModalRescan.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang phân tích...';

            try {
                const endpoint = (API_BASE ? API_BASE : '') + `/api/roi/${currentClassInfo.classId}/rescan`;
                const res = await fetch(endpoint, { method: 'POST' });
                const data = await res.json();
                if (res.ok && data.success) {
                    showToast(`✓ Đã nhận diện lại lớp ${currentClassInfo.name}! Hiện diện: ${data.present_count} HS, Vắng: ${data.absent_count} HS.`, 'success');
                    currentClassInfo.present = data.present_count;
                    currentClassInfo.absent = data.absent_count;
                    if (data.annotated_url) {
                        currentClassInfo.annPath = getMediaUrl(data.annotated_url);
                        document.getElementById('modalAnnotatedImg').src = currentClassInfo.annPath;
                    }
                    document.getElementById('modalClassSub').innerText = `Sĩ số chuẩn: ${data.standard_count || currentClassInfo.standard} | Hiện diện: ${data.present_count} | Vắng mặt: ${data.absent_count} học sinh`;
                    loadLatestAttendance();
                } else {
                    showToast('Lỗi: ' + (data.detail || data.message || 'Không thể quét lại'), 'danger');
                }
            } catch (err) {
                showToast('Lỗi kết nối máy chủ: ' + err.message, 'danger');
            } finally {
                btnModalRescan.disabled = false;
                btnModalRescan.innerHTML = originalHtml;
            }
        });
    }

    // Filter pills
    document.querySelectorAll('.filter-pill').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentFilter = e.target.dataset.filter;
            renderClassGrid();
        });
    });

    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', renderClassGrid);
    }
});
