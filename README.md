# DirectAdmin Email Forwarder Manager
<p align="center" width="100%">
    <img width="33%" src="https://github.com/GitTimeraider/Assets/blob/main/img/Directadmin-Emailforwarder/icon_main_25.png">
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)

A Dockerized secure web application for managing email forwarders through the DirectAdmin API. Features a clean web interface with authentication, 2FA support, user management options.

## ✨ Features

- **🔐 Secure Authentication**: Built-in user authentication system with session management
- **📱 Two-Factor Authentication**: Optional TOTP-based 2FA for enhanced security
- **📧 Email Forwarder Management**: 
  - Create email forwarders with intuitive interface
  - List all existing forwarders
  - Delete forwarders with confirmation
  - Auto-refresh forwarders list every 60 seconds
- **🎨 Modern Web UI**: Clean, responsive interface built with vanilla JavaScript
- **🐳 Docker Support**: 
  - Multi-architecture images (amd64, arm64)
  - Configurable UID/GID for proper file permissions
  - Available on GitHub Container Registry
- **🔄 DirectAdmin Integration**: Direct API integration with DirectAdmin servers
- **📊 Real-time Updates**: Automatic refresh of forwarder list
<p align="center" width="100%">
    <img width="100%" src="https://github.com/GitTimeraider/Assets/blob/main/img/Directadmin-Emailforwarder/dashboard.jpg">
</p>


## 📚 Prerequisites

- **DirectAdmin Server**: Access to a DirectAdmin server with API enabled
- **DirectAdmin API Credentials**: Username and password with email management permissions
- **Docker** (recommended): Docker Engine 20.10+ and Docker Compose 2.0+
- **Python** (for manual installation): Python 3.11+

## 🚀 Quick Start

```bash
# Pull and run the Docker image
docker run -d \
  --name email-forwarder \
  -p 5000:5000 \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  -v email-forwarder-data:/app/data \
  ghcr.io/gittimeraider/directadmin-emailforwarder:main
```
Access the application at `http://localhost:5000`

-   Default username: `admin`
-   Default password: `changeme` (⚠️ Change immediately!)

### Environment Variables

| Variable | Description | Required | Default | Example |
| --- | --- | --- | --- | --- |
| `SECRET_KEY` | Flask secret key for session encryption | ✅ | \- | `your-secret-key-here` |
| `USER_UID` | User ID for container process | ❌ | `1000` | `1001` |
| `USER_GID` | Group ID for container process | ❌ | `1000` | `1001` |
| `DATABASE_URL` | SQLAlchemy database URL | ❌ | `sqlite:///users.db` | `postgresql://...` |

## 📖 Usage

### First-Time Setup

1.  **Access the application**
    Navigate to `http://localhost:5000`

2.  **Login with default credentials**
    -   Username: `admin`
    -   Password: `changeme`
3.  **Change default password immediately**
    -   This is critical for security
4.  **Configure additional users** (if needed)
    -   Navigate to User Management under Admin
    -   Create users for team members
5.  **Enable 2FA** (Recommended)
    -   Click "Enable 2FA" in the settings
    -   Scan QR code with authenticator app

### Managing Email Forwarders

#### Creating a Forwarder

1.  Navigate to the dashboard
2.  Enter the alias (e.g., "support" for [support@yourdomain.com](mailto:support@yourdomain.com))
3.  Select destination email from dropdown
4.  Click "Create Forwarder"

#### Viewing Forwarders

-   All forwarders are listed with their destinations
-   List auto-refreshes every 60 seconds
-   Shows alias → destination mapping

#### Deleting a Forwarder

1.  Find the forwarder in the list
2.  Click "Delete" button
3.  Confirm deletion

## 👥 User Management

### Accessing User Management

Only administrators can access user management at `/admin/users`

### Managing Users

#### Creating Users

1.  Click "Add New User"
2.  Enter username and password
3.  Optionally generate secure password
4.  Assign admin privileges if needed
5.  Click "Save"

#### Editing Users

1.  Click "Edit" next to user
2.  Modify username, password, or privileges
3.  Reset 2FA if needed
4.  Click "Save"

#### Deleting Users

1.  Click "Delete" next to user
2.  Confirm deletion
3.  System prevents deleting:
    -   Your own account
    -   The last administrator

### User Information Displayed

-   Username
-   Role (Admin/User)
-   2FA Status
-   Creation date
-   Last login time

## 🔒 Security

### Best Practices

1.  **Immediate Actions**
    -   Change default admin password
    -   Enable 2FA for all administrators
    -   Use strong, unique passwords
2.  **Password Security**

    Bash

    `# Generate secure secret key openssl rand -hex 32  # Generate secure password openssl rand -base64 12`

3.  **Environment Security**
    -   Never commit `.env` files
    -   Use HTTPS in production
    -   Restrict database file permissions
    -   Keep DirectAdmin credentials secure
4.  **Container Security**
    -   Run as non-root user
    -   Use specific UID/GID
    -   Mount volumes with appropriate permissions

### Security Features

-   Password hashing (Werkzeug PBKDF2)
-   Session-based authentication
-   TOTP 2FA (RFC 6238 compliant)
-   CSRF protection
-   Admin/user role separation
-   Activity logging

## 🔧 Troubleshooting

### Common Issues

**Cannot connect to DirectAdmin**

-   Verify URL format: `https://server.com:2222`
-   Check API credentials
-   Ensure API is enabled for user
-   Test with curl: `curl -u user:pass https://server.com:2222/CMD_API_SHOW_DOMAINS`

**Permission errors**

-   Set correct UID/GID: `-e USER_UID=$(id -u) -e USER_GID=$(id -g)`
-   Fix data directory: `chown -R $(id -u):$(id -g) ./data`

**2FA not working**

-   Verify device time is synchronized
-   Try adjacent codes (±30 seconds)
-   Ensure using TOTP not HOTP
-   Admin can reset user's 2FA

**Database errors**

-   Check data directory permissions
-   Ensure volume is mounted correctly
-   Verify DATABASE\_URL if using external DB
