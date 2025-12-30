from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from seller.models import SellingRequest, PropertyDocument, AgentNotification
from .models import PropertyListing, PropertyListingPhoto, PropertyListingDocument

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """User serializer for reading user data with professional information"""
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'profile_picture', 'license_number', 'agent_papers',
            'about', 'company_details', 'years_of_experience', 'area_of_expertise',
            'languages', 'service_areas', 'property_types', 'availability',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        ref_name = 'AgentUserSerializer'
    
    def get_profile_picture(self, obj):
        """Return absolute URL for profile picture"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    access_token = serializers.SerializerMethodField()
    refresh_token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2', 'first_name',
            'last_name', 'phone_number', 'access_token', 'refresh_token'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
        ref_name = 'AgentRegisterSerializer'

    def validate(self, attrs):
        """Validate that passwords match"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        """Create user and return tokens"""
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

    def get_access_token(self, obj):
        """Generate access token on user creation"""
        refresh = RefreshToken.for_user(obj)
        return str(refresh.access_token)

    def get_refresh_token(self, obj):
        """Generate refresh token on user creation"""
        refresh = RefreshToken.for_user(obj)
        return str(refresh)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer with additional user information"""
    
    class Meta:
        ref_name = 'AgentCustomTokenObtainPairSerializer'
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
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
        ref_name = 'AgentLoginSerializer'

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
            refresh['user_type'] = 'agent'
            return str(refresh.access_token)
        return None

    def get_refresh_token(self, obj):
        user = obj.get('user')
        if user:
            refresh = RefreshToken.for_user(user)
            # Add user_type claim for custom authentication
            refresh['user_type'] = 'agent'
            return str(refresh)
        return None


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile with all professional information"""
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    agent_papers = serializers.FileField(required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'phone_number', 'profile_picture', 'license_number', 'agent_papers',
            'about', 'company_details', 'years_of_experience', 'area_of_expertise',
            'languages', 'service_areas', 'property_types', 'availability'
        ]
        extra_kwargs = {
            'username': {'required': False},
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone_number': {'required': False},
            'profile_picture': {'required': False},
            'license_number': {'required': False},
            'agent_papers': {'required': False},
            'about': {'required': False},
            'company_details': {'required': False},
            'years_of_experience': {'required': False},
            'area_of_expertise': {'required': False},
            'languages': {'required': False},
            'service_areas': {'required': False},
            'property_types': {'required': False},
            'availability': {'required': False},
        }
        ref_name = 'AgentProfileUpdateSerializer'

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
        ref_name = 'AgentChangePasswordSerializer'

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
        ref_name = 'AgentLogoutSerializer'


class AgentSellingRequestSerializer(serializers.ModelSerializer):
    """Serializer for agents to view selling requests"""
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    seller_email = serializers.CharField(source='seller.email', read_only=True)
    seller_phone = serializers.CharField(source='seller.phone_number', read_only=True)
    
    class Meta:
        model = SellingRequest
        fields = [
            'id', 'seller', 'seller_name', 'seller_email', 'seller_phone',
            'selling_reason', 'contact_name', 'contact_email', 'contact_phone',
            'asking_price', 'start_date', 'end_date', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'seller', 'seller_name', 'seller_email', 'seller_phone',
            'selling_reason', 'contact_name', 'contact_email', 'contact_phone',
            'asking_price', 'start_date', 'end_date', 'created_at', 'updated_at'
        ]


class AgentSellingRequestStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for agents to update selling request status"""
    class Meta:
        model = SellingRequest
        fields = ['status']
    
    def validate_status(self, value):
        """Validate status is either accepted or rejected"""
        if value not in ['accepted', 'rejected']:
            raise serializers.ValidationError(
                "Status must be either 'accepted' or 'rejected'."
            )
        return value


class AgentNotificationSerializer(serializers.ModelSerializer):
    """Serializer for reading agent notifications"""
    seller_name = serializers.CharField(source='selling_request.seller.get_full_name', read_only=True, allow_null=True)
    seller_email = serializers.CharField(source='selling_request.seller.email', read_only=True, allow_null=True)
    selling_request_id = serializers.IntegerField(source='selling_request.id', read_only=True, allow_null=True)
    selling_request_status = serializers.CharField(source='selling_request.status', read_only=True, allow_null=True)
    document_id = serializers.IntegerField(source='property_document.id', read_only=True, allow_null=True)
    document_title = serializers.CharField(source='property_document.title', read_only=True, allow_null=True)
    document_type = serializers.CharField(source='property_document.document_type', read_only=True, allow_null=True)
    cma_status = serializers.CharField(source='property_document.cma_status', read_only=True, allow_null=True)
    
    # Showing schedule fields
    showing_schedule_id = serializers.IntegerField(source='showing_schedule.id', read_only=True, allow_null=True)
    showing_status = serializers.CharField(source='showing_schedule.status', read_only=True, allow_null=True)
    buyer_name = serializers.SerializerMethodField()
    property_title = serializers.SerializerMethodField()
    property_image = serializers.SerializerMethodField()
    property_document = serializers.SerializerMethodField()
    
    # Dynamic action text based on notification type
    action_text = serializers.SerializerMethodField()
    
    def get_buyer_name(self, obj):
        if obj.showing_schedule and obj.showing_schedule.buyer:
            return obj.showing_schedule.buyer.get_full_name() or obj.showing_schedule.buyer.username
        return None
    
    def get_property_title(self, obj):
        if obj.showing_schedule and obj.showing_schedule.property_listing:
            return obj.showing_schedule.property_listing.title
        return None
    
    def get_property_image(self, obj):
        """Return primary photo of the property listing"""
        if obj.showing_schedule and obj.showing_schedule.property_listing:
            photos = obj.showing_schedule.property_listing.photos.all().order_by('created_at')
            if photos.exists():
                photo = photos.first()
                request = self.context.get('request')
                if request and photo.photo:
                    return request.build_absolute_uri(photo.photo.url)
                return photo.photo.url if photo.photo else None
        return None
    
    def get_property_document(self, obj):
        """Return first document of the property listing"""
        if obj.showing_schedule and obj.showing_schedule.property_listing:
            documents = obj.showing_schedule.property_listing.listing_documents.all().order_by('created_at')
            if documents.exists():
                doc = documents.first()
                return {
                    'id': doc.id,
                    'title': doc.title,
                    'document_type': doc.document_type,
                    'file': self._get_file_url(doc.document),
                }
        return None
    
    def _get_file_url(self, file_field):
        """Get absolute URL for file"""
        if file_field:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(file_field.url)
            return file_field.url
        return None
    
    def get_action_text(self, obj):
        """Return dynamic action text based on notification type"""
        if obj.notification_type == 'document_uploaded':
            return "View Documents"
        elif obj.notification_type == 'new_selling_request':
            return "View Selling Request"
        elif obj.notification_type == 'showing_requested':
            return "View Showing"
        elif obj.notification_type == 'showing_accepted':
            return "View Accepted Showing"
        elif obj.notification_type == 'showing_declined':
            return "View Declined Showing"
        elif obj.notification_type == 'cma_requested':
            return "View CMA Request"
        elif obj.notification_type == 'document_updated':
            return "View Document"
        # Fallback to stored action_text or default
        return obj.action_text or "View Details"
    
    class Meta:
        model = AgentNotification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'selling_request_id', 'selling_request_status', 'seller_name', 'seller_email',
            'document_id', 'document_title', 'document_type', 'cma_status',
            'showing_schedule_id', 'showing_status', 'buyer_name', 'property_title', 'property_image', 'property_document',
            'action_url', 'action_text', 'is_read',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AgentNotificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for marking agent notifications as read"""
    class Meta:
        model = AgentNotification
        fields = ['is_read']


class PropertyDocumentForCMASerializer(serializers.ModelSerializer):
    """Serializer for property documents related to CMA"""
    file_extension = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyDocument
        fields = [
            'id', 'document_type', 'title', 'description', 
            'file', 'file_extension', 'file_size_mb',
            'cma_status', 'cma_document_status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'file_size_mb', 'file_extension', 'created_at', 'updated_at']
    
    def get_file_extension(self, obj):
        return obj.get_file_extension()
    
    def get_file_size_mb(self, obj):
        return obj.get_file_size_mb()


class AgentPropertyDocumentSerializer(serializers.ModelSerializer):
    """Serializer for agents to view property documents uploaded by sellers"""
    file_size_mb = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    selling_request_id = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()
    selling_agreement_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyDocument
        fields = [
            'id', 'document_type', 'title', 'file_size_mb', 'description',
            'cma_status', 'cma_document_status', 'selling_agreement_file', 'selling_agreement_url',
            'agreement_status', 'seller_name', 'selling_request_id', 'files', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_file_size_mb(self, obj):
        return obj.get_file_size_mb()

    def get_seller_name(self, obj):
        """Return seller's full name"""
        return obj.seller.get_full_name() or obj.seller.username

    def get_selling_request_id(self, obj):
        """Return selling request ID"""
        return obj.selling_request.id

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


class AgentCMAUploadSerializer(serializers.Serializer):
    """Serializer for agent to upload CMA documents to a selling request"""
    document_type = serializers.ChoiceField(choices=[('cma', 'CMA Report')], default='cma')
    title = serializers.CharField(max_length=255)
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        help_text="List of CMA files to upload (PDF, JPG, JPEG, PNG)"
    )
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_document_type(self, value):
        """Ensure document type is CMA for agent upload"""
        if value != 'cma':
            raise serializers.ValidationError(
                "Agent can only upload CMA reports. Set document_type to 'cma'."
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
        """Validate selling request exists and is approved"""
        selling_request_id = self.context.get('selling_request_id')

        if not selling_request_id:
            raise serializers.ValidationError("Selling request ID is required")

        try:
            selling_request = SellingRequest.objects.get(pk=selling_request_id)
        except SellingRequest.DoesNotExist:
            raise serializers.ValidationError("Selling request not found")

        if selling_request.status != 'accepted':
            raise serializers.ValidationError(
                "Can only upload CMA for approved selling requests"
            )

        if selling_request.agent != self.context.get('request').user:
            raise serializers.ValidationError(
                "You can only upload CMA for selling requests assigned to you"
            )

        return attrs


class AgentCMAUploadResponseSerializer(serializers.ModelSerializer):
    """Serializer for CMA upload response with files array"""
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


class AgentSellingAgreementUploadSerializer(serializers.ModelSerializer):
    """Serializer for agent to upload selling agreement to a property document"""
    class Meta:
        model = PropertyDocument
        fields = ['selling_agreement_file']
    
    def validate_selling_agreement_file(self, value):
        """Validate selling agreement file size and extension"""
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size must not exceed 10 MB. Current size: {round(value.size / (1024 * 1024), 2)} MB"
            )
        
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type '{file_extension}' is not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value
    
    def validate(self, attrs):
        """Validate property document exists and belongs to an accepted selling request"""
        document_id = self.context.get('document_id')
        
        if not document_id:
            raise serializers.ValidationError("Document ID is required")
        
        try:
            document = PropertyDocument.objects.get(pk=document_id)
        except PropertyDocument.DoesNotExist:
            raise serializers.ValidationError("Property document not found")
        
        # Verify the document belongs to an accepted selling request
        if document.selling_request.status != 'accepted':
            raise serializers.ValidationError(
                "Can only upload selling agreement for approved selling requests"
            )
        
        return attrs
    
    def update(self, instance, validated_data):
        """Update property document with selling agreement file and set status to pending"""
        instance.selling_agreement_file = validated_data.get('selling_agreement_file', instance.selling_agreement_file)
        # Set agreement_status to pending by default
        instance.agreement_status = 'pending'
        instance.save()
        return instance


class AgentCreateListingSerializer(serializers.ModelSerializer):
    """
    Serializer for agent to create a property listing.
    Only works after seller has accepted the selling agreement.
    """
    photos = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True,
        help_text="Property photos (JPG, PNG, max 10MB each)"
    )
    documents = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True,
        help_text="Property documents (PDF, JPG, PNG, max 10MB each)"
    )
    
    class Meta:
        model = PropertyListing
        fields = [
            'title', 'street_address', 'city', 'state', 'zip_code',
            'property_type', 'bedrooms', 'bathrooms', 'square_feet',
            'description', 'price', 'photos', 'documents'
        ]
    
    def validate_photos(self, value):
        """Validate photo files"""
        max_size = 10 * 1024 * 1024  # 10MB
        allowed_extensions = ['jpg', 'jpeg', 'png']
        
        for photo in value:
            if photo.size > max_size:
                raise serializers.ValidationError(
                    f"Photo size must not exceed 10 MB. '{photo.name}' is {round(photo.size / (1024 * 1024), 2)} MB"
                )
            ext = photo.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise serializers.ValidationError(
                    f"Photo type '{ext}' not allowed. Allowed: {', '.join(allowed_extensions)}"
                )
        return value
    
    def validate_documents(self, value):
        """Validate document files"""
        max_size = 10 * 1024 * 1024  # 10MB
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
        
        for doc in value:
            if doc.size > max_size:
                raise serializers.ValidationError(
                    f"Document size must not exceed 10 MB. '{doc.name}' is {round(doc.size / (1024 * 1024), 2)} MB"
                )
            ext = doc.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise serializers.ValidationError(
                    f"Document type '{ext}' not allowed. Allowed: {', '.join(allowed_extensions)}"
                )
        return value
    
    def create(self, validated_data):
        """Create property listing with photos and documents"""
        photos = validated_data.pop('photos', [])
        documents = validated_data.pop('documents', [])
        
        # Automatically set status to 'for_sale' when agent creates listing
        validated_data['status'] = 'for_sale'
        
        # Create the listing
        listing = PropertyListing.objects.create(**validated_data)
        
        # Create photos
        for i, photo in enumerate(photos):
            PropertyListingPhoto.objects.create(
                listing=listing,
                photo=photo,
                is_primary=(i == 0),  # First photo is primary
                order=i,
                file_size=photo.size
            )
        
        # Create documents
        for doc in documents:
            PropertyListingDocument.objects.create(
                listing=listing,
                document=doc,
                title=doc.name,
                file_size=doc.size
            )
        
        return listing


class PropertyListingResponseSerializer(serializers.ModelSerializer):
    """Serializer for returning property listing details"""
    photos_count = serializers.SerializerMethodField()
    documents_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyListing
        fields = [
            'id', 'title', 'street_address', 'city', 'state', 'zip_code',
            'property_type', 'bedrooms', 'bathrooms', 'square_feet',
            'description', 'price', 'status', 'photos_count', 'documents_count',
            'created_at', 'updated_at'
        ]
    
    def get_photos_count(self, obj):
        return obj.photos.count()
    
    def get_documents_count(self, obj):
        return obj.listing_documents.count()


class AgentShowingScheduleSerializer(serializers.Serializer):
    """Serializer for agent viewing showing schedules"""
    id = serializers.IntegerField(read_only=True)
    buyer = serializers.SerializerMethodField()
    property_listing = serializers.SerializerMethodField()
    
    requested_date = serializers.DateField()
    preferred_time = serializers.CharField()
    additional_notes = serializers.CharField(allow_blank=True)
    
    status = serializers.CharField(read_only=True)
    agent_response = serializers.CharField(allow_null=True)
    responded_at = serializers.DateTimeField(allow_null=True, read_only=True)
    
    confirmed_date = serializers.DateField(allow_null=True)
    confirmed_time = serializers.TimeField(allow_null=True)
    
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
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
                'full_name': obj.buyer.get_full_name() or obj.buyer.username,
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
        ref_name = 'AgentShowingScheduleSerializer'


class AgentShowingResponseSerializer(serializers.Serializer):
    """Serializer for agent accepting/declining showing requests"""
    status = serializers.ChoiceField(
        choices=['accepted', 'declined'],
        help_text="Accept or decline the showing request"
    )
    agent_response = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional message to the buyer"
    )
    confirmed_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Confirmed date (required if accepting)"
    )
    confirmed_time = serializers.TimeField(
        required=False,
        allow_null=True,
        help_text="Confirmed time (required if accepting)"
    )
    
    def validate(self, data):
        """Validate that confirmed date/time are provided when accepting"""
        if data.get('status') == 'accepted':
            if not data.get('confirmed_date'):
                raise serializers.ValidationError({
                    'confirmed_date': 'Confirmed date is required when accepting a showing'
                })
            if not data.get('confirmed_time'):
                raise serializers.ValidationError({
                    'confirmed_time': 'Confirmed time is required when accepting a showing'
                })
        return data
    
    class Meta:
        ref_name = 'AgentShowingResponseSerializer'



class AgentCreateShowingSerializer(serializers.Serializer):
    """Serializer for agent creating a showing schedule"""
    buyer_id = serializers.IntegerField(help_text="ID of the buyer")
    property_listing_id = serializers.IntegerField(help_text="ID of agent's property listing")
    scheduled_date = serializers.DateField(help_text="Scheduled showing date (YYYY-MM-DD)")
    scheduled_time = serializers.TimeField(help_text="Scheduled showing time (HH:MM:SS)")
    agent_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Notes for the buyer about the showing"
    )
    
    def validate_scheduled_date(self, value):
        """Ensure scheduled date is not in the past"""
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Scheduled date cannot be in the past")
        return value
    
    def validate(self, data):
        """Validate buyer exists and listing belongs to agent"""
        from buyer.models import Buyer
        from agent.models import PropertyListing
        
        # Validate buyer exists
        try:
            buyer = Buyer.objects.get(id=data['buyer_id'])
        except Buyer.DoesNotExist:
            raise serializers.ValidationError({'buyer_id': 'Buyer not found'})
        
        # Validate property listing exists
        try:
            listing = PropertyListing.objects.get(id=data['property_listing_id'])
        except PropertyListing.DoesNotExist:
            raise serializers.ValidationError({'property_listing_id': 'Property listing not found'})
        
        # Store for use in view
        data['_buyer'] = buyer
        data['_listing'] = listing
        
        return data
    
    class Meta:
        ref_name = 'AgentCreateShowingSerializer'
