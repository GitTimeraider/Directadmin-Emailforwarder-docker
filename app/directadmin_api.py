import requests
import base64
from urllib.parse import urlencode, parse_qs, unquote
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DirectAdminAPI:
    def __init__(self, server, username, password):
        self.server = server.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()

    def _make_request(self, cmd, method='GET', data=None):
        url = f"{self.server}/CMD_{cmd}"

        # Use basic auth
        auth = (self.username, self.password)

        try:
            print(f"Making request to: {url}")

            if method == 'GET':
                response = self.session.get(
                    url, 
                    auth=auth, 
                    verify=False, 
                    timeout=10,
                    allow_redirects=False  # Don't follow redirects
                )
            else:
                response = self.session.post(
                    url, 
                    auth=auth, 
                    data=data if isinstance(data, str) else urlencode(data) if data else None,
                    verify=False, 
                    timeout=10,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    allow_redirects=False  # Don't follow redirects
                )

            print(f"Response status: {response.status_code}")

            if response.status_code == 401:
                raise Exception("Authentication failed - invalid username or password")
            elif response.status_code == 302 or response.status_code == 301:
                # DirectAdmin might redirect on auth failure
                raise Exception("Authentication required - check credentials")

            return response
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to server at {self.server}")
        except requests.exceptions.Timeout:
            raise Exception("Connection timeout - server not responding")
        except requests.exceptions.SSLError:
            raise Exception("SSL error - try using http:// instead of https://")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Connection error: {str(e)}")

    def test_connection(self):
        """Test connection with a simple API call"""
        try:
            # Try the simplest API call - show API version
            # Some of these endpoints might work depending on DA version
            test_endpoints = [
                'API_SHOW_DOMAINS',  # List domains
                'API_SHOW_USER_USAGE',  # Show user usage
                'API_SHOW_USER_CONFIG',  # Show user config
            ]

            last_error = None
            for endpoint in test_endpoints:
                try:
                    response = self._make_request(endpoint)
                    if response.status_code == 200:
                        # Check if response looks like DirectAdmin
                        content = response.text.lower()
                        if 'error=1' in content:
                            # DirectAdmin error response
                            continue
                        elif '=' in response.text or response.text.strip():
                            # Looks like a valid DirectAdmin response
                            return True, "Connection successful!"
                except Exception as e:
                    last_error = str(e)
                    print(f"Test endpoint {endpoint} failed: {e}")
                    continue

            # If we get here, no endpoint worked
            if last_error:
                return False, last_error
            else:
                return False, "Could not verify DirectAdmin API access"

        except Exception as e:
            return False, str(e)

    def get_email_accounts(self, domain):
        try:
            response = self._make_request(f'API_POP?domain={domain}')
            if response.status_code == 200:
                accounts = []
                # Parse the response - DirectAdmin returns URL-encoded list
                if response.text.strip():
                    # Response format: account1=data&account2=data&...
                    # or sometimes: account1&account2&account3
                    if '=' in response.text:
                        parsed = parse_qs(response.text.strip())
                        for account_name in parsed.keys():
                            if (account_name != self.username and 
                                not account_name.startswith('_') and
                                '@' not in account_name):
                                accounts.append(f"{account_name}@{domain}")
                    else:
                        # Simple list format
                        for line in response.text.strip().split('\n'):
                            account_name = line.split('&')[0].strip()
                            if (account_name and 
                                account_name != self.username and 
                                not account_name.startswith('_')):
                                accounts.append(f"{account_name}@{domain}")

                return sorted(accounts)
            return []
        except Exception as e:
            print(f"Error in get_email_accounts: {e}")
            return []

    # ... rest of the methods remain the same ...


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

            # Check for success in response
            if response.status_code == 200:
                if 'error=0' in response.text or 'success' in response.text.lower():
                    return True
                elif 'error=1' in response.text:
                    print(f"DirectAdmin error: {response.text}")
                    return False
                else:
                    # If no clear error indicator, assume success
                    return True
            return False
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

            # Check for success in response
            if response.status_code == 200:
                if 'error=0' in response.text or 'success' in response.text.lower():
                    return True
                elif 'error=1' in response.text:
                    print(f"DirectAdmin error: {response.text}")
                    return False
                else:
                    # If no clear error indicator, assume success
                    return True
            return False
        except Exception as e:
            print(f"Error in delete_forwarder: {e}")
            return False
