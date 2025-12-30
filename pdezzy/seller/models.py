from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import os


class Seller(AbstractUser):
    """Seller user model with property listing fields"""
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/sellers/', blank=True, null=True, help_text="Profile image")
    location = models.CharField(max_length=255, blank=True, null=True, help_text="Property location")
    bedrooms = models.IntegerField(blank=True, null=True, help_text="Number of bedrooms")
    bathrooms = models.IntegerField(blank=True, null=True, help_text="Number of bathrooms")
    property_condition = models.TextField(blank=True, null=True, help_text="Description of property condition")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Seller'
        verbose_name_plural = 'Sellers'

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    # Override ManyToMany related names to prevent clash with Agent
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='seller_groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='seller_permissions'
    )


class SellingRequest(models.Model):
    """Model for property selling requests with status tracking"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    # Relationship
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='selling_requests')
    agent = models.ForeignKey('agent.Agent', on_delete=models.SET_NULL, null=True, blank=True, related_name='selling_requests')
    
    # Description
    selling_reason = models.TextField(help_text="Reason for selling the property")
    
    # Contact Information
    contact_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    
    # Price Information
    asking_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Asking price in dollars")
    
    # Time Frame
    start_date = models.DateField(help_text="When the selling period starts")
    end_date = models.DateField(help_text="When the selling period ends")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Status of the selling request"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Selling Request'
        verbose_name_plural = 'Selling Requests'
    
    def __str__(self):
        return f"Selling Request from {self.seller.get_full_name()} - {self.status.upper()}"


class SellerNotification(models.Model):
    """Model for seller notifications when agent accepts or rejects selling requests"""
    
    NOTIFICATION_TYPES = [
        ('approved', 'Selling Request Approved'),
        ('rejected', 'Selling Request Rejected'),
        ('cma_ready', 'CMA Report Ready'),
        ('agreement', 'Selling Agreement'),
    ]
    
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='notifications')
    selling_request = models.ForeignKey(SellingRequest, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    cma_document = models.ForeignKey('PropertyDocument', on_delete=models.SET_NULL, related_name='notifications', null=True, blank=True, help_text="Related CMA document for cma_ready notifications")
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='approved')
    title = models.CharField(max_length=255)
    message = models.TextField()
    action_url = models.CharField(max_length=500, blank=True, null=True, help_text="URL for action button")
    action_text = models.CharField(max_length=100, blank=True, null=True, help_text="Text for action button")
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Seller Notification'
        verbose_name_plural = 'Seller Notifications'
    
    def __str__(self):
        return f"{self.title} - {self.seller.get_full_name()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class PropertyDocument(models.Model):
    """Model for storing property documents (CMA, inspections, etc.) for approved selling requests"""
    
    DOCUMENT_TYPES = [
        ('cma', 'CMA Report'),
        ('inspection', 'Inspection Report'),
        ('appraisal', 'Appraisal Report'),
        ('other', 'Other Document'),
    ]
    
    STATUS_CHOICES = [
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    selling_request = models.ForeignKey(SellingRequest, on_delete=models.CASCADE, related_name='documents')
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='property_documents')
    
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='cma')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Remove single file field - now using DocumentFile model for multiple files
    # file = models.FileField(upload_to='property_documents/%Y/%m/%d/')
    # file_size = models.BigIntegerField(help_text="File size in bytes")
    
    # CMA specific status fields
    cma_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        null=True,
        blank=True,
        help_text="Status of the CMA report (accepted or rejected)"
    )
    cma_document_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        null=True,
        blank=True,
        help_text="Document approval status (accepted or rejected)"
    )
    
    # Selling Agreement Document
    selling_agreement_file = models.FileField(
        upload_to='selling_agreements/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Selling agreement document (PDF, JPG, PNG)"
    )
    
    # Selling Agreement Status
    agreement_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        null=True,
        blank=True,
        help_text="Status of the selling agreement (accepted or rejected)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Property Document'
        verbose_name_plural = 'Property Documents'
    
    def __str__(self):
        return f"{self.title} - {self.selling_request.seller.get_full_name()}"
    
    def get_file_extension(self):
        """Get file extension of first file (for backward compatibility)"""
        if self.files.exists():
            return self.files.first().get_file_extension()
        return ""
    
    def get_file_size_mb(self):
        """Get total file size in MB of all files"""
        total_size = sum(file.file_size for file in self.files.all())
        return round(total_size / (1024 * 1024), 2)


class DocumentFile(models.Model):
    """Model for storing individual files attached to a property document"""
    property_document = models.ForeignKey(PropertyDocument, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='property_documents/%Y/%m/%d/')
    file_size = models.BigIntegerField(help_text="File size in bytes")
    original_filename = models.CharField(max_length=255, help_text="Original filename before upload")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Document File'
        verbose_name_plural = 'Document Files'
    
    def __str__(self):
        return f"{self.original_filename} ({self.property_document.title})"
    
    def get_file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.file.name)[1].lower().lstrip('.')
    
    def get_file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)


class AgentNotification(models.Model):
    """Model for agent notifications when sellers update documents or when documents are uploaded"""
    
    NOTIFICATION_TYPES = [
        ('document_uploaded', 'Seller Uploaded Document'),
        ('cma_requested', 'CMA Requested'),
        ('document_updated', 'Document Updated'),
        ('new_selling_request', 'New Selling Request'),
        ('showing_requested', 'Showing Requested'),
        ('showing_accepted', 'Showing Accepted'),
        ('showing_declined', 'Showing Declined'),
    ]
    
    # For multi-agent support in future, link to agent who should receive notification
    # For now, notifications go to admin/first agent
    agent = models.ForeignKey('agent.Agent', on_delete=models.CASCADE, related_name='notifications', null=True, blank=True, help_text="Agent who receives this notification")
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    
    # Related entities
    selling_request = models.ForeignKey(SellingRequest, on_delete=models.CASCADE, related_name='agent_notifications', null=True, blank=True)
    property_document = models.ForeignKey(PropertyDocument, on_delete=models.CASCADE, related_name='agent_notifications', null=True, blank=True)
    showing_schedule = models.ForeignKey('buyer.ShowingSchedule', on_delete=models.CASCADE, related_name='agent_notifications', null=True, blank=True, help_text="Related showing schedule")
    
    # Notification content
    title = models.CharField(max_length=255)
    message = models.TextField()
    action_url = models.CharField(max_length=500, blank=True, null=True)
    action_text = models.CharField(max_length=100, blank=True, null=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Agent Notification'
        verbose_name_plural = 'Agent Notifications'
    
    def __str__(self):
        if self.selling_request:
            return f"{self.title} - {self.selling_request.seller.get_full_name()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
        elif self.showing_schedule:
            return f"{self.title} - Showing Request ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
        return f"{self.title} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class SellerPrivacySecurity(models.Model):
    """Privacy and Security settings for Seller - One record per Seller"""
    seller = models.OneToOneField(Seller, on_delete=models.CASCADE, related_name='privacy_security')
    
    # Data Collection
    collect_basic_info = models.BooleanField(
        default=True,
        help_text="Collect name, email, phone number, login details"
    )
    collect_property_info = models.BooleanField(
        default=True,
        help_text="Collect property information and agreement documents"
    )
    collect_activity_logs = models.BooleanField(
        default=True,
        help_text="Collect activity logs related to buying/selling/browsing"
    )
    collect_chat_messages = models.BooleanField(
        default=True,
        help_text="Collect chat messages and communications"
    )
    collect_documents = models.BooleanField(
        default=True,
        help_text="Collect uploaded documents for compliance"
    )
    collect_optional_info = models.BooleanField(
        default=False,
        help_text="Collect optional identity verification files"
    )
    
    # Data Usage
    use_for_services = models.BooleanField(
        default=True,
        help_text="Use data to provide property search and connection services"
    )
    use_for_cma_reports = models.BooleanField(
        default=True,
        help_text="Use data to prepare CMA reports"
    )
    use_for_alerts = models.BooleanField(
        default=True,
        help_text="Send alerts about tours, offers, pricing updates"
    )
    use_for_compliance = models.BooleanField(
        default=True,
        help_text="Use data for platform security and compliance"
    )
    
    # Data Sharing
    share_with_partners = models.BooleanField(
        default=True,
        help_text="Share with e-signature vendors, payment processors, valuation partners"
    )
    share_with_legal = models.BooleanField(
        default=True,
        help_text="Share with legal authorities when required by law"
    )
    
    # Security
    allow_multi_factor_auth = models.BooleanField(
        default=True,
        help_text="Enable multi-factor authentication"
    )
    encrypted_communication = models.BooleanField(
        default=True,
        help_text="Use HTTPS/SSL encryption for sensitive actions"
    )
    
    # Data Retention
    data_retention_months = models.IntegerField(
        default=24,
        help_text="Keep transaction records and agreement history for X months"
    )
    allow_data_deletion = models.BooleanField(
        default=True,
        help_text="Allow user to request data deletion"
    )
    
    # Additional Settings
    privacy_policy_accepted = models.BooleanField(
        default=False,
        help_text="User has accepted privacy policy"
    )
    privacy_policy_version = models.CharField(
        max_length=10,
        default="1.0",
        help_text="Version of accepted privacy policy"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Seller Privacy & Security'
        verbose_name_plural = 'Seller Privacy & Security'
    
    def __str__(self):
        return f"Privacy & Security for {self.seller.username}"


class SellerTermsConditions(models.Model):
    """Terms and Conditions settings for Seller - One record per Seller"""
    seller = models.OneToOneField(Seller, on_delete=models.CASCADE, related_name='terms_conditions')
    
    # Account Responsibility
    account_responsibility = models.BooleanField(
        default=True,
        help_text="Accept responsibility for keeping account details accurate and secure"
    )
    
    # Service Description
    service_description_accepted = models.BooleanField(
        default=False,
        help_text="Accept the app's service description: browse properties, communicate, request CMA reports, sign agreements"
    )
    
    # Digital Agreements
    accept_digital_agreements = models.BooleanField(
        default=False,
        help_text="Accept that app may include legally binding digital agreements (touring, buyer, listing agreements)"
    )
    
    # Payment Terms
    payment_charges_understood = models.BooleanField(
        default=False,
        help_text="Understand all charges will be shown before payment"
    )
    
    # Unauthorized Activity
    no_fraud = models.BooleanField(
        default=True,
        help_text="Agree not to use app for fraud, harassment, unauthorized marketing, data scraping, or illegal activity"
    )
    no_harmful_content = models.BooleanField(
        default=True,
        help_text="Agree not to upload harmful, abusive, or copyrighted content without permission"
    )
    
    # Version Tracking
    terms_version = models.CharField(
        max_length=10,
        default="1.0",
        help_text="Version of accepted terms and conditions"
    )
    terms_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the user accepted the terms"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Seller Terms & Conditions'
        verbose_name_plural = 'Seller Terms & Conditions'
    
    def __str__(self):
        return f"Terms & Conditions for {self.seller.username}"
