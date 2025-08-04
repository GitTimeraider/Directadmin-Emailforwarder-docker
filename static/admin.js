let currentEditUserId = null;

async function loadUsers() {
    try {
        const response = await fetch('/admin/api/users');
        const users = await response.json();
        const tbody = document.getElementById('usersList');

        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No users found</td></tr>';
            return;
        }

        tbody.innerHTML = users.map(user => `
            <tr>
                <td>${user.username}</td>
                <td>${user.is_admin ? '<span class="badge admin">Admin</span>' : '<span class="badge user">User</span>'}</td>
                <td>${user.totp_enabled ? '<span class="badge enabled">Enabled</span>' : '<span class="badge disabled">Disabled</span>'}</td>
                <td>${formatDate(user.created_at)}</td>
                <td>${user.last_login ? formatDate(user.last_login) : 'Never'}</td>
                <td class="actions">
                    <button onclick="editUser(${user.id})" class="btn-small">Edit</button>
                    <button onclick="deleteUser(${user.id}, '${user.username}')" class="btn-small delete-btn">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function showCreateUserModal() {
    document.getElementById('modalTitle').textContent = 'Create New User';
    document.getElementById('userForm').reset();
    document.getElementById('userId').value = '';
    document.getElementById('passwordHint').style.display = 'none';
    document.getElementById('reset2faGroup').style.display = 'none';
    document.getElementById('password').required = true;
    currentEditUserId = null;
    document.getElementById('userModal').style.display = 'flex';
}

async function editUser(userId) {
    const users = await fetch('/admin/api/users').then(r => r.json());
    const user = users.find(u => u.id === userId);

    if (!user) return;

    document.getElementById('modalTitle').textContent = 'Edit User';
    document.getElementById('userId').value = user.id;
    document.getElementById('username').value = user.username;
    document.getElementById('password').value = '';
    document.getElementById('password').required = false;
    document.getElementById('is_admin').checked = user.is_admin;
    document.getElementById('passwordHint').style.display = 'block';
    document.getElementById('reset2faGroup').style.display = user.totp_enabled ? 'block' : 'none';
    currentEditUserId = userId;
    document.getElementById('userModal').style.display = 'flex';
}

function closeUserModal() {
    document.getElementById('userModal').style.display = 'none';
    document.getElementById('userForm').reset();
}

async function generatePassword() {
    try {
        const response = await fetch(`/admin/api/users/0/generate-password`);
        const data = await response.json();
        document.getElementById('password').value = data.password;
        document.getElementById('password').type = 'text';
    } catch (error) {
        console.error('Error generating password:', error);
    }
}

function togglePasswordVisibility() {
    const passwordInput = document.getElementById('password');
    passwordInput.type = passwordInput.type === 'password' ? 'text' : 'password';
}

document.getElementById('userForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        username: document.getElementById('username').value,
        is_admin: document.getElementById('is_admin').checked
    };

    const password = document.getElementById('password').value;
    if (password) {
        formData.password = password;
    }

    if (currentEditUserId) {
        formData.reset_2fa = document.getElementById('reset_2fa').checked;
    }

    try {
        const url = currentEditUserId 
            ? `/admin/api/users/${currentEditUserId}`
            : '/admin/api/users';

        const method = currentEditUserId ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok) {
            closeUserModal();
            loadUsers();
        } else {
            alert(result.error || 'Failed to save user');
        }
    } catch (error) {
        console.error('Error saving user:', error);
        alert('Error saving user');
    }
});

async function deleteUser(userId, username) {
    if (!confirm(`Are you sure you want to delete user "${username}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/admin/api/users/${userId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (response.ok) {
            loadUsers();
        } else {
            alert(result.error || 'Failed to delete user');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        alert('Error deleting user');
    }
}

// Load users on page load
document.addEventListener('DOMContentLoaded', () => {
    loadUsers();
});

// Click outside modal to close
document.getElementById('userModal').addEventListener('click', (e) => {
    if (e.target.id === 'userModal') {
        closeUserModal();
    }
});
