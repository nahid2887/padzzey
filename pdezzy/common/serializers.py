from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import PasswordResetToken


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password - send OTP (email only)"""
    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate that email exists in any user type account"""
        from agent.models import Agent
        from seller.models import Seller
        from buyer.models import Buyer
        
        # Check if email exists in any user type
        agent_exists = Agent.objects.filter(email=value).exists()
        seller_exists = Seller.objects.filter(email=value).exists()
        buyer_exists = Buyer.objects.filter(email=value).exists()
        
        if not (agent_exists or seller_exists or buyer_exists):
            raise serializers.ValidationError("No account found with this email address.")
        
        # Store the user type for later use
        if agent_exists:
            self.user_type = 'agent'
        elif seller_exists:
            self.user_type = 'seller'
        else:
            self.user_type = 'buyer'
        
        return value


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP (email only, user type auto-detected)"""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')

        try:
            # Find the OTP token regardless of user type
            token = PasswordResetToken.objects.filter(
                email=email,
                otp=otp
            ).latest('created_at')

            if not token.is_valid():
                raise serializers.ValidationError("OTP is invalid or expired.")

            attrs['token'] = token
            attrs['user_type'] = token.user_type  # Get user type from token
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP or email.")

        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for resetting password (email only, user type auto-detected)"""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    new_password2 = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {"new_password": "Password fields didn't match."}
            )

        email = attrs.get('email')
        otp = attrs.get('otp')

        try:
            # Find the OTP token regardless of user type
            token = PasswordResetToken.objects.filter(
                email=email,
                otp=otp
            ).latest('created_at')

            if not token.is_valid():
                raise serializers.ValidationError("OTP is invalid or expired.")

            attrs['token'] = token
            attrs['user_type'] = token.user_type  # Get user type from token
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP or email.")

        return attrs

    def save(self):
        email = self.validated_data['email']
        user_type = self.validated_data['user_type']
        new_password = self.validated_data['new_password']
        token = self.validated_data['token']

        if user_type == 'agent':
            from agent.models import Agent
            user = Agent.objects.get(email=email)
        elif user_type == 'seller':
            from seller.models import Seller
            user = Seller.objects.get(email=email)
        elif user_type == 'buyer':
            from buyer.models import Buyer
            user = Buyer.objects.get(email=email)

        user.set_password(new_password)
        user.save()

        # Mark token as used
        token.is_used = True
        token.save()

        return user


class LegalDocumentSerializer(serializers.ModelSerializer):
    """Serializer for viewing legal documents"""
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        from .models import LegalDocument
        model = LegalDocument
        fields = [
            'id', 'document_type', 'document_type_display', 'user_type', 
            'user_type_display', 'title', 'content', 'version', 'is_active',
            'effective_date', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.get_full_name()} ({obj.created_by.username})"
        return "System"


class LegalDocumentCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating legal documents (Admin only)"""
    
    class Meta:
        from .models import LegalDocument
        model = LegalDocument
        fields = [
            'document_type', 'title', 'content', 
            'version', 'is_active', 'effective_date'
        ]
        read_only_fields = ['user_type']  # Auto-determined from document_type
    
    def validate_content(self, value):
        """Ensure content is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Content cannot be empty")
        return value