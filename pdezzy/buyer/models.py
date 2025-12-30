from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Buyer(AbstractUser):
    """Buyer user model with property preference fields"""
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/buyers/', blank=True, null=True, help_text="Profile image")
    price_range = models.CharField(max_length=255, blank=True, null=True, help_text="Preferred price range")
    location = models.CharField(max_length=255, blank=True, null=True, help_text="Preferred buying area")
    bedrooms = models.IntegerField(blank=True, null=True, help_text="Preferred number of bedrooms")
    bathrooms = models.IntegerField(blank=True, null=True, help_text="Preferred number of bathrooms")
    mortgage_letter = models.FileField(upload_to='mortgage_letters/buyers/', blank=True, null=True, help_text="Mortgage pre-approval letter (PDF, JPG, PNG - max 10MB)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Buyer'
        verbose_name_plural = 'Buyers'

    def __str__(self):
        return f"{self.username} - {self.email}"


class BuyerPrivacySecurity(models.Model):
    """Privacy and Security settings for Buyer - One record per Buyer"""
    buyer = models.OneToOneField(Buyer, on_delete=models.CASCADE, related_name='privacy_security')
    
    # Data Collection
    collect_basic_info = models.BooleanField(
        default=True,
        help_text="Collect name, email, phone number, login details"
    )
    collect_property_preferences = models.BooleanField(
        default=True,
        help_text="Collect property preferences and search history"
    )
    collect_activity_logs = models.BooleanField(
        default=True,
        help_text="Collect activity logs related to property browsing"
    )
    collect_chat_messages = models.BooleanField(
        default=True,
        help_text="Collect chat messages with sellers and agents"
    )
    collect_documents = models.BooleanField(
        default=True,
        help_text="Collect agreement documents and contracts"
    )
    collect_optional_info = models.BooleanField(
        default=False,
        help_text="Collect optional identity verification files"
    )
    
    # Data Usage
    use_for_services = models.BooleanField(
        default=True,
        help_text="Use data to provide property search services"
    )
    use_for_recommendations = models.BooleanField(
        default=True,
        help_text="Use data to recommend properties based on preferences"
    )
    use_for_alerts = models.BooleanField(
        default=True,
        help_text="Send alerts about new listings and pricing updates"
    )
    use_for_compliance = models.BooleanField(
        default=True,
        help_text="Use data for platform security and compliance"
    )
    
    # Data Sharing
    share_with_partners = models.BooleanField(
        default=True,
        help_text="Share with payment processors and service providers"
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
        help_text="Use HTTPS/SSL encryption"
    )
    
    # Data Retention
    data_retention_months = models.IntegerField(
        default=24,
        help_text="Keep transaction records and agreements for X months"
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
        verbose_name = 'Buyer Privacy & Security'
        verbose_name_plural = 'Buyer Privacy & Security'
    
    def __str__(self):
        return f"Privacy & Security for {self.buyer.username}"

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    # Override ManyToMany related names to prevent clash with Agent and Seller
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='buyer_groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='buyer_permissions'
    )


class BuyerTermsConditions(models.Model):
    """Terms and Conditions settings for Buyer - One record per Buyer"""
    buyer = models.OneToOneField(Buyer, on_delete=models.CASCADE, related_name='terms_conditions')
    
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
        verbose_name = 'Buyer Terms & Conditions'
        verbose_name_plural = 'Buyer Terms & Conditions'
    
    def __str__(self):
        return f"Terms & Conditions for {self.buyer.username}"


class ShowingSchedule(models.Model):
    """Schedule for showing requests by buyers to view agent property listings"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    PREFERRED_TIME_CHOICES = [
        ('morning', 'Morning (9 AM - 12 PM)'),
        ('afternoon', 'Afternoon (12 PM - 5 PM)'),
        ('evening', 'Evening (5 PM - 8 PM)'),
    ]
    
    buyer = models.ForeignKey(
        Buyer,
        on_delete=models.CASCADE,
        related_name='showing_schedules',
        help_text="Buyer requesting the showing"
    )
    property_listing = models.ForeignKey(
        'agent.PropertyListing',
        on_delete=models.CASCADE,
        related_name='showing_schedules',
        help_text="Property listing to view"
    )
    
    # Schedule Details
    requested_date = models.DateField(help_text="Preferred date for showing")
    preferred_time = models.CharField(
        max_length=20,
        choices=PREFERRED_TIME_CHOICES,
        default='afternoon',
        help_text="Preferred time slot"
    )
    additional_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Any special requests or questions"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Status of the showing request"
    )
    
    # Agent Response
    agent_response = models.TextField(
        blank=True,
        null=True,
        help_text="Agent's response or notes"
    )
    responded_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the agent responded"
    )
    
    # Confirmed Details (after acceptance)
    confirmed_date = models.DateField(
        blank=True,
        null=True,
        help_text="Final confirmed date for showing"
    )
    confirmed_time = models.TimeField(
        blank=True,
        null=True,
        help_text="Final confirmed time for showing"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Showing Schedule'
        verbose_name_plural = 'Showing Schedules'
    
    def __str__(self):
        return f"{self.buyer.username} - {self.property_listing.title} ({self.status})"


class BuyerNotification(models.Model):
    """Notifications for buyers about showing responses and updates"""
    
    NOTIFICATION_TYPES = [
        ('showing_accepted', 'Showing Accepted'),
        ('showing_declined', 'Showing Declined'),
        ('showing_reminder', 'Showing Reminder'),
        ('general', 'General Notification'),
    ]
    
    buyer = models.ForeignKey(
        Buyer,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="Buyer receiving the notification"
    )
    showing_schedule = models.ForeignKey(
        ShowingSchedule,
        on_delete=models.CASCADE,
        related_name='buyer_notifications',
        blank=True,
        null=True,
        help_text="Related showing schedule"
    )
    
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default='general',
        help_text="Type of notification"
    )
    title = models.CharField(max_length=255, help_text="Notification title")
    message = models.TextField(help_text="Notification message")
    
    # Status
    is_read = models.BooleanField(default=False, help_text="Whether notification has been read")
    read_at = models.DateTimeField(blank=True, null=True, help_text="When notification was read")
    
    # Action
    action_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL for action button"
    )
    action_text = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Text for action button"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Buyer Notification'
        verbose_name_plural = 'Buyer Notifications'
    
    def __str__(self):
        return f"{self.buyer.username} - {self.title}"


class ShowingAgreement(models.Model):
    """Digital showing agreement with buyer signature"""
    
    showing_schedule = models.OneToOneField(
        ShowingSchedule,
        on_delete=models.CASCADE,
        related_name='agreement',
        help_text="Related showing schedule"
    )
    buyer = models.ForeignKey(
        Buyer,
        on_delete=models.CASCADE,
        related_name='showing_agreements',
        help_text="Buyer signing the agreement"
    )
    agent = models.ForeignKey(
        'agent.Agent',
        on_delete=models.CASCADE,
        related_name='showing_agreements',
        help_text="Agent for the showing"
    )
    
    # Agreement Details
    duration_type = models.CharField(
        max_length=50,
        choices=[('7_days', '7 Days'), ('one_property', 'One Property Only')],
        default='one_property',
        help_text="Duration of the agreement"
    )
    property_address = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Property address if applicable"
    )
    showing_date = models.DateField(help_text="Scheduled showing date")
    
    # Signature
    signature = models.TextField(
        blank=True,
        null=True,
        help_text="Buyer's digital signature (base64 encoded image or text)"
    )
    
    agreement_accepted = models.BooleanField(
        default=False,
        help_text="Whether buyer accepted the terms"
    )
    
    # Terms Acceptance
    terms_text = models.TextField(
        blank=True,
        null=True,
        help_text="Full text of terms that were accepted"
    )
    
    # Timestamps
    signed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Showing Agreement'
        verbose_name_plural = 'Showing Agreements'
    
    def __str__(self):
        return f"Agreement - {self.buyer.username} - {self.showing_schedule}"


class BuyerDocument(models.Model):
    """Model for storing buyer agreement documents"""
    
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255, help_text="Document title")
    description = models.TextField(blank=True, null=True, help_text="Document description")
    document_file = models.FileField(upload_to='buyer_documents/%Y/%m/%d/', help_text="Document file (PDF)")
    file_size = models.BigIntegerField(help_text="File size in bytes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Buyer Document'
        verbose_name_plural = 'Buyer Documents'
    
    def __str__(self):
        return f"{self.title} - {self.buyer.username}"
    
    def get_file_extension(self):
        """Get file extension"""
        import os
        return os.path.splitext(self.document_file.name)[1].lower().lstrip('.')
    
    def get_file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)


class SavedListing(models.Model):
    """Buyer saved/bookmarked listings for later viewing"""
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, related_name='saved_listings')
    listing_id = models.IntegerField(help_text="PropertyListing ID that buyer saved")
    notes = models.TextField(blank=True, null=True, help_text="Optional notes about why this listing was saved")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Saved Listing'
        verbose_name_plural = 'Saved Listings'
        unique_together = ['buyer', 'listing_id']
    
    def __str__(self):
        return f"{self.buyer.username} saved listing #{self.listing_id}"
