from rest_framework import serializers
from .models import (
    AgentPrivacyPolicy, AgentTermsConditions,
    SellerPrivacyPolicy, SellerTermsConditions,
    BuyerPrivacyPolicy, BuyerTermsConditions,
    PlatformDocument
)
from buyer.models import Buyer


class AgentPrivacyPolicySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = AgentPrivacyPolicy
        fields = ['id', 'title', 'content', 'version', 'is_active', 
                  'effective_date', 'created_by', 'created_by_name', 
                  'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class AgentTermsConditionsSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = AgentTermsConditions
        fields = ['id', 'title', 'content', 'version', 'is_active', 
                  'effective_date', 'created_by', 'created_by_name', 
                  'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class SellerPrivacyPolicySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = SellerPrivacyPolicy
        fields = ['id', 'title', 'content', 'version', 'is_active', 
                  'effective_date', 'created_by', 'created_by_name', 
                  'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class SellerTermsConditionsSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = SellerTermsConditions
        fields = ['id', 'title', 'content', 'version', 'is_active', 
                  'effective_date', 'created_by', 'created_by_name', 
                  'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class BuyerPrivacyPolicySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = BuyerPrivacyPolicy
        fields = ['id', 'title', 'content', 'version', 'is_active', 
                  'effective_date', 'created_by', 'created_by_name', 
                  'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class BuyerTermsConditionsSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = BuyerTermsConditions
        fields = ['id', 'title', 'content', 'version', 'is_active', 
                  'effective_date', 'created_by', 'created_by_name', 
                  'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class BuyerListSerializer(serializers.ModelSerializer):
    """Serializer for listing all buyers"""
    full_name = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    mortgage_letter_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Buyer
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'profile_image', 'profile_image_url',
            'price_range', 'location', 'bedrooms', 'bathrooms',
            'mortgage_letter', 'mortgage_letter_url',
            'is_active', 'date_joined', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'date_joined', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_profile_image_url(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
        return None
    
    def get_mortgage_letter_url(self, obj):
        if obj.mortgage_letter:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.mortgage_letter.url)
        return None


class BuyerDetailSerializer(serializers.ModelSerializer):
    """Serializer for viewing and updating buyer details"""
    full_name = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    mortgage_letter_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Buyer
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'profile_image', 'profile_image_url',
            'price_range', 'location', 'bedrooms', 'bathrooms',
            'mortgage_letter', 'mortgage_letter_url',
            'is_active', 'is_staff', 'date_joined', 'last_login',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_profile_image_url(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
        return None
    
    def get_mortgage_letter_url(self, obj):
        if obj.mortgage_letter:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.mortgage_letter.url)
        return None


class BuyerUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin updating buyer information"""
    
    class Meta:
        model = Buyer
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'phone_number', 'price_range', 'location', 'bedrooms', 'bathrooms',
            'is_active'
        ]
    
    def validate_email(self, value):
        """Ensure email is unique when updating"""
        buyer_id = self.instance.id if self.instance else None
        if Buyer.objects.filter(email=value).exclude(id=buyer_id).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value
    
    def validate_username(self, value):
        """Ensure username is unique when updating"""
        buyer_id = self.instance.id if self.instance else None
        if Buyer.objects.filter(username=value).exclude(id=buyer_id).exists():
            raise serializers.ValidationError("This username is already in use.")
        return value


class PlatformDocumentSerializer(serializers.ModelSerializer):
    """Serializer for platform documents (read-only)"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    document_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PlatformDocument
        fields = [
            'id', 'document_type', 'document_type_display', 'title', 
            'description', 'document', 'document_url', 'file_size', 
            'is_active', 'version', 'uploaded_by', 'uploaded_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'file_size', 'created_at', 'updated_at']
    
    def get_document_url(self, obj):
        """Get full URL for document"""
        request = self.context.get('request')
        if request and obj.document:
            return request.build_absolute_uri(obj.document.url)
        return obj.document.url if obj.document else None


class PlatformDocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading platform documents (admin only)"""
    
    class Meta:
        model = PlatformDocument
        fields = [
            'id', 'document_type', 'title', 'description', 
            'document', 'is_active', 'version'
        ]
        read_only_fields = ['id']
    
    def validate_document(self, value):
        """Validate file size (max 50MB) and type"""
        max_size = 50 * 1024 * 1024  # 50MB
        
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds 50MB limit. Your file is {value.size / 1024 / 1024:.2f}MB"
            )
        
        # Check file extension
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
        file_extension = value.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type '.{file_extension}' not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value

