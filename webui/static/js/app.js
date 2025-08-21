// VNBdigitaler WebUI JavaScript Utilities

/**
 * Global utility functions for the VNBdigitaler WebUI
 */

// Global variables
let currentMessages = [];
let messageTimeout = null;

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', function () {
    initializeTooltips();
    initializeMessageSystem();
    initializeTableEnhancements();
    initializeFormValidation();
});

/**
 * API request helper function
 */
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    };

    const config = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    try {
        const response = await fetch(url, config);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        } else {
            return await response.text();
        }
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

/**
 * Show a message to the user
 */
function showMessage(message, type = 'info', duration = 5000) {
    const messageContainer = getOrCreateMessageContainer();

    const messageId = 'message-' + Date.now();
    const alertClass = `alert-${type}`;
    const iconClass = getMessageIcon(type);

    const messageElement = document.createElement('div');
    messageElement.id = messageId;
    messageElement.className = `alert ${alertClass} alert-dismissible fade show slide-in`;
    messageElement.innerHTML = `
        <i class="${iconClass} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    messageContainer.appendChild(messageElement);
    currentMessages.push(messageId);

    // Auto-dismiss after duration
    if (duration > 0) {
        setTimeout(() => {
            dismissMessage(messageId);
        }, duration);
    }

    return messageId;
}

/**
 * Dismiss a specific message
 */
function dismissMessage(messageId) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        messageElement.remove();
        currentMessages = currentMessages.filter(id => id !== messageId);
    }
}

/**
 * Clear all messages
 */
function clearMessages() {
    currentMessages.forEach(messageId => {
        dismissMessage(messageId);
    });
}

/**
 * Get or create the message container
 */
function getOrCreateMessageContainer() {
    let container = document.getElementById('message-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'message-container';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    return container;
}

/**
 * Get icon class for message type
 */
function getMessageIcon(type) {
    const icons = {
        'success': 'fas fa-check-circle',
        'warning': 'fas fa-exclamation-triangle',
        'danger': 'fas fa-times-circle',
        'info': 'fas fa-info-circle',
        'primary': 'fas fa-bell'
    };
    return icons[type] || icons['info'];
}

/**
 * Show loading indicator
 */
function showLoading(element, text = 'Loading...') {
    if (element) {
        element.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="spinner-border spinner-border-sm me-2" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                ${text}
            </div>
        `;
        element.style.display = 'block';
    }
}

/**
 * Hide loading indicator
 */
function hideLoading(element) {
    if (element) {
        element.style.display = 'none';
    }
}

/**
 * Format number with locale
 */
function formatNumber(number, locale = 'de-DE') {
    return new Intl.NumberFormat(locale).format(number);
}

/**
 * Format date with locale
 */
function formatDate(date, locale = 'de-DE', options = {}) {
    const defaultOptions = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    };

    return new Intl.DateTimeFormat(locale, { ...defaultOptions, ...options }).format(new Date(date));
}

/**
 * Format datetime with locale
 */
function formatDateTime(date, locale = 'de-DE') {
    return formatDate(date, locale, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Debounce function
 */
function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

/**
 * Throttle function
 */
function throttle(func, delay) {
    let timeoutId;
    let lastExecTime = 0;
    return function (...args) {
        const currentTime = Date.now();

        if (currentTime - lastExecTime > delay) {
            func.apply(this, args);
            lastExecTime = currentTime;
        } else {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                func.apply(this, args);
                lastExecTime = Date.now();
            }, delay - (currentTime - lastExecTime));
        }
    };
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

/**
 * Initialize message system
 */
function initializeMessageSystem() {
    // Create message container if it doesn't exist
    getOrCreateMessageContainer();

    // Listen for flash messages from server
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        const type = message.dataset.type || 'info';
        const text = message.textContent.trim();
        if (text) {
            showMessage(text, type);
        }
        message.remove();
    });
}

/**
 * Initialize table enhancements
 */
function initializeTableEnhancements() {
    // Add row click handlers for tables with data-clickable="true"
    const clickableTables = document.querySelectorAll('table[data-clickable="true"]');
    clickableTables.forEach(table => {
        const rows = table.querySelectorAll('tbody tr[data-href]');
        rows.forEach(row => {
            row.style.cursor = 'pointer';
            row.addEventListener('click', function () {
                const href = this.dataset.href;
                if (href) {
                    window.location.href = href;
                }
            });
        });
    });

    // Add sorting indicators
    const sortableHeaders = document.querySelectorAll('th[data-sortable="true"]');
    sortableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.innerHTML += ' <i class="fas fa-sort text-muted"></i>';

        header.addEventListener('click', function () {
            const column = this.dataset.column;
            const currentSort = new URLSearchParams(window.location.search).get('sort');
            const currentOrder = new URLSearchParams(window.location.search).get('order');

            let newOrder = 'asc';
            if (currentSort === column && currentOrder === 'asc') {
                newOrder = 'desc';
            }

            const url = new URL(window.location);
            url.searchParams.set('sort', column);
            url.searchParams.set('order', newOrder);
            url.searchParams.set('page', '1');

            window.location.href = url.toString();
        });
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');

    forms.forEach(form => {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();

                // Find first invalid field and focus it
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }

                showMessage('Please correct the errors in the form.', 'warning');
            }

            form.classList.add('was-validated');
        });
    });
}

/**
 * Confirm dialog helper
 */
function confirmAction(message, callback, options = {}) {
    const defaultOptions = {
        title: 'Confirm Action',
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        type: 'warning'
    };

    const config = { ...defaultOptions, ...options };

    // For now, use simple confirm dialog
    // In a full implementation, you might want to use a modal
    if (confirm(`${config.title}\n\n${message}`)) {
        callback();
    }
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text, successMessage = 'Copied to clipboard!') {
    try {
        await navigator.clipboard.writeText(text);
        showMessage(successMessage, 'success', 2000);
    } catch (err) {
        console.error('Failed to copy to clipboard:', err);
        showMessage('Failed to copy to clipboard', 'danger', 3000);
    }
}

/**
 * Download data as file
 */
function downloadData(data, filename, type = 'application/json') {
    const blob = new Blob([data], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * Pagination helper
 */
function goToPage(page) {
    const url = new URL(window.location);
    url.searchParams.set('page', page);
    window.location.href = url.toString();
}

/**
 * Search helper
 */
function performSearch(query, immediate = false) {
    const url = new URL(window.location);
    url.searchParams.set('search', query);
    url.searchParams.set('page', '1');

    if (immediate) {
        window.location.href = url.toString();
    } else {
        // Use debounced search for better UX
        if (window.searchTimeout) {
            clearTimeout(window.searchTimeout);
        }

        window.searchTimeout = setTimeout(() => {
            window.location.href = url.toString();
        }, 500);
    }
}

/**
 * Filter helper
 */
function applyFilter(filterName, filterValue) {
    const url = new URL(window.location);

    if (filterValue && filterValue !== '') {
        url.searchParams.set(filterName, filterValue);
    } else {
        url.searchParams.delete(filterName);
    }

    url.searchParams.set('page', '1');
    window.location.href = url.toString();
}

/**
 * Export current view as CSV
 */
async function exportAsCsv(endpoint = null) {
    try {
        showMessage('Preparing export...', 'info');

        const url = endpoint || (window.location.pathname + '/export');
        const params = new URLSearchParams(window.location.search);
        params.set('format', 'csv');

        const response = await apiRequest(`${url}?${params.toString()}`);

        const filename = `export_${new Date().toISOString().split('T')[0]}.csv`;
        downloadData(response, filename, 'text/csv');

        showMessage('Export completed successfully!', 'success');

    } catch (error) {
        console.error('Export failed:', error);
        showMessage(`Export failed: ${error.message}`, 'danger');
    }
}

// Export global functions for use in templates
window.VNB = {
    apiRequest,
    showMessage,
    dismissMessage,
    clearMessages,
    showLoading,
    hideLoading,
    formatNumber,
    formatDate,
    formatDateTime,
    debounce,
    throttle,
    confirmAction,
    copyToClipboard,
    downloadData,
    goToPage,
    performSearch,
    applyFilter,
    exportAsCsv
};
