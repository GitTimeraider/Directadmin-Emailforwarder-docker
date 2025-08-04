import requests
import urllib.parse
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class DirectAdminAPI:
    """DirectAdmin API wrapper for email management"""

    def __init__(self, server, username, password, domain=None):
        """Initialize DirectAdmin API connection"""
        self.server = server.rstrip('/')
        self.username = username
        self.password = password
        self.domain = domain

    def _make_request(self, endpoint, data=None, method='POST'):
        """Make request to DirectAdmin API with improved parsing"""
        try:
            url = f"{self.server}{endpoint}"

            print(f"Making {method} request to: {url}")
            if data:
                print(f"Request data: {data}")

            # Common headers
            headers = {
                'User-Agent': 'DirectAdmin Email Forwarder'
            }

            # Make the request
            if method == 'GET':
                response = requests.get(
                    url,
                    params=data,
                    auth=(self.username, self.password),
                    verify=False,
                    timeout=10,
                    headers=headers
                )
            else:
                response = requests.post(
                    url,
                    data=data,
                    auth=(self.username, self.password),
                    verify=False,
                    timeout=10,
                    headers=headers
                )

            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')

                # Try JSON first
                if 'json' in content_type:
                    return response.json()

                # Parse DirectAdmin's various response formats
                text = response.text.strip()
                print(f"Raw response: {text[:500]}...")  # First 500 chars for debugging

                # Check for error
                if text.startswith('error=') or 'error=' in text:
                    error_msg = text.split('error=')[1].split('&')[0]
                    print(f"API Error: {urllib.parse.unquote(error_msg)}")
                    return None

                # Parse different response formats
                result = {}

                # Format 1: URL encoded (key=value&key2=value2)
                if '=' in text and not text.startswith('<!'):
                    # Handle special case for lists
                    if 'list[]=' in text:
                        items = []
                        for part in text.split('&'):
                            if part.startswith('list[]='):
                                items.append(urllib.parse.unquote(part[7:]))
                        return {'list': items}

                    # Standard key=value parsing
                    for pair in text.split('&'):
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            result[urllib.parse.unquote(key)] = urllib.parse.unquote(value)

                # Format 2: Line-based (key=value\nkey2=value2)
                elif '\n' in text and '=' in text:
                    for line in text.split('\n'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            result[key.strip()] = value.strip()

                # Format 3: Simple list (one item per line)
                elif '\n' in text and '@' in text:
                    items = [line.strip() for line in text.split('\n') if line.strip()]
                    return {'list': items}

                # Return parsed result or raw text
                return result if result else text

            elif response.status_code == 401:
                print("Authentication failed")
                return None
            else:
                print(f"Request failed with status: {response.status_code}")
                print(f"Response: {response.text}")
                return None

        except requests.exceptions.Timeout:
            print("Request timed out")
            return None
        except Exception as e:
            print(f"Request error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def test_connection(self):
        """Test the connection to DirectAdmin"""
        try:
            # Try CMD_API_SHOW_DOMAINS first
            endpoint = '/CMD_API_SHOW_DOMAINS'
            response = self._make_request(endpoint, method='GET')

            if response:
                if isinstance(response, dict):
                    # Check if our domain is in the list
                    if self.domain:
                        # DirectAdmin might return domains in various formats
                        domain_list = []
                        for key, value in response.items():
                            if 'domain' in key.lower() or key.startswith('list'):
                                domain_list.append(value)
                            elif '.' in key:  # Might be domain name as key
                                domain_list.append(key)

                        if self.domain in domain_list:
                            return True, f"Successfully connected. Domain {self.domain} found."
                        else:
                            return True, f"Connected, but domain {self.domain} not found in account."
                    else:
                        return True, "Successfully connected to DirectAdmin."
                else:
                    return True, "Successfully connected to DirectAdmin."

            # If that fails, try a simpler endpoint
            endpoint = '/CMD_API_SHOW_USER_CONFIG'
            response = self._make_request(endpoint, method='GET')

            if response:
                return True, "Successfully connected to DirectAdmin."

            return False, "Failed to connect. Please check your credentials."

        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def get_email_accounts(self):
        """Get all email accounts for the domain"""
        try:
            print(f"\n=== Getting Email Accounts for {self.domain} ===")

            # Try multiple endpoints
            endpoints = [
                ('/CMD_API_POP', {'action': 'list', 'domain': self.domain}),
                ('/CMD_API_POP', {'domain': self.domain}),
                ('/CMD_API_EMAIL_POP', {'domain': self.domain}),
            ]

            response = None
            for endpoint, params in endpoints:
                print(f"Trying endpoint: {endpoint}")
                response = self._make_request(endpoint, params, method='GET')
                if response:
                    break

            if response is None:
                print("No response from any email endpoint")
                return []

            print(f"Raw response type: {type(response)}")
            print(f"Raw response: {response}")

            accounts = []

            # Parse various response formats
            if isinstance(response, dict):
                print(f"Response is dict with keys: {list(response.keys())}")

                # Format 1: list format
                if 'list' in response:
                    accounts = response['list']
                # Format 2: numbered keys (0, 1, 2, etc)
                elif any(key.isdigit() for key in response.keys()):
                    for key in sorted(response.keys()):
                        if key.isdigit() and response[key]:
                            if '@' in response[key]:
                                accounts.append(response[key])
                            else:
                                accounts.append(f"{response[key]}@{self.domain}")
                # Format 3: email addresses as keys
                else:
                    for key, value in response.items():
                        if '@' in key and not key.startswith('error'):
                            accounts.append(key)
                        elif value and '@' in str(value):
                            accounts.append(str(value))
                        elif value and not key.startswith('error'):
                            # Might be just username
                            accounts.append(f"{value}@{self.domain}")

            elif isinstance(response, str) and response:
                print("Response is string, parsing...")
                # Parse text response
                lines = response.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and '@' in line:
                        accounts.append(line)
                    elif line and not line.startswith('error'):
                        accounts.append(f"{line}@{self.domain}")

            # Remove duplicates and filter
            accounts = list(set(accounts))
            api_email = f"{self.username}@{self.domain}"
            filtered = [email for email in accounts if email.lower() != api_email.lower()]

            print(f"Found {len(filtered)} email accounts (excluding API user)")
            return sorted(filtered)

        except Exception as e:
            print(f"ERROR in get_email_accounts: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_forwarders(self):
        """Get all email forwarders for the domain"""
        try:
            print(f"\n=== Getting Forwarders for {self.domain} ===")

            # Try multiple endpoint variations
            endpoints = [
                ('/CMD_API_EMAIL_FORWARDERS', {'domain': self.domain, 'action': 'list'}),
                ('/CMD_API_EMAIL_FORWARDERS', {'domain': self.domain}),
                ('/CMD_EMAIL_FORWARDERS', {'domain': self.domain}),
            ]

            response = None
            for endpoint, params in endpoints:
                print(f"\nTrying: {endpoint} with params: {params}")

                # Try GET first
                response = self._make_request(endpoint, params, method='GET')
                if response:
                    print(f"Got response with GET")
                    break

                # Try POST
                response = self._make_request(endpoint, params, method='POST')
                if response:
                    print(f"Got response with POST")
                    break

            if response is None:
                print("ERROR: No response from any forwarders endpoint!")
                return []

            print(f"\n=== FORWARDERS RAW RESPONSE ===")
            print(f"Type: {type(response)}")
            print(f"Content: {response}")
            print("=" * 50)

            forwarders = []

            if isinstance(response, dict):
                # Look for any sign of forwarders in the response
                for key, value in response.items():
                    print(f"Processing key: '{key}' with value: '{value}'")

                    if key.startswith('error'):
                        print(f"Found error: {value}")
                        continue

                    # Various possible formats
                    if '@' in str(key):
                        forwarders.append({
                            'address': key,
                            'destination': str(value)
                        })
                    elif 'forward' in str(key).lower():
                        print(f"Found forward-related key: {key} = {value}")
                    elif value and '=' in str(value):
                        parts = str(value).split('=', 1)
                        if len(parts) == 2:
                            forwarders.append({
                                'address': parts[0],
                                'destination': parts[1]
                            })

            elif isinstance(response, str):
                print("Response is string, checking for forwarders...")
                # Maybe it's a different format
                if '@' in response:
                    lines = response.strip().split('\n')
                    for line in lines:
                        if '=' in line and '@' in line:
                            parts = line.split('=', 1)
                            if len(parts) == 2:
                                forwarders.append({
                                    'address': parts[0].strip(),
                                    'destination': parts[1].strip()
                                })

            print(f"\nParsed {len(forwarders)} forwarders")
            return forwarders

        except Exception as e:
            print(f"ERROR in get_forwarders: {e}")
            import traceback
            traceback.print_exc()
            return []

    def create_forwarder(self, address, destination):
        """Create an email forwarder"""
        try:
            # Ensure full email addresses
            if '@' not in address:
                address = f"{address}@{self.domain}"

            # Extract username from address
            username = address.split('@')[0]

            endpoint = '/CMD_API_EMAIL_FORWARDERS'
            data = {
                'domain': self.domain,
                'action': 'create',
                'user': username,
                'email': destination
            }

            print(f"\n=== Creating Forwarder ===")
            print(f"Address: {address} -> {destination}")

            response = self._make_request(endpoint, data)

            if response:
                # Check for success
                if isinstance(response, dict):
                    if 'error' in response:
                        return False, response.get('error', 'Unknown error')
                    elif 'success' in response or 'created' in response:
                        return True, f"Forwarder {address} → {destination} created successfully"

                # If no error, assume success
                return True, f"Forwarder {address} → {destination} created"

            return False, "Failed to create forwarder"

        except Exception as e:
            print(f"Error creating forwarder: {e}")
            return False, str(e)

    def delete_forwarder(self, address):
        """Delete an email forwarder"""
        try:
            # Ensure full email address
            if '@' not in address:
                address = f"{address}@{self.domain}"

            # Extract username from address
            username = address.split('@')[0]

            endpoint = '/CMD_API_EMAIL_FORWARDERS'
            data = {
                'domain': self.domain,
                'action': 'delete',
                'user': username,
                'select0': username  # DirectAdmin expects select0 for deletion
            }

            print(f"\n=== Deleting Forwarder ===")
            print(f"Address: {address}")

            response = self._make_request(endpoint, data)

            if response:
                # Check for success
                if isinstance(response, dict):
                    if 'error' in response:
                        return False, response.get('error', 'Unknown error')
                    elif 'success' in response or 'deleted' in response:
                        return True, f"Forwarder {address} deleted successfully"

                # If no error, assume success
                return True, f"Forwarder {address} deleted"

            return False, "Failed to delete forwarder"

        except Exception as e:
            print(f"Error deleting forwarder: {e}")
            return False, str(e)

    def validate_email(self, email):
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
