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
    AgentListView,
    SellingRequestListCreateView,
    SellingRequestDetailView,
    SellerNotificationListView,
    SellerNotificationDetailView,
    SellerNotificationUnreadCountView,
    SellerNotificationMarkAllReadView,
    PropertyDocumentUploadView,
    PropertyDocumentListView,
    PropertyDocumentDetailView,
    SellerCMAListView,
    SellerCMADetailView,
    CMAAcceptView,
    CMARejectView,
    SellerAgreementListView,
    SellerAgreementDetailView,
    AgreementAcceptView,
    AgreementRejectView,
    # Legal Documents views
    seller_get_privacy_policy,
    seller_get_terms_conditions,
    seller_agreement_documents,
)

app_name = 'seller'

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
    
    # Selling Request endpoints
    path('selling-requests/', SellingRequestListCreateView.as_view(), name='selling_request_list'),
    path('selling-requests/<int:pk>/', SellingRequestDetailView.as_view(), name='selling_request_detail'),
    
    # Agent endpoints
    path('agents/', AgentListView.as_view(), name='agent_list'),
    
    # Notification endpoints
    path('notifications/', SellerNotificationListView.as_view(), name='notification_list'),
    path('notifications/<int:pk>/', SellerNotificationDetailView.as_view(), name='notification_detail'),
    path('notifications/unread-count/', SellerNotificationUnreadCountView.as_view(), name='notification_unread_count'),
    path('notifications/mark-all-read/', SellerNotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
    
    # Property Document endpoints
    path('selling-requests/<int:selling_request_id>/documents/upload/', PropertyDocumentUploadView.as_view(), name='document_upload'),
    path('selling-requests/<int:selling_request_id>/documents/', PropertyDocumentListView.as_view(), name='document_list'),
    path('documents/<int:pk>/', PropertyDocumentDetailView.as_view(), name='document_detail'),
    
    # CMA endpoints
    path('cma/', SellerCMAListView.as_view(), name='cma_list'),
    path('cma/<int:pk>/', SellerCMADetailView.as_view(), name='cma_detail'),
    path('cma/<int:pk>/accept/', CMAAcceptView.as_view(), name='cma_accept'),
    path('cma/<int:pk>/reject/', CMARejectView.as_view(), name='cma_reject'),
    
    # Selling Agreement endpoints
    path('agreements/', SellerAgreementListView.as_view(), name='agreement_list'),
    path('agreements/<int:pk>/', SellerAgreementDetailView.as_view(), name='agreement_detail'),
    path('agreements/<int:pk>/accept/', AgreementAcceptView.as_view(), name='agreement_accept'),
    path('agreements/<int:pk>/reject/', AgreementRejectView.as_view(), name='agreement_reject'),
    
    # Legal Documents (GET only)
    path('privacy-policy/', seller_get_privacy_policy, name='get_privacy_policy'),
    path('terms-conditions/', seller_get_terms_conditions, name='get_terms_conditions'),
    path('agreements/documents/', seller_agreement_documents, name='seller_agreements'),
]

