// Dashboard functionality for DirectAdmin Email Forwarder
let currentForwarders = [];
let emailAccounts = [];

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

// Load email accounts for destination dropdown
async function loadEmailAccounts() {
    try {
        const response = await fetch('/api/email-accounts');
        const data = await response.json();

        if (response.ok && data.accounts) {
            emailAccounts = data.accounts;
            updateDestinationDropdown();
        } else {
            console.error('Failed to load email accounts:', data.error);
            showMessage('Failed to load email accounts', 'error');
        }
    } catch (error) {
        console.error('Error loading email accounts:', error);
    }
}

// Update destination dropdown with email accounts
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

    // Handle destination type radio buttons (if they exist)
    const radioButtons = document.querySelectorAll('input[name="destination_type"]');
    radioButtons.forEach(radio => {
        radio.addEventListener('change', function() {
            updateDestinationVisibility();
        });
    });

    // Initial visibility update
    updateDestinationVisibility();
}

// Update visibility based on destination type selection
function updateDestinationVisibility() {
    const destinationType = document.querySelector('input[name="destination_type"]:checked');
    const destSelect = document.getElementById('destination');
    const customGroup = document.getElementById('custom-destination-group');
    const customInput = document.getElementById('custom-destination'); // FIXED: Using kebab-case

    if (!destinationType) return;

    const isCustom = destinationType.value === 'custom';

    // Handle destination select
    if (destSelect) {
        destSelect.style.display = isCustom ? 'none' : 'block';
        destSelect.required = !isCustom;
    }

    // Handle custom destination group
    if (customGroup) {
        customGroup.style.display = isCustom ? 'block' : 'none';
    }

    // Handle custom destination input
    if (customInput) {
        customInput.required = isCustom;
        if (!isCustom) {
            customInput.value = '';
        }
    }
}

// Load forwarders from API
async function loadForwarders() {
    const tbody = document.querySelector('#forwardersTable tbody');
    if (!tbody) return;

    try {
        const response = await fetch('/api/forwarders');

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
        tbody.innerHTML = '<tr><td colspan="3" class="error-message">Failed to load forwarders. Please check your DirectAdmin settings.</td></tr>';
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
        deleteBtn.className = 'btn-danger btn-sm';
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
    const addressInput = form.querySelector('#alias'); // FIXED: Changed from #address to #alias
    const destinationType = document.querySelector('input[name="destination_type"]:checked');
    const destinationSelect = form.querySelector('#destination');
    const customDestInput = form.querySelector('#custom-destination'); // FIXED: Using kebab-case
    const submitButton = form.querySelector('button[type="submit"]');

    // Get the actual destination
    let destination;

    if (destinationType && destinationType.value === 'custom') {
        // Using custom destination
        if (!customDestInput || !customDestInput.value.trim()) {
            showMessage('Please enter a custom destination', 'error');
            if (customDestInput) customDestInput.focus();
            return;
        }

        destination = customDestInput.value.trim();

        // Validate the destination
        if (!isValidDestination(destination)) {
            showMessage('Please enter a valid email address or special destination (e.g., :blackhole:, :fail:, |/path/to/script)', 'error');
            customDestInput.focus();
            return;
        }
    } else {
        // Using existing email from dropdown
        if (!destinationSelect || !destinationSelect.value) {
            showMessage('Please select a destination email', 'error');
            return;
        }
        destination = destinationSelect.value;
    }

    // Validate alias
    if (!addressInput || !addressInput.value.trim()) {
        showMessage('Please enter an alias', 'error');
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
                destination: destination
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Clear form
            form.reset();

            // Reset visibility
            updateDestinationVisibility();

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
                address: address
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
    loadEmailAccounts();
    loadForwarders();

    // Set up auto-refresh every 60 seconds
    setInterval(loadForwarders, 60000);

    // Set up form handler
    const form = document.getElementById('createForwarderForm');
    if (form) {
        form.addEventListener('submit', createForwarder);
    } else {
        console.error('Create forwarder form not found');
    }

    // Set up manual refresh button (if you want one)
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadForwarders();
            showMessage('Forwarders refreshed', 'info');
        });
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
