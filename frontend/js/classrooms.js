/**
 * CLASSROOMS MANAGEMENT CONTROLLER - THPT ĐIỀU CẢI
 * Xử lý dữ liệu danh mục 30 lớp học, sĩ số chuẩn và liên kết camera
 */

// Danh sách giáo viên chủ nhiệm mẫu chuẩn của THPT Điều Cải
const DEFAULT_TEACHERS = {
    '10A1': 'Cô Nguyễn Thị Hoa', '10A2': 'Thầy Trần Văn Minh', '10A3': 'Cô Lê Thị Mai', '10A4': 'Thầy Phạm Đức Hải',
    '10A5': 'Cô Hoàng Thu Thủy', '10A6': 'Thầy Vũ Đình Nam', '10A7': 'Cô Đỗ Thanh Hương', '10A8': 'Thầy Bùi Quốc Bảo',
    '10A9': 'Cô Ngô Phương Thảo', '10A10': 'Thầy Đinh Quang Huy',
    '11A1': 'Cô Phan Thu Trang', '11A2': 'Thầy Nguyễn Trọng Tấn', '11A3': 'Cô Vũ Bích Ngọc', '11A4': 'Thầy Đặng Thành Nam',
    '11A5': 'Cô Trịnh Lan Anh', '11A6': 'Thầy Lê Hoàng Long', '11A7': 'Cô Mai Kiều Trang', '11A8': 'Thầy Hồ Anh Tuấn',
    '11A9': 'Cô Nguyễn Kiều Oanh', '11A10': 'Thầy Cao Văn Sơn',
    '12A1': 'Thầy Trương Văn Dũng', '12A2': 'Cô Đào Thị Bích', '12A3': 'Thầy Nguyễn Thế Anh', '12A4': 'Cô Phạm Thị Nga',
    '12A5': 'Thầy Lương Tuấn Kiệt', '12A6': 'Cô Hoàng Yến Nhi', '12A7': 'Thầy Đỗ Minh Quân', '12A8': 'Cô Tạ Thu Hằng',
    '12A9': 'Thầy Chu Văn Phúc', '12A10': 'Cô Nguyễn Bích Liên'
};

class ClassroomsManager {
    constructor() {
        this.classrooms = [];
        this.attendanceMap = {};
        this.currentFilter = 'ALL';
        this.searchQuery = '';
        this.teachersData = JSON.parse(localStorage.getItem('dieucai_teachers_map') || '{}');

        // Gộp với danh sách mặc định nếu chưa có
        for (const [k, v] of Object.entries(DEFAULT_TEACHERS)) {
            if (!this.teachersData[k]) {
                this.teachersData[k] = v;
            }
        }

        this.init();
    }

    async init() {
        this.bindEvents();
        await this.loadData();
    }

    bindEvents() {
        // Lọc theo khối
        document.querySelectorAll('.grade-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.grade-tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentFilter = btn.dataset.grade;
                this.renderTable();
            });
        });

        // Tìm kiếm
        const searchInput = document.getElementById('classSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value.trim().toLowerCase();
                this.renderTable();
            });
        }

        // Nút làm mới
        const btnRefresh = document.getElementById('btnRefreshList');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', () => this.loadData());
        }

        // Nút thêm lớp mới
        const btnAdd = document.getElementById('btnAddClassroom');
        if (btnAdd) {
            btnAdd.addEventListener('click', () => this.openAddModal());
        }

        // Nút sĩ số hàng loạt
        const btnBatch = document.getElementById('btnBatchStandard');
        if (btnBatch) {
            btnBatch.addEventListener('click', () => this.openBatchModal());
        }

        // Đóng modals
        const btnCloseClassModal = document.getElementById('classModalCloseBtn');
        const btnCancelClassModal = document.getElementById('btnCancelClassModal');
        if (btnCloseClassModal) btnCloseClassModal.addEventListener('click', () => this.closeClassModal());
        if (btnCancelClassModal) btnCancelClassModal.addEventListener('click', () => this.closeClassModal());

        const btnCloseBatchModal = document.getElementById('batchModalCloseBtn');
        const btnCancelBatchModal = document.getElementById('btnCancelBatchModal');
        if (btnCloseBatchModal) btnCloseBatchModal.addEventListener('click', () => this.closeBatchModal());
        if (btnCancelBatchModal) btnCancelBatchModal.addEventListener('click', () => this.closeBatchModal());

        // Lưu thông tin lớp
        const btnSaveClass = document.getElementById('btnSaveClassroom');
        if (btnSaveClass) {
            btnSaveClass.addEventListener('click', () => this.saveClassroom());
        }

        // Áp dụng sĩ số chuẩn hàng loạt
        const btnApplyBatch = document.getElementById('btnApplyBatchStandard');
        if (btnApplyBatch) {
            btnApplyBatch.addEventListener('click', () => this.applyBatchStandard());
        }
    }

    async loadData() {
        try {
            const token = localStorage.getItem('access_token');
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            // 1. Tải danh sách camera/lớp
            const camRes = await fetch('/api/cameras', { headers });
            if (camRes.ok) {
                const data = await camRes.json();
                this.classrooms = data.cameras || [];
            }

            // 2. Tải điểm danh gần nhất
            try {
                const attRes = await fetch('/api/attendance/latest', { headers });
                if (attRes.ok) {
                    const attData = await attRes.json();
                    if (attData.details) {
                        attData.details.forEach(d => {
                            this.attendanceMap[d.classroom_id] = d;
                        });
                    }
                }
            } catch (err) {
                console.warn('Chưa có dữ liệu điểm danh hôm nay:', err);
            }

            this.updateKPIs();
            this.renderTable();
        } catch (error) {
            console.error('Lỗi khi tải dữ liệu lớp học:', error);
            const tbody = document.getElementById('classroomsTableBody');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" style="text-align: center; padding: 2rem; color: #ef4444;">
                            <i class="fa-solid fa-triangle-exclamation" style="font-size: 1.5rem; margin-bottom: 6px; display: block;"></i>
                            Không thể tải danh sách lớp học. Vui lòng kiểm tra kết nối mạng hoặc phiên đăng nhập.
                        </td>
                    </tr>
                `;
            }
        }
    }

    getGradeOfClass(name, code) {
        const text = `${name} ${code}`.toUpperCase();
        if (text.includes('10')) return '10';
        if (text.includes('11')) return '11';
        if (text.includes('12')) return '12';
        return '10';
    }

    updateKPIs() {
        const totalClasses = this.classrooms.length;
        const totalStandard = this.classrooms.reduce((sum, c) => sum + (c.standard_count || 40), 0);
        const camerasLinked = this.classrooms.filter(c => c.rtsp_url && c.rtsp_url.trim().length > 0).length;

        // Điểm danh
        let totalPresent = 0;
        let totalRecorded = 0;
        for (const c of this.classrooms) {
            const att = this.attendanceMap[c.id];
            if (att && att.present_count !== undefined) {
                totalPresent += att.present_count;
                totalRecorded += (c.standard_count || 40);
            }
        }

        const rateStr = totalRecorded > 0 ? `${Math.round((totalPresent / totalRecorded) * 100)}%` : '-- %';

        document.getElementById('kpiTotalClasses').textContent = totalClasses;
        document.getElementById('kpiTotalStandard').textContent = totalStandard.toLocaleString('vi-VN');
        document.getElementById('kpiCamerasLinked').textContent = `${camerasLinked} / ${totalClasses}`;
        document.getElementById('kpiAttendanceRate').textContent = rateStr;

        // Đếm theo khối
        let count10 = 0, count11 = 0, count12 = 0;
        this.classrooms.forEach(c => {
            const g = this.getGradeOfClass(c.name, c.code);
            if (g === '10') count10++;
            else if (g === '11') count11++;
            else if (g === '12') count12++;
        });

        document.getElementById('badgeCountAll').textContent = totalClasses;
        document.getElementById('badgeCount10').textContent = count10;
        document.getElementById('badgeCount11').textContent = count11;
        document.getElementById('badgeCount12').textContent = count12;
    }

    renderTable() {
        const tbody = document.getElementById('classroomsTableBody');
        if (!tbody) return;

        let filtered = this.classrooms.filter(c => {
            const grade = this.getGradeOfClass(c.name, c.code);
            if (this.currentFilter !== 'ALL' && grade !== this.currentFilter) return false;

            if (this.searchQuery) {
                const teacher = this.teachersData[c.name.replace(/[^0-9A-Za-z]/g, '')] || '';
                const searchStr = `${c.code} ${c.name} ${c.room_number || ''} ${teacher}`.toLowerCase();
                if (!searchStr.includes(this.searchQuery)) return false;
            }

            return true;
        });

        if (filtered.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" style="text-align: center; padding: 2.5rem; color: #64748b;">
                        <i class="fa-solid fa-folder-open" style="font-size: 1.5rem; color: #94a3b8; margin-bottom: 6px; display: block;"></i>
                        Không tìm thấy lớp học nào phù hợp với bộ lọc hiện tại.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = filtered.map((c, index) => {
            const grade = this.getGradeOfClass(c.name, c.code);
            const cleanClassName = (c.name || '').replace(/[^0-9A-Za-z]/g, '');
            const teacher = this.teachersData[cleanClassName] || DEFAULT_TEACHERS[cleanClassName] || 'Thầy/Cô chủ nhiệm';
            const att = this.attendanceMap[c.id];

            let attHtml = '<span style="color: #94a3b8; font-size: 0.82rem;">Chưa có dữ liệu</span>';
            if (att) {
                const p = att.present_count || 0;
                const s = c.standard_count || 40;
                const a = Math.max(0, s - p);
                const color = a === 0 ? '#10b981' : (a <= 2 ? '#f59e0b' : '#ef4444');
                attHtml = `
                    <div style="display: flex; flex-direction: column;">
                        <span style="font-weight: 700; color: ${color}; font-size: 0.88rem;">${p} / ${s} học sinh</span>
                        <span style="font-size: 0.75rem; color: #64748b;">${a === 0 ? 'Đủ 100%' : `Vắng ${a} em`}</span>
                    </div>
                `;
            }

            const isCamLinked = Boolean(c.rtsp_url && c.rtsp_url.trim().length > 0);
            const camBadge = isCamLinked
                ? `<span class="camera-status-pill online"><i class="fa-solid fa-circle" style="font-size: 7px;"></i> Kênh ${c.id}</span>`
                : `<span class="camera-status-pill offline"><i class="fa-regular fa-circle" style="font-size: 7px;"></i> Chưa gán</span>`;

            return `
                <tr class="class-row">
                    <td style="text-align: center; font-weight: 600; color: #64748b;">${index + 1}</td>
                    <td><span class="class-code-badge">${c.code || `LOP_${c.id}`}</span></td>
                    <td><strong class="class-name-text">${c.name}</strong></td>
                    <td><span class="grade-tag grade-${grade}">Khối ${grade}</span></td>
                    <td><span style="font-weight: 600; color: #475569;"><i class="fa-solid fa-door-open" style="color: #94a3b8; margin-right: 4px;"></i>${c.room_number || `P.${100 + c.id}`}</span></td>
                    <td>
                        <div style="display: inline-flex; align-items: center; gap: 6px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 3px 8px; border-radius: 6px;">
                            <i class="fa-solid fa-users" style="color: #2563eb; font-size: 0.8rem;"></i>
                            <strong style="color: #0f172a;">${c.standard_count || 40}</strong>
                            <span style="color: #64748b; font-size: 0.78rem;">em</span>
                        </div>
                    </td>
                    <td>
                        <span class="teacher-name">
                            <i class="fa-solid fa-user-tie" style="color: #64748b; font-size: 0.85rem;"></i>
                            ${teacher}
                        </span>
                    </td>
                    <td>${camBadge}</td>
                    <td>${attHtml}</td>
                    <td style="text-align: right;">
                        <div class="table-action-btn-group" style="justify-content: flex-end;">
                            <button type="button" class="action-btn action-btn-primary" onclick="window.classroomsManager.openEditModal(${c.id})" title="Chỉnh sửa thông tin lớp">
                                <i class="fa-solid fa-pen-to-square"></i> Sửa
                            </button>
                            <a href="roi-config.html?camera_id=${c.id}" class="action-btn" title="Cấu hình vùng nhận diện ROI">
                                <i class="fa-solid fa-draw-polygon" style="color: #6366f1;"></i> ROI
                            </a>
                            <a href="cameras.html?cam=${c.id}" class="action-btn" title="Xem luồng trực tiếp trên Ma trận Camera">
                                <i class="fa-solid fa-video" style="color: #059669;"></i> Xem
                            </a>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    openEditModal(classId) {
        const cls = this.classrooms.find(c => c.id === classId);
        if (!cls) return;

        document.getElementById('editClassId').value = cls.id;
        document.getElementById('editClassCode').value = cls.code || `LOP_${cls.id}`;
        document.getElementById('editClassName').value = cls.name || '';
        document.getElementById('editClassRoom').value = cls.room_number || '';
        document.getElementById('editClassStandard').value = cls.standard_count || 40;
        document.getElementById('editClassRtsp').value = cls.rtsp_url || '';

        const cleanName = (cls.name || '').replace(/[^0-9A-Za-z]/g, '');
        document.getElementById('editClassTeacher').value = this.teachersData[cleanName] || DEFAULT_TEACHERS[cleanName] || '';

        document.getElementById('classModalTitle').textContent = `Chỉnh Sửa: ${cls.name}`;
        document.getElementById('classroomModal').classList.add('is-open');
    }

    openAddModal() {
        document.getElementById('editClassId').value = '';
        document.getElementById('editClassCode').value = `LOP_${this.classrooms.length + 1}`;
        document.getElementById('editClassName').value = '';
        document.getElementById('editClassRoom').value = '';
        document.getElementById('editClassStandard').value = 40;
        document.getElementById('editClassTeacher').value = '';
        document.getElementById('editClassRtsp').value = '';

        document.getElementById('classModalTitle').textContent = 'Thêm Lớp Học Mới';
        document.getElementById('classroomModal').classList.add('is-open');
    }

    closeClassModal() {
        document.getElementById('classroomModal').classList.remove('is-open');
    }

    openBatchModal() {
        document.getElementById('batchStandardModal').classList.add('is-open');
    }

    closeBatchModal() {
        document.getElementById('batchStandardModal').classList.remove('is-open');
    }

    async saveClassroom() {
        const id = document.getElementById('editClassId').value;
        const code = document.getElementById('editClassCode').value.trim();
        const name = document.getElementById('editClassName').value.trim();
        const room = document.getElementById('editClassRoom').value.trim();
        const standard = parseInt(document.getElementById('editClassStandard').value, 10) || 40;
        const teacher = document.getElementById('editClassTeacher').value.trim();
        const rtsp = document.getElementById('editClassRtsp').value.trim();

        if (!name || !code) {
            alert('Vui lòng nhập đầy đủ Mã Lớp và Tên Lớp!');
            return;
        }

        const token = localStorage.getItem('access_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        try {
            if (id) {
                // Update
                const res = await fetch(`/api/cameras/${id}`, {
                    method: 'PUT',
                    headers,
                    body: JSON.stringify({
                        name,
                        room_number: room,
                        standard_count: standard,
                        rtsp_url: rtsp || undefined
                    })
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Lỗi khi cập nhật lớp học');
                }
            } else {
                // Create
                const res = await fetch('/api/cameras', {
                    method: 'POST',
                    headers,
                    body: JSON.stringify({
                        code,
                        name,
                        room_number: room,
                        standard_count: standard,
                        rtsp_url: rtsp || 'dataset/samples/classroom_sample_15s.mp4',
                        is_active: true
                    })
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Lỗi khi thêm lớp học');
                }
            }

            // Lưu tên giáo viên
            if (teacher) {
                const cleanName = name.replace(/[^0-9A-Za-z]/g, '');
                this.teachersData[cleanName] = teacher;
                localStorage.setItem('dieucai_teachers_map', JSON.stringify(this.teachersData));
            }

            this.closeClassModal();
            await this.loadData();
        } catch (error) {
            alert(error.message);
        }
    }

    async applyBatchStandard() {
        const count = parseInt(document.getElementById('inputBatchStandardCount').value, 10);
        if (!count || count < 1) {
            alert('Vui lòng nhập sĩ số hợp lệ!');
            return;
        }

        const confirmMsg = `Bạn có chắc chắn muốn cập nhật sĩ số chuẩn của tất cả ${this.classrooms.length} lớp học thành ${count} em?`;
        if (!confirm(confirmMsg)) return;

        const token = localStorage.getItem('access_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const btnApply = document.getElementById('btnApplyBatchStandard');
        if (btnApply) {
            btnApply.disabled = true;
            btnApply.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang áp dụng...';
        }

        try {
            // Cập nhật từng lớp
            for (const cls of this.classrooms) {
                await fetch(`/api/cameras/${cls.id}`, {
                    method: 'PUT',
                    headers,
                    body: JSON.stringify({
                        standard_count: count
                    })
                });
            }

            this.closeBatchModal();
            await this.loadData();
            alert(`Đã cập nhật thành công sĩ số ${count} em cho toàn bộ lớp học!`);
        } catch (err) {
            alert('Lỗi cập nhật sĩ số hàng loạt: ' + err.message);
        } finally {
            if (btnApply) {
                btnApply.disabled = false;
                btnApply.innerHTML = '<i class="fa-solid fa-check"></i> Áp Dụng Cho 30 Lớp';
            }
        }
    }
}

// Khởi chạy
document.addEventListener('DOMContentLoaded', () => {
    window.classroomsManager = new ClassroomsManager();
});
