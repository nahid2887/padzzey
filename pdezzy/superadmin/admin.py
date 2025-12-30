from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.db.models import Count, Q
from django.utils.html import format_html
from agent.models import Agent, PropertyListing
from seller.models import Seller
from buyer.models import Buyer
from datetime import datetime, timedelta


class CustomAdminSite(admin.AdminSite):
    site_header = "PDezzy Admin Dashboard"
    site_title = "PDezzy Admin"
    index_title = "Welcome to PDezzy Administration"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        """Custom dashboard view with statistics"""
        # Get counts
        total_agents = Agent.objects.count()
        total_sellers = Seller.objects.count()
        total_buyers = Buyer.objects.count()
        total_users = total_agents + total_sellers + total_buyers
        total_listings = PropertyListing.objects.count()
        
        # Active users (logged in within last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        active_agents = Agent.objects.filter(last_login__gte=thirty_days_ago).count()
        active_sellers = Seller.objects.filter(last_login__gte=thirty_days_ago).count()
        
        # Recent users (last 10)
        recent_agents = Agent.objects.order_by('-date_joined')[:3]
        recent_sellers = Seller.objects.order_by('-date_joined')[:3]
        recent_buyers = Buyer.objects.order_by('-date_joined')[:4]
        
        # Recent properties
        recent_properties = PropertyListing.objects.select_related('agent').order_by('-created_at')[:5]
        
        # Weekly data for chart (last 7 days)
        weekly_data = []
        for i in range(6, -1, -1):
            day = datetime.now() - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            agents_count = Agent.objects.filter(date_joined__gte=day_start, date_joined__lte=day_end).count()
            sellers_count = Seller.objects.filter(date_joined__gte=day_start, date_joined__lte=day_end).count()
            buyers_count = Buyer.objects.filter(date_joined__gte=day_start, date_joined__lte=day_end).count()
            
            weekly_data.append({
                'day': day.strftime('%a'),
                'active': agents_count + sellers_count + buyers_count,
                'new': buyers_count
            })
        
        context = {
            **self.each_context(request),
            'total_users': total_users,
            'total_agents': total_agents,
            'total_sellers': total_sellers,
            'total_buyers': total_buyers,
            'total_listings': total_listings,
            'active_agents': active_agents,
            'active_sellers': active_sellers,
            'recent_agents': recent_agents,
            'recent_sellers': recent_sellers,
            'recent_buyers': recent_buyers,
            'recent_properties': recent_properties,
            'weekly_data': weekly_data,
        }
        
        return render(request, 'admin/dashboard.html', context)
    
    def index(self, request, extra_context=None):
        """Override index to redirect to custom dashboard"""
        return self.dashboard_view(request)


# Create custom admin site instance
admin_site = CustomAdminSite(name='custom_admin')


@admin.register(Agent, site=admin_site)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'phone_number', 'license_number', 'is_active', 'date_joined')
    list_filter = ('is_active', 'date_joined')
    search_fields = ('username', 'email', 'phone_number', 'license_number')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        ('Account Info', {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone_number', 'license_number', 'profile_picture', 'agent_papers')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login')
        }),
    )


@admin.register(Seller, site=admin_site)
class SellerAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'phone_number', 'location', 'is_active', 'date_joined')
    list_filter = ('is_active', 'date_joined')
    search_fields = ('username', 'email', 'phone_number', 'location')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        ('Account Info', {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone_number')
        }),
        ('Property Info', {
            'fields': ('location', 'bedrooms', 'bathrooms', 'property_condition')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login')
        }),
    )


@admin.register(Buyer, site=admin_site)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'phone_number', 'location', 'price_range', 'is_active', 'date_joined')
    list_filter = ('is_active', 'date_joined')
    search_fields = ('username', 'email', 'phone_number', 'location')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        ('Account Info', {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone_number')
        }),
        ('Preferences', {
            'fields': ('price_range', 'location', 'bedrooms', 'bathrooms')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login')
        }),
    )


@admin.register(PropertyListing, site=admin_site)
class PropertyListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'agent', 'price', 'city', 'bedrooms', 'bathrooms', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'bedrooms', 'bathrooms', 'property_type')
    search_fields = ('title', 'city', 'street_address', 'description', 'agent__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('agent', 'property_document', 'title', 'description', 'status')
        }),
        ('Address', {
            'fields': ('street_address', 'city', 'state', 'zip_code')
        }),
        ('Property Details', {
            'fields': ('price', 'bedrooms', 'bathrooms', 'square_feet', 'lot_size', 'property_type', 'year_built')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
