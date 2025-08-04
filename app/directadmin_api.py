def get_email_accounts(self):
    """Get all email accounts for the domain"""
    try:
        # Try the primary endpoint
        endpoint = '/CMD_API_POP'
        params = {
            'action': 'list',
            'domain': self.domain
        }

        print(f"\n=== Getting Email Accounts ===")
        print(f"Endpoint: {endpoint}")
        print(f"Params: {params}")

        response = self._make_request(endpoint, params, method='GET')

        print(f"Raw response type: {type(response)}")
        print(f"Raw response: {response}")

        if response is None:
            print("No response, trying alternative endpoint")
            # Try without action parameter
            response = self._make_request(endpoint, {'domain': self.domain}, method='GET')

        accounts = []

        # Parse various response formats
        if isinstance(response, dict):
            print(f"Response is dict with keys: {list(response.keys())}")

            # Format 1: list[] format
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

        print(f"Found accounts: {filtered}")
        return filtered

    except Exception as e:
        print(f"ERROR in get_email_accounts: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_forwarders(self):
    """Get all email forwarders for the domain"""
    try:
        endpoint = '/CMD_API_EMAIL_FORWARDERS'
        data = {
            'domain': self.domain,
            'action': 'list'
        }

        print(f"\n=== Getting Forwarders ===")
        print(f"Endpoint: {endpoint}")
        print(f"Data: {data}")

        response = self._make_request(endpoint, data, method='GET')

        print(f"Raw response type: {type(response)}")
        print(f"Raw response: {response}")

        if response is None:
            # Try POST method
            print("No response with GET, trying POST")
            response = self._make_request(endpoint, data, method='POST')

        forwarders = []

        if isinstance(response, dict):
            print(f"Response is dict with keys: {list(response.keys())}")

            for key, value in response.items():
                if key.startswith('error'):
                    continue

                # Format: address=destination
                if '@' in key and value:
                    forwarders.append({
                        'address': key,
                        'destination': str(value)
                    })
                # Alternative format
                elif '=' in str(value):
                    parts = str(value).split('=', 1)
                    if len(parts) == 2:
                        forwarders.append({
                            'address': parts[0],
                            'destination': parts[1]
                        })

        print(f"Found forwarders: {forwarders}")
        return forwarders

    except Exception as e:
        print(f"ERROR in get_forwarders: {e}")
        import traceback
        traceback.print_exc()
        return []
