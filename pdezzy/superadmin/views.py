from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, 
    HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_204_NO_CONTENT
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from agent.models import Agent, PropertyListing
from seller.models import Seller, PropertyDocument, SellingRequest
from buyer.models import Buyer, ShowingAgreement, ShowingSchedule, BuyerDocument
from datetime import datetime, timedelta
from django.db.models import Q, Value
from django.db.models.functions import Concat


def get_dashboard_data():
    """Helper function to get all dashboard statistics"""
    total_agents = Agent.objects.count()
    total_sellers = Seller.objects.count()
    total_buyers = Buyer.objects.count()
    total_users = total_agents + total_sellers + total_buyers
    total_listings = PropertyListing.objects.count()
    
    # Active users (is_active=True)
    active_agents = Agent.objects.filter(is_active=True).count()
    active_sellers = Seller.objects.filter(is_active=True).count()
    
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
    
    return {
        'total_users': total_users,
        'total_agents': total_agents,
        'total_sellers': total_sellers,
        'total_buyers': total_buyers,
        'total_listings': total_listings,
        'active_agents': active_agents,
        'active_sellers': active_sellers,
        'weekly_chart': weekly_data,
    }


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description='Dashboard data retrieved successfully (requires authentication)',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'total_users': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total users (Agents + Sellers + Buyers)'),
                    'total_agents': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total agents'),
                    'total_sellers': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total sellers'),
                    'total_buyers': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total buyers'),
                    'total_listings': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total property listings'),
                    'active_agents': openapi.Schema(type=openapi.TYPE_INTEGER, description='Agents active in last 30 days'),
                    'active_sellers': openapi.Schema(type=openapi.TYPE_INTEGER, description='Sellers active in last 30 days'),
                    'weekly_chart': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'day': openapi.Schema(type=openapi.TYPE_STRING, description='Day of week'),
                                'active': openapi.Schema(type=openapi.TYPE_INTEGER, description='Active users'),
                                'new': openapi.Schema(type=openapi.TYPE_INTEGER, description='New registrations'),
                            }
                        ),
                        description='Weekly user registration data'
                    ),
                }
            )
        ),
        401: openapi.Response(description='Unauthorized - Bearer token required'),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard_data(request):
    """
    Get Admin Dashboard Data (Protected)
    
    **Requires Authentication**: Bearer token in Authorization header
    
    **Authorization Header Example:**
    ```
    Authorization: Bearer <access_token>
    ```
    
    **Returns:**
    - total_users: All users (Agents + Sellers + Buyers)
    - total_agents: Number of agents
    - total_sellers: Number of sellers
    - total_buyers: Number of buyers
    - total_listings: All property listings
    - active_agents: Agents active in last 30 days
    - active_sellers: Sellers active in last 30 days
    - weekly_chart: 7-day user registration chart with:
      - day: Day name (Mon-Sun)
      - active: Total users that day
      - new: New registrations that day
    
    **How to use:**
    1. Login with `/api/v1/admin/login/` to get access token
    2. Use the access token in the Authorization header
    3. Call this endpoint to get dashboard data
    """
    dashboard_data = get_dashboard_data()
    return Response(dashboard_data, status=HTTP_200_OK)


# ==================== USER MANAGEMENT ENDPOINTS ====================

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('user_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                         description='Filter by user type: agent, seller, buyer (optional)'),
        openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                         description='Search by first name, last name, or email (optional)'),
    ],
    responses={
        200: openapi.Response(
            description='List of all users',
            schema=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'username': openapi.Schema(type=openapi.TYPE_STRING),
                        'email': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_type': openapi.Schema(type=openapi.TYPE_STRING),
                        'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'date_joined': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        ),
        401: openapi.Response(description='Unauthorized'),
    }
)
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email address'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password'),
            'user_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['agent', 'seller', 'buyer'], description='User type'),
            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name (optional)'),
            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name (optional)'),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number (optional)'),
        },
        required=['username', 'email', 'password', 'user_type'],
    ),
    responses={
        201: openapi.Response(
            description='User created successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'user': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'username': openapi.Schema(type=openapi.TYPE_STRING),
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'user_type': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            )
        ),
        400: openapi.Response(description='Bad request'),
    }
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def admin_list_users(request):
    """
    List all users or create a new user
    
    **GET**: List all users (Agents, Sellers, Buyers)
    - Supports filtering by user_type and searching by first name, last name, or email
    
    **POST**: Create a new user
    - Requires: username, email, password, user_type
    - Optional: first_name, last_name, phone_number
    """
    if request.method == 'POST':
        # Validate required fields for creation
        required_fields = ['username', 'email', 'password', 'user_type']
        for field in required_fields:
            if field not in request.data:
                return Response(
                    {'error': f'{field} is required'},
                    status=HTTP_400_BAD_REQUEST
                )
        
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        user_type = request.data.get('user_type', '').lower()
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        phone_number = request.data.get('phone_number', '')
        
        # Validate user_type
        if user_type not in ['agent', 'seller', 'buyer']:
            return Response(
                {'error': 'user_type must be agent, seller, or buyer'},
                status=HTTP_400_BAD_REQUEST
            )
        
        # Check if username already exists
        if user_type == 'agent' and Agent.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=HTTP_400_BAD_REQUEST)
        elif user_type == 'seller' and Seller.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=HTTP_400_BAD_REQUEST)
        elif user_type == 'buyer' and Buyer.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=HTTP_400_BAD_REQUEST)
        
        # Check if email already exists
        if user_type == 'agent' and Agent.objects.filter(email=email).exists():
            return Response({'error': 'Email already exists'}, status=HTTP_400_BAD_REQUEST)
        elif user_type == 'seller' and Seller.objects.filter(email=email).exists():
            return Response({'error': 'Email already exists'}, status=HTTP_400_BAD_REQUEST)
        elif user_type == 'buyer' and Buyer.objects.filter(email=email).exists():
            return Response({'error': 'Email already exists'}, status=HTTP_400_BAD_REQUEST)
        
        try:
            # Create user based on type
            if user_type == 'agent':
                user = Agent.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                if phone_number:
                    user.phone_number = phone_number
                    user.save()
            
            elif user_type == 'seller':
                user = Seller.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                if phone_number:
                    user.phone_number = phone_number
                    user.save()
            
            elif user_type == 'buyer':
                user = Buyer.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                if phone_number:
                    user.phone_number = phone_number
                    user.save()
            
            return Response({
                'message': f'{user_type.capitalize()} user created successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'user_type': user_type,
                }
            }, status=HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=HTTP_400_BAD_REQUEST
            )
    
    # GET method - List users
    user_type = request.query_params.get('user_type', '').lower()
    search = request.query_params.get('search', '').strip()
    
    users_list = []
    
    # Get agents
    if not user_type or user_type == 'agent':
        agents = Agent.objects.all()
        if search:
            agents = agents.filter(
                Q(first_name__icontains=search) | 
                Q(last_name__icontains=search) | 
                Q(email__icontains=search)
            )
        for agent in agents:
            users_list.append({
                'id': agent.id,
                'username': agent.username,
                'email': agent.email,
                'user_type': 'agent',
                'is_active': agent.is_active,
                'date_joined': agent.date_joined.isoformat(),
            })
    
    # Get sellers
    if not user_type or user_type == 'seller':
        sellers = Seller.objects.all()
        if search:
            sellers = sellers.filter(
                Q(first_name__icontains=search) | 
                Q(last_name__icontains=search) | 
                Q(email__icontains=search)
            )
        for seller in sellers:
            users_list.append({
                'id': seller.id,
                'username': seller.username,
                'email': seller.email,
                'user_type': 'seller',
                'is_active': seller.is_active,
                'date_joined': seller.date_joined.isoformat(),
            })
    
    # Get buyers
    if not user_type or user_type == 'buyer':
        buyers = Buyer.objects.all()
        if search:
            buyers = buyers.filter(
                Q(first_name__icontains=search) | 
                Q(last_name__icontains=search) | 
                Q(email__icontains=search)
            )
        for buyer in buyers:
            users_list.append({
                'id': buyer.id,
                'username': buyer.username,
                'email': buyer.email,
                'user_type': 'buyer',
                'is_active': buyer.is_active,
                'date_joined': buyer.date_joined.isoformat(),
            })
    
    return Response(users_list, status=HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('user_type', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                         description='User type: agent, seller, or buyer', required=True),
    ],
    responses={
        200: openapi.Response(
            description='User details',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'username': openapi.Schema(type=openapi.TYPE_STRING),
                    'email': openapi.Schema(type=openapi.TYPE_STRING),
                    'first_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'last_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'user_type': openapi.Schema(type=openapi.TYPE_STRING),
                    'date_joined': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        404: openapi.Response(description='User not found'),
    }
)
@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def admin_get_user(request, user_id):
    """
    Get complete user details with all information (GET) or delete user (DELETE)
    
    **Requires Authentication**: Bearer token
    
    **Parameters:**
    - user_id: ID of the user
    - user_type (query): 'agent', 'seller', or 'buyer'
    
    **GET Response includes:**
    - Basic info (id, username, email, first_name, last_name)
    - Contact (phone_number)
    - Profile image/picture
    - Location/Address info
    - User type specific fields
    - Account status (is_active, date_joined)
    - Metadata (created_at, updated_at)
    
    **DELETE Response:**
    - Success message
    
    **Example:**
    ```
    GET /api/v1/admin/users/6/?user_type=agent
    DELETE /api/v1/admin/users/6/?user_type=agent
    ```
    """
    user_type = request.query_params.get('user_type', '').lower()
    
    if not user_type:
        return Response({'error': 'user_type query parameter required'}, status=HTTP_400_BAD_REQUEST)
    
    # Handle DELETE request
    if request.method == 'DELETE':
        try:
            if user_type == 'agent':
                user = Agent.objects.get(id=user_id)
            elif user_type == 'seller':
                user = Seller.objects.get(id=user_id)
            elif user_type == 'buyer':
                user = Buyer.objects.get(id=user_id)
            else:
                return Response({'error': 'Invalid user_type'}, status=HTTP_400_BAD_REQUEST)
            
            username = user.username
            user.delete()
            
            return Response(
                {
                    'message': f'{user_type.capitalize()} "{username}" deleted successfully',
                    'deleted_user_id': user_id,
                    'user_type': user_type
                },
                status=HTTP_204_NO_CONTENT
            )
        
        except Agent.DoesNotExist:
            return Response({'error': 'Agent not found'}, status=HTTP_404_NOT_FOUND)
        except Seller.DoesNotExist:
            return Response({'error': 'Seller not found'}, status=HTTP_404_NOT_FOUND)
        except Buyer.DoesNotExist:
            return Response({'error': 'Buyer not found'}, status=HTTP_404_NOT_FOUND)
    
    # Handle GET request
    try:
        if user_type == 'agent':
            user = Agent.objects.get(id=user_id)
            profile_pic = user.profile_picture.url if user.profile_picture else None
            profile_pic_full = request.build_absolute_uri(profile_pic) if profile_pic else None
            
            user_data = {
                # Basic Information
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': f"{user.first_name} {user.last_name}".strip(),
                
                # Contact Information
                'phone_number': user.phone_number or '',
                
                # Profile Picture
                'profile_picture': profile_pic,
                'profile_picture_url': profile_pic_full,
                
                # Professional Information
                'license_number': user.license_number or '',
                'company_details': user.company_details or '',
                'years_of_experience': user.years_of_experience,
                'area_of_expertise': user.area_of_expertise or '',
                'about': user.about or '',
                
                # Languages & Service Areas
                'languages': user.languages or [],
                'service_areas': user.service_areas or [],
                'property_types': user.property_types or [],
                
                # Availability
                'availability': user.availability or '',
                
                # Agent Papers
                'agent_papers': user.agent_papers.url if user.agent_papers else None,
                'agent_papers_url': request.build_absolute_uri(user.agent_papers.url) if user.agent_papers else None,
                
                # Account Status
                'is_active': user.is_active,
                'user_type': 'agent',
                
                # Timestamps
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') else None,
                'updated_at': user.updated_at.isoformat() if hasattr(user, 'updated_at') else None,
            }
        
        elif user_type == 'seller':
            user = Seller.objects.get(id=user_id)
            profile_pic = user.profile_image.url if user.profile_image else None
            profile_pic_full = request.build_absolute_uri(profile_pic) if profile_pic else None
            
            user_data = {
                # Basic Information
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': f"{user.first_name} {user.last_name}".strip(),
                
                # Contact Information
                'phone_number': user.phone_number or '',
                
                # Profile Picture
                'profile_image': profile_pic,
                'profile_image_url': profile_pic_full,
                
                # Location & Property Information
                'location': user.location or '',
                'bedrooms': user.bedrooms,
                'bathrooms': user.bathrooms,
                'property_condition': user.property_condition or '',
                
                # Account Status
                'is_active': user.is_active,
                'user_type': 'seller',
                
                # Timestamps
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') else None,
                'updated_at': user.updated_at.isoformat() if hasattr(user, 'updated_at') else None,
            }
        
        elif user_type == 'buyer':
            user = Buyer.objects.get(id=user_id)
            profile_pic = user.profile_image.url if user.profile_image else None
            profile_pic_full = request.build_absolute_uri(profile_pic) if profile_pic else None
            mortgage = user.mortgage_letter.url if user.mortgage_letter else None
            mortgage_full = request.build_absolute_uri(mortgage) if mortgage else None
            
            user_data = {
                # Basic Information
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': f"{user.first_name} {user.last_name}".strip(),
                
                # Contact Information
                'phone_number': user.phone_number or '',
                
                # Profile Picture
                'profile_image': profile_pic,
                'profile_image_url': profile_pic_full,
                
                # Buying Preferences
                'price_range': user.price_range or '',
                'location': user.location or '',
                'bedrooms': user.bedrooms,
                'bathrooms': user.bathrooms,
                
                # Documents
                'mortgage_letter': mortgage,
                'mortgage_letter_url': mortgage_full,
                
                # Account Status
                'is_active': user.is_active,
                'user_type': 'buyer',
                
                # Timestamps
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') else None,
                'updated_at': user.updated_at.isoformat() if hasattr(user, 'updated_at') else None,
            }
        
        else:
            return Response({'error': 'Invalid user_type'}, status=HTTP_400_BAD_REQUEST)
        
        return Response(user_data, status=HTTP_200_OK)
    
    except Agent.DoesNotExist:
        return Response({'error': 'Agent not found'}, status=HTTP_404_NOT_FOUND)
    except Seller.DoesNotExist:
        return Response({'error': 'Seller not found'}, status=HTTP_404_NOT_FOUND)
    except Buyer.DoesNotExist:
        return Response({'error': 'Buyer not found'}, status=HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='patch',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'first_name': openapi.Schema(type=openapi.TYPE_STRING),
            'last_name': openapi.Schema(type=openapi.TYPE_STRING),
            'email': openapi.Schema(type=openapi.TYPE_STRING),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
        }
    ),
    responses={
        200: openapi.Response(description='User updated successfully'),
        404: openapi.Response(description='User not found'),
    }
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_update_user(request, user_id):
    """
    Update user information
    
    **Requires Authentication**: Bearer token
    
    **Parameters:**
    - user_id: ID of the user
    - user_type (query): 'agent', 'seller', or 'buyer'
    
    **Body Example:**
    ```json
    {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "is_active": true
    }
    ```
    """
    user_type = request.query_params.get('user_type', '').lower()
    
    if not user_type:
        return Response({'error': 'user_type query parameter required'}, status=HTTP_400_BAD_REQUEST)
    
    try:
        if user_type == 'agent':
            user = Agent.objects.get(id=user_id)
        elif user_type == 'seller':
            user = Seller.objects.get(id=user_id)
        elif user_type == 'buyer':
            user = Buyer.objects.get(id=user_id)
        else:
            return Response({'error': 'Invalid user_type'}, status=HTTP_400_BAD_REQUEST)
        
        # Update fields
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        if 'email' in request.data:
            user.email = request.data['email']
        if 'is_active' in request.data:
            user.is_active = request.data['is_active']
        if 'phone_number' in request.data and hasattr(user, 'phone_number'):
            user.phone_number = request.data['phone_number']
        
        user.save()
        
        return Response({
            'message': 'User updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
            }
        }, status=HTTP_200_OK)
    
    except (Agent.DoesNotExist, Seller.DoesNotExist, Buyer.DoesNotExist):
        return Response({'error': 'User not found'}, status=HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='delete',
    responses={
        204: openapi.Response(description='User deleted successfully'),
        404: openapi.Response(description='User not found'),
    }
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_delete_user(request, user_id):
    """
    Delete a user (Deactivate or Hard Delete)
    
    **Requires Authentication**: Bearer token
    
    **Parameters:**
    - user_id: ID of the user
    - user_type (query): 'agent', 'seller', or 'buyer'
    
    **Example:**
    ```
    DELETE /api/v1/admin/users/5/?user_type=agent
    ```
    """
    user_type = request.query_params.get('user_type', '').lower()
    
    if not user_type:
        return Response({'error': 'user_type query parameter required'}, status=HTTP_400_BAD_REQUEST)
    
    try:
        if user_type == 'agent':
            user = Agent.objects.get(id=user_id)
        elif user_type == 'seller':
            user = Seller.objects.get(id=user_id)
        elif user_type == 'buyer':
            user = Buyer.objects.get(id=user_id)
        else:
            return Response({'error': 'Invalid user_type'}, status=HTTP_400_BAD_REQUEST)
        
        username = user.username
        user.delete()
        
        return Response({
            'message': f'User {username} deleted successfully'
        }, status=HTTP_204_NO_CONTENT)
    
    except (Agent.DoesNotExist, Seller.DoesNotExist, Buyer.DoesNotExist):
        return Response({'error': 'User not found'}, status=HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='Admin username'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='Admin password'),
        },
        required=['username', 'password']
    ),
    responses={
        200: openapi.Response(
            description='Login successful with dashboard data',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token'),
                    'access': openapi.Schema(type=openapi.TYPE_STRING, description='Access token (Bearer)'),
                    'user': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'username': openapi.Schema(type=openapi.TYPE_STRING),
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                            'is_superuser': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        }
                    ),
                    'dashboard': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'total_users': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total users (Agents + Sellers + Buyers)'),
                            'total_agents': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total agents'),
                            'total_sellers': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total sellers'),
                            'total_buyers': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total buyers'),
                            'total_listings': openapi.Schema(type=openapi.TYPE_INTEGER, description='Total property listings'),
                            'active_agents': openapi.Schema(type=openapi.TYPE_INTEGER, description='Agents active in last 30 days'),
                            'active_sellers': openapi.Schema(type=openapi.TYPE_INTEGER, description='Sellers active in last 30 days'),
                            'weekly_chart': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'day': openapi.Schema(type=openapi.TYPE_STRING, description='Day of week (Mon-Sun)'),
                                        'active': openapi.Schema(type=openapi.TYPE_INTEGER, description='Active users for that day'),
                                        'new': openapi.Schema(type=openapi.TYPE_INTEGER, description='New registrations for that day'),
                                    }
                                ),
                                description='Weekly user registration data for last 7 days'
                            ),
                        }
                    ),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        401: openapi.Response(description='Invalid credentials or insufficient permissions'),
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """
    Admin Dashboard Login API with Statistics
    
    Authenticate as admin/superuser and get JWT tokens + dashboard statistics.
    
    **Returns:**
    - **refresh**: Use to get a new access token when it expires
    - **access**: JWT token for API authentication (Bearer token)
    - **dashboard**: Complete statistics:
      - total_users: All users (Agents + Sellers + Buyers)
      - total_agents: Number of agents
      - total_sellers: Number of sellers
      - total_buyers: Number of buyers
      - total_listings: Number of property listings
      - active_agents: Agents active in last 30 days
      - active_sellers: Sellers active in last 30 days
    
    **Usage:**
    
    1. Login and get tokens:
    ```
    POST /api/v1/admin/login/
    {
      "username": "admin",
      "password": "password123"
    }
    ```
    
    2. Use access token in API requests:
    ```
    Authorization: Bearer <access_token>
    ```
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=HTTP_401_UNAUTHORIZED
        )
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response(
            {'error': 'Invalid credentials'},
            status=HTTP_401_UNAUTHORIZED
        )
    
    if not (user.is_superuser or user.is_staff):
        return Response(
            {'error': 'Admin access required'},
            status=HTTP_401_UNAUTHORIZED
        )
    
    refresh = RefreshToken.for_user(user)
    dashboard_data = get_dashboard_data()
    
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_superuser': user.is_superuser,
        },
        'dashboard': dashboard_data,
        'message': 'Login successful. Use the access token in Authorization header.'
    }, status=HTTP_200_OK)


# ==================== ADMIN PROFILE ENDPOINTS ====================

@swagger_auto_schema(
    method='get',
    operation_summary="Get Admin Profile",
    operation_description="Retrieve authenticated admin's profile information including profile image",
    tags=['Superadmin - Profile'],
    responses={
        200: openapi.Response(
            description='Admin profile information',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'username': openapi.Schema(type=openapi.TYPE_STRING),
                    'email': openapi.Schema(type=openapi.TYPE_STRING),
                    'first_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'last_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                    'profile_image': openapi.Schema(type=openapi.TYPE_STRING, format='uri', description='Profile image URL'),
                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'is_superuser': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'is_staff': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'date_joined': openapi.Schema(type=openapi.TYPE_STRING),
                    'user_type': openapi.Schema(type=openapi.TYPE_STRING, description='User role: agent, seller, buyer, or null for superadmin'),
                }
            )
        ),
        401: openapi.Response(description='Unauthorized'),
    }
)
@swagger_auto_schema(
    method='patch',
    operation_summary="Update Admin Profile",
    operation_description="Update authenticated admin's profile information including password change and profile image upload. All fields are optional. Use multipart/form-data for file uploads.",
    tags=['Superadmin - Profile'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name'),
            'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name'),
            'email': openapi.Schema(type=openapi.TYPE_STRING, format='email', description='Email address'),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number'),
            'profile_picture': openapi.Schema(type=openapi.TYPE_STRING, format='binary', description='Profile picture image (JPG/PNG, max 5MB)'),
            'current_password': openapi.Schema(type=openapi.TYPE_STRING, description='Current password (required for password change)'),
            'new_password': openapi.Schema(type=openapi.TYPE_STRING, description='New password (minimum 6 characters)'),
            'confirm_password': openapi.Schema(type=openapi.TYPE_STRING, description='Confirm new password (must match new_password)'),
        }
    ),
    responses={
        200: openapi.Response(
            description='Profile updated successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example='Profile and password updated successfully'),
                    'profile': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                            'username': openapi.Schema(type=openapi.TYPE_STRING, example='admin'),
                            'email': openapi.Schema(type=openapi.TYPE_STRING, example='admin@pdezzy.com'),
                            'first_name': openapi.Schema(type=openapi.TYPE_STRING, example='Admin'),
                            'last_name': openapi.Schema(type=openapi.TYPE_STRING, example='User'),
                            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, example='+91 22 014'),
                            'profile_image': openapi.Schema(type=openapi.TYPE_STRING, format='uri', example='http://10.10.13.27:8005/media/profile_pictures/admin_photo.jpg'),
                        }
                    )
                }
            )
        ),
        400: openapi.Response(description='Bad request - validation error (email in use, file too large, password mismatch, etc.)'),
        401: openapi.Response(description='Unauthorized - authentication token required or invalid'),
    }
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def admin_profile(request):
    """
    Get or update admin's own profile
    
    **GET**: Retrieve authenticated admin's profile information
    
    **PATCH**: Update authenticated admin's profile
    - Optional fields: first_name, last_name, email, phone_number
    
    **Requires Authentication**: Bearer token
    
    **GET Examples:**
    ```
    GET /api/v1/admin/profile/
    ```
    
    **PATCH Examples:**
    ```
    PATCH /api/v1/admin/profile/
    
    // Form-data for file upload (multipart/form-data):
    - first_name: "John"
    - last_name: "Doe"
    - email: "john.doe@example.com"
    - phone_number: "+1234567890"
    - profile_picture: <file>
    - current_password: "oldpass"
    - new_password: "newpass123"
    - confirm_password: "newpass123"
    ```
    """
    # GET method - Retrieve profile
    if request.method == 'GET':
        user = request.user
        
        # Get profile image URL (full URL)
        profile_image_url = None
        if hasattr(user, 'profile_picture') and user.profile_picture:
            profile_image_url = request.build_absolute_uri(user.profile_picture.url)
        elif hasattr(user, 'profile_image') and user.profile_image:
            profile_image_url = request.build_absolute_uri(user.profile_image.url)
        
        # Prepare response based on user type
        user_type = None
        if isinstance(user, Agent):
            user_type = 'agent'
        elif isinstance(user, Seller):
            user_type = 'seller'
        elif isinstance(user, Buyer):
            user_type = 'buyer'
        
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': getattr(user, 'phone_number', ''),
            'profile_image': profile_image_url,
            'is_active': user.is_active,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'date_joined': user.date_joined.isoformat(),
            'user_type': user_type,
        }, status=HTTP_200_OK)
    
    # PATCH method - Update profile
    if request.method == 'PATCH':
        user = request.user
        
        # Get fields to update
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        email = request.data.get('email')
        phone_number = request.data.get('phone_number')
        profile_picture = request.FILES.get('profile_picture')
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        # Handle password change if provided
        if current_password or new_password:
            # All password fields must be provided
            if not all([current_password, new_password, confirm_password]):
                return Response(
                    {'error': 'Current password, new password, and confirm password are all required for password change'},
                    status=HTTP_400_BAD_REQUEST
                )
            
            # Verify current password
            if not user.check_password(current_password):
                return Response(
                    {'error': 'Current password is incorrect'},
                    status=HTTP_400_BAD_REQUEST
                )
            
            # Verify new passwords match
            if new_password != confirm_password:
                return Response(
                    {'error': 'New password and confirm password do not match'},
                    status=HTTP_400_BAD_REQUEST
                )
            
            # Validate password strength (minimum 6 characters)
            if len(new_password) < 6:
                return Response(
                    {'error': 'Password must be at least 6 characters long'},
                    status=HTTP_400_BAD_REQUEST
                )
            
            # Set new password
            user.set_password(new_password)
        
        # Validate email if provided
        if email:
            # Check if email is already used by another user of same type
            user_class = user.__class__
            if user_class.objects.filter(email=email).exclude(id=user.id).exists():
                return Response(
                    {'error': 'Email already in use'},
                    status=HTTP_400_BAD_REQUEST
                )
            user.email = email
        
        # Update fields
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if phone_number is not None:
            user.phone_number = phone_number
        
        # Handle profile picture upload
        if profile_picture:
            # Validate file size (max 5MB)
            if profile_picture.size > 5 * 1024 * 1024:
                return Response(
                    {'error': 'Profile picture size must not exceed 5MB'},
                    status=HTTP_400_BAD_REQUEST
                )
            
            # Set the profile picture based on user type
            if hasattr(user, 'profile_picture'):
                user.profile_picture = profile_picture
            elif hasattr(user, 'profile_image'):
                user.profile_image = profile_picture
        
        try:
            user.save()
            
            # Get updated profile image URL (full URL)
            profile_image_url = None
            if hasattr(user, 'profile_picture') and user.profile_picture:
                profile_image_url = request.build_absolute_uri(user.profile_picture.url)
            elif hasattr(user, 'profile_image') and user.profile_image:
                profile_image_url = request.build_absolute_uri(user.profile_image.url)
            
            response_message = 'Profile updated successfully'
            if current_password and new_password:
                response_message = 'Profile and password updated successfully'
            
            return Response({
                'message': response_message,
                'profile': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone_number': user.phone_number,
                    'profile_image': profile_image_url,
                }
            }, status=HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=HTTP_400_BAD_REQUEST
            )


# ==================== PROPERTY LISTING MANAGEMENT ENDPOINTS ====================

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                         description='Search by title, address, or agent name (optional)'),
        openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                         description='Filter by status: draft, pending, published, sold, archived (optional)'),
        openapi.Parameter('agent_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, 
                         description='Filter by agent ID (optional)'),
    ],
    responses={
        200: openapi.Response(
            description='List of all property listings',
            schema=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_STRING),
                        'title': openapi.Schema(type=openapi.TYPE_STRING),
                        'location': openapi.Schema(type=openapi.TYPE_STRING),
                        'price': openapi.Schema(type=openapi.TYPE_STRING),
                        'details': openapi.Schema(type=openapi.TYPE_STRING),
                        'agent': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        ),
        401: openapi.Response(description='Unauthorized'),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_list_property_listings(request):
    """
    List all property listings with optional filters
    
    **Requires Authentication**: Bearer token
    
    **Query Parameters:**
    - search: Search in title, address, or agent name
    - status: Filter by listing status
    - agent_id: Filter by specific agent
    
    **Returns:** Array of property listings with details
    """
    # Get query parameters
    search = request.query_params.get('search', '').strip()
    status_filter = request.query_params.get('status', '').strip().lower()
    agent_id = request.query_params.get('agent_id', '').strip()
    
    # Start with all listings
    listings = PropertyListing.objects.all().select_related('agent', 'property_document')
    
    # Apply filters
    if search:
        listings = listings.filter(
            Q(title__icontains=search) |
            Q(street_address__icontains=search) |
            Q(city__icontains=search) |
            Q(agent__username__icontains=search) |
            Q(agent__first_name__icontains=search) |
            Q(agent__last_name__icontains=search)
        )
    
    if status_filter:
        listings = listings.filter(status=status_filter)
    
    if agent_id:
        try:
            listings = listings.filter(agent_id=int(agent_id))
        except ValueError:
            pass
    
    # Build response
    listings_data = []
    for listing in listings:
        # Get photos with details
        photos = []
        for photo in listing.photos.all():
            photo_url = request.build_absolute_uri(photo.photo.url) if photo.photo else None
            photos.append({
                'id': photo.id,
                'url': photo_url,
                'caption': photo.caption,
                'is_primary': photo.is_primary,
                'order': photo.order,
                'file_size': photo.file_size,
                'created_at': photo.created_at.isoformat(),
            })
        
        # Get documents with details
        documents = []
        for doc in listing.listing_documents.all():
            doc_url = request.build_absolute_uri(doc.document.url) if doc.document else None
            documents.append({
                'id': doc.id,
                'title': doc.title,
                'document_type': doc.document_type,
                'url': doc_url,
                'file_size': doc.file_size,
                'created_at': doc.created_at.isoformat(),
            })
        
        listings_data.append({
            'id': listing.id,
            'title': listing.title,
            'street_address': listing.street_address,
            'city': listing.city,
            'state': listing.state,
            'zip_code': listing.zip_code,
            'property_type': listing.property_type,
            'bedrooms': listing.bedrooms,
            'bathrooms': str(listing.bathrooms) if listing.bathrooms else '0.0',
            'square_feet': listing.square_feet,
            'description': listing.description,
            'price': str(listing.price),
            'status': listing.status,
            'photos': photos,
            'documents': documents,
            'created_at': listing.created_at.isoformat(),
            'updated_at': listing.updated_at.isoformat(),
        })
    
    return Response(listings_data, status=HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description='Property listing details',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'title': openapi.Schema(type=openapi.TYPE_STRING),
                    'street_address': openapi.Schema(type=openapi.TYPE_STRING),
                    'city': openapi.Schema(type=openapi.TYPE_STRING),
                    'state': openapi.Schema(type=openapi.TYPE_STRING),
                    'zip_code': openapi.Schema(type=openapi.TYPE_STRING),
                    'property_type': openapi.Schema(type=openapi.TYPE_STRING),
                    'bedrooms': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'bathrooms': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'square_feet': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                    'price': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'agent': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'photos': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                    'documents': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                }
            )
        ),
        404: openapi.Response(description='Listing not found'),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_get_property_listing(request, listing_id):
    """
    Get detailed information about a specific property listing
    
    **Requires Authentication**: Bearer token
    
    **Parameters:**
    - listing_id: ID of the property listing
    
    **Returns:** Detailed listing information with photos and documents
    """
    try:
        listing = PropertyListing.objects.select_related('agent', 'property_document').get(id=listing_id)
    except PropertyListing.DoesNotExist:
        return Response({'error': 'Listing not found'}, status=HTTP_404_NOT_FOUND)
    
    # Get photos
    photos = []
    for photo in listing.photos.all():
        photos.append({
            'id': photo.id,
            'url': photo.photo.url if photo.photo else None,
            'caption': photo.caption,
            'is_primary': photo.is_primary,
        })
    
    # Get documents
    documents = []
    for doc in listing.listing_documents.all():
        documents.append({
            'id': doc.id,
            'title': doc.title,
            'document_type': doc.document_type,
            'url': doc.document.url if doc.document else None,
        })
    
    # Agent info
    agent = listing.agent
    agent_info = {
        'id': agent.id,
        'username': agent.username,
        'full_name': f"{agent.first_name} {agent.last_name}".strip() or agent.username,
        'email': agent.email,
        'phone_number': agent.phone_number,
        'license_number': agent.license_number,
    }
    
    # Build response
    listing_data = {
        'id': listing.id,
        'title': listing.title,
        'street_address': listing.street_address,
        'city': listing.city,
        'state': listing.state,
        'zip_code': listing.zip_code,
        'property_type': listing.property_type,
        'bedrooms': listing.bedrooms,
        'bathrooms': float(listing.bathrooms) if listing.bathrooms else None,
        'square_feet': listing.square_feet,
        'description': listing.description,
        'price': float(listing.price),
        'status': listing.status,
        'agent': agent_info,
        'photos': photos,
        'documents': documents,
        'created_at': listing.created_at.isoformat(),
        'updated_at': listing.updated_at.isoformat(),
        'published_at': listing.published_at.isoformat() if listing.published_at else None,
    }
    
    return Response(listing_data, status=HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['agent_id', 'title', 'street_address', 'city', 'state', 'zip_code', 'price'],
        properties={
            'agent_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Agent ID'),
            'title': openapi.Schema(type=openapi.TYPE_STRING, description='Property title'),
            'street_address': openapi.Schema(type=openapi.TYPE_STRING, description='Street address'),
            'city': openapi.Schema(type=openapi.TYPE_STRING, description='City'),
            'state': openapi.Schema(type=openapi.TYPE_STRING, description='State'),
            'zip_code': openapi.Schema(type=openapi.TYPE_STRING, description='ZIP code'),
            'property_type': openapi.Schema(type=openapi.TYPE_STRING, description='Property type (house, apartment, etc.)'),
            'bedrooms': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of bedrooms'),
            'bathrooms': openapi.Schema(type=openapi.TYPE_NUMBER, description='Number of bathrooms'),
            'square_feet': openapi.Schema(type=openapi.TYPE_INTEGER, description='Square footage'),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description='Property description'),
            'price': openapi.Schema(type=openapi.TYPE_NUMBER, description='Listing price'),
            'status': openapi.Schema(type=openapi.TYPE_STRING, description='Status (draft, published, etc.)'),
        }
    ),
    responses={
        201: openapi.Response(
            description='Listing created successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'listing': openapi.Schema(type=openapi.TYPE_OBJECT),
                }
            )
        ),
        400: openapi.Response(description='Bad request'),
        404: openapi.Response(description='Agent not found'),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_create_property_listing(request):
    """
    Create a new property listing (admin only)
    
    **Requires Authentication**: Bearer token
    
    **Required Fields:**
    - agent_id: ID of the agent who will manage the listing
    - title: Property title
    - street_address: Street address
    - city: City
    - state: State
    - zip_code: ZIP code
    - price: Listing price
    
    **Optional Fields:**
    - property_type: Type of property (default: 'house')
    - bedrooms: Number of bedrooms
    - bathrooms: Number of bathrooms
    - square_feet: Square footage
    - description: Property description
    - status: Listing status (default: 'draft')
    
    **Returns:** Created listing data
    """
    # Validate required fields
    required_fields = ['agent_id', 'title', 'street_address', 'city', 'state', 'zip_code', 'price']
    for field in required_fields:
        if field not in request.data:
            return Response({'error': f'{field} is required'}, status=HTTP_400_BAD_REQUEST)
    
    # Get agent
    agent_id = request.data.get('agent_id')
    try:
        agent = Agent.objects.get(id=agent_id)
    except Agent.DoesNotExist:
        return Response({'error': 'Agent not found'}, status=HTTP_404_NOT_FOUND)
    
    # Note: Creating listing without property_document (admin override)
    # In production, you might want to create a dummy property document or handle this differently
    try:
        listing = PropertyListing.objects.create(
            agent=agent,
            property_document=None,  # Admin can create without document
            title=request.data.get('title'),
            street_address=request.data.get('street_address'),
            city=request.data.get('city'),
            state=request.data.get('state'),
            zip_code=request.data.get('zip_code'),
            property_type=request.data.get('property_type', 'house'),
            bedrooms=request.data.get('bedrooms'),
            bathrooms=request.data.get('bathrooms'),
            square_feet=request.data.get('square_feet'),
            description=request.data.get('description', ''),
            price=request.data.get('price'),
            status=request.data.get('status', 'draft'),
        )
        
        return Response({
            'message': 'Property listing created successfully',
            'listing': {
                'id': listing.id,
                'title': listing.title,
                'address': f"{listing.street_address}, {listing.city}, {listing.state} {listing.zip_code}",
                'price': float(listing.price),
                'status': listing.status,
                'agent': {
                    'id': agent.id,
                    'username': agent.username,
                }
            }
        }, status=HTTP_201_CREATED)
    
    except Exception as e:
        return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='delete',
    responses={
        204: openapi.Response(description='Listing deleted successfully'),
        404: openapi.Response(description='Listing not found'),
    }
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_delete_property_listing(request, listing_id):
    """
    Delete a property listing
    
    **Requires Authentication**: Bearer token
    
    **Parameters:**
    - listing_id: ID of the property listing to delete
    
    **Returns:** Success message
    
    **Note:** This will permanently delete the listing and all associated photos and documents
    """
    try:
        listing = PropertyListing.objects.get(id=listing_id)
        listing_title = listing.title
        listing.delete()
        
        return Response({
            'message': f'Listing "{listing_title}" deleted successfully'
        }, status=HTTP_204_NO_CONTENT)
    
    except PropertyListing.DoesNotExist:
        return Response({'error': 'Listing not found'}, status=HTTP_404_NOT_FOUND)


# ==================== CMA REPORT MANAGEMENT ENDPOINTS ====================

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                         description='Search by title, seller name, or property address (optional)'),
        openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                         description='Filter by status: accepted, rejected (optional)'),
        openapi.Parameter('seller_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, 
                         description='Filter by seller ID (optional)'),
    ],
    responses={
        200: openapi.Response(
            description='List of all CMA reports',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'cmas': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'title': openapi.Schema(type=openapi.TYPE_STRING),
                                'seller': openapi.Schema(type=openapi.TYPE_STRING),
                                'seller_email': openapi.Schema(type=openapi.TYPE_STRING),
                                'property_address': openapi.Schema(type=openapi.TYPE_STRING),
                                'listing_price': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING),
                                'date': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    ),
                }
            )
        ),
        401: openapi.Response(description='Unauthorized'),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_list_cma_reports(request):
    """
    List all CMA reports with optional filters and all files
    
    **Requires Authentication**: Bearer token
    
    **Query Parameters:**
    - search: Search in title, seller name, or property address
    - status: Filter by CMA status (accepted, rejected)
    - seller_id: Filter by specific seller
    
    **Returns:** Array of CMA reports with complete details and files
    """
    # Get query parameters
    search = request.query_params.get('search', '').strip()
    status_filter = request.query_params.get('status', '').strip().lower()
    seller_id = request.query_params.get('seller_id', '').strip()
    
    # Start with all CMA documents
    cmas = PropertyDocument.objects.filter(document_type='cma').select_related(
        'seller', 'selling_request', 'selling_request__agent'
    ).prefetch_related('files')
    
    # Apply filters
    if search:
        cmas = cmas.filter(
            Q(title__icontains=search) |
            Q(seller__username__icontains=search) |
            Q(seller__first_name__icontains=search) |
            Q(seller__last_name__icontains=search) |
            Q(seller__email__icontains=search) |
            Q(selling_request__contact_name__icontains=search) |
            Q(seller__location__icontains=search)
        )
    
    if status_filter:
        cmas = cmas.filter(cma_status=status_filter)
    
    if seller_id:
        try:
            cmas = cmas.filter(seller_id=int(seller_id))
        except ValueError:
            pass
    
    # Build response
    cmas_data = []
    for cma in cmas:
        seller_name = f"{cma.seller.first_name} {cma.seller.last_name}".strip() or cma.seller.username
        property_address = cma.seller.location or "Not specified"
        agent_name = "Unassigned"
        agent_email = ""
        
        # Get agent name from the selling request
        if cma.selling_request and cma.selling_request.agent:
            agent = cma.selling_request.agent
            agent_name = f"{agent.first_name} {agent.last_name}".strip() or agent.username
            agent_email = agent.email
        
        # Get all files for this document
        files_list = []
        for doc_file in cma.files.all():
            files_list.append({
                'id': doc_file.id,
                'filename': doc_file.original_filename,
                'file_url': request.build_absolute_uri(doc_file.file.url),
                'file_size_mb': doc_file.get_file_size_mb(),
                'file_extension': doc_file.get_file_extension(),
                'uploaded_at': doc_file.created_at.isoformat(),
            })
        
        cmas_data.append({
            'id': cma.id,
            'title': cma.title,
            'description': cma.description,
            'seller': seller_name,
            'seller_id': cma.seller.id,
            'seller_email': cma.seller.email,
            'property_address': property_address,
            'agent': agent_name,
            'agent_email': agent_email,
            'listing_price': f"${cma.selling_request.asking_price:,.0f}" if cma.selling_request else "N/A",
            'status': cma.cma_status or 'pending',
            'document_status': cma.cma_document_status,
            'files': files_list,
            'file_count': len(files_list),
            'date': cma.created_at.strftime('%m/%d/%Y'),
            'created_at': cma.created_at.isoformat(),
            'updated_at': cma.updated_at.isoformat(),
        })
    
    return Response({
        'count': len(cmas_data),
        'cmas': cmas_data
    }, status=HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description='CMA report details',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'title': openapi.Schema(type=openapi.TYPE_STRING),
                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                    'document_type': openapi.Schema(type=openapi.TYPE_STRING),
                    'file': openapi.Schema(type=openapi.TYPE_STRING),
                    'file_extension': openapi.Schema(type=openapi.TYPE_STRING),
                    'file_size_mb': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'cma_status': openapi.Schema(type=openapi.TYPE_STRING),
                    'cma_document_status': openapi.Schema(type=openapi.TYPE_STRING),
                    'seller': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'selling_request': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                    'updated_at': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        404: openapi.Response(description='CMA report not found'),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_get_cma_report(request, cma_id):
    """
    Get detailed information about a specific CMA report with all files
    
    **Requires Authentication**: Bearer token
    
    **Parameters:**
    - cma_id: ID of the CMA report
    
    **Returns:** Detailed CMA report information with seller, selling request, and all files
    """
    try:
        cma = PropertyDocument.objects.select_related(
            'seller', 'selling_request', 'selling_request__agent'
        ).prefetch_related('files').get(id=cma_id, document_type='cma')
    except PropertyDocument.DoesNotExist:
        return Response({'error': 'CMA report not found'}, status=HTTP_404_NOT_FOUND)
    
    # Seller info
    seller = cma.seller
    seller_info = {
        'id': seller.id,
        'username': seller.username,
        'full_name': f"{seller.first_name} {seller.last_name}".strip() or seller.username,
        'email': seller.email,
        'phone_number': seller.phone_number,
        'location': seller.location,
        'bedrooms': seller.bedrooms,
        'bathrooms': seller.bathrooms,
    }
    
    # Agent info
    agent_info = None
    if cma.selling_request and cma.selling_request.agent:
        agent = cma.selling_request.agent
        agent_info = {
            'id': agent.id,
            'username': agent.username,
            'full_name': f"{agent.first_name} {agent.last_name}".strip() or agent.username,
            'email': agent.email,
            'phone_number': agent.phone_number,
            'license_number': agent.license_number,
        }
    
    # Selling request info
    selling_request_info = None
    if cma.selling_request:
        sr = cma.selling_request
        selling_request_info = {
            'id': sr.id,
            'contact_name': sr.contact_name,
            'contact_email': sr.contact_email,
            'contact_phone': sr.contact_phone,
            'asking_price': float(sr.asking_price),
            'selling_reason': sr.selling_reason,
            'start_date': sr.start_date.isoformat(),
            'end_date': sr.end_date.isoformat(),
            'status': sr.status,
        }
    
    # Get all files for this CMA
    files_list = []
    for doc_file in cma.files.all():
        files_list.append({
            'id': doc_file.id,
            'filename': doc_file.original_filename,
            'file_url': request.build_absolute_uri(doc_file.file.url),
            'file_size_mb': doc_file.get_file_size_mb(),
            'file_extension': doc_file.get_file_extension(),
            'uploaded_at': doc_file.created_at.isoformat(),
        })
    
    # Build response
    cma_data = {
        'id': cma.id,
        'title': cma.title,
        'description': cma.description,
        'document_type': cma.document_type,
        'cma_status': cma.cma_status,
        'cma_document_status': cma.cma_document_status,
        'seller': seller_info,
        'agent': agent_info,
        'selling_request': selling_request_info,
        'files': files_list,
        'file_count': len(files_list),
        'total_size_mb': sum(f['file_size_mb'] for f in files_list),
        'created_at': cma.created_at.isoformat(),
        'updated_at': cma.updated_at.isoformat(),
    }
    
    return Response(cma_data, status=HTTP_200_OK)


# ==================== SHOWING AGREEMENT MANAGEMENT ENDPOINTS ====================

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                         description='Search by buyer name, agent name, or property address (optional)'),
        openapi.Parameter('buyer_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, 
                         description='Filter by buyer ID (optional)'),
        openapi.Parameter('agent_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, 
                         description='Filter by agent ID (optional)'),
    ],
    responses={
        200: openapi.Response(
            description='List of all showing agreements',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'agreements': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'agreement_type': openapi.Schema(type=openapi.TYPE_STRING),
                                'buyer': openapi.Schema(type=openapi.TYPE_STRING),
                                'buyer_email': openapi.Schema(type=openapi.TYPE_STRING),
                                'agent': openapi.Schema(type=openapi.TYPE_STRING),
                                'agent_email': openapi.Schema(type=openapi.TYPE_STRING),
                                'signed_date': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    ),
                }
            )
        ),
        401: openapi.Response(description='Unauthorized'),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_list_showing_agreements(request):
    """
    List all showing agreements/schedules with complete information
    
    **Requires Authentication**: Bearer token
    
    **Query Parameters:**
    - search: Search in buyer name, agent name, or property address
    - buyer_id: Filter by specific buyer
    - status: Filter by status (pending, confirmed, completed, cancelled)
    
    **Returns:** Array of showing agreements with buyer, property, and schedule details
    """
    # Get query parameters
    search = request.query_params.get('search', '').strip()
    buyer_id = request.query_params.get('buyer_id', '').strip()
    status = request.query_params.get('status', '').strip()
    
    # Get all showing schedules with related data
    schedules = ShowingSchedule.objects.all().select_related(
        'buyer', 'property_listing', 'property_listing__agent'
    ).order_by('-created_at')
    
    # Apply filters
    if search:
        # Annotate with full names and complete address for searching
        schedules = schedules.annotate(
            buyer_full_name=Concat('buyer__first_name', Value(' '), 'buyer__last_name'),
            agent_full_name=Concat('property_listing__agent__first_name', Value(' '), 'property_listing__agent__last_name'),
            property_full_address=Concat(
                'property_listing__street_address', Value(', '),
                'property_listing__city', Value(', '),
                'property_listing__state'
            )
        )
        # Search across buyer full_name, agent full_name, and property address
        schedules = schedules.filter(
            Q(buyer_full_name__icontains=search) |  # Buyer full name
            Q(agent_full_name__icontains=search) |  # Agent full name
            Q(property_full_address__icontains=search) |  # Property complete address
            Q(buyer__username__icontains=search) |
            Q(buyer__first_name__icontains=search) |
            Q(buyer__last_name__icontains=search) |
            Q(buyer__email__icontains=search) |
            Q(property_listing__agent__username__icontains=search) |
            Q(property_listing__agent__first_name__icontains=search) |
            Q(property_listing__agent__last_name__icontains=search) |
            Q(property_listing__agent__email__icontains=search) |
            Q(property_listing__title__icontains=search) |
            Q(property_listing__street_address__icontains=search) |
            Q(property_listing__city__icontains=search) |
            Q(property_listing__state__icontains=search)
        )
    
    if buyer_id:
        try:
            schedules = schedules.filter(buyer_id=int(buyer_id))
        except ValueError:
            pass
    
    if status:
        schedules = schedules.filter(status=status)
    
    # Build comprehensive response with all details
    schedules_data = []
    for schedule in schedules:
        # Get buyer information
        buyer = schedule.buyer
        buyer_data = {
            'id': buyer.id,
            'username': buyer.username,
            'full_name': f"{buyer.first_name} {buyer.last_name}".strip() or buyer.username,
            'email': buyer.email,
            'phone_number': getattr(buyer, 'phone_number', '') or getattr(buyer, 'phone', ''),
        }
        
        # Get agent information from property listing
        agent_data = None
        if schedule.property_listing and schedule.property_listing.agent:
            agent = schedule.property_listing.agent
            agent_data = {
                'id': agent.id,
                'username': agent.username,
                'full_name': f"{agent.first_name} {agent.last_name}".strip() or agent.username,
                'email': agent.email,
                'phone_number': getattr(agent, 'phone_number', '') or getattr(agent, 'phone', ''),
            }
        
        # Get property listing information
        property_data = None
        if schedule.property_listing:
            prop = schedule.property_listing
            property_data = {
                'id': prop.id,
                'title': prop.title,
                'address': f"{prop.street_address}, {prop.city}, {prop.state}" if prop.street_address else None,
                'street_address': prop.street_address,
                'city': prop.city,
                'state': prop.state,
                'zip_code': prop.zip_code,
                'price': float(prop.price) if prop.price else None,
                'bedrooms': prop.bedrooms,
                'bathrooms': float(prop.bathrooms) if prop.bathrooms else None,
                'square_feet': prop.square_feet,
                'property_type': prop.property_type,
            }
        
        # Get agreement information if exists
        agreement = schedule.showing_agreement.first() if hasattr(schedule, 'showing_agreement') else None
        has_agreement = agreement is not None
        agreement_signed_at = agreement.signed_at if agreement else None
        
        schedules_data.append({
            'id': schedule.id,
            'buyer': buyer_data,
            'agent': agent_data,
            'property_listing': property_data,
            'requested_date': schedule.requested_date.strftime('%Y-%m-%d') if schedule.requested_date else None,
            'preferred_time': schedule.preferred_time,
            'additional_notes': schedule.additional_notes,
            'status': schedule.status,
            'agent_response': schedule.agent_response,
            'responded_at': schedule.responded_at.isoformat() if schedule.responded_at else None,
            'confirmed_date': schedule.confirmed_date.strftime('%Y-%m-%d') if schedule.confirmed_date else None,
            'confirmed_time': schedule.confirmed_time.strftime('%H:%M') if schedule.confirmed_time else None,
            'created_at': schedule.created_at.isoformat(),
            'updated_at': schedule.updated_at.isoformat(),
            'has_agreement': has_agreement,
            'agreement_signed_at': agreement_signed_at.isoformat() if agreement_signed_at else None,
        })
    
    return Response({
        'count': len(schedules_data),
        'results': schedules_data
    }, status=HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(description="Showing agreement details"),
        404: "Not Found - Showing not found"
    },
    tags=['Admin Showings']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_get_showing_schedule(request, schedule_id):
    """
    Get detailed information about a specific showing schedule
    
    **Requires Authentication**: Bearer token
    
    **Parameters:**
    - schedule_id: ID of the showing schedule
    
    **Returns:** Detailed showing schedule information with buyer, agent, and property details
    """
    try:
        schedule = ShowingSchedule.objects.select_related(
            'buyer', 'property_listing', 'property_listing__agent'
        ).get(id=schedule_id)
    except ShowingSchedule.DoesNotExist:
        return Response(
            {'error': 'Showing schedule not found'},
            status=HTTP_404_NOT_FOUND
        )
    
    # Get buyer information
    buyer = schedule.buyer
    buyer_data = {
        'id': buyer.id,
        'username': buyer.username,
        'full_name': f"{buyer.first_name} {buyer.last_name}".strip() or buyer.username,
        'email': buyer.email,
        'phone_number': getattr(buyer, 'phone_number', '') or getattr(buyer, 'phone', ''),
    }
    
    # Get agent information from property listing
    agent_data = None
    if schedule.property_listing and schedule.property_listing.agent:
        agent = schedule.property_listing.agent
        agent_data = {
            'id': agent.id,
            'username': agent.username,
            'full_name': f"{agent.first_name} {agent.last_name}".strip() or agent.username,
            'email': agent.email,
            'phone_number': getattr(agent, 'phone_number', '') or getattr(agent, 'phone', ''),
        }
    
    # Get property listing information
    property_data = None
    if schedule.property_listing:
        prop = schedule.property_listing
        property_data = {
            'id': prop.id,
            'title': prop.title,
            'address': f"{prop.street_address}, {prop.city}, {prop.state}" if prop.street_address else None,
            'street_address': prop.street_address,
            'city': prop.city,
            'state': prop.state,
            'zip_code': prop.zip_code,
            'price': float(prop.price) if prop.price else None,
            'bedrooms': prop.bedrooms,
            'bathrooms': float(prop.bathrooms) if prop.bathrooms else None,
            'square_feet': prop.square_feet,
            'property_type': prop.property_type,
        }
    
    # Get agreement information if exists
    agreement = schedule.showing_agreement.first() if hasattr(schedule, 'showing_agreement') else None
    has_agreement = agreement is not None
    agreement_signed_at = agreement.signed_at if agreement else None
    
    schedule_data = {
        'id': schedule.id,
        'buyer': buyer_data,
        'agent': agent_data,
        'property_listing': property_data,
        'requested_date': schedule.requested_date.strftime('%Y-%m-%d') if schedule.requested_date else None,
        'preferred_time': schedule.preferred_time,
        'additional_notes': schedule.additional_notes,
        'status': schedule.status,
        'agent_response': schedule.agent_response,
        'responded_at': schedule.responded_at.isoformat() if schedule.responded_at else None,
        'confirmed_date': schedule.confirmed_date.strftime('%Y-%m-%d') if schedule.confirmed_date else None,
        'confirmed_time': schedule.confirmed_time.strftime('%H:%M') if schedule.confirmed_time else None,
        'created_at': schedule.created_at.isoformat(),
        'updated_at': schedule.updated_at.isoformat(),
        'has_agreement': has_agreement,
        'agreement_signed_at': agreement_signed_at.isoformat() if agreement_signed_at else None,
    }
    
    return Response(schedule_data, status=HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description='Showing agreement details',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'showing_schedule_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'duration_type': openapi.Schema(type=openapi.TYPE_STRING),
                    'property_address': openapi.Schema(type=openapi.TYPE_STRING),
                    'showing_date': openapi.Schema(type=openapi.TYPE_STRING),
                    'agreement_accepted': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'signed_at': openapi.Schema(type=openapi.TYPE_STRING),
                    'buyer': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'agent': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'showing_schedule': openapi.Schema(type=openapi.TYPE_OBJECT),
                }
            )
        ),
        404: openapi.Response(description='Showing agreement not found'),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_get_showing_agreement(request, agreement_id):
    """
    Get detailed information about a specific showing agreement
    
    **Requires Authentication**: Bearer token
    
    **Parameters:**
    - agreement_id: ID of the showing agreement
    
    **Returns:** Detailed showing agreement information with buyer, agent, and showing details
    """
    try:
        agreement = ShowingAgreement.objects.select_related(
            'buyer', 'agent', 'showing_schedule', 'showing_schedule__property_listing'
        ).get(id=agreement_id)
    except ShowingAgreement.DoesNotExist:
        return Response({'error': 'Showing agreement not found'}, status=HTTP_404_NOT_FOUND)
    
    # Buyer info
    buyer = agreement.buyer
    buyer_info = {
        'id': buyer.id,
        'username': buyer.username,
        'full_name': f"{buyer.first_name} {buyer.last_name}".strip() or buyer.username,
        'email': buyer.email,
        'phone_number': buyer.phone_number,
    }
    
    # Agent info
    agent = agreement.agent
    agent_info = {
        'id': agent.id,
        'username': agent.username,
        'full_name': f"{agent.first_name} {agent.last_name}".strip() or agent.username,
        'email': agent.email,
        'phone_number': agent.phone_number,
        'license_number': agent.license_number,
    }
    
    # Showing schedule info
    schedule = agreement.showing_schedule
    listing = schedule.property_listing
    showing_info = {
        'id': schedule.id,
        'property_listing_id': listing.id,
        'property_title': listing.title,
        'property_address': f"{listing.street_address}, {listing.city}, {listing.state}",
        'requested_date': schedule.requested_date.isoformat(),
        'confirmed_date': schedule.confirmed_date.isoformat() if schedule.confirmed_date else None,
        'confirmed_time': schedule.confirmed_time.strftime('%H:%M') if schedule.confirmed_time else None,
        'status': schedule.status,
        'created_at': schedule.created_at.isoformat(),
    }
    
    # Build response
    agreement_data = {
        'id': agreement.id,
        'showing_schedule_id': schedule.id,
        'duration_type': agreement.duration_type,
        'duration_display': dict(ShowingAgreement._meta.get_field('duration_type').choices).get(agreement.duration_type),
        'property_address': agreement.property_address,
        'showing_date': agreement.showing_date.isoformat(),
        'signature': agreement.signature[:100] + '...' if agreement.signature and len(agreement.signature) > 100 else agreement.signature,
        'agreement_accepted': agreement.agreement_accepted,
        'terms_text': agreement.terms_text,
        'signed_at': agreement.signed_at.isoformat(),
        'buyer': buyer_info,
        'agent': agent_info,
        'showing_schedule': showing_info,
        'created_at': agreement.created_at.isoformat(),
        'updated_at': agreement.updated_at.isoformat(),
    }
    
    return Response(agreement_data, status=HTTP_200_OK)


# ==================== SELLING AGREEMENT MANAGEMENT ENDPOINTS ====================

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                         description='Search by seller name, agent name, or property address (optional)'),
        openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                         description='Filter by status: accepted, rejected (optional)'),
        openapi.Parameter('seller_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, 
                         description='Filter by seller ID (optional)'),
    ],
    responses={
        200: openapi.Response(
            description='List of all selling agreements',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'agreements': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'agreement_type': openapi.Schema(type=openapi.TYPE_STRING),
                                'seller': openapi.Schema(type=openapi.TYPE_STRING),
                                'seller_email': openapi.Schema(type=openapi.TYPE_STRING),
                                'agent': openapi.Schema(type=openapi.TYPE_STRING),
                                'agent_email': openapi.Schema(type=openapi.TYPE_STRING),
                                'signed_date': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    ),
                }
            )
        ),
        401: openapi.Response(description='Unauthorized'),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_list_selling_agreements(request):
    """
    List all selling agreements with optional filters and all files
    
    **Requires Authentication**: Bearer token
    
    **Query Parameters:**
    - search: Search in seller name, agent name, or property address
    - status: Filter by agreement status (accepted, rejected)
    - seller_id: Filter by specific seller
    
    **Returns:** Array of selling agreements with complete details and files
    """
    # Get query parameters
    search = request.query_params.get('search', '').strip()
    status_filter = request.query_params.get('status', '').strip().lower()
    seller_id = request.query_params.get('seller_id', '').strip()
    
    # Get all property documents that have selling agreements
    agreements = PropertyDocument.objects.filter(
        selling_agreement_file__isnull=False
    ).select_related(
        'seller', 'selling_request', 'selling_request__agent'
    ).prefetch_related('files')
    
    # Apply filters
    if search:
        agreements = agreements.filter(
            Q(seller__username__icontains=search) |
            Q(seller__first_name__icontains=search) |
            Q(seller__last_name__icontains=search) |
            Q(seller__email__icontains=search) |
            Q(seller__location__icontains=search) |
            Q(selling_request__contact_name__icontains=search)
        )
    
    if status_filter:
        agreements = agreements.filter(agreement_status=status_filter)
    
    if seller_id:
        try:
            agreements = agreements.filter(seller_id=int(seller_id))
        except ValueError:
            pass
    
    # Build response
    agreements_data = []
    for agreement in agreements:
        seller_name = f"{agreement.seller.first_name} {agreement.seller.last_name}".strip() or agreement.seller.username
        
        # Get agent info if available from selling request
        agent_name = "Not assigned"
        agent_email = ""
        if agreement.selling_request and agreement.selling_request.agent:
            agent = agreement.selling_request.agent
            agent_name = f"{agent.first_name} {agent.last_name}".strip() or agent.username
            agent_email = agent.email
        
        # Get all files for this document
        files_list = []
        for doc_file in agreement.files.all():
            files_list.append({
                'id': doc_file.id,
                'filename': doc_file.original_filename,
                'file_url': request.build_absolute_uri(doc_file.file.url),
                'file_size_mb': doc_file.get_file_size_mb(),
                'file_extension': doc_file.get_file_extension(),
                'uploaded_at': doc_file.created_at.isoformat(),
            })
        
        agreements_data.append({
            'id': agreement.id,
            'title': agreement.title,
            'agreement_type': 'SA',
            'seller': seller_name,
            'seller_id': agreement.seller.id,
            'seller_email': agreement.seller.email,
            'agent': agent_name,
            'agent_email': agent_email,
            'signed_date': agreement.created_at.strftime('%m/%d/%Y'),
            'status': agreement.agreement_status or 'pending',
            'files': files_list,
            'file_count': len(files_list),
            'created_at': agreement.created_at.isoformat(),
            'updated_at': agreement.updated_at.isoformat(),
        })
    
    return Response({
        'count': len(agreements_data),
        'agreements': agreements_data
    }, status=HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description='Selling agreement details',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'title': openapi.Schema(type=openapi.TYPE_STRING),
                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                    'selling_agreement_file': openapi.Schema(type=openapi.TYPE_STRING),
                    'agreement_status': openapi.Schema(type=openapi.TYPE_STRING),
                    'file_extension': openapi.Schema(type=openapi.TYPE_STRING),
                    'file_size_mb': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'seller': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'selling_request': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                    'updated_at': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        404: openapi.Response(description='Selling agreement not found'),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_get_selling_agreement(request, agreement_id):
    """
    Get detailed information about a specific selling agreement with all files
    
    **Requires Authentication**: Bearer token
    
    **Parameters:**
    - agreement_id: ID of the selling agreement (PropertyDocument ID)
    
    **Returns:** Detailed selling agreement information with seller, selling request, and all files
    """
    try:
        agreement = PropertyDocument.objects.select_related(
            'seller', 'selling_request', 'selling_request__agent'
        ).prefetch_related('files').get(id=agreement_id, selling_agreement_file__isnull=False)
    except PropertyDocument.DoesNotExist:
        return Response({'error': 'Selling agreement not found'}, status=HTTP_404_NOT_FOUND)
    
    # Seller info
    seller = agreement.seller
    seller_info = {
        'id': seller.id,
        'username': seller.username,
        'full_name': f"{seller.first_name} {seller.last_name}".strip() or seller.username,
        'email': seller.email,
        'phone_number': seller.phone_number,
        'location': seller.location,
        'bedrooms': seller.bedrooms,
        'bathrooms': seller.bathrooms,
    }
    
    # Agent info
    agent_info = None
    if agreement.selling_request and agreement.selling_request.agent:
        agent = agreement.selling_request.agent
        agent_info = {
            'id': agent.id,
            'username': agent.username,
            'full_name': f"{agent.first_name} {agent.last_name}".strip() or agent.username,
            'email': agent.email,
            'phone_number': agent.phone_number,
            'license_number': agent.license_number,
        }
    
    # Selling request info
    selling_request_info = None
    if agreement.selling_request:
        sr = agreement.selling_request
        selling_request_info = {
            'id': sr.id,
            'contact_name': sr.contact_name,
            'contact_email': sr.contact_email,
            'contact_phone': sr.contact_phone,
            'asking_price': float(sr.asking_price),
            'selling_reason': sr.selling_reason,
            'start_date': sr.start_date.isoformat(),
            'end_date': sr.end_date.isoformat(),
            'status': sr.status,
        }
    
    # Get all files for this selling agreement
    files_list = []
    for doc_file in agreement.files.all():
        files_list.append({
            'id': doc_file.id,
            'filename': doc_file.original_filename,
            'file_url': request.build_absolute_uri(doc_file.file.url),
            'file_size_mb': doc_file.get_file_size_mb(),
            'file_extension': doc_file.get_file_extension(),
            'uploaded_at': doc_file.created_at.isoformat(),
        })
    
    # Build response
    agreement_data = {
        'id': agreement.id,
        'title': agreement.title,
        'description': agreement.description,
        'agreement_status': agreement.agreement_status,
        'seller': seller_info,
        'agent': agent_info,
        'selling_request': selling_request_info,
        'files': files_list,
        'file_count': len(files_list),
        'total_size_mb': sum(f['file_size_mb'] for f in files_list),
        'created_at': agreement.created_at.isoformat(),
        'updated_at': agreement.updated_at.isoformat(),
    }
    
    return Response(agreement_data, status=HTTP_200_OK)


# ==================== BUYER DOCUMENT MANAGEMENT ENDPOINTS ====================

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, 
                         description='Search by buyer name or email (optional)'),
        openapi.Parameter('buyer_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, 
                         description='Filter by buyer ID (optional)'),
    ],
    responses={
        200: openapi.Response(
            description='List of all buyer documents',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'documents': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                }
            )
        ),
        401: openapi.Response(description='Unauthorized'),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_list_buyer_documents(request):
    """
    List all buyer documents with optional filters
    
    **Requires Authentication**: Bearer token
    
    **Query Parameters:**
    - search: Search in buyer name or email
    - buyer_id: Filter by specific buyer
    
    **Returns:** Array of buyer documents with details
    """
    # Get query parameters
    search = request.query_params.get('search', '').strip()
    buyer_id = request.query_params.get('buyer_id', '').strip()
    
    # Get all buyer documents
    documents = BuyerDocument.objects.all().select_related('buyer')
    
    # Apply filters
    if search:
        documents = documents.filter(
            Q(buyer__username__icontains=search) |
            Q(buyer__first_name__icontains=search) |
            Q(buyer__last_name__icontains=search) |
            Q(buyer__email__icontains=search) |
            Q(title__icontains=search)
        )
    
    if buyer_id:
        try:
            documents = documents.filter(buyer_id=int(buyer_id))
        except ValueError:
            pass
    
    # Build response
    documents_data = []
    for doc in documents:
        buyer_name = f"{doc.buyer.first_name} {doc.buyer.last_name}".strip() or doc.buyer.username
        
        documents_data.append({
            'id': doc.id,
            'title': doc.title,
            'description': doc.description,
            'buyer': buyer_name,
            'buyer_email': doc.buyer.email,
            'file_url': doc.document_file.url if doc.document_file else None,
            'file_size_mb': doc.get_file_size_mb(),
            'created_at': doc.created_at.strftime('%m/%d/%Y'),
        })
    
    return Response({
        'count': len(documents_data),
        'documents': documents_data
    }, status=HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description='Buyer document details',
            schema=openapi.Schema(type=openapi.TYPE_OBJECT)
        ),
        404: openapi.Response(description='Document not found'),
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_get_buyer_document(request, document_id):
    """
    Get detailed information about a specific buyer document
    
    **Requires Authentication**: Bearer token
    
    **Parameters:**
    - document_id: ID of the buyer document
    
    **Returns:** Detailed buyer document information
    """
    try:
        document = BuyerDocument.objects.select_related('buyer').get(id=document_id)
    except BuyerDocument.DoesNotExist:
        return Response({'error': 'Buyer document not found'}, status=HTTP_404_NOT_FOUND)
    
    # Buyer info
    buyer = document.buyer
    buyer_info = {
        'id': buyer.id,
        'username': buyer.username,
        'full_name': f"{buyer.first_name} {buyer.last_name}".strip() or buyer.username,
        'email': buyer.email,
        'phone_number': buyer.phone_number,
    }
    
    # Build response
    document_data = {
        'id': document.id,
        'title': document.title,
        'description': document.description,
        'document_file': document.document_file.url if document.document_file else None,
        'file_extension': document.get_file_extension(),
        'file_size_mb': document.get_file_size_mb(),
        'buyer': buyer_info,
        'created_at': document.created_at.isoformat(),
        'updated_at': document.updated_at.isoformat(),
    }
    
    return Response(document_data, status=HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['buyer_id', 'title', 'document_file'],
        properties={
            'buyer_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Buyer ID'),
            'title': openapi.Schema(type=openapi.TYPE_STRING, description='Document title'),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description='Document description'),
            'document_file': openapi.Schema(type=openapi.TYPE_STRING, format='binary', description='PDF file'),
        }
    ),
    responses={
        201: openapi.Response(
            description='Document uploaded successfully',
            schema=openapi.Schema(type=openapi.TYPE_OBJECT)
        ),
        400: openapi.Response(description='Bad request'),
        404: openapi.Response(description='Buyer not found'),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_upload_buyer_document(request):
    """
    Upload a buyer document (PDF)
    
    **Requires Authentication**: Bearer token
    
    **Required Fields:**
    - buyer_id: ID of the buyer
    - title: Document title
    - document_file: PDF file (max 10MB)
    
    **Optional Fields:**
    - description: Document description
    
    **Returns:** Created document data
    """
    # Validate required fields
    required_fields = ['buyer_id', 'title']
    for field in required_fields:
        if field not in request.data:
            return Response({'error': f'{field} is required'}, status=HTTP_400_BAD_REQUEST)
    
    # Check for file
    if 'document_file' not in request.FILES:
        return Response({'error': 'document_file is required'}, status=HTTP_400_BAD_REQUEST)
    
    # Get buyer
    buyer_id = request.data.get('buyer_id')
    try:
        buyer = Buyer.objects.get(id=buyer_id)
    except Buyer.DoesNotExist:
        return Response({'error': 'Buyer not found'}, status=HTTP_404_NOT_FOUND)
    
    # Get file
    document_file = request.FILES['document_file']
    
    # Validate file size (10MB max)
    max_size = 10 * 1024 * 1024  # 10MB
    if document_file.size > max_size:
        return Response({'error': 'File size exceeds 10MB limit'}, status=HTTP_400_BAD_REQUEST)
    
    # Validate file extension (PDF only)
    import os
    file_extension = os.path.splitext(document_file.name)[1].lower()
    if file_extension not in ['.pdf']:
        return Response({'error': 'Only PDF files are allowed'}, status=HTTP_400_BAD_REQUEST)
    
    try:
        # Create document
        document = BuyerDocument.objects.create(
            buyer=buyer,
            title=request.data.get('title'),
            description=request.data.get('description', ''),
            document_file=document_file,
            file_size=document_file.size
        )
        
        return Response({
            'message': 'Buyer document uploaded successfully',
            'document': {
                'id': document.id,
                'title': document.title,
                'file_url': document.document_file.url,
                'file_size_mb': document.get_file_size_mb(),
                'buyer': {
                    'id': buyer.id,
                    'username': buyer.username,
                }
            }
        }, status=HTTP_201_CREATED)
    
    except Exception as e:
        return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='delete',
    responses={
        204: openapi.Response(description='Document deleted successfully'),
        404: openapi.Response(description='Document not found'),
    }
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_delete_buyer_document(request, document_id):
    """
    Delete a buyer document
    
    **Requires Authentication**: Bearer token
    
    **Parameters:**
    - document_id: ID of the buyer document to delete
    
    **Returns:** Success message
    """
    try:
        document = BuyerDocument.objects.get(id=document_id)
        document_title = document.title
        document.delete()
        
        return Response({
            'message': f'Document "{document_title}" deleted successfully'
        }, status=HTTP_204_NO_CONTENT)
    
    except BuyerDocument.DoesNotExist:
        return Response({'error': 'Document not found'}, status=HTTP_404_NOT_FOUND)


# ================== Legal Documents Management ==================

@swagger_auto_schema(
    method='get',
    operation_summary="List all Agent Privacy Policies",
    operation_description="Get all agent privacy policies (admin only)",
    tags=['Superadmin - Legal Documents'],
    responses={200: 'List of agent privacy policies'}
)
@swagger_auto_schema(
    method='post',
    operation_summary="Create Agent Privacy Policy",
    operation_description="Create a new privacy policy for agents",
    tags=['Superadmin - Legal Documents'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['title', 'content', 'effective_date'],
        properties={
            'title': openapi.Schema(type=openapi.TYPE_STRING),
            'content': openapi.Schema(type=openapi.TYPE_STRING),
            'version': openapi.Schema(type=openapi.TYPE_STRING, default='1.0'),
            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
            'effective_date': openapi.Schema(type=openapi.TYPE_STRING, format='date')
        }
    ),
    responses={201: 'Privacy policy created', 400: 'Invalid data'}
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def agent_privacy_policy_list_create(request):
    from .models import AgentPrivacyPolicy
    from .serializers import AgentPrivacyPolicySerializer
    
    if request.method == 'GET':
        policies = AgentPrivacyPolicy.objects.all()
        serializer = AgentPrivacyPolicySerializer(policies, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = AgentPrivacyPolicySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_summary="Get Agent Privacy Policy",
    operation_description="Get specific agent privacy policy by ID",
    tags=['Superadmin - Legal Documents']
)
@swagger_auto_schema(
    method='patch',
    operation_summary="Update Agent Privacy Policy",
    operation_description="Update existing agent privacy policy",
    tags=['Superadmin - Legal Documents'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'title': openapi.Schema(type=openapi.TYPE_STRING),
            'content': openapi.Schema(type=openapi.TYPE_STRING),
            'version': openapi.Schema(type=openapi.TYPE_STRING),
            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            'effective_date': openapi.Schema(type=openapi.TYPE_STRING, format='date')
        }
    )
)
@swagger_auto_schema(
    method='delete',
    operation_summary="Delete Agent Privacy Policy",
    operation_description="Delete agent privacy policy by ID",
    tags=['Superadmin - Legal Documents']
)
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def agent_privacy_policy_detail(request, pk):
    from .models import AgentPrivacyPolicy
    from .serializers import AgentPrivacyPolicySerializer
    
    try:
        policy = AgentPrivacyPolicy.objects.get(pk=pk)
    except AgentPrivacyPolicy.DoesNotExist:
        return Response({'error': 'Privacy policy not found'}, status=HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = AgentPrivacyPolicySerializer(policy)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = AgentPrivacyPolicySerializer(policy, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        policy.delete()
        return Response({'message': 'Privacy policy deleted'}, status=HTTP_204_NO_CONTENT)


@swagger_auto_schema(
    method='get',
    operation_summary="List all Agent Terms & Conditions",
    tags=['Superadmin - Legal Documents']
)
@swagger_auto_schema(
    method='post',
    operation_summary="Create Agent Terms & Conditions",
    tags=['Superadmin - Legal Documents'],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['title', 'content', 'effective_date'],
        properties={
            'title': openapi.Schema(type=openapi.TYPE_STRING),
            'content': openapi.Schema(type=openapi.TYPE_STRING),
            'version': openapi.Schema(type=openapi.TYPE_STRING, default='1.0'),
            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
            'effective_date': openapi.Schema(type=openapi.TYPE_STRING, format='date')
        }
    )
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def agent_terms_conditions_list_create(request):
    from .models import AgentTermsConditions
    from .serializers import AgentTermsConditionsSerializer
    
    if request.method == 'GET':
        terms = AgentTermsConditions.objects.all()
        serializer = AgentTermsConditionsSerializer(terms, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = AgentTermsConditionsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_summary="Get Agent Terms & Conditions",
    tags=['Superadmin - Legal Documents']
)
@swagger_auto_schema(
    method='patch',
    operation_summary="Update Agent Terms & Conditions",
    tags=['Superadmin - Legal Documents']
)
@swagger_auto_schema(
    method='delete',
    operation_summary="Delete Agent Terms & Conditions",
    tags=['Superadmin - Legal Documents']
)
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def agent_terms_conditions_detail(request, pk):
    from .models import AgentTermsConditions
    from .serializers import AgentTermsConditionsSerializer
    
    try:
        terms = AgentTermsConditions.objects.get(pk=pk)
    except AgentTermsConditions.DoesNotExist:
        return Response({'error': 'Terms & conditions not found'}, status=HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = AgentTermsConditionsSerializer(terms)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = AgentTermsConditionsSerializer(terms, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        terms.delete()
        return Response({'message': 'Terms & conditions deleted'}, status=HTTP_204_NO_CONTENT)


# Seller Privacy Policy
@swagger_auto_schema(method='get', operation_summary="List all Seller Privacy Policies", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='post', operation_summary="Create Seller Privacy Policy", tags=['Superadmin - Legal Documents'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def seller_privacy_policy_list_create(request):
    from .models import SellerPrivacyPolicy
    from .serializers import SellerPrivacyPolicySerializer
    
    if request.method == 'GET':
        policies = SellerPrivacyPolicy.objects.all()
        serializer = SellerPrivacyPolicySerializer(policies, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = SellerPrivacyPolicySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='get', operation_summary="Get Seller Privacy Policy", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='patch', operation_summary="Update Seller Privacy Policy", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='delete', operation_summary="Delete Seller Privacy Policy", tags=['Superadmin - Legal Documents'])
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def seller_privacy_policy_detail(request, pk):
    from .models import SellerPrivacyPolicy
    from .serializers import SellerPrivacyPolicySerializer
    
    try:
        policy = SellerPrivacyPolicy.objects.get(pk=pk)
    except SellerPrivacyPolicy.DoesNotExist:
        return Response({'error': 'Privacy policy not found'}, status=HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = SellerPrivacyPolicySerializer(policy)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = SellerPrivacyPolicySerializer(policy, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        policy.delete()
        return Response({'message': 'Privacy policy deleted'}, status=HTTP_204_NO_CONTENT)


# Seller Terms & Conditions
@swagger_auto_schema(method='get', operation_summary="List all Seller Terms & Conditions", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='post', operation_summary="Create Seller Terms & Conditions", tags=['Superadmin - Legal Documents'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def seller_terms_conditions_list_create(request):
    from .models import SellerTermsConditions
    from .serializers import SellerTermsConditionsSerializer
    
    if request.method == 'GET':
        terms = SellerTermsConditions.objects.all()
        serializer = SellerTermsConditionsSerializer(terms, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = SellerTermsConditionsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='get', operation_summary="Get Seller Terms & Conditions", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='patch', operation_summary="Update Seller Terms & Conditions", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='delete', operation_summary="Delete Seller Terms & Conditions", tags=['Superadmin - Legal Documents'])
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def seller_terms_conditions_detail(request, pk):
    from .models import SellerTermsConditions
    from .serializers import SellerTermsConditionsSerializer
    
    try:
        terms = SellerTermsConditions.objects.get(pk=pk)
    except SellerTermsConditions.DoesNotExist:
        return Response({'error': 'Terms & conditions not found'}, status=HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = SellerTermsConditionsSerializer(terms)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = SellerTermsConditionsSerializer(terms, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        terms.delete()
        return Response({'message': 'Terms & conditions deleted'}, status=HTTP_204_NO_CONTENT)


# Buyer Privacy Policy
@swagger_auto_schema(method='get', operation_summary="List all Buyer Privacy Policies", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='post', operation_summary="Create Buyer Privacy Policy", tags=['Superadmin - Legal Documents'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def buyer_privacy_policy_list_create(request):
    from .models import BuyerPrivacyPolicy
    from .serializers import BuyerPrivacyPolicySerializer
    
    if request.method == 'GET':
        policies = BuyerPrivacyPolicy.objects.all()
        serializer = BuyerPrivacyPolicySerializer(policies, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = BuyerPrivacyPolicySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='get', operation_summary="Get Buyer Privacy Policy", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='patch', operation_summary="Update Buyer Privacy Policy", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='delete', operation_summary="Delete Buyer Privacy Policy", tags=['Superadmin - Legal Documents'])
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def buyer_privacy_policy_detail(request, pk):
    from .models import BuyerPrivacyPolicy
    from .serializers import BuyerPrivacyPolicySerializer
    
    try:
        policy = BuyerPrivacyPolicy.objects.get(pk=pk)
    except BuyerPrivacyPolicy.DoesNotExist:
        return Response({'error': 'Privacy policy not found'}, status=HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = BuyerPrivacyPolicySerializer(policy)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = BuyerPrivacyPolicySerializer(policy, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        policy.delete()
        return Response({'message': 'Privacy policy deleted'}, status=HTTP_204_NO_CONTENT)


# Buyer Terms & Conditions
@swagger_auto_schema(method='get', operation_summary="List all Buyer Terms & Conditions", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='post', operation_summary="Create Buyer Terms & Conditions", tags=['Superadmin - Legal Documents'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def buyer_terms_conditions_list_create(request):
    from .models import BuyerTermsConditions
    from .serializers import BuyerTermsConditionsSerializer
    
    if request.method == 'GET':
        terms = BuyerTermsConditions.objects.all()
        serializer = BuyerTermsConditionsSerializer(terms, many=True)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = BuyerTermsConditionsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='get', operation_summary="Get Buyer Terms & Conditions", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='patch', operation_summary="Update Buyer Terms & Conditions", tags=['Superadmin - Legal Documents'])
@swagger_auto_schema(method='delete', operation_summary="Delete Buyer Terms & Conditions", tags=['Superadmin - Legal Documents'])
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def buyer_terms_conditions_detail(request, pk):
    from .models import BuyerTermsConditions
    from .serializers import BuyerTermsConditionsSerializer
    
    try:
        terms = BuyerTermsConditions.objects.get(pk=pk)
    except BuyerTermsConditions.DoesNotExist:
        return Response({'error': 'Terms & conditions not found'}, status=HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = BuyerTermsConditionsSerializer(terms)
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = BuyerTermsConditionsSerializer(terms, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        terms.delete()
        return Response({'message': 'Terms & conditions deleted'}, status=HTTP_204_NO_CONTENT)


# ============================================
# BUYER MANAGEMENT APIs
# ============================================

@swagger_auto_schema(
    method='get',
    operation_description="Get list of all buyers with their information",
    responses={
        200: openapi.Response(
            description="List of buyers",
            examples={
                'application/json': {
                    'count': 10,
                    'results': [{
                        'id': 1,
                        'username': 'buyer1',
                        'email': 'buyer1@example.com',
                        'full_name': 'John Doe',
                        'phone_number': '1234567890',
                        'price_range': '$300,000 - $500,000',
                        'location': 'New York',
                        'bedrooms': 3,
                        'bathrooms': 2,
                        'is_active': True
                    }]
                }
            }
        ),
        401: "Unauthorized"
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buyer_list(request):
    """Get list of all buyers"""
    from .serializers import BuyerListSerializer
    
    buyers = Buyer.objects.all().order_by('-created_at')
    
    # Optional filtering
    search = request.query_params.get('search', None)
    if search:
        buyers = buyers.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(location__icontains=search)
        )
    
    is_active = request.query_params.get('is_active', None)
    if is_active is not None:
        buyers = buyers.filter(is_active=is_active.lower() == 'true')
    
    serializer = BuyerListSerializer(buyers, many=True, context={'request': request})
    return Response({
        'count': buyers.count(),
        'results': serializer.data
    }, status=HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    operation_description="Get detailed information about a specific buyer by ID",
    responses={
        200: openapi.Response(
            description="Buyer details",
            examples={
                'application/json': {
                    'id': 1,
                    'username': 'buyer1',
                    'email': 'buyer1@example.com',
                    'full_name': 'John Doe',
                    'phone_number': '1234567890',
                    'profile_image_url': 'http://example.com/media/profile.jpg',
                    'price_range': '$300,000 - $500,000',
                    'location': 'New York',
                    'bedrooms': 3,
                    'bathrooms': 2,
                    'mortgage_letter_url': 'http://example.com/media/mortgage.pdf',
                    'is_active': True,
                    'date_joined': '2025-01-01T00:00:00Z'
                }
            }
        ),
        404: "Buyer not found",
        401: "Unauthorized"
    }
)
@swagger_auto_schema(
    method='patch',
    operation_description="Update buyer information by ID",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING),
            'email': openapi.Schema(type=openapi.TYPE_STRING, format='email'),
            'first_name': openapi.Schema(type=openapi.TYPE_STRING),
            'last_name': openapi.Schema(type=openapi.TYPE_STRING),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
            'price_range': openapi.Schema(type=openapi.TYPE_STRING),
            'location': openapi.Schema(type=openapi.TYPE_STRING),
            'bedrooms': openapi.Schema(type=openapi.TYPE_INTEGER),
            'bathrooms': openapi.Schema(type=openapi.TYPE_INTEGER),
            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Activate or deactivate buyer account'),
        }
    ),
    responses={
        200: "Buyer updated successfully",
        400: "Bad Request - Validation errors",
        404: "Buyer not found",
        401: "Unauthorized"
    }
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def buyer_detail(request, pk):
    """Get or update buyer details by ID"""
    from .serializers import BuyerDetailSerializer, BuyerUpdateSerializer
    
    try:
        buyer = Buyer.objects.get(pk=pk)
    except Buyer.DoesNotExist:
        return Response({'error': 'Buyer not found'}, status=HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = BuyerDetailSerializer(buyer, context={'request': request})
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = BuyerUpdateSerializer(buyer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return detailed response
            detail_serializer = BuyerDetailSerializer(buyer, context={'request': request})
            return Response(detail_serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


# Platform Documents API

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def platform_documents_list(request):
    """
    List all platform documents (GET) or upload new document (POST - admin only)
    
    **Accessible by:** All authenticated users can GET, only admin can POST
    
    **POST Parameters:**
    - document_type: Type of document (required)
    - title: Document title (required)
    - description: Document description (optional)
    - document: Document file (required)
    - is_active: Is document active (optional, default: true)
    - version: Document version (optional, default: 1.0)
    """
    from .models import PlatformDocument
    from .serializers import PlatformDocumentSerializer, PlatformDocumentUploadSerializer
    
    if request.method == 'GET':
        # Get all documents (both active and inactive)
        documents = PlatformDocument.objects.all().order_by('-created_at')
        
        # Filter by document type if provided
        doc_type = request.query_params.get('document_type')
        if doc_type:
            documents = documents.filter(document_type=doc_type)
        
        # Filter by active status if provided (optional)
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']
            documents = documents.filter(is_active=is_active_bool)
        
        serializer = PlatformDocumentSerializer(
            documents, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'count': documents.count(),
            'results': serializer.data
        }, status=HTTP_200_OK)
    
    elif request.method == 'POST':
        # Only admin can upload
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only administrators can upload documents'},
                status=HTTP_403_FORBIDDEN
            )
        
        serializer = PlatformDocumentUploadSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(uploaded_by=request.user)
            
            # Return full document details
            document = PlatformDocument.objects.get(pk=serializer.data['id'])
            response_serializer = PlatformDocumentSerializer(
                document,
                context={'request': request}
            )
            
            return Response(response_serializer.data, status=HTTP_201_CREATED)
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def platform_document_detail(request, document_id):
    """
    Get, update, or delete a specific platform document
    
    **Accessible by:**
    - GET: All authenticated users
    - PATCH: Admin only
    - DELETE: Admin only
    """
    from .models import PlatformDocument
    from .serializers import PlatformDocumentSerializer, PlatformDocumentUploadSerializer
    
    try:
        document = PlatformDocument.objects.get(pk=document_id)
    except PlatformDocument.DoesNotExist:
        return Response(
            {'error': 'Document not found'},
            status=HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        # All authenticated users can view
        serializer = PlatformDocumentSerializer(
            document,
            context={'request': request}
        )
        return Response(serializer.data, status=HTTP_200_OK)
    
    elif request.method == 'PATCH':
        # Only admin can update
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only administrators can update documents'},
                status=HTTP_403_FORBIDDEN
            )
        
        serializer = PlatformDocumentUploadSerializer(
            document,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Return full document details
            response_serializer = PlatformDocumentSerializer(
                document,
                context={'request': request}
            )
            return Response(response_serializer.data, status=HTTP_200_OK)
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only admin can delete
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only administrators can delete documents'},
                status=HTTP_403_FORBIDDEN
            )
        
        document.delete()
        return Response(
            {'message': 'Document deleted successfully'},
            status=HTTP_204_NO_CONTENT
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def platform_documents_public(request):
    """
    Get platform documents - public endpoint (no authentication required)
    
    **Query Parameters:**
    - document_type: Filter by document type (optional)
    
    **Returns:** List of active documents
    """
    from .models import PlatformDocument
    from .serializers import PlatformDocumentSerializer
    
    # Get all active documents
    documents = PlatformDocument.objects.filter(is_active=True).order_by('-created_at')
    
    # Filter by document type if provided
    doc_type = request.query_params.get('document_type')
    if doc_type:
        documents = documents.filter(document_type=doc_type)
    
    serializer = PlatformDocumentSerializer(
        documents,
        many=True,
        context={'request': request}
    )
    
    return Response({
        'count': documents.count(),
        'results': serializer.data
    }, status=HTTP_200_OK)

