from rest_framework import status, views, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import models
from .models import PasswordResetToken
from .serializers import ForgotPasswordSerializer, VerifyOTPSerializer, ResetPasswordSerializer
from .utils import send_otp_email, send_password_reset_confirmation


class ForgotPasswordView(views.APIView):
    """
    Request password reset by sending OTP to email
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Request password reset by sending OTP to email",
        request_body=ForgotPasswordSerializer,
        responses={
            200: openapi.Response(
                description="OTP sent",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message')
                    }
                )
            ),
            400: "Bad Request - Validation errors",
            500: "Internal Server Error - Failed to send email"
        }
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user_type = serializer.user_type  # Get user type from serializer

            # Create OTP token
            token = PasswordResetToken.create_otp_token(email, user_type)

            # Send OTP via email
            email_sent = send_otp_email(email, token.otp, user_type)

            if email_sent:
                return Response(
                    {"message": "OTP sent to your email address."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Failed to send email. Please try again later."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(views.APIView):
    """
    Verify OTP sent to email
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Verify OTP sent to email",
        request_body=VerifyOTPSerializer,
        responses={
            200: openapi.Response(
                description="OTP verified",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message')
                    }
                )
            ),
            400: "Bad Request - Invalid or expired OTP"
        }
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                {"message": "OTP verified successfully. You can now reset your password."},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(views.APIView):
    """
    Reset password using OTP
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Reset password using verified OTP",
        request_body=ResetPasswordSerializer,
        responses={
            200: openapi.Response(
                description="Password reset",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message')
                    }
                )
            ),
            400: "Bad Request - Invalid OTP or validation errors"
        }
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_type = serializer.validated_data['user_type']
            email = serializer.validated_data['email']

            # Send confirmation email
            send_password_reset_confirmation(email, user_type)

            return Response(
                {"message": "Password reset successfully. You can now login with your new password."},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# Legal Documents Views
# =============================================================================

class LegalDocumentListView(generics.ListAPIView):
    """
    Get all active legal documents for the current user type.
    Available to all authenticated users (agent, seller, buyer)
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get all active legal documents for current user",
        responses={
            200: "List of legal documents",
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        from .models import LegalDocument
        from .serializers import LegalDocumentSerializer
        
        # Determine user type
        user_type = None
        if hasattr(request.user, 'agent'):
            user_type = 'agent'
        elif hasattr(request.user, 'seller'):
            user_type = 'seller'
        elif hasattr(request.user, 'buyer'):
            user_type = 'buyer'
        
        # Get documents for this user type (privacy_policy and terms_conditions)
        documents = LegalDocument.objects.filter(
            is_active=True,
            user_type=user_type
        ).order_by('document_type')
        
        serializer = LegalDocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LegalDocumentDetailView(generics.RetrieveAPIView):
    """
    Get specific legal document by type.
    Available to all authenticated users
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get specific legal document by type",
        manual_parameters=[
            openapi.Parameter(
                'document_type',
                openapi.IN_PATH,
                description="Document type (agent_privacy_policy, agent_terms_conditions, seller_privacy_policy, seller_terms_conditions, buyer_privacy_policy, buyer_terms_conditions)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: "Legal document details",
            401: "Unauthorized",
            404: "Document not found"
        }
    )
    def get(self, request, document_type, *args, **kwargs):
        from .models import LegalDocument
        from .serializers import LegalDocumentSerializer
        
        # Determine user type
        user_type = None
        if hasattr(request.user, 'agent'):
            user_type = 'agent'
        elif hasattr(request.user, 'seller'):
            user_type = 'seller'
        elif hasattr(request.user, 'buyer'):
            user_type = 'buyer'
        
        # Verify the document_type matches the user_type
        if not document_type.startswith(f"{user_type}_"):
            return Response(
                {"error": "You don't have permission to access this document"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get the active document for this specific type
            document = LegalDocument.objects.filter(
                document_type=document_type,
                is_active=True
            ).first()
            
            if not document:
                return Response(
                    {"error": "Document not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = LegalDocumentSerializer(document)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# =============================================================================
# Admin Legal Documents Management Views
# =============================================================================

class AdminLegalDocumentListCreateView(generics.ListCreateAPIView):
    """
    Admin endpoint to list all legal documents and create new ones
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        operation_description="Get all legal documents (admin only)",
        responses={
            200: "List of all legal documents",
            401: "Unauthorized",
            403: "Forbidden - Admin only"
        }
    )
    def get(self, request, *args, **kwargs):
        from .models import LegalDocument
        from .serializers import LegalDocumentSerializer
        
        documents = LegalDocument.objects.all().order_by('-created_at')
        serializer = LegalDocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Create new legal document (admin only)",
        responses={
            201: "Document created successfully",
            400: "Bad Request - Validation errors",
            401: "Unauthorized",
            403: "Forbidden - Admin only"
        }
    )
    def post(self, request, *args, **kwargs):
        from .models import LegalDocument
        from .serializers import LegalDocumentCreateUpdateSerializer, LegalDocumentSerializer
        
        serializer = LegalDocumentCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            document = serializer.save(created_by=request.user)
            response_serializer = LegalDocumentSerializer(document)
            return Response(
                {
                    "message": "Legal document created successfully",
                    "data": response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminLegalDocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin endpoint to retrieve, update, or delete a legal document
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @swagger_auto_schema(
        operation_description="Get legal document details (admin only)",
        responses={
            200: "Document details",
            401: "Unauthorized",
            403: "Forbidden - Admin only",
            404: "Document not found"
        }
    )
    def get(self, request, pk, *args, **kwargs):
        from .models import LegalDocument
        from .serializers import LegalDocumentSerializer
        
        try:
            document = LegalDocument.objects.get(pk=pk)
            serializer = LegalDocumentSerializer(document)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LegalDocument.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_description="Update legal document (admin only)",
        responses={
            200: "Document updated successfully",
            400: "Bad Request - Validation errors",
            401: "Unauthorized",
            403: "Forbidden - Admin only",
            404: "Document not found"
        }
    )
    def put(self, request, pk, *args, **kwargs):
        from .models import LegalDocument
        from .serializers import LegalDocumentCreateUpdateSerializer, LegalDocumentSerializer
        
        try:
            document = LegalDocument.objects.get(pk=pk)
            serializer = LegalDocumentCreateUpdateSerializer(document, data=request.data)
            if serializer.is_valid():
                document = serializer.save()
                response_serializer = LegalDocumentSerializer(document)
                return Response(
                    {
                        "message": "Legal document updated successfully",
                        "data": response_serializer.data
                    },
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except LegalDocument.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_description="Partially update legal document (admin only)",
        responses={
            200: "Document updated successfully",
            400: "Bad Request - Validation errors",
            401: "Unauthorized",
            403: "Forbidden - Admin only",
            404: "Document not found"
        }
    )
    def patch(self, request, pk, *args, **kwargs):
        from .models import LegalDocument
        from .serializers import LegalDocumentCreateUpdateSerializer, LegalDocumentSerializer
        
        try:
            document = LegalDocument.objects.get(pk=pk)
            serializer = LegalDocumentCreateUpdateSerializer(
                document, 
                data=request.data, 
                partial=True
            )
            if serializer.is_valid():
                document = serializer.save()
                response_serializer = LegalDocumentSerializer(document)
                return Response(
                    {
                        "message": "Legal document updated successfully",
                        "data": response_serializer.data
                    },
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except LegalDocument.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @swagger_auto_schema(
        operation_description="Delete legal document (admin only)",
        responses={
            204: "Document deleted successfully",
            401: "Unauthorized",
            403: "Forbidden - Admin only",
            404: "Document not found"
        }
    )
    def delete(self, request, pk, *args, **kwargs):
        from .models import LegalDocument
        
        try:
            document = LegalDocument.objects.get(pk=pk)
            document.delete()
            return Response(
                {"message": "Legal document deleted successfully"},
                status=status.HTTP_204_NO_CONTENT
            )
        except LegalDocument.DoesNotExist:
            return Response(
                {"error": "Document not found"},
                status=status.HTTP_404_NOT_FOUND
            )
