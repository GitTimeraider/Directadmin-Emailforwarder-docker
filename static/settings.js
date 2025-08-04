// Helper function to safely parse JSON
async function parseResponse(response) {
    const text = await response.text();
    try {
        return JSON.parse(text);
    } catch (e) {
        console.error('Response is not JSON:', text);
        throw new Error('Server returned invalid response (not JSON)');
    }
}

// Load current settings on page load
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/settings/api/da-config');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const config = await parseResponse(response);
        console.log('Loaded config:', config);

        if (config.da_server) document.getElementById('da_server').value = config.da_server;
        if (config.da_username) document.getElementById('da_username').value = config.da_username;
        if (config.da_domain) document.getElementById('da_domain').value = config.da_domain;

        if (config.has_password) {
            document.getElementById('da_password').placeholder = 'Password is set (leave empty to keep current)';
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        if (error.message.includes('not JSON')) {
            alert('Session expired. Please login again.');
            window.location.href = '/login';
        }
    }
});

// Handle form submission
document.getElementById('daConfigForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        da_server: document.getElementById('da_server').value.trim(),
        da_username: document.getElementById('da_username').value.trim(),
        da_password: document.getElementById('da_password').value,
        da_domain: document.getElementById('da_domain').value.trim()
    };

    console.log('Submitting settings:', { ...formData, da_password: '***' });

    try {
        const response = await fetch('/settings/api/da-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',  // Important for cookies!
            body: JSON.stringify(formData)
        });

        const result = await parseResponse(response);
        console.log('Save response:', result);

        if (response.ok && result.success) {
            alert('Settings saved successfully!');
            document.getElementById('da_password').value = '';
            document.getElementById('da_password').placeholder = 'Password is set (leave empty to keep current)';

            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1000);
        } else {
            console.error('Save failed:', result);
            alert(result.error || 'Failed to save settings');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        alert('Error saving settings: ' + error.message);
    }
});

// Test connection function
async function testConnection() {
    const formData = {
        da_server: document.getElementById('da_server').value.trim(),
        da_username: document.getElementById('da_username').value.trim(),
        da_password: document.getElementById('da_password').value
    };

    if (!formData.da_server || !formData.da_username) {
        alert('Please enter server URL and username');
        return;
    }

    // Ensure URL has protocol
    if (!formData.da_server.startsWith('http://') && !formData.da_server.startsWith('https://')) {
        formData.da_server = 'https://' + formData.da_server;
        document.getElementById('da_server').value = formData.da_server;
    }

    if (!formData.da_password && !confirm('No password entered. Test with saved password?')) {
        return;
    }

    console.log('Testing connection to:', formData.da_server);

    // Show loading state
    const originalText = event.target.textContent;
    event.target.textContent = 'Testing...';
    event.target.disabled = true;

    try {
        const response = await fetch('/settings/api/test-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',  // Important!
            body: JSON.stringify(formData)
        });

        const result = await parseResponse(response);
        console.log('Test response:', result);

        if (response.ok && result.success) {
            alert('✓ ' + result.message);
        } else {
            alert('✗ Connection failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error testing connection:', error);
        alert('✗ Connection test failed: ' + error.message);
    } finally {
        // Restore button state
        event.target.textContent = originalText;
        event.target.disabled = false;
    }
}
