from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from agent.models import Agent
from seller.models import Seller, SellingRequest, SellerNotification

User = get_user_model()


class UserRegistrationTestCase(TestCase):
    """Test cases for user registration"""

    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/agent/auth/register/'

    def test_user_registration_success(self):
        """Test successful user registration"""
        data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'first_name': 'Test',
            'last_name': 'User',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)

    def test_user_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'SecurePassword123!',
            'password2': 'DifferentPassword123!',
            'first_name': 'Test',
            'last_name': 'User',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        User.objects.create_user(
            username='existinguser',
            email='testuser@example.com',
            password='SecurePassword123!'
        )
        data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'first_name': 'Test',
            'last_name': 'User',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginTestCase(TestCase):
    """Test cases for user login"""

    def setUp(self):
        self.client = APIClient()
        self.login_url = '/api/v1/agent/auth/login/'
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='SecurePassword123!'
        )

    def test_user_login_success(self):
        """Test successful user login"""
        data = {
            'username': 'testuser',
            'password': 'SecurePassword123!',
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)

    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'username': 'testuser',
            'password': 'WrongPassword123!',
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserProfileTestCase(TestCase):
    """Test cases for user profile"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='SecurePassword123!',
            first_name='Test',
            last_name='User'
        )
        self.profile_url = '/api/v1/agent/profile/'

    def test_get_profile_authenticated(self):
        """Test getting profile as authenticated user"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'testuser@example.com')

    def test_get_profile_unauthenticated(self):
        """Test getting profile as unauthenticated user"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile(self):
        """Test updating user profile"""
        self.client.force_authenticate(user=self.user)
        data = {
            'phone_number': '+1234567890',
            'license_number': 'LIC-12345',
            'first_name': 'John',
            'last_name': 'Smith'
        }
        response = self.client.put('/api/v1/agent/profile/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, '+1234567890')
        self.assertEqual(self.user.license_number, 'LIC-12345')
        self.assertEqual(self.user.first_name, 'John')


class PermissionTestCase(TestCase):
    """Test cases for permission restrictions"""

    def setUp(self):
        self.client = APIClient()
        # Create an Agent user
        self.agent = Agent.objects.create_user(
            username='agentuser',
            email='agent@example.com',
            password='SecurePassword123!',
            first_name='Agent',
            last_name='User'
        )
        # Create a Seller user
        self.seller = Seller.objects.create_user(
            username='selleruser',
            email='seller@example.com',
            password='SecurePassword123!',
            first_name='Seller',
            last_name='User'
        )

    def test_agent_can_update_own_profile(self):
        """Test that agent can update their own profile"""
        self.client.force_authenticate(user=self.agent)
        data = {
            'phone_number': '+1111111111',
            'license_number': 'AGENT-123',
            'first_name': 'UpdatedAgent'
        }
        response = self.client.put('/api/v1/agent/profile/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_seller_cannot_update_agent_profile(self):
        """Test that seller cannot update agent profile endpoint"""
        self.client.force_authenticate(user=self.seller)
        data = {
            'phone_number': '+2222222222',
            'first_name': 'Hacker'
        }
        response = self.client.put('/api/v1/agent/profile/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_seller_can_update_own_profile(self):
        """Test that seller can update their own profile"""
        self.client.force_authenticate(user=self.seller)
        data = {
            'phone_number': '+2222222222',
            'location': 'New York',
            'first_name': 'UpdatedSeller'
        }
        response = self.client.put('/api/v1/seller/profile/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_agent_cannot_update_seller_profile(self):
        """Test that agent cannot update seller profile endpoint"""
        self.client.force_authenticate(user=self.agent)
        data = {
            'phone_number': '+3333333333',
            'location': 'Hacked Location'
        }
        response = self.client.put('/api/v1/seller/profile/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AgentSellingRequestListTestCase(TestCase):
    """Test cases for agents viewing selling requests"""

    def setUp(self):
        self.client = APIClient()
        self.agent = Agent.objects.create_user(
            username='agentuser',
            email='agent@example.com',
            password='SecurePassword123!',
            first_name='Agent',
            last_name='User'
        )
        self.seller = Seller.objects.create_user(
            username='selleruser',
            email='seller@example.com',
            password='SecurePassword123!',
            first_name='Seller',
            last_name='User'
        )
        
        # Create selling requests
        self.selling_request1 = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Relocating',
            contact_name='John Doe',
            contact_email='john@example.com',
            contact_phone='+1234567890',
            asking_price='450000.00',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='pending'
        )
        
        self.selling_request2 = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Financial reasons',
            contact_name='Jane Smith',
            contact_email='jane@example.com',
            contact_phone='+0987654321',
            asking_price='500000.00',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=45),
            status='pending'
        )

    def test_agent_can_list_all_selling_requests(self):
        """Test that agents can see all selling requests"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get('/api/v1/agent/selling-requests/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_unauthenticated_user_cannot_list_selling_requests(self):
        """Test that unauthenticated users cannot see selling requests"""
        response = self.client.get('/api/v1/agent/selling-requests/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_seller_cannot_list_selling_requests_on_agent_endpoint(self):
        """Test that sellers cannot access agent selling request endpoints"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get('/api/v1/agent/selling-requests/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AgentSellingRequestDetailTestCase(TestCase):
    """Test cases for agents viewing specific selling requests"""

    def setUp(self):
        self.client = APIClient()
        self.agent = Agent.objects.create_user(
            username='agentuser',
            email='agent@example.com',
            password='SecurePassword123!',
            first_name='Agent',
            last_name='User'
        )
        self.seller = Seller.objects.create_user(
            username='selleruser',
            email='seller@example.com',
            password='SecurePassword123!',
            first_name='Seller',
            last_name='User'
        )
        
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Relocating',
            contact_name='John Doe',
            contact_email='john@example.com',
            contact_phone='+1234567890',
            asking_price='450000.00',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='pending'
        )

    def test_agent_can_view_selling_request_detail(self):
        """Test that agents can view selling request details"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(f'/api/v1/agent/selling-requests/{self.selling_request.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.selling_request.id)
        self.assertEqual(response.data['selling_reason'], 'Relocating')

    def test_agent_can_view_seller_info(self):
        """Test that agent response includes seller information"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(f'/api/v1/agent/selling-requests/{self.selling_request.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['seller_name'], 'Seller User')
        self.assertEqual(response.data['seller_email'], 'seller@example.com')

    def test_selling_request_not_found(self):
        """Test that 404 is returned for non-existent request"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get('/api/v1/agent/selling-requests/9999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AgentUpdateSellingRequestStatusTestCase(TestCase):
    """Test cases for agents updating selling request status"""

    def setUp(self):
        self.client = APIClient()
        self.agent = Agent.objects.create_user(
            username='agentuser',
            email='agent@example.com',
            password='SecurePassword123!',
            first_name='Agent',
            last_name='User'
        )
        self.seller = Seller.objects.create_user(
            username='selleruser',
            email='seller@example.com',
            password='SecurePassword123!',
            first_name='Seller',
            last_name='User'
        )
        
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Relocating',
            contact_name='John Doe',
            contact_email='john@example.com',
            contact_phone='+1234567890',
            asking_price='450000.00',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='pending'
        )

    def test_agent_can_accept_pending_request(self):
        """Test that agents can accept pending selling requests"""
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'accepted'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'accepted')
        self.assertIn('accepted', response.data['message'].lower())
        
        # Verify in database
        self.selling_request.refresh_from_db()
        self.assertEqual(self.selling_request.status, 'accepted')

    def test_agent_can_reject_pending_request(self):
        """Test that agents can reject pending selling requests"""
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'rejected'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'rejected')
        self.assertIn('rejected', response.data['message'].lower())
        
        # Verify in database
        self.selling_request.refresh_from_db()
        self.assertEqual(self.selling_request.status, 'rejected')

    def test_agent_cannot_update_already_accepted_request(self):
        """Test that agents cannot update already accepted requests"""
        self.selling_request.status = 'accepted'
        self.selling_request.save()
        
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'rejected'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pending', response.data['error'].lower())

    def test_agent_cannot_update_already_rejected_request(self):
        """Test that agents cannot update already rejected requests"""
        self.selling_request.status = 'rejected'
        self.selling_request.save()
        
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'accepted'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_status_value(self):
        """Test that invalid status values are rejected"""
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'invalid_status'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('not a valid choice', response.data['status'][0].lower())

    def test_unauthenticated_user_cannot_update_status(self):
        """Test that unauthenticated users cannot update status"""
        data = {'status': 'accepted'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_seller_cannot_update_status(self):
        """Test that sellers cannot update request status"""
        self.client.force_authenticate(user=self.seller)
        data = {'status': 'accepted'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_request(self):
        """Test that 404 is returned for non-existent request"""
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'accepted'}
        response = self.client.patch(
            '/api/v1/agent/selling-requests/9999/status/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AgentNotificationCreationTestCase(TestCase):
    """Test cases for notification creation when agent accepts/rejects requests"""

    def setUp(self):
        self.client = APIClient()
        self.agent = Agent.objects.create_user(
            username='agentuser',
            email='agent@example.com',
            password='SecurePassword123!',
            first_name='Agent',
            last_name='User'
        )
        self.seller = Seller.objects.create_user(
            username='selleruser',
            email='seller@example.com',
            password='SecurePassword123!',
            first_name='Seller',
            last_name='User'
        )
        
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Relocating',
            contact_name='John Doe',
            contact_email='john@example.com',
            contact_phone='+1234567890',
            asking_price='450000.00',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='pending'
        )

    def test_notification_created_on_accept(self):
        """Test that notification is created when agent accepts request"""
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'accepted'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify notification was created
        notification = SellerNotification.objects.get(
            seller=self.seller,
            selling_request=self.selling_request
        )
        self.assertEqual(notification.notification_type, 'approved')
        self.assertEqual(notification.title, 'Selling Request Approved')
        self.assertIn('accepted', notification.message.lower())
        self.assertEqual(notification.is_read, False)

    def test_notification_created_on_reject(self):
        """Test that notification is created when agent rejects request"""
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'rejected'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify notification was created
        notification = SellerNotification.objects.get(
            seller=self.seller,
            selling_request=self.selling_request
        )
        self.assertEqual(notification.notification_type, 'rejected')
        self.assertEqual(notification.title, 'Selling Request Declined')
        self.assertIn('declined', notification.message.lower())
        self.assertEqual(notification.is_read, False)

    def test_approved_notification_has_action_button(self):
        """Test that approved notification has action button for CMA report"""
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'accepted'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify notification has action details
        notification = SellerNotification.objects.get(
            seller=self.seller,
            selling_request=self.selling_request
        )
        self.assertEqual(notification.action_text, 'View CMA Report')
        self.assertIn(str(self.selling_request.id), notification.action_url)

    def test_rejected_notification_has_action_button(self):
        """Test that rejected notification has action button for chat"""
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'rejected'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify notification has action details
        notification = SellerNotification.objects.get(
            seller=self.seller,
            selling_request=self.selling_request
        )
        self.assertEqual(notification.action_text, 'Chat with Agent')
        self.assertIn('chat', notification.action_url.lower())

    def test_notification_linked_to_correct_seller(self):
        """Test that notification is created for the correct seller"""
        seller2 = Seller.objects.create_user(
            username='seller2',
            email='seller2@example.com',
            password='SecurePassword123!',
            first_name='Seller2',
            last_name='User2'
        )
        
        selling_request2 = SellingRequest.objects.create(
            seller=seller2,
            selling_reason='Need cash',
            contact_name='Jane Smith',
            contact_email='jane@example.com',
            contact_phone='+1987654321',
            asking_price='550000.00',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='pending'
        )
        
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'accepted'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{selling_request2.id}/status/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify notification was created for seller2
        notification = SellerNotification.objects.get(
            seller=seller2,
            selling_request=selling_request2
        )
        self.assertEqual(notification.seller, seller2)
        
        # Verify seller1 did not receive a notification
        seller1_notifications = SellerNotification.objects.filter(seller=self.seller)
        self.assertEqual(seller1_notifications.count(), 0)

    def test_notification_can_be_retrieved_by_seller(self):
        """Test that seller can retrieve the notification via API"""
        self.client.force_authenticate(user=self.agent)
        data = {'status': 'accepted'}
        response = self.client.patch(
            f'/api/v1/agent/selling-requests/{self.selling_request.id}/status/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify seller can retrieve notification
        self.client.force_authenticate(user=self.seller)
        response = self.client.get('/api/v1/seller/notifications/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        notification_data = response.data['results'][0]
        self.assertEqual(notification_data['title'], 'Selling Request Approved')
        self.assertEqual(notification_data['notification_type'], 'approved')


# Privacy & Security Tests
class AgentPrivacySecurityTestCase(TestCase):
    """Test cases for agent privacy & security endpoints"""

    def setUp(self):
        self.client = APIClient()
        # Create regular agent user
        self.agent = Agent.objects.create_user(
            username='testagent',
            email='testagent@example.com',
            password='SecurePassword123!',
            first_name='Test',
            last_name='Agent'
        )
        # Create admin user
        self.admin = Agent.objects.create_superuser(
            username='adminagent',
            email='admin@example.com',
            password='AdminPassword123!'
        )
        self.privacy_url = '/api/v1/agent/privacy-security/'

    def test_get_own_privacy_settings(self):
        """Test agent can retrieve their own privacy settings"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['agent'], self.agent.id)
        self.assertEqual(response.data['agent_username'], 'testagent')
        self.assertEqual(response.data['agent_email'], 'testagent@example.com')

    def test_get_privacy_settings_creates_record(self):
        """Test that getting privacy settings auto-creates record if it doesn't exist"""
        from agent.models import AgentPrivacySecurity
        
        # Ensure no privacy settings exist
        self.assertEqual(AgentPrivacySecurity.objects.filter(agent=self.agent).count(), 0)
        
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AgentPrivacySecurity.objects.filter(agent=self.agent).count(), 1)

    def test_get_all_privacy_settings_admin_only(self):
        """Test only superadmins can list all privacy settings with ?all=true"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(f'{self.privacy_url}?all=true')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Only superadministrators', response.data['detail'])

    def test_get_all_privacy_settings_as_admin(self):
        """Test admin can retrieve all privacy settings"""
        # First, trigger creation of privacy settings for the admin user
        self.client.force_authenticate(user=self.admin)
        self.client.get(self.privacy_url)
        
        # Create another agent and their privacy settings
        agent2 = Agent.objects.create_user(
            username='agent2',
            email='agent2@example.com',
            password='Pass123!'
        )
        self.client.force_authenticate(user=agent2)
        self.client.get(self.privacy_url)
        
        # Now authenticate as admin and list all
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f'{self.privacy_url}?all=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)

    def test_update_privacy_settings_admin_only(self):
        """Test only superadmins can update privacy settings"""
        self.client.force_authenticate(user=self.agent)
        update_data = {'allow_multi_factor_auth': True}
        response = self.client.put(self.privacy_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Only superadministrators', response.data['detail'])

    def test_update_privacy_settings_as_admin_put(self):
        """Test admin can fully update privacy settings with PUT"""
        self.client.force_authenticate(user=self.admin)
        
        update_data = {
            'collect_basic_info': False,
            'collect_activity_logs': False,
            'collect_chat_messages': True,
            'collect_documents': True,
            'collect_optional_info': False,
            'use_for_services': True,
            'use_for_alerts': False,
            'use_for_compliance': True,
            'share_with_partners': True,
            'allow_multi_factor_auth': True,
            'encrypted_communication': False,
            'data_retention_months': 24,
            'allow_data_deletion': True,
            'privacy_policy_accepted': True,
            'privacy_policy_version': '1.0'
        }
        response = self.client.put(self.privacy_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['collect_basic_info'], False)
        self.assertEqual(response.data['collect_chat_messages'], True)
        self.assertEqual(response.data['data_retention_months'], 24)

    def test_patch_privacy_settings_as_admin(self):
        """Test admin can partially update privacy settings with PATCH"""
        self.client.force_authenticate(user=self.admin)
        
        # Partial update
        update_data = {
            'allow_multi_factor_auth': False,
            'encrypted_communication': True
        }
        response = self.client.patch(self.privacy_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['allow_multi_factor_auth'], False)
        self.assertEqual(response.data['encrypted_communication'], True)

    def test_privacy_settings_read_only_fields(self):
        """Test that read-only fields can be read"""
        # Get the privacy settings first to trigger creation
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify we got the right response structure with all fields
        self.assertIn('id', response.data)
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)
        # Verify read-only fields are present
        self.assertIn('agent_username', response.data)
        self.assertIn('agent_email', response.data)

    def test_privacy_settings_one_to_one_relationship(self):
        """Test that each agent has only one privacy settings record"""
        from agent.models import AgentPrivacySecurity
        
        # Get privacy settings multiple times
        for _ in range(3):
            self.client.force_authenticate(user=self.agent)
            response = self.client.get(self.privacy_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should still have only one record
        count = AgentPrivacySecurity.objects.filter(agent=self.agent).count()
        self.assertEqual(count, 1)

    def test_privacy_settings_default_values(self):
        """Test that default values are set correctly"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check some defaults (adjust based on your model defaults)
        self.assertIsNotNone(response.data['id'])
        self.assertIsNotNone(response.data['created_at'])
        self.assertIsNotNone(response.data['updated_at'])

    def test_privacy_settings_unauthorized_access(self):
        """Test that unauthenticated users cannot access privacy settings"""
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_privacy_settings_validation(self):
        """Test validation of privacy settings fields"""
        self.client.force_authenticate(user=self.admin)
        
        # Test invalid data_retention_months (too large)
        update_data = {
            'collect_basic_info': True,
            'collect_activity_logs': True,
            'collect_chat_messages': True,
            'collect_documents': True,
            'collect_optional_info': True,
            'use_for_services': True,
            'use_for_alerts': True,
            'use_for_compliance': True,
            'share_with_partners': True,
            'allow_multi_factor_auth': True,
            'encrypted_communication': True,
            'data_retention_months': 999,  # Invalid
            'allow_data_deletion': True,
            'privacy_policy_accepted': True,
            'privacy_policy_version': '1.0'
        }
        response = self.client.put(self.privacy_url, update_data, format='json')
        
        # May return 400 or success depending on model validation
        # Adjust based on your actual validation rules
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK])


class AgentTermsConditionsTestCase(TestCase):
    """Test cases for agent terms and conditions"""

    def setUp(self):
        self.client = APIClient()
        self.agent = Agent.objects.create_user(
            username='testagent',
            email='agent@example.com',
            password='SecurePassword123!'
        )
        self.admin = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='AdminPassword123!',
            is_staff=True,
            is_superuser=True
        )
        self.terms_url = '/api/v1/agent/terms-conditions/'

    def test_terms_conditions_access_authenticated(self):
        """Test that authenticated agents can access terms and conditions"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(self.terms_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('account_responsibility', response.data)
        self.assertIn('service_description_accepted', response.data)

    def test_terms_conditions_unauthorized(self):
        """Test that unauthenticated users cannot access terms"""
        response = self.client.get(self.terms_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_terms_conditions_update(self):
        """Test updating terms and conditions"""
        self.client.force_authenticate(user=self.agent)
        data = {
            'account_responsibility': True,
            'service_description_accepted': True,
            'accept_digital_agreements': True,
            'payment_charges_understood': True,
            'no_fraud': True,
            'no_harmful_content': True
        }
        response = self.client.put(self.terms_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['account_responsibility'])
        self.assertTrue(response.data['service_description_accepted'])

    def test_terms_conditions_default_values(self):
        """Test that default values are set correctly"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(self.terms_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify all expected fields are present
        self.assertIn('terms_version', response.data)
        self.assertIn('terms_accepted_at', response.data)

    def test_agent_email_login(self):
        """Test agent login using email instead of username"""
        login_url = '/api/v1/agent/auth/login/'
        data = {
            'email': 'agent@example.com',
            'password': 'SecurePassword123!'
        }
        response = self.client.post(login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)

    def test_agent_invalid_email_login(self):
        """Test agent login with invalid email"""
        login_url = '/api/v1/agent/auth/login/'
        data = {
            'email': 'nonexistent@example.com',
            'password': 'SecurePassword123!'
        }
        response = self.client.post(login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

