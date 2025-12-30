from django.urls import path
from .views import (
    ForgotPasswordView, VerifyOTPView, ResetPasswordView,
    LegalDocumentListView, LegalDocumentDetailView,
    AdminLegalDocumentListCreateView, AdminLegalDocumentDetailView
)

app_name = 'common'

urlpatterns = [
    # Password Reset
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    
    # Legal Documents (for all authenticated users)
    path('legal-documents/', LegalDocumentListView.as_view(), name='legal_documents_list'),
    path('legal-documents/<str:document_type>/', LegalDocumentDetailView.as_view(), name='legal_document_detail'),
    
    # Admin Legal Documents Management
    path('admin/legal-documents/', AdminLegalDocumentListCreateView.as_view(), name='admin_legal_documents'),
    path('admin/legal-documents/<int:pk>/', AdminLegalDocumentDetailView.as_view(), name='admin_legal_document_detail'),
]

