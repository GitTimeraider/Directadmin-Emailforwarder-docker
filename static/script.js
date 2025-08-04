let refreshInterval;

async function loadEmailAccounts() {
    try {
        const response = await fetch('/api/email-accounts');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const accounts = await response.json();
        const select = document.getElementById('destination');

        if (accounts.error) {
            select.innerHTML = '<option value="">Error loading accounts</option>';
            console.error('API Error:', accounts.error);
            return;
        }

        // Clear and rebuild options
        select.innerHTML = '<option value="">Select destination</option>';

        // Add email accounts from DirectAdmin
        if (accounts.length > 0) {
            const optgroup = document.createElement('optgroup');
            optgroup.label = 'Email Accounts';
            accounts.forEach(email => {
                const option = document.createElement('option');
                option.value = email;
                option.textContent = email;
                optgroup.appendChild(option);
            });
            select.appendChild(optgroup);
        }

        // Add custom email option
        const customOption = document.createElement('option');
        customOption.value = 'custom';
        customOption.textContent = '➕ Custom Email Address...';
        select.appendChild(customOption);

    } catch (error) {
        console.error('Error loading email accounts:', error);
        document.getElementById('destination').innerHTML = '<option value="">Error loading accounts</option>';
    }
}

function toggleCustomEmail() {
    const select = document.getElementById('destination');
    const customGroup = document.getElementById('customEmailGroup');
    const customInput = document.getElementById('customEmail');

    if (select.value === 'custom') {
        customGroup.style.display = 'block';
        customInput.required = true;
        customInput.focus();
    } else {
        customGroup.style.display = 'none';
        customInput.required = false;
        customInput.value = '';
    }
}

async function loadForwarders() {
    try {
        const response = await fetch('/api/forwarders');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const forwarders = await response.json();
        const list = document.getElementById('forwardersList');

        if (forwarders.error) {
            list.innerHTML = '<p class="error">Error loading forwarders: ' + forwarders.error + '</p>';
            return;
        }

        if (forwarders.length === 0) {
            list.innerHTML = '<p class="no-forwarders">No forwarders configured</p>';
            return;
        }

        // Create formatted list of forwarders
        list.innerHTML = forwarders.map(f => `
            <div class="forwarder-item">
                <div class="forwarder-info">
                    <span class="forwarder-alias">${f.alias}</span>
                    <span class="forwarder-arrow">→</span>
                    <div class="forwarder-destinations">
                        ${f.destinations.map(dest => `<span class="destination-tag">${dest}</span>`).join('')}
                    </div>
                </div>
                <button class="delete-btn" onclick="deleteForwarder('${f.alias}')">Delete</button>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading forwarders:', error);
        document.getElementById('forwardersList').innerHTML = '<p class="error">Error loading forwarders</p>';
    }
}

async function deleteForwarder(alias) {
    if (!confirm(`Are you sure you want to delete the forwarder "${alias}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/forwarders/${encodeURIComponent(alias)}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadForwarders();
        } else {
            alert('Failed to delete forwarder');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error deleting forwarder');
    }
}

document.getElementById('createForwarderForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const alias = document.getElementById('alias').value;
    const destinationSelect = document.getElementById('destination').value;
    let destination;

    // Check if custom email is selected
    if (destinationSelect === 'custom') {
        destination = document.getElementById('customEmail').value;
        if (!destination) {
            alert('Please enter a custom email address');
            return;
        }
    } else {
        destination = destinationSelect;
    }

    if (!destination) {
        alert('Please select or enter a destination email');
        return;
    }

    try {
        const response = await fetch('/api/forwarders', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ alias, destination })
        });

        if (response.ok) {
            document.getElementById('createForwarderForm').reset();
            document.getElementById('customEmailGroup').style.display = 'none';
            loadForwarders();
        } else {
            alert('Failed to create forwarder');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error creating forwarder');
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadEmailAccounts();
    loadForwarders();

    // Refresh forwarders every 60 seconds
    refreshInterval = setInterval(loadForwarders, 60000);
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});
