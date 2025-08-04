# Directadmin-Emailforwarder - UNDER DEVELOPMENT

# DirectAdmin Email Forwarder Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)

A secure web application for managing email forwarders through the DirectAdmin API. Features a clean web interface with authentication, 2FA support, and Docker deployment options.

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

</details>

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
  -e DA_SERVER=https://your-directadmin-server.com:2222 \
  -e DA_USERNAME=your_username \
  -e DA_PASSWORD=your_password \
  -e DA_DOMAIN=yourdomain.com \
  -v email-forwarder-data:/app/data \
  ghcr.io/gittimeraider/directadmin-emailforwarder:latest
```
