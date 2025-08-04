let refreshInterval;

async function loadEmailAccounts() {
    try {
        const response = await fetch('/api/email-accounts');
        const accounts = await response.json();
        const select = document.getElementById('destination');

        select.innerHTML = '<option value="">Select destination email</option>';
        accounts.forEach(email => {
            const option = document.createElement('option');
            option.value = email;
            option.textContent = email;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading email accounts:', error);
    }
}

async function loadForwarders() {
    try {
        const response = await fetch('/api/forwarders');
        const forwarders = await response.json();
        const list = document.getElementById('forwardersList');

        if (forwarders.length === 0) {
            list.innerHTML = '<p>No forwarders configured</p>';
            return;
        }

        list.innerHTML = forwarders.map(f => `
            <div class="forwarder-item">
                <div>
                    <strong>${f.alias}</strong> → ${f.destinations.join(', ')}
                </div>
                <button class="delete-btn" onclick="deleteForwarder('${f.alias}')">Delete</button>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading forwarders:', error);
    }
}

async function createForwarder(event) {
    event.preventDefault();

    const alias = document.getElementById('alias').value;
    const destination = document.getElementById('destination').value;

    try {
        const response = await fetch('/api/forwarders', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ alias, destination })
        });

        const result = await response.json();
        if (result.success) {
            document.getElementById('createForwarderForm').reset();
            loadForwarders();
        } else {
            alert('Failed to create forwarder');
        }
    } catch (error) {
        console.error('Error creating forwarder:', error);
        alert('Error creating forwarder');
    }
}

async function deleteForwarder(alias) {
    if (!confirm(`Delete forwarder ${alias}?`)) return;

    try {
        const response = await fetch(`/api/forwarders/${alias}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        if (result.success) {
            loadForwarders();
        } else {
            alert('Failed to delete forwarder');
        }
    } catch (error) {
        console.error('Error deleting forwarder:', error);
        alert('Error deleting forwarder');
    }
}

async function toggle2FA() {
    const action = confirm('Toggle 2FA status?');
    if (!action) return;

    try {
        const response = await fetch('/setup-2fa', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'enable=true'
        });

        if (response.redirected) {
            window.location.reload();
        } else {
            const data = await response.json();
            if (data.qr_code) {
                document.getElementById('qrCode').innerHTML = 
                    `<img src="data:image/png;base64,${data.qr_code}" alt="QR Code">`;
                document.getElementById('totpSecret').textContent = data.secret;
                document.getElementById('qrModal').style.display = 'flex';
            }
        }
    } catch (error) {
        console.error('Error toggling 2FA:', error);
    }
}

function closeModal() {
    document.getElementById('qrModal').style.display = 'none';
    window.location.reload();
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('createForwarderForm')) {
        document.getElementById('createForwarderForm').addEventListener('submit', createForwarder);
        loadEmailAccounts();
        loadForwarders();

        // Refresh every 60 seconds
        refreshInterval = setInterval(loadForwarders, 60000);
    }
});
