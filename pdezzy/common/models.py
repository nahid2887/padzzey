from django.db import models
from django.utils import timezone
from django.conf import settings
import random
import string


class PasswordResetToken(models.Model):
    """Model to store OTP tokens for password reset"""
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    user_type = models.CharField(
        max_length=10,
        choices=[('agent', 'Agent'), ('seller', 'Seller'), ('buyer', 'Buyer')],
        help_text="Type of user requesting password reset"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} - {self.user_type} - {'USED' if self.is_used else 'ACTIVE'}"

    def is_valid(self):
        """Check if OTP is valid and not expired"""
        now = timezone.now()
        return not self.is_used and self.expires_at > now

    @staticmethod
    def generate_otp():
        """Generate a random 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))

    @staticmethod
    def create_otp_token(email, user_type):
        """Create a new OTP token for password reset"""
        from django.conf import settings
        otp = PasswordResetToken.generate_otp()
        expires_at = timezone.now() + timezone.timedelta(
            minutes=settings.OTP_EXPIRY_MINUTES
        )
        token = PasswordResetToken.objects.create(
            email=email,
            otp=otp,
            user_type=user_type,
            expires_at=expires_at
        )
        return token


class LegalDocument(models.Model):
    """Model for storing legal documents like Terms & Conditions, Privacy Policy, etc."""
    DOCUMENT_TYPES = [
        ('agent_privacy_policy', 'Agent Privacy Policy'),
        ('agent_terms_conditions', 'Agent Terms & Conditions'),
        ('seller_privacy_policy', 'Seller Privacy Policy'),
        ('seller_terms_conditions', 'Seller Terms & Conditions'),
        ('buyer_privacy_policy', 'Buyer Privacy Policy'),
        ('buyer_terms_conditions', 'Buyer Terms & Conditions'),
    ]
    
    USER_TYPES = [
        ('agent', 'Agents'),
        ('seller', 'Sellers'),
        ('buyer', 'Buyers'),
    ]
    
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPES,
        unique=True,
        help_text="Type of legal document - each type can only have one active document"
    )
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPES,
        help_text="Target user type for this document (auto-determined from document_type)"
    )
    title = models.CharField(
        max_length=255,
        help_text="Document title"
    )
    content = models.TextField(
        help_text="Full document content (supports HTML)"
    )
    version = models.CharField(
        max_length=50,
        default='1.0',
        help_text="Document version number"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active documents are shown to users"
    )
    effective_date = models.DateField(
        default=timezone.now,
        help_text="Date when this version becomes effective"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_legal_documents',
        help_text="Admin who created this document"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Legal Document'
        verbose_name_plural = 'Legal Documents'
        # Ensure only one active document per type and user type

    def __str__(self):
        return f"{self.get_document_type_display()} v{self.version}"

    def save(self, *args, **kwargs):
        """Auto-set user_type based on document_type and ensure only one document per type"""
        # Extract user type from document type
        if self.document_type.startswith('agent_'):
            self.user_type = 'agent'
        elif self.document_type.startswith('seller_'):
            self.user_type = 'seller'
        elif self.document_type.startswith('buyer_'):
            self.user_type = 'buyer'
        
        # Deactivate other documents of the same type
        if self.is_active:
            LegalDocument.objects.filter(
                document_type=self.document_type,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        




