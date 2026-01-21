"""
Debug script to test Paragon MLS API connection
Run with: python manage.py shell < test_paragon.py
"""
import requests
import os
from django.conf import settings

print("=" * 60)
print("Testing Paragon MLS API Connection")
print("=" * 60)

# Get credentials
client_id = getattr(settings, 'PARAGON_CLIENT_ID', os.getenv('PARAGON_CLIENT_ID', ''))
client_secret = getattr(settings, 'PARAGON_CLIENT_SECRET', os.getenv('PARAGON_CLIENT_SECRET', ''))
token_url = getattr(settings, 'PARAGON_TOKEN_URL', 'https://PrimeMLS.paragonrels.com/OData/PrimeMLS/identity/connect/token')
base_url = getattr(settings, 'PARAGON_BASE_URL', 'https://PrimeMLS.paragonrels.com/OData/PrimeMLS')

print(f"\nClient ID: {client_id}")
print(f"Client Secret: {'*' * len(client_secret) if client_secret else 'NOT SET'}")
print(f"Token URL: {token_url}")
print(f"Base URL: {base_url}")

# Step 1: Get OAuth Token
print("\n" + "-" * 40)
print("Step 1: Requesting OAuth Token...")
print("-" * 40)

try:
    token_response = requests.post(
        token_url,
        data={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'OData',
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=30
    )
    
    print(f"Status Code: {token_response.status_code}")
    print(f"Response: {token_response.text[:500]}")
    
    if token_response.status_code == 200:
        token_data = token_response.json()
        access_token = token_data.get('access_token', '')
        print(f"\n✓ Token obtained! Length: {len(access_token)} chars")
        print(f"Expires in: {token_data.get('expires_in')} seconds")
        
        # Step 2: Test Property API
        print("\n" + "-" * 40)
        print("Step 2: Testing Property API...")
        print("-" * 40)
        
        property_url = f"{base_url}/DD1.7/Property"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
        }
        params = {
            '$top': 5,
            '$count': 'true',
        }
        
        print(f"URL: {property_url}")
        
        prop_response = requests.get(
            property_url,
            headers=headers,
            params=params,
            timeout=30
        )
        
        print(f"Status Code: {prop_response.status_code}")
        
        if prop_response.status_code == 200:
            data = prop_response.json()
            count = data.get('@odata.count', 'N/A')
            properties = data.get('value', [])
            print(f"\n✓ SUCCESS! Found {count} total properties")
            print(f"Returned {len(properties)} properties in this request")
            
            if properties:
                print("\nFirst property sample:")
                prop = properties[0]
                print(f"  ListingKey: {prop.get('ListingKey', 'N/A')}")
                print(f"  ListPrice: ${prop.get('ListPrice', 'N/A')}")
                print(f"  City: {prop.get('City', 'N/A')}")
                print(f"  Status: {prop.get('StandardStatus', 'N/A')}")
        else:
            print(f"✗ API Error: {prop_response.text[:500]}")
    else:
        print(f"\n✗ Token request failed!")
        
except Exception as e:
    print(f"\n✗ Error: {e}")

print("\n" + "=" * 60)
