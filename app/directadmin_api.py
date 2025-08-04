import requests
import base64
from urllib.parse import urlencode

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

        if method == 'GET':
            response = self.session.get(url, headers=headers)
        else:
            response = self.session.post(url, headers=headers, data=urlencode(data) if data else None)

        return response

    def get_email_accounts(self, domain):
        response = self._make_request(f'API_POP?domain={domain}')
        if response.status_code == 200:
            accounts = []
            for line in response.text.strip().split('\n'):
                if '=' in line:
                    email = line.split('=')[0]
                    if email != self.username:  # Exclude API username
                        accounts.append(f"{email}@{domain}")
            return accounts
        return []

    def get_forwarders(self, domain):
        response = self._make_request(f'API_EMAIL_FORWARDERS?domain={domain}')
        if response.status_code == 200:
            forwarders = []
            for line in response.text.strip().split('\n'):
                if '=' in line:
                    alias, destinations = line.split('=', 1)
                    forwarders.append({
                        'alias': alias,
                        'destinations': destinations.split(',')
                    })
            return forwarders
        return []

    def create_forwarder(self, domain, alias, destination):
        data = {
            'domain': domain,
            'user': alias,
            'email': destination,
            'action': 'create'
        }
        response = self._make_request('API_EMAIL_FORWARDERS', method='POST', data=data)
        return response.status_code == 200

    def delete_forwarder(self, domain, alias):
        data = {
            'domain': domain,
            'select0': alias,
            'action': 'delete'
        }
        response = self._make_request('API_EMAIL_FORWARDERS', method='POST', data=data)
        return response.status_code == 200
