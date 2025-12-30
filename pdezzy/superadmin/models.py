from django.db import models
from django.conf import settings


class AgentPrivacyPolicy(models.Model):
    """Privacy Policy for Agents"""
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Privacy policy content (supports HTML)")
    version = models.CharField(max_length=50, default="1.0")
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_agent_privacy_policies'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agent Privacy Policy"
        verbose_name_plural = "Agent Privacy Policies"
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def save(self, *args, **kwargs):
        if self.is_active:
            AgentPrivacyPolicy.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class AgentTermsConditions(models.Model):
    """Terms & Conditions for Agents"""
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Terms & conditions content (supports HTML)")
    version = models.CharField(max_length=50, default="1.0")
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_agent_terms_conditions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agent Terms & Conditions"
        verbose_name_plural = "Agent Terms & Conditions"
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def save(self, *args, **kwargs):
        if self.is_active:
            AgentTermsConditions.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class SellerPrivacyPolicy(models.Model):
    """Privacy Policy for Sellers"""
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Privacy policy content (supports HTML)")
    version = models.CharField(max_length=50, default="1.0")
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_seller_privacy_policies'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Seller Privacy Policy"
        verbose_name_plural = "Seller Privacy Policies"
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def save(self, *args, **kwargs):
        if self.is_active:
            SellerPrivacyPolicy.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class SellerTermsConditions(models.Model):
    """Terms & Conditions for Sellers"""
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Terms & conditions content (supports HTML)")
    version = models.CharField(max_length=50, default="1.0")
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_seller_terms_conditions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Seller Terms & Conditions"
        verbose_name_plural = "Seller Terms & Conditions"
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def save(self, *args, **kwargs):
        if self.is_active:
            SellerTermsConditions.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class BuyerPrivacyPolicy(models.Model):
    """Privacy Policy for Buyers"""
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Privacy policy content (supports HTML)")
    version = models.CharField(max_length=50, default="1.0")
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_buyer_privacy_policies'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Buyer Privacy Policy"
        verbose_name_plural = "Buyer Privacy Policies"
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def save(self, *args, **kwargs):
        if self.is_active:
            BuyerPrivacyPolicy.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class BuyerTermsConditions(models.Model):
    """Terms & Conditions for Buyers"""
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Terms & conditions content (supports HTML)")
    version = models.CharField(max_length=50, default="1.0")
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_buyer_terms_conditions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Buyer Terms & Conditions"
        verbose_name_plural = "Buyer Terms & Conditions"
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def save(self, *args, **kwargs):
        if self.is_active:
            BuyerTermsConditions.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class PlatformDocument(models.Model):
    """
    Platform-wide documents (Mortgage Letter, CMA Report, Showing Agreement, Selling Agreement, Buyer Agreement)
    Uploaded by admin and viewable by buyers/sellers
    """
    
    DOCUMENT_TYPES = [
        ('mortgage_letter', 'Mortgage Letter'),
        ('cma_report', 'CMA Report'),
        ('showing_agreement', 'Showing Agreement'),
        ('selling_agreement', 'Selling Agreement'),
        ('buyer_agreement', 'Buyer Agreement'),
    ]
    
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPES,
        help_text="Type of document"
    )
    title = models.CharField(
        max_length=255,
        help_text="Document title"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Document description or notes"
    )
    document = models.FileField(
        upload_to='platform_documents/%Y/%m/%d/',
        help_text="Document file (PDF, JPG, PNG supported)"
    )
    file_size = models.BigIntegerField(
        default=0,
        editable=False,
        help_text="File size in bytes"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is this document currently active?"
    )
    version = models.CharField(
        max_length=50,
        default="1.0",
        help_text="Document version"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_platform_documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Platform Document"
        verbose_name_plural = "Platform Documents"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document_type', 'is_active']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.title}"
    
    def save(self, *args, **kwargs):
        # Store file size
        if self.document:
            self.file_size = self.document.size
        super().save(*args, **kwargs)

