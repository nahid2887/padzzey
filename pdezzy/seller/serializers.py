from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Seller, SellingRequest, SellerNotification, PropertyDocument
from agent.models import Agent

User = Seller


class UserSerializer(serializers.ModelSerializer):
    """User serializer for reading user data"""
    profile_image = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'profile_image', 'location', 'bedrooms', 'bathrooms', 'property_condition',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        ref_name = 'SellerUserSerializer'
    
    def get_profile_image(self, obj):
        """Return absolute URL for profile image"""
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None


class RegisterResponseSerializer(serializers.Serializer):
    """Serializer for registration response"""
    access_token = serializers.CharField(help_text="JWT access token")
    refresh_token = serializers.CharField(help_text="JWT refresh token")
    email = serializers.EmailField(help_text="Registered email address")
    phone_number = serializers.CharField(help_text="Phone number", allow_null=True)
    location = serializers.CharField(help_text="Property location", allow_null=True)
    bedrooms = serializers.IntegerField(help_text="Number of bedrooms", allow_null=True)
    bathrooms = serializers.IntegerField(help_text="Number of bathrooms", allow_null=True)
    property_condition = serializers.CharField(help_text="Property condition description", allow_null=True)

    class Meta:
        ref_name = 'SellerRegisterResponseSerializer'


class RegisterRequestSerializer(serializers.Serializer):
    """Serializer for registration request (Swagger documentation)"""
    name = serializers.CharField(required=True, help_text="Full name")
    email = serializers.EmailField(required=True, help_text="Email address")
    password = serializers.CharField(required=True, help_text="Password")
    password2 = serializers.CharField(required=True, help_text="Confirm password")
    phone_number = serializers.CharField(required=False, allow_blank=True, help_text="Phone number")
    location = serializers.CharField(required=False, allow_blank=True, help_text="Property location")
    bedrooms = serializers.IntegerField(required=False, allow_null=True, help_text="Number of bedrooms")
    bathrooms = serializers.IntegerField(required=False, allow_null=True, help_text="Number of bathrooms")
    property_condition = serializers.CharField(required=False, allow_blank=True, help_text="Description of property condition")

    class Meta:
        ref_name = 'SellerRegisterRequestSerializer'


class LoginRequestSerializer(serializers.Serializer):
    """Serializer for login request (Swagger documentation)"""
    email = serializers.EmailField(required=True, help_text="Email address")
    password = serializers.CharField(required=True, help_text="Password")

    class Meta:
        ref_name = 'SellerLoginRequestSerializer'


class LoginResponseSerializer(serializers.Serializer):
    """Serializer for login response"""
    access_token = serializers.CharField(help_text="JWT access token")
    refresh_token = serializers.CharField(help_text="JWT refresh token")
    user = UserSerializer(help_text="User information")

    class Meta:
        ref_name = 'SellerLoginResponseSerializer'


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for seller registration"""
    name = serializers.CharField(write_only=True, required=True, help_text="Full name")
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, help_text="Confirm password")
    access_token = serializers.SerializerMethodField()
    refresh_token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'name', 'email', 'password', 'password2', 'phone_number',
            'location', 'bedrooms', 'bathrooms', 'property_condition',
            'access_token', 'refresh_token'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'phone_number': {'required': False},
            'location': {'required': False},
            'bedrooms': {'required': False},
            'bathrooms': {'required': False},
            'property_condition': {'required': False},
        }
        ref_name = 'SellerRegisterSerializer'

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
        """Generate access token on user creation with user_type claim"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(obj)
        # Add user_type to token
        refresh['user_type'] = 'seller'
        return str(refresh.access_token)

    def get_refresh_token(self, obj):
        """Generate refresh token on user creation with user_type claim"""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(obj)
        # Add user_type to token
        refresh['user_type'] = 'seller'
        return str(refresh)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer with additional user information"""
    
    class Meta:
        ref_name = 'SellerCustomTokenObtainPairSerializer'
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['user_type'] = 'seller'  # Add user type
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class LoginSerializer(serializers.Serializer):
    """Serializer for user login with email and password"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    access_token = serializers.SerializerMethodField(read_only=True)
    refresh_token = serializers.SerializerMethodField(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        ref_name = 'SellerLoginSerializer'

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
            # Add user_type to token
            refresh['user_type'] = 'seller'
            return str(refresh.access_token)
        return None

    def get_refresh_token(self, obj):
        user = obj.get('user')
        if user:
            refresh = RefreshToken.for_user(user)
            # Add user_type to token
            refresh['user_type'] = 'seller'
            return str(refresh)
        return None


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'phone_number', 'profile_image', 'location', 'bedrooms', 'bathrooms', 'property_condition'
        ]
        extra_kwargs = {
            'username': {'required': False},
            'email': {'required': False},
            'profile_image': {'required': False},
        }
        ref_name = 'SellerProfileUpdateSerializer'

    def update(self, instance, validated_data):
        """Update user profile"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    new_password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        ref_name = 'SellerChangePasswordSerializer'

    def validate(self, attrs):
        """Validate that new passwords match"""
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {"new_password": "Password fields didn't match."}
            )
        return attrs

    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value

    def save(self):
        """Save new password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout"""
    refresh = serializers.CharField()

    class Meta:
        ref_name = 'SellerLogoutSerializer'


class SellingRequestSerializer(serializers.ModelSerializer):
    """Serializer for creating and reading selling requests"""
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    seller_email = serializers.CharField(source='seller.email', read_only=True)
    seller_phone = serializers.CharField(source='seller.phone_number', read_only=True)
    agent_id = serializers.IntegerField(source='agent.id', read_only=True, allow_null=True)
    agent_name = serializers.CharField(source='agent.get_full_name', read_only=True, allow_null=True)
    agent_email = serializers.CharField(source='agent.email', read_only=True, allow_null=True)
    agent_phone = serializers.CharField(source='agent.phone_number', read_only=True, allow_null=True)
    agent_license_number = serializers.CharField(source='agent.license_number', read_only=True, allow_null=True)
    agent_profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = SellingRequest
        fields = [
            'id', 'seller', 'seller_name', 'seller_email', 'seller_phone',
            'agent_id', 'agent_name', 'agent_email', 'agent_phone', 'agent_license_number', 'agent_profile_picture',
            'selling_reason', 'contact_name', 'contact_email', 'contact_phone',
            'asking_price', 'start_date', 'end_date', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'seller', 'seller_name', 'seller_email', 'seller_phone', 'created_at', 'updated_at']
    
    def get_agent_profile_picture(self, obj):
        """Return absolute URL for agent's profile picture"""
        if obj.agent and obj.agent.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.agent.profile_picture.url)
            return obj.agent.profile_picture.url
        return None


class SellingRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating selling requests"""
    asking_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Asking price in dollars"
    )
    agent = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.all(),
        required=False,
        allow_null=True,
        help_text="Agent ID (optional)"
    )
    
    class Meta:
        model = SellingRequest
        fields = [
            'selling_reason', 'contact_name', 'contact_email', 'contact_phone',
            'asking_price', 'start_date', 'end_date', 'agent'
        ]
        extra_kwargs = {
            'selling_reason': {'help_text': 'Reason for selling the property'},
            'contact_name': {'help_text': 'Contact person name'},
            'contact_email': {'help_text': 'Contact person email'},
            'contact_phone': {'help_text': 'Contact person phone number'},
            'start_date': {'help_text': 'When the selling period starts (YYYY-MM-DD)'},
            'end_date': {'help_text': 'When the selling period ends (YYYY-MM-DD)'},
        }
    
    def validate(self, attrs):
        """Validate start date is before end date"""
        if attrs['start_date'] >= attrs['end_date']:
            raise serializers.ValidationError(
                {"end_date": "End date must be after start date."}
            )
        return attrs


class SellingRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating selling requests"""
    asking_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        help_text="Asking price in dollars"
    )
    agent = serializers.PrimaryKeyRelatedField(
        queryset=Agent.objects.all(),
        required=False,
        allow_null=True,
        help_text="Agent ID (optional)"
    )
    
    class Meta:
        model = SellingRequest
        fields = [
            'selling_reason', 'contact_name', 'contact_email', 'contact_phone',
            'asking_price', 'start_date', 'end_date', 'agent'
        ]
        extra_kwargs = {
            'selling_reason': {'required': False, 'help_text': 'Reason for selling the property'},
            'contact_name': {'required': False, 'help_text': 'Contact person name'},
            'contact_email': {'required': False, 'help_text': 'Contact person email'},
            'contact_phone': {'required': False, 'help_text': 'Contact person phone number'},
            'start_date': {'required': False, 'help_text': 'When the selling period starts (YYYY-MM-DD)'},
            'end_date': {'required': False, 'help_text': 'When the selling period ends (YYYY-MM-DD)'},
        }
    
    def validate(self, attrs):
        """Validate start date is before end date"""
        if 'start_date' in attrs and 'end_date' in attrs:
            if attrs['start_date'] >= attrs['end_date']:
                raise serializers.ValidationError(
                    {"end_date": "End date must be after start date."}
                )
        return attrs


class SellingRequestStatusSerializer(serializers.ModelSerializer):
    """Serializer for updating selling request status"""
    class Meta:
        model = SellingRequest
        fields = ['status']


class SellerNotificationSerializer(serializers.ModelSerializer):
    """Serializer for reading seller notifications"""
    selling_request_id = serializers.IntegerField(source='selling_request.id', read_only=True, allow_null=True)
    selling_request_status = serializers.CharField(source='selling_request.status', read_only=True, allow_null=True)
    agent_id = serializers.IntegerField(source='selling_request.agent.id', read_only=True, allow_null=True)
    agreement_status = serializers.SerializerMethodField(read_only=True)
    agreement_id = serializers.SerializerMethodField(read_only=True)
    cma_id = serializers.IntegerField(source='cma_document.id', read_only=True, allow_null=True)
    cma_status = serializers.SerializerMethodField(read_only=True)
    title = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    action_text = serializers.SerializerMethodField()
    
    class Meta:
        model = SellerNotification
        fields = [
            'id', 'notification_type', 'title', 'message', 
            'action_url', 'action_text', 'is_read',
            'selling_request_id', 'selling_request_status', 'agent_id', 'agreement_status', 'agreement_id', 'cma_id', 'cma_status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_cma_status(self, obj):
        """Get the current CMA status"""
        if obj.cma_document:
            return obj.cma_document.cma_status
        return None
    
    def get_agreement_id(self, obj):
        """Get the agreement document ID (PropertyDocument with selling_agreement_file)"""
        if obj.selling_request:
            # Find the document with a selling_agreement_file for this selling request
            agreement_doc = obj.selling_request.documents.filter(
                selling_agreement_file__isnull=False
            ).exclude(selling_agreement_file='').first()
            return agreement_doc.id if agreement_doc else None
        return None
    
    def get_title(self, obj):
        """Generate dynamic title based on CMA status or agreement status"""
        if obj.notification_type == 'cma_ready' and obj.cma_document:
            if obj.cma_document.cma_status == 'accepted':
                return 'CMA Report Accepted'
            elif obj.cma_document.cma_status == 'rejected':
                return 'CMA Report Rejected'
        
        # Dynamic title for agreement notifications
        if obj.notification_type == 'agreement' and obj.selling_request:
            agreement_doc = obj.selling_request.documents.filter(
                selling_agreement_file__isnull=False
            ).exclude(selling_agreement_file='').first()
            
            if agreement_doc and agreement_doc.agreement_status:
                if agreement_doc.agreement_status == 'accepted':
                    return 'Selling Agreement Accepted'
                elif agreement_doc.agreement_status == 'rejected':
                    return 'Selling Agreement Rejected'
        
        return obj.title
    
    def get_message(self, obj):
        """Generate dynamic message based on CMA status or agreement status"""
        if obj.notification_type == 'cma_ready' and obj.cma_document:
            if obj.cma_document.cma_status == 'accepted':
                return f'You have accepted the CMA report "{obj.cma_document.title}". The agent has been notified.'
            elif obj.cma_document.cma_status == 'rejected':
                return f'You have rejected the CMA report "{obj.cma_document.title}". The agent has been notified to review and resubmit.'
        
        # Dynamic message for agreement notifications
        if obj.notification_type == 'agreement' and obj.selling_request:
            agreement_doc = obj.selling_request.documents.filter(
                selling_agreement_file__isnull=False
            ).exclude(selling_agreement_file='').first()
            
            if agreement_doc and agreement_doc.agreement_status:
                if agreement_doc.agreement_status == 'accepted':
                    return 'You have accepted the selling agreement. The agent has been notified and will proceed with the next steps.'
                elif agreement_doc.agreement_status == 'rejected':
                    return 'You have rejected the selling agreement. The agent has been notified to review and prepare a revised agreement.'
        
        return obj.message
    
    def get_action_text(self, obj):
        """Generate dynamic action text based on CMA status or agreement status"""
        if obj.notification_type == 'cma_ready' and obj.cma_document:
            if obj.cma_document.cma_status == 'accepted':
                return 'View Accepted CMA'
            elif obj.cma_document.cma_status == 'rejected':
                return 'View Rejected CMA'
        
        # Dynamic action text for agreement notifications
        if obj.notification_type == 'agreement' and obj.selling_request:
            agreement_doc = obj.selling_request.documents.filter(
                selling_agreement_file__isnull=False
            ).exclude(selling_agreement_file='').first()
            
            if agreement_doc and agreement_doc.agreement_status:
                if agreement_doc.agreement_status == 'accepted':
                    return 'View Accepted Agreement'
                elif agreement_doc.agreement_status == 'rejected':
                    return 'View Rejected Agreement'
        
        return obj.action_text
    
    def get_agreement_status(self, obj):
        """Get the agreement status from the related selling agreement document"""
        if obj.selling_request:
            # Get the document with selling_agreement_file (the actual agreement document)
            agreement_doc = obj.selling_request.documents.filter(
                selling_agreement_file__isnull=False
            ).exclude(selling_agreement_file='').first()
            
            if agreement_doc:
                return agreement_doc.agreement_status
        return None


class SellerNotificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for marking notifications as read"""
    class Meta:
        model = SellerNotification
        fields = ['is_read']

class PropertyDocumentSerializer(serializers.ModelSerializer):
    """Serializer for reading property documents"""
    file_extension = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    selling_agreement_url = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyDocument
        fields = [
            'id', 'document_type', 'title', 'file_extension', 'file_size_mb',
            'description', 'cma_status', 'cma_document_status', 'selling_agreement_file', 'selling_agreement_url',
            'agreement_status', 'files', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'file_size_mb', 'file_extension', 'selling_agreement_url', 'files', 'created_at', 'updated_at']
    
    def get_file_extension(self, obj):
        return obj.get_file_extension()
    
    def get_file_size_mb(self, obj):
        return obj.get_file_size_mb()
    
    def get_selling_agreement_url(self, obj):
        """Return absolute URL for the selling agreement file"""
        if obj.selling_agreement_file:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.selling_agreement_file.url)
            # Fallback if no request context - construct URL manually
            from django.conf import settings
            base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            return f"{base_url}{obj.selling_agreement_file.url}"
        return None
    
    def get_files(self, obj):
        """Return list of files with full URLs"""
        files_data = []
        for doc_file in obj.files.all():
            request = self.context.get('request')
            file_url = None
            if doc_file.file:
                if request is not None:
                    file_url = request.build_absolute_uri(doc_file.file.url)
                else:
                    from django.conf import settings
                    base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
                    file_url = f"{base_url}{doc_file.file.url}"
            
            files_data.append({
                'id': doc_file.id,
                'file': file_url,
                'file_url': file_url,
                'original_filename': doc_file.original_filename,
                'file_extension': doc_file.get_file_extension(),
                'file_size_mb': doc_file.get_file_size_mb(),
                'created_at': doc_file.created_at
            })
        return files_data


class PropertyDocumentUploadResponseSerializer(serializers.ModelSerializer):
    """Serializer for upload response with files array"""
    files = serializers.SerializerMethodField()

    class Meta:
        model = PropertyDocument
        fields = [
            'id', 'document_type', 'title', 'description', 'files', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_files(self, obj):
        """Return list of files with full URLs"""
        files_data = []
        for doc_file in obj.files.all():
            request = self.context.get('request')
            file_url = None
            if doc_file.file:
                if request is not None:
                    file_url = request.build_absolute_uri(doc_file.file.url)
                else:
                    from django.conf import settings
                    base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
                    file_url = f"{base_url}{doc_file.file.url}"

            files_data.append({
                'id': doc_file.id,
                'file': file_url,
                'file_url': file_url,
                'original_filename': doc_file.original_filename,
                'file_extension': doc_file.get_file_extension(),
                'file_size_mb': doc_file.get_file_size_mb(),
                'created_at': doc_file.created_at
            })
        return files_data


class CMADetailedSerializer(serializers.ModelSerializer):
    """Serializer for displaying CMA report details with selling request information"""
    file_extension = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    selling_agreement_url = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()
    
    # Selling Request details
    selling_request_id = serializers.IntegerField(source='selling_request.id', read_only=True)
    selling_request_contact_name = serializers.CharField(source='selling_request.contact_name', read_only=True)
    selling_request_contact_email = serializers.CharField(source='selling_request.contact_email', read_only=True)
    selling_request_contact_phone = serializers.CharField(source='selling_request.contact_phone', read_only=True)
    selling_request_property_location = serializers.CharField(source='selling_request.seller.location', read_only=True)
    selling_request_asking_price = serializers.DecimalField(
        source='selling_request.asking_price', 
        read_only=True, 
        max_digits=12, 
        decimal_places=2
    )
    selling_request_status = serializers.CharField(source='selling_request.status', read_only=True)
    selling_request_start_date = serializers.DateField(source='selling_request.start_date', read_only=True)
    selling_request_end_date = serializers.DateField(source='selling_request.end_date', read_only=True)
    selling_request_reason = serializers.CharField(source='selling_request.selling_reason', read_only=True)
    agent_id = serializers.IntegerField(source='selling_request.agent.id', read_only=True, allow_null=True)
    
    class Meta:
        model = PropertyDocument
        fields = [
            'id', 
            'document_type', 
            'title', 
            'description',
            'file_url',
            'file_extension', 
            'file_size_mb',
            'files',
            'cma_status',
            'cma_document_status',
            'selling_agreement_file',
            'selling_agreement_url',
            'agreement_status',
            'created_at', 
            'updated_at',
            # Selling Request fields
            'selling_request_id',
            'selling_request_contact_name',
            'selling_request_contact_email',
            'selling_request_contact_phone',
            'selling_request_property_location',
            'selling_request_asking_price',
            'selling_request_status',
            'selling_request_start_date',
            'selling_request_end_date',
            'selling_request_reason',
            # Agent fields
            'agent_id',
        ]
        read_only_fields = fields
    
    def get_file_extension(self, obj):
        return obj.get_file_extension()
    
    def get_file_size_mb(self, obj):
        return obj.get_file_size_mb()
    
    def get_file_url(self, obj):
        """Return absolute URL for the first document file"""
        first_file = obj.files.first()
        if first_file and first_file.file:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(first_file.file.url)
            # Fallback if no request context - construct URL manually
            from django.conf import settings
            base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            return f"{base_url}{first_file.file.url}"
        return None
    
    def get_files(self, obj):
        """Return list of files with full URLs"""
        files_data = []
        for doc_file in obj.files.all():
            request = self.context.get('request')
            file_url = None
            if doc_file.file:
                if request is not None:
                    file_url = request.build_absolute_uri(doc_file.file.url)
                else:
                    from django.conf import settings
                    base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
                    file_url = f"{base_url}{doc_file.file.url}"
            
            files_data.append({
                'id': doc_file.id,
                'file': file_url,
                'file_url': file_url,
                'original_filename': doc_file.original_filename,
                'file_extension': doc_file.get_file_extension(),
                'file_size_mb': doc_file.get_file_size_mb(),
                'created_at': doc_file.created_at
            })
        return files_data
    
    def get_selling_agreement_url(self, obj):
        """Return absolute URL for the selling agreement file"""
        if obj.selling_agreement_file:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.selling_agreement_file.url)
            # Fallback if no request context - construct URL manually
            from django.conf import settings
            base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            return f"{base_url}{obj.selling_agreement_file.url}"
        return None
    
    def get_file_size_mb(self, obj):
        return obj.get_file_size_mb()


class PropertyDocumentUploadSerializer(serializers.Serializer):
    """Serializer for uploading multiple property documents (excluding CMA - only agents can upload CMA)"""
    document_type = serializers.ChoiceField(
        choices=[('inspection', 'Inspection Report'), ('appraisal', 'Appraisal Report'), ('other', 'Other Document')],
        default='other'
    )
    title = serializers.CharField(max_length=255)
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        help_text="List of files to upload (PDF, JPG, JPEG, PNG)"
    )
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_document_type(self, value):
        """Seller cannot upload CMA documents - only agents can"""
        if value == 'cma':
            raise serializers.ValidationError(
                "Sellers cannot upload CMA documents. Only agents can upload CMA reports."
            )
        return value

    def validate_files(self, value):
        """Validate each file in the list"""
        if not value:
            raise serializers.ValidationError("At least one file must be provided.")

        max_files = 10  # Limit number of files
        if len(value) > max_files:
            raise serializers.ValidationError(f"Maximum {max_files} files can be uploaded at once.")

        max_size = 10 * 1024 * 1024  # 10MB per file
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']

        for file in value:
            if file.size > max_size:
                raise serializers.ValidationError(
                    f"File '{file.name}' size must not exceed 10 MB. Current size: {round(file.size / (1024 * 1024), 2)} MB"
                )

            file_extension = file.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise serializers.ValidationError(
                    f"File type '{file_extension}' is not allowed for file '{file.name}'. Allowed types: {', '.join(allowed_extensions)}"
                )

        return value

    def validate(self, attrs):
        """Validate selling request is approved"""
        request = self.context.get('request')
        selling_request_id = self.context.get('selling_request_id')

        if not selling_request_id:
            raise serializers.ValidationError("Selling request ID is required")

        try:
            selling_request = SellingRequest.objects.get(pk=selling_request_id)
        except SellingRequest.DoesNotExist:
            raise serializers.ValidationError("Selling request not found")

        if selling_request.status != 'accepted':
            raise serializers.ValidationError(
                "Can only upload documents for approved selling requests"
            )

        if selling_request.seller != request.user:
            raise serializers.ValidationError(
                "You can only upload documents for your own selling requests"
            )

        return attrs
    
    def create(self, validated_data):
        """Create document with multiple files"""
        from .models import DocumentFile
        
        selling_request_id = self.context.get('selling_request_id')
        selling_request = SellingRequest.objects.get(pk=selling_request_id)
        
        # Remove files from validated_data and create document first
        files = validated_data.pop('files')
        
        # Calculate total file size
        total_file_size = sum(file.size for file in files)
        
        # Create the document (without file field since we're using DocumentFile)
        document = PropertyDocument.objects.create(
            selling_request=selling_request,
            seller=selling_request.seller,
            file_size=total_file_size,
            **validated_data
        )
        
        # Create DocumentFile instances for each uploaded file
        for file in files:
            DocumentFile.objects.create(
                property_document=document,
                file=file,
                file_size=file.size,
                original_filename=file.name
            )
        
        return document


class CMAStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating CMA document status (accept or reject)"""
    class Meta:
        model = PropertyDocument
        fields = ['cma_status', 'cma_document_status']
    
    def validate_cma_status(self, value):
        """Validate CMA status is either accepted or rejected"""
        if value not in ['accepted', 'rejected']:
            raise serializers.ValidationError(
                "CMA status must be either 'accepted' or 'rejected'."
            )
        return value
    
    def validate_cma_document_status(self, value):
        """Validate document status is either accepted or rejected"""
        if value not in ['accepted', 'rejected']:
            raise serializers.ValidationError(
                "Document status must be either 'accepted' or 'rejected'."
            )
        return value


class SellingAgreementDetailedSerializer(serializers.ModelSerializer):
    """Serializer for displaying selling agreement details with selling request information"""
    file_extension = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    selling_agreement_file_extension = serializers.SerializerMethodField()
    cma_id = serializers.SerializerMethodField()
    
    # Selling Request details
    selling_request_id = serializers.IntegerField(source='selling_request.id', read_only=True)
    selling_request_contact_name = serializers.CharField(source='selling_request.contact_name', read_only=True)
    selling_request_contact_email = serializers.CharField(source='selling_request.contact_email', read_only=True)
    selling_request_contact_phone = serializers.CharField(source='selling_request.contact_phone', read_only=True)
    selling_request_property_location = serializers.CharField(source='selling_request.seller.location', read_only=True)
    selling_request_asking_price = serializers.DecimalField(
        source='selling_request.asking_price', 
        read_only=True, 
        max_digits=12, 
        decimal_places=2
    )
    selling_request_status = serializers.CharField(source='selling_request.status', read_only=True)
    selling_request_start_date = serializers.DateField(source='selling_request.start_date', read_only=True)
    selling_request_end_date = serializers.DateField(source='selling_request.end_date', read_only=True)
    selling_request_reason = serializers.CharField(source='selling_request.selling_reason', read_only=True)
    
    # Seller details
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    seller_email = serializers.CharField(source='seller.email', read_only=True)
    
    class Meta:
        model = PropertyDocument
        fields = [
            'id', 
            'document_type', 
            'title', 
            'description',
            'file_extension', 
            'file_size_mb',
            'selling_agreement_file',
            'selling_agreement_file_extension',
            'agreement_status',
            'cma_id',
            'created_at', 
            'updated_at',
            # Seller details
            'seller_name',
            'seller_email',
            # Selling Request fields
            'selling_request_id',
            'selling_request_contact_name',
            'selling_request_contact_email',
            'selling_request_contact_phone',
            'selling_request_property_location',
            'selling_request_asking_price',
            'selling_request_status',
            'selling_request_start_date',
            'selling_request_end_date',
            'selling_request_reason',
        ]
        read_only_fields = fields
    
    def get_cma_id(self, obj):
        """Get the ID of the CMA document for this selling request"""
        if obj.document_type == 'cma':
            # If this is already the CMA document, return its ID
            return obj.id
        # Otherwise, find the related CMA document for the same selling request
        cma_document = obj.selling_request.documents.filter(document_type='cma').first()
        return cma_document.id if cma_document else None
    
    def get_file_extension(self, obj):
        return obj.get_file_extension()
    
    def get_file_size_mb(self, obj):
        return obj.get_file_size_mb()
    
    def get_selling_agreement_file_extension(self, obj):
        """Get file extension for selling agreement file"""
        if obj.selling_agreement_file and obj.selling_agreement_file.name:
            import os
            return os.path.splitext(obj.selling_agreement_file.name)[1].lower().lstrip('.')
        return None


class AgreementStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating selling agreement status (accept or reject)"""
    class Meta:
        model = PropertyDocument
        fields = ['agreement_status']
    
    def validate_agreement_status(self, value):
        """Validate agreement status is either accepted or rejected"""
        if value not in ['accepted', 'rejected']:
            raise serializers.ValidationError(
                "Agreement status must be either 'accepted' or 'rejected'."
            )
        return value


class AgentListSerializer(serializers.ModelSerializer):
    """Serializer for listing agents - for seller view"""
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = Agent
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'profile_picture', 'license_number',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_profile_picture(self, obj):
        """Return absolute URL for profile picture"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None
