console.log('Settings page loaded');

let currentDomains = [];

// Load current settings and domains on page load
document.addEventListener('DOMContentLoaded', async () => {
    await loadSettings();
    await loadDomains();
});

async function loadSettings() {
    try {
        const response = await fetch('/settings/api/da-config');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const config = await response.json();
        console.log('Loaded config:', config);

        if (config.da_server) document.getElementById('da_server').value = config.da_server;
        if (config.da_username) document.getElementById('da_username').value = config.da_username;

        if (config.has_password) {
            document.getElementById('da_password').placeholder = 'Password is set (leave empty to keep current)';
        }

        // Load theme preference
        if (config.theme_preference) {
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) {
                themeToggle.checked = config.theme_preference === 'dark';
            }
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function loadDomains() {
    try {
        const response = await fetch('/settings/api/domains');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        if (result.success) {
            currentDomains = result.domains;
            renderDomains();
        }
    } catch (error) {
        console.error('Error loading domains:', error);
    }
}

// Form submission handler for DirectAdmin config
document.getElementById('daConfigForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const saveButton = e.target.querySelector('button[type="submit"]');
    const originalText = saveButton.textContent;
    saveButton.textContent = 'Saving...';
    saveButton.disabled = true;

    const formData = {
        da_server: document.getElementById('da_server').value.trim(),
        da_username: document.getElementById('da_username').value.trim(),
        da_password: document.getElementById('da_password').value
    };

    try {
        const response = await fetch('/settings/api/da-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showMessage('success', result.message || 'Settings saved successfully!');
            document.getElementById('da_password').value = '';
            document.getElementById('da_password').placeholder = 'Password is set (leave empty to keep current)';
        } else {
            showMessage('error', result.error || 'Failed to save settings');
            if (result.missing_fields) {
                result.missing_fields.forEach(field => {
                    const element = document.getElementById(field);
                    if (element) element.classList.add('error');
                });
            }
        }
    } catch (error) {
        console.error('Save error:', error);
        showMessage('error', 'Error saving settings: ' + error.message);
    } finally {
        saveButton.textContent = originalText;
        saveButton.disabled = false;
    }
});

// Domain management functions
function renderDomains() {
    const container = document.getElementById('domains-container');
    
    if (currentDomains.length === 0) {
        container.innerHTML = '<p class="no-domains">No domains configured. Add a domain above to get started.</p>';
        return;
    }

    const domainsList = currentDomains.map((domain, index) => `
        <div class="domain-item" data-domain="${domain}">
            <div class="domain-info">
                <span class="domain-name">${domain}</span>
                ${index === 0 ? '<span class="domain-badge">Default</span>' : ''}
            </div>
            <div class="domain-actions">
                ${index > 0 ? `<button type="button" onclick="moveDomainUp('${domain}')" class="btn-small">↑</button>` : ''}
                ${index < currentDomains.length - 1 ? `<button type="button" onclick="moveDomainDown('${domain}')" class="btn-small">↓</button>` : ''}
                <button type="button" onclick="removeDomain('${domain}')" class="btn-small btn-danger">Remove</button>
            </div>
        </div>
    `).join('');

    container.innerHTML = `<div class="domains-list-content">${domainsList}</div>`;
}

async function addDomain() {
    const input = document.getElementById('new_domain');
    const domain = input.value.trim();

    if (!domain) {
        showMessage('error', 'Please enter a domain name');
        return;
    }

    if (!domain.includes('.') || domain.includes(' ')) {
        showMessage('error', 'Please enter a valid domain name');
        return;
    }

    try {
        const response = await fetch('/settings/api/domains', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({ domain })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showMessage('success', result.message);
            currentDomains = result.domains;
            renderDomains();
            input.value = '';
        } else {
            showMessage('error', result.error || 'Failed to add domain');
        }
    } catch (error) {
        console.error('Error adding domain:', error);
        showMessage('error', 'Error adding domain: ' + error.message);
    }
}

async function removeDomain(domain) {
    if (!confirm(`Are you sure you want to remove the domain "${domain}"?`)) {
        return;
    }

    try {
        const response = await fetch('/settings/api/domains', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({ domain })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showMessage('success', result.message);
            currentDomains = result.domains;
            renderDomains();
        } else {
            showMessage('error', result.error || 'Failed to remove domain');
        }
    } catch (error) {
        console.error('Error removing domain:', error);
        showMessage('error', 'Error removing domain: ' + error.message);
    }
}

async function moveDomainUp(domain) {
    const index = currentDomains.indexOf(domain);
    if (index <= 0) return;

    const newOrder = [...currentDomains];
    [newOrder[index - 1], newOrder[index]] = [newOrder[index], newOrder[index - 1]];
    
    await reorderDomains(newOrder);
}

async function moveDomainDown(domain) {
    const index = currentDomains.indexOf(domain);
    if (index < 0 || index >= currentDomains.length - 1) return;

    const newOrder = [...currentDomains];
    [newOrder[index], newOrder[index + 1]] = [newOrder[index + 1], newOrder[index]];
    
    await reorderDomains(newOrder);
}

async function reorderDomains(newOrder) {
    try {
        const response = await fetch('/settings/api/domains/reorder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({ domains: newOrder })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            currentDomains = result.domains;
            renderDomains();
        } else {
            showMessage('error', result.error || 'Failed to reorder domains');
        }
    } catch (error) {
        console.error('Error reordering domains:', error);
        showMessage('error', 'Error reordering domains: ' + error.message);
    }
}

// Allow Enter key to add domain
document.getElementById('new_domain').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        addDomain();
    }
});


// Test connection function - COMPLETELY SEPARATE
async function testConnection(event) {
    console.log('testConnection called');
    const testButton = event.target;
    const originalText = testButton.textContent;
    
    // Ensure we always reset the button state
    const resetButton = () => {
        testButton.textContent = originalText;
        testButton.disabled = false;
    };
    
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
        resetButton();
        return;
    }

    console.log('Testing connection to:', formData.da_server);

    try {
        // Add timeout to prevent hanging
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            console.log('Connection test timeout reached, aborting...');
            controller.abort();
        }, 15000); // 15 second timeout for faster debugging

        const response = await fetch('/settings/api/test-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify(formData),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('Test response:', result);

        if (result.success) {
            showMessage('success', '✓ ' + result.message);
        } else {
            showMessage('warning', '✗ Connection failed: ' + (result.error || result.message || 'Unknown error') + '\nYou can still save these settings.');
        }
    } catch (error) {
        console.error('Error testing connection:', error);
        if (error.name === 'AbortError') {
            showMessage('error', '✗ Connection test timed out after 30 seconds. Please check your DirectAdmin server URL and network connection.');
        } else {
            showMessage('error', '✗ Test error: ' + error.message + '\nYou can still save these settings.');
        }
    } finally {
        resetButton();
        console.log('testConnection completed, button reset');
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
