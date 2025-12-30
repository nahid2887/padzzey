from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    CustomTokenObtainPairView,
    RefreshTokenView,
    LogoutView,
    ProfileView,
    ProfileUpdateView,
    ChangePasswordView,
    UserDetailView,
    AgentSellingRequestListView,
    AgentSellingRequestDetailView,
    AgentSellingRequestStatusUpdateView,
    AgentSellingRequestStatsView,
    AgentNotificationListView,
    AgentNotificationDetailView,
    AgentNotificationUnreadCountView,
    AgentNotificationMarkAllReadView,
    AgentCMAUploadView,
    AgentCMAListView,
    AgentPropertyDocumentListView,
    AgentPropertyDocumentDetailView,
    AgentSellingAgreementUploadView,
    # Property Listing view
    AgentListingsView,
    AgentCreateListingView,
    AgentListingPhotoUploadView,
    AgentListingDocumentUploadView,
    # Showing Schedule views
    AgentShowingScheduleListView,
    AgentShowingScheduleDetailView,
    AgentShowingRespondView,
    AgentShowingAcceptView,
    AgentShowingRejectView,
    AgentCreateShowingView,
    AgentRescheduleShowingView,
    AgentShowingAgreementDetailView,
    # Agreement views
    AgentAgreementListView,
    AgentAgreementDetailView,
    # Legal Documents views
    agent_get_privacy_policy,
    agent_get_terms_conditions,
)

app_name = 'agent'

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    # Profile endpoints
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('user/', UserDetailView.as_view(), name='user_detail'),
    
    # Selling Request Management endpoints
    path('selling-requests/', AgentSellingRequestListView.as_view(), name='selling_request_list'),
    path('selling-requests/<int:pk>/', AgentSellingRequestDetailView.as_view(), name='selling_request_detail'),
    path('selling-requests/<int:pk>/status/', AgentSellingRequestStatusUpdateView.as_view(), name='update_selling_request_status'),
    path('selling-requests/stats/', AgentSellingRequestStatsView.as_view(), name='selling_request_stats'),
    
    # Agent Notification endpoints
    path('notifications/', AgentNotificationListView.as_view(), name='notification_list'),
    path('notifications/<int:pk>/', AgentNotificationDetailView.as_view(), name='notification_detail'),
    path('notifications/unread-count/', AgentNotificationUnreadCountView.as_view(), name='notification_unread_count'),
    path('notifications/mark-all-read/', AgentNotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
    
    # Agent CMA Management endpoints
    path('selling-requests/<int:selling_request_id>/cma/upload/', AgentCMAUploadView.as_view(), name='cma_upload'),
    path('selling-requests/<int:selling_request_id>/cma/', AgentCMAListView.as_view(), name='cma_list'),
    
    # Agent Property Document Management endpoints
    path('selling-requests/<int:selling_request_id>/documents/', AgentPropertyDocumentListView.as_view(), name='property_document_list'),
    path('documents/<int:pk>/', AgentPropertyDocumentDetailView.as_view(), name='property_document_detail'),
    
    # Agent Selling Agreement Management endpoints
    path('property-documents/<int:pk>/selling-agreement/upload/', AgentSellingAgreementUploadView.as_view(), name='selling_agreement_upload'),
    
    # Agent Agreement List and Detail endpoints (View agreements with status)
    path('agreements/', AgentAgreementListView.as_view(), name='agent_agreement_list'),
    path('agreements/<int:pk>/', AgentAgreementDetailView.as_view(), name='agent_agreement_detail'),
    
    # =========================================================================
    # Property Listing endpoint (only after seller accepts agreement)
    # =========================================================================
    path('listings/', AgentListingsView.as_view(), name='agent_listings_list'),
    path('agreements/<int:agreement_id>/create-listing/', AgentCreateListingView.as_view(), name='create_listing'),
    path('agreements/<int:agreement_id>/listing/photos/', AgentListingPhotoUploadView.as_view(), name='listing_photo_upload'),
    path('agreements/<int:agreement_id>/listing/documents/', AgentListingDocumentUploadView.as_view(), name='listing_document_upload'),
    
    # =========================================================================
    # Showing Schedule Management endpoints
    # =========================================================================
    path('showings/', AgentShowingScheduleListView.as_view(), name='showing_list'),
    path('showings/create/', AgentCreateShowingView.as_view(), name='showing_create'),
    path('showings/<int:schedule_id>/', AgentShowingScheduleDetailView.as_view(), name='showing_detail'),
    path('showings/<int:schedule_id>/respond/', AgentShowingRespondView.as_view(), name='showing_respond'),
    path('showings/<int:schedule_id>/accept/', AgentShowingAcceptView.as_view(), name='showing_accept'),
    path('showings/<int:schedule_id>/reject/', AgentShowingRejectView.as_view(), name='showing_reject'),
    path('showings/<int:schedule_id>/reschedule/', AgentRescheduleShowingView.as_view(), name='showing_reschedule'),
    path('showings/<int:schedule_id>/agreement/', AgentShowingAgreementDetailView.as_view(), name='showing_agreement_detail'),
    
    # =========================================================================
    # Legal Documents (GET only)
    # =========================================================================
    path('privacy-policy/', agent_get_privacy_policy, name='get_privacy_policy'),
    path('terms-conditions/', agent_get_terms_conditions, name='get_terms_conditions'),
]
