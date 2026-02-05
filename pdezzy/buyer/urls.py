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
    # MLS Listing Views
    MLSListingsView,
    MLSListingDetailView,
    MLSListingSearchView,
    MLSFeaturedListingsView,
    MLSNearbyListingsView,
    # Agent Listings View
    BuyerAgentListingsView,
    BuyerAgentListingDetailView,
    # Showing Schedule Views
    ShowingScheduleCreateView,
    ShowingScheduleListView,
    ShowingScheduleDetailView,
    BuyerRescheduleShowingView,
    # Notification Views
    BuyerNotificationListView,
    BuyerNotificationDetailView,
    # Showing Agreement Views
    ShowingAgreementSignView,
    ShowingAgreementDetailView,
    # Agreement Views
    BuyerAgreementListView,
    BuyerAgreementDetailView,
    BuyerAgreementDownloadView,
    # Saved Listings Views
    SavedListingCreateView,
    SavedListingListView,
    SavedListingDeleteView,
    # Legal Documents views
    buyer_get_privacy_policy,
    buyer_get_terms_conditions,
    buyer_agreement_documents,
)

app_name = 'buyer'

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
    
    # User endpoints
    path('user/', UserDetailView.as_view(), name='user_detail'),
    
    # MLS Listings endpoints
    path('listings/', MLSListingsView.as_view(), name='mls_listings'),
    path('listings/search/', MLSListingSearchView.as_view(), name='mls_listing_search'),
    path('listings/featured/', MLSFeaturedListingsView.as_view(), name='mls_featured_listings'),
    path('listings/nearby/', MLSNearbyListingsView.as_view(), name='mls_nearby_listings'),
    path('listings/<str:mls_number>/', MLSListingDetailView.as_view(), name='mls_listing_detail'),
    
    # Agent Created Listings endpoints
    path('agent-listings/', BuyerAgentListingsView.as_view(), name='agent_listings'),
    path('agent-listings/<int:listing_id>/', BuyerAgentListingDetailView.as_view(), name='agent_listing_detail'),
    
    # Showing Schedule endpoints
    path('showings/', ShowingScheduleListView.as_view(), name='showing_list'),
    path('showings/create/', ShowingScheduleCreateView.as_view(), name='showing_create'),
    path('showings/<int:schedule_id>/', ShowingScheduleDetailView.as_view(), name='showing_detail'),
    path('showings/<int:schedule_id>/reschedule/', BuyerRescheduleShowingView.as_view(), name='showing_reschedule'),
    path('showings/<int:schedule_id>/sign-agreement/', ShowingAgreementSignView.as_view(), name='showing_sign_agreement'),
    path('showings/<int:schedule_id>/agreement/', ShowingAgreementDetailView.as_view(), name='showing_agreement_detail'),
    
    # Notification endpoints
    path('notifications/', BuyerNotificationListView.as_view(), name='notifications'),
    path('notifications/<int:notification_id>/read/', BuyerNotificationDetailView.as_view(), name='notification_read'),
    
    # Saved Listings endpoints
    path('saved-listings/', SavedListingListView.as_view(), name='saved_listing_list'),
    path('saved-listings/add/', SavedListingCreateView.as_view(), name='saved_listing_create'),
    path('saved-listings/<int:saved_listing_id>/', SavedListingDeleteView.as_view(), name='saved_listing_delete'),
    
    # Buyer Agreements endpoints
    path('agreements/', BuyerAgreementListView.as_view(), name='buyer_agreements_list'),
    path('agreements/<int:agreement_id>/', BuyerAgreementDetailView.as_view(), name='buyer_agreement_detail'),
    path('agreements/<int:agreement_id>/download/<str:filename>', BuyerAgreementDownloadView.as_view(), name='buyer_agreement_download_with_filename'),
    path('agreements/<int:agreement_id>/download/', BuyerAgreementDownloadView.as_view(), name='buyer_agreement_download'),
    
    # Legal Documents (GET only)
    path('privacy-policy/', buyer_get_privacy_policy, name='get_privacy_policy'),
    path('terms-conditions/', buyer_get_terms_conditions, name='get_terms_conditions'),
    path('agreements-documents/', buyer_agreement_documents, name='buyer_agreements_documents'),
]

