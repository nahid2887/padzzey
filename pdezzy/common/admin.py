from django.contrib import admin
from .models import PasswordResetToken, LegalDocument


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """Admin interface for PasswordResetToken"""
    list_display = ('email', 'user_type', 'otp', 'is_valid_status', 'created_at', 'expires_at', 'is_used')
    list_filter = ('user_type', 'is_used', 'created_at')
    search_fields = ('email', 'otp')
    readonly_fields = ('created_at', 'expires_at')

    def is_valid_status(self, obj):
        """Display if token is valid"""
        return obj.is_valid()
    is_valid_status.short_description = 'Is Valid'


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    """Admin interface for Legal Documents"""
    list_display = ('title', 'document_type', 'user_type', 'version', 'is_active', 'effective_date', 'created_at')
    list_filter = ('document_type', 'user_type', 'is_active', 'effective_date', 'created_at')
    search_fields = ('title', 'content', 'version')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    
    fieldsets = (
        ('Document Information', {
            'fields': ('document_type', 'user_type', 'title', 'version')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('Status & Dates', {
            'fields': ('is_active', 'effective_date')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user if not set"""
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
