// Load current settings on page load
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/settings/api/da-config');
        const config = await response.json();

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

// Handle form submission
document.getElementById('daConfigForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        da_server: document.getElementById('da_server').value,
        da_username: document.getElementById('da_username').value,
        da_password: document.getElementById('da_password').value,
        da_domain: document.getElementById('da_domain').value
    };

    try {
        const response = await fetch('/settings/api/da-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok) {
            alert('Settings saved successfully!');
            // Clear password field
            document.getElementById('da_password').value = '';
            document.getElementById('da_password').placeholder = 'Password is set (leave empty to keep current)';

            // Redirect to dashboard after successful save
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1000);
        } else {
            alert(result.error || 'Failed to save settings');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        alert('Error saving settings');
    }
});

// Test connection function
async function testConnection() {
    const formData = {
        da_server: document.getElementById('da_server').value,
        da_username: document.getElementById('da_username').value,
        da_password: document.getElementById('da_password').value
    };

    if (!formData.da_server || !formData.da_username) {
        alert('Please enter server URL and username');
        return;
    }

    if (!formData.da_password && !confirm('No password entered. Test with saved password?')) {
        return;
    }

    try {
        const response = await fetch('/settings/api/test-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok) {
            alert('✓ ' + result.message);
        } else {
            alert('✗ Connection failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error testing connection:', error);
        alert('✗ Connection test failed');
    }
}
