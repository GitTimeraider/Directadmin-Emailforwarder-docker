// Load current settings on page load
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/settings/api/da-config');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const config = await response.json();
        console.log('Loaded config:', config);

        if (config.da_server) document.getElementById('da_server').value = config.da_server;
        if (config.da_username) document.getElementById('da_username').value = config.da_username;
        if (config.da_domain) document.getElementById('da_domain').value = config.da_domain;

        if (config.has_password) {
            document.getElementById('da_password').placeholder = 'Password is set (leave empty to keep current)';
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
});

// Handle form submission - SAVE WITHOUT TESTING
document.getElementById('daConfigForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const saveButton = e.target.querySelector('button[type="submit"]');
    const originalText = saveButton.textContent;
    saveButton.textContent = 'Saving...';
    saveButton.disabled = true;

    const formData = {
        da_server: document.getElementById('da_server').value.trim(),
        da_username: document.getElementById('da_username').value.trim(),
        da_password: document.getElementById('da_password').value,
        da_domain: document.getElementById('da_domain').value.trim()
    };

    console.log('Submitting settings (no connection test):', { ...formData, da_password: '***' });

    try {
        const response = await fetch('/settings/api/da-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        console.log('Save response:', result);

        if (response.ok && result.success) {
            // Show success message
            showMessage('success', result.message || 'Settings saved successfully!');

            // Clear password field
            document.getElementById('da_password').value = '';
            document.getElementById('da_password').placeholder = 'Password is set (leave empty to keep current)';

            // Optional: Redirect after a delay
            setTimeout(() => {
                if (confirm('Settings saved! Go to dashboard now?')) {
                    window.location.href = '/dashboard';
                }
            }, 1000);
        } else {
            showMessage('error', result.error || 'Failed to save settings');

            // Highlight missing fields if any
            if (result.missing_fields) {
                result.missing_fields.forEach(field => {
                    document.getElementById(field).classList.add('error');
                });
            }
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showMessage('error', 'Error saving settings: ' + error.message);
    } finally {
        saveButton.textContent = originalText;
        saveButton.disabled = false;
    }
});

// Test connection function - COMPLETELY SEPARATE
async function testConnection() {
    const testButton = event.target;
    const originalText = testButton.textContent;
    testButton.textContent = 'Testing...';
    testButton.disabled = true;

    const formData = {
        da_server: document.getElementById('da_server').value.trim(),
        da_username: document.getElementById('da_username').value.trim(),
        da_password: document.getElementById('da_password').value,
        da_domain: document.getElementById('da_domain').value.trim()
    };

    if (!formData.da_server || !formData.da_username) {
        showMessage('warning', 'Please enter server URL and username to test');
        testButton.textContent = originalText;
        testButton.disabled = false;
        return;
    }

    console.log('Testing connection to:', formData.da_server);

    try {
        const response = await fetch('/settings/api/test-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        console.log('Test response:', result);

        if (result.success) {
            showMessage('success', '✓ ' + result.message);
        } else {
            showMessage('warning', '✗ Connection failed: ' + (result.error || 'Unknown error') + '\nYou can still save these settings.');
        }
    } catch (error) {
        console.error('Error testing connection:', error);
        showMessage('error', '✗ Test error: ' + error.message + '\nYou can still save these settings.');
    } finally {
        testButton.textContent = originalText;
        testButton.disabled = false;
    }
}

// Helper function to show messages
function showMessage(type, message) {
    // Remove any existing messages
    const existingMsg = document.querySelector('.message');
    if (existingMsg) existingMsg.remove();

    const msgDiv = document.createElement('div');
    msgDiv.className = `message message-${type}`;
    msgDiv.textContent = message;

    // Insert after form title
    const formTitle = document.querySelector('h2');
    formTitle.parentNode.insertBefore(msgDiv, formTitle.nextSibling);

    // Auto-remove after 5 seconds
    setTimeout(() => msgDiv.remove(), 5000);
}

// Remove error class on input
document.querySelectorAll('input').forEach(input => {
    input.addEventListener('input', () => {
        input.classList.remove('error');
    });
});
