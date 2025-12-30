from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.db.models import JSONField


class Agent(AbstractUser):
    """Agent user model with profile fields"""
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    license_number = models.CharField(max_length=50, blank=True, null=True)
    agent_papers = models.FileField(upload_to='agent_papers/', blank=True, null=True, help_text="Agent certificate or documents")
    
    # About & Bio
    about = models.TextField(blank=True, null=True, help_text="Tell clients about yourself (max 500 characters)")
    
    # Professional Information
    company_details = models.CharField(max_length=255, blank=True, null=True, help_text="Real estate company or firm name")
    years_of_experience = models.IntegerField(blank=True, null=True, help_text="Years of experience in real estate")
    area_of_expertise = models.TextField(blank=True, null=True, help_text="Areas of expertise (e.g., residential, commercial)")
    
    # Languages - Multiple entries (stored as JSON array)
    languages = JSONField(
        default=list,
        blank=True,
        help_text="Languages spoken (array of strings, e.g., ['English', 'Spanish', 'French'])"
    )
    
    # Service Areas - Multiple entries
    service_areas = JSONField(
        default=list,
        blank=True,
        help_text="Service areas (array of strings, e.g., ['Springfield', 'Downtown', 'Suburban Areas'])"
    )
    
    # Property Types - Multiple entries
    property_types = JSONField(
        default=list,
        blank=True,
        help_text="Property types handled (array of strings, e.g., ['Single Family', 'Condos', 'Townhouses'])"
    )
    
    # Availability Type
    AVAILABILITY_CHOICES = [
        ('full-time', 'Full-time'),
        ('part-time', 'Part-time'),
        ('project-based', 'Project-Based'),
    ]
    availability = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default='full-time',
        blank=True,
        null=True,
        help_text="Agent availability type"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Agent'
        verbose_name_plural = 'Agents'

    def __str__(self):
        return f"{self.username} - {self.email}"
    
    # Override ManyToMany related names to prevent clash
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='agent_groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='agent_permissions'
    )


class AgentPrivacySecurity(models.Model):
    """Privacy and Security settings for Agent - One record per Agent"""
    agent = models.OneToOneField(Agent, on_delete=models.CASCADE, related_name='privacy_security')
    
    # Data Collection
    collect_basic_info = models.BooleanField(
        default=True,
        help_text="Collect name, email, phone number, login details"
    )
    collect_activity_logs = models.BooleanField(
        default=True,
        help_text="Collect activity logs and platform usage"
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
        help_text="Collect optional identity verification and files"
    )
    
    # Data Usage
    use_for_services = models.BooleanField(
        default=True,
        help_text="Use data to provide services"
    )
    use_for_alerts = models.BooleanField(
        default=True,
        help_text="Send alerts about offers and updates"
    )
    use_for_compliance = models.BooleanField(
        default=True,
        help_text="Use data for platform security and compliance"
    )
    
    # Data Sharing
    share_with_partners = models.BooleanField(
        default=True,
        help_text="Share with trusted service providers and legal authorities"
    )
    
    # Security
    allow_multi_factor_auth = models.BooleanField(
        default=True,
        help_text="Enable multi-factor authentication"
    )
    encrypted_communication = models.BooleanField(
        default=True,
        help_text="Use HTTPS/SSL encryption"
    )
    
    # Data Retention
    data_retention_months = models.IntegerField(
        default=24,
        help_text="Keep data for X months unless legally required"
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
        verbose_name = 'Agent Privacy & Security'
        verbose_name_plural = 'Agent Privacy & Security'
    
    def __str__(self):
        return f"Privacy & Security for {self.agent.username}"


class AgentTermsConditions(models.Model):
    """Terms and Conditions settings for Agent - One record per Agent"""
    agent = models.OneToOneField(Agent, on_delete=models.CASCADE, related_name='terms_conditions')
    
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
        verbose_name = 'Agent Terms & Conditions'
        verbose_name_plural = 'Agent Terms & Conditions'
    
    def __str__(self):
        return f"Terms & Conditions for {self.agent.username}"


class PropertyListing(models.Model):
    """Property listing created by agent after seller accepts agreement"""
    
    PROPERTY_TYPE_CHOICES = [
        ('house', 'House'),
        ('apartment', 'Apartment'),
        ('condo', 'Condominium'),
        ('townhouse', 'Townhouse'),
        ('land', 'Land'),
        ('commercial', 'Commercial'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('published', 'Published'),
        ('sold', 'Sold'),
        ('archived', 'Archived'),
    ]
    
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='property_listings')
    property_document = models.OneToOneField(
        'seller.PropertyDocument',
        on_delete=models.CASCADE,
        related_name='listing',
        null=True,
        blank=True,
        help_text="Property document with accepted selling agreement (optional for admin-created listings)"
    )
    
    # Basic Info
    title = models.CharField(max_length=255, help_text="Property title")
    
    # Address
    street_address = models.CharField(max_length=255, help_text="Street address")
    city = models.CharField(max_length=100, help_text="City")
    state = models.CharField(max_length=50, help_text="State")
    zip_code = models.CharField(max_length=20, help_text="ZIP code")
    
    # Property Details
    property_type = models.CharField(
        max_length=20,
        choices=PROPERTY_TYPE_CHOICES,
        default='house',
        help_text="Type of property"
    )
    bedrooms = models.IntegerField(null=True, blank=True, help_text="Number of bedrooms")
    bathrooms = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Number of bathrooms"
    )
    square_feet = models.IntegerField(null=True, blank=True, help_text="Square footage")
    description = models.TextField(null=True, blank=True, help_text="Property description")
    
    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Listing price in dollars")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Listing status"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Property Listing'
        verbose_name_plural = 'Property Listings'
    
    def __str__(self):
        return f"{self.title} - {self.city}, {self.state}"


class PropertyListingPhoto(models.Model):
    """Photos for property listing"""
    listing = models.ForeignKey(PropertyListing, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to='property_photos/%Y/%m/', help_text="Property photo (JPG, PNG, max 10MB)")
    caption = models.CharField(max_length=255, null=True, blank=True, help_text="Photo caption")
    is_primary = models.BooleanField(default=False, help_text="Is this the primary/featured photo")
    order = models.IntegerField(default=0, help_text="Display order")
    file_size = models.BigIntegerField(null=True, blank=True, help_text="File size in bytes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Property Listing Photo'
        verbose_name_plural = 'Property Listing Photos'
    
    def __str__(self):
        return f"Photo for {self.listing.title}"


class PropertyListingDocument(models.Model):
    """Documents for property listing"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('deed', 'Property Deed'),
        ('inspection', 'Inspection Report'),
        ('appraisal', 'Appraisal Report'),
        ('floor_plan', 'Floor Plan'),
        ('other', 'Other Document'),
    ]
    
    listing = models.ForeignKey(PropertyListing, on_delete=models.CASCADE, related_name='listing_documents')
    document = models.FileField(upload_to='listing_documents/%Y/%m/', help_text="Document file (PDF, JPG, PNG, max 10MB)")
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        default='other',
        help_text="Type of document"
    )
    title = models.CharField(max_length=255, help_text="Document title")
    file_size = models.BigIntegerField(null=True, blank=True, help_text="File size in bytes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Property Listing Document'
        verbose_name_plural = 'Property Listing Documents'
    
    def __str__(self):
        return f"{self.title} - {self.listing.title}"
