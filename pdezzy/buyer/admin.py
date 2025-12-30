from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Buyer,
    ShowingSchedule,
    BuyerNotification,
    ShowingAgreement,
    SavedListing
)


@admin.register(Buyer)
class BuyerAdmin(BaseUserAdmin):
    """Admin interface for Buyer model"""
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Preferences', {'fields': ('price_range', 'location', 'bedrooms', 'bathrooms')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')
    list_display = ('username', 'email', 'first_name', 'last_name', 'location', 'created_at')
    list_filter = ('is_active', 'is_staff', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'location')


@admin.register(ShowingSchedule)
class ShowingScheduleAdmin(admin.ModelAdmin):
    """Admin interface for Showing Schedules"""
    fieldsets = (
        ('Showing Details', {
            'fields': ('buyer', 'property_listing', 'status')
        }),
        ('Schedule Request', {
            'fields': ('requested_date', 'preferred_time', 'additional_notes')
        }),
        ('Agent Response', {
            'fields': ('agent_response', 'responded_at')
        }),
        ('Confirmed Details', {
            'fields': ('confirmed_date', 'confirmed_time')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    list_display = ('buyer', 'property_listing', 'requested_date', 'preferred_time', 'status', 'created_at')
    list_filter = ('status', 'preferred_time', 'requested_date', 'created_at')
    search_fields = ('buyer__username', 'buyer__email', 'property_listing__title', 'property_listing__city')
    list_editable = ('status',)
    date_hierarchy = 'requested_date'



@admin.register(BuyerNotification)
class BuyerNotificationAdmin(admin.ModelAdmin):
    """Admin interface for Buyer Notifications"""
    list_display = ('buyer', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('buyer__username', 'buyer__email', 'title', 'message')
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    fieldsets = (
        ('Notification Details', {'fields': ('buyer', 'showing_schedule', 'notification_type', 'title', 'message')}),
        ('Status', {'fields': ('is_read', 'read_at')}),
        ('Action', {'fields': ('action_url', 'action_text')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(ShowingAgreement)
class ShowingAgreementAdmin(admin.ModelAdmin):
    """Admin interface for Showing Agreements"""
    list_display = ('buyer', 'agent', 'showing_date', 'duration_type', 'agreement_accepted', 'signed_at')
    list_filter = ('duration_type', 'agreement_accepted', 'signed_at')
    search_fields = ('buyer__username', 'agent__username', 'property_address')
    readonly_fields = ('signed_at', 'created_at', 'updated_at')
    fieldsets = (
        ('Agreement Details', {'fields': ('showing_schedule', 'buyer', 'agent')}),
        ('Property & Schedule', {'fields': ('duration_type', 'property_address', 'showing_date')}),
        ('Signature', {'fields': ('signature', 'agreement_accepted')}),
        ('Terms', {'fields': ('terms_text',)}),
        ('Timestamps', {'fields': ('signed_at', 'created_at', 'updated_at')}),
    )


@admin.register(SavedListing)
class SavedListingAdmin(admin.ModelAdmin):
    """Admin interface for Saved Listings"""
    list_display = ('buyer', 'listing_id', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('buyer__username', 'buyer__email', 'listing_id', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Saved Listing Details', {'fields': ('buyer', 'listing_id', 'notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
