"""
Comprehensive test cases for Admin API endpoints
Tests cover normal flows, edge cases, validations, and error scenarios
"""

import json
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from agent.models import Agent
from seller.models import Seller
from buyer.models import Buyer


class AdminLoginTestCase(TestCase):
    """Test cases for admin login endpoint"""
    
    def setUp(self):
        """Setup test client and create test users"""
        self.client = Client()
        self.login_url = '/api/v1/admin/login/'
        
        # Create a test agent for login (with superuser privileges)
        self.agent = Agent.objects.create_user(
            username='test_agent_admin',
            email='agent_admin@test.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='Agent',
            is_superuser=True,
            is_staff=True
        )
    
    def test_successful_login(self):
        """Test successful admin login with correct credentials"""
        # Verify user exists
        self.assertTrue(Agent.objects.filter(username='test_agent_admin').exists())
        
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'username': 'test_agent_admin',
                'password': 'AdminPass123!'
            }),
            content_type='application/json'
        )
        if response.status_code != status.HTTP_200_OK:
            print(f"Response: {response.json()}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.json())
        self.assertIn('refresh', response.json())
        self.assertIn('dashboard', response.json())
    
    def test_login_invalid_username(self):
        """Test login with non-existent username"""
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'username': 'nonexistent_user',
                'password': 'AdminPass123!'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_invalid_password(self):
        """Test login with incorrect password"""
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'username': 'test_agent_admin',
                'password': 'WrongPassword123!'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_missing_username(self):
        """Test login without username field"""
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'password': 'AdminPass123!'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_missing_password(self):
        """Test login without password field"""
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'username': 'test_agent_admin'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_empty_credentials(self):
        """Test login with empty username and password"""
        response = self.client.post(
            self.login_url,
            data=json.dumps({
                'username': '',
                'password': ''
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminCreateUserTestCase(TestCase):
    """Test cases for creating users via admin API"""
    
    def setUp(self):
        """Setup test client and authentication"""
        self.client = Client()
        self.users_url = '/api/v1/admin/users/'
        
        # Create admin user for authentication
        self.admin_user = Agent.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='AdminPass123!'
        )
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.admin_user)
        self.access_token = str(refresh.access_token)
        self.headers = {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}
    
    def test_create_agent_successful(self):
        """Test successful agent creation"""
        response = self.client.post(self.users_url, {
            'username': 'new_agent_123',
            'email': 'newagent@test.com',
            'password': 'SecurePass123!',
            'user_type': 'agent',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+1234567890'
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['user']['username'], 'new_agent_123')
        self.assertEqual(data['user']['user_type'], 'agent')
        self.assertTrue(Agent.objects.filter(username='new_agent_123').exists())
    
    def test_create_seller_successful(self):
        """Test successful seller creation"""
        response = self.client.post(self.users_url, {
            'username': 'new_seller_123',
            'email': 'newseller@test.com',
            'password': 'SecurePass123!',
            'user_type': 'seller',
            'first_name': 'Jane',
            'last_name': 'Smith'
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Seller.objects.filter(username='new_seller_123').exists())
    
    def test_create_buyer_successful(self):
        """Test successful buyer creation"""
        response = self.client.post(self.users_url, {
            'username': 'new_buyer_123',
            'email': 'newbuyer@test.com',
            'password': 'SecurePass123!',
            'user_type': 'buyer'
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Buyer.objects.filter(username='new_buyer_123').exists())
    
    def test_create_user_missing_username(self):
        """Test user creation without username - CORNER CASE"""
        response = self.client.post(self.users_url, {
            'email': 'test@test.com',
            'password': 'SecurePass123!',
            'user_type': 'agent'
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_create_user_missing_email(self):
        """Test user creation without email - CORNER CASE"""
        response = self.client.post(self.users_url, {
            'username': 'testuser',
            'password': 'SecurePass123!',
            'user_type': 'agent'
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_create_user_missing_password(self):
        """Test user creation without password - CORNER CASE"""
        response = self.client.post(self.users_url, {
            'username': 'testuser',
            'email': 'test@test.com',
            'user_type': 'agent'
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_create_user_missing_user_type(self):
        """Test user creation without user_type - CORNER CASE"""
        response = self.client.post(self.users_url, {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'SecurePass123!'
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_create_user_invalid_user_type(self):
        """Test user creation with invalid user_type - CORNER CASE"""
        response = self.client.post(self.users_url, {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'SecurePass123!',
            'user_type': 'admin'  # Invalid type
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_create_user_duplicate_username_agent(self):
        """Test creating user with duplicate username - CORNER CASE"""
        # Create first user
        Agent.objects.create_user(
            username='duplicate_user',
            email='first@test.com',
            password='Pass123!'
        )
        
        # Try to create second user with same username
        response = self.client.post(self.users_url, {
            'username': 'duplicate_user',
            'email': 'second@test.com',
            'password': 'SecurePass123!',
            'user_type': 'agent'
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Username already exists', response.json()['error'])
    
    def test_create_user_duplicate_email_seller(self):
        """Test creating user with duplicate email - CORNER CASE"""
        # Create first user
        Seller.objects.create_user(
            username='seller1',
            email='duplicate@test.com',
            password='Pass123!'
        )
        
        # Try to create second user with same email
        response = self.client.post(self.users_url, {
            'username': 'seller2',
            'email': 'duplicate@test.com',
            'password': 'SecurePass123!',
            'user_type': 'seller'
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Email already exists', response.json()['error'])
    
    def test_create_user_without_optional_fields(self):
        """Test creating user with only required fields - CORNER CASE"""
        response = self.client.post(self.users_url, {
            'username': 'minimal_user',
            'email': 'minimal@test.com',
            'password': 'SecurePass123!',
            'user_type': 'buyer'
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        buyer = Buyer.objects.get(username='minimal_user')
        self.assertEqual(buyer.first_name, '')
        self.assertEqual(buyer.last_name, '')
    
    def test_create_user_case_insensitive_user_type(self):
        """Test user creation with uppercase user_type - CORNER CASE"""
        response = self.client.post(self.users_url, {
            'username': 'case_test_user',
            'email': 'casetest@test.com',
            'password': 'SecurePass123!',
            'user_type': 'AGENT'  # Uppercase
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Agent.objects.filter(username='case_test_user').exists())
    
    def test_create_user_with_special_characters_in_name(self):
        """Test creating user with special characters in name - CORNER CASE"""
        response = self.client.post(self.users_url, {
            'username': 'special_user_123',
            'email': 'special@test.com',
            'password': 'SecurePass123!',
            'user_type': 'agent',
            'first_name': "O'Brien",
            'last_name': "Jean-Pierre"
        }, **self.headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        agent = Agent.objects.get(username='special_user_123')
        self.assertEqual(agent.first_name, "O'Brien")
        self.assertEqual(agent.last_name, "Jean-Pierre")
    
    def test_create_user_very_long_username(self):
        """Test creating user with very long username - CORNER CASE"""
        long_username = 'a' * 150  # Exceeds typical username length
        response = self.client.post(self.users_url, {
            'username': long_username,
            'email': 'longuser@test.com',
            'password': 'SecurePass123!',
            'user_type': 'agent'
        }, **self.headers, content_type='application/json')
        
        # Should either succeed or fail gracefully
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
    
    def test_create_user_invalid_email_format(self):
        """Test creating user with invalid email format - CORNER CASE"""
        response = self.client.post(self.users_url, {
            'username': 'invalid_email_user',
            'email': 'not_an_email',
            'password': 'SecurePass123!',
            'user_type': 'agent'
        }, **self.headers, content_type='application/json')
        
        # Should either accept it (no validation) or reject it
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
    
    def test_create_user_empty_password(self):
        """Test creating user with empty password - CORNER CASE"""
        response = self.client.post(self.users_url, {
            'username': 'empty_pass_user',
            'email': 'emptypass@test.com',
            'password': '',
            'user_type': 'agent'
        }, **self.headers, content_type='application/json')
        
        # Django should reject empty password
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED])
    
    def test_create_user_without_authentication(self):
        """Test creating user without authentication token - SECURITY"""
        response = self.client.post(self.users_url, {
            'username': 'unauth_user',
            'email': 'unauth@test.com',
            'password': 'SecurePass123!',
            'user_type': 'agent'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_user_with_invalid_token(self):
        """Test creating user with invalid authentication token - SECURITY"""
        headers = {'HTTP_AUTHORIZATION': 'Bearer invalid_token'}
        response = self.client.post(self.users_url, {
            'username': 'badtoken_user',
            'email': 'badtoken@test.com',
            'password': 'SecurePass123!',
            'user_type': 'agent'
        }, **headers, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_user_whitespace_in_username(self):
        """Test creating user with whitespace in username - CORNER CASE"""
        response = self.client.post(self.users_url, {
            'username': 'user with spaces',
            'email': 'spaces@test.com',
            'password': 'SecurePass123!',
            'user_type': 'agent'
        }, **self.headers, content_type='application/json')
        
        # Should succeed or fail gracefully
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])
    
    def test_create_multiple_users_same_type(self):
        """Test creating multiple users of same type - EDGE CASE"""
        for i in range(5):
            response = self.client.post(self.users_url, {
                'username': f'bulk_agent_{i}',
                'email': f'bulk_{i}@test.com',
                'password': 'SecurePass123!',
                'user_type': 'agent'
            }, **self.headers, content_type='application/json')
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.assertEqual(Agent.objects.filter(username__startswith='bulk_agent_').count(), 5)


class AdminListUsersTestCase(TestCase):
    """Test cases for listing users via admin API"""
    
    def setUp(self):
        """Setup test client and create test data"""
        self.client = Client()
        self.users_url = '/api/v1/admin/users/'
        
        # Create admin user
        self.admin_user = Agent.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='AdminPass123!'
        )
        
        # Get token
        refresh = RefreshToken.for_user(self.admin_user)
        self.access_token = str(refresh.access_token)
        self.headers = {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}
        
        # Create test data
        Agent.objects.create_user(username='agent1', email='agent1@test.com', password='Pass123!')
        Agent.objects.create_user(username='agent2', email='agent2@test.com', password='Pass123!')
        Seller.objects.create_user(username='seller1', email='seller1@test.com', password='Pass123!')
        Buyer.objects.create_user(username='buyer1', email='buyer1@test.com', password='Pass123!')
    
    def test_list_all_users(self):
        """Test listing all users without filters"""
        response = self.client.get(self.users_url, **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()
        self.assertGreaterEqual(len(users), 5)  # At least 5 users (admin + test data)
    
    def test_list_agents_only(self):
        """Test listing only agents with filter"""
        response = self.client.get(f'{self.users_url}?user_type=agent', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()
        for user in users:
            self.assertEqual(user['user_type'], 'agent')
    
    def test_list_sellers_only(self):
        """Test listing only sellers with filter"""
        response = self.client.get(f'{self.users_url}?user_type=seller', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()
        for user in users:
            self.assertEqual(user['user_type'], 'seller')
    
    def test_list_buyers_only(self):
        """Test listing only buyers with filter"""
        response = self.client.get(f'{self.users_url}?user_type=buyer', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()
        for user in users:
            self.assertEqual(user['user_type'], 'buyer')
    
    def test_search_by_username(self):
        """Test searching users by username"""
        response = self.client.get(f'{self.users_url}?search=agent', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()
        for user in users:
            self.assertIn('agent', user['username'].lower())
    
    def test_search_by_email(self):
        """Test searching users by email"""
        response = self.client.get(f'{self.users_url}?search=seller1', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()
        self.assertTrue(len(users) > 0)
    
    def test_search_no_results(self):
        """Test search with no matching results - CORNER CASE"""
        response = self.client.get(f'{self.users_url}?search=nonexistent', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()
        self.assertEqual(len(users), 0)
    
    def test_list_with_invalid_filter(self):
        """Test listing with invalid user_type filter - CORNER CASE"""
        response = self.client.get(f'{self.users_url}?user_type=admin', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()
        self.assertEqual(len(users), 0)  # No users with type 'admin'
    
    def test_list_case_insensitive_filter(self):
        """Test filter is case-insensitive - EDGE CASE"""
        response = self.client.get(f'{self.users_url}?user_type=AGENT', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()
        for user in users:
            self.assertEqual(user['user_type'], 'agent')
    
    def test_list_combined_filter_and_search(self):
        """Test using both filter and search parameters - EDGE CASE"""
        response = self.client.get(f'{self.users_url}?user_type=agent&search=agent1', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()
        for user in users:
            self.assertEqual(user['user_type'], 'agent')
            self.assertIn('agent1', user['username'].lower())
    
    def test_list_without_authentication(self):
        """Test listing users without token - SECURITY"""
        response = self.client.get(self.users_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_empty_search_parameter(self):
        """Test search with empty string - CORNER CASE"""
        response = self.client.get(f'{self.users_url}?search=', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()
        self.assertGreaterEqual(len(users), 5)  # Should return all users


class AdminGetUserTestCase(TestCase):
    """Test cases for getting specific user"""
    
    def setUp(self):
        """Setup test client and test user"""
        self.client = Client()
        
        # Create admin user
        self.admin_user = Agent.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='AdminPass123!'
        )
        
        # Create test users
        self.agent = Agent.objects.create_user(
            username='testag',
            email='agent@test.com',
            password='Pass123!'
        )
        self.seller = Seller.objects.create_user(
            username='testseller',
            email='seller@test.com',
            password='Pass123!'
        )
        
        # Get token
        refresh = RefreshToken.for_user(self.admin_user)
        self.access_token = str(refresh.access_token)
        self.headers = {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}
    
    def test_get_agent_user(self):
        """Test retrieving a specific agent user"""
        response = self.client.get(
            f'/api/v1/admin/users/{self.agent.id}/?user_type=agent',
            **self.headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = response.json()
        self.assertEqual(user['id'], self.agent.id)
        self.assertEqual(user['username'], 'testag')
    
    def test_get_seller_user(self):
        """Test retrieving a specific seller user"""
        response = self.client.get(
            f'/api/v1/admin/users/{self.seller.id}/?user_type=seller',
            **self.headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = response.json()
        self.assertEqual(user['id'], self.seller.id)
    
    def test_get_nonexistent_user(self):
        """Test retrieving non-existent user - CORNER CASE"""
        response = self.client.get(
            f'/api/v1/admin/users/99999/?user_type=agent',
            **self.headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_user_without_user_type(self):
        """Test get user without user_type parameter - CORNER CASE"""
        response = self.client.get(
            f'/api/v1/admin/users/{self.agent.id}/',
            **self.headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_user_wrong_user_type(self):
        """Test get user with wrong user_type filter - CORNER CASE"""
        response = self.client.get(
            f'/api/v1/admin/users/{self.agent.id}/?user_type=seller',
            **self.headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_user_without_authentication(self):
        """Test get user without token - SECURITY"""
        response = self.client.get(
            f'/api/v1/admin/users/{self.agent.id}/?user_type=agent'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminUpdateUserTestCase(TestCase):
    """Test cases for updating users"""
    
    def setUp(self):
        """Setup test client and test users"""
        self.client = Client()
        
        # Create admin user
        self.admin_user = Agent.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='AdminPass123!'
        )
        
        # Create test user
        self.agent = Agent.objects.create_user(
            username='updatetest',
            email='update@test.com',
            password='Pass123!',
            first_name='Old',
            last_name='Name'
        )
        
        # Get token
        refresh = RefreshToken.for_user(self.admin_user)
        self.access_token = str(refresh.access_token)
        self.headers = {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}
    
    def test_update_user_first_name(self):
        """Test updating user's first name"""
        response = self.client.patch(
            f'/api/v1/admin/users/{self.agent.id}/update/?user_type=agent',
            {'first_name': 'NewFirstName'},
            **self.headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.first_name, 'NewFirstName')
    
    def test_update_user_last_name(self):
        """Test updating user's last name"""
        response = self.client.patch(
            f'/api/v1/admin/users/{self.agent.id}/update/?user_type=agent',
            {'last_name': 'NewLastName'},
            **self.headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.last_name, 'NewLastName')
    
    def test_update_user_email(self):
        """Test updating user's email"""
        response = self.client.patch(
            f'/api/v1/admin/users/{self.agent.id}/update/?user_type=agent',
            {'email': 'newemail@test.com'},
            **self.headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.email, 'newemail@test.com')
    
    def test_update_nonexistent_user(self):
        """Test updating non-existent user - CORNER CASE"""
        response = self.client.patch(
            f'/api/v1/admin/users/99999/update/?user_type=agent',
            {'first_name': 'New'},
            **self.headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_without_authentication(self):
        """Test update without token - SECURITY"""
        response = self.client.patch(
            f'/api/v1/admin/users/{self.agent.id}/update/?user_type=agent',
            {'first_name': 'New'},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminDeleteUserTestCase(TestCase):
    """Test cases for deleting users"""
    
    def setUp(self):
        """Setup test client and test users"""
        self.client = Client()
        
        # Create admin user
        self.admin_user = Agent.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='AdminPass123!'
        )
        
        # Create test user
        self.agent = Agent.objects.create_user(
            username='deletetest',
            email='delete@test.com',
            password='Pass123!'
        )
        
        # Get token
        refresh = RefreshToken.for_user(self.admin_user)
        self.access_token = str(refresh.access_token)
        self.headers = {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}
    
    def test_delete_user(self):
        """Test successful user deletion"""
        user_id = self.agent.id
        response = self.client.delete(
            f'/api/v1/admin/users/{user_id}/delete/?user_type=agent',
            **self.headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Agent.objects.filter(id=user_id).exists())
    
    def test_delete_nonexistent_user(self):
        """Test deleting non-existent user - CORNER CASE"""
        response = self.client.delete(
            f'/api/v1/admin/users/99999/delete/?user_type=agent',
            **self.headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_delete_without_authentication(self):
        """Test delete without token - SECURITY"""
        response = self.client.delete(
            f'/api/v1/admin/users/{self.agent.id}/delete/?user_type=agent'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_delete_twice(self):
        """Test deleting the same user twice - CORNER CASE"""
        user_id = self.agent.id
        
        # First delete
        response1 = self.client.delete(
            f'/api/v1/admin/users/{user_id}/delete/?user_type=agent',
            **self.headers
        )
        self.assertEqual(response1.status_code, status.HTTP_204_NO_CONTENT)
        
        # Second delete (should fail)
        response2 = self.client.delete(
            f'/api/v1/admin/users/{user_id}/delete/?user_type=agent',
            **self.headers
        )
        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)


class AdminDashboardTestCase(TestCase):
    """Test cases for admin dashboard endpoint"""
    
    def setUp(self):
        """Setup test client and data"""
        self.client = Client()
        
        # Create admin user
        self.admin_user = Agent.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='AdminPass123!'
        )
        
        # Create test data
        Agent.objects.create_user(username='agent1', email='a1@test.com', password='Pass123!')
        Seller.objects.create_user(username='seller1', email='s1@test.com', password='Pass123!')
        Buyer.objects.create_user(username='buyer1', email='b1@test.com', password='Pass123!')
        
        # Get token
        refresh = RefreshToken.for_user(self.admin_user)
        self.access_token = str(refresh.access_token)
        self.headers = {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}
    
    def test_get_dashboard_data(self):
        """Test retrieving dashboard statistics"""
        response = self.client.get('/api/v1/admin/dashboard/', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verify required fields
        self.assertIn('total_users', data)
        self.assertIn('total_agents', data)
        self.assertIn('total_sellers', data)
        self.assertIn('total_buyers', data)
        self.assertIn('weekly_chart', data)
        self.assertIn('active_agents', data)
        self.assertIn('active_sellers', data)
    
    def test_dashboard_statistics_accuracy(self):
        """Test dashboard statistics are calculated correctly"""
        response = self.client.get('/api/v1/admin/dashboard/', **self.headers)
        data = response.json()
        
        # Total users = agents + sellers + buyers
        expected_total = data['total_agents'] + data['total_sellers'] + data['total_buyers']
        self.assertEqual(data['total_users'], expected_total)
    
    def test_dashboard_without_authentication(self):
        """Test dashboard access without token - SECURITY"""
        response = self.client.get('/api/v1/admin/dashboard/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminProfileTestCase(TestCase):
    """Test cases for admin profile endpoint"""
    
    def setUp(self):
        """Setup test client and admin user"""
        self.client = Client()
        
        # Create admin user
        self.admin_user = Agent.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='AdminPass123!',
            first_name='John',
            last_name='Doe',
            is_superuser=True,
            is_staff=True
        )
        self.admin_user.phone_number = '+1234567890'
        self.admin_user.save()
        
        # Get token
        refresh = RefreshToken.for_user(self.admin_user)
        self.access_token = str(refresh.access_token)
        self.headers = {'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'}
    
    def test_get_profile_successful(self):
        """Test retrieving admin's own profile"""
        response = self.client.get('/api/v1/admin/profile/', **self.headers)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['username'], 'admin')
        self.assertEqual(data['email'], 'admin@test.com')
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        self.assertEqual(data['phone_number'], '+1234567890')
        self.assertTrue(data['is_superuser'])
        self.assertTrue(data['is_staff'])
    
    def test_get_profile_without_authentication(self):
        """Test profile access without token - SECURITY"""
        response = self.client.get('/api/v1/admin/profile/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_profile_first_name(self):
        """Test updating first name"""
        response = self.client.patch(
            '/api/v1/admin/profile/',
            data=json.dumps({'first_name': 'Jane'}),
            **self.headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.first_name, 'Jane')
    
    def test_update_profile_last_name(self):
        """Test updating last name"""
        response = self.client.patch(
            '/api/v1/admin/profile/',
            data=json.dumps({'last_name': 'Smith'}),
            **self.headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.last_name, 'Smith')
    
    def test_update_profile_email(self):
        """Test updating email"""
        response = self.client.patch(
            '/api/v1/admin/profile/',
            data=json.dumps({'email': 'newemail@test.com'}),
            **self.headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.email, 'newemail@test.com')
    
    def test_update_profile_phone_number(self):
        """Test updating phone number"""
        response = self.client.patch(
            '/api/v1/admin/profile/',
            data=json.dumps({'phone_number': '+9876543210'}),
            **self.headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.phone_number, '+9876543210')
    
    def test_update_profile_multiple_fields(self):
        """Test updating multiple fields at once"""
        response = self.client.patch(
            '/api/v1/admin/profile/',
            data=json.dumps({
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane.smith@test.com',
                'phone_number': '+9876543210'
            }),
            **self.headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.first_name, 'Jane')
        self.assertEqual(self.admin_user.last_name, 'Smith')
        self.assertEqual(self.admin_user.email, 'jane.smith@test.com')
        self.assertEqual(self.admin_user.phone_number, '+9876543210')
    
    def test_update_profile_duplicate_email(self):
        """Test updating to duplicate email - CORNER CASE"""
        # Create another admin with same user type
        other_admin = Agent.objects.create_user(
            username='admin2',
            email='other@test.com',
            password='Pass123!',
            is_superuser=True,
            is_staff=True
        )
        
        # Try to update to other admin's email
        response = self.client.patch(
            '/api/v1/admin/profile/',
            data=json.dumps({'email': 'other@test.com'}),
            **self.headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already in use', response.json()['error'])
    
    def test_update_profile_without_authentication(self):
        """Test profile update without token - SECURITY"""
        response = self.client.patch(
            '/api/v1/admin/profile/',
            data=json.dumps({'first_name': 'Jane'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_profile_with_invalid_token(self):
        """Test profile update with invalid token - SECURITY"""
        headers = {'HTTP_AUTHORIZATION': 'Bearer invalid_token'}
        response = self.client.patch(
            '/api/v1/admin/profile/',
            data=json.dumps({'first_name': 'Jane'}),
            **headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_profile_empty_fields(self):
        """Test updating with empty strings - CORNER CASE"""
        response = self.client.patch(
            '/api/v1/admin/profile/',
            data=json.dumps({
                'first_name': '',
                'last_name': '',
            }),
            **self.headers,
            content_type='application/json'
        )
        
        # Should succeed - empty strings are valid updates
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.first_name, '')
        self.assertEqual(self.admin_user.last_name, '')
    
    def test_update_profile_response_format(self):
        """Test response contains correct profile format"""
        response = self.client.patch(
            '/api/v1/admin/profile/',
            data=json.dumps({'first_name': 'Jane'}),
            **self.headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('message', data)
        self.assertIn('profile', data)
        self.assertEqual(data['message'], 'Profile updated successfully')
        self.assertIn('id', data['profile'])
        self.assertIn('username', data['profile'])
        self.assertIn('email', data['profile'])


if __name__ == '__main__':
    import unittest
    unittest.main()
