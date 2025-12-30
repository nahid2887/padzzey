from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.admin_login, name='admin_login'),
    
    # Dashboard
    path('dashboard/', views.admin_dashboard_data, name='admin_dashboard_data'),
    
    # Admin Profile
    path('profile/', views.admin_profile, name='admin_profile'),
    
    # User Management
    path('users/', views.admin_list_users, name='admin_list_users'),
    path('users/<int:user_id>/', views.admin_get_user, name='admin_get_user'),  # GET, DELETE
    path('users/<int:user_id>/update/', views.admin_update_user, name='admin_update_user'),
    
    # Property Listing Management
    path('listings/', views.admin_list_property_listings, name='admin_list_property_listings'),
    path('listings/<int:listing_id>/', views.admin_get_property_listing, name='admin_get_property_listing'),
    path('listings/create/', views.admin_create_property_listing, name='admin_create_property_listing'),
    path('listings/<int:listing_id>/delete/', views.admin_delete_property_listing, name='admin_delete_property_listing'),
    
    # CMA Report Management
    path('cma/', views.admin_list_cma_reports, name='admin_list_cma_reports'),
    path('cma/<int:cma_id>/', views.admin_get_cma_report, name='admin_get_cma_report'),
    
    # Showing Agreement Management
    path('showing-agreements/', views.admin_list_showing_agreements, name='admin_list_showing_agreements'),
    path('showing-agreements/<int:schedule_id>/', views.admin_get_showing_schedule, name='admin_get_showing_schedule'),
    
    # Selling Agreement Management
    path('selling-agreements/', views.admin_list_selling_agreements, name='admin_list_selling_agreements'),
    path('selling-agreements/<int:agreement_id>/', views.admin_get_selling_agreement, name='admin_get_selling_agreement'),
    
    # Buyer Document Management
    path('buyer-documents/', views.admin_list_buyer_documents, name='admin_list_buyer_documents'),
    path('buyer-documents/<int:document_id>/', views.admin_get_buyer_document, name='admin_get_buyer_document'),
    path('buyer-documents/upload/', views.admin_upload_buyer_document, name='admin_upload_buyer_document'),
    path('buyer-documents/<int:document_id>/delete/', views.admin_delete_buyer_document, name='admin_delete_buyer_document'),
    
    # Legal Documents Management - Agent
    path('legal-documents/agent/privacy-policy/', views.agent_privacy_policy_list_create, name='agent_privacy_policy_list_create'),
    path('legal-documents/agent/privacy-policy/<int:pk>/', views.agent_privacy_policy_detail, name='agent_privacy_policy_detail'),
    path('legal-documents/agent/terms-conditions/', views.agent_terms_conditions_list_create, name='agent_terms_conditions_list_create'),
    path('legal-documents/agent/terms-conditions/<int:pk>/', views.agent_terms_conditions_detail, name='agent_terms_conditions_detail'),
    
    # Legal Documents Management - Seller
    path('legal-documents/seller/privacy-policy/', views.seller_privacy_policy_list_create, name='seller_privacy_policy_list_create'),
    path('legal-documents/seller/privacy-policy/<int:pk>/', views.seller_privacy_policy_detail, name='seller_privacy_policy_detail'),
    path('legal-documents/seller/terms-conditions/', views.seller_terms_conditions_list_create, name='seller_terms_conditions_list_create'),
    path('legal-documents/seller/terms-conditions/<int:pk>/', views.seller_terms_conditions_detail, name='seller_terms_conditions_detail'),
    
    # Legal Documents Management - Buyer
    path('legal-documents/buyer/privacy-policy/', views.buyer_privacy_policy_list_create, name='buyer_privacy_policy_list_create'),
    path('legal-documents/buyer/privacy-policy/<int:pk>/', views.buyer_privacy_policy_detail, name='buyer_privacy_policy_detail'),
    path('legal-documents/buyer/terms-conditions/', views.buyer_terms_conditions_list_create, name='buyer_terms_conditions_list_create'),
    path('legal-documents/buyer/terms-conditions/<int:pk>/', views.buyer_terms_conditions_detail, name='buyer_terms_conditions_detail'),
    
    # Buyer Management
    path('buyers/', views.buyer_list, name='buyer_list'),
    path('buyers/<int:pk>/', views.buyer_detail, name='buyer_detail'),
    
    # Platform Documents Management
    path('documents/', views.platform_documents_list, name='platform_documents_list'),
    path('documents/<int:document_id>/', views.platform_document_detail, name='platform_document_detail'),
    path('documents/public/', views.platform_documents_public, name='platform_documents_public'),
]
