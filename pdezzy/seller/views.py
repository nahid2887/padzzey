from rest_framework import viewsets, status, views, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from pdezzy.permissions import IsSeller
from .models import Seller, SellingRequest, SellerNotification, PropertyDocument, DocumentFile, AgentNotification
from agent.models import Agent

from .serializers import (
    UserSerializer,
    RegisterSerializer,
    RegisterRequestSerializer,
    RegisterResponseSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
    CustomTokenObtainPairSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
    SellingRequestSerializer,
    SellingRequestCreateSerializer,
    SellingRequestUpdateSerializer,
    SellingRequestStatusSerializer,
    SellerNotificationSerializer,
    SellerNotificationUpdateSerializer,
    PropertyDocumentSerializer,
    PropertyDocumentUploadSerializer,
    PropertyDocumentUploadResponseSerializer,
    CMADetailedSerializer,
    CMAStatusUpdateSerializer,
    SellingAgreementDetailedSerializer,
    AgreementStatusUpdateSerializer,
    AgentListSerializer,
)

User = Seller


class RegisterView(generics.CreateAPIView):
    """
    Register a new seller account.
    Returns access and refresh tokens upon successful registration.
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @swagger_auto_schema(
        operation_description="Register a new seller account",
        request_body=RegisterSerializer,
        responses={
            201: RegisterSerializer,
            400: "Bad Request - Validation errors"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class LoginView(views.APIView):
    """
    Seller login endpoint.
    Returns access and refresh tokens along with user information.
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @swagger_auto_schema(
        operation_description="Login with email and password to get access token",
        request_body=LoginSerializer,
        responses={
            200: LoginSerializer,
            400: "Bad Request - Invalid credentials"
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain pair view with user information.
    """
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(
        operation_description="Obtain JWT token pair (access and refresh)",
        responses={
            200: openapi.Response("Token pair", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'access': openapi.Schema(type=openapi.TYPE_STRING, description='Access token'),
                    'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token'),
                }
            )),
            401: "Unauthorized - Invalid credentials"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RefreshTokenView(TokenRefreshView):
    """
    Refresh access token using refresh token.
    """
    @swagger_auto_schema(
        operation_description="Refresh access token using refresh token",
        responses={
            200: openapi.Response("New access token", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'access': openapi.Schema(type=openapi.TYPE_STRING, description='New access token'),
                }
            )),
            401: "Unauthorized - Invalid refresh token"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LogoutView(views.APIView):
    """
    Logout endpoint to invalidate the refresh token.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Logout and invalidate refresh token",
        request_body=LogoutSerializer,
        responses={
            200: openapi.Response("Success", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                }
            )),
            400: "Bad Request - Invalid token",
            401: "Unauthorized"
        }
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            try:
                refresh_token = serializer.validated_data['refresh']
                token = RefreshToken(refresh_token)
                token.blacklist()
                
                return Response(
                    {"message": "Successfully logged out."},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(views.APIView):
    """
    Get current seller profile.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get current seller profile",
        responses={
            200: UserSerializer,
            401: "Unauthorized"
        }
    )
    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProfileUpdateView(generics.UpdateAPIView):
    """
    Update current seller profile.
    Only sellers can update their own profile.
    Supports multipart/form-data for file uploads (profile image).
    """
    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated, IsSeller]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_object(self):
        """Return the current authenticated user"""
        return self.request.user

    @swagger_auto_schema(
        operation_description="Update current seller profile (multipart/form-data for file uploads)",
        request_body=ProfileUpdateSerializer,
        responses={
            200: UserSerializer,
            400: "Bad Request - Validation errors",
            401: "Unauthorized"
        }
    )
    def put(self, request, *args, **kwargs):
        """Update seller profile"""
        response = super().update(request, *args, **kwargs)
        # Return using UserSerializer for complete user data
        return Response(UserSerializer(self.request.user, context={'request': request}).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Partially update current seller profile (multipart/form-data for file uploads)",
        request_body=ProfileUpdateSerializer,
        responses={
            200: UserSerializer,
            400: "Bad Request - Validation errors",
            401: "Unauthorized"
        }
    )
    def patch(self, request, *args, **kwargs):
        """Partially update seller profile"""
        response = super().partial_update(request, *args, **kwargs)
        # Return using UserSerializer for complete user data
        return Response(UserSerializer(self.request.user, context={'request': request}).data, status=status.HTTP_200_OK)


class ChangePasswordView(views.APIView):
    """
    Change current seller's password.
    Only sellers can change their own password.
    """
    permission_classes = [IsAuthenticated, IsSeller]

    @swagger_auto_schema(
        operation_description="Change current seller password",
        request_body=ChangePasswordSerializer,
        responses={
            200: openapi.Response("Success", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
                }
            )),
            400: "Bad Request - Validation errors",
            401: "Unauthorized"
        }
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Password changed successfully."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a seller instance.
    Only sellers can access their own details.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsSeller]

    def get_object(self):
        return self.request.user

    @swagger_auto_schema(
        operation_description="Retrieve the authenticated seller's user details",
        responses={
            200: UserSerializer,
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update the authenticated seller's user details",
        request_body=UserSerializer,
        responses={
            200: UserSerializer,
            400: "Bad Request - Validation errors",
            401: "Unauthorized"
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete the authenticated seller's account",
        responses={
            204: "No Content - Successfully deleted",
            401: "Unauthorized"
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class AgentListView(generics.ListAPIView):
    """
    List all available agents.
    Only authenticated sellers can access this endpoint.
    """
    queryset = Agent.objects.all()
    serializer_class = AgentListSerializer
    permission_classes = [IsAuthenticated, IsSeller]

    @swagger_auto_schema(
        operation_description="List all available agents",
        responses={
            200: AgentListSerializer(many=True),
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SellingRequestListCreateView(generics.ListCreateAPIView):
    """
    List all selling requests for the authenticated seller and create new ones.
    Only authenticated sellers can access this endpoint.
    """
    serializer_class = SellingRequestSerializer
    permission_classes = [IsAuthenticated, IsSeller]

    def get_queryset(self):
        """Return only selling requests for the authenticated seller"""
        if getattr(self, 'swagger_fake_view', False):
            return SellingRequest.objects.none()
        return SellingRequest.objects.filter(seller=self.request.user)

    def perform_create(self, serializer):
        """Create a new selling request for the authenticated seller"""
        serializer.save(seller=self.request.user)

    @swagger_auto_schema(
        operation_description="List all selling requests for the authenticated seller",
        responses={
            200: SellingRequestSerializer(many=True),
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new selling request",
        request_body=SellingRequestCreateSerializer,
        responses={
            201: SellingRequestSerializer,
            400: "Bad Request - Validation errors",
            401: "Unauthorized"
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = SellingRequestCreateSerializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(
                SellingRequestSerializer(serializer.instance, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SellingRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a specific selling request.
    Only the seller who created the request can access it.
    """
    serializer_class = SellingRequestSerializer
    permission_classes = [IsAuthenticated, IsSeller]

    def get_queryset(self):
        """Return only selling requests for the authenticated seller"""
        if getattr(self, 'swagger_fake_view', False):
            return SellingRequest.objects.none()
        return SellingRequest.objects.filter(seller=self.request.user)

    @swagger_auto_schema(
        operation_description="Retrieve a specific selling request",
        responses={
            200: SellingRequestSerializer,
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a specific selling request (only pending requests)",
        request_body=SellingRequestUpdateSerializer,
        responses={
            200: SellingRequestSerializer,
            400: "Bad Request - Request not pending or validation errors",
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def put(self, request, *args, **kwargs):
        selling_request = self.get_object()
        if selling_request.status != 'pending':
            return Response(
                {"error": "Can only update selling requests with 'pending' status."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = SellingRequestUpdateSerializer(
            selling_request,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                SellingRequestSerializer(selling_request, context={'request': request}).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Partially update a specific selling request (only pending requests)",
        request_body=SellingRequestUpdateSerializer,
        responses={
            200: SellingRequestSerializer,
            400: "Bad Request - Request not pending or validation errors",
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def patch(self, request, *args, **kwargs):
        return self.put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete a specific selling request (only pending requests)",
        responses={
            204: "No Content - Successfully deleted",
            400: "Bad Request - Request not pending",
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def delete(self, request, *args, **kwargs):
        selling_request = self.get_object()
        if selling_request.status != 'pending':
            return Response(
                {"error": "Can only delete selling requests with 'pending' status."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().delete(request, *args, **kwargs)


class SellerNotificationListView(generics.ListAPIView):
    """
    List all notifications for the authenticated seller.
    Ordered by most recent first.
    """
    serializer_class = SellerNotificationSerializer
    permission_classes = [IsAuthenticated, IsSeller]

    def get_queryset(self):
        """Return only notifications for the authenticated seller"""
        if getattr(self, 'swagger_fake_view', False):
            return SellerNotification.objects.none()
        return SellerNotification.objects.filter(seller=self.request.user)

    @swagger_auto_schema(
        operation_description="List all notifications for the authenticated seller",
        responses={
            200: SellerNotificationSerializer(many=True),
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SellerNotificationDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update a specific notification.
    Only the seller who owns the notification can access it.
    """
    serializer_class = SellerNotificationSerializer
    permission_classes = [IsAuthenticated, IsSeller]

    def get_queryset(self):
        """Return only notifications for the authenticated seller"""
        if getattr(self, 'swagger_fake_view', False):
            return SellerNotification.objects.none()
        return SellerNotification.objects.filter(seller=self.request.user)

    @swagger_auto_schema(
        operation_description="Retrieve a specific seller notification",
        responses={
            200: SellerNotificationSerializer,
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a specific seller notification (e.g., mark as read)",
        request_body=SellerNotificationUpdateSerializer,
        responses={
            200: SellerNotificationSerializer,
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def patch(self, request, *args, **kwargs):
        notification = self.get_object()
        serializer = SellerNotificationUpdateSerializer(
            notification,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                SellerNotificationSerializer(notification).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SellerNotificationUnreadCountView(views.APIView):
    """
    Get count of unread notifications for the authenticated seller.
    """
    permission_classes = [IsAuthenticated, IsSeller]

    @swagger_auto_schema(
        operation_description="Get count of unread seller notifications",
        responses={
            200: openapi.Response(
                description="Unread count",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'unread_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of unread notifications')
                    }
                )
            ),
            401: "Unauthorized"
        }
    )
    def get(self, request):
        unread_count = SellerNotification.objects.filter(
            seller=request.user,
            is_read=False
        ).count()
        return Response(
            {"unread_count": unread_count},
            status=status.HTTP_200_OK
        )


class SellerNotificationMarkAllReadView(views.APIView):
    """
    Mark all notifications as read for the authenticated seller.
    """
    permission_classes = [IsAuthenticated, IsSeller]

    @swagger_auto_schema(
        operation_description="Mark all seller notifications as read",
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'updated_count': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            401: "Unauthorized"
        }
    )
    def post(self, request):
        updated_count = SellerNotification.objects.filter(
            seller=request.user,
            is_read=False
        ).update(is_read=True)
        return Response(
            {
                "message": f"Marked {updated_count} notification(s) as read.",
                "updated_count": updated_count
            },
            status=status.HTTP_200_OK
        )


class PropertyDocumentUploadView(views.APIView):
    """
    Upload multiple CMA or property documents to an approved selling request.
    Only sellers can upload documents to their approved selling requests.
    Triggers agent notification when documents are uploaded.
    """
    permission_classes = [IsAuthenticated, IsSeller]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_description="Upload multiple property documents to an approved selling request",
        manual_parameters=[
            openapi.Parameter(
                'document_type',
                openapi.IN_FORM,
                description="Type of document (inspection, appraisal, other)",
                type=openapi.TYPE_STRING,
                enum=['inspection', 'appraisal', 'other'],
                default='other'
            ),
            openapi.Parameter(
                'title',
                openapi.IN_FORM,
                description="Title for the documents",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'files',
                openapi.IN_FORM,
                description="Multiple files to upload (PDF, JPG, JPEG, PNG)",
                type=openapi.TYPE_FILE,
                required=True
            ),
            openapi.Parameter(
                'description',
                openapi.IN_FORM,
                description="Optional description for the documents",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            201: openapi.Response(
                description="Documents uploaded successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'document': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'document_type': openapi.Schema(type=openapi.TYPE_STRING),
                                'title': openapi.Schema(type=openapi.TYPE_STRING),
                                'description': openapi.Schema(type=openapi.TYPE_STRING),
                                'files': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'file': openapi.Schema(type=openapi.TYPE_STRING),
                                            'file_url': openapi.Schema(type=openapi.TYPE_STRING),
                                            'original_filename': openapi.Schema(type=openapi.TYPE_STRING),
                                            'file_extension': openapi.Schema(type=openapi.TYPE_STRING),
                                            'file_size_mb': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time')
                                        }
                                    )
                                ),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time')
                            }
                        )
                    }
                )
            ),
            400: "Bad Request - Validation errors or request not accepted",
            401: "Unauthorized",
            403: "Forbidden - Not your selling request",
            404: "Not Found - Selling request not found"
        }
    )
    def post(self, request, selling_request_id, *args, **kwargs):
        """Upload multiple documents to a selling request"""
        try:
            selling_request = SellingRequest.objects.get(pk=selling_request_id)
        except SellingRequest.DoesNotExist:
            return Response(
                {"error": "Selling request not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if selling_request.seller != request.user:
            return Response(
                {"error": "You can only upload documents for your own selling requests"},
                status=status.HTTP_403_FORBIDDEN
            )

        if selling_request.status != 'accepted':
            return Response(
                {"error": "Can only upload documents for approved selling requests"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PropertyDocumentUploadSerializer(
            data=request.data,
            context={'request': request, 'selling_request_id': selling_request_id}
        )
        if serializer.is_valid():
            # Create a single property document
            document = PropertyDocument.objects.create(
                selling_request=selling_request,
                seller=request.user,
                document_type=serializer.validated_data['document_type'],
                title=serializer.validated_data['title'],
                description=serializer.validated_data.get('description', '')
            )

            # Create DocumentFile instances for each uploaded file
            uploaded_files = []
            files = serializer.validated_data['files']

            for file in files:
                document_file = DocumentFile.objects.create(
                    property_document=document,
                    file=file,
                    file_size=file.size,
                    original_filename=file.name
                )
                uploaded_files.append(document_file)

            # Create notification only for the assigned agent if one exists
            if selling_request.agent and uploaded_files:
                file_count = len(uploaded_files)
                file_names = [doc_file.original_filename for doc_file in uploaded_files[:3]]  # Show first 3 filenames
                if file_count > 3:
                    file_names.append(f"and {file_count - 3} more")

                AgentNotification.objects.create(
                    agent=selling_request.agent,
                    notification_type='document_uploaded',
                    selling_request=selling_request,
                    property_document=document,
                    title=f"Documents Uploaded - {selling_request.seller.get_full_name()}",
                    message=f"Seller {selling_request.seller.get_full_name()} uploaded {file_count} new document(s) '{', '.join(file_names)}' for their property selling request.",
                    action_url=f"/api/v1/agent/selling-requests/{selling_request.id}/documents/",
                    action_text="View Documents",
                    is_read=False
                )

            # Serialize the document with files
            response_serializer = PropertyDocumentUploadResponseSerializer(document, context={'request': request})

            return Response({
                "message": f"Successfully uploaded {len(uploaded_files)} document(s)",
                "document": response_serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PropertyDocumentListView(generics.ListAPIView):
    """
    List all property documents for a specific selling request.
    Only the seller who owns the selling request can access documents.
    """
    serializer_class = PropertyDocumentSerializer
    permission_classes = [IsAuthenticated, IsSeller]

    def get_queryset(self):
        """Return documents for the selling request"""
        if getattr(self, 'swagger_fake_view', False):
            return PropertyDocument.objects.none()
        selling_request_id = self.kwargs.get('selling_request_id')
        try:
            selling_request = SellingRequest.objects.get(pk=selling_request_id)
        except SellingRequest.DoesNotExist:
            return PropertyDocument.objects.none()

        if selling_request.seller != self.request.user:
            return PropertyDocument.objects.none()

        return PropertyDocument.objects.filter(selling_request=selling_request)

    @swagger_auto_schema(
        operation_description="List all property documents for a specific selling request",
        responses={
            200: PropertyDocumentSerializer(many=True),
            401: "Unauthorized",
            404: "Not Found - Selling request not found or not yours"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SellerCMAListView(generics.ListAPIView):
    """
    List all CMA reports uploaded by agent for the authenticated seller's selling requests.
    Displays CMA details with selling request information.
    Only shows CMAs for the authenticated seller's properties.
    """
    serializer_class = CMADetailedSerializer
    permission_classes = [IsAuthenticated, IsSeller]

    def get_queryset(self):
        """Return only CMA documents for authenticated seller's selling requests"""
        if getattr(self, 'swagger_fake_view', False):
            return PropertyDocument.objects.none()
        return PropertyDocument.objects.filter(
            seller=self.request.user,
            document_type='cma'
        ).select_related('selling_request', 'seller').order_by('-created_at')

    @swagger_auto_schema(
        operation_description="List all CMA reports for the authenticated seller",
        operation_summary="Get CMA Reports List",
        tags=['Seller - CMA'],
        responses={
            200: openapi.Response(
                description="List of CMA reports with pagination",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of CMA reports'),
                        'next': openapi.Schema(type=openapi.TYPE_STRING, description='URL for next page', nullable=True),
                        'previous': openapi.Schema(type=openapi.TYPE_STRING, description='URL for previous page', nullable=True),
                        'results': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT),
                            description='Array of CMA report objects'
                        )
                    }
                )
            ),
            401: openapi.Response(description='Unauthorized - Authentication required'),
            403: openapi.Response(description='Forbidden - Only sellers can access this endpoint')
        }
    )
    def get(self, request, *args, **kwargs):
        """Get list of all CMA reports for the authenticated seller"""
        return super().get(request, *args, **kwargs)


class SellerCMADetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific CMA document for the authenticated seller.
    Only the seller who owns the CMA can access it.
    Returns detailed CMA information with selling request details.
    """
    serializer_class = CMADetailedSerializer
    permission_classes = [IsAuthenticated, IsSeller]

    def get_queryset(self):
        """Return only CMA documents for the authenticated seller"""
        if getattr(self, 'swagger_fake_view', False):
            return PropertyDocument.objects.none()
        return PropertyDocument.objects.filter(
            seller=self.request.user,
            document_type='cma'
        ).select_related('selling_request', 'seller')

    @swagger_auto_schema(
        operation_description="Get detailed CMA report information for authenticated seller",
        operation_summary="Get CMA Report Detail",
        tags=['Seller - CMA'],
        responses={
            200: CMADetailedSerializer,
            401: openapi.Response(description='Unauthorized - Authentication required'),
            403: openapi.Response(description='Forbidden - CMA does not belong to you'),
            404: openapi.Response(description='Not Found - CMA not found')
        }
    )
    def get(self, request, *args, **kwargs):
        """Get detailed CMA report information"""
        return super().get(request, *args, **kwargs)


class PropertyDocumentDetailView(generics.RetrieveDestroyAPIView):
    """
    Retrieve or delete a specific property document.
    Only the seller who owns the document can access it.
    GET returns detailed CMA information with selling request details.
    DELETE removes both CMA and associated selling request (one-to-one relationship).
    """
    permission_classes = [IsAuthenticated, IsSeller]

    def get_serializer_class(self):
        """Use detailed serializer for GET, standard for other operations"""
        if self.request.method == 'GET':
            from .serializers import CMADetailedSerializer
            return CMADetailedSerializer
        return PropertyDocumentSerializer

    def get_queryset(self):
        """Return only documents for the authenticated seller"""
        if getattr(self, 'swagger_fake_view', False):
            return PropertyDocument.objects.none()
        return PropertyDocument.objects.filter(seller=self.request.user)

    @swagger_auto_schema(
        operation_description="Get detailed property document/CMA report information",
        responses={
            200: CMADetailedSerializer,
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def get(self, request, *args, **kwargs):
        """Get detailed CMA report information"""
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Delete property document and associated selling request",
        responses={
            204: "No Content - Successfully deleted",
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def delete(self, request, *args, **kwargs):
        """Delete CMA report and associated selling request"""
        document = self.get_object()
        selling_request = document.selling_request
        selling_request_id = selling_request.id
        document_id = document.id
        
        # Delete the selling request (which will cascade delete the document via on_delete=CASCADE)
        selling_request.delete()
        
        # For 204 No Content, we typically don't return a body, but we return empty Response
        return Response(status=status.HTTP_204_NO_CONTENT)


class CMAAcceptView(views.APIView):
    """
    Accept a CMA document.
    Only the seller who owns the CMA can accept it.
    Updates cma_status and cma_document_status to 'accepted'.
    """
    permission_classes = [IsAuthenticated, IsSeller]
    
    @swagger_auto_schema(
        operation_description="Accept a CMA document and update its status. This is a one-time operation - once accepted, it cannot be rejected.",
        responses={
            200: CMADetailedSerializer,
            400: "Bad Request - CMA already accepted or rejected",
            401: "Unauthorized",
            403: "Forbidden - Not your CMA document",
            404: "Not Found - CMA document not found"
        }
    )
    def post(self, request, pk):
        """Accept CMA document"""
        try:
            cma_document = PropertyDocument.objects.get(pk=pk, document_type='cma')
        except PropertyDocument.DoesNotExist:
            return Response(
                {"detail": "CMA document not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if the CMA belongs to the authenticated seller
        if cma_document.seller != request.user:
            return Response(
                {"detail": "You can only accept CMAs for your own selling requests."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already accepted or rejected (one-time operation)
        if cma_document.cma_status == 'accepted':
            return Response(
                {"detail": "This CMA has already been accepted."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if cma_document.cma_status == 'rejected':
            return Response(
                {"detail": "This CMA has been rejected and cannot be accepted."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cma_document.cma_status = 'accepted'
        cma_document.cma_document_status = 'accepted'
        cma_document.save()
        
        # No need to update notification - serializer handles dynamic display based on cma_status
        
        # Create notification for agent
        if cma_document.selling_request.agent:
            AgentNotification.objects.create(
                agent=cma_document.selling_request.agent,
                notification_type='cma_ready',
                selling_request=cma_document.selling_request,
                property_document=cma_document,
                title='CMA Report Accepted',
                message=f'Your CMA report "{cma_document.title}" for {cma_document.selling_request.seller.get_full_name()} has been accepted.',
                action_url=f'/agent/cma/{cma_document.id}/',
                action_text='View CMA'
            )
        
        serializer = CMADetailedSerializer(cma_document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CMARejectView(views.APIView):
    """
    Reject a CMA document.
    Only the seller who owns the CMA can reject it.
    Updates cma_status and cma_document_status to 'rejected'.
    """
    permission_classes = [IsAuthenticated, IsSeller]
    
    @swagger_auto_schema(
        operation_description="Reject a CMA document and update its status. This is a one-time operation - once rejected, it cannot be accepted.",
        responses={
            200: CMADetailedSerializer,
            400: "Bad Request - CMA already accepted or rejected",
            401: "Unauthorized",
            403: "Forbidden - Not your CMA document",
            404: "Not Found - CMA document not found"
        }
    )
    def post(self, request, pk):
        """Reject CMA document"""
        try:
            cma_document = PropertyDocument.objects.get(pk=pk, document_type='cma')
        except PropertyDocument.DoesNotExist:
            return Response(
                {"detail": "CMA document not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if the CMA belongs to the authenticated seller
        if cma_document.seller != request.user:
            return Response(
                {"detail": "You can only reject CMAs for your own selling requests."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already accepted or rejected (one-time operation)
        if cma_document.cma_status == 'rejected':
            return Response(
                {"detail": "This CMA has already been rejected."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if cma_document.cma_status == 'accepted':
            return Response(
                {"detail": "This CMA has been accepted and cannot be rejected."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cma_document.cma_status = 'rejected'
        cma_document.cma_document_status = 'rejected'
        cma_document.save()
        
        # No need to update notification - serializer handles dynamic display based on cma_status
        
        # Create notification for agent
        if cma_document.selling_request.agent:
            AgentNotification.objects.create(
                agent=cma_document.selling_request.agent,
                notification_type='cma_requested',
                selling_request=cma_document.selling_request,
                property_document=cma_document,
                title='CMA Report Rejected',
                message=f'Your CMA report "{cma_document.title}" for {cma_document.selling_request.seller.get_full_name()} has been rejected. Please review and resubmit.',
                action_url=f'/agent/cma/{cma_document.id}/',
                action_text='View CMA'
            )
        
        serializer = CMADetailedSerializer(cma_document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SellerAgreementListView(generics.ListAPIView):
    """
    List all selling agreements uploaded by agent for the authenticated seller's selling requests.
    Displays agreement details with selling request information.
    Only shows agreements for the authenticated seller's properties that have a selling_agreement_file.
    """
    serializer_class = SellingAgreementDetailedSerializer
    permission_classes = [IsAuthenticated, IsSeller]

    def get_queryset(self):
        """Return only documents with selling agreements for this seller"""
        if getattr(self, 'swagger_fake_view', False):
            return PropertyDocument.objects.none()
        return PropertyDocument.objects.filter(
            seller=self.request.user,
            selling_agreement_file__isnull=False
        ).exclude(selling_agreement_file='').select_related(
            'selling_request', 'seller'
        )

    @swagger_auto_schema(
        operation_description="List all selling agreements for the authenticated seller",
        responses={
            200: openapi.Response(
                description="List of selling agreements",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'agreements': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                    }
                )
            ),
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "count": queryset.count(),
            "agreements": serializer.data
        }, status=status.HTTP_200_OK)


class SellerAgreementDetailView(generics.RetrieveAPIView):
    """
    View a specific selling agreement.
    Only the seller who owns the property document can view it.
    """
    serializer_class = SellingAgreementDetailedSerializer
    permission_classes = [IsAuthenticated, IsSeller]
    lookup_field = 'pk'

    def get_queryset(self):
        """Return only documents with selling agreements for this seller"""
        if getattr(self, 'swagger_fake_view', False):
            return PropertyDocument.objects.none()
        return PropertyDocument.objects.filter(
            seller=self.request.user,
            selling_agreement_file__isnull=False
        ).exclude(selling_agreement_file='').select_related(
            'selling_request', 'seller'
        )

    @swagger_auto_schema(
        operation_description="View a specific selling agreement",
        responses={
            200: SellingAgreementDetailedSerializer,
            401: "Unauthorized",
            404: "Not Found - Agreement not found or not yours"
        }
    )
    def get(self, request, pk, *args, **kwargs):
        try:
            agreement = self.get_queryset().get(pk=pk)
        except PropertyDocument.DoesNotExist:
            return Response(
                {"detail": "Selling agreement not found or you don't have permission to view it."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(agreement)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AgreementAcceptView(views.APIView):
    """
    Accept a selling agreement.
    Updates agreement_status to 'accepted'.
    Only the seller who owns the property document can accept it.
    Notifies the agent about the acceptance.
    """
    permission_classes = [IsAuthenticated, IsSeller]
    
    @swagger_auto_schema(
        operation_description="Accept a selling agreement",
        responses={
            200: openapi.Response(
                description="Agreement accepted",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: "Bad Request - No agreement file or already accepted",
            401: "Unauthorized",
            403: "Forbidden - Not your agreement",
            404: "Not Found - Property document not found"
        }
    )
    def post(self, request, pk):
        """Accept selling agreement"""
        # Get the property document
        try:
            document = PropertyDocument.objects.select_related(
                'selling_request', 'seller'
            ).get(pk=pk)
        except PropertyDocument.DoesNotExist:
            return Response(
                {"detail": "Property document not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify ownership
        if document.seller != request.user:
            return Response(
                {"detail": "You don't have permission to accept this agreement."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if selling agreement file exists
        if not document.selling_agreement_file:
            return Response(
                {"detail": "No selling agreement file has been uploaded for this document."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already accepted
        if document.agreement_status == 'accepted':
            return Response(
                {"detail": "This selling agreement has already been accepted."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already rejected (prevent changing from rejected to accepted)
        if document.agreement_status == 'rejected':
            return Response(
                {"detail": "This selling agreement has been rejected and cannot be accepted."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status
        document.agreement_status = 'accepted'
        document.save()
        
        # No need to update notification - serializer handles dynamic display based on agreement_status
        
        # Create notification for agent
        seller_name = request.user.get_full_name() or request.user.username
        property_location = request.user.location or "the property"
        
        AgentNotification.objects.create(
            agent=document.selling_request.agent,
            notification_type='document_updated',
            selling_request=document.selling_request,
            property_document=document,
            title='Selling Agreement Accepted',
            message=f'Seller {seller_name} has accepted the selling agreement for {property_location}. '
                   f'The agreement is now legally binding and you can proceed with the next steps.',
            action_url=f'/agent/selling-requests/{document.selling_request.id}/',
            action_text='View Selling Request'
        )
        
        serializer = SellingAgreementDetailedSerializer(document)
        return Response({
            "message": "Selling agreement accepted successfully. Agent has been notified.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class AgreementRejectView(views.APIView):
    """
    Reject a selling agreement.
    Updates agreement_status to 'rejected'.
    Only the seller who owns the property document can reject it.
    Notifies the agent about the rejection.
    """
    permission_classes = [IsAuthenticated, IsSeller]
    
    @swagger_auto_schema(
        operation_description="Reject a selling agreement. Optionally provide a reason.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'reason': openapi.Schema(type=openapi.TYPE_STRING, description='Optional rejection reason')
            }
        ),
        responses={
            200: openapi.Response(
                description="Agreement rejected",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: "Bad Request - No agreement file or already rejected",
            401: "Unauthorized",
            403: "Forbidden - Not your agreement",
            404: "Not Found - Property document not found"
        }
    )
    def post(self, request, pk):
        """Reject selling agreement"""
        # Get the property document
        try:
            document = PropertyDocument.objects.select_related(
                'selling_request', 'seller'
            ).get(pk=pk)
        except PropertyDocument.DoesNotExist:
            return Response(
                {"detail": "Property document not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify ownership
        if document.seller != request.user:
            return Response(
                {"detail": "You don't have permission to reject this agreement."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if selling agreement file exists
        if not document.selling_agreement_file:
            return Response(
                {"detail": "No selling agreement file has been uploaded for this document."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already rejected
        if document.agreement_status == 'rejected':
            return Response(
                {"detail": "This selling agreement has already been rejected."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already accepted (prevent changing from accepted to rejected)
        if document.agreement_status == 'accepted':
            return Response(
                {"detail": "This selling agreement has been accepted and cannot be rejected."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get optional rejection reason
        rejection_reason = request.data.get('reason', '')
        
        # Update status
        document.agreement_status = 'rejected'
        document.save()
        
        # No need to update notification - serializer handles dynamic display based on agreement_status
        
        # Create notification for agent
        seller_name = request.user.get_full_name() or request.user.username
        property_location = request.user.location or "the property"
        
        rejection_message = f'Seller {seller_name} has rejected the selling agreement for {property_location}.'
        if rejection_reason:
            rejection_message += f' Reason: {rejection_reason}'
        rejection_message += ' Please review and prepare a revised agreement if needed.'
        
        AgentNotification.objects.create(
            agent=document.selling_request.agent,
            notification_type='document_updated',
            selling_request=document.selling_request,
            property_document=document,
            title='Selling Agreement Rejected',
            message=rejection_message,
            action_url=f'/agent/selling-requests/{document.selling_request.id}/',
            action_text='View Selling Request'
        )
        
        serializer = SellingAgreementDetailedSerializer(document)
        return Response({
            "message": "Selling agreement rejected. Agent has been notified.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


# ================== Legal Documents Views (GET Only) ==================

@swagger_auto_schema(
    method='get',
    operation_summary="Get Active Seller Privacy Policy",
    operation_description="Get the currently active privacy policy for sellers",
    tags=['Seller - Legal Documents'],
    responses={
        200: openapi.Response('Active privacy policy'),
        404: 'No active privacy policy found'
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seller_get_privacy_policy(request):
    """Get the active privacy policy for sellers"""
    from superadmin.models import SellerPrivacyPolicy
    from superadmin.serializers import SellerPrivacyPolicySerializer
    
    try:
        policy = SellerPrivacyPolicy.objects.filter(is_active=True).latest('effective_date')
        serializer = SellerPrivacyPolicySerializer(policy)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except SellerPrivacyPolicy.DoesNotExist:
        return Response({'error': 'No active privacy policy found'}, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='get',
    operation_summary="Get Active Seller Terms & Conditions",
    operation_description="Get the currently active terms & conditions for sellers",
    tags=['Seller - Legal Documents'],
    responses={
        200: openapi.Response('Active terms & conditions'),
        404: 'No active terms & conditions found'
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seller_get_terms_conditions(request):
    """Get the active terms & conditions for sellers"""
    from superadmin.models import SellerTermsConditions
    from superadmin.serializers import SellerTermsConditionsSerializer
    
    try:
        terms = SellerTermsConditions.objects.filter(is_active=True).latest('effective_date')
        serializer = SellerTermsConditionsSerializer(terms)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except SellerTermsConditions.DoesNotExist:
        return Response({'error': 'No active terms & conditions found'}, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='get',
    operation_description='Get all active seller/selling agreement documents',
    responses={
        200: 'List of selling agreement documents',
        401: 'Unauthorized'
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSeller])
def seller_agreement_documents(request):
    """
    Get all active selling agreement documents.
    Sellers can view selling agreement documents.
    """
    from superadmin.models import PlatformDocument
    from superadmin.serializers import PlatformDocumentSerializer
    
    documents = PlatformDocument.objects.filter(
        document_type='selling_agreement',
        is_active=True
    ).order_by('-created_at')
    
    serializer = PlatformDocumentSerializer(documents, many=True, context={'request': request})
    return Response({
        'count': documents.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)
