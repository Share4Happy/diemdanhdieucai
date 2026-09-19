# Frontend Development Guide
**THPT Điều Cải - Attendance System**

## 📁 Cấu Trúc Dự Án

```
frontend/
├── pages/              # HTML templates
├── css/               # Stylesheets
│   ├── base.css       # CSS variables, reset, utilities
│   ├── layout/        # Layout components (header, responsive)
│   ├── components/    # UI components (buttons, cards, modals, tables)
│   └── pages/         # Page-specific styles
├── js/
│   ├── core/          # Core utilities (api, config, utils)
│   ├── shared/        # Shared resources (constants, validators)
│   ├── components/    # UI component logic (modals, forms)
│   └── modules/       # Page-specific modules
└── assets/            # Static assets (images, icons, fonts)
```

## 🚀 Getting Started

### Tạo Trang Mới

1. **Tạo HTML file trong `pages/`**
```html
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Trang Mới - THPT Điều Cải</title>
    
    <!-- Base Styles -->
    <link rel="stylesheet" href="../css/base.css">
    
    <!-- Layout -->
    <link rel="stylesheet" href="../css/layout/header.css">
    <link rel="stylesheet" href="../css/layout/responsive.css">
    
    <!-- Components -->
    <link rel="stylesheet" href="../css/components/buttons.css">
    <link rel="stylesheet" href="../css/components/cards.css">
    <link rel="stylesheet" href="../css/components/modal-system.css">
    
    <!-- Page Specific (optional) -->
    <link rel="stylesheet" href="../css/pages/your-page.css">
    
    <!-- JavaScript -->
    <script src="../js/core/config.js"></script>
    <script src="../js/core/api.js"></script>
    <script src="../js/core/utils.js"></script>
    <script src="../js/shared/constants.js"></script>
    <script src="../js/components/modal-notifications.js"></script>
</head>
<body>
    <!-- Your content here -->
</body>
</html>
```

2. **Tạo page-specific CSS (nếu cần)**
```css
/* css/pages/your-page.css */
.your-custom-class {
  /* styles */
}
```

3. **Tạo page-specific JS module (nếu cần)**
```javascript
// js/modules/your-page.js
document.addEventListener('DOMContentLoaded', () => {
  // Your page logic
});
```

## 🎨 Sử Dụng Components

### Buttons
```html
<button class="btn btn-primary">Primary</button>
<button class="btn btn-success">Success</button>
<button class="btn btn-danger">Danger</button>
<button class="btn btn-secondary">Secondary</button>
```

### Cards
```html
<div class="card">
  <div class="card-header">
    <h3>Card Title</h3>
  </div>
  <div class="card-body">
    Card content here
  </div>
</div>
```

### KPI Cards
```html
<div class="kpi-card">
  <div class="kpi-icon primary">📊</div>
  <div class="kpi-label">Total Students</div>
  <div class="kpi-value">1,234</div>
  <div class="kpi-change positive">+5.2%</div>
</div>
```

### Tables
```html
<div class="table-container">
  <div class="table-header">
    <h3>Table Title</h3>
    <div class="table-search">
      <input type="text" placeholder="Tìm kiếm...">
    </div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Column 1</th>
        <th>Column 2</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Data 1</td>
        <td>Data 2</td>
      </tr>
    </tbody>
  </table>
</div>
```

### Modals
```javascript
// Show notification modal
showSuccessModal('Thành công!', 'Dữ liệu đã được lưu.');
showErrorModal('Lỗi!', 'Không thể kết nối server.');
showWarningModal('Cảnh báo!', 'Vui lòng kiểm tra lại.');
showInfoModal('Thông tin', 'Đây là thông báo.');

// Show confirm modal
showConfirmModal(
  'Xác nhận xóa?',
  'Bạn có chắc muốn xóa item này?',
  async () => {
    // On confirm
    await deleteItem();
  },
  () => {
    // On cancel
    console.log('Cancelled');
  }
);
```

## 🔌 API Usage

```javascript
// GET request
const data = await api.get('/api/cameras');

// POST request
const result = await api.post('/api/cameras', {
  name: 'Camera 1',
  url: 'rtsp://...'
});

// PUT request
await api.put('/api/cameras/123', { name: 'Updated' });

// DELETE request
await api.delete('/api/cameras/123');

// With error handling
try {
  const response = await api.post('/api/attendance/trigger');
  showSuccessModal('Success', response.message);
} catch (error) {
  showErrorModal('Error', error.message);
}
```

## 🛠️ Utilities

### Date Formatting
```javascript
Utils.formatDate(new Date()); // "19/09/2026 14:30:45"
Utils.formatRelativeTime(date); // "2 giờ trước"
```

### Storage
```javascript
Utils.storage.set('key', { data: 'value' });
const data = Utils.storage.get('key');
Utils.storage.remove('key');
```

### Debounce / Throttle
```javascript
const search = Utils.debounce((query) => {
  // Search logic
}, 300);

input.addEventListener('input', (e) => search(e.target.value));
```

### Other Utils
```javascript
Utils.copyToClipboard('text');
Utils.downloadFile('/api/download', 'file.xlsx');
Utils.formatNumber(1234567); // "1,234,567"
Utils.truncate('Long text...', 20);
```

## ✅ Form Validation

```javascript
// Define validation rules
const rules = {
  name: [
    Validators.required,
    (v) => Validators.minLength(v, 3),
    (v) => Validators.maxLength(v, 100),
  ],
  url: [
    Validators.required,
    Validators.rtspUrl,
  ],
};

// Validate form
const formData = {
  name: form.name.value,
  url: form.url.value,
};

const result = Validators.validateForm(formData, rules);

if (result.valid) {
  // Submit form
  await api.post('/api/cameras', formData);
} else {
  // Display errors
  Validators.displayErrors(result.errors, form);
}
```

## 🎨 CSS Variables

```css
/* Use in your custom CSS */
.custom-element {
  color: var(--primary);
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
  transition: var(--transition-base);
}
```

### Available Variables
- Colors: `--primary`, `--success`, `--warning`, `--danger`, `--info`
- Backgrounds: `--card-bg`, `--body-bg`, `--dark-bg`
- Text: `--text-main`, `--text-muted`
- Borders: `--border-color`
- Shadows: `--shadow-sm`, `--shadow-md`, `--shadow-lg`, `--shadow-xl`
- Radius: `--radius`, `--radius-sm`, `--radius-lg`
- Transitions: `--transition-base`, `--transition-fast`, `--transition-smooth`

## 📱 Responsive Design

All components are mobile-first and responsive by default. Use responsive.css breakpoints:

- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: >= 1024px
- Large Desktop: >= 1280px
- XL: >= 1536px

## 🔍 Best Practices

1. **Always include base.css first**
2. **Use utility classes for common styles**
3. **Validate user input before API calls**
4. **Show loading states for async operations**
5. **Handle errors gracefully with modal notifications**
6. **Keep inline JS minimal - extract to modules**
7. **Use constants instead of magic strings/numbers**
8. **Comment complex logic**
9. **Test on different screen sizes**

## 📝 Notes

- **Backend Integration**: HTML pages in `frontend/pages/` use relative paths. Backend still serves from `web/templates/` with Flask routes.
- **API Calls**: All API endpoints are defined in `js/core/config.js`
- **Modal System**: Uses `modal-system.css` + `modal-notifications.js`
- **No Build Step**: Pure HTML/CSS/JS - no bundler required

## 🐛 Debugging

1. Check browser console for errors
2. Use `CONFIG.FEATURES.ENABLE_DEBUG_MODE = true` for verbose logging
3. Verify API endpoints in `config.js`
4. Test API calls in browser DevTools Network tab

## 📚 Further Reading

- Modal System: See `/MODAL_SYSTEM_GUIDE.md`
- API Documentation: Check backend `app.py` routes
- CSS Components: Explore `css/components/` files
