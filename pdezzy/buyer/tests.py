from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import Buyer

User = Buyer


class BuyerRegistrationTestCase(TestCase):
    """Test cases for buyer registration"""

    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/buyer/auth/register/'

    def test_buyer_registration_success(self):
        """Test successful buyer registration"""
        data = {
            'username': 'buyer1',
            'email': 'buyer1@example.com',
            'password': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)

    def test_buyer_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        data = {
            'username': 'buyer1',
            'email': 'buyer1@example.com',
            'password': 'SecurePassword123!',
            'password2': 'DifferentPassword123!',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_buyer_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        User.objects.create_user(
            username='existingbuyer',
            email='buyer1@example.com',
            password='SecurePassword123!'
        )
        data = {
            'username': 'buyer1',
            'email': 'buyer1@example.com',
            'password': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BuyerLoginTestCase(TestCase):
    """Test cases for buyer login"""

    def setUp(self):
        self.client = APIClient()
        self.login_url = '/api/v1/buyer/auth/login/'
        self.buyer = User.objects.create_user(
            username='buyer1',
            email='buyer1@example.com',
            password='SecurePassword123!'
        )

    def test_buyer_login_success(self):
        """Test successful buyer login"""
        data = {
            'username': 'buyer1',
            'password': 'SecurePassword123!',
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)

    def test_buyer_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'username': 'buyer1',
            'password': 'WrongPassword123!',
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BuyerProfileTestCase(TestCase):
    """Test cases for buyer profile"""

    def setUp(self):
        self.client = APIClient()
        self.buyer = User.objects.create_user(
            username='buyer1',
            email='buyer1@example.com',
            password='SecurePassword123!',
            first_name='John',
            last_name='Doe'
        )
        self.profile_url = '/api/v1/buyer/profile/'

    def test_get_profile_authenticated(self):
        """Test getting profile as authenticated buyer"""
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'buyer1')
        self.assertEqual(response.data['email'], 'buyer1@example.com')

    def test_get_profile_unauthenticated(self):
        """Test getting profile as unauthenticated buyer"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile(self):
        """Test updating buyer profile"""
        self.client.force_authenticate(user=self.buyer)
        data = {
            'phone_number': '+1234567890',
            'price_range': '$200,000 - $500,000',
            'location': 'New York',
            'bedrooms': 3,
            'bathrooms': 2,
            'first_name': 'John',
            'last_name': 'Doe'
        }
        response = self.client.put('/api/v1/buyer/profile/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.phone_number, '+1234567890')
        self.assertEqual(self.buyer.price_range, '$200,000 - $500,000')
        self.assertEqual(self.buyer.location, 'New York')
        self.assertEqual(self.buyer.bedrooms, 3)


# Privacy & Security Tests
class BuyerPrivacySecurityTestCase(TestCase):
    """Test cases for buyer privacy & security endpoints"""

    def setUp(self):
        self.client = APIClient()
        # Create regular buyer user
        self.buyer = Buyer.objects.create_user(
            username='testbuyer',
            email='testbuyer@example.com',
            password='SecurePassword123!',
            first_name='Test',
            last_name='Buyer'
        )
        # Create admin user
        self.admin = Buyer.objects.create_superuser(
            username='adminbuyer',
            email='admin@example.com',
            password='AdminPassword123!'
        )
        self.privacy_url = '/api/v1/buyer/privacy-security/'

    def test_get_own_privacy_settings(self):
        """Test buyer can retrieve their own privacy settings"""
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['buyer'], self.buyer.id)
        self.assertEqual(response.data['buyer_username'], 'testbuyer')
        self.assertEqual(response.data['buyer_email'], 'testbuyer@example.com')

    def test_get_privacy_settings_creates_record(self):
        """Test that getting privacy settings auto-creates record if it doesn't exist"""
        from buyer.models import BuyerPrivacySecurity
        
        # Ensure no privacy settings exist
        self.assertEqual(BuyerPrivacySecurity.objects.filter(buyer=self.buyer).count(), 0)
        
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BuyerPrivacySecurity.objects.filter(buyer=self.buyer).count(), 1)

    def test_get_all_privacy_settings_admin_only(self):
        """Test only superadmins can list all privacy settings with ?all=true"""
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(f'{self.privacy_url}?all=true')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Only superadministrators', response.data['detail'])

    def test_get_all_privacy_settings_as_admin(self):
        """Test admin can retrieve all privacy settings"""
        # First, trigger creation of privacy settings for the admin user
        self.client.force_authenticate(user=self.admin)
        self.client.get(self.privacy_url)
        
        # Create another buyer and their privacy settings
        buyer2 = Buyer.objects.create_user(
            username='buyer2',
            email='buyer2@example.com',
            password='Pass123!'
        )
        self.client.force_authenticate(user=buyer2)
        self.client.get(self.privacy_url)
        
        # Now authenticate as admin and list all
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f'{self.privacy_url}?all=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)

    def test_update_privacy_settings_admin_only(self):
        """Test only superadmins can update privacy settings"""
        self.client.force_authenticate(user=self.buyer)
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
            'collect_property_preferences': True,
            'use_for_services': True,
            'use_for_alerts': False,
            'use_for_compliance': True,
            'use_for_recommendations': True,
            'share_with_partners': True,
            'share_with_legal': False,
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
        self.assertEqual(response.data['collect_property_preferences'], True)
        self.assertEqual(response.data['data_retention_months'], 24)

    def test_patch_privacy_settings_as_admin(self):
        """Test admin can partially update privacy settings with PATCH"""
        self.client.force_authenticate(user=self.admin)
        
        # Partial update
        update_data = {
            'allow_multi_factor_auth': False,
            'encrypted_communication': True,
            'use_for_recommendations': False
        }
        response = self.client.patch(self.privacy_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['allow_multi_factor_auth'], False)
        self.assertEqual(response.data['encrypted_communication'], True)
        self.assertEqual(response.data['use_for_recommendations'], False)

    def test_privacy_settings_buyer_specific_fields(self):
        """Test buyer-specific privacy fields are present"""
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check buyer-specific fields
        self.assertIn('collect_property_preferences', response.data)
        self.assertIn('use_for_recommendations', response.data)
        self.assertIn('share_with_legal', response.data)

    def test_privacy_settings_one_to_one_relationship(self):
        """Test that each buyer has only one privacy settings record"""
        from buyer.models import BuyerPrivacySecurity
        
        # Get privacy settings multiple times
        for _ in range(3):
            self.client.force_authenticate(user=self.buyer)
            response = self.client.get(self.privacy_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should still have only one record
        count = BuyerPrivacySecurity.objects.filter(buyer=self.buyer).count()
        self.assertEqual(count, 1)

    def test_privacy_settings_unauthorized_access(self):
        """Test that unauthenticated users cannot access privacy settings"""
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BuyerTermsConditionsTestCase(TestCase):
    """Test cases for buyer terms and conditions"""

    def setUp(self):
        self.client = APIClient()
        self.buyer = Buyer.objects.create_user(
            username='testbuyer',
            email='buyer@example.com',
            password='SecurePassword123!'
        )
        self.register_url = '/api/v1/buyer/auth/register/'
        self.terms_url = '/api/v1/buyer/terms-conditions/'

    def test_buyer_terms_conditions_access(self):
        """Test that authenticated buyers can access terms and conditions"""
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(self.terms_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('account_responsibility', response.data)

    def test_buyer_terms_update(self):
        """Test updating buyer terms and conditions"""
        self.client.force_authenticate(user=self.buyer)
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

    def test_buyer_terms_unauthorized(self):
        """Test that unauthenticated users cannot access terms"""
        response = self.client.get(self.terms_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_buyer_registration_with_all_fields(self):
        """Test buyer registration with all preference fields"""
        data = {
            'name': 'Jane Smith',
            'email': 'newbuyer@example.com',
            'password': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'phone_number': '5551234567',
            'price_range': '$400,000 - $600,000',
            'location': 'San Francisco, CA',
            'bedrooms': 3,
            'bathrooms': 2
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        buyer = Buyer.objects.get(email='newbuyer@example.com')
        self.assertEqual(buyer.phone_number, '5551234567')
        self.assertEqual(buyer.price_range, '$400,000 - $600,000')
        self.assertEqual(buyer.bedrooms, 3)

    def test_buyer_email_login(self):
        """Test buyer login using email"""
        login_url = '/api/v1/buyer/auth/login/'
        data = {
            'email': 'buyer@example.com',
            'password': 'SecurePassword123!'
        }
        response = self.client.post(login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)

    def test_buyer_wrong_password(self):
        """Test buyer login with wrong password"""
        login_url = '/api/v1/buyer/auth/login/'
        data = {
            'email': 'buyer@example.com',
            'password': 'WrongPassword123!'
        }
        response = self.client.post(login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

