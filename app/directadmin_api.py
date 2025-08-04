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

    def _make_request(self, endpoint, data=None):
        try:
            url = f"{self.server}{endpoint}"
    
            # For GET requests (like listing)
            if data and data.get('action') == 'list':
                response = requests.get(
                    url,
                    params=data,
                    auth=(self.username, self.password),
                    verify=False,
                    timeout=10
                )
            else:
                # For POST requests
                response = requests.post(
                    url,
                    data=data,
                    auth=(self.username, self.password),
                    verify=False,
                    timeout=10
                )
    
            print(f"API Response Status: {response.status_code}")
            print(f"API Response Headers: {response.headers}")
    
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
    
                # Try to parse as JSON first
                if 'json' in content_type:
                    return response.json()
                else:
                    # Parse DirectAdmin's key=value format
                    text = response.text.strip()
                    result = {}
    
                    # Handle URL encoded responses
                    if 'urlencoded' in content_type or '=' in text:
                        import urllib.parse
    
                        # For email lists, DA often returns: list[]=email1&list[]=email2
                        if 'list[]=' in text:
                            emails = []
                            for part in text.split('&'):
                                if part.startswith('list[]='):
                                    email = urllib.parse.unquote(part[7:])
                                    emails.append(email)
                            return {'emails': emails}
                        else:
                            # Standard key=value parsing
                            for line in text.split('\n'):
                                if '=' in line:
                                    key, value = line.split('=', 1)
                                    result[urllib.parse.unquote(key)] = urllib.parse.unquote(value)
    
                    return result if result else text
    
            return None
    
        except Exception as e:
            print(f"API request error: {e}")
            return None

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
    
        def get_email_accounts(self):
            try:
            # DirectAdmin API endpoint for listing email accounts
                endpoint = '/CMD_API_POP'
                params = {
                    'action': 'list',
                    'domain': self.domain
                }
    
                response = self._make_request(endpoint, params)
    
                if response is None:
                       return []
    
                # Parse the response
                accounts = []
    
                # DirectAdmin returns data in key=value format
                if isinstance(response, dict):
                    # If it's already parsed as dict
                    for key, value in response.items():
                        if '@' in key:  # It's an email address
                            accounts.append(key)
                        elif key.startswith('list[]'):  # Alternative format
                            accounts.append(value)
                else:
                    # If it's raw text response
                    lines = response.strip().split('\n') if isinstance(response, str) else []
                    for line in lines:
                        if '=' in line:
                            key, value = line.split('=', 1)
                            # Check various formats DA might use
                            if '@' in value:
                                accounts.append(value)
                            elif '@' not in key and value and not key.startswith('error'):
                                # It might be username only, add domain
                                email = f"{value}@{self.domain}"
                                accounts.append(email)
    
                # Filter out the API username's email
                filtered_accounts = []
                api_email = f"{self.username}@{self.domain}"
    
                for email in accounts:
                    if email.lower() != api_email.lower():
                        filtered_accounts.append(email)
    
                print(f"Found email accounts: {filtered_accounts}")
                return sorted(filtered_accounts)
    
            except Exception as e:
                print(f"Error getting email accounts: {e}")
                import traceback
                traceback.print_exc()
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
