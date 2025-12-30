from rest_framework import viewsets, status, views, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from pdezzy.permissions import IsAgent
from seller.models import SellingRequest, SellerNotification, PropertyDocument, AgentNotification, DocumentFile
from .models import PropertyListing

from .serializers import (
    UserSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
    AgentSellingRequestSerializer,
    AgentSellingRequestStatusUpdateSerializer,
    AgentNotificationSerializer,
    AgentNotificationUpdateSerializer,
    AgentCMAUploadSerializer,
    AgentCMAUploadResponseSerializer,
    AgentSellingAgreementUploadSerializer,
    AgentCreateListingSerializer,
    PropertyListingResponseSerializer,
    AgentShowingScheduleSerializer,
    AgentShowingResponseSerializer,
    AgentCreateShowingSerializer,
    AgentPropertyDocumentSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    Register a new user account.
    Returns access and refresh tokens upon successful registration.
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @swagger_auto_schema(
        operation_description="Register a new agent account",
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
    User login endpoint.
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
            400: "Bad Request - Invalid token"
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
    Get current user profile.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get current user profile",
        responses={
            200: UserSerializer,
            401: "Unauthorized"
        }
    )
    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProfileUpdateView(views.APIView):
    """
    Update current user profile with comprehensive professional information.
    Only agents can update their own profile.
    Supports file uploads for profile pictures and agent documents.
    """
    permission_classes = [IsAuthenticated, IsAgent]

    @swagger_auto_schema(
        operation_description="Update current user profile with all information (Basic, Professional, Languages, Service Areas, Property Types, Availability)",
        request_body=ProfileUpdateSerializer,
        responses={
            200: UserSerializer,
            400: "Bad Request - Validation errors",
            401: "Unauthorized"
        }
    )
    def put(self, request):
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(UserSerializer(request.user, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Partially update current user profile (supports all fields: Basic, Professional, Languages, Service Areas, Property Types, Availability)",
        request_body=ProfileUpdateSerializer,
        responses={
            200: UserSerializer,
            400: "Bad Request - Validation errors",
            401: "Unauthorized"
        }
    )
    def patch(self, request):
        return self.put(request)


class ChangePasswordView(views.APIView):
    """
    Change current user's password.
    Only agents can change their own password.
    """
    permission_classes = [IsAuthenticated, IsAgent]

    @swagger_auto_schema(
        operation_description="Change current user password",
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
    Retrieve, update or delete a user instance.
    Only agents can access their own details.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    def get_object(self):
        return self.request.user

    @swagger_auto_schema(
        operation_description="Retrieve the authenticated agent's user details",
        responses={
            200: UserSerializer,
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update the authenticated agent's user details",
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
        operation_description="Delete the authenticated agent's account",
        responses={
            204: "No Content - Successfully deleted",
            401: "Unauthorized"
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class AgentSellingRequestStatsView(views.APIView):
    """
    Get selling request statistics for authenticated agent.
    Shows counts of pending, accepted, and rejected requests.
    """
    permission_classes = [IsAuthenticated, IsAgent]

    @swagger_auto_schema(
        operation_description="Get selling request statistics for the authenticated agent",
        responses={
            200: openapi.Response(
                description="Selling request statistics",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_requests': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total number of requests'),
                        'pending_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of pending requests'),
                        'accepted_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of accepted requests'),
                        'rejected_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of rejected requests'),
                        'stats': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                                    'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            )
                        )
                    }
                )
            ),
            401: "Unauthorized"
        },
        tags=['Agent Selling Requests']
    )
    def get(self, request):
        """Get selling request statistics for agent"""
        from seller.models import SellingRequest
        
        # Get all selling requests for this agent
        agent_requests = SellingRequest.objects.filter(agent=request.user)
        
        # Count by status
        pending_count = agent_requests.filter(status='pending').count()
        accepted_count = agent_requests.filter(status='accepted').count()
        rejected_count = agent_requests.filter(status='rejected').count()
        total_count = agent_requests.count()
        
        stats_by_status = [
            {'status': 'pending', 'count': pending_count},
            {'status': 'accepted', 'count': accepted_count},
            {'status': 'rejected', 'count': rejected_count},
        ]
        
        return Response({
            'total_requests': total_count,
            'pending_count': pending_count,
            'accepted_count': accepted_count,
            'rejected_count': rejected_count,
            'stats': stats_by_status
        }, status=status.HTTP_200_OK)


class AgentSellingRequestListView(generics.ListAPIView):
    """
    List all selling requests for agents to review.
    Only authenticated agents can access this endpoint.
    """
    queryset = SellingRequest.objects.all()
    serializer_class = AgentSellingRequestSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    @swagger_auto_schema(
        operation_description="List all selling requests for agent review",
        responses={
            200: AgentSellingRequestSerializer(many=True),
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AgentSellingRequestDetailView(generics.RetrieveAPIView):
    """
    Retrieve details of a specific selling request.
    Only authenticated agents can access this endpoint.
    """
    queryset = SellingRequest.objects.all()
    serializer_class = AgentSellingRequestSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    @swagger_auto_schema(
        operation_description="Retrieve details of a specific selling request",
        responses={
            200: AgentSellingRequestSerializer,
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AgentSellingRequestStatusUpdateView(views.APIView):
    """
    Update selling request status (accept/reject).
    Only authenticated agents can update request status.
    Can change status from 'pending' to 'accepted' or 'rejected'.
    Single unified endpoint for both accept and reject operations.
    """
    permission_classes = [IsAuthenticated, IsAgent]

    @swagger_auto_schema(
        operation_description="Update selling request status to accepted or rejected",
        request_body=AgentSellingRequestStatusUpdateSerializer,
        responses={
            200: AgentSellingRequestSerializer,
            400: "Bad Request - Invalid status or request not pending",
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def patch(self, request, pk):
        try:
            selling_request = SellingRequest.objects.get(pk=pk)
        except SellingRequest.DoesNotExist:
            return Response(
                {"error": "Selling request not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if selling_request.status != 'pending':
            return Response(
                {"error": f"Can only update requests with 'pending' status. Current status: {selling_request.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AgentSellingRequestStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            new_status = serializer.validated_data['status']
            selling_request.status = new_status
            selling_request.save()
            
            # Create notification for seller
            if new_status == 'accepted':
                notification_title = "Selling Request Approved"
                notification_message = (
                    f"Your property selling request has been accepted for review. "
                    f"Upload your property images or supporting documents so we can prepare your CMA report."
                )
                notification_type = 'approved'
                action_text = "View CMA Report"
                action_url = f"/api/v1/seller/selling-requests/{selling_request.id}/"
            else:  # rejected
                notification_title = "Selling Request Declined"
                notification_message = (
                    f"Your property selling request has been declined by the agent. "
                    f"We will reach out to you shortly to discuss next steps or you can contact via chat."
                )
                notification_type = 'rejected'
                action_text = "Chat with Agent"
                action_url = f"/api/v1/seller/chat/"
            
            SellerNotification.objects.create(
                seller=selling_request.seller,
                selling_request=selling_request,
                notification_type=notification_type,
                title=notification_title,
                message=notification_message,
                action_url=action_url,
                action_text=action_text,
                is_read=False
            )
            
            response_message = f"Selling request {new_status} successfully."
            return Response(
                {
                    "message": response_message,
                    "data": AgentSellingRequestSerializer(selling_request).data
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AgentNotificationListView(generics.ListAPIView):
    """
    List all notifications for the agent.
    Includes notifications about selling requests and showing schedules.
    Ordered by most recent first.
    """
    serializer_class = AgentNotificationSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    def get_queryset(self):
        """Return agent's notifications for their assigned selling requests"""
        # Only show notifications for this specific agent
        return AgentNotification.objects.filter(
            agent=self.request.user  # Only notifications assigned to this agent
        ).order_by('-created_at')

    @swagger_auto_schema(
        operation_description="List all agent notifications ordered by most recent first",
        responses={
            200: AgentNotificationSerializer(many=True),
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AgentNotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific agent notification.
    Agents can mark notifications as read.
    """
    serializer_class = AgentNotificationSerializer
    permission_classes = [IsAuthenticated, IsAgent]
    queryset = AgentNotification.objects.all()

    @swagger_auto_schema(
        operation_description="Retrieve a specific agent notification",
        responses={
            200: AgentNotificationSerializer,
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Update a specific agent notification (e.g., mark as read)",
        request_body=AgentNotificationUpdateSerializer,
        responses={
            200: AgentNotificationSerializer,
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def patch(self, request, *args, **kwargs):
        notification = self.get_object()
        serializer = AgentNotificationUpdateSerializer(
            notification,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                AgentNotificationSerializer(notification).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Delete a specific agent notification",
        responses={
            204: "No Content - Successfully deleted",
            401: "Unauthorized",
            404: "Not Found"
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class AgentNotificationUnreadCountView(views.APIView):
    """
    Get the count of unread agent notifications.
    """
    permission_classes = [IsAuthenticated, IsAgent]

    @swagger_auto_schema(
        operation_description="Get count of unread agent notifications",
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
        unread_count = AgentNotification.objects.filter(
            agent=request.user,
            is_read=False
        ).count()
        return Response(
            {"unread_count": unread_count},
            status=status.HTTP_200_OK
        )


class AgentNotificationMarkAllReadView(views.APIView):
    """
    Mark all agent notifications as read.
    """
    permission_classes = [IsAuthenticated, IsAgent]

    @swagger_auto_schema(
        operation_description="Mark all agent notifications as read",
        responses={
            200: openapi.Response(
                description="Success",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'marked_read_count': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            401: "Unauthorized"
        }
    )
    def post(self, request):
        unread_notifications = AgentNotification.objects.filter(
            agent=request.user,
            is_read=False
        )
        count = unread_notifications.count()
        unread_notifications.update(is_read=True)
        
        return Response(
            {
                "message": "All notifications marked as read.",
                "marked_read_count": count
            },
            status=status.HTTP_200_OK
        )


class AgentCMAUploadView(views.APIView):
    """
    Upload CMA documents to an approved selling request.
    Only agents can upload CMA documents. Supports multiple files.
    """
    permission_classes = [IsAuthenticated, IsAgent]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_description="Upload multiple CMA documents to an approved selling request. Notifies the seller.",
        manual_parameters=[
            openapi.Parameter(
                'document_type',
                openapi.IN_FORM,
                description="Document type (must be 'cma')",
                type=openapi.TYPE_STRING,
                default='cma'
            ),
            openapi.Parameter(
                'title',
                openapi.IN_FORM,
                description="Title for the CMA documents",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'files',
                openapi.IN_FORM,
                description="Multiple CMA files to upload (PDF, JPG, JPEG, PNG)",
                type=openapi.TYPE_FILE,
                required=True
            ),
            openapi.Parameter(
                'description',
                openapi.IN_FORM,
                description="Optional description for the CMA documents",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            201: openapi.Response(
                description="CMA documents uploaded successfully",
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
            400: "Bad Request - Request not accepted",
            401: "Unauthorized",
            404: "Not Found - Selling request not found"
        }
    )
    def post(self, request, selling_request_id, *args, **kwargs):
        """Upload multiple CMA documents to a selling request"""
        try:
            selling_request = SellingRequest.objects.get(pk=selling_request_id)
        except SellingRequest.DoesNotExist:
            return Response(
                {"error": "Selling request not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if selling_request.status != 'accepted':
            return Response(
                {"error": "Can only upload CMA for approved selling requests"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if selling_request.agent != request.user:
            return Response(
                {"error": "You can only upload CMA for selling requests assigned to you"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AgentCMAUploadSerializer(
            data=request.data,
            context={'request': request, 'selling_request_id': selling_request_id}
        )
        if serializer.is_valid():
            # Create a single CMA document
            document = PropertyDocument.objects.create(
                selling_request=selling_request,
                seller=selling_request.seller,
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

            # Create notification for seller about CMA being ready
            seller = selling_request.seller
            seller_name = seller.get_full_name() or seller.username
            property_location = seller.location or "your property"

            file_count = len(uploaded_files)
            file_names = [doc_file.original_filename for doc_file in uploaded_files[:3]]
            if file_count > 3:
                file_names.append(f"and {file_count - 3} more")

            notification_message = (
                f"Hi {seller_name}, your CMA (Comparative Market Analysis) report for {property_location} "
                f"has been prepared by the agent. The report contains {file_count} file(s): {', '.join(file_names)}. "
                f"Please review it and contact the agent if you have any questions."
            )

            SellerNotification.objects.create(
                seller=seller,
                selling_request=selling_request,
                cma_document=document,
                notification_type='cma_ready',
                title=f"CMA Report Ready - {property_location}",
                message=notification_message,
                action_url=f"/api/v1/seller/selling-requests/{selling_request.id}/documents/",
                action_text="View CMA Report",
                is_read=False
            )

            # Serialize the document with files
            response_serializer = AgentCMAUploadResponseSerializer(document, context={'request': request})

            return Response({
                "message": f"CMA documents uploaded successfully. Seller has been notified.",
                "document": response_serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AgentCMAListView(generics.ListAPIView):
    """
    List all CMA documents for a specific selling request.
    Only agents can access this endpoint.
    """
    serializer_class = AgentNotificationSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    def get_queryset(self):
        """Return CMA documents for the selling request"""
        selling_request_id = self.kwargs.get('selling_request_id')
        try:
            selling_request = SellingRequest.objects.get(pk=selling_request_id)
        except SellingRequest.DoesNotExist:
            return PropertyDocument.objects.none()

        # Return CMA documents only
        return PropertyDocument.objects.filter(
            selling_request=selling_request,
            document_type='cma'
        )

    @swagger_auto_schema(
        operation_description="List all CMA documents for a specific selling request",
        responses={
            200: openapi.Response(
                description="List of CMA documents",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'selling_request_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'seller': openapi.Schema(type=openapi.TYPE_STRING),
                        'cma_documents': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                    }
                )
            ),
            401: "Unauthorized",
            404: "Not Found - Selling request not found"
        }
    )
    def get(self, request, *args, **kwargs):
        selling_request_id = self.kwargs.get('selling_request_id')
        try:
            selling_request = SellingRequest.objects.get(pk=selling_request_id)
        except SellingRequest.DoesNotExist:
            return Response(
                {"error": "Selling request not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        cma_documents = PropertyDocument.objects.filter(
            selling_request=selling_request,
            document_type='cma'
        )
        
        from .serializers import PropertyDocumentForCMASerializer
        serializer = PropertyDocumentForCMASerializer(cma_documents, many=True)
        return Response(
            {
                "selling_request_id": selling_request_id,
                "seller": selling_request.seller.get_full_name(),
                "cma_documents": serializer.data
            },
            status=status.HTTP_200_OK
        )


class AgentPropertyDocumentListView(generics.ListAPIView):
    """
    List all property documents for a specific selling request.
    Only agents assigned to the selling request can access this endpoint.
    """
    serializer_class = AgentPropertyDocumentSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    def get_queryset(self):
        """Return property documents for the selling request that the agent is assigned to"""
        selling_request_id = self.kwargs.get('selling_request_id')
        try:
            selling_request = SellingRequest.objects.get(pk=selling_request_id)
        except SellingRequest.DoesNotExist:
            return PropertyDocument.objects.none()

        # Check if the agent is assigned to this selling request
        if selling_request.agent != self.request.user:
            return PropertyDocument.objects.none()

        # Return all property documents (not just CMA)
        return PropertyDocument.objects.filter(
            selling_request=selling_request
        ).exclude(document_type='cma')  # Exclude CMA as they have their own endpoint

    @swagger_auto_schema(
        operation_description="List all property documents for a specific selling request (excluding CMA)",
        responses={
            200: openapi.Response(
                description="List of property documents",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'selling_request_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'seller': openapi.Schema(type=openapi.TYPE_STRING),
                        'documents': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                    }
                )
            ),
            401: "Unauthorized",
            403: "Forbidden - Not assigned to this selling request",
            404: "Not Found - Selling request not found"
        }
    )
    def get(self, request, *args, **kwargs):
        selling_request_id = self.kwargs.get('selling_request_id')
        try:
            selling_request = SellingRequest.objects.get(pk=selling_request_id)
        except SellingRequest.DoesNotExist:
            return Response(
                {"error": "Selling request not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if the agent is assigned to this selling request
        if selling_request.agent != request.user:
            return Response(
                {"error": "You can only view documents for selling requests assigned to you"},
                status=status.HTTP_403_FORBIDDEN
            )

        documents = self.get_queryset()

        serializer = self.get_serializer(documents, many=True, context={'request': request})
        return Response(
            {
                "selling_request_id": selling_request_id,
                "seller": selling_request.seller.get_full_name(),
                "documents": serializer.data
            },
            status=status.HTTP_200_OK
        )


class AgentPropertyDocumentDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific property document.
    Only agents assigned to the selling request can access this endpoint.
    """
    serializer_class = AgentPropertyDocumentSerializer
    permission_classes = [IsAuthenticated, IsAgent]

    def get_queryset(self):
        """Return property documents that the agent has access to"""
        return PropertyDocument.objects.filter(
            selling_request__agent=self.request.user
        )

    @swagger_auto_schema(
        operation_description="Retrieve a specific property document",
        responses={
            200: AgentPropertyDocumentSerializer,
            401: "Unauthorized",
            403: "Forbidden - Not assigned to this selling request",
            404: "Not Found - Document not found"
        }
    )
    def get(self, request, *args, **kwargs):
        document = self.get_object()

        # Check if the agent is assigned to this selling request
        if document.selling_request.agent != request.user:
            return Response(
                {"error": "You can only view documents for selling requests assigned to you"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AgentSellingAgreementUploadView(generics.UpdateAPIView):
    """
    Upload or update selling agreement document for a property document.
    Only agents can upload selling agreements.
    Sets agreement_status to 'pending' by default.
    """
    serializer_class = AgentSellingAgreementUploadSerializer
    permission_classes = [IsAuthenticated, IsAgent]
    lookup_field = 'pk'

    def get_queryset(self):
        """Return property documents from accepted selling requests"""
        return PropertyDocument.objects.filter(
            selling_request__status='accepted'
        )

    def perform_update(self, serializer):
        """Update property document with selling agreement file"""
        document = serializer.save()
        selling_request = document.selling_request
        seller = selling_request.seller
        
        # Find related CMA document for this selling request
        cma_document = selling_request.documents.filter(document_type='cma').first()
        
        # Create notification for seller about selling agreement being ready
        seller_name = seller.get_full_name() or seller.username
        property_location = seller.location or "your property"
        
        notification_message = (
            f"Hi {seller_name}, your selling agreement document for {property_location} "
            f"has been prepared by the agent and is ready for your review. "
            f"Please review the agreement and confirm your acceptance."
        )
        
        SellerNotification.objects.create(
            seller=seller,
            selling_request=selling_request,
            cma_document=cma_document,
            notification_type='agreement',
            title=f"Selling Agreement Ready - {property_location}",
            message=notification_message,
            action_url=f"/api/v1/seller/agreements/{document.id}/",
            action_text="Review Agreement",
            is_read=False
        )

    @swagger_auto_schema(
        operation_description="Upload or update selling agreement document for a property document. Notifies the seller.",
        request_body=AgentSellingAgreementUploadSerializer,
        responses={
            200: openapi.Response(
                description="Selling agreement uploaded successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: "Bad Request - Request not accepted",
            401: "Unauthorized",
            404: "Not Found - Property document not found"
        }
    )
    def patch(self, request, pk, *args, **kwargs):
        """Upload or update selling agreement for a property document"""
        try:
            document = PropertyDocument.objects.get(pk=pk)
        except PropertyDocument.DoesNotExist:
            return Response(
                {"error": "Property document not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if document.selling_request.status != 'accepted':
            return Response(
                {"error": "Can only upload selling agreement for approved selling requests"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AgentSellingAgreementUploadSerializer(
            document,
            data=request.data,
            partial=True,
            context={'request': request, 'document_id': pk}
        )
        if serializer.is_valid():
            self.perform_update(serializer)
            selling_agreement_url = None
            if serializer.instance.selling_agreement_file:
                selling_agreement_url = request.build_absolute_uri(serializer.instance.selling_agreement_file.url)
            return Response(
                {
                    "message": "Selling agreement uploaded successfully. Seller has been notified.",
                    "data": {
                        "id": serializer.instance.id,
                        "selling_agreement_file": selling_agreement_url,
                        "agreement_status": serializer.instance.agreement_status,
                        "updated_at": serializer.instance.updated_at
                    }
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AgentCreateListingView(views.APIView):
    """
    Create a property listing after seller accepts the agreement.
    
    Agent can only create a listing when:
    1. The property document exists
    2. The selling agreement has been uploaded
    3. The seller has accepted the agreement (agreement_status = 'accepted')
    """
    permission_classes = [IsAuthenticated, IsAgent]
    parser_classes = (MultiPartParser, FormParser)
    @swagger_auto_schema(
        operation_description="Create a property listing after seller accepts agreement",
        manual_parameters=[
            openapi.Parameter(
                'agreement_id',
                openapi.IN_PATH,
                description='ID of the selling agreement (property document)',
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'title',
                openapi.IN_FORM,
                description='Property title/name',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'street_address',
                openapi.IN_FORM,
                description='Street address',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'city',
                openapi.IN_FORM,
                description='City name',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'state',
                openapi.IN_FORM,
                description='State/Province',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'zip_code',
                openapi.IN_FORM,
                description='ZIP/Postal code',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'property_type',
                openapi.IN_FORM,
                description='Type of property (e.g., House, Apartment, Condo)',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'bedrooms',
                openapi.IN_FORM,
                description='Number of bedrooms',
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'bathrooms',
                openapi.IN_FORM,
                description='Number of bathrooms',
                type=openapi.TYPE_NUMBER,
                required=True
            ),
            openapi.Parameter(
                'price',
                openapi.IN_FORM,
                description='Property price',
                type=openapi.TYPE_NUMBER,
                required=True
            ),
            openapi.Parameter(
                'square_feet',
                openapi.IN_FORM,
                description='Property size in square feet',
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'description',
                openapi.IN_FORM,
                description='Property description',
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'photos',
                openapi.IN_FORM,
                description='Property photos (JPG, PNG, max 10MB each) - can upload multiple',
                type=openapi.TYPE_FILE,
                required=False
            ),
            openapi.Parameter(
                'documents',
                openapi.IN_FORM,
                description='Property documents (PDF, JPG, PNG, max 10MB each) - can upload multiple',
                type=openapi.TYPE_FILE,
                required=False
            ),
        ],
        responses={
            201: openapi.Response(description="Listing created successfully"),
            400: "Bad Request - Agreement not accepted or validation error",
            401: "Unauthorized",
            404: "Not Found - Property document not found"
        }
    )
    def post(self, request, agreement_id, *args, **kwargs):
        """Create a property listing for an accepted agreement"""
        from .serializers import AgentCreateListingSerializer, PropertyListingResponseSerializer
        from .models import PropertyListing
        
        # Get the property document (agreement)
        try:
            property_document = PropertyDocument.objects.get(pk=agreement_id)
        except PropertyDocument.DoesNotExist:
            return Response(
                {"error": "Property document not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if agreement has been accepted by seller
        if property_document.agreement_status != 'accepted':
            return Response(
                {"error": "Cannot create listing. Seller has not accepted the agreement yet."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if listing already exists for this agreement
        if hasattr(property_document, 'listing'):
            return Response(
                {"error": "A listing already exists for this agreement."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the listing
        serializer = AgentCreateListingSerializer(data=request.data)
        if serializer.is_valid():
            listing = serializer.save(
                agent=request.user,
                property_document=property_document
            )
            
            response_serializer = PropertyListingResponseSerializer(listing)
            return Response(
                {
                    "message": "Property listing created successfully",
                    "data": response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Update a property listing - supports metadata, photos, and documents in one request",
        responses={
            200: openapi.Response(description="Listing updated successfully"),
            400: "Bad Request - Validation error",
            401: "Unauthorized",
            403: "Forbidden - Not the listing owner",
            404: "Not Found - Listing not found"
        }
    )
    def patch(self, request, agreement_id, *args, **kwargs):
        """Update a property listing - metadata, photos, and documents"""
        from .serializers import PropertyListingResponseSerializer
        from .models import PropertyListing, PropertyListingPhoto, PropertyListingDocument
        
        # Get the property document (agreement)
        try:
            property_document = PropertyDocument.objects.get(pk=agreement_id)
        except PropertyDocument.DoesNotExist:
            return Response(
                {"error": "Property document not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the listing for this agreement
        if not hasattr(property_document, 'listing'):
            return Response(
                {"error": "No listing exists for this agreement yet. Create one first using POST."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        listing = property_document.listing
        
        # Check if the user is the listing owner
        if listing.agent_id != request.user.id:
            return Response(
                {"error": "You do not have permission to update this listing."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only allow specific fields to be updated for metadata
        allowed_fields = {
            'title', 'street_address', 'city', 'state', 'zip_code', 
            'property_type', 'bedrooms', 'bathrooms', 'square_feet', 
            'description', 'price', 'status'
        }
        
        # Track what was updated
        update_summary = {}
        
        # 1. Update metadata fields
        update_data = {}
        for key in request.data.keys():
            if key in allowed_fields:
                value = request.data.get(key)
                # Skip empty values
                if value is not None and value != '':
                    update_data[key] = value
        
        if update_data:
            for field, value in update_data.items():
                setattr(listing, field, value)
            update_summary['metadata'] = list(update_data.keys())
        
        # 2. Handle photo uploads
        photos = request.FILES.getlist('photos')
        uploaded_photos = []
        if photos:
            for photo_file in photos:
                try:
                    photo = PropertyListingPhoto.objects.create(
                        listing=listing,
                        photo=photo_file,
                        is_primary=listing.photos.count() == 0,  # First photo is primary
                        order=listing.photos.count()
                    )
                    uploaded_photos.append({
                        'id': photo.id,
                        'url': request.build_absolute_uri(photo.photo.url),
                        'is_primary': photo.is_primary,
                        'created_at': photo.created_at.isoformat()
                    })
                except Exception as e:
                    return Response(
                        {"error": f"Failed to upload photo: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            update_summary['photos'] = len(uploaded_photos)
        
        # 3. Handle document uploads
        documents = request.FILES.getlist('documents')
        uploaded_documents = []
        if documents:
            document_type = request.data.get('document_type', 'other')
            
            # Validate document type
            valid_types = ['deed', 'inspection', 'appraisal', 'floor_plan', 'other']
            if document_type not in valid_types:
                return Response(
                    {"error": f"Invalid document type. Must be one of: {', '.join(valid_types)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            for doc_file in documents:
                try:
                    title = doc_file.name.rsplit('.', 1)[0]
                    
                    document = PropertyListingDocument.objects.create(
                        listing=listing,
                        document=doc_file,
                        document_type=document_type,
                        title=title,
                        file_size=doc_file.size
                    )
                    uploaded_documents.append({
                        'id': document.id,
                        'title': document.title,
                        'document_type': document.document_type,
                        'url': request.build_absolute_uri(document.document.url),
                        'file_size': document.file_size,
                        'created_at': document.created_at.isoformat()
                    })
                except Exception as e:
                    return Response(
                        {"error": f"Failed to upload document: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            update_summary['documents'] = len(uploaded_documents)
        
        # Check if anything was actually updated
        if not update_data and not photos and not documents:
            return Response(
                {
                    "error": "No data provided to update. You can update: metadata fields, upload photos, and/or upload documents.",
                    "allowed_metadata_fields": sorted(list(allowed_fields)),
                    "allowed_document_types": ['deed', 'inspection', 'appraisal', 'floor_plan', 'other']
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save listing if metadata was updated
        if update_data:
            try:
                listing.full_clean()
                listing.save()
            except Exception as e:
                return Response(
                    {"error": f"Validation error: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        response_serializer = PropertyListingResponseSerializer(listing)
        return Response(
            {
                "message": "Property listing updated successfully",
                "updated_sections": update_summary,
                "data": response_serializer.data,
                "photos_added": len(uploaded_photos),
                "documents_added": len(uploaded_documents)
            },
            status=status.HTTP_200_OK
        )


class AgentListingPhotoUploadView(views.APIView):
    """
    Upload photos to a property listing
    """
    permission_classes = [IsAuthenticated, IsAgent]
    parser_classes = (MultiPartParser, FormParser)
    
    @swagger_auto_schema(
        operation_description="Upload photos to a property listing",
        responses={
            201: openapi.Response(description="Photos uploaded successfully"),
            400: "Bad Request - Validation error",
            401: "Unauthorized",
            403: "Forbidden - Not the listing owner",
            404: "Not Found - Listing not found"
        }
    )
    def post(self, request, agreement_id, *args, **kwargs):
        """Upload photos to listing"""
        from .models import PropertyListing, PropertyListingPhoto
        
        # Get the property document (agreement)
        try:
            property_document = PropertyDocument.objects.get(pk=agreement_id)
        except PropertyDocument.DoesNotExist:
            return Response(
                {"error": "Property document not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the listing
        if not hasattr(property_document, 'listing'):
            return Response(
                {"error": "No listing exists for this agreement"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        listing = property_document.listing
        
        # Check if user owns the listing
        if listing.agent_id != request.user.id:
            return Response(
                {"error": "You do not have permission to update this listing"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Handle photo uploads
        photos = request.FILES.getlist('photos')
        if not photos:
            return Response(
                {"error": "No photos provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_photos = []
        for photo_file in photos:
            try:
                photo = PropertyListingPhoto.objects.create(
                    listing=listing,
                    photo=photo_file,
                    is_primary=len(uploaded_photos) == 0,  # First photo is primary
                    order=listing.photos.count()
                )
                uploaded_photos.append({
                    'id': photo.id,
                    'url': request.build_absolute_uri(photo.photo.url),
                    'is_primary': photo.is_primary,
                    'created_at': photo.created_at.isoformat()
                })
            except Exception as e:
                return Response(
                    {"error": f"Failed to upload photo: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            {
                "message": f"{len(uploaded_photos)} photo(s) uploaded successfully",
                "photos": uploaded_photos
            },
            status=status.HTTP_201_CREATED
        )


class AgentListingDocumentUploadView(views.APIView):
    """
    Upload documents to a property listing
    """
    permission_classes = [IsAuthenticated, IsAgent]
    parser_classes = (MultiPartParser, FormParser)
    
    @swagger_auto_schema(
        operation_description="Upload documents to a property listing",
        responses={
            201: openapi.Response(description="Documents uploaded successfully"),
            400: "Bad Request - Validation error",
            401: "Unauthorized",
            403: "Forbidden - Not the listing owner",
            404: "Not Found - Listing not found"
        }
    )
    def post(self, request, agreement_id, *args, **kwargs):
        """Upload documents to listing"""
        from .models import PropertyListing, PropertyListingDocument
        
        # Get the property document (agreement)
        try:
            property_document = PropertyDocument.objects.get(pk=agreement_id)
        except PropertyDocument.DoesNotExist:
            return Response(
                {"error": "Property document not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the listing
        if not hasattr(property_document, 'listing'):
            return Response(
                {"error": "No listing exists for this agreement"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        listing = property_document.listing
        
        # Check if user owns the listing
        if listing.agent_id != request.user.id:
            return Response(
                {"error": "You do not have permission to update this listing"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Handle document uploads
        documents = request.FILES.getlist('documents')
        if not documents:
            return Response(
                {"error": "No documents provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document_type = request.data.get('document_type', 'other')
        
        # Validate document type
        valid_types = ['deed', 'inspection', 'appraisal', 'floor_plan', 'other']
        if document_type not in valid_types:
            return Response(
                {"error": f"Invalid document type. Must be one of: {', '.join(valid_types)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_documents = []
        for doc_file in documents:
            try:
                # Extract filename as title
                title = doc_file.name.rsplit('.', 1)[0]  # Remove extension
                
                document = PropertyListingDocument.objects.create(
                    listing=listing,
                    document=doc_file,
                    document_type=document_type,
                    title=title,
                    file_size=doc_file.size
                )
                uploaded_documents.append({
                    'id': document.id,
                    'title': document.title,
                    'document_type': document.document_type,
                    'url': request.build_absolute_uri(document.document.url),
                    'file_size': document.file_size,
                    'created_at': document.created_at.isoformat()
                })
            except Exception as e:
                return Response(
                    {"error": f"Failed to upload document: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            {
                "message": f"{len(uploaded_documents)} document(s) uploaded successfully",
                "documents": uploaded_documents
            },
            status=status.HTTP_201_CREATED
        )


class AgentListingsView(views.APIView):
    """
    Get all property listings created by the authenticated agent.
    Supports filtering by price range, bedrooms, and location.
    """
    permission_classes = [IsAuthenticated, IsAgent]
    
    @swagger_auto_schema(
        operation_description="Get all property listings created by the agent with optional filters",
        manual_parameters=[
            openapi.Parameter('min_price', openapi.IN_QUERY, description="Minimum price", type=openapi.TYPE_NUMBER),
            openapi.Parameter('max_price', openapi.IN_QUERY, description="Maximum price", type=openapi.TYPE_NUMBER),
            openapi.Parameter('bedrooms', openapi.IN_QUERY, description="Minimum bedrooms", type=openapi.TYPE_INTEGER),
            openapi.Parameter('city', openapi.IN_QUERY, description="Filter by city", type=openapi.TYPE_STRING),
            openapi.Parameter('state', openapi.IN_QUERY, description="Filter by state", type=openapi.TYPE_STRING),
            openapi.Parameter('zip_code', openapi.IN_QUERY, description="Filter by ZIP code", type=openapi.TYPE_STRING),
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status (draft, pending, published, sold, archived)", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('per_page', openapi.IN_QUERY, description="Results per page", type=openapi.TYPE_INTEGER, default=20),
        ],
        responses={
            200: openapi.Response(
                description="List of property listings",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'results': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'per_page': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
            401: "Unauthorized"
        },
        tags=['Agent Listings']
    )
    def get(self, request):
        """Get agent's property listings with filters"""
        from django.db.models import Q
        
        # Start with agent's listings
        queryset = PropertyListing.objects.filter(agent=request.user)
        
        # Apply filters
        min_price = request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=float(min_price))
        
        max_price = request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=float(max_price))
        
        bedrooms = request.query_params.get('bedrooms')
        if bedrooms:
            queryset = queryset.filter(bedrooms__gte=int(bedrooms))
        
        city = request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        state = request.query_params.get('state')
        if state:
            queryset = queryset.filter(state__icontains=state)
        
        zip_code = request.query_params.get('zip_code')
        if zip_code:
            queryset = queryset.filter(zip_code=zip_code)
        
        listing_status = request.query_params.get('status')
        if listing_status:
            queryset = queryset.filter(status=listing_status)
        
        # Order by created date (newest first)
        queryset = queryset.order_by('-created_at')
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        total = queryset.count()
        start = (page - 1) * per_page
        end = start + per_page
        
        listings = queryset[start:end]
        
        # Build response
        results = []
        for listing in listings:
            # Get primary photo
            primary_photo = listing.photos.filter(is_primary=True).first()
            if not primary_photo:
                primary_photo = listing.photos.first()
            
            photo_url = request.build_absolute_uri(primary_photo.photo.url) if primary_photo else None
            
            results.append({
                'id': listing.id,
                'mls_number': f"LOCAL-{listing.id}",
                'title': listing.title,
                'address': listing.street_address,
                'city': listing.city,
                'state': listing.state,
                'zip_code': listing.zip_code,
                'price': float(listing.price),
                'bedrooms': listing.bedrooms,
                'bathrooms': float(listing.bathrooms) if listing.bathrooms else None,
                'square_feet': listing.square_feet,
                'property_type': listing.property_type,
                'status': listing.status,
                'description': listing.description,
                'photo_url': photo_url,
                'photos_count': listing.photos.count(),
                'documents_count': listing.listing_documents.count(),
                'created_at': listing.created_at.isoformat(),
                'updated_at': listing.updated_at.isoformat(),
                'published_at': listing.published_at.isoformat() if listing.published_at else None,
            })
        
        return Response({
            'results': results,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 0,
        }, status=status.HTTP_200_OK)


class AgentShowingScheduleListView(views.APIView):
    """
    Get all showing schedule requests for the authenticated agent's listings.
    """
    permission_classes = [IsAuthenticated, IsAgent]
    
    @swagger_auto_schema(
        operation_description="Get all showing requests for agent's property listings",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="List of showing schedules",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_OBJECT)
                )
            )
        },
        tags=['Agent Showings']
    )
    def get(self, request):
        """Get agent's showing schedule requests"""
        from buyer.models import ShowingSchedule
        from .serializers import AgentShowingScheduleSerializer
        
        # Get showings for agent's listings
        showings = ShowingSchedule.objects.filter(
            property_listing__agent=request.user
        ).select_related('buyer', 'property_listing')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            showings = showings.filter(status=status_filter)
        
        serializer = AgentShowingScheduleSerializer(showings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AgentShowingScheduleDetailView(views.APIView):
    """
    Get details of a specific showing request.
    """
    permission_classes = [IsAuthenticated, IsAgent]
    
    @swagger_auto_schema(
        operation_description="Get details of a specific showing request",
        responses={
            200: openapi.Response(description="Showing schedule details"),
            404: "Not Found - Schedule not found or not owned by agent"
        },
        tags=['Agent Showings']
    )
    def get(self, request, schedule_id):
        """Get showing schedule details"""
        from buyer.models import ShowingSchedule
        from .serializers import AgentShowingScheduleSerializer
        
        try:
            schedule = ShowingSchedule.objects.select_related('buyer', 'property_listing').get(
                id=schedule_id,
                property_listing__agent=request.user
            )
        except ShowingSchedule.DoesNotExist:
            return Response(
                {'error': 'Showing schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AgentShowingScheduleSerializer(schedule)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AgentShowingRespondView(views.APIView):
    """
    Agent accepts or declines a showing request.
    """
    permission_classes = [IsAuthenticated, IsAgent]
    
    @swagger_auto_schema(
        operation_description="Accept or decline a showing request",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['status'],
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['accepted', 'declined'],
                    description='Accept or decline the showing'
                ),
                'agent_response': openapi.Schema(type=openapi.TYPE_STRING, description='Optional message to buyer'),
                'confirmed_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Confirmed date (required if accepting)'),
                'confirmed_time': openapi.Schema(type=openapi.TYPE_STRING, format='time', description='Confirmed time (required if accepting)'),
            }
        ),
        responses={
            200: openapi.Response(description="Showing schedule updated successfully"),
            400: "Bad Request - Invalid data",
            404: "Not Found - Schedule not found"
        },
        tags=['Agent Showings']
    )
    def post(self, request, schedule_id):
        """Accept or decline showing request"""
        from buyer.models import ShowingSchedule
        from .serializers import AgentShowingResponseSerializer, AgentShowingScheduleSerializer
        from django.utils import timezone
        
        try:
            schedule = ShowingSchedule.objects.get(
                id=schedule_id,
                property_listing__agent=request.user
            )
        except ShowingSchedule.DoesNotExist:
            return Response(
                {'error': 'Showing schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Can only respond to pending requests
        if schedule.status != 'pending':
            return Response(
                {'error': f'Cannot respond to a showing with status: {schedule.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AgentShowingResponseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update showing schedule
        schedule.status = serializer.validated_data['status']
        schedule.agent_response = serializer.validated_data.get('agent_response', '')
        schedule.responded_at = timezone.now()
        
        if serializer.validated_data['status'] == 'accepted':
            schedule.confirmed_date = serializer.validated_data['confirmed_date']
            schedule.confirmed_time = serializer.validated_data['confirmed_time']
        
        schedule.save()
        
        # Return updated schedule
        response_serializer = AgentShowingScheduleSerializer(schedule)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class AgentShowingAcceptView(views.APIView):
    """
    Agent accepts a showing request - simplified endpoint without needing schedule details.
    Only requires showing schedule ID.
    """
    permission_classes = [IsAuthenticated, IsAgent]
    
    @swagger_auto_schema(
        operation_description="Agent accepts a showing request",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'agent_response': openapi.Schema(type=openapi.TYPE_STRING, description='Optional message to buyer'),
            }
        ),
        responses={
            200: openapi.Response(description="Showing accepted successfully"),
            400: "Bad Request - Showing already responded",
            404: "Not Found - Showing not found"
        },
        tags=['Agent Showings']
    )
    def post(self, request, schedule_id):
        """Accept showing request"""
        from buyer.models import ShowingSchedule
        from .serializers import AgentShowingScheduleSerializer
        from django.utils import timezone
        
        try:
            schedule = ShowingSchedule.objects.get(
                id=schedule_id,
                property_listing__agent=request.user
            )
        except ShowingSchedule.DoesNotExist:
            return Response(
                {'error': 'Showing schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Can only respond to pending requests
        if schedule.status != 'pending':
            return Response(
                {'error': f'Cannot respond to a showing with status: {schedule.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update showing schedule - Accept
        schedule.status = 'accepted'
        schedule.agent_response = request.data.get('agent_response', '')
        schedule.responded_at = timezone.now()
        schedule.save()
        
        # Return updated schedule
        response_serializer = AgentShowingScheduleSerializer(schedule)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class AgentShowingRejectView(views.APIView):
    """
    Agent rejects a showing request - simplified endpoint without needing schedule details.
    Only requires showing schedule ID.
    """
    permission_classes = [IsAuthenticated, IsAgent]
    
    @swagger_auto_schema(
        operation_description="Agent rejects a showing request",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'agent_response': openapi.Schema(type=openapi.TYPE_STRING, description='Optional message to buyer explaining rejection'),
            }
        ),
        responses={
            200: openapi.Response(description="Showing rejected successfully"),
            400: "Bad Request - Showing already responded",
            404: "Not Found - Showing not found"
        },
        tags=['Agent Showings']
    )
    def post(self, request, schedule_id):
        """Reject showing request"""
        from buyer.models import ShowingSchedule
        from .serializers import AgentShowingScheduleSerializer
        from django.utils import timezone
        
        try:
            schedule = ShowingSchedule.objects.get(
                id=schedule_id,
                property_listing__agent=request.user
            )
        except ShowingSchedule.DoesNotExist:
            return Response(
                {'error': 'Showing schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Can only respond to pending requests
        if schedule.status != 'pending':
            return Response(
                {'error': f'Cannot respond to a showing with status: {schedule.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update showing schedule - Reject
        schedule.status = 'declined'
        schedule.agent_response = request.data.get('agent_response', '')
        schedule.responded_at = timezone.now()
        schedule.save()
        
        # Return updated schedule
        response_serializer = AgentShowingScheduleSerializer(schedule)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class AgentCreateShowingView(views.APIView):
    """
    Agent creates a showing schedule for a buyer (automatically accepted)
    """
    permission_classes = [IsAuthenticated, IsAgent]
    
    @swagger_auto_schema(
        operation_description="Agent creates a showing schedule with a buyer",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['buyer_id', 'property_listing_id', 'scheduled_date', 'scheduled_time'],
            properties={
                'buyer_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Buyer ID"),
                'property_listing_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Property listing ID"),
                'scheduled_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', description="Scheduled date (YYYY-MM-DD)"),
                'scheduled_time': openapi.Schema(type=openapi.TYPE_STRING, format='time', description="Scheduled time (HH:MM:SS)"),
                'agent_notes': openapi.Schema(type=openapi.TYPE_STRING, description="Optional notes for buyer"),
            }
        ),
        responses={
            201: openapi.Response(description="Showing created successfully"),
            400: "Bad Request - Invalid data",
            403: "Forbidden - Not agent's listing"
        },
        tags=['Agent Showings']
    )
    def post(self, request):
        """Create a new showing schedule"""
        from buyer.models import ShowingSchedule
        from .serializers import AgentCreateShowingSerializer, AgentShowingScheduleSerializer
        from django.utils import timezone
        
        serializer = AgentCreateShowingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        buyer = serializer.validated_data['_buyer']
        listing = serializer.validated_data['_listing']
        
        # Verify listing belongs to this agent
        if listing.agent != request.user:
            return Response(
                {'error': 'You can only create showings for your own listings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create showing schedule (automatically accepted since agent created it)
        showing = ShowingSchedule.objects.create(
            buyer=buyer,
            property_listing=listing,
            requested_date=serializer.validated_data['scheduled_date'],
            preferred_time='afternoon',  # Default, not critical when agent schedules
            status='accepted',  # Automatically accepted
            confirmed_date=serializer.validated_data['scheduled_date'],
            confirmed_time=serializer.validated_data['scheduled_time'],
            agent_response=serializer.validated_data.get('agent_notes', ''),
            responded_at=timezone.now(),
            additional_notes='Scheduled by agent'
        )
        
        response_serializer = AgentShowingScheduleSerializer(showing)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class AgentRescheduleShowingView(views.APIView):
    """
    Agent reschedule showing endpoint
    Agent can change confirmed date/time, status remains 'accepted'
    Buyer receives notification about the reschedule
    """
    permission_classes = [IsAuthenticated, IsAgent]

    @swagger_auto_schema(
        operation_description="Reschedule a showing (agent changes confirmed date/time)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['confirmed_date', 'confirmed_time'],
            properties={
                'confirmed_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='New confirmed date (YYYY-MM-DD)'),
                'confirmed_time': openapi.Schema(type=openapi.TYPE_STRING, format='time', description='New confirmed time (HH:MM:SS)'),
                'agent_response': openapi.Schema(type=openapi.TYPE_STRING, description='Optional notes about rescheduling'),
            }
        ),
        responses={
            200: openapi.Response(description="Showing rescheduled successfully"),
            400: "Bad Request - Validation errors",
            403: "Forbidden - Not your listing",
            404: "Not Found - Showing not found"
        },
        tags=['Agent Showings']
    )
    def patch(self, request, schedule_id):
        """Reschedule showing"""
        from buyer.models import ShowingSchedule
        from .serializers_reschedule import AgentRescheduleShowingSerializer
        from django.utils import timezone

        try:
            showing = ShowingSchedule.objects.select_related('property_listing').get(
                id=schedule_id,
                property_listing__agent=request.user
            )
        except ShowingSchedule.DoesNotExist:
            return Response(
                {'error': 'Showing schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AgentRescheduleShowingSerializer(
            data=request.data,
            context={'showing': showing, 'agent': request.user}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Store old values for tracking changes
        old_date = showing.confirmed_date
        old_time = showing.confirmed_time

        # Update showing with new confirmed date/time
        showing.confirmed_date = serializer.validated_data['confirmed_date']
        showing.confirmed_time = serializer.validated_data['confirmed_time']
        
        if 'agent_response' in serializer.validated_data:
            showing.agent_response = serializer.validated_data['agent_response']

        # Keep status as 'accepted' (agent's decision is final)
        showing.status = 'accepted'
        showing.responded_at = timezone.now()

        # Set flag to indicate this is a reschedule (for signal detection)
        showing._is_rescheduled_by = 'agent'
        showing._old_date = old_date
        showing._old_time = old_time
        
        showing.save()

        from .serializers import AgentShowingScheduleSerializer
        response_serializer = AgentShowingScheduleSerializer(showing)
        
        return Response({
            'message': 'Showing rescheduled successfully. Buyer will be notified.',
            'showing': response_serializer.data
        }, status=status.HTTP_200_OK)


class AgentShowingAgreementDetailView(views.APIView):
    """
    Get showing agreement details for agent's listing
    """
    permission_classes = [IsAuthenticated, IsAgent]
    
    @swagger_auto_schema(
        operation_description="Get showing agreement details for a showing on agent's listing",
        responses={
            200: openapi.Response(description="Agreement details"),
            404: "Not Found - Agreement not found or not for your listing"
        },
        tags=['Agent Showings']
    )
    def get(self, request, schedule_id):
        """Get showing agreement"""
        from buyer.models import ShowingSchedule, ShowingAgreement
        from buyer.serializers import ShowingAgreementResponseSerializer
        
        try:
            schedule = ShowingSchedule.objects.select_related('property_listing').get(
                id=schedule_id,
                property_listing__agent=request.user
            )
            agreement = schedule.agreement
        except ShowingSchedule.DoesNotExist:
            return Response(
                {'error': 'Showing schedule not found or not for your listing'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ShowingAgreement.DoesNotExist:
            return Response(
                {'error': 'No agreement found for this showing'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ShowingAgreementResponseSerializer(agreement)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ================== Agent Agreement Views ==================

class AgentAgreementListView(generics.ListAPIView):
    """
    List all selling agreements uploaded by the authenticated agent.
    Shows all agreements with their current status (accepted, rejected, pending).
    """
    serializer_class = None  # Will be set in get_serializer method
    permission_classes = [IsAuthenticated, IsAgent]

    def get_queryset(self):
        """Return all agreements uploaded by this agent"""
        if getattr(self, 'swagger_fake_view', False):
            return PropertyDocument.objects.none()
        # Get all selling requests created by this agent
        selling_requests = SellingRequest.objects.filter(agent=self.request.user)
        # Get all documents with selling agreements for these requests
        return PropertyDocument.objects.filter(
            selling_request__in=selling_requests,
            selling_agreement_file__isnull=False
        ).exclude(selling_agreement_file='').select_related(
            'selling_request', 'seller'
        ).order_by('-created_at')

    def get_serializer_class(self):
        """Import here to avoid circular imports"""
        from seller.serializers import SellingAgreementDetailedSerializer
        return SellingAgreementDetailedSerializer

    @swagger_auto_schema(
        operation_description="List all selling agreements uploaded by this agent with their current status",
        responses={
            200: openapi.Response(
                description="List of selling agreements with status (accepted/rejected/pending)",
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


class AgentAgreementDetailView(generics.RetrieveAPIView):
    """
    View a specific selling agreement uploaded by the agent.
    Shows all details including agreement_status and seller acceptance info.
    """
    serializer_class = None  # Will be set in get_serializer method
    permission_classes = [IsAuthenticated, IsAgent]
    lookup_field = 'pk'

    def get_queryset(self):
        """Return agreements uploaded by this agent"""
        if getattr(self, 'swagger_fake_view', False):
            return PropertyDocument.objects.none()
        selling_requests = SellingRequest.objects.filter(agent=self.request.user)
        return PropertyDocument.objects.filter(
            selling_request__in=selling_requests,
            selling_agreement_file__isnull=False
        ).exclude(selling_agreement_file='').select_related(
            'selling_request', 'seller'
        )

    def get_serializer_class(self):
        """Import here to avoid circular imports"""
        from seller.serializers import SellingAgreementDetailedSerializer
        return SellingAgreementDetailedSerializer

    @swagger_auto_schema(
        operation_description="View a specific selling agreement with full details including acceptance status",
        responses={
            200: openapi.Response(description="Selling agreement details with agreement_status"),
            401: "Unauthorized",
            404: "Not Found - Agreement not found or not yours"
        }
    )
    def get(self, request, pk, *args, **kwargs):
        try:
            agreement = self.get_queryset().get(pk=pk)
        except PropertyDocument.DoesNotExist:
            return Response(
                {"detail": "Agreement not found or you don't have permission to view it."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(agreement)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ================== Legal Documents Views (GET Only) ==================

@swagger_auto_schema(
    method='get',
    operation_summary="Get Active Agent Privacy Policy",
    operation_description="Get the currently active privacy policy for agents",
    tags=['Agent - Legal Documents'],
    responses={
        200: openapi.Response('Active privacy policy', openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'title': openapi.Schema(type=openapi.TYPE_STRING),
                'content': openapi.Schema(type=openapi.TYPE_STRING),
                'version': openapi.Schema(type=openapi.TYPE_STRING),
                'effective_date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
            }
        )),
        404: 'No active privacy policy found'
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_get_privacy_policy(request):
    """Get the active privacy policy for agents"""
    from superadmin.models import AgentPrivacyPolicy
    from superadmin.serializers import AgentPrivacyPolicySerializer
    
    try:
        policy = AgentPrivacyPolicy.objects.filter(is_active=True).latest('effective_date')
        serializer = AgentPrivacyPolicySerializer(policy)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except AgentPrivacyPolicy.DoesNotExist:
        return Response({'error': 'No active privacy policy found'}, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='get',
    operation_summary="Get Active Agent Terms & Conditions",
    operation_description="Get the currently active terms & conditions for agents",
    tags=['Agent - Legal Documents'],
    responses={
        200: openapi.Response('Active terms & conditions'),
        404: 'No active terms & conditions found'
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_get_terms_conditions(request):
    """Get the active terms & conditions for agents"""
    from superadmin.models import AgentTermsConditions
    from superadmin.serializers import AgentTermsConditionsSerializer
    
    try:
        terms = AgentTermsConditions.objects.filter(is_active=True).latest('effective_date')
        serializer = AgentTermsConditionsSerializer(terms)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except AgentTermsConditions.DoesNotExist:
        return Response({'error': 'No active terms & conditions found'}, status=status.HTTP_404_NOT_FOUND)

