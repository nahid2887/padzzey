from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Agent, PropertyListing, PropertyListingPhoto, PropertyListingDocument


@admin.register(Agent)
class AgentAdmin(BaseUserAdmin):
    """Admin interface for Agent model"""
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Profile', {'fields': ('profile_picture', 'license_number', 'agent_papers')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'created_at')
    list_filter = ('is_active', 'is_staff', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'license_number')


class PropertyListingPhotoInline(admin.TabularInline):
    """Inline admin for property listing photos"""
    model = PropertyListingPhoto
    extra = 0
    readonly_fields = ('file_size', 'created_at')


class PropertyListingDocumentInline(admin.TabularInline):
    """Inline admin for property listing documents"""
    model = PropertyListingDocument
    extra = 0
    readonly_fields = ('file_size', 'created_at')


@admin.register(PropertyListing)
class PropertyListingAdmin(admin.ModelAdmin):
    """Admin interface for Property Listings"""
    fieldsets = (
        ('Basic Info', {'fields': ('agent', 'property_document', 'title', 'status')}),
        ('Address', {'fields': ('street_address', 'city', 'state', 'zip_code', 'property_type')}),
        ('Details', {'fields': ('bedrooms', 'bathrooms', 'square_feet', 'description')}),
        ('Pricing', {'fields': ('price',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at', 'published_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'published_at')
    list_display = ('title', 'agent', 'property_type', 'price', 'status', 'city', 'state', 'created_at')
    list_filter = ('status', 'property_type', 'state', 'created_at')
    search_fields = ('title', 'street_address', 'city', 'agent__username', 'agent__email')
    inlines = [PropertyListingPhotoInline, PropertyListingDocumentInline]


@admin.register(PropertyListingPhoto)
class PropertyListingPhotoAdmin(admin.ModelAdmin):
    """Admin interface for Property Listing Photos"""
    list_display = ('listing', 'caption', 'is_primary', 'order', 'file_size', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('listing__title', 'caption')
    readonly_fields = ('file_size', 'created_at')


@admin.register(PropertyListingDocument)
class PropertyListingDocumentAdmin(admin.ModelAdmin):
    """Admin interface for Property Listing Documents"""
    list_display = ('listing', 'title', 'document_type', 'file_size', 'created_at')
    list_filter = ('document_type', 'created_at')
    search_fields = ('listing__title', 'title')
    readonly_fields = ('file_size', 'created_at')
