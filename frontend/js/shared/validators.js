/**
 * Validation Functions for THPT Điều Cải Attendance System
 * Form and data validation utilities
 */

const Validators = {
  /**
   * Validate required field
   * @param {any} value - Value to validate
   * @returns {Object} Validation result
   */
  required(value) {
    const isValid = value !== null && value !== undefined && value !== '';
    return {
      valid: isValid,
      message: isValid ? '' : 'Trường này là bắt buộc',
    };
  },

  /**
   * Validate minimum length
   * @param {string} value - Value to validate
   * @param {number} minLength - Minimum length
   * @returns {Object} Validation result
   */
  minLength(value, minLength) {
    const isValid = value && value.length >= minLength;
    return {
      valid: isValid,
      message: isValid ? '' : `Tối thiểu ${minLength} ký tự`,
    };
  },

  /**
   * Validate maximum length
   * @param {string} value - Value to validate
   * @param {number} maxLength - Maximum length
   * @returns {Object} Validation result
   */
  maxLength(value, maxLength) {
    const isValid = !value || value.length <= maxLength;
    return {
      valid: isValid,
      message: isValid ? '' : `Tối đa ${maxLength} ký tự`,
    };
  },

  /**
   * Validate URL format
   * @param {string} url - URL to validate
   * @returns {Object} Validation result
   */
  url(url) {
    const pattern = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/;
    const isValid = !url || pattern.test(url);
    return {
      valid: isValid,
      message: isValid ? '' : 'URL không hợp lệ',
    };
  },

  /**
   * Validate RTSP URL format
   * @param {string} url - RTSP URL to validate
   * @returns {Object} Validation result
   */
  rtspUrl(url) {
    const pattern = /^rtsp:\/\/.+/;
    const isValid = pattern.test(url);
    return {
      valid: isValid,
      message: isValid ? '' : 'URL RTSP không hợp lệ (phải bắt đầu với rtsp://)',
    };
  },

  /**
   * Validate IP address format
   * @param {string} ip - IP address to validate
   * @returns {Object} Validation result
   */
  ipAddress(ip) {
    const pattern = /^(\d{1,3}\.){3}\d{1,3}$/;
    const isValid = pattern.test(ip);
    
    if (isValid) {
      const parts = ip.split('.');
      const validRange = parts.every(part => {
        const num = parseInt(part, 10);
        return num >= 0 && num <= 255;
      });
      
      return {
        valid: validRange,
        message: validRange ? '' : 'Địa chỉ IP không hợp lệ',
      };
    }
    
    return {
      valid: false,
      message: 'Địa chỉ IP không hợp lệ',
    };
  },

  /**
   * Validate camera name
   * @param {string} name - Camera name to validate
   * @returns {Object} Validation result
   */
  cameraName(name) {
    const requiredCheck = this.required(name);
    if (!requiredCheck.valid) return requiredCheck;

    const minCheck = this.minLength(name, 3);
    if (!minCheck.valid) return minCheck;

    const maxCheck = this.maxLength(name, 100);
    if (!maxCheck.valid) return maxCheck;

    return { valid: true, message: '' };
  },

  /**
   * Validate camera type
   * @param {string} type - Camera type to validate
   * @returns {Object} Validation result
   */
  cameraType(type) {
    const validTypes = Object.values(CONSTANTS?.CAMERA_TYPES || { RTSP: 'rtsp', HTTP: 'http', USB: 'usb' });
    const isValid = validTypes.includes(type);
    
    return {
      valid: isValid,
      message: isValid ? '' : 'Loại camera không hợp lệ',
    };
  },

  /**
   * Validate camera URL based on type
   * @param {string} url - URL to validate
   * @param {string} type - Camera type
   * @returns {Object} Validation result
   */
  cameraUrl(url, type) {
    const requiredCheck = this.required(url);
    if (!requiredCheck.valid) return requiredCheck;

    if (type === 'rtsp') {
      return this.rtspUrl(url);
    } else if (type === 'http') {
      return this.url(url);
    }

    return { valid: true, message: '' };
  },

  /**
   * Validate number range
   * @param {number} value - Value to validate
   * @param {number} min - Minimum value
   * @param {number} max - Maximum value
   * @returns {Object} Validation result
   */
  numberRange(value, min, max) {
    const num = parseFloat(value);
    const isValid = !isNaN(num) && num >= min && num <= max;
    
    return {
      valid: isValid,
      message: isValid ? '' : `Giá trị phải từ ${min} đến ${max}`,
    };
  },

  /**
   * Validate form data
   * @param {Object} formData - Form data to validate
   * @param {Object} rules - Validation rules
   * @returns {Object} Validation results
   */
  validateForm(formData, rules) {
    const errors = {};
    let isValid = true;

    for (const [field, validations] of Object.entries(rules)) {
      const value = formData[field];
      
      for (const validation of validations) {
        const result = validation(value);
        
        if (!result.valid) {
          errors[field] = result.message;
          isValid = false;
          break; // Stop at first error for this field
        }
      }
    }

    return {
      valid: isValid,
      errors,
    };
  },

  /**
   * Display validation errors on form
   * @param {Object} errors - Validation errors object
   * @param {HTMLFormElement} form - Form element
   */
  displayErrors(errors, form) {
    // Clear previous errors
    form.querySelectorAll('.error-message').forEach(el => el.remove());
    form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));

    // Display new errors
    for (const [field, message] of Object.entries(errors)) {
      const input = form.querySelector(`[name="${field}"]`);
      if (input) {
        input.classList.add('error');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        errorDiv.style.color = 'var(--danger, #ef4444)';
        errorDiv.style.fontSize = '0.85rem';
        errorDiv.style.marginTop = '0.25rem';
        
        input.parentElement.appendChild(errorDiv);
      }
    }
  },

  /**
   * Clear validation errors from form
   * @param {HTMLFormElement} form - Form element
   */
  clearErrors(form) {
    form.querySelectorAll('.error-message').forEach(el => el.remove());
    form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
  },
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Validators;
}
