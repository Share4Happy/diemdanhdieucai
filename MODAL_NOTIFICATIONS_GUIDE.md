# 🔔 Modal Notification System - Hướng Dẫn Sử Dụng

**File:** `web/static/js/modal-notifications.js`  
**Mục đích:** Thay thế `alert()` và `confirm()` cũ bằng modal đẹp, hiện đại

---

## 🎯 Đã Áp Dụng Vào Đâu?

### ✅ cameras.html
- ✅ Thông báo lưu camera thành công
- ✅ Thông báo lỗi kết nối
- ✅ Cảnh báo nhập thiếu thông tin
- ✅ Xác nhận xóa camera (modal confirm)
- ✅ Xác nhận khôi phục danh sách lớp

### ✅ dashboard.html
- ✅ Thông báo hoàn thành quét điểm danh
- ✅ Thông báo lỗi quét

### ✅ reports.html
- ✅ Thông báo xuất Excel thành công
- ✅ Thông báo gửi email thành công
- ✅ Thông báo lưu cấu hình Zalo
- ✅ Thông báo vị trí thư mục
- ✅ Thông báo kết nối CSDL

**Tổng cộng:** ~15 chỗ đã thay thế alert/confirm bằng modal đẹp!

---

## 🚀 Các Loại Modal Có Sẵn

### 1. Success Modal (Xanh lá) ✅
**Dùng khi:** Thao tác thành công

```javascript
showSuccess('Lưu thành công!');
showSuccess('Đã cập nhật dữ liệu!', 'Hoàn Thành');
showSuccess('Gửi email thành công!', 'Thành Công', 5000); // auto close sau 5s
```

**Tham số:**
- `message` (required): Nội dung thông báo
- `title` (optional): Tiêu đề, mặc định "Thành Công"
- `duration` (optional): Tự động đóng sau X milliseconds, mặc định 3000ms

---

### 2. Error Modal (Đỏ) ❌
**Dùng khi:** Có lỗi xảy ra

```javascript
showError('Không thể kết nối máy chủ!');
showError('Lỗi: Thiếu thông tin bắt buộc', 'Lỗi Validation');
```

**Tham số:**
- `message` (required): Nội dung lỗi
- `title` (optional): Tiêu đề, mặc định "Lỗi"

---

### 3. Warning Modal (Cam) ⚠️
**Dùng khi:** Cảnh báo user

```javascript
showWarning('Vui lòng nhập đầy đủ thông tin!');
showWarning('File quá lớn, tối đa 5MB', 'Cảnh Báo');
```

**Tham số:**
- `message` (required): Nội dung cảnh báo
- `title` (optional): Tiêu đề, mặc định "Cảnh Báo"

---

### 4. Info Modal (Xanh dương) ℹ️
**Dùng khi:** Hiển thị thông tin

```javascript
showInfo('Thư mục được lưu tại: /storage/reports');
showInfo('Hệ thống sẽ bảo trì vào 2h sáng mai', 'Thông Báo');
```

**Tham số:**
- `message` (required): Nội dung thông tin
- `title` (optional): Tiêu đề, mặc định "Thông Tin"

---

### 5. Confirm Modal (Xác nhận Yes/No) ❓
**Dùng khi:** Cần user xác nhận trước khi thực hiện

```javascript
// Basic usage
confirmAction(
    'Bạn có chắc muốn xóa?',
    () => {
        // User clicked YES - Do something
        console.log('User confirmed!');
    }
);

// Advanced usage
confirmAction(
    'Xóa camera này sẽ xóa luôn dữ liệu ROI. Tiếp tục?',
    () => {
        // User clicked YES
        deleteCamera(id);
    },
    () => {
        // User clicked NO (optional)
        console.log('User cancelled');
    },
    'Xác Nhận Xóa' // Custom title
);
```

**Tham số:**
- `message` (required): Câu hỏi xác nhận
- `onConfirm` (required): Function gọi khi user click YES
- `onCancel` (optional): Function gọi khi user click NO
- `title` (optional): Tiêu đề, mặc định "Xác Nhận"

---

### 6. Global Loading Modal ⏳
**Dùng khi:** Cần hiển thị loading toàn màn hình

```javascript
// Show loading
showGlobalLoading('Đang xử lý...');

// Do something async
await someAsyncOperation();

// Hide loading
hideGlobalLoading();
```

**Example trong async function:**
```javascript
async function processData() {
    showGlobalLoading('Đang xử lý dữ liệu...');
    
    try {
        await fetch('/api/process');
        hideGlobalLoading();
        showSuccess('Xử lý thành công!');
    } catch (err) {
        hideGlobalLoading();
        showError('Lỗi: ' + err.message);
    }
}
```

---

## 📖 Examples Thực Tế Trong Code

### Example 1: Lưu Dữ Liệu (cameras.html)
```javascript
async function saveCamera() {
    // Validation
    if (!name || !url) {
        showWarning('Vui lòng nhập đầy đủ thông tin!');
        return;
    }
    
    // Show loading on modal
    showModalLoading();
    
    try {
        const res = await fetch('/api/cameras', {...});
        const result = await res.json();
        
        hideModalLoading();
        
        if (result.success) {
            closeModal();
            showSuccess(result.message); // Modal thông báo thành công
        } else {
            showError('Lỗi: ' + result.message);
        }
    } catch (err) {
        hideModalLoading();
        showError('Lỗi kết nối: ' + err);
    }
}
```

### Example 2: Xóa Với Confirm (cameras.html)
```javascript
async function deleteCamera(id, name) {
    // Show confirm modal
    confirmAction(
        `Xóa camera "${name}"? Dữ liệu ROI cũng sẽ bị xóa.`,
        async () => {
            // User confirmed - proceed
            showGlobalLoading('Đang xóa...');
            
            try {
                const res = await fetch(`/api/cameras/${id}`, {method: 'DELETE'});
                const result = await res.json();
                
                hideGlobalLoading();
                
                if (res.ok) {
                    await loadCameras();
                    showSuccess('Đã xóa camera thành công!');
                } else {
                    showError('Không thể xóa: ' + result.message);
                }
            } catch (err) {
                hideGlobalLoading();
                showError('Lỗi: ' + err);
            }
        },
        null, // onCancel - do nothing
        'Xác Nhận Xóa'
    );
}
```

### Example 3: Thông Báo Thành Công (reports.html)
```javascript
async function exportExcel() {
    try {
        const res = await fetch('/api/export-excel');
        const result = await res.json();
        
        if (result.success) {
            // Show success with 5s auto-close
            showSuccess(
                `Xuất Excel thành công! File: ${result.filename}`,
                'Xuất Báo Cáo Thành Công',
                5000
            );
            
            // Open file
            window.open(result.download_url, '_blank');
        } else {
            showError('Lỗi xuất Excel: ' + result.error);
        }
    } catch (err) {
        showError('Lỗi kết nối: ' + err.message);
    }
}
```

---

## 🎨 Giao Diện Modal

### Success Modal
```
┌────────────────────────────────┐
│ ✅ Thành Công              ✕  │
├────────────────────────────────┤
│                                │
│        🎉 (Icon lớn)          │
│                                │
│     Lưu dữ liệu thành công!   │
│                                │
├────────────────────────────────┤
│              [✓ OK]            │
└────────────────────────────────┘
```

### Error Modal
```
┌────────────────────────────────┐
│ ❌ Lỗi                      ✕ │
├────────────────────────────────┤
│                                │
│        ⛔ (Icon lớn)          │
│                                │
│  Không thể kết nối máy chủ!   │
│                                │
├────────────────────────────────┤
│             [✕ Đóng]           │
└────────────────────────────────┘
```

### Confirm Modal
```
┌────────────────────────────────┐
│ ❓ Xác Nhận                 ✕ │
├────────────────────────────────┤
│                                │
│        ❓ (Icon lớn)          │
│                                │
│  Bạn có chắc muốn xóa không?  │
│                                │
├────────────────────────────────┤
│      [✕ Hủy]  [✓ Xác Nhận]    │
└────────────────────────────────┘
```

---

## 🔧 Customization

### Thay đổi thời gian auto-close
```javascript
// Mặc định 3 giây
showSuccess('Message');

// Custom 5 giây
showSuccess('Message', 'Title', 5000);

// Không tự động đóng
showSuccess('Message', 'Title', 0);
```

### Thêm callback sau khi đóng
```javascript
function showSuccessWithCallback(message, callback) {
    showSuccess(message);
    setTimeout(() => {
        if (callback) callback();
    }, 3000); // Wait for modal auto-close
}
```

---

## 💡 Best Practices

### ✅ DO
```javascript
// 1. Dùng đúng loại modal
showSuccess('Lưu thành công!');
showError('Lỗi kết nối!');
showWarning('Vui lòng nhập email!');

// 2. Message ngắn gọn, rõ ràng
showSuccess('Đã gửi email thành công!');

// 3. Có confirm trước khi xóa
confirmAction('Xóa dữ liệu?', () => deleteData());

// 4. Show loading khi async
showGlobalLoading('Đang tải...');
await fetchData();
hideGlobalLoading();
```

### ❌ DON'T
```javascript
// 1. Đừng dùng alert() nữa
alert('Success!'); // ❌ Old style

// 2. Message quá dài
showSuccess('Thao tác đã hoàn thành thành công và dữ liệu đã được lưu vào cơ sở dữ liệu và hệ thống đã tự động gửi email thông báo...'); // ❌ Too long

// 3. Quên hide loading
showGlobalLoading('Loading...');
// ... forgot hideGlobalLoading() // ❌ Loading stuck

// 4. Success cho error
showSuccess('Có lỗi xảy ra!'); // ❌ Wrong type
```

---

## 📱 Responsive

- **Desktop:** Modal size nhỏ (400px), centered
- **Mobile:** Modal full width, touch-friendly
- **Tự động điều chỉnh** - Không cần code thêm!

---

## 🎯 Tóm Tắt Nhanh

| Function | Dùng Khi | Icon | Màu |
|----------|----------|------|-----|
| `showSuccess()` | Thành công | ✅ | Xanh lá |
| `showError()` | Có lỗi | ❌ | Đỏ |
| `showWarning()` | Cảnh báo | ⚠️ | Cam |
| `showInfo()` | Thông tin | ℹ️ | Xanh dương |
| `confirmAction()` | Xác nhận | ❓ | Cam |
| `showGlobalLoading()` | Loading | ⏳ | Xanh dương |

---

## 🔗 Related Files

- **Source:** `web/static/js/modal-notifications.js`
- **CSS:** `web/static/css/modal-system.css`
- **Examples:**
  - `web/templates/cameras.html` (nhiều examples nhất)
  - `web/templates/dashboard.html`
  - `web/templates/reports.html`

---

**🎉 Giờ hệ thống có modal thông báo đẹp thay vì alert() xấu xí! 🎉**

*Last updated: September 19, 2026*
