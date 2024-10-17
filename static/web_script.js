// Select DOM elements
const inputField = document.getElementById('user-text');
const attributeSelect = document.getElementById('attribute');
const attributeValueInput = document.getElementById('attribute-value');
const notification = document.getElementById('notification');
const copyButton = document.getElementById('copy-button');
const themeToggle = document.getElementById('theme-toggle');
const form = document.getElementById('attribute-form');
const textOutput = document.getElementById('text-output');

// Error message elements
const attributeError = document.getElementById('attribute-error');
const attributeValueError = document.getElementById('attribute-value-error');
const userTextError = document.getElementById('user-text-error');

/**
 * Validates the attribute selection and its value.
 * @returns {boolean} True if valid, false otherwise.
 */
function validateAttributeForm() {
    let isValid = true;

    // Validate attribute selection
    if (!attributeSelect.value) {
        attributeError.style.display = 'block';
        isValid = false;
    } else {
        attributeError.style.display = 'none';
    }

    // Validate attribute value input
    if (!attributeValueInput.value.trim()) {
        attributeValueError.style.display = 'block';
        isValid = false;
    } else {
        attributeValueError.style.display = 'none';
    }

    return isValid;
}

/**
 * Validates the user text input.
 * @returns {boolean} True if valid, false otherwise.
 */
function validateTextForm() {
    let isValid = true;

    // Validate user text input
    if (!inputField.value.trim()) {
        userTextError.style.display = 'block';
        isValid = false;
    } else {
        userTextError.style.display = 'none';
    }

    return isValid;
}

/**
 * Applies the selected attribute to the input field.
 */
function applyAttribute() {
    // Validate attribute fields only
    if (!validateAttributeForm()) return;

    // Hide user text error if previously shown
    userTextError.style.display = 'none';

    const attribute = attributeSelect.value;
    const value = attributeValueInput.value.trim();

    // Apply the attribute to the input field
    if (attribute === 'id') {
        inputField.id = value;  // Set the ID
    } else if (attribute === 'class') {
        inputField.className = value;  // Set the class
    }

    // Show success notification
    showNotification(`Successfully set ${attribute.toUpperCase()} to "${value}" for the text input field!`);
}

/**
 * Displays the entered text in the output area.
 */
function displayText() {
    // Validate user text input only
    if (!validateTextForm()) return;

    // Hide attribute-related errors if previously shown
    attributeError.style.display = 'none';
    attributeValueError.style.display = 'none';

    const userText = inputField.value.trim();
    textOutput.textContent = userText;

    // Show success notification
    showNotification('Text displayed successfully!');
}

/**
 * Clears the output area.
 */
function clearOutput() {
    textOutput.textContent = 'Your text will appear here...';
    showNotification('Output cleared.');
}

/**
 * Resets the form and hides all error messages.
 */
function resetForm() {
    form.reset();
    inputField.id = '';
    inputField.className = '';
    clearOutput();

    // Hide all error messages
    attributeError.style.display = 'none';
    attributeValueError.style.display = 'none';
    userTextError.style.display = 'none';

    showNotification('Form has been reset.');
}

/**
 * Shows a notification with the given message and type.
 * @param {string} message - The message to display.
 * @param {string} [type='success'] - The type of notification ('success' or 'error').
 */
function showNotification(message, type = 'success') {
    if (type === 'error') {
        notification.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
        notification.style.backgroundColor = 'rgba(255, 107, 107, 0.8)';
    } else {
        // Reset to default based on theme
        if (document.body.classList.contains('dark-mode')) {
            notification.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
        } else {
            notification.style.backgroundColor = 'rgba(0, 0, 0, 0.2)';
        }
        notification.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
    }

    notification.classList.add('show');

    // Hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

/**
 * Copies the text from the output area to the clipboard.
 */
function copyText() {
    const text = textOutput.textContent;
    if (!text || text === 'Your text will appear here...') {
        showNotification('Nothing to copy!', 'error');
        return;
    }
    navigator.clipboard.writeText(text)
        .then(() => showNotification('Text copied to clipboard!'))
        .catch(() => showNotification('Failed to copy text.', 'error'));
}

/**
 * Toggles between dark mode and light mode.
 */
function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    // Save user preference to localStorage
    if (document.body.classList.contains('dark-mode')) {
        localStorage.setItem('theme', 'dark');
        showNotification('Switched to Dark Mode');
    } else {
        localStorage.setItem('theme', 'light');
        showNotification('Switched to Light Mode');
    }
}

// Event Listener for Theme Toggle Switch
themeToggle.addEventListener('change', toggleTheme);

/**
 * Loads the saved theme preference from localStorage.
 */
function loadTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        themeToggle.checked = true;
    } else {
        document.body.classList.remove('dark-mode');
        themeToggle.checked = false;
    }
}

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', loadTheme);
