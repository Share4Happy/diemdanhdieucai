# 🎨 Modal System Component Library

## 📋 Tổng Quan

**Modal System** là hệ thống component modal chuyên nghiệp, nhất quán và tái sử dụng được thiết kế cho toàn bộ hệ thống THPT Điều Cải.

### ✨ Đặc điểm

- ✅ **5 size variants**: sm, md, lg, xl, full
- ✅ **4 style variants**: success, warning, danger, info
- ✅ **Mobile-first responsive**
- ✅ **Smooth animations**
- ✅ **Loading states**
- ✅ **Accessibility support**
- ✅ **Custom scrollbar**
- ✅ **Form integration**

---

## 🚀 Quick Start

### 1. Import CSS

```html
<link rel="stylesheet" href="/static/css/modal-system.css">
```

### 2. Basic Modal Structure

```html
<div class="modal-backdrop" id="myModal">
    <div class="modal-container">
        <div class="modal-header">
            <div class="modal-header-content">
                <h3 class="modal-title">Modal Title</h3>
                <p class="modal-subtitle">Optional subtitle</p>
            </div>
            <button class="modal-close-btn" onclick="closeModal()">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        <div class="modal-body">
            <!-- Your content here -->
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary">Cancel</button>
            <button class="btn btn-primary">Save</button>
        </div>
    </div>
</div>
```

### 3. JavaScript Control

```javascript
// Open modal
function openModal() {
    document.getElementById('myModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Close modal
function closeModal() {
    document.getElementById('myModal').classList.remove('active');
    document.body.style.overflow = '';
}
```

---

## 📐 Size Variants

### Small Modal (480px)
```html
<div class="modal-container modal-sm">
    <!-- Confirmation, alerts -->
</div>
```

### Medium Modal (640px) - Default
```html
<div class="modal-container modal-md">
    <!-- Standard forms -->
</div>
```

### Large Modal (860px)
```html
<div class="modal-container modal-lg">
    <!-- Complex forms, settings -->
</div>
```

### Extra Large Modal (1080px)
```html
<div class="modal-container modal-xl">
    <!-- Data tables, multi-step forms -->
</div>
```

### Full Width Modal (95vw)
```html
<div class="modal-container modal-full">
    <!-- Image preview, video player -->
</div>
```

---

## 🎨 Style Variants

### Success Modal
```html
<div class="modal-container modal-success">
    <!-- Green gradient header -->
</div>
```

### Warning Modal
```html
<div class="modal-container modal-warning">
    <!-- Orange gradient header -->
</div>
```

### Danger Modal
```html
<div class="modal-container modal-danger">
    <!-- Red gradient header -->
</div>
```

### Info Modal
```html
<div class="modal-container modal-info">
    <!-- Blue gradient header -->
</div>
```

---

## 📝 Form Components

### Form Grid Layout

```html
<div class="modal-body">
    <!-- 2-column grid -->
    <div class="modal-form-grid modal-form-grid-2">
        <div class="modal-form-field">...</div>
        <div class="modal-form-field">...</div>
    </div>

    <!-- 3-column grid -->
    <div class="modal-form-grid modal-form-grid-3">
        <div class="modal-form-field">...</div>
        <div class="modal-form-field">...</div>
        <div class="modal-form-field">...</div>
    </div>
</div>
```

### Form Field

```html
<div class="modal-form-field">
    <label class="modal-form-label required">
        <i class="fa-solid fa-tag modal-form-label-icon"></i>
        Field Label
    </label>
    <input type="text" class="modal-form-input" placeholder="Enter value">
    <span class="modal-form-helper">Helper text</span>
</div>
```

### Select Dropdown

```html
<div class="modal-form-field">
    <label class="modal-form-label">Dropdown</label>
    <select class="modal-form-select">
        <option>Option 1</option>
        <option>Option 2</option>
    </select>
</div>
```

### Textarea

```html
<div class="modal-form-field">
    <label class="modal-form-label">Message</label>
    <textarea class="modal-form-textarea" 
              placeholder="Enter message"></textarea>
</div>
```

### Checkbox

```html
<div class="modal-form-checkbox-group">
    <input type="checkbox" class="modal-form-checkbox" id="cb1">
    <label class="modal-form-checkbox-label" for="cb1">
        Enable feature
    </label>
</div>
```

---

## 🧩 Content Components

### Section with Title

```html
<div class="modal-section">
    <h4 class="modal-section-title">
        <i class="fa-solid fa-circle-info modal-section-title-icon"></i>
        Section Title
    </h4>
    <p class="modal-section-description">Optional description</p>
    <!-- Content -->
</div>
```

### Divider

```html
<div class="modal-divider"></div>
```

### Info Box

```html
<!-- Info (blue) -->
<div class="modal-info-box info">
    <i class="fa-solid fa-lightbulb modal-info-box-icon"></i>
    <div>Message content</div>
</div>

<!-- Success (green) -->
<div class="modal-info-box success">
    <i class="fa-solid fa-circle-check modal-info-box-icon"></i>
    <div>Success message</div>
</div>

<!-- Warning (orange) -->
<div class="modal-info-box warning">
    <i class="fa-solid fa-triangle-exclamation modal-info-box-icon"></i>
    <div>Warning message</div>
</div>

<!-- Error (red) -->
<div class="modal-info-box error">
    <i class="fa-solid fa-circle-exclamation modal-info-box-icon"></i>
    <div>Error message</div>
</div>
```

### Badge

```html
<span class="modal-badge badge-primary">Primary</span>
<span class="modal-badge badge-success">Success</span>
<span class="modal-badge badge-warning">Warning</span>
<span class="modal-badge badge-danger">Danger</span>
```

---

## ⚙️ Advanced Features

### Loading State

```html
<div class="modal-container loading">
    <div class="modal-loading-overlay">
        <div class="modal-loading-spinner"></div>
    </div>
    <!-- Modal content -->
</div>
```

**JavaScript control:**
```javascript
function showLoading() {
    document.querySelector('.modal-container').classList.add('loading');
}

function hideLoading() {
    document.querySelector('.modal-container').classList.remove('loading');
}
```

### Footer Layouts

**Right-aligned (default):**
```html
<div class="modal-footer">
    <button class="btn btn-secondary">Cancel</button>
    <button class="btn btn-primary">Save</button>
</div>
```

**Centered:**
```html
<div class="modal-footer centered">
    <button class="btn btn-primary">OK</button>
</div>
```

**Space Between:**
```html
<div class="modal-footer space-between">
    <div class="modal-footer-left">
        <button class="btn btn-secondary">Help</button>
    </div>
    <div class="modal-footer-right">
        <button class="btn btn-secondary">Cancel</button>
        <button class="btn btn-primary">Save</button>
    </div>
</div>
```

---

## 📱 Responsive Behavior

### Desktop (>1024px)
- Max width theo size variant
- Horizontal form grids
- Centered trong viewport

### Tablet (768px - 1024px)
- Form grid → 1 column
- Modal centered với padding

### Mobile (<768px)
- Slide from bottom
- Border radius top only
- Full width
- Stacked footer buttons
- Max height: 85vh

### Extra Small (<480px)
- Near full screen
- Minimal padding
- Max height: 92vh

---

## 🎭 Animation Variants

### Default: Slide Up
```html
<div class="modal-backdrop">
    <!-- Slide from bottom -->
</div>
```

### Scale Animation
```html
<div class="modal-backdrop scale">
    <!-- Scale from center -->
</div>
```

### Bottom Slide (Mobile)
```html
<div class="modal-backdrop slide-up">
    <!-- Slide from bottom edge -->
</div>
```

---

## ♿ Accessibility

### Keyboard Support

```javascript
// Escape key closes modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
    }
});
```

### Focus Management

```javascript
function openModal() {
    const modal = document.getElementById('myModal');
    modal.classList.add('active');
    // Focus first input
    modal.querySelector('input, button, select')?.focus();
}
```

### Backdrop Click to Close

```javascript
const backdrop = document.getElementById('myModal');
backdrop.addEventListener('click', (e) => {
    if (e.target === backdrop) {
        closeModal();
    }
});
```

---

## 📚 Common Use Cases

### 1. Form Modal (Add/Edit)

```html
<div class="modal-backdrop" id="formModal">
    <div class="modal-container modal-lg">
        <div class="modal-header">
            <div class="modal-header-content">
                <h3 class="modal-title">
                    <i class="fa-solid fa-plus modal-title-icon"></i>
                    Add New Item
                </h3>
                <p class="modal-subtitle">Fill in the details below</p>
            </div>
            <button class="modal-close-btn" onclick="closeFormModal()">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        <div class="modal-body">
            <div class="modal-form-grid modal-form-grid-2">
                <!-- Form fields -->
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary">Cancel</button>
            <button class="btn btn-primary">Save</button>
        </div>
    </div>
</div>
```

### 2. Confirmation Modal (Delete)

```html
<div class="modal-backdrop" id="confirmModal">
    <div class="modal-container modal-sm modal-danger">
        <div class="modal-header">
            <div class="modal-header-content">
                <h3 class="modal-title">
                    <i class="fa-solid fa-triangle-exclamation modal-title-icon"></i>
                    Confirm Delete
                </h3>
            </div>
            <button class="modal-close-btn" onclick="closeConfirmModal()">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        <div class="modal-body">
            <p>Are you sure you want to delete this item?</p>
            <div class="modal-info-box warning">
                <i class="fa-solid fa-triangle-exclamation modal-info-box-icon"></i>
                <div>This action cannot be undone!</div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary">Cancel</button>
            <button class="btn btn-danger">Delete</button>
        </div>
    </div>
</div>
```

### 3. Success Notification

```html
<div class="modal-backdrop" id="successModal">
    <div class="modal-container modal-sm modal-success">
        <div class="modal-header">
            <div class="modal-header-content">
                <h3 class="modal-title">
                    <i class="fa-solid fa-circle-check modal-title-icon"></i>
                    Success!
                </h3>
            </div>
            <button class="modal-close-btn" onclick="closeSuccessModal()">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        <div class="modal-body">
            <p>Your changes have been saved successfully.</p>
        </div>
        <div class="modal-footer centered">
            <button class="btn btn-success">OK</button>
        </div>
    </div>
</div>
```

### 4. Image Preview (Lightbox)

```html
<div class="modal-backdrop fullscreen" id="imageModal">
    <div class="modal-container modal-full">
        <div class="modal-header">
            <div class="modal-header-content">
                <h3 class="modal-title">
                    <i class="fa-solid fa-image modal-title-icon"></i>
                    Image Preview
                </h3>
            </div>
            <button class="modal-close-btn" onclick="closeImageModal()">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
        <div class="modal-body" style="text-align: center;">
            <img src="..." alt="Preview" style="max-width: 100%; border-radius: 8px;">
        </div>
    </div>
</div>
```

---

## 🐛 Troubleshooting

### Modal not showing?
- Check if `active` class is added
- Ensure CSS file is loaded
- Check z-index conflicts

### Backdrop not blurring?
- Check browser support for `backdrop-filter`
- Fallback: adjust `--modal-backdrop-bg` opacity

### Scrollbar issues?
- Check if `overflow-y: auto` is on `.modal-body`
- Adjust `max-height` if needed

### Mobile responsiveness?
- Test on real devices
- Check viewport meta tag
- Adjust breakpoints if needed

---

## 📊 Browser Support

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ⚠️ IE11 (requires polyfills for backdrop-filter)

---

## 🔧 Customization

### Override CSS Variables

```css
:root {
    --modal-backdrop-bg: rgba(0, 0, 0, 0.8);
    --modal-bg: #ffffff;
    --modal-border-radius: 20px;
    --modal-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
}
```

### Custom Animation

```css
.modal-backdrop.fade .modal-container {
    animation: fadeInScale 0.4s ease;
}

@keyframes fadeInScale {
    from {
        opacity: 0;
        transform: scale(0.9);
    }
    to {
        opacity: 1;
        transform: scale(1);
    }
}
```

---

## 📝 Best Practices

1. **Always provide a close button**
2. **Use semantic HTML (h3 for title, p for subtitle)**
3. **Add loading states for async operations**
4. **Prevent body scroll when modal is open**
5. **Close on Escape key**
6. **Close on backdrop click (optional)**
7. **Focus first input/button on open**
8. **Use appropriate size variant**
9. **Use appropriate style variant**
10. **Keep modal content concise**

---

## 🎯 Demo

Xem demo đầy đủ tại: `/modal-demo`

Hoặc mở file: `web/templates/modal-demo.html`

---

## 📚 Related Files

- CSS: `web/static/css/modal-system.css`
- Demo: `web/templates/modal-demo.html`
- Guide: `web/static/css/MODAL_SYSTEM_GUIDE.md`

---

**Version:** 2.0  
**Last Updated:** 2026  
**Author:** Kiro AI Assistant
