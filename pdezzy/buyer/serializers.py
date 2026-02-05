from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import (
    Buyer,
    BuyerNotification,
    ShowingAgreement,
    SavedListing,
    BuyerDocument
)

User = Buyer


class UserSerializer(serializers.ModelSerializer):
    """User serializer for reading user data - returns comprehensive buyer profile"""
    profile_image_url = serializers.SerializerMethodField()
    mortgage_letter_url = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'profile_image', 'profile_image_url',
            'price_range', 'location', 'bedrooms', 'bathrooms',
            'mortgage_letter', 'mortgage_letter_url',
            'is_active', 'date_joined', 'last_login',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'created_at', 'updated_at']
        ref_name = 'BuyerUserSerializer'
    
    def get_full_name(self, obj):
        """Return formatted full name"""
        return obj.get_full_name() or obj.username
    
    def get_profile_image_url(self, obj):
        """Return absolute URL for profile image"""
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None
    
    def get_mortgage_letter_url(self, obj):
        """Return absolute URL for mortgage letter"""
        if obj.mortgage_letter:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.mortgage_letter.url)
            return obj.mortgage_letter.url
        return None


class RegisterResponseSerializer(serializers.Serializer):
    """Serializer for registration response"""
    access_token = serializers.CharField(help_text="JWT access token")
    refresh_token = serializers.CharField(help_text="JWT refresh token")
    email = serializers.EmailField(help_text="Registered email address")
    phone_number = serializers.CharField(help_text="Phone number", allow_null=True)
    price_range = serializers.CharField(help_text="Preferred price range", allow_null=True)
    location = serializers.CharField(help_text="Preferred buying area", allow_null=True)
    bedrooms = serializers.IntegerField(help_text="Preferred number of bedrooms", allow_null=True)
    bathrooms = serializers.IntegerField(help_text="Preferred number of bathrooms", allow_null=True)

    class Meta:
        ref_name = 'BuyerRegisterResponseSerializer'


class RegisterRequestSerializer(serializers.Serializer):
    """Serializer for registration request (Swagger documentation)"""
    name = serializers.CharField(required=True, help_text="Full name")
    email = serializers.EmailField(required=True, help_text="Email address")
    password = serializers.CharField(required=True, help_text="Password")
    password2 = serializers.CharField(required=True, help_text="Confirm password")
    phone_number = serializers.CharField(required=False, allow_blank=True, help_text="Phone number")
    price_range = serializers.CharField(required=False, allow_blank=True, help_text="Preferred price range")
    location = serializers.CharField(required=False, allow_blank=True, help_text="Preferred buying area")
    bedrooms = serializers.IntegerField(required=False, allow_null=True, help_text="Preferred number of bedrooms")
    bathrooms = serializers.IntegerField(required=False, allow_null=True, help_text="Preferred number of bathrooms")

    class Meta:
        ref_name = 'BuyerRegisterRequestSerializer'


class LoginRequestSerializer(serializers.Serializer):
    """Serializer for login request (Swagger documentation)"""
    email = serializers.EmailField(required=True, help_text="Email address")
    password = serializers.CharField(required=True, help_text="Password")

    class Meta:
        ref_name = 'BuyerLoginRequestSerializer'


class LoginResponseSerializer(serializers.Serializer):
    """Serializer for login response"""
    access_token = serializers.CharField(help_text="JWT access token")
    refresh_token = serializers.CharField(help_text="JWT refresh token")
    user = UserSerializer(help_text="User information")

    class Meta:
        ref_name = 'BuyerLoginResponseSerializer'


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for buyer registration"""
    name = serializers.CharField(write_only=True, required=True, help_text="Full name")
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, help_text="Confirm password")
    access_token = serializers.SerializerMethodField()
    refresh_token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'name', 'email', 'password', 'password2', 'phone_number',
            'price_range', 'location', 'bedrooms', 'bathrooms',
            'access_token', 'refresh_token'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'phone_number': {'required': False},
            'price_range': {'required': False},
            'location': {'required': False},
            'bedrooms': {'required': False},
            'bathrooms': {'required': False},
        }
        ref_name = 'BuyerRegisterSerializer'

    def validate(self, attrs):
        """Validate that passwords match and email is unique"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        # Check if email already exists
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError(
                {"email": "This email address is already registered."}
            )
        return attrs

    def create(self, validated_data):
        """Create user and return tokens"""
        validated_data.pop('password2')
        
        # Split name into first_name and last_name
        full_name = validated_data.pop('name', '')
        name_parts = full_name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Generate username from email
        email = validated_data.get('email', '')
        username = email.split('@')[0] if email else ''
        
        # Ensure username is unique
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            **validated_data
        )
        return user

    def get_access_token(self, obj):
        """Generate access token on user creation"""
        refresh = RefreshToken.for_user(obj)
        # Add user_type claim for proper authentication
        refresh['user_type'] = 'buyer'
        return str(refresh.access_token)

    def get_refresh_token(self, obj):
        """Generate refresh token on user creation"""
        refresh = RefreshToken.for_user(obj)
        # Add user_type claim for proper authentication
        refresh['user_type'] = 'buyer'
        return str(refresh)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer with additional user information"""
    
    class Meta:
        ref_name = 'BuyerCustomTokenObtainPairSerializer'
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['user_type'] = 'buyer'  # Add user_type claim for authentication
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """Custom token refresh serializer that preserves user_type claim"""
    
    class Meta:
        ref_name = 'BuyerCustomTokenRefreshSerializer'
    
    def validate(self, attrs):
        refresh = RefreshToken(attrs['refresh'])
        
        # Ensure user_type claim is present
        if 'user_type' not in refresh:
            refresh['user_type'] = 'buyer'
        
        data = {
            'access': str(refresh.access_token),
        }
        
        return data


class LoginSerializer(serializers.Serializer):
    """Serializer for user login with email and password"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    access_token = serializers.SerializerMethodField(read_only=True)
    refresh_token = serializers.SerializerMethodField(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        ref_name = 'BuyerLoginSerializer'

    def validate(self, attrs):
        from django.contrib.auth.hashers import check_password
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError("Email and password are required.")

        try:
            user = User.objects.get(email=email)
            if not check_password(password, user.password):
                raise serializers.ValidationError("Invalid credentials.")
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials.")

        attrs['user'] = user
        return attrs

    def get_access_token(self, obj):
        user = obj.get('user')
        if user:
            refresh = RefreshToken.for_user(user)
            # Add user_type claim for custom authentication
            refresh['user_type'] = 'buyer'
            return str(refresh.access_token)
        return None

    def get_refresh_token(self, obj):
        user = obj.get('user')
        if user:
            refresh = RefreshToken.for_user(user)
            # Add user_type claim for custom authentication
            refresh['user_type'] = 'buyer'
            return str(refresh)
        return None


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'phone_number', 'profile_image', 'price_range', 'location', 'bedrooms', 'bathrooms',
            'mortgage_letter'
        ]
        extra_kwargs = {
            'username': {'required': False},
            'email': {'required': False},
            'profile_image': {'required': False},
            'mortgage_letter': {'required': False},
        }
        ref_name = 'BuyerProfileUpdateSerializer'
    
    def validate_mortgage_letter(self, value):
        """Validate mortgage letter file"""
        if value:
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("Mortgage letter file size must not exceed 10MB")
            
            allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
            file_ext = value.name.split('.')[-1].lower()
            if file_ext not in allowed_extensions:
                raise serializers.ValidationError(f"Supported formats: {', '.join(allowed_extensions)}")
        
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        ref_name = 'BuyerChangePasswordSerializer'

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {"new_password": "Password fields didn't match."}
            )
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout"""
    refresh = serializers.CharField()

    class Meta:
        ref_name = 'BuyerLogoutSerializer'


# =============================================================================
# MLS Listing Serializers
# =============================================================================

class MLSListingPhotoSerializer(serializers.Serializer):
    """Serializer for MLS listing photos"""
    url = serializers.URLField(help_text="Photo URL")
    caption = serializers.CharField(allow_null=True, required=False, help_text="Photo caption")
    is_primary = serializers.BooleanField(default=False, help_text="Is primary photo")

    class Meta:
        ref_name = 'BuyerMLSListingPhotoSerializer'


class MLSListingAgentSerializer(serializers.Serializer):
    """Serializer for listing agent info"""
    id = serializers.IntegerField(help_text="Agent ID")
    name = serializers.CharField(help_text="Agent name")
    email = serializers.EmailField(allow_null=True, required=False, help_text="Agent email")
    phone = serializers.CharField(allow_null=True, required=False, help_text="Agent phone")

    class Meta:
        ref_name = 'BuyerMLSListingAgentSerializer'


class MLSListingSerializer(serializers.Serializer):
    """Serializer for MLS listing data"""
    mls_number = serializers.CharField(help_text="MLS listing number")
    title = serializers.CharField(help_text="Property title")
    address = serializers.CharField(help_text="Street address")
    city = serializers.CharField(help_text="City")
    state = serializers.CharField(help_text="State")
    zip_code = serializers.CharField(help_text="ZIP code")
    price = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Listing price")
    bedrooms = serializers.IntegerField(allow_null=True, help_text="Number of bedrooms")
    bathrooms = serializers.DecimalField(
        max_digits=3, decimal_places=1, 
        allow_null=True, 
        help_text="Number of bathrooms"
    )
    square_feet = serializers.IntegerField(allow_null=True, help_text="Square footage")
    property_type = serializers.CharField(help_text="Property type")
    status = serializers.CharField(help_text="Listing status (for_sale, pending, sold)")
    description = serializers.CharField(allow_null=True, required=False, help_text="Property description")
    photo_url = serializers.URLField(allow_null=True, required=False, help_text="Primary photo URL")
    photos = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of photo URLs"
    )
    agent_name = serializers.CharField(allow_null=True, required=False, help_text="Listing agent name")
    agent_id = serializers.IntegerField(allow_null=True, required=False, help_text="Agent ID")
    created_at = serializers.DateTimeField(required=False, help_text="Listing creation date")
    updated_at = serializers.DateTimeField(required=False, help_text="Last update date")

    class Meta:
        ref_name = 'BuyerMLSListingSerializer'


class MLSListingDetailSerializer(serializers.Serializer):
    """Serializer for detailed MLS listing data"""
    mls_number = serializers.CharField(help_text="MLS listing number")
    title = serializers.CharField(help_text="Property title")
    address = serializers.CharField(help_text="Street address")
    city = serializers.CharField(help_text="City")
    state = serializers.CharField(help_text="State")
    zip_code = serializers.CharField(help_text="ZIP code")
    price = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Listing price")
    bedrooms = serializers.IntegerField(allow_null=True, help_text="Number of bedrooms")
    bathrooms = serializers.DecimalField(
        max_digits=3, decimal_places=1, 
        allow_null=True, 
        help_text="Number of bathrooms"
    )
    square_feet = serializers.IntegerField(allow_null=True, help_text="Square footage")
    property_type = serializers.CharField(help_text="Property type")
    status = serializers.CharField(help_text="Listing status")
    description = serializers.CharField(allow_null=True, required=False, help_text="Property description")
    photos = MLSListingPhotoSerializer(many=True, required=False, help_text="Property photos")
    agent = MLSListingAgentSerializer(required=False, help_text="Listing agent details")
    created_at = serializers.DateTimeField(required=False, help_text="Listing creation date")
    updated_at = serializers.DateTimeField(required=False, help_text="Last update date")
    source = serializers.CharField(required=False, help_text="Data source (mls or local)")

    class Meta:
        ref_name = 'BuyerMLSListingDetailSerializer'


class MLSListingResponseSerializer(serializers.Serializer):
    """Serializer for paginated MLS listing response"""
    results = MLSListingSerializer(many=True, help_text="List of listings")
    total = serializers.IntegerField(help_text="Total number of listings")
    page = serializers.IntegerField(help_text="Current page number")
    per_page = serializers.IntegerField(help_text="Results per page")
    total_pages = serializers.IntegerField(help_text="Total number of pages")
    source = serializers.CharField(required=False, help_text="Data source")

    class Meta:
        ref_name = 'BuyerMLSListingResponseSerializer'


class MLSSearchParamsSerializer(serializers.Serializer):
    """Serializer for MLS listing search parameters"""
    city = serializers.CharField(required=False, help_text="Filter by city")
    state = serializers.CharField(required=False, help_text="Filter by state")
    zip_code = serializers.CharField(required=False, help_text="Filter by ZIP code")
    mls_number = serializers.CharField(required=False, help_text="Filter by MLS number")
    title = serializers.CharField(required=False, help_text="Filter by title")
    address = serializers.CharField(required=False, help_text="Filter by address")
    min_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, 
        required=False, 
        help_text="Minimum price filter"
    )
    max_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, 
        required=False, 
        help_text="Maximum price filter"
    )
    bedrooms = serializers.IntegerField(required=False, help_text="Minimum bedrooms")
    bathrooms = serializers.IntegerField(required=False, help_text="Minimum bathrooms")
    property_type = serializers.ChoiceField(
        choices=[
            ('house', 'House'),
            ('apartment', 'Apartment'),
            ('condo', 'Condominium'),
            ('townhouse', 'Townhouse'),
            ('land', 'Land'),
            ('commercial', 'Commercial'),
        ],
        required=False,
        help_text="Property type filter"
    )
    status = serializers.ChoiceField(
        choices=[
            ('for_sale', 'For Sale'),
            ('pending', 'Pending'),
            ('sold', 'Sold'),
        ],
        default='for_sale',
        required=False,
        help_text="Listing status filter"
    )
    page = serializers.IntegerField(default=1, min_value=1, help_text="Page number")
    per_page = serializers.IntegerField(
        default=20, 
        min_value=1, 
        max_value=100, 
        help_text="Results per page (max 100)"
    )
    sort_by = serializers.ChoiceField(
        choices=[
            ('price', 'Price'),
            ('created_at', 'Date Listed'),
            ('bedrooms', 'Bedrooms'),
            ('square_feet', 'Square Feet'),
        ],
        default='price',
        required=False,
        help_text="Sort field"
    )
    sort_order = serializers.ChoiceField(
        choices=[('asc', 'Ascending'), ('desc', 'Descending')],
        default='asc',
        required=False,
        help_text="Sort order"
    )

    class Meta:
        ref_name = 'BuyerMLSSearchParamsSerializer'


class MLSKeywordSearchSerializer(serializers.Serializer):
    """Serializer for keyword search"""
    query = serializers.CharField(help_text="Search query (address, neighborhood, etc.)")
    location = serializers.CharField(required=False, help_text="Location filter (city, state, zip)")
    page = serializers.IntegerField(default=1, min_value=1, help_text="Page number")
    per_page = serializers.IntegerField(default=20, min_value=1, max_value=100, help_text="Results per page")

    class Meta:
        ref_name = 'BuyerMLSKeywordSearchSerializer'


class FavoriteListingSerializer(serializers.Serializer):
    """Serializer for favoriting a listing"""
    mls_number = serializers.CharField(help_text="MLS listing number to favorite")
    
    class Meta:
        ref_name = 'BuyerFavoriteListingSerializer'


class AgentPropertyListingDetailSerializer(serializers.Serializer):
    """Detailed serializer for a single agent property listing"""
    id = serializers.IntegerField(help_text="Property listing ID")
    mls_number = serializers.CharField(help_text="Local MLS number")
    title = serializers.CharField(help_text="Property title")
    
    # Address
    street_address = serializers.CharField(help_text="Street address")
    city = serializers.CharField(help_text="City")
    state = serializers.CharField(help_text="State")
    zip_code = serializers.CharField(help_text="ZIP code")
    
    # Property Details
    property_type = serializers.CharField(help_text="Type of property")
    bedrooms = serializers.IntegerField(allow_null=True, help_text="Number of bedrooms")
    bathrooms = serializers.DecimalField(
        max_digits=3, decimal_places=1, 
        allow_null=True, 
        help_text="Number of bathrooms"
    )
    square_feet = serializers.IntegerField(allow_null=True, help_text="Square footage")
    description = serializers.CharField(allow_null=True, help_text="Property description")
    
    # Pricing
    price = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Listing price")
    
    # Status
    status = serializers.CharField(help_text="Listing status")
    
    # Photos
    photos = serializers.ListField(
        child=serializers.DictField(),
        help_text="Property photos"
    )
    
    # Agent Information
    agent = serializers.DictField(help_text="Agent information")
    
    # Timestamps
    created_at = serializers.DateTimeField(help_text="Created date")
    updated_at = serializers.DateTimeField(help_text="Updated date")
    published_at = serializers.DateTimeField(allow_null=True, help_text="Published date")
    
    class Meta:
        ref_name = 'BuyerAgentPropertyListingDetailSerializer'


class ShowingScheduleSerializer(serializers.Serializer):
    """Serializer for showing schedule"""
    id = serializers.IntegerField(read_only=True, help_text="Schedule ID")
    buyer = serializers.SerializerMethodField(help_text="Buyer information")
    property_listing = serializers.SerializerMethodField(help_text="Property listing details")
    
    requested_date = serializers.DateField(help_text="Requested showing date")
    preferred_time = serializers.ChoiceField(
        choices=[
            ('morning', 'Morning (9 AM - 12 PM)'),
            ('afternoon', 'Afternoon (12 PM - 5 PM)'),
            ('evening', 'Evening (5 PM - 8 PM)'),
        ],
        help_text="Preferred time slot"
    )
    additional_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Additional notes or requests"
    )
    
    status = serializers.CharField(read_only=True, help_text="Status of showing request")
    agent_response = serializers.CharField(read_only=True, allow_null=True, help_text="Agent's response")
    responded_at = serializers.DateTimeField(read_only=True, allow_null=True, help_text="Response timestamp")
    
    confirmed_date = serializers.DateField(read_only=True, allow_null=True, help_text="Confirmed date")
    confirmed_time = serializers.TimeField(read_only=True, allow_null=True, help_text="Confirmed time")
    
    created_at = serializers.DateTimeField(read_only=True, help_text="Created timestamp")
    updated_at = serializers.DateTimeField(read_only=True, help_text="Updated timestamp")
    
    # Agreement status
    has_agreement = serializers.SerializerMethodField(help_text="Whether showing agreement is signed")
    agreement_signed_at = serializers.SerializerMethodField(help_text="When agreement was signed")
    
    def get_has_agreement(self, obj):
        return hasattr(obj, 'agreement')
    
    def get_agreement_signed_at(self, obj):
        if hasattr(obj, 'agreement'):
            return obj.agreement.signed_at
        return None
    
    def get_buyer(self, obj):
        if hasattr(obj, 'buyer'):
            return {
                'id': obj.buyer.id,
                'username': obj.buyer.username,
                'email': obj.buyer.email,
                'phone_number': obj.buyer.phone_number,
            }
        return None
    
    def get_property_listing(self, obj):
        if hasattr(obj, 'property_listing'):
            listing = obj.property_listing
            return {
                'id': listing.id,
                'title': listing.title,
                'address': f"{listing.street_address}, {listing.city}, {listing.state}",
                'price': float(listing.price),
            }
        return None
    
    class Meta:
        ref_name = 'BuyerShowingScheduleSerializer'


class ShowingScheduleCreateSerializer(serializers.Serializer):
    """Serializer for creating a showing schedule request"""
    property_listing_id = serializers.IntegerField(help_text="ID of the property listing")
    requested_date = serializers.DateField(help_text="Preferred showing date (YYYY-MM-DD)")
    preferred_time = serializers.ChoiceField(
        choices=[
            ('morning', 'Morning (9 AM - 12 PM)'),
            ('afternoon', 'Afternoon (12 PM - 5 PM)'),
            ('evening', 'Evening (5 PM - 8 PM)'),
        ],
        help_text="Preferred time slot"
    )
    additional_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Any special requests or questions"
    )
    
    def validate_requested_date(self, value):
        """Ensure requested date is not in the past"""
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Requested date cannot be in the past")
        return value
    
    class Meta:
        ref_name = 'BuyerShowingScheduleCreateSerializer'



class BuyerNotificationSerializer(serializers.Serializer):
    """Serializer for buyer notifications"""
    id = serializers.IntegerField(read_only=True)
    notification_type = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    read_at = serializers.DateTimeField(read_only=True, allow_null=True)
    action_url = serializers.CharField(read_only=True, allow_null=True)
    action_text = serializers.CharField(read_only=True, allow_null=True)
    showing_schedule_id = serializers.IntegerField(source='showing_schedule.id', read_only=True, allow_null=True)
    property_title = serializers.CharField(source='showing_schedule.property_listing.title', read_only=True, allow_null=True)
    agent_name = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    
    # Additional fields for showing_accepted notification type
    buyer_details = serializers.SerializerMethodField()
    agent_details = serializers.SerializerMethodField()
    showing_details = serializers.SerializerMethodField()
    property_details = serializers.SerializerMethodField()
    
    def get_agent_name(self, obj):
        if obj.showing_schedule and obj.showing_schedule.property_listing:
            agent = obj.showing_schedule.property_listing.agent
            return agent.get_full_name() or agent.username
        return None
    
    def get_buyer_details(self, obj):
        """Return buyer details if notification is showing_accepted"""
        if obj.notification_type in ['showing_accepted', 'showing_declined'] and obj.showing_schedule:
            buyer = obj.showing_schedule.buyer
            return {
                'id': buyer.id,
                'username': buyer.username,
                'full_name': buyer.get_full_name() or buyer.username,
                'email': buyer.email,
                'phone_number': getattr(buyer, 'phone_number', ''),
                'first_name': buyer.first_name,
                'last_name': buyer.last_name,
            }
        return None
    
    def get_agent_details(self, obj):
        """Return agent details if notification is showing_accepted"""
        if obj.notification_type in ['showing_accepted', 'showing_declined'] and obj.showing_schedule and obj.showing_schedule.property_listing:
            agent = obj.showing_schedule.property_listing.agent
            return {
                'id': agent.id,
                'username': agent.username,
                'full_name': agent.get_full_name() or agent.username,
                'email': agent.email,
                'phone_number': getattr(agent, 'phone_number', ''),
                'first_name': agent.first_name,
                'last_name': agent.last_name,
                'license_number': getattr(agent, 'license_number', ''),
            }
        return None
    
    def get_showing_details(self, obj):
        """Return showing schedule details if notification is showing_accepted"""
        if obj.notification_type in ['showing_accepted', 'showing_declined'] and obj.showing_schedule:
            schedule = obj.showing_schedule
            return {
                'id': schedule.id,
                'requested_date': schedule.requested_date.isoformat() if schedule.requested_date else None,
                'confirmed_date': schedule.confirmed_date.isoformat() if schedule.confirmed_date else None,
                'confirmed_time': schedule.confirmed_time.strftime('%H:%M') if schedule.confirmed_time else None,
                'preferred_time': schedule.preferred_time,
                'status': schedule.status,
                'additional_notes': schedule.additional_notes,
            }
        return None
    
    def get_property_details(self, obj):
        """Return property listing details if notification is showing_accepted"""
        if obj.notification_type in ['showing_accepted', 'showing_declined'] and obj.showing_schedule and obj.showing_schedule.property_listing:
            prop = obj.showing_schedule.property_listing
            return {
                'id': prop.id,
                'title': prop.title,
                'address': f"{prop.street_address}, {prop.city}, {prop.state}",
                'street_address': prop.street_address,
                'city': prop.city,
                'state': prop.state,
                'zip_code': prop.zip_code,
                'price': float(prop.price) if prop.price else None,
                'bedrooms': prop.bedrooms,
                'bathrooms': float(prop.bathrooms) if prop.bathrooms else None,
                'square_feet': prop.square_feet,
                'property_type': prop.property_type,
                'description': prop.description,
            }
        return None
    
    class Meta:
        ref_name = 'BuyerBuyerNotificationSerializer'


class ShowingAgreementSerializer(serializers.Serializer):
    """Serializer for showing agreement creation"""
    duration_type = serializers.ChoiceField(
        choices=[('7_days', '7 Days'), ('one_property', 'One Property Only')],
        default='one_property',
        help_text="Duration of the agreement"
    )
    property_address = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Property address (optional)"
    )
    signature = serializers.CharField(
        help_text="Base64 encoded signature image"
    )
    agreement_accepted = serializers.BooleanField(
        help_text="Buyer agrees to terms and conditions"
    )
    
    def validate_agreement_accepted(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the agreement terms to continue")
        return value
    
    def validate_signature(self, value):
        if not value or len(value) < 50:
            raise serializers.ValidationError("Please provide a valid signature")
        return value
    
    class Meta:
        ref_name = 'BuyerShowingAgreementSerializer'


class ShowingAgreementResponseSerializer(serializers.Serializer):
    """Serializer for showing agreement response with all details"""
    id = serializers.IntegerField(read_only=True)
    showing_schedule_id = serializers.IntegerField(source='showing_schedule.id', read_only=True)
    duration_type = serializers.CharField(read_only=True)
    property_address = serializers.CharField(read_only=True, allow_null=True)
    showing_date = serializers.DateField(read_only=True)
    agreement_accepted = serializers.BooleanField(read_only=True)
    signed_at = serializers.DateTimeField(read_only=True)
    terms_text = serializers.CharField(read_only=True, allow_null=True)
    signature_url = serializers.SerializerMethodField()
    
    # Basic names
    buyer_name = serializers.SerializerMethodField()
    agent_name = serializers.SerializerMethodField()
    
    # Full details
    buyer_details = serializers.SerializerMethodField()
    agent_details = serializers.SerializerMethodField()
    showing_details = serializers.SerializerMethodField()
    property_details = serializers.SerializerMethodField()
    
    def get_signature_url(self, obj):
        """Return URL to download the signed agreement PDF"""
        request = self.context.get('request')
        if request and obj.id:
            return request.build_absolute_uri(f'/api/v1/buyer/agreements/{obj.id}/download/agreement_{obj.id}.pdf')
        return None
    
    def get_buyer_name(self, obj):
        return obj.buyer.get_full_name() or obj.buyer.username
    
    def get_agent_name(self, obj):
        return obj.agent.get_full_name() or obj.agent.username
    
    def get_buyer_details(self, obj):
        """Return full buyer details"""
        buyer = obj.buyer
        return {
            'id': buyer.id,
            'username': buyer.username,
            'full_name': buyer.get_full_name() or buyer.username,
            'email': buyer.email,
            'phone_number': getattr(buyer, 'phone_number', ''),
            'first_name': buyer.first_name,
            'last_name': buyer.last_name,
        }
    
    def get_agent_details(self, obj):
        """Return full agent details"""
        agent = obj.agent
        return {
            'id': agent.id,
            'username': agent.username,
            'full_name': agent.get_full_name() or agent.username,
            'email': agent.email,
            'phone_number': getattr(agent, 'phone_number', ''),
            'first_name': agent.first_name,
            'last_name': agent.last_name,
            'license_number': getattr(agent, 'license_number', ''),
        }
    
    def get_showing_details(self, obj):
        """Return full showing schedule details"""
        schedule = obj.showing_schedule
        return {
            'id': schedule.id,
            'requested_date': schedule.requested_date.isoformat() if schedule.requested_date else None,
            'confirmed_date': schedule.confirmed_date.isoformat() if schedule.confirmed_date else None,
            'confirmed_time': schedule.confirmed_time.strftime('%H:%M') if schedule.confirmed_time else None,
            'preferred_time': schedule.preferred_time,
            'status': schedule.status,
            'additional_notes': schedule.additional_notes,
        }
    
    def get_property_details(self, obj):
        """Return full property listing details"""
        prop = obj.showing_schedule.property_listing
        return {
            'id': prop.id,
            'title': prop.title,
            'address': f"{prop.street_address}, {prop.city}, {prop.state}",
            'street_address': prop.street_address,
            'city': prop.city,
            'state': prop.state,
            'zip_code': prop.zip_code,
            'price': float(prop.price) if prop.price else None,
            'bedrooms': prop.bedrooms,
            'bathrooms': float(prop.bathrooms) if prop.bathrooms else None,
            'square_feet': prop.square_feet,
            'property_type': prop.property_type,
            'description': prop.description,
        }
    
    class Meta:
        ref_name = 'BuyerShowingAgreementResponseSerializer'


class BuyerDocumentListSerializer(serializers.ModelSerializer):
    """Serializer for listing buyer agreement documents"""
    document_url = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    agent_name = serializers.SerializerMethodField()
    property_name = serializers.SerializerMethodField()
    property_address = serializers.SerializerMethodField()
    signature_date = serializers.SerializerMethodField()
    
    class Meta:
        model = BuyerDocument
        fields = [
            'id', 'title', 'description', 'document_url', 
            'status', 'agent_name', 'property_name', 'property_address',
            'signature_date', 'file_size', 'created_at'
        ]
        read_only_fields = fields
        ref_name = 'BuyerDocumentListSerializer'
    
    def get_document_url(self, obj):
        request = self.context.get('request')
        if obj.document_file:
            if request:
                return request.build_absolute_uri(obj.document_file.url)
            return obj.document_file.url
        return None
    
    def get_status(self, obj):
        """Return document status based on title"""
        if 'pending' in obj.title.lower():
            return 'pending'
        elif 'signed' in obj.title.lower() or obj.description and 'signed' in obj.description.lower():
            return 'signed'
        return 'signed'
    
    def get_agent_name(self, obj):
        """Extract agent name from description if available"""
        if obj.description and 'Agent:' in obj.description:
            try:
                agent_info = obj.description.split('Agent:')[1].split('|')[0].strip()
                return agent_info
            except:
                pass
        return 'Not specified'
    
    def get_property_name(self, obj):
        """Extract property name from title"""
        if obj.title:
            return obj.title.split('-')[0].strip() if '-' in obj.title else obj.title
        return 'N/A'
    
    def get_property_address(self, obj):
        """Extract address from description"""
        if obj.description and 'Address:' in obj.description:
            try:
                address = obj.description.split('Address:')[1].split('|')[0].strip()
                return address
            except:
                pass
        return 'Not specified'
    
    def get_signature_date(self, obj):
        """Return signature date"""
        return obj.created_at.date().isoformat() if obj.created_at else None


class BuyerDocumentDetailSerializer(serializers.ModelSerializer):
    """Serializer for viewing a single agreement document"""
    document_url = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = BuyerDocument
        fields = [
            'id', 'title', 'description', 'document_url',
            'status', 'file_size', 'file_size_mb', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
        ref_name = 'BuyerDocumentDetailSerializer'
    
    def get_document_url(self, obj):
        request = self.context.get('request')
        if obj.document_file:
            if request:
                return request.build_absolute_uri(obj.document_file.url)
            return obj.document_file.url
        return None
    
    def get_status(self, obj):
        if 'pending' in obj.title.lower():
            return 'pending'
        elif 'signed' in obj.title.lower() or obj.description and 'signed' in obj.description.lower():
            return 'signed'
        return 'signed'
    
    def get_file_size_mb(self, obj):
        return round(obj.file_size / (1024 * 1024), 2)


class SavedListingSerializer(serializers.ModelSerializer):
    """Serializer for creating a saved listing"""
    
    class Meta:
        model = SavedListing
        fields = ['id', 'listing_id', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']
        ref_name = 'BuyerSavedListingSerializer'


class SavedListingDetailSerializer(serializers.ModelSerializer):
    """Serializer for listing saved listings with property details"""
    listing_details = serializers.SerializerMethodField()
    
    class Meta:
        model = SavedListing
        fields = ['id', 'listing_id', 'notes', 'listing_details', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        ref_name = 'BuyerSavedListingDetailSerializer'
    
    def get_listing_details(self, obj):
        """Get property listing details with photos and documents"""
        from agent.models import PropertyListing
        try:
            listing = PropertyListing.objects.prefetch_related('photos', 'listing_documents').get(id=obj.listing_id)
            request = self.context.get('request')
            
            # Get photos
            photos = []
            for photo in listing.photos.all():
                try:
                    if photo.photo:
                        photo_url = request.build_absolute_uri(photo.photo.url) if request else photo.photo.url
                    else:
                        photo_url = None
                except (ValueError, AttributeError):
                    photo_url = None
                    
                photos.append({
                    'id': photo.id,
                    'photo': photo_url,
                    'caption': photo.caption,
                    'is_primary': photo.is_primary,
                    'order': photo.order,
                    'file_size': photo.file_size,
                    'created_at': photo.created_at.isoformat() if photo.created_at else None,
                })
            
            # Get documents
            documents = []
            for doc in listing.listing_documents.all():
                try:
                    if doc.document:
                        doc_url = request.build_absolute_uri(doc.document.url) if request else doc.document.url
                    else:
                        doc_url = None
                except (ValueError, AttributeError):
                    doc_url = None
                    
                documents.append({
                    'id': doc.id,
                    'document': doc_url,
                    'document_type': doc.document_type,
                    'title': doc.title,
                    'file_size': doc.file_size,
                    'created_at': doc.created_at.isoformat() if doc.created_at else None,
                })
            
            return {
                'id': listing.id,
                'title': listing.title,
                'address': f"{listing.street_address}, {listing.city}, {listing.state}",
                'street_address': listing.street_address,
                'city': listing.city,
                'state': listing.state,
                'zip_code': listing.zip_code,
                'price': float(listing.price) if listing.price else None,
                'bedrooms': listing.bedrooms,
                'bathrooms': float(listing.bathrooms) if listing.bathrooms else None,
                'square_feet': listing.square_feet,
                'property_type': listing.property_type,
                'description': listing.description,
                'status': listing.status,
                'photos': photos,
                'documents': documents,
                'photo_count': len(photos),
                'document_count': len(documents),
            }
        except PropertyListing.DoesNotExist:
            return None
