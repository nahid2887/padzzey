import requests
import logging
import hashlib
import hmac
import base64
from datetime import datetime
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.core.cache import cache

# Set up logging
logger = logging.getLogger(__name__)

class LoneWolfMLSService:
    """
    Service class for fetching MLS listings from Lone Wolf Real Estate Technologies API.
    Implements authentication and data retrieval from Lone Wolf WolfConnect API.
    """

    def __init__(self):
        """Initialize Lone Wolf API client with credentials from Django settings"""
        # Get credentials from Django settings
        self.api_token = getattr(settings, 'LONE_WOLF_API_TOKEN', None)
        self.client_code = getattr(settings, 'LONE_WOLF_CLIENT_CODE', None)
        self.secret_key = getattr(settings, 'LONE_WOLF_SECRET_KEY', None)
        self.base_url = getattr(settings, 'LONE_WOLF_BASE_URL', 'https://api.lwolf.com/v1')
        
        # Cache timeout (5 minutes)
        self.cache_timeout = 300
        
        # Session for reusing connections
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
        
        # Check if credentials are configured
        if not all([self.api_token, self.client_code, self.secret_key]):
            logger.warning("Lone Wolf API credentials not configured. Set LONE_WOLF_API_TOKEN, LONE_WOLF_CLIENT_CODE, and LONE_WOLF_SECRET_KEY in settings.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Lone Wolf MLS Service initialized successfully")

    def _generate_auth_headers(self, method: str, path: str, body: str = '') -> Dict[str, str]:
        """
        Generate authentication headers for Lone Wolf API requests.
        
        Content-MD5: base64 encoded MD5 hash of request body
        Authorization: HMAC-SHA256 signature
        """
        # Generate Content-MD5 hash
        if body:
            content_md5 = base64.b64encode(hashlib.md5(body.encode()).digest()).decode()
        else:
            content_md5 = ''
        
        # Generate date header
        date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Create signature string
        signature_string = f"{method}\n{content_md5}\napplication/json\n{date}\n{path}"
        
        # Generate HMAC-SHA256 signature
        signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode(),
                signature_string.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
        
        # Create authorization header
        authorization = f"{self.client_code}:{self.api_token}:{signature}"
        
        return {
            'Content-MD5': content_md5,
            'Date': date,
            'Authorization': authorization,
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        data: Dict = None
    ) -> Optional[Dict]:
        """Make authenticated request to Lone Wolf API"""
        if not self.enabled:
            logger.error("Lone Wolf API not enabled. Check credentials.")
            return None
        
        url = f"{self.base_url}/{endpoint}"
        path = f"/{endpoint}"
        
        # Prepare request body
        body = ''
        if data:
            import json
            body = json.dumps(data)
        
        # Generate auth headers
        auth_headers = self._generate_auth_headers(method, path, body)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=body if body else None,
                headers=auth_headers,
                timeout=30
            )
            
            logger.debug(f"Lone Wolf API Request: {method} {url}")
            logger.debug(f"Response Status: {response.status_code}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Lone Wolf API request failed: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return None

    def get_transactions(
        self,
        filters: Dict = None,
        top: int = 20,
        skip: int = 0,
        orderby: str = None
    ) -> List[Dict]:
        """
        Get real estate transactions (property listings).
        
        Args:
            filters: OData filter expression dict
            top: Number of results to return
            skip: Number of results to skip (pagination)
            orderby: Field to order results by
        
        Returns:
            List of transaction objects
        """
        cache_key = f"lonewolf:transactions:{filters}:{top}:{skip}:{orderby}"
        cached = cache.get(cache_key)
        
        if cached:
            logger.debug("Returning cached transactions")
            return cached
        
        # Build OData query parameters
        params = {
            '$top': top,
            '$skip': skip,
        }
        
        if orderby:
            params['$orderby'] = orderby
        
        if filters:
            # Build OData filter string
            filter_parts = []
            for key, value in filters.items():
                if isinstance(value, str):
                    filter_parts.append(f"{key} eq '{value}'")
                else:
                    filter_parts.append(f"{key} eq {value}")
            
            if filter_parts:
                params['$filter'] = ' and '.join(filter_parts)
        
        response = self._make_request('GET', 'transactions', params=params)
        
        if response:
            results = response if isinstance(response, list) else response.get('value', [])
            cache.set(cache_key, results, self.cache_timeout)
            return results
        
        return []

    def get_transaction_detail(self, transaction_id: str) -> Optional[Dict]:
        """
        Get detailed information for a specific transaction.
        
        Args:
            transaction_id: Lone Wolf transaction ID
        
        Returns:
            Transaction details dict
        """
        cache_key = f"lonewolf:transaction:{transaction_id}"
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        response = self._make_request('GET', f'transactions/{transaction_id}')
        
        if response:
            cache.set(cache_key, response, self.cache_timeout)
            return response
        
        return None

    def get_members(self, top: int = 100, skip: int = 0, filters: Dict = None) -> List[Dict]:
        """
        Get real estate agents/members.
        
        Args:
            top: Number of results
            skip: Skip count for pagination
            filters: OData filters
        
        Returns:
            List of member objects
        """
        params = {
            '$top': top,
            '$skip': skip,
        }
        
        if filters:
            filter_parts = []
            for key, value in filters.items():
                if isinstance(value, str):
                    filter_parts.append(f"{key} eq '{value}'")
                else:
                    filter_parts.append(f"{key} eq {value}")
            
            if filter_parts:
                params['$filter'] = ' and '.join(filter_parts)
        
        response = self._make_request('GET', 'members', params=params)
        
        if response:
            return response if isinstance(response, list) else response.get('value', [])
        
        return []

    def get_property_types(self) -> List[Dict]:
        """Get all configured property types"""
        cache_key = "lonewolf:property_types"
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        response = self._make_request('GET', 'propertytypes')
        
        if response:
            results = response if isinstance(response, list) else response.get('value', [])
            cache.set(cache_key, results, 3600)  # Cache for 1 hour
            return results
        
        return []

    def search_listings(
        self,
        city: str = None,
        state: str = None,
        zip_code: str = None,
        min_price: float = None,
        max_price: float = None,
        property_type: str = None,
        status: str = 'Open',
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Search for property listings with filters.
        
        Returns standardized format for compatibility with existing views.
        """
        skip = (page - 1) * per_page
        
        # Build filters
        filters = {}
        
        if status:
            filters['Status'] = status
        
        # Build OData filter for price range
        filter_parts = []
        
        if min_price:
            filter_parts.append(f"SellPrice ge {min_price}")
        if max_price:
            filter_parts.append(f"SellPrice le {max_price}")
        
        # Get transactions
        transactions = self.get_transactions(
            filters=filters if filters else None,
            top=per_page,
            skip=skip,
            orderby='SellPrice asc'
        )
        
        # Transform to standard format
        results = []
        for transaction in transactions:
            listing = self._transform_transaction_to_listing(transaction)
            
            # Apply additional filters in Python (since OData may be limited)
            if city and listing.get('city', '').lower() != city.lower():
                continue
            if state and listing.get('state', '').lower() != state.lower():
                continue
            if zip_code and listing.get('zip_code') != zip_code:
                continue
            
            results.append(listing)
        
        total_pages = (len(results) + per_page - 1) // per_page if results else 1
        
        return {
            'results': results[:per_page],
            'total': len(results),
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'source': 'lone_wolf'
        }

    def _transform_transaction_to_listing(self, transaction: Dict) -> Dict:
        """Transform Lone Wolf transaction to standardized listing format"""
        mls_address = transaction.get('MLSAddress', {})
        property_type_obj = transaction.get('PropertyType', {})
        
        return {
            'mls_number': transaction.get('MLSNumber', transaction.get('Number', '')),
            'title': f"{mls_address.get('StreetNumber', '')} {mls_address.get('StreetName', '')}".strip(),
            'address': f"{mls_address.get('StreetNumber', '')} {mls_address.get('StreetName', '')} {mls_address.get('Unit', '')}".strip(),
            'city': mls_address.get('City', ''),
            'state': mls_address.get('ProvinceCode', ''),
            'zip_code': mls_address.get('PostalCode', ''),
            'price': float(transaction.get('SellPrice', 0)),
            'property_type': property_type_obj.get('Name', 'Unknown'),
            'status': transaction.get('Status', 'Unknown'),
            'description': transaction.get('LegalDescription', ''),
            'created_at': transaction.get('CreatedTimestamp', ''),
            'updated_at': transaction.get('ModifiedTimestamp', ''),
            'source': 'lone_wolf',
            'id': transaction.get('Id'),
        }


class MLSService:
    """
    Service class for fetching MLS listings from public APIs.
    Supports public MLS providers.
    """

    # Public MLS API Configuration (replace this URL with the actual public MLS API URL)
    PUBLIC_MLS_BASE_URL = 'http://10.10.13.27:8005/api/v1'  # Example, replace with actual public API URL

    # Cache settings
    CACHE_TIMEOUT = 300  # 5 minutes

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        data: Dict = None
    ) -> Optional[Dict]:
        """
        Make HTTP request to public MLS API and log the response for debugging.
        """
        url = f"{self.PUBLIC_MLS_BASE_URL}/{endpoint}"

        try:
            # Send the API request
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            
            # Log request details and response for debugging
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request Params: {params}")
            logger.debug(f"Response Status Code: {response.status_code}")
            logger.debug(f"Response Body: {response.text}")

            # If the request was successful, return the JSON response
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"MLS API request failed: {e}")
            return None

    def get_listings(
        self,
        city: str = None,
        state: str = None,
        zip_code: str = None,
        min_price: float = None,
        max_price: float = None,
        bedrooms: int = None,
        bathrooms: int = None,
        property_type: str = None,
        status: str = 'for_sale',
        page: int = 1,
        per_page: int = 20,
        sort_by: str = 'price',
        sort_order: str = 'asc'
    ) -> Dict[str, Any]:
        """
        Fetch MLS listings with filters.

        Returns:
            Dict with 'results', 'total', 'page', 'per_page'
        """
        # Build cache key
        cache_key = f"mls_listings:{city}:{state}:{zip_code}:{min_price}:{max_price}:{bedrooms}:{bathrooms}:{property_type}:{status}:{page}:{per_page}"

        # Try cache first
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Returning cached results")
            return cached

        # Build query parameters
        params = {
            'page': page,
            'per_page': per_page,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'status': status,
        }

        if city:
            params['city'] = city
        if state:
            params['state'] = state
        if zip_code:
            params['zip_code'] = zip_code
        if min_price:
            params['min_price'] = min_price
        if max_price:
            params['max_price'] = max_price
        if bedrooms:
            params['bedrooms_min'] = bedrooms
        if bathrooms:
            params['bathrooms_min'] = bathrooms
        if property_type:
            params['property_type'] = property_type

        # Make API request
        response = self._make_request('GET', 'listings', params=params)

        if response:
            # Cache the response for subsequent requests
            cache.set(cache_key, response, self.CACHE_TIMEOUT)
            return response
        
        # If public API fails, return an empty response
        logger.error("No data returned from public MLS API")
        return {"results": [], "total": 0, "page": page, "per_page": per_page, "total_pages": 0, "source": "public"}
    
    def get_listing_detail(self, mls_number: str) -> Optional[Dict]:
        """
        Get detailed information for a specific MLS listing.

        Args:
            mls_number: The MLS listing number
            
        Returns:
            Dict with listing details or None
        """
        cache_key = f"mls_listing:{mls_number}"
        cached = cache.get(cache_key)

        if cached:
            logger.debug("Returning cached listing details")
            return cached

        response = self._make_request('GET', f'listings/{mls_number}', params={})

        if response:
            # Cache the response for subsequent requests
            cache.set(cache_key, response, self.CACHE_TIMEOUT)
            return response

        # If public API fails, return empty or sample data
        logger.error(f"Listing {mls_number} not found in public MLS API")
        return {"mls_number": mls_number, "details": "No details found", "source": "public"}

# Service instances - use lone_wolf_service for real MLS data
lone_wolf_service = LoneWolfMLSService()
mls_service = MLSService()  # Fallback for generic APIs
