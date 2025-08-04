import requests
import base64
from urllib.parse import urlencode, parse_qs, unquote

class DirectAdminAPI:
    def __init__(self, server, username, password):
        self.server = server.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        # Disable SSL warnings for self-signed certificates
        requests.packages.urllib3.disable_warnings()

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
                # Parse the response - DirectAdmin returns URL-encoded list
                if response.text.strip():
                    # Response format: account1=data&account2=data&...
                    parsed = parse_qs(response.text.strip())
                    for account_name in parsed.keys():
                        # Skip the API username and system accounts
                        if (account_name != self.username and 
                            not account_name.startswith('_') and
                            '@' not in account_name):
                            accounts.append(f"{account_name}@{domain}")

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

                if response.text.strip():
                    # DirectAdmin returns forwarders in format: alias=destination1,destination2&alias2=dest
                    # First, unescape the response
                    decoded_response = unquote(response.text.strip())

                    # Split by & to get individual forwarders
                    forwarder_entries = decoded_response.split('&')

                    for entry in forwarder_entries:
                        if '=' in entry and entry.strip():
                            parts = entry.split('=', 1)
                            if len(parts) == 2:
                                alias = parts[0].strip()
                                destinations_str = parts[1].strip()

                                # Split destinations by comma
                                destinations = [d.strip() for d in destinations_str.split(',') if d.strip()]

                                if alias and destinations:
                                    forwarders.append({
                                        'alias': alias,
                                        'destinations': destinations
                                    })

                return sorted(forwarders, key=lambda x: x['alias'])
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
            return response.status_code == 200 and 'error=0' in response.text
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
            return response.status_code == 200 and 'error=0' in response.text
        except Exception as e:
            print(f"Error in delete_forwarder: {e}")
            return False
