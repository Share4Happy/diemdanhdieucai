# Frontend - THPT Điều Cải Attendance System

## 📁 Cấu Trúc Thư Mục

```
frontend/
├── pages/              # HTML templates
│   ├── dashboard.html
│   ├── cameras.html
│   ├── reports.html
│   └── roi_config.html
│
├── css/
│   ├── layout/        # Layout components
│   │   ├── sidebar.css
│   │   ├── header.css
│   │   └── responsive.css
│   │
│   ├── components/    # Reusable UI components
│   │   ├── modal-system.css
│   │   ├── buttons.css
│   │   ├── cards.css
│   │   ├── tables.css
│   │   └── form-components.css
│   │
│   └── pages/         # Page-specific styles
│       ├── dashboard.css
│       ├── cameras.css
│       ├── reports.css
│       └── roi_config.css
│
├── js/
│   ├── core/          # Core utilities
│   │   ├── api.js         # API calls
│   │   ├── config.js      # Configuration
│   │   └── utils.js       # Helper functions
│   │
│   ├── shared/        # Shared resources
│   │   ├── constants.js   # Constants
│   │   └── validators.js  # Validation functions
│   │
│   ├── components/    # UI component logic
│   │   ├── modal-notifications.js
│   │   ├── sidebar.js
│   │   └── charts.js
│   │
│   └── modules/       # Page-specific modules
│       ├── dashboard.js
│       ├── cameras.js
│       ├── reports.js
│       └── roi_config.js
│
└── assets/
    ├── images/        # Images & logos
    ├── icons/         # Icon files
    └── fonts/         # Custom fonts
```

## 🚀 Migration Status

### ✅ Phase 0-1: Structure Created
- [x] Created folder structure
- [x] Created README.md

### ⏳ Next Phases
- [ ] Phase 2: Copy CSS files
- [ ] Phase 3: Copy JS files
- [ ] Phase 4: Copy HTML templates
- [ ] Phase 5: Create core files (api.js, config.js, utils.js)
- [ ] Phase 6: Extract inline JS to modules
- [ ] Phase 7: Testing & Documentation

## 📝 Notes

- **Migration Date**: 2026-09-19
- **Branch**: phat
- **Strategy**: Copy-only (không xóa web/ để đảm bảo backend vẫn hoạt động)
- **Purpose**: Tách biệt frontend/backend, cấu trúc modular, dễ bảo trì

## 🔗 Related Files

- Modal System: `css/components/modal-system.css`
- Notifications: `js/components/modal-notifications.js`
- Documentation: `/MODAL_SYSTEM_GUIDE.md`
