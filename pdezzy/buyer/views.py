from rest_framework import viewsets, status, views, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from pdezzy.permissions import IsBuyer
from .models import Buyer
from .mls_service import mls_service

from .serializers import (
    UserSerializer,
    RegisterSerializer,
    RegisterRequestSerializer,
    RegisterResponseSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
    CustomTokenObtainPairSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
    # MLS Listing Serializers
    MLSListingSerializer,
    MLSListingDetailSerializer,
    MLSListingResponseSerializer,
    MLSSearchParamsSerializer,
    MLSKeywordSearchSerializer,
    FavoriteListingSerializer,
    # Showing Schedule Serializers
    ShowingScheduleSerializer,
    ShowingScheduleCreateSerializer,
    AgentPropertyListingDetailSerializer,
)

User = Buyer


class RegisterView(generics.CreateAPIView):
    """
    Register a new buyer account.
    Returns access and refresh tokens upon successful registration.
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @swagger_auto_schema(
        operation_description="Register a new buyer account",
        request_body=RegisterSerializer,
        responses={
            201: RegisterSerializer,
            400: "Bad Request - Validation errors"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class LoginView(views.APIView):
    """
    Buyer login endpoint.
    Returns access and refresh tokens along with user information.
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @swagger_auto_schema(
        operation_description="Login with email and password to get access token",
        request_body=LoginSerializer,
        responses={
            200: LoginSerializer,
            400: "Bad Request - Invalid credentials"
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain pair view with user information.
    """
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(
        operation_description="Obtain JWT token pair (access and refresh)",
        responses={
            200: openapi.Response("Token pair", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'access': openapi.Schema(type=openapi.TYPE_STRING, description='Access token'),
                    'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token'),
                }
            )),
            401: "Unauthorized - Invalid credentials"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RefreshTokenView(TokenRefreshView):
    """
    Refresh access token using refresh token.
    Custom serializer ensures user_type claim is preserved.
    """
    from buyer.serializers import CustomTokenRefreshSerializer
    serializer_class = CustomTokenRefreshSerializer
    
    @swagger_auto_schema(
        operation_description="Refresh access token using refresh token (preserves user_type claim)",
        responses={
            200: openapi.Response("New access token", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'access': openapi.Schema(type=openapi.TYPE_STRING, description='New access token with user_type claim'),
                }
            )),
            401: "Unauthorized - Invalid refresh token"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(views.APIView):
    """
    Logout endpoint to invalidate the refresh token.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Logout and invalidate refresh token",
        request_body=LogoutSerializer,
        responses={
            200: openapi.Response("Success", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                }
            )),
            400: "Bad Request - Invalid token",
            401: "Unauthorized"
        }
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            try:
                refresh_token = serializer.validated_data['refresh']
                token = RefreshToken(refresh_token)
                token.blacklist()
                
                return Response(
                    {"message": "Successfully logged out."},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(views.APIView):
    """
    Get current buyer profile.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get current buyer profile",
        responses={
            200: UserSerializer,
            401: "Unauthorized"
        }
    )
    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProfileUpdateView(generics.UpdateAPIView):
    """
    Update current buyer profile.
    Only buyers can update their own profile.
    Supports multipart/form-data for file uploads (profile image).
    """
    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated, IsBuyer]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_object(self):
        """Return the current authenticated user"""
        return self.request.user

    @swagger_auto_schema(
        operation_description="Update current buyer profile (multipart/form-data for file uploads)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['mortgage_letter'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, format='email', description='Email address'),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name'),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number'),
                'profile_image': openapi.Schema(type=openapi.TYPE_STRING, format='binary', description='Profile image (JPG, PNG)'),
                'price_range': openapi.Schema(type=openapi.TYPE_STRING, description='Preferred price range'),
                'location': openapi.Schema(type=openapi.TYPE_STRING, description='Preferred location'),
                'bedrooms': openapi.Schema(type=openapi.TYPE_INTEGER, description='Preferred number of bedrooms'),
                'bathrooms': openapi.Schema(type=openapi.TYPE_INTEGER, description='Preferred number of bathrooms'),
                'mortgage_letter': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    format='binary', 
                    title='Mortgage Pre-approval Letter',
                    description='Mortgage pre-approval letter (PDF, JPG, JPEG, PNG - max 10MB). Required for profile verification.',
                    example='mortgage_approval_2025.pdf'
                ),
            }
        ),
        responses={
            200: UserSerializer,
            400: "Bad Request - Validation errors",
            401: "Unauthorized"
        }
    )
    def put(self, request, *args, **kwargs):
        """Update buyer profile"""
        response = super().update(request, *args, **kwargs)
        # Return using UserSerializer for complete user data
        return Response(UserSerializer(self.request.user, context={'request': request}).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Partially update current buyer profile (multipart/form-data for file uploads)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, format='email', description='Email address'),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name'),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number'),
                'profile_image': openapi.Schema(type=openapi.TYPE_STRING, format='binary', description='Profile image (JPG, PNG)'),
                'price_range': openapi.Schema(type=openapi.TYPE_STRING, description='Preferred price range'),
                'location': openapi.Schema(type=openapi.TYPE_STRING, description='Preferred location'),
                'bedrooms': openapi.Schema(type=openapi.TYPE_INTEGER, description='Preferred number of bedrooms'),
                'bathrooms': openapi.Schema(type=openapi.TYPE_INTEGER, description='Preferred number of bathrooms'),
                'mortgage_letter': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    format='binary', 
                    title='Mortgage Pre-approval Letter',
                    description='Mortgage pre-approval letter (PDF, JPG, JPEG, PNG - max 10MB). Upload your mortgage pre-approval letter for profile verification.',
                    example='mortgage_approval_2025.pdf'
                ),
            }
        ),
        responses={
            200: UserSerializer,
            400: "Bad Request - Validation errors",
            401: "Unauthorized"
        }
    )
    def patch(self, request, *args, **kwargs):
        """Partially update buyer profile"""
        response = super().partial_update(request, *args, **kwargs)
        # Return using UserSerializer for complete user data
        return Response(UserSerializer(self.request.user, context={'request': request}).data, status=status.HTTP_200_OK)


class ChangePasswordView(views.APIView):
    """
    Change current buyer's password.
    Only buyers can change their own password.
    """
    permission_classes = [IsAuthenticated, IsBuyer]

    @swagger_auto_schema(
        operation_description="Change current buyer password",
        request_body=ChangePasswordSerializer,
        responses={
            200: openapi.Response("Success", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                }
            )),
            400: "Bad Request - Validation errors",
            401: "Unauthorized"
        }
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Password changed successfully."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a buyer instance.
    Only buyers can access their own details.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsBuyer]

    def get_object(self):
        return self.request.user

    @swagger_auto_schema(
        operation_description="Retrieve the authenticated buyer's user details",
        responses={
            200: UserSerializer,
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update the authenticated buyer's user details",
        request_body=UserSerializer,
        responses={
            200: UserSerializer,
            400: "Bad Request - Validation errors",
            401: "Unauthorized"
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete the authenticated buyer's account",
        responses={
            204: "No Content - Successfully deleted",
            401: "Unauthorized"
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# =============================================================================
# MLS Listing Views
# =============================================================================

class MLSListingsView(views.APIView):
    """
    MLS Listings API - Get property listings from MLS

    This endpoint allows buyers to browse property listings with a unified search bar.
    Search across: MLS number, title, address, city, state, ZIP code, description, and more.
    Data is fetched from external MLS providers (Lone Wolf API) with fallback to local listings.
    """
    permission_classes = [AllowAny]  # Allow public access to listings
    
    @swagger_auto_schema(
        operation_description="Get MLS property listings with unified search or advanced filters",
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, description="Unified search across MLS number, title, address, city, state, ZIP code, description, agent name, etc. (use this single field to search for anything)", type=openapi.TYPE_STRING),
            openapi.Parameter('city', openapi.IN_QUERY, description="Filter by city (advanced filter)", type=openapi.TYPE_STRING),
            openapi.Parameter('state', openapi.IN_QUERY, description="Filter by state (advanced filter)", type=openapi.TYPE_STRING),
            openapi.Parameter('zip_code', openapi.IN_QUERY, description="Filter by ZIP code (advanced filter)", type=openapi.TYPE_STRING),
            openapi.Parameter('min_price', openapi.IN_QUERY, description="Minimum price (advanced filter)", type=openapi.TYPE_NUMBER),
            openapi.Parameter('max_price', openapi.IN_QUERY, description="Maximum price (advanced filter)", type=openapi.TYPE_NUMBER),
            openapi.Parameter('bedrooms', openapi.IN_QUERY, description="Minimum bedrooms (advanced filter)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('bathrooms', openapi.IN_QUERY, description="Minimum bathrooms (advanced filter)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('property_type', openapi.IN_QUERY, description="Property type (advanced filter): house, apartment, condo, townhouse, land, commercial", type=openapi.TYPE_STRING),
            openapi.Parameter('status', openapi.IN_QUERY, description="Listing status (advanced filter): for_sale, pending, sold", type=openapi.TYPE_STRING, default='for_sale'),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number (default 1)", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('per_page', openapi.IN_QUERY, description="Results per page (default 20, max 1000). Use per_page=1000 to get all results", type=openapi.TYPE_INTEGER, default=20),
            openapi.Parameter('all', openapi.IN_QUERY, description="Set to 'true' to get ALL results at once without pagination (ignores page/per_page)", type=openapi.TYPE_STRING),
            openapi.Parameter('sort_by', openapi.IN_QUERY, description="Sort field: price, created_at, bedrooms, square_feet", type=openapi.TYPE_STRING, default='price'),
            openapi.Parameter('sort_order', openapi.IN_QUERY, description="Sort order: asc, desc", type=openapi.TYPE_STRING, default='asc'),
        ],
        responses={
            200: MLSListingResponseSerializer,
            400: "Bad Request - Invalid parameters"
        },
        tags=['MLS Listings']
    )
    def get(self, request):
        """Get MLS listings with unified search or advanced filters
        
        Examples:
        - Get first 20 results: /api/v1/buyer/listings/
        - Get all results: /api/v1/buyer/listings/?all=true
        - Get 100 per page: /api/v1/buyer/listings/?per_page=100
        - Get page 2: /api/v1/buyer/listings/?page=2&per_page=50
        - Search with all results: /api/v1/buyer/listings/?search=manchester&all=true
        """
        # Validate parameters
        serializer = MLSSearchParamsSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        params = serializer.validated_data

        # Unified search parameter - searches across all fields
        unified_search = request.query_params.get('search', '').strip()
        
        # Check if user wants all results
        get_all = request.query_params.get('all', '').lower() in ['true', '1', 'yes']
        
        # Determine per_page
        per_page = params.get('per_page', 20)
        if get_all:
            # Return all results at once
            per_page = 10000  # Large number to get everything
            page = 1
        else:
            page = params.get('page', 1)
            # Cap per_page at 1000 max
            per_page = min(per_page, 1000)

        result = mls_service.get_listings(
            city=params.get('city'),
            state=params.get('state'),
            zip_code=params.get('zip_code'),
            min_price=params.get('min_price'),
            max_price=params.get('max_price'),
            bedrooms=params.get('bedrooms'),
            bathrooms=params.get('bathrooms'),
            property_type=params.get('property_type'),
            status=params.get('status', 'for_sale'),
            page=page,
            per_page=per_page,
            sort_by=params.get('sort_by', 'price'),
            sort_order=params.get('sort_order', 'asc'),
            search=unified_search
        )

        return Response(result, status=status.HTTP_200_OK)


class MLSListingDetailView(views.APIView):
    """
    MLS Listing Detail API - Get detailed information about a specific listing
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Get detailed information for a specific MLS listing",
        responses={
            200: MLSListingDetailSerializer,
            404: "Listing not found"
        },
        tags=['MLS Listings']
    )
    def get(self, request, mls_number):
        """Get detailed listing by MLS number"""
        result = mls_service.get_listing_detail(mls_number)
        
        if not result:
            return Response(
                {"error": "Listing not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(result, status=status.HTTP_200_OK)


class MLSListingSearchView(views.APIView):
    """
    MLS Listing Search API - Search listings by keyword/address
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Search MLS listings by keyword or address",
        manual_parameters=[
            openapi.Parameter('query', openapi.IN_QUERY, description="Search query (address, neighborhood, etc.)", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('location', openapi.IN_QUERY, description="Location filter (city, state, zip)", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('per_page', openapi.IN_QUERY, description="Results per page", type=openapi.TYPE_INTEGER, default=20),
        ],
        responses={
            200: MLSListingResponseSerializer,
            400: "Bad Request - Query parameter required"
        },
        tags=['MLS Listings']
    )
    def get(self, request):
        """Search listings by keyword"""
        query = request.query_params.get('query')
        
        if not query:
            return Response(
                {"error": "Query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        location = request.query_params.get('location')
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        
        result = mls_service.search_listings(
            query=query,
            location=location,
            page=page,
            per_page=per_page
        )
        
        return Response(result, status=status.HTTP_200_OK)


class MLSFeaturedListingsView(views.APIView):
    """
    MLS Featured Listings API - Get featured/promoted listings
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Get featured/promoted MLS listings",
        manual_parameters=[
            openapi.Parameter('limit', openapi.IN_QUERY, description="Number of listings to return", type=openapi.TYPE_INTEGER, default=10),
        ],
        responses={
            200: MLSListingResponseSerializer,
        },
        tags=['MLS Listings']
    )
    def get(self, request):
        """Get featured listings"""
        limit = int(request.query_params.get('limit', 10))
        result = mls_service.get_featured_listings(limit=limit)
        return Response(result, status=status.HTTP_200_OK)


class MLSNearbyListingsView(views.APIView):
    """
    MLS Nearby Listings API - Get listings near a location
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Get MLS listings near a specific location (lat/lon)",
        manual_parameters=[
            openapi.Parameter('latitude', openapi.IN_QUERY, description="Latitude", type=openapi.TYPE_NUMBER, required=True),
            openapi.Parameter('longitude', openapi.IN_QUERY, description="Longitude", type=openapi.TYPE_NUMBER, required=True),
            openapi.Parameter('radius', openapi.IN_QUERY, description="Search radius in miles", type=openapi.TYPE_NUMBER, default=10),
            openapi.Parameter('limit', openapi.IN_QUERY, description="Number of listings to return", type=openapi.TYPE_INTEGER, default=20),
        ],
        responses={
            200: MLSListingResponseSerializer,
            400: "Bad Request - Latitude and longitude required"
        },
        tags=['MLS Listings']
    )
    def get(self, request):
        """Get nearby listings by coordinates"""
        lat = request.query_params.get('latitude')
        lon = request.query_params.get('longitude')
        
        if not lat or not lon:
            return Response(
                {"error": "Latitude and longitude are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            latitude = float(lat)
            longitude = float(lon)
        except ValueError:
            return Response(
                {"error": "Invalid latitude or longitude format"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        radius = float(request.query_params.get('radius', 10))
        limit = int(request.query_params.get('limit', 20))
        
        result = mls_service.get_nearby_listings(
            latitude=latitude,
            longitude=longitude,
            radius_miles=radius,
            limit=limit
        )
        
        return Response(result, status=status.HTTP_200_OK)


class BuyerAgentListingsView(views.APIView):
    """
    Get all published property listings created by agents.
    Supports filtering by price range, bedrooms, and location.
    """
    permission_classes = [AllowAny]  # Public access
    
    @swagger_auto_schema(
        operation_description="Get all published property listings from agents with optional filters",
        manual_parameters=[
            openapi.Parameter('min_price', openapi.IN_QUERY, description="Minimum price", type=openapi.TYPE_NUMBER),
            openapi.Parameter('max_price', openapi.IN_QUERY, description="Maximum price", type=openapi.TYPE_NUMBER),
            openapi.Parameter('bedrooms', openapi.IN_QUERY, description="Minimum bedrooms", type=openapi.TYPE_INTEGER),
            openapi.Parameter('city', openapi.IN_QUERY, description="Filter by city", type=openapi.TYPE_STRING),
            openapi.Parameter('state', openapi.IN_QUERY, description="Filter by state", type=openapi.TYPE_STRING),
            openapi.Parameter('zip_code', openapi.IN_QUERY, description="Filter by ZIP code", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('per_page', openapi.IN_QUERY, description="Results per page", type=openapi.TYPE_INTEGER, default=20),
        ],
        responses={
            200: openapi.Response(
                description="List of property listings",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'results': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'per_page': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            )
        },
        tags=['Buyer Listings']
    )
    def get(self, request):
        """Get all published agent listings with filters"""
        from agent.models import PropertyListing
        
        # Show all listings (draft, pending, published, etc)
        queryset = PropertyListing.objects.all()
        
        # Apply filters
        min_price = request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=float(min_price))
        
        max_price = request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=float(max_price))
        
        bedrooms = request.query_params.get('bedrooms')
        if bedrooms:
            queryset = queryset.filter(bedrooms__gte=int(bedrooms))
        
        city = request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        state = request.query_params.get('state')
        if state:
            queryset = queryset.filter(state__icontains=state)
        
        zip_code = request.query_params.get('zip_code')
        if zip_code:
            queryset = queryset.filter(zip_code=zip_code)
        
        # Order by created date (newest first)
        queryset = queryset.order_by('-created_at')
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        total = queryset.count()
        start = (page - 1) * per_page
        end = start + per_page
        
        listings = queryset[start:end]
        
        # Build response
        results = []
        for listing in listings:
            # Get primary photo
            primary_photo = listing.photos.filter(is_primary=True).first()
            if not primary_photo:
                primary_photo = listing.photos.first()
            
            photo_url = request.build_absolute_uri(primary_photo.photo.url) if primary_photo else None
            
            results.append({
                'id': listing.id,
                'mls_number': f"LOCAL-{listing.id}",
                'title': listing.title,
                'address': listing.street_address,
                'city': listing.city,
                'state': listing.state,
                'zip_code': listing.zip_code,
                'price': float(listing.price),
                'bedrooms': listing.bedrooms,
                'bathrooms': float(listing.bathrooms) if listing.bathrooms else None,
                'square_feet': listing.square_feet,
                'property_type': listing.property_type,
                'status': 'for_sale',
                'description': listing.description,
                'photo_url': photo_url,
                'photos_count': listing.photos.count(),
                'agent_name': f"{listing.agent.first_name} {listing.agent.last_name}".strip() or listing.agent.username,
                'agent_id': listing.agent.id,
                'agent_phone': listing.agent.phone_number,
                'agent_email': listing.agent.email,
                'created_at': listing.created_at.isoformat(),
                'updated_at': listing.updated_at.isoformat(),
                'published_at': listing.published_at.isoformat() if listing.published_at else None,
            })
        
        return Response({
            'results': results,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 0,
            'source': 'agent_listings'
        }, status=status.HTTP_200_OK)


class BuyerAgentListingDetailView(views.APIView):
    """
    Get detailed information about a single agent property listing.
    """
    permission_classes = [AllowAny]  # Public access
    
    @swagger_auto_schema(
        operation_description="Get detailed information about a specific agent property listing",
        responses={
            200: openapi.Response(
                description="Property listing details",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            404: "Not Found - Listing does not exist"
        },
        tags=['Buyer Listings']
    )
    def get(self, request, listing_id):
        """Get detailed agent listing information"""
        from agent.models import PropertyListing
        from django.db.models import Q
        
        try:
            listing = PropertyListing.objects.get(id=listing_id)
        except PropertyListing.DoesNotExist:
            return Response(
                {'error': 'Property listing not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all photos
        photos = []
        for photo in listing.photos.all():
            photos.append({
                'id': photo.id,
                'url': request.build_absolute_uri(photo.photo.url),
                'caption': photo.caption,
                'is_primary': photo.is_primary,
                'order': photo.order,
            })
        
        # Get all documents
        documents = []
        for doc in listing.listing_documents.all():
            documents.append({
                'id': doc.id,
                'title': doc.title,
                'document_type': doc.document_type,
                'url': request.build_absolute_uri(doc.document.url),
                'file_size': doc.file_size,
                'created_at': doc.created_at.isoformat(),
            })
        
        # Agent info
        agent = listing.agent
        agent_info = {
            'id': agent.id,
            'username': agent.username,
            'first_name': agent.first_name,
            'last_name': agent.last_name,
            'full_name': f"{agent.first_name} {agent.last_name}".strip() or agent.username,
            'email': agent.email,
            'phone_number': agent.phone_number,
            'license_number': agent.license_number,
        }
        
        # Build detailed response
        result = {
            'id': listing.id,
            'mls_number': f"LOCAL-{listing.id}",
            'title': listing.title,
            'street_address': listing.street_address,
            'city': listing.city,
            'state': listing.state,
            'zip_code': listing.zip_code,
            'property_type': listing.property_type,
            'bedrooms': listing.bedrooms,
            'bathrooms': float(listing.bathrooms) if listing.bathrooms else None,
            'square_feet': listing.square_feet,
            'description': listing.description,
            'price': float(listing.price),
            'status': listing.status,
            'photos': photos,
            'documents': documents,
            'agent': agent_info,
            'created_at': listing.created_at.isoformat(),
            'updated_at': listing.updated_at.isoformat(),
            'published_at': listing.published_at.isoformat() if listing.published_at else None,
        }
        
        return Response(result, status=status.HTTP_200_OK)


class ShowingScheduleCreateView(views.APIView):
    """
    Create a new showing schedule request for a property listing.
    Buyer can request to schedule a showing with the agent.
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Create a showing schedule request for a property listing",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['property_listing_id', 'requested_date', 'preferred_time'],
            properties={
                'property_listing_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Property listing ID'),
                'requested_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Preferred showing date (YYYY-MM-DD)'),
                'preferred_time': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['morning', 'afternoon', 'evening'],
                    description='Preferred time slot'
                ),
                'additional_notes': openapi.Schema(type=openapi.TYPE_STRING, description='Additional notes or requests'),
            }
        ),
        responses={
            201: openapi.Response(description="Showing schedule created successfully"),
            400: "Bad Request - Invalid data",
            404: "Not Found - Property listing not found"
        },
        tags=['Buyer Showings']
    )
    def post(self, request):
        """Create a showing schedule request"""
        from agent.models import PropertyListing
        from .models import ShowingSchedule
        from .serializers import ShowingScheduleCreateSerializer, ShowingScheduleSerializer
        
        serializer = ShowingScheduleCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the property listing
        listing_id = serializer.validated_data['property_listing_id']
        try:
            listing = PropertyListing.objects.get(id=listing_id, status__in=['published', 'for_sale'])
        except PropertyListing.DoesNotExist:
            return Response(
                {'error': 'Property listing not found or not available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create the showing schedule
        schedule = ShowingSchedule.objects.create(
            buyer=request.user,
            property_listing=listing,
            requested_date=serializer.validated_data['requested_date'],
            preferred_time=serializer.validated_data['preferred_time'],
            additional_notes=serializer.validated_data.get('additional_notes', ''),
            status='pending'
        )
        
        # Return the created schedule
        response_serializer = ShowingScheduleSerializer(schedule)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ShowingScheduleListView(views.APIView):
    """
    Get all showing schedules for the authenticated buyer.
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Get all showing schedules for the authenticated buyer",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="List of showing schedules",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                )
            )
        },
        tags=['Buyer Showings']
    )
    def get(self, request):
        """Get buyer's showing schedules"""
        from .models import ShowingSchedule
        from .serializers import ShowingScheduleSerializer
        
        schedules = ShowingSchedule.objects.filter(buyer=request.user)
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            schedules = schedules.filter(status=status_filter)
        
        serializer = ShowingScheduleSerializer(schedules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ShowingScheduleDetailView(views.APIView):
    """
    Get, update, or cancel a specific showing schedule.
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Get details of a specific showing schedule",
        responses={
            200: openapi.Response(description="Showing schedule details"),
            404: "Not Found - Schedule not found"
        },
        tags=['Buyer Showings']
    )
    def get(self, request, schedule_id):
        """Get showing schedule details"""
        from .models import ShowingSchedule
        from .serializers import ShowingScheduleSerializer
        
        try:
            schedule = ShowingSchedule.objects.get(id=schedule_id, buyer=request.user)
        except ShowingSchedule.DoesNotExist:
            return Response(
                {'error': 'Showing schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ShowingScheduleSerializer(schedule)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Cancel a showing schedule request",
        responses={
            200: "Schedule cancelled successfully",
            400: "Bad Request - Cannot cancel this schedule",
            404: "Not Found - Schedule not found"
        },
        tags=['Buyer Showings']
    )
    def delete(self, request, schedule_id):
        """Cancel a showing schedule"""
        from .models import ShowingSchedule
        
        try:
            schedule = ShowingSchedule.objects.get(id=schedule_id, buyer=request.user)
        except ShowingSchedule.DoesNotExist:
            return Response(
                {'error': 'Showing schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Only allow cancellation if status is pending or accepted
        if schedule.status not in ['pending', 'accepted']:
            return Response(
                {'error': f'Cannot cancel a schedule with status: {schedule.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        schedule.status = 'cancelled'
        schedule.save()
        
        return Response(
            {'message': 'Showing schedule cancelled successfully'},
            status=status.HTTP_200_OK
        )


class BuyerNotificationListView(views.APIView):
    """
    Get buyer's notifications
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Get all notifications for the buyer",
        manual_parameters=[
            openapi.Parameter('is_read', openapi.IN_QUERY, description="Filter by read status (true/false)", type=openapi.TYPE_BOOLEAN),
        ],
        responses={
            200: openapi.Response(
                description="List of notifications",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'unread_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'results': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                    }
                )
            )
        },
        tags=['Buyer Notifications']
    )
    def get(self, request):
        """Get buyer's notifications"""
        from .models import BuyerNotification
        from .serializers import BuyerNotificationSerializer
        
        notifications = BuyerNotification.objects.filter(buyer=request.user)
        
        # Filter by read status if provided
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            notifications = notifications.filter(is_read=is_read_bool)
        
        unread_count = BuyerNotification.objects.filter(buyer=request.user, is_read=False).count()
        
        serializer = BuyerNotificationSerializer(notifications, many=True)
        return Response({
            'count': notifications.count(),
            'unread_count': unread_count,
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class BuyerNotificationDetailView(views.APIView):
    """
    Mark notification as read
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Mark notification as read",
        responses={
            200: "Notification marked as read",
            404: "Notification not found"
        },
        tags=['Buyer Notifications']
    )
    def patch(self, request, notification_id):
        """Mark notification as read"""
        from .models import BuyerNotification
        from django.utils import timezone
        
        try:
            notification = BuyerNotification.objects.get(id=notification_id, buyer=request.user)
        except BuyerNotification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        return Response(
            {'message': 'Notification marked as read'},
            status=status.HTTP_200_OK
        )


class ShowingAgreementSignView(views.APIView):
    """
    Upload buyer signature for showing agreement - supports file uploads (photo/PDF)
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    parser_classes = (MultiPartParser, FormParser)
    
    @swagger_auto_schema(
        operation_description="Sign showing agreement after agent accepts - supports photo/PDF upload",
        manual_parameters=[
            openapi.Parameter('duration_type', openapi.IN_FORM, type=openapi.TYPE_STRING, description='Duration type: 7_days or one_property'),
            openapi.Parameter('property_address', openapi.IN_FORM, type=openapi.TYPE_STRING, description='Property address'),
            openapi.Parameter('signature', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True, description='Signature file (JPG, PNG, PDF, max 5MB)'),
            openapi.Parameter('agreement_accepted', openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, required=True, description='Must be true'),
        ],
        responses={
            201: openapi.Response(description="Agreement signed successfully"),
            400: "Bad Request - Invalid data or showing not accepted",
            404: "Not Found - Showing not found"
        },
        tags=['Buyer Showings']
    )
    def post(self, request, schedule_id):
        """Sign showing agreement with signature file"""
        from .models import ShowingSchedule, ShowingAgreement
        from .serializers import ShowingAgreementResponseSerializer
        from django.utils import timezone
        import base64
        from django.core.files.base import ContentFile
        
        # Get the showing schedule
        try:
            schedule = ShowingSchedule.objects.get(id=schedule_id, buyer=request.user)
        except ShowingSchedule.DoesNotExist:
            return Response(
                {'error': 'Showing schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if showing is accepted
        if schedule.status != 'accepted':
            return Response(
                {'error': 'Can only sign agreement for accepted showings'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if agreement already exists
        if hasattr(schedule, 'agreement') and schedule.agreement:
            return Response(
                {'error': 'Agreement already signed for this showing'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate required fields
        signature_file = request.FILES.get('signature')
        agreement_accepted_raw = request.data.get('agreement_accepted', '')
        # Safely convert to string and handle various input types
        agreement_accepted_value = str(agreement_accepted_raw).lower().strip() if agreement_accepted_raw else ''
        # Accept multiple truthy values: 'yes', 'true', '1', 'on'
        agreement_accepted = agreement_accepted_value in ['yes', 'true', '1', 'on']
        
        if not signature_file:
            return Response(
                {'error': 'Signature file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not agreement_accepted:
            return Response(
                {'error': 'Agreement must be accepted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 5MB)
        if signature_file.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'File size exceeds 5MB limit'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file type
        allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
        file_name = signature_file.name.lower()
        file_ext = file_name.split('.')[-1] if '.' in file_name else ''
        
        if file_ext not in allowed_extensions:
            return Response(
                {'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert file to base64 for storage
        signature_content = signature_file.read()
        signature_base64 = base64.b64encode(signature_content).decode('utf-8')
        
        # Create showing agreement
        agreement = ShowingAgreement.objects.create(
            showing_schedule=schedule,
            buyer=request.user,
            agent=schedule.property_listing.agent,
            duration_type=request.data.get('duration_type', 'one_property'),
            property_address=request.data.get('property_address', 
                f"{schedule.property_listing.street_address}, {schedule.property_listing.city}"),
            showing_date=schedule.confirmed_date or schedule.requested_date,
            signature=signature_base64,  # Store base64 encoded signature
            agreement_accepted=True,
            signed_at=timezone.now()
        )
        
        # Update showing status to completed
        schedule.status = 'completed'
        schedule.save()
        
        # Update existing notification to indicate signature uploaded
        from .models import BuyerNotification
        try:
            notification = BuyerNotification.objects.filter(
                buyer=request.user,
                showing_schedule=schedule,
                notification_type='showing_accepted'
            ).first()
            
            if notification:
                notification.title = "Agreement Signed Successfully ✓"
                notification.message = (
                    f"You have successfully signed the showing agreement for {schedule.property_listing.title}. "
                    f"The agreement is now complete and the agent has been notified."
                )
                notification.action_url = f'/api/v1/buyer/showings/{schedule.id}/agreement/'
                notification.action_text = 'View Agreement'
                notification.save()
        except Exception as e:
            pass  # Don't fail if notification update fails
        
        # Create notification for agent
        from seller.models import AgentNotification
        try:
            AgentNotification.objects.create(
                agent=schedule.property_listing.agent,
                showing_schedule=schedule,
                notification_type='agreement_signed',
                title=f"Buyer Signed Agreement for {schedule.property_listing.title}",
                message=(
                    f"{request.user.get_full_name() or request.user.username} has signed the showing agreement "
                    f"for {schedule.property_listing.title}. The showing is now completed."
                ),
                action_url=f'/api/v1/agent/showings/{schedule.id}/agreement/',
                action_text='View Agreement'
            )
        except Exception as e:
            pass  # Don't fail if agent notification fails
        
        response_serializer = ShowingAgreementResponseSerializer(agreement)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ShowingAgreementDetailView(views.APIView):
    """
    Get showing agreement details
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Get showing agreement details",
        responses={
            200: openapi.Response(description="Agreement details"),
            404: "Not Found - Agreement not found"
        },
        tags=['Buyer Showings']
    )
    def get(self, request, schedule_id):
        """Get showing agreement"""
        from .models import ShowingSchedule, ShowingAgreement
        from .serializers import ShowingAgreementResponseSerializer
        
        try:
            schedule = ShowingSchedule.objects.get(id=schedule_id, buyer=request.user)
            agreement = schedule.agreement
        except ShowingSchedule.DoesNotExist:
            return Response(
                {'error': 'Showing schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ShowingAgreement.DoesNotExist:
            return Response(
                {'error': 'No agreement found for this showing'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ShowingAgreementResponseSerializer(agreement)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BuyerRescheduleShowingView(views.APIView):
    """
    Buyer reschedule showing endpoint
    Buyer can change preferred date/time, status resets to 'pending'
    Agent receives notification about the reschedule request
    """
    permission_classes = [IsAuthenticated, IsBuyer]

    @swagger_auto_schema(
        operation_description="Reschedule a showing (buyer changes preferred date/time)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['preferred_date', 'preferred_time'],
            properties={
                'preferred_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='New preferred date (YYYY-MM-DD)'),
                'preferred_time': openapi.Schema(type=openapi.TYPE_STRING, description='New preferred time slot'),
                'additional_notes': openapi.Schema(type=openapi.TYPE_STRING, description='Optional notes about rescheduling'),
            }
        ),
        responses={
            200: openapi.Response(description="Showing rescheduled successfully"),
            400: "Bad Request - Validation errors",
            403: "Forbidden - Not your showing",
            404: "Not Found - Showing not found"
        },
        tags=['Buyer Showings']
    )
    def patch(self, request, schedule_id):
        """Reschedule showing"""
        from .models import ShowingSchedule
        from .serializers_reschedule import BuyerRescheduleShowingSerializer

        try:
            showing = ShowingSchedule.objects.select_related('property_listing').get(
                id=schedule_id,
                buyer=request.user
            )
        except ShowingSchedule.DoesNotExist:
            return Response(
                {'error': 'Showing schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BuyerRescheduleShowingSerializer(
            data=request.data,
            context={'showing': showing}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Store old values for tracking changes
        old_date = showing.requested_date
        old_time = showing.get_preferred_time_display()

        # Update showing with new preferred date/time
        showing.requested_date = serializer.validated_data['preferred_date']
        showing.preferred_time = serializer.validated_data['preferred_time']
        
        if 'additional_notes' in serializer.validated_data:
            showing.additional_notes = serializer.validated_data['additional_notes']

        # Reset status to pending if it was accepted (needs agent re-approval)
        if showing.status == 'accepted':
            showing.status = 'pending'
            showing.confirmed_date = None
            showing.confirmed_time = None

        # Set flag to indicate this is a reschedule (for signal detection)
        showing._is_rescheduled_by = 'buyer'
        showing._old_date = old_date
        showing._old_time = old_time
        
        showing.save()

        from .serializers import ShowingScheduleSerializer
        response_serializer = ShowingScheduleSerializer(showing)
        
        return Response({
            'message': 'Showing rescheduled successfully. Waiting for agent confirmation.',
            'showing': response_serializer.data
        }, status=status.HTTP_200_OK)


# ================== Legal Documents Views (GET Only) ==================

@swagger_auto_schema(
    method='get',
    operation_summary="Get Active Buyer Privacy Policy",
    operation_description="Get the currently active privacy policy for buyers",
    tags=['Buyer - Legal Documents'],
    responses={
        200: openapi.Response('Active privacy policy'),
        404: 'No active privacy policy found'
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buyer_get_privacy_policy(request):
    """Get the active privacy policy for buyers"""
    from superadmin.models import BuyerPrivacyPolicy
    from superadmin.serializers import BuyerPrivacyPolicySerializer
    
    try:
        policy = BuyerPrivacyPolicy.objects.filter(is_active=True).latest('effective_date')
        serializer = BuyerPrivacyPolicySerializer(policy)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except BuyerPrivacyPolicy.DoesNotExist:
        return Response({'error': 'No active privacy policy found'}, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='get',
    operation_summary="Get Active Buyer Terms & Conditions",
    operation_description="Get the currently active terms & conditions for buyers",
    tags=['Buyer - Legal Documents'],
    responses={
        200: openapi.Response('Active terms & conditions'),
        404: 'No active terms & conditions found'
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buyer_get_terms_conditions(request):
    """Get the active terms & conditions for buyers"""
    from superadmin.models import BuyerTermsConditions
    from superadmin.serializers import BuyerTermsConditionsSerializer
    
    try:
        terms = BuyerTermsConditions.objects.filter(is_active=True).latest('effective_date')
        serializer = BuyerTermsConditionsSerializer(terms)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except BuyerTermsConditions.DoesNotExist:
        return Response({'error': 'No active terms & conditions found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsBuyer])
def buyer_agreement_documents(request):
    """
    Get all active buyer agreement documents.
    Buyers can view buyer agreement documents.
    """
    from superadmin.models import PlatformDocument
    from superadmin.serializers import PlatformDocumentSerializer
    
    documents = PlatformDocument.objects.filter(
        document_type='buyer_agreement',
        is_active=True
    ).order_by('-created_at')
    
    serializer = PlatformDocumentSerializer(documents, many=True, context={'request': request})
    return Response({
        'count': documents.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


# ================== Saved Listings Views ==================

class SavedListingCreateView(views.APIView):
    """
    Save a listing for later viewing
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Save a listing by listing_id for later viewing",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['listing_id'],
            properties={
                'listing_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the property listing to save'),
                'notes': openapi.Schema(type=openapi.TYPE_STRING, description='Optional notes about this listing'),
            }
        ),
        responses={
            201: openapi.Response(description="Listing saved successfully"),
            400: "Bad Request - Invalid listing_id or already saved",
            404: "Not Found - Listing not found"
        },
        tags=['Buyer Saved Listings']
    )
    def post(self, request):
        """Save a listing"""
        from .models import SavedListing
        from .serializers import SavedListingSerializer
        from agent.models import PropertyListing
        
        listing_id = request.data.get('listing_id')
        
        if not listing_id:
            return Response(
                {'error': 'listing_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if listing exists
        try:
            PropertyListing.objects.get(id=listing_id)
        except PropertyListing.DoesNotExist:
            return Response(
                {'error': 'Listing not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already saved
        if SavedListing.objects.filter(buyer=request.user, listing_id=listing_id).exists():
            return Response(
                {'error': 'Listing already saved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create saved listing
        saved_listing = SavedListing.objects.create(
            buyer=request.user,
            listing_id=listing_id,
            notes=request.data.get('notes', '')
        )
        
        serializer = SavedListingSerializer(saved_listing)
        return Response(
            {
                'message': 'Listing saved successfully',
                'saved_listing': serializer.data
            },
            status=status.HTTP_201_CREATED
        )


class SavedListingListView(views.APIView):
    """
    List all saved listings for the authenticated buyer
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Get all saved listings for the authenticated buyer",
        responses={
            200: openapi.Response(description="List of saved listings"),
        },
        tags=['Buyer Saved Listings']
    )
    def get(self, request):
        """List saved listings"""
        from .models import SavedListing
        from .serializers import SavedListingDetailSerializer
        
        saved_listings = SavedListing.objects.filter(buyer=request.user)
        serializer = SavedListingDetailSerializer(saved_listings, many=True, context={'request': request})
        
        return Response(
            {
                'count': saved_listings.count(),
                'results': serializer.data
            },
            status=status.HTTP_200_OK
        )


class SavedListingDeleteView(views.APIView):
    """
    Remove a saved listing
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Remove a saved listing by its ID",
        responses={
            200: openapi.Response(description="Listing removed successfully"),
            404: "Not Found - Saved listing not found"
        },
        tags=['Buyer Saved Listings']
    )
    def delete(self, request, saved_listing_id):
        """Remove saved listing"""
        from .models import SavedListing
        
        try:
            saved_listing = SavedListing.objects.get(id=saved_listing_id, buyer=request.user)
            saved_listing.delete()
            return Response(
                {'message': 'Saved listing removed successfully'},
                status=status.HTTP_200_OK
            )
        except SavedListing.DoesNotExist:
            return Response(
                {'error': 'Saved listing not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class BuyerAgreementListView(views.APIView):
    """
    List all buyer agreements (showing agreements and buyer documents)
    Separated into pending and signed agreements
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Get all buyer agreements - showing agreements and buyer documents separated by status",
        responses={
            200: openapi.Response(description="List of buyer agreements"),
        },
        tags=['Buyer Agreements']
    )
    def get(self, request):
        """List all buyer agreements"""
        from .models import ShowingAgreement, BuyerDocument, ShowingSchedule
        from .serializers import ShowingAgreementResponseSerializer, BuyerDocumentListSerializer
        
        # Get showing agreements (pending and signed)
        pending_showing_agreements = ShowingAgreement.objects.filter(
            buyer=request.user,
            agreement_accepted=False
        ).select_related('showing_schedule', 'showing_schedule__property_listing', 'agent')
        
        signed_showing_agreements = ShowingAgreement.objects.filter(
            buyer=request.user,
            agreement_accepted=True
        ).select_related('showing_schedule', 'showing_schedule__property_listing', 'agent')
        
        # Get buyer documents
        buyer_documents = BuyerDocument.objects.filter(buyer=request.user)
        
        pending_serializer = ShowingAgreementResponseSerializer(
            pending_showing_agreements, 
            many=True,
            context={'request': request}
        )
        signed_serializer = ShowingAgreementResponseSerializer(
            signed_showing_agreements,
            many=True,
            context={'request': request}
        )
        documents_serializer = BuyerDocumentListSerializer(
            buyer_documents,
            many=True,
            context={'request': request}
        )
        
        return Response(
            {
                'pending_agreements': pending_serializer.data,
                'signed_agreements': signed_serializer.data,
                'documents': documents_serializer.data,
                'total_pending': pending_showing_agreements.count(),
                'total_signed': signed_showing_agreements.count(),
                'total_documents': buyer_documents.count()
            },
            status=status.HTTP_200_OK
        )


class BuyerAgreementDetailView(views.APIView):
    """
    Get single buyer agreement details
    Can view either a showing agreement or a buyer document
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Get a single buyer agreement details by agreement ID or document ID",
        responses={
            200: openapi.Response(description="Agreement details"),
            404: "Not Found - Agreement not found"
        },
        tags=['Buyer Agreements']
    )
    def get(self, request, agreement_id):
        """Get agreement details"""
        from .models import ShowingAgreement, BuyerDocument
        from .serializers import ShowingAgreementResponseSerializer, BuyerDocumentDetailSerializer
        
        # Try to get as showing agreement first
        try:
            agreement = ShowingAgreement.objects.select_related(
                'showing_schedule', 
                'showing_schedule__property_listing', 
                'agent'
            ).get(id=agreement_id, buyer=request.user)
            
            serializer = ShowingAgreementResponseSerializer(agreement, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ShowingAgreement.DoesNotExist:
            pass
        
        # Try to get as buyer document
        try:
            document = BuyerDocument.objects.get(id=agreement_id, buyer=request.user)
            serializer = BuyerDocumentDetailSerializer(document, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except BuyerDocument.DoesNotExist:
            pass
        
        return Response(
            {'error': 'Agreement not found'},
            status=status.HTTP_404_NOT_FOUND
        )

class BuyerAgreementDownloadView(views.APIView):
    """
    Download signed agreement PDF
    Serves the base64 encoded signature/PDF as a downloadable file
    """
    permission_classes = [IsAuthenticated, IsBuyer]
    
    @swagger_auto_schema(
        operation_description="Download signed agreement PDF",
        responses={
            200: openapi.Response(description="PDF file"),
            404: "Not Found - Agreement not found"
        },
        tags=['Buyer Agreements']
    )
    def get(self, request, agreement_id, filename=None):
        """Download agreement PDF"""
        from .models import ShowingAgreement
        import base64
        from django.http import FileResponse, HttpResponse
        
        try:
            agreement = ShowingAgreement.objects.get(id=agreement_id, buyer=request.user)
        except ShowingAgreement.DoesNotExist:
            return Response(
                {'error': 'Agreement not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not agreement.signature:
            return Response(
                {'error': 'No signature/PDF available for this agreement'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Decode base64 signature/PDF
            signature_bytes = base64.b64decode(agreement.signature)
            
            # Use provided filename or generate default
            download_filename = filename or f'agreement_{agreement.id}.pdf'
            
            # Create HTTP response with PDF content
            response = HttpResponse(
                signature_bytes,
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{download_filename}"'
            
            return response
        except Exception as e:
            return Response(
                {'error': f'Error downloading agreement: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )