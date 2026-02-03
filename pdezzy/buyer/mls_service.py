import requests
import logging
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.core.cache import cache
import threading

# Set up logging
logger = logging.getLogger(__name__)


class ParagonMLSService:
    """
    Service class for fetching MLS listings from Paragon OData API (PrimeMLS).
    Implements OAuth 2.0 client_credentials flow and OData queries.
    
    API Documentation: https://vendorsupport.paragonrels.com/
    Uses RESO-mapped data from /DD1.7 endpoint.
    """

    def __init__(self):
        """Initialize Paragon API client with credentials from Django settings"""
        # Get credentials from Django settings
        self.client_id = getattr(settings, 'PARAGON_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'PARAGON_CLIENT_SECRET', None)
        self.token_url = getattr(settings, 'PARAGON_TOKEN_URL', 
            'https://PrimeMLS.paragonrels.com/OData/PrimeMLS/identity/connect/token')
        self.base_url = getattr(settings, 'PARAGON_BASE_URL', 
            'https://PrimeMLS.paragonrels.com/OData/PrimeMLS')
        
        # Token management
        self._access_token = None
        self._token_expires_at = None
        self._token_lock = threading.Lock()
        
        # Cache timeout (5 minutes)
        self.cache_timeout = 300
        
        # Session for reusing connections
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
        
        # Check if credentials are configured
        # NOTE: Re-enabled after credentials configuration
        if not all([self.client_id, self.client_secret]):
            logger.warning("Paragon API credentials not configured. Set PARAGON_CLIENT_ID and PARAGON_CLIENT_SECRET in settings.")
            self.enabled = False
        else:
            # Re-enabled - test with configured credentials
            self.enabled = True
            logger.info("Paragon MLS API enabled with configured credentials")

    def _get_access_token(self) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        Uses OAuth 2.0 client_credentials grant.
        """
        with self._token_lock:
            # Check if we have a valid cached token
            if self._access_token and self._token_expires_at:
                if datetime.utcnow() < self._token_expires_at - timedelta(seconds=60):
                    return self._access_token
            
            # Request new token
            try:
                print(f"[DEBUG] Requesting token from: {self.token_url}")
                print(f"[DEBUG] Client ID: {self.client_id}")
                response = requests.post(
                    self.token_url,
                    data={
                        'grant_type': 'client_credentials',
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'scope': 'OData',
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=30
                )
                
                print(f"[DEBUG] Token response status: {response.status_code}")
                print(f"[DEBUG] Token response body: {response.text[:200]}")
                
                if response.status_code != 200:
                    logger.error(f"Token request failed: {response.status_code} - {response.text}")
                    print(f"[ERROR] Token request failed: {response.text}")
                    return None
                
                token_data = response.json()
                
                self._access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                logger.info("Successfully obtained Paragon access token")
                print(f"[DEBUG] Token obtained, expires in {expires_in}s")
                return self._access_token
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to obtain Paragon access token: {e}")
                print(f"[ERROR] Token request exception: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response: {e.response.text}")
                    print(f"[ERROR] Response: {e.response.text}")
                return None

    def _make_request(
        self,
        endpoint: str,
        params: Dict = None,
        use_reso: bool = True
    ) -> Optional[Dict]:
        """
        Make authenticated OData request to Paragon API.
        
        Args:
            endpoint: OData resource name (e.g., 'Property', 'Media')
            params: OData query parameters
            use_reso: If True, use DD1.7 (RESO-mapped), else use Paragon native
        """
        if not self.enabled:
            logger.error("Paragon API not enabled. Check credentials.")
            return None
        
        access_token = self._get_access_token()
        if not access_token:
            logger.error("Could not obtain access token")
            return None
        
        # Build URL: /DD1.7/Property or /Paragon/Property
        # Check if data source is already in base_url to avoid duplication
        data_source = 'DD1.7' if use_reso else 'Paragon'
        if data_source in self.base_url:
            url = f"{self.base_url}/{endpoint}"
        else:
            url = f"{self.base_url}/{data_source}/{endpoint}"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
        }
        
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=30
            )
            
            logger.debug(f"Paragon API Request: {url}")
            logger.debug(f"Params: {params}")
            logger.debug(f"Response Status: {response.status_code}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Paragon API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
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
        sort_order: str = 'asc',
        mls_number: str = None,
        title: str = None,
        address: str = None,
        search: str = None
    ) -> Dict[str, Any]:
        """
        Fetch property listings from Paragon OData API.
        
        Returns standardized format:
        {
            'results': [...],
            'total': int,
            'page': int,
            'per_page': int,
            'total_pages': int,
            'source': 'paragon_mls'
        }
        """
        # Build cache key
        cache_key = f"paragon:listings:{city}:{state}:{zip_code}:{min_price}:{max_price}:{bedrooms}:{bathrooms}:{property_type}:{status}:{page}:{per_page}:{sort_by}:{sort_order}:{mls_number}:{title}:{address}:{search}"
        
        # Try cache first
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Returning cached Paragon results")
            return cached
        
        # Build OData query parameters
        # For client-side pagination with search filtering, fetch all data first then paginate locally
        # This ensures we have enough data after filtering
        fetch_per_page = 1000  # Fetch large batch to support pagination after filtering
        skip = 0  # Always start from beginning since we'll paginate locally
        
        params = {
            '$top': fetch_per_page,
            '$skip': skip,
            '$count': 'true',  # Request total count
        }
        
        # Build $orderby clause
        sort_field_map = {
            'price': 'ListPrice',
            'created_at': 'OnMarketDate',
            'bedrooms': 'BedroomsTotal',
            'square_feet': 'LivingArea',
        }
        odata_sort_field = sort_field_map.get(sort_by, 'ListPrice')
        params['$orderby'] = f"{odata_sort_field} {sort_order}"
        
        # Build $filter clause
        filter_parts = []
        
        # Location filters - these work
        if city:
            filter_parts.append(f"substringof('{city}', City)")
        if state:
            filter_parts.append(f"StateOrProvince eq '{state}'")
        if zip_code:
            filter_parts.append(f"PostalCode eq '{zip_code}'")
        
        # Price range - these work
        if min_price:
            filter_parts.append(f"ListPrice ge {min_price}")
        if max_price:
            filter_parts.append(f"ListPrice le {max_price}")
        
        # Bedrooms/Bathrooms - these work
        if bedrooms:
            filter_parts.append(f"BedroomsTotal ge {bedrooms}")
        if bathrooms:
            filter_parts.append(f"BathroomsFull ge {bathrooms}")
        
        # Property type (map to RESO PropertyType) - these work
        property_type_map = {
            'house': 'Residential',
            'residential': 'Residential',
            'condo': 'Condominium',
            'townhouse': 'Townhouse',
            'land': 'Land',
            'commercial': 'Commercial',
            'apartment': 'Residential Income',
        }
        if property_type and property_type.lower() in property_type_map:
            filter_parts.append(f"PropertyType eq '{property_type_map[property_type.lower()]}'")
        
        # Unified search - temporarily disabled due to Paragon API 500 errors
        # The search parameter is accepted but not processed at the API level
        if search:
            # Log for tracking
            logger.info(f"Client requested unified search: '{search}' - note: search filtering not yet available")
        
        # Note: Status filter causes Paragon API 500 errors, so it's disabled
        # All results are returned as-is from Paragon
        
        if filter_parts:
            params['$filter'] = ' and '.join(filter_parts)
        
        # Select specific fields to optimize response
        params['$select'] = ','.join([
            'ListingKey', 'ListingId', 'ListPrice', 'OriginalListPrice',
            'UnparsedAddress', 'StreetNumber', 'StreetName', 'StreetSuffix',
            'City', 'StateOrProvince', 'PostalCode', 'Country',
            'BedroomsTotal', 'BathroomsFull', 'BathroomsTotalInteger',
            'LivingArea', 'LotSizeAcres', 'LotSizeSquareFeet',
            'PropertyType', 'PropertySubType', 'StandardStatus',
            'PublicRemarks', 'PrivateRemarks',
            'OnMarketDate', 'ModificationTimestamp', 'ListAgentFullName',
            'ListAgentEmail', 'ListAgentDirectPhone', 'ListOfficeName',
        ])
        
        # Make API request
        response = self._make_request('Property', params=params)
        
        if not response:
            logger.error("No response from Paragon API, returning empty results")
            return {
                'results': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'source': 'paragon_mls'
            }
        
        # Parse OData response
        properties = response.get('value', [])
        total_count = response.get('@odata.count', len(properties))
        
        # Transform to standardized format
        results = []
        for prop in properties:
            listing = self._transform_property_to_listing(prop)
            results.append(listing)
        
        # Fetch photos for listings (batch request)
        self._attach_photos_to_listings(results)
        
        # Client-side filtering for search parameter (since Paragon API has filtering limitations)
        if search:
            results = self._filter_results_by_search(results, search)
        
        # Recalculate total and pages after filtering
        filtered_total = len(results)
        total_pages = (filtered_total + per_page - 1) // per_page if filtered_total > 0 else 0
        
        # Apply pagination to filtered results
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = results[start_idx:end_idx]
        
        result = {
            'results': paginated_results,
            'total': filtered_total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'source': 'paragon_mls'
        }
        
        # Cache the result
        cache.set(cache_key, result, self.cache_timeout)
        
        return result

    def _filter_results_by_search(self, listings: List[Dict], search_term: str) -> List[Dict]:
        """
        Filter listings by search term. Searches across:
        - MLS number
        - Title/Address
        - City, State, ZIP code
        - Description/Remarks
        - Agent name
        - Office name
        """
        if not search_term:
            return listings
        
        search_lower = search_term.lower().strip()
        filtered = []
        
        for listing in listings:
            # Check each field for a match (case-insensitive substring match)
            if any([
                search_lower in str(listing.get('mls_number', '')).lower(),
                search_lower in str(listing.get('title', '')).lower(),
                search_lower in str(listing.get('address', '')).lower(),
                search_lower in str(listing.get('city', '')).lower(),
                search_lower in str(listing.get('state', '')).lower(),
                search_lower in str(listing.get('zip_code', '')).lower(),
                search_lower in str(listing.get('description', '')).lower(),
                search_lower in str(listing.get('agent_name', '')).lower(),
                search_lower in str(listing.get('office_name', '')).lower(),
            ]):
                filtered.append(listing)
        
        logger.info(f"Search '{search_term}' filtered {len(listings)} results to {len(filtered)}")
        return filtered

    def _transform_property_to_listing(self, prop: Dict) -> Dict:
        """Transform Paragon/RESO property to standardized listing format"""
        # Build address from components
        address_parts = [
            prop.get('StreetNumber', ''),
            prop.get('StreetName', ''),
            prop.get('StreetSuffix', ''),
        ]
        address = ' '.join(filter(None, address_parts)).strip()
        if not address:
            address = prop.get('UnparsedAddress', '')
        
        # Map status
        status_map = {
            'Active': 'for_sale',
            'Pending': 'pending',
            'Closed': 'sold',
            'Withdrawn': 'withdrawn',
            'Expired': 'expired',
        }
        reso_status = prop.get('StandardStatus', 'Active')
        status = status_map.get(reso_status, 'for_sale')
        
        return {
            'mls_number': prop.get('ListingKey') or prop.get('ListingId', ''),
            'title': address or 'Property Listing',
            'address': address,
            'city': prop.get('City', ''),
            'state': prop.get('StateOrProvince', ''),
            'zip_code': prop.get('PostalCode', ''),
            'price': float(prop.get('ListPrice') or 0),
            'original_price': float(prop.get('OriginalListPrice')) if prop.get('OriginalListPrice') else None,
            'bedrooms': prop.get('BedroomsTotal'),
            'bathrooms': prop.get('BathroomsFull') or prop.get('BathroomsTotalInteger'),
            'square_feet': prop.get('LivingArea'),
            'lot_size_acres': prop.get('LotSizeAcres'),
            'lot_size_sqft': prop.get('LotSizeSquareFeet'),
            'property_type': prop.get('PropertyType', 'Unknown'),
            'property_subtype': prop.get('PropertySubType'),
            'status': status,
            'description': prop.get('PublicRemarks', ''),
            'agent_name': prop.get('ListAgentFullName', ''),
            'agent_email': prop.get('ListAgentEmail', ''),
            'agent_phone': prop.get('ListAgentDirectPhone', ''),
            'office_name': prop.get('ListOfficeName', ''),
            'on_market_date': prop.get('OnMarketDate', ''),
            'updated_at': prop.get('ModificationTimestamp', ''),
            'created_at': prop.get('OnMarketDate', ''),
            'photos': [],  # Will be populated by _attach_photos_to_listings
            'photo_url': None,  # Primary photo URL
            'source': 'paragon_mls',
        }

    def _attach_photos_to_listings(self, listings: List[Dict]) -> None:
        """Fetch and attach photos to listings"""
        if not listings:
            return
        
        # Get listing keys for batch photo request
        listing_keys = [l['mls_number'] for l in listings if l.get('mls_number')]
        
        if not listing_keys:
            return
        
        # Build filter for batch photo request
        # Limit to first 10 listings for performance
        batch_keys = listing_keys[:10]
        filter_parts = [f"ResourceRecordKey eq '{key}'" for key in batch_keys]
        filter_str = ' or '.join(filter_parts)
        
        params = {
            '$filter': f"({filter_str}) and MediaCategory eq 'Photo'",
            '$orderby': 'Order asc',
            '$select': 'ResourceRecordKey,MediaURL,Order,ShortDescription',
            '$top': 100,  # Limit total photos
        }
        
        response = self._make_request('Media', params=params)
        
        if not response:
            return
        
        media_items = response.get('value', [])
        
        # Group photos by listing key
        photos_by_listing = {}
        for media in media_items:
            key = media.get('ResourceRecordKey')
            if key not in photos_by_listing:
                photos_by_listing[key] = []
            photos_by_listing[key].append({
                'url': media.get('MediaURL', ''),
                'order': media.get('Order', 0),
                'caption': media.get('ShortDescription', ''),
            })
        
        # Attach photos to listings
        for listing in listings:
            key = listing.get('mls_number')
            if key in photos_by_listing:
                photos = sorted(photos_by_listing[key], key=lambda x: x.get('order', 0))
                listing['photos'] = photos
                if photos:
                    listing['photo_url'] = photos[0].get('url')

    def get_listing_detail(self, mls_number: str) -> Optional[Dict]:
        """
        Get detailed information for a specific MLS listing.
        
        Args:
            mls_number: The MLS listing key/ID
            
        Returns:
            Dict with listing details or None
        """
        cache_key = f"paragon:listing:{mls_number}"
        cached = cache.get(cache_key)
        
        if cached:
            logger.debug("Returning cached listing details")
            return cached
        
        # Query by ListingKey
        params = {
            '$filter': f"ListingKey eq '{mls_number}'",
        }
        
        response = self._make_request('Property', params=params)
        
        if not response or not response.get('value'):
            logger.error(f"Listing {mls_number} not found in Paragon API")
            return None
        
        properties = response.get('value', [])
        if not properties:
            return None
        
        prop = properties[0]
        listing = self._transform_property_to_listing(prop)
        
        # Fetch all photos for this listing
        self._attach_photos_to_listings([listing])
        
        # Cache the result
        cache.set(cache_key, listing, self.cache_timeout)
        
        return listing

    def search_listings(
        self,
        query: str = None,
        location: str = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Search listings by keyword or address.
        
        Args:
            query: Search keyword (address, neighborhood, etc.)
            location: Optional location filter
            page: Page number
            per_page: Results per page
            
        Returns:
            Dict with search results
        """
        if not query:
            return {
                'results': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'source': 'paragon_mls'
            }
        
        # Build OData filter for text search
        skip = (page - 1) * per_page
        
        # Search in address fields
        filter_parts = [
            f"contains(UnparsedAddress, '{query}')",
            f"contains(City, '{query}')",
            f"contains(PublicRemarks, '{query}')",
        ]
        
        params = {
            '$filter': f"({' or '.join(filter_parts)}) and StandardStatus eq 'Active'",
            '$top': per_page,
            '$skip': skip,
            '$count': 'true',
            '$orderby': 'ListPrice asc',
        }
        
        if location:
            # Add location filter
            params['$filter'] += f" and (contains(City, '{location}') or contains(StateOrProvince, '{location}') or PostalCode eq '{location}')"
        
        response = self._make_request('Property', params=params)
        
        if not response:
            return {
                'results': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'source': 'paragon_mls'
            }
        
        properties = response.get('value', [])
        total_count = response.get('@odata.count', len(properties))
        
        results = [self._transform_property_to_listing(p) for p in properties]
        self._attach_photos_to_listings(results)
        
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0
        
        return {
            'results': results,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'source': 'paragon_mls'
        }

    def get_featured_listings(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get featured/promoted listings (highest priced active listings).
        
        Args:
            limit: Number of listings to return
            
        Returns:
            Dict with featured listings
        """
        params = {
            '$filter': "StandardStatus eq 'Active'",
            '$top': limit,
            '$orderby': 'ListPrice desc',
            '$count': 'true',
        }
        
        response = self._make_request('Property', params=params)
        
        if not response:
            return {
                'results': [],
                'total': 0,
                'source': 'paragon_mls'
            }
        
        properties = response.get('value', [])
        results = [self._transform_property_to_listing(p) for p in properties]
        self._attach_photos_to_listings(results)
        
        return {
            'results': results,
            'total': len(results),
            'source': 'paragon_mls'
        }

    def get_nearby_listings(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float = 10,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get listings near a specific location.
        
        Note: Paragon OData may not support geospatial queries directly.
        This returns active listings sorted by price as a fallback.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate  
            radius_miles: Search radius in miles
            limit: Number of listings to return
            
        Returns:
            Dict with nearby listings
        """
        # Note: OData geospatial queries require OData 4.0 geo.distance
        # If not supported, return featured active listings instead
        logger.warning("Geospatial query not fully implemented, returning active listings")
        
        return self.get_featured_listings(limit=limit)


# Keep legacy service for backwards compatibility
class LoneWolfMLSService:
    """
    Legacy Lone Wolf service - kept for backwards compatibility.
    Paragon service is now the primary MLS data source.
    """
    def __init__(self):
        self.enabled = False
        logger.info("LoneWolfMLSService is deprecated. Using ParagonMLSService instead.")


class MLSService:
    """
    Legacy MLSService wrapper - redirects to Paragon service.
    """
    def __init__(self):
        self._paragon = ParagonMLSService()
    
    def get_listings(self, **kwargs):
        return self._paragon.get_listings(**kwargs)
    
    def get_listing_detail(self, mls_number: str):
        return self._paragon.get_listing_detail(mls_number)
    
    def search_listings(self, **kwargs):
        return self._paragon.search_listings(**kwargs)
    
    def get_featured_listings(self, limit: int = 10):
        return self._paragon.get_featured_listings(limit)
    
    def get_nearby_listings(self, **kwargs):
        return self._paragon.get_nearby_listings(**kwargs)


# Service instances
paragon_mls_service = ParagonMLSService()
mls_service = MLSService()  # Wraps Paragon for compatibility with views
lone_wolf_service = LoneWolfMLSService()  # Deprecated

