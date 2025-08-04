import requests
import base64
from urllib.parse import urlencode, parse_qs

class DirectAdminAPI:
    def __init__(self, server, username, password):
        self.server = server.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()

    def _make_request(self, cmd, method='GET', data=None):
        url = f"{self.server}/CMD_{cmd}"
        auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, verify=False, timeout=10)
            else:
                response = self.session.post(url, headers=headers, data=urlencode(data) if data else None, verify=False, timeout=10)

            if response.status_code == 401:
                raise Exception("DirectAdmin authentication failed")

            return response
        except requests.exceptions.RequestException as e:
            raise Exception(f"DirectAdmin connection error: {str(e)}")

    def get_email_accounts(self, domain):
        try:
            response = self._make_request(f'API_POP?domain={domain}')
            if response.status_code == 200:
                accounts = []
                # Parse URL-encoded response
                data = parse_qs(response.text.strip())
                for key in data:
                    if '@' not in key and key != self.username:
                        accounts.append(f"{key}@{domain}")
                return sorted(accounts)
            return []
        except Exception as e:
            print(f"Error in get_email_accounts: {e}")
            return []

    def get_forwarders(self, domain):
        try:
            response = self._make_request(f'API_EMAIL_FORWARDERS?domain={domain}')
            if response.status_code == 200:
                forwarders = []
                # Parse the response
                lines = response.text.strip().split('\n')
                for line in lines:
                    if '=' in line and line.strip():
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            alias = parts[0]
                            destinations = parts[1].split(',')
                            forwarders.append({
                                'alias': alias,
                                'destinations': [d.strip() for d in destinations if d.strip()]
                            })
                return forwarders
            return []
        except Exception as e:
            print(f"Error in get_forwarders: {e}")
            return []

    def create_forwarder(self, domain, alias, destination):
        try:
            data = {
                'domain': domain,
                'user': alias,
                'email': destination,
                'action': 'create'
            }
            response = self._make_request('API_EMAIL_FORWARDERS', method='POST', data=data)
            return response.status_code == 200
        except Exception as e:
            print(f"Error in create_forwarder: {e}")
            return False

    def delete_forwarder(self, domain, alias):
        try:
            data = {
                'domain': domain,
                'select0': alias,
                'action': 'delete'
            }
            response = self._make_request('API_EMAIL_FORWARDERS', method='POST', data=data)
            return response.status_code == 200
        except Exception as e:
            print(f"Error in delete_forwarder: {e}")
            return False
