// Dashboard functionality for DirectAdmin Email Forwarder
let currentForwarders = [];
let emailAccounts = [];
let availableDomains = [];
let selectedDomain = null;

// Generate a random string for email alias (12-18 characters)
function generateRandomAlias() {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    const length = Math.floor(Math.random() * 7) + 12; // Random length between 12 and 18
    let randomString = '';
    
    for (let i = 0; i < length; i++) {
        randomString += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    
    const aliasInput = document.getElementById('alias');
    if (aliasInput) {
        aliasInput.value = randomString;
    }
}

// Escape a string for HTML insertion (prevents XSS)
function escapeHTML(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

// Helper function to validate destinations (including special ones)
function isValidDestination(destination) {
    // Allow special destinations
    if (destination.startsWith(':') || destination.startsWith('|')) {
        return true;
    }

    // Otherwise check if it's a valid email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(destination);
}

// Load available domains
async function loadDomains() {
    try {
        const response = await fetch('/api/domains');
        const data = await response.json();

        if (response.ok && data.domains) {
            availableDomains = data.domains;
            
            // Set selected domain to first domain if not set
            if (!selectedDomain && availableDomains.length > 0) {
                selectedDomain = availableDomains[0];
            }
            
            updateDomainSelector();
            updateDomainSuffix();
            
            // Load data for selected domain
            if (selectedDomain) {
                await loadEmailAccounts();
                await loadForwarders();
            }
        } else {
            console.error('Failed to load domains:', data.error);
            showMessage('Failed to load domains', 'error');
        }
    } catch (error) {
        console.error('Error loading domains:', error);
        showMessage('Error loading domains', 'error');
    }
}

// Update domain selector dropdown
function updateDomainSelector() {
    const select = document.getElementById('domainSelect');
    if (!select) return;

    select.innerHTML = '';

    if (availableDomains.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No domains configured';
        option.disabled = true;
        option.selected = true;
        select.appendChild(option);
        return;
    }

    availableDomains.forEach(domain => {
        const option = document.createElement('option');
        option.value = domain;
        option.textContent = domain;
        option.selected = domain === selectedDomain;
        select.appendChild(option);
    });
}

// Update domain suffix in form
function updateDomainSuffix() {
    const suffix = document.getElementById('domainSuffix');
    if (suffix) {
        suffix.textContent = selectedDomain ? `@${selectedDomain}` : '@no-domain';
    }
}

// Switch to different domain
async function switchDomain() {
    const select = document.getElementById('domainSelect');
    if (!select) return;

    const newDomain = select.value;
    if (newDomain === selectedDomain) return;

    selectedDomain = newDomain;
    updateDomainSuffix();
    
    // Clear current data
    currentForwarders = [];
    emailAccounts = [];
    
    // Load new data
    if (selectedDomain) {
        await loadEmailAccounts();
        await loadForwarders();
    }
}

// Make switchDomain globally available
window.switchDomain = switchDomain;

// Load email accounts for destination dropdown
async function loadEmailAccounts() {
    if (!selectedDomain) {
        console.log('No domain selected, skipping email accounts load');
        return;
    }

    try {
        const response = await fetch(`/api/email-accounts?domain=${encodeURIComponent(selectedDomain)}`);
        const data = await response.json();

        if (response.ok && data.accounts) {
            emailAccounts = data.accounts;
            updateDestinationDropdown();
        } else {
            console.error('Failed to load email accounts:', data.error);
            if (response.status === 403) {
                showMessage(`Domain access denied: ${selectedDomain} may not be configured in your DirectAdmin account`, 'error');
            } else {
                showMessage(`Failed to load email accounts for ${selectedDomain}: ${data.error || 'Unknown error'}`, 'error');
            }
            
            // Clear dropdown on error
            updateDestinationDropdown();
        }
    } catch (error) {
        console.error('Error loading email accounts:', error);
        showMessage(`Error loading email accounts for ${selectedDomain}`, 'error');
        updateDestinationDropdown();
    }
}

// Update destination dropdown with email accounts AND custom option
function updateDestinationDropdown() {
    const select = document.getElementById('destination');
    if (!select) return;

    // Clear existing options
    select.innerHTML = '';

    // Add placeholder
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Select destination...';
    placeholder.disabled = true;
    placeholder.selected = true;
    select.appendChild(placeholder);

    // Add email account options
    if (emailAccounts.length > 0) {
        emailAccounts.forEach(email => {
            const option = document.createElement('option');
            option.value = email;
            option.textContent = email;
            select.appendChild(option);
        });
    }

    // Add separator
    const separator = document.createElement('option');
    separator.disabled = true;
    separator.textContent = '──────────────';
    select.appendChild(separator);

    // Add custom option
    const customOption = document.createElement('option');
    customOption.value = 'custom';
    customOption.textContent = 'Custom destination...';
    select.appendChild(customOption);

    // Add change event listener
    select.addEventListener('change', function() {
        const customInput = document.getElementById('custom-destination');
        if (!customInput) return;

        if (this.value === 'custom') {
            customInput.style.display = 'block';
            customInput.required = true;
            customInput.focus();
        } else {
            customInput.style.display = 'none';
            customInput.required = false;
            customInput.value = '';
        }
    });
}

// Load forwarders from API
async function loadForwarders() {
    const tbody = document.querySelector('#forwardersTable tbody');
    if (!tbody) return;

    if (!selectedDomain) {
        tbody.innerHTML = '<tr><td colspan="3" class="no-data">No domain selected</td></tr>';
        return;
    }

    try {
        const response = await fetch(`/api/forwarders?domain=${encodeURIComponent(selectedDomain)}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Forwarders response:', data);

        // Extract forwarders array from response
        if (data && Array.isArray(data.forwarders)) {
            currentForwarders = data.forwarders;
        } else {
            console.warn('Unexpected forwarders format:', data);
            currentForwarders = [];
        }

        displayForwarders();

    } catch (error) {
        console.error('Error loading forwarders:', error);
        
        if (error.response && error.response.status === 403) {
            tbody.innerHTML = '<tr><td colspan="3" class="error-message">Domain access denied: ' + escapeHTML(selectedDomain) + ' may not be configured in your DirectAdmin account.</td></tr>';
        } else {
            tbody.innerHTML = '<tr><td colspan="3" class="error-message">Failed to load forwarders for ' + escapeHTML(selectedDomain) + '. Please check your DirectAdmin settings.</td></tr>';
        }
    }
}

// Display forwarders in the table
function displayForwarders() {
    const tbody = document.querySelector('#forwardersTable tbody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (currentForwarders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="no-data">No email forwarders configured</td></tr>';
        return;
    }

    currentForwarders.forEach(forwarder => {
        const row = document.createElement('tr');

        // Create cells
        const fromCell = document.createElement('td');
        fromCell.textContent = forwarder.address || 'Unknown';

        const toCell = document.createElement('td');
        toCell.textContent = forwarder.destination || 'Unknown';

        const actionsCell = document.createElement('td');
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn-danger';
        deleteBtn.textContent = 'Delete';
        deleteBtn.onclick = () => deleteForwarder(forwarder.address);
        actionsCell.appendChild(deleteBtn);

        row.appendChild(fromCell);
        row.appendChild(toCell);
        row.appendChild(actionsCell);
        tbody.appendChild(row);
    });
}

// Create new forwarder
async function createForwarder(event) {
    event.preventDefault();

    const form = event.target;
    const addressInput = form.querySelector('#alias');
    const destinationSelect = form.querySelector('#destination');
    const customDestInput = form.querySelector('#custom-destination');
    const submitButton = form.querySelector('button[type="submit"]');

    // Validate alias
    if (!addressInput || !addressInput.value.trim()) {
        showMessage('Please enter an alias', 'error');
        return;
    }

    // Get the actual destination
    let destination;

    if (destinationSelect.value === 'custom') {
        // Using custom destination
        if (!customDestInput || !customDestInput.value.trim()) {
            showMessage('Please enter a custom destination', 'error');
            customDestInput.focus();
            return;
        }

        destination = customDestInput.value.trim();

        // Validate the destination
        if (!isValidDestination(destination)) {
            showMessage('Please enter a valid email address or special destination (e.g., :blackhole:, :fail:)', 'error');
            customDestInput.focus();
            return;
        }
    } else if (destinationSelect.value) {
        // Using existing email from dropdown
        destination = destinationSelect.value;
    } else {
        showMessage('Please select a destination', 'error');
        return;
    }

    // Disable form during submission
    submitButton.disabled = true;
    submitButton.textContent = 'Creating...';

    try {
        const response = await fetch('/api/forwarders', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                address: addressInput.value.trim(),
                destination: destination,
                domain: selectedDomain
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Clear form
            form.reset();

            // Hide custom input
            if (customDestInput) {
                customDestInput.style.display = 'none';
                customDestInput.required = false;
            }

            // Reload forwarders
            await loadForwarders();

            // Show success message
            showMessage(data.message || 'Forwarder created successfully', 'success');
        } else {
            showMessage(data.error || 'Failed to create forwarder', 'error');
        }
    } catch (error) {
        console.error('Error creating forwarder:', error);
        showMessage('Failed to create forwarder. Please try again.', 'error');
    } finally {
        // Re-enable form
        submitButton.disabled = false;
        submitButton.textContent = 'Create Forwarder';
    }
}

// Delete forwarder
async function deleteForwarder(address) {
    if (!address) {
        console.error('No address provided for deletion');
        return;
    }

    if (!confirm(`Are you sure you want to delete the forwarder for ${address}?`)) {
        return;
    }

    try {
        const response = await fetch('/api/forwarders', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                address: address,
                domain: selectedDomain
            })
        });

        const data = await response.json();

        if (response.ok) {
            await loadForwarders();
            showMessage(data.message || 'Forwarder deleted successfully', 'success');
        } else {
            showMessage(data.error || 'Failed to delete forwarder', 'error');
        }
    } catch (error) {
        console.error('Error deleting forwarder:', error);
        showMessage('Failed to delete forwarder. Please try again.', 'error');
    }
}

// Show message to user
function showMessage(message, type = 'info') {
    const container = document.getElementById('messageContainer');
    if (!container) {
        console.error('Message container not found');
        return;
    }

    // Create message element
    const div = document.createElement('div');
    div.className = `alert alert-${type}`;
    div.textContent = message;

    // Add close button
    const closeBtn = document.createElement('span');
    closeBtn.innerHTML = '&times;';
    closeBtn.style.float = 'right';
    closeBtn.style.cursor = 'pointer';
    closeBtn.style.marginLeft = '15px';
    closeBtn.onclick = () => div.remove();
    div.appendChild(closeBtn);

    // Clear existing messages and add new one
    container.innerHTML = '';
    container.appendChild(div);

    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (div.parentNode) {
            div.remove();
        }
    }, 5000);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard JS loaded');

    // Check if we're on the dashboard page
    const forwardersTable = document.getElementById('forwardersTable');
    if (!forwardersTable) {
        console.log('Not on dashboard page, skipping initialization');
        return;
    }

    console.log('Initializing dashboard...');

    // Load initial data
    loadDomains();

    // Set up auto-refresh every 60 seconds
    setInterval(() => {
        if (selectedDomain) {
            loadForwarders();
        }
    }, 60000);

    // Set up form handler
    const form = document.getElementById('createForwarderForm');
    if (form) {
        form.addEventListener('submit', createForwarder);
    } else {
        console.error('Create forwarder form not found');
    }

});

// Utility function to escape HTML (prevent XSS)
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
