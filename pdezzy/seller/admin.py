from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Seller, SellingRequest, SellerNotification


@admin.register(Seller)
class SellerAdmin(BaseUserAdmin):
    """Admin interface for Seller model"""
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Property info', {'fields': ('location', 'bedrooms', 'bathrooms', 'property_condition')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')
    list_display = ('username', 'email', 'first_name', 'last_name', 'location', 'created_at')
    list_filter = ('is_active', 'is_staff', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'location')


@admin.register(SellingRequest)
class SellingRequestAdmin(admin.ModelAdmin):
    """Admin interface for SellingRequest model"""
    fieldsets = (
        ('Seller Info', {'fields': ('seller',)}),
        ('Description', {'fields': ('selling_reason',)}),
        ('Contact Info', {'fields': ('contact_name', 'contact_email', 'contact_phone')}),
        ('Price', {'fields': ('asking_price',)}),
        ('Time Frame', {'fields': ('start_date', 'end_date')}),
        ('Status', {'fields': ('status',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')
    list_display = ('id', 'seller', 'contact_name', 'asking_price', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'start_date', 'end_date')
    search_fields = ('seller__username', 'seller__email', 'contact_name', 'contact_email')
    date_hierarchy = 'created_at'


@admin.register(SellerNotification)
class SellerNotificationAdmin(admin.ModelAdmin):
    """Admin interface for SellerNotification model"""
    fieldsets = (
        ('Recipient', {'fields': ('seller',)}),
        ('Related Request', {'fields': ('selling_request',)}),
        ('Notification Content', {'fields': ('notification_type', 'title', 'message')}),
        ('Action', {'fields': ('action_url', 'action_text')}),
        ('Status', {'fields': ('is_read',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')
    list_display = ('id', 'seller', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('seller__username', 'seller__email', 'title', 'message')
    date_hierarchy = 'created_at'
