#!/usr/bin/env python
"""Test script to verify Paragon MLS API connectivity and data"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdezzy.settings')
django.setup()

from buyer.mls_service import paragon_mls_service

print('=== Paragon MLS Service Status ===')
print(f'Enabled: {paragon_mls_service.enabled}')
print(f'Client ID: {paragon_mls_service.client_id}')
print(f'Base URL: {paragon_mls_service.base_url}')

print('\n=== Testing Token Request ===')
token = paragon_mls_service._get_access_token()
print(f'Token obtained: {bool(token)}')

if not token:
    print('ERROR: Could not obtain token')
    exit(1)

print('\n=== Testing Property Query ===')

params = {
    '$top': 5,
    '$filter': "StandardStatus eq 'Active'",
    '$count': 'true',
    '$select': 'ListingKey,City,ListPrice,StateOrProvince'
}

response = paragon_mls_service._make_request('Property', params=params)

if response:
    print(f'Response keys: {list(response.keys())}')
    print(f'Total count: {response.get("@odata.count", "N/A")}')
    properties = response.get('value', [])
    print(f'Properties returned: {len(properties)}')
    
    if properties:
        print('\nFirst 3 properties:')
        for i, prop in enumerate(properties[:3]):
            print(f'  {i+1}. {prop.get("City")}, {prop.get("StateOrProvince")} - ${prop.get("ListPrice")}')
    else:
        print('No properties in response')
else:
    print('ERROR: No response from API')
