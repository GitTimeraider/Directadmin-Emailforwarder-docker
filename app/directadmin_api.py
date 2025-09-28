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

            print(f"Starting HTTP request with 10 second timeout...")
            
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

            print(f"HTTP request completed successfully!")
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

                # Check if we got HTML instead of API data
                if text.startswith('<!DOCTYPE html') or text.startswith('<html'):
                    print(f"ERROR: Received HTML response instead of API data")
                    print(f"This usually means the API endpoint doesn't exist or authentication failed")
                    return None

                # Check for empty response
                if not text:
                    print(f"ERROR: Empty response from DirectAdmin API")
                    return None

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
            print(f"\n=== Testing Connection to {self.server} ===")
            print(f"Username: {self.username}")
            print(f"Domain: {self.domain}")
            
            # First try a simple HTTP request test
            print(f"Testing basic HTTP connectivity...")
            import requests
            test_url = f"{self.server}/CMD_API_SHOW_DOMAINS"
            
            try:
                basic_response = requests.get(
                    test_url,
                    auth=(self.username, self.password),
                    verify=False,
                    timeout=5  # Shorter timeout for basic test
                )
                print(f"Basic HTTP test: status={basic_response.status_code}")
                if basic_response.status_code != 200:
                    return False, f"HTTP request failed with status {basic_response.status_code}"
            except Exception as e:
                print(f"Basic HTTP test failed: {e}")
                return False, f"Basic connectivity test failed: {str(e)}"
            
            # Try CMD_API_SHOW_DOMAINS with our parser
            endpoint = '/CMD_API_SHOW_DOMAINS'
            print(f"Making test request to: {self.server}{endpoint}")
            response = self._make_request(endpoint, method='GET')

            if response is not None:
                if isinstance(response, dict):
                    # Check if our domain is in the list
                    if self.domain:
                        # DirectAdmin might return domains in various formats
                        domain_list = []
                        for key, value in response.items():
                            if 'domain' in key.lower() or key.startswith('list'):
                                # Handle case where value is a list (like list[] parameters)
                                if isinstance(value, list):
                                    domain_list.extend(value)  # Use extend instead of append to flatten
                                else:
                                    domain_list.append(value)
                            elif '.' in key and not key.startswith('<'):  # Might be domain name as key, but not HTML
                                domain_list.append(key)

                        print(f"Found domains: {domain_list}")
                        if self.domain in domain_list:
                            return True, f"Successfully connected. Domain {self.domain} found."
                        else:
                            return True, f"Connected, but domain {self.domain} not found in account. Available domains: {', '.join(domain_list[:3])}{'...' if len(domain_list) > 3 else ''}"
                    else:
                        return True, "Successfully connected to DirectAdmin."
                else:
                    return True, "Successfully connected to DirectAdmin."
            else:
                print("CMD_API_SHOW_DOMAINS returned None (likely HTML response)")

            # If that fails, try a simpler endpoint
            print("Trying CMD_API_SHOW_USER_CONFIG...")
            endpoint = '/CMD_API_SHOW_USER_CONFIG'
            response = self._make_request(endpoint, method='GET')

            if response is not None:
                return True, "Successfully connected to DirectAdmin."
            else:
                print("CMD_API_SHOW_USER_CONFIG also returned None")

            return False, "Failed to connect. Server returned HTML instead of API data - please check your DirectAdmin URL, credentials, and API access."

        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Connection test exception: {error_msg}")
            traceback.print_exc()
            
            # Provide more specific error messages
            if 'timeout' in error_msg.lower():
                return False, "Connection timed out. Please check your DirectAdmin server URL and network connection."
            elif 'connection' in error_msg.lower():
                return False, "Unable to connect to DirectAdmin server. Please verify the server URL and credentials."
            elif 'ssl' in error_msg.lower() or 'certificate' in error_msg.lower():
                return False, "SSL certificate error. Try using HTTP instead of HTTPS."
            else:
                return False, f"Connection error: {error_msg}"

    def validate_domain_access(self):
        """Check if the current domain is accessible via the API"""
        try:
            print(f"\n=== Validating Domain Access for {self.domain} ===")
            
            # Try to get domain list to verify access
            endpoint = '/CMD_API_SHOW_DOMAINS'
            response = self._make_request(endpoint, method='GET')
            
            if response and isinstance(response, dict):
                domain_list = []
                for key, value in response.items():
                    if 'domain' in key.lower() or key.startswith('list'):
                        # Handle case where value is a list (like list[] parameters)
                        if isinstance(value, list):
                            domain_list.extend(value)  # Use extend instead of append to flatten
                        else:
                            domain_list.append(value)
                    elif '.' in key and not key.startswith('<'):  # Might be domain name as key, but not HTML
                        domain_list.append(key)
                
                print(f"Parsed domain list: {domain_list}")
                
                if self.domain in domain_list:
                    print(f"✓ Domain {self.domain} found in account")
                    return True, f"Domain {self.domain} is accessible"
                else:
                    print(f"✗ Domain {self.domain} not found in account")
                    print(f"Available domains: {domain_list}")
                    return False, f"Domain {self.domain} not found in DirectAdmin account"
            
            print("Could not verify domain access - no domain list returned")
            return False, "Unable to verify domain access"
            
        except Exception as e:
            print(f"Error validating domain access: {e}")
            return False, f"Error validating domain: {str(e)}"

    def get_email_accounts(self):
        """Get all email accounts for the domain"""
        try:
            print(f"\n=== Getting Email Accounts for {self.domain} ===")

            # Try API endpoints only
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
                print("No valid response from any email accounts endpoint")
                print("This could mean:")
                print("- The domain doesn't exist in DirectAdmin")
                print("- API user doesn't have permission for this domain")
                print("- DirectAdmin API is not properly configured")
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

            # Ensure all accounts have domain part and filter out invalid entries
            processed_accounts = []
            for account in accounts:
                if account:  # Skip empty strings
                    # Skip entries that look like HTML
                    if account.startswith('<') or '"' in account or account.startswith(':root'):
                        print(f"Skipping invalid account that looks like HTML: {account}")
                        continue
                    
                    # Validate email format
                    import re
                    if '@' not in account:
                        # Validate username part before adding domain
                        if re.match(r'^[a-zA-Z0-9._-]+$', account):
                            processed_accounts.append(f"{account}@{self.domain}")
                        else:
                            print(f"Skipping invalid username: {account}")
                    else:
                        # Validate full email
                        if re.match(r'^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', account):
                            processed_accounts.append(account)
                        else:
                            print(f"Skipping invalid email: {account}")

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

            # Try API endpoints only (avoid web interface endpoints)
            endpoints = [
                ('/CMD_API_EMAIL_FORWARDERS', {'domain': self.domain, 'action': 'list'}),
                ('/CMD_API_EMAIL_FORWARDERS', {'domain': self.domain}),
            ]

            response = None
            for endpoint, params in endpoints:
                print(f"\nTrying: {endpoint} with params: {params}")

                # Try GET first
                response = self._make_request(endpoint, params, method='GET')
                if response:
                    print(f"Got valid response with GET")
                    break

                # Try POST
                response = self._make_request(endpoint, params, method='POST')
                if response:
                    print(f"Got valid response with POST")
                    break

            if response is None:
                print("ERROR: No valid response from any API endpoint!")
                print("This could mean:")
                print("- The domain doesn't exist in DirectAdmin")
                print("- API user doesn't have permission for this domain")
                print("- DirectAdmin API is not properly configured")
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

                        # Skip invalid keys that look like HTML
                        if key.startswith('<') or '"' in key or key.startswith(':root'):
                            print(f"Skipping invalid key that looks like HTML: {key}")
                            continue

                        # Validate that the key looks like a valid email username
                        # Allow alphanumeric, dots, hyphens, underscores
                        import re
                        if not re.match(r'^[a-zA-Z0-9._-]+$', key):
                            print(f"Skipping invalid username: {key}")
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
