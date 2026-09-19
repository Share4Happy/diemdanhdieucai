# 🎨 Modal System - Quick Start Guide

**Status:** ✅ Production Ready  
**Version:** 1.0  
**Last Updated:** September 19, 2026

---

## 🚀 Quick Start (3 Steps)

### 1. Link CSS
```html
<link rel="stylesheet" href="/static/css/modal-system.css">
```

### 2. Copy Template
```html
<div class="modal-backdrop" id="myModal">
    <div class="modal-container modal-lg">
        <!-- Header -->
        <div class="modal-header">
            <div class="modal-header-content">
                <h3 class="modal-title">
                    <i class="fa-solid fa-icon modal-title-icon"></i>
                    Title
                </h3>
                <p class="modal-subtitle">Subtitle</p>
            </div>
            <button class="modal-close-btn" onclick="closeModal()">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        
        <!-- Body -->
        <div class="modal-body">
            <div class="modal-section">
                <h4 class="modal-section-title">Section</h4>
                <!-- Content -->
            </div>
        </div>
        
        <!-- Footer -->
        <div class="modal-footer">
            <button class="modal-btn modal-btn-secondary">Cancel</button>
            <button class="modal-btn modal-btn-primary">Save</button>
        </div>
    </div>
</div>
```

### 3. Add JavaScript
```javascript
function openModal() {
    document.getElementById('myModal').classList.add('active');
}

function closeModal() {
    document.getElementById('myModal').classList.remove('active');
}
```

---

## 📏 Size Variants

```html
<div class="modal-container modal-sm">   <!-- 400px -->
<div class="modal-container modal-md">   <!-- 600px (default) -->
<div class="modal-container modal-lg">   <!-- 800px -->
<div class="modal-container modal-xl">   <!-- 1000px -->
<div class="modal-container modal-full"> <!-- 95vw -->
```

---

## 🎨 Style Variants

```html
<div class="modal-container modal-success">  <!-- Green header -->
<div class="modal-container modal-warning">  <!-- Orange header -->
<div class="modal-container modal-danger">   <!-- Red header -->
<div class="modal-container modal-info">     <!-- Blue header -->
```

---

## 🔘 Buttons

```html
<button class="modal-btn modal-btn-primary">Save</button>
<button class="modal-btn modal-btn-secondary">Cancel</button>
<button class="modal-btn modal-btn-danger">Delete</button>

<!-- Sizes -->
<button class="modal-btn modal-btn-primary modal-btn-sm">Small</button>
<button class="modal-btn modal-btn-primary modal-btn-lg">Large</button>
```

---

## 📝 Form Example

```html
<div class="modal-form-grid modal-form-grid-2">
    <div class="modal-form-field">
        <label class="modal-form-label required">
            <i class="fa-solid fa-user modal-form-label-icon"></i>
            Name
        </label>
        <input type="text" class="modal-form-input" placeholder="Enter name">
        <span class="modal-form-helper">This is a helper text</span>
    </div>
    
    <div class="modal-form-field">
        <label class="modal-form-label">Email</label>
        <input type="email" class="modal-form-input">
    </div>
</div>
```

---

## ⏳ Loading State

### HTML
```html
<div class="modal-loading-overlay" id="myModalLoading">
    <div class="modal-loading-spinner"></div>
</div>
```

### JavaScript
```javascript
function showLoading() {
    document.getElementById('myModalLoading').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('myModalLoading').style.display = 'none';
}

async function saveData() {
    showLoading();
    try {
        await fetch('/api/save', {...});
        hideLoading();
    } catch (err) {
        hideLoading();
    }
}
```

---

## 📐 Layout Components

### Sections & Dividers
```html
<div class="modal-section">
    <h4 class="modal-section-title">
        <i class="fa-solid fa-icon modal-section-title-icon"></i>
        Section Title
    </h4>
    <!-- Content -->
</div>

<div class="modal-divider"></div>
```

### Grid Layouts
```html
<!-- 2 columns -->
<div class="modal-form-grid modal-form-grid-2">
    <div class="modal-form-field">...</div>
    <div class="modal-form-field">...</div>
</div>

<!-- 3 columns -->
<div class="modal-form-grid modal-form-grid-3">
    <div class="modal-form-field">...</div>
    <div class="modal-form-field">...</div>
    <div class="modal-form-field">...</div>
</div>
```

---

## ✅ Checkbox

```html
<label class="modal-form-checkbox">
    <input type="checkbox" id="myCheck">
    <span class="modal-form-checkbox-label">Accept terms</span>
</label>
```

---

## 🔗 Links

```html
<a href="#" class="modal-link">Click here</a>
```

---

## 📱 Responsive

- **Desktop (≥768px):** Full size variants
- **Tablet (768px):** 95vw width, adjusted padding
- **Mobile (<768px):** 100vw width, stacked fields

Auto-responsive, không cần code thêm!

---

## 🎯 Real Examples in Project

### Simple Image Modal
```html
<!-- See: web/templates/reports.html - #imgModal -->
```

### Complex Form Modal
```html
<!-- See: web/templates/cameras.html - #cameraModal -->
```

### Comparison Modal
```html
<!-- See: web/templates/dashboard.html - #imageModal -->
```

---

## 📚 Full Documentation

- **Complete Guide:** `web/static/css/MODAL_SYSTEM_GUIDE.md`
- **Implementation Summary:** `MODAL_SYSTEM_IMPLEMENTATION_COMPLETE.md`
- **Source Code:** `web/static/css/modal-system.css`

---

## 🐛 Common Issues

### Modal không hiển thị?
```javascript
// Check: có class 'active' chưa?
document.getElementById('myModal').classList.add('active');
```

### Loading spinner không quay?
```css
/* Check: CSS đã link chưa? */
<link rel="stylesheet" href="/static/css/modal-system.css">
```

### Form không responsive?
```html
<!-- Check: có dùng modal-form-grid chưa? -->
<div class="modal-form-grid modal-form-grid-2">...</div>
```

### Button không đúng style?
```html
<!-- Check: có class modal-btn chưa? -->
<button class="modal-btn modal-btn-primary">...</button>
```

---

## ✨ Best Practices

1. ✅ Always use semantic sections
2. ✅ Add loading states for async operations
3. ✅ Use helper text for complex fields
4. ✅ Icon-enhance important labels
5. ✅ Use appropriate size variant
6. ✅ Add close function for all modals
7. ✅ Test on mobile devices

---

## 📞 Need Help?

1. Check examples in `cameras.html`, `dashboard.html`, `reports.html`
2. Read `MODAL_SYSTEM_GUIDE.md` for detailed docs
3. Look at `modal-system.css` source code (có comments chi tiết)

---

**🎉 Happy Coding!**

*Modal System v1.0 - THPT Điều Cải*
