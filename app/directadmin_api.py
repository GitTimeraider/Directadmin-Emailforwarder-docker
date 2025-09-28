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

                # Parse response into dictionary first
                result = {}

                # Format 1: URL encoded (key=value&key2=value2)
                if '=' in text and not text.startswith('<!'):
                    # Handle special case for lists with duplicate keys
                    if 'list[]=' in text:
                        items = []
                        for part in text.split('&'):
                            if part.startswith('list[]='):
                                items.append(urllib.parse.unquote(part[7:]))
                        return {'list': items}

                    # Standard key=value parsing - handle duplicate keys by collecting all values
                    for pair in text.split('&'):
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            key_decoded = urllib.parse.unquote(key)
                            value_decoded = urllib.parse.unquote(value)
                            
                            # If key already exists, convert to list or append to existing list
                            if key_decoded in result:
                                if not isinstance(result[key_decoded], list):
                                    # Convert existing single value to list
                                    result[key_decoded] = [result[key_decoded]]
                                result[key_decoded].append(value_decoded)
                            else:
                                result[key_decoded] = value_decoded

                    # IMPORTANT: Check if this is an error response
                    # error=0 means SUCCESS in DirectAdmin!
                    if 'error' in result:
                        error_code = result.get('error', '1')
                        if error_code != '0':  # Only treat non-zero as error
                            error_msg = result.get('text', 'Unknown error')
                            print(f"API Error {error_code}: {error_msg}")
                            return None
                        else:
                            print(f"Success (error=0): {result.get('text', 'Operation completed')}")

                    return result

                # Format 2: Line-based (key=value\nkey2=value2)
                elif '\n' in text and '=' in text:
                    for line in text.split('\n'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            result[key.strip()] = value.strip()
                    return result

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
            import traceback
            print(f"Connection error: {str(e)}")
            traceback.print_exc()
            return False, "Connection error: Unable to connect to DirectAdmin."

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
                    list_data = response['list']
                    if isinstance(list_data, list):
                        accounts = list_data
                    else:
                        accounts = [list_data]  # Single item, convert to list
                        
                # Format 2: list[] key (from fixed parsing)
                elif 'list[]' in response:
                    list_data = response['list[]']
                    if isinstance(list_data, list):
                        accounts = list_data
                    else:
                        accounts = [list_data]  # Single item, convert to list
                        
                # Format 3: numbered keys (0, 1, 2, etc)
                elif any(key.isdigit() for key in response.keys()):
                    for key in sorted(response.keys()):
                        if key.isdigit() and response[key]:
                            if '@' in response[key]:
                                accounts.append(response[key])
                            else:
                                accounts.append(f"{response[key]}@{self.domain}")
                                
                # Format 4: email addresses as keys
                else:
                    for key, value in response.items():
                        if '@' in key and not key.startswith('error'):
                            accounts.append(key)
                        elif value and '@' in str(value):
                            if isinstance(value, list):
                                accounts.extend([str(v) for v in value])
                            else:
                                accounts.append(str(value))
                        elif value and not key.startswith('error'):
                            # Might be just username(s)
                            if isinstance(value, list):
                                accounts.extend([f"{v}@{self.domain}" for v in value])
                            else:
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

            # Ensure all accounts have domain part
            processed_accounts = []
            for account in accounts:
                if account:  # Skip empty strings
                    if '@' not in account:
                        # Add domain if missing
                        processed_accounts.append(f"{account}@{self.domain}")
                    else:
                        processed_accounts.append(account)

            # Remove duplicates and filter out API user
            processed_accounts = list(set(processed_accounts))
            api_email = f"{self.username}@{self.domain}"
            filtered = [email for email in processed_accounts if email.lower() != api_email.lower()]

            print(f"Found {len(filtered)} email accounts (excluding API user)")
            for account in filtered:
                print(f"  - {account}")
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
                # DirectAdmin commonly uses these formats for forwarders:

                # Format 1: select0, select1, etc. (common for lists)
                select_keys = [k for k in response.keys() if k.startswith('select')]
                if select_keys:
                    print(f"Found select keys: {select_keys}")
                    for key in select_keys:
                        value = response[key]
                        if '=' in str(value):
                            # Format: alias=destination
                            parts = str(value).split('=', 1)
                            if len(parts) == 2:
                                forwarders.append({
                                    'address': f"{parts[0]}@{self.domain}",
                                    'destination': parts[1]
                                })
                        elif value:  # Accept ANY non-empty value
                            # Check if there's a corresponding destination key
                            dest_key = key.replace('select', 'destination')
                            if dest_key in response:
                                forwarders.append({
                                    'address': f"{value}@{self.domain}" if '@' not in str(value) else str(value),
                                    'destination': response[dest_key]
                                })

                # Format 2: list[] array
                elif 'list' in response and isinstance(response['list'], list):
                    print("Found list array")
                    for item in response['list']:
                        if '=' in str(item):
                            parts = str(item).split('=', 1)
                            if len(parts) == 2:
                                forwarders.append({
                                    'address': f"{parts[0]}@{self.domain}" if '@' not in parts[0] else parts[0],
                                    'destination': parts[1]
                                })

                # Format 3: Direct key-value pairs (most common)
                else:
                    # Look for all key-value pairs
                    for key, value in response.items():
                        if key.startswith('error') or key == 'domain':
                            continue

                        # IMPORTANT: Accept ALL non-empty values as valid destinations
                        if value:
                            # Key is the username, value is the destination
                            forwarders.append({
                                'address': f"{key}@{self.domain}",
                                'destination': str(value)
                            })

            elif isinstance(response, str):
                print("Response is string, parsing...")
                lines = response.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if '=' in line:
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            forwarders.append({
                                'address': f"{parts[0]}@{self.domain}" if '@' not in parts[0] else parts[0],
                                'destination': parts[1]
                            })

            print(f"\nParsed {len(forwarders)} forwarders:")
            for f in forwarders:
                print(f"  {f['address']} -> {f['destination']}")

            return forwarders

        except Exception as e:
            print(f"ERROR in get_forwarders: {e}")
            import traceback
            traceback.print_exc()
            return []

    def create_forwarder(self, address, destination):
        """Create an email forwarder"""
        try:
            # Ensure we have just the username part for the alias
            if '@' in address:
                username = address.split('@')[0]
            else:
                username = address

            # SMART DESTINATION HANDLING:
            # 1. If it has @, it's already a full email address
            # 2. If it starts with : (like :blackhole:, :fail:), it's a special destination
            # 3. If it starts with | (pipe to script), it's a special destination
            # 4. Otherwise, assume it's a local username and add domain

            if '@' not in destination:
                # Check if it's a special destination
                if destination.startswith(':') or destination.startswith('|'):
                    # Special destination - use as-is
                    print(f"Special destination detected: {destination}")
                else:
                    # Regular username - add domain
                    destination = f"{destination}@{self.domain}"

            print(f"\n=== Creating Forwarder ===")
            print(f"Username: {username}")
            print(f"Domain: {self.domain}")
            print(f"Destination: {destination}")

            # Use the correct parameter format that DirectAdmin expects
            endpoint = '/CMD_API_EMAIL_FORWARDERS'
            data = {
                'domain': self.domain,
                'action': 'create',
                'user': username,
                'email': destination
            }

            print(f"Sending parameters: {data}")

            response = self._make_request(endpoint, data, method='POST')

            if response:
                print(f"Got response: {response}")

                if isinstance(response, dict):
                    # Check the error code properly
                    error_code = response.get('error', '1')

                    # error=0 means SUCCESS!
                    if error_code == '0' or error_code == 0:
                        return True, f"Forwarder {username}@{self.domain} → {destination} created successfully"

                    # Non-zero error code means actual error
                    details = response.get('details', '')
                    text = response.get('text', '')

                    if details:
                        details = urllib.parse.unquote(details)
                    if text:
                        text = urllib.parse.unquote(text)

                    return False, f"{text}: {details}" if text and details else "Failed to create forwarder"

                elif isinstance(response, str):
                    if 'error' not in response.lower():
                        return True, f"Forwarder {username}@{self.domain} → {destination} created"

            return False, "Failed to create forwarder. No response from server."

        except Exception as e:
            print(f"Error creating forwarder: {e}")
            import traceback
            traceback.print_exc()
            return False, "An error occurred while creating the forwarder"

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
                if isinstance(response, dict):
                    # Check the error code properly
                    error_code = response.get('error', '1')

                    # error=0 means SUCCESS!
                    if error_code == '0' or error_code == 0:
                        return True, f"Forwarder {address} deleted successfully"

                    # Non-zero error code means actual error
                    text = response.get('text', 'Unknown error')
                    details = response.get('details', '')

                    if text:
                        text = urllib.parse.unquote(text)
                    if details:
                        details = urllib.parse.unquote(details)

                    return False, f"{text}: {details}" if details else text

                elif isinstance(response, str):
                    if 'error' not in response.lower():
                        return True, f"Forwarder {address} deleted"

            return False, "Failed to delete forwarder"

        except Exception as e:
            print(f"Error deleting forwarder: {e}")
            return False, "An error occurred while deleting the forwarder"

    def validate_email(self, email):
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
