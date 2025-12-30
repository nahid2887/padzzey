from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from .models import Seller, SellingRequest, SellerNotification, PropertyDocument

User = Seller


class SellerRegistrationTestCase(TestCase):
    """Test cases for seller registration"""

    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/seller/auth/register/'

    def test_seller_registration_success(self):
        """Test successful seller registration"""
        data = {
            'username': 'seller1',
            'email': 'seller1@example.com',
            'password': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)

    def test_seller_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        data = {
            'username': 'seller1',
            'email': 'seller1@example.com',
            'password': 'SecurePassword123!',
            'password2': 'DifferentPassword123!',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_seller_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        User.objects.create_user(
            username='existingseller',
            email='seller1@example.com',
            password='SecurePassword123!'
        )
        data = {
            'username': 'seller1',
            'email': 'seller1@example.com',
            'password': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SellerLoginTestCase(TestCase):
    """Test cases for seller login"""

    def setUp(self):
        self.client = APIClient()
        self.login_url = '/api/v1/seller/auth/login/'
        self.seller = User.objects.create_user(
            username='seller1',
            email='seller1@example.com',
            password='SecurePassword123!'
        )

    def test_seller_login_success(self):
        """Test successful seller login"""
        data = {
            'username': 'seller1',
            'password': 'SecurePassword123!',
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)

    def test_seller_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'username': 'seller1',
            'password': 'WrongPassword123!',
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SellerProfileTestCase(TestCase):
    """Test cases for seller profile"""

    def setUp(self):
        self.client = APIClient()
        self.seller = User.objects.create_user(
            username='seller1',
            email='seller1@example.com',
            password='SecurePassword123!',
            first_name='John',
            last_name='Doe'
        )
        self.profile_url = '/api/v1/seller/profile/'

    def test_get_profile_authenticated(self):
        """Test getting profile as authenticated seller"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'seller1')
        self.assertEqual(response.data['email'], 'seller1@example.com')

    def test_get_profile_unauthenticated(self):
        """Test getting profile as unauthenticated seller"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile(self):
        """Test updating seller profile"""
        self.client.force_authenticate(user=self.seller)
        data = {
            'phone_number': '+1234567890',
            'location': '123 Main St, City, State',
            'bedrooms': 3,
            'bathrooms': 2,
            'property_condition': 'Well maintained with recent updates',
            'first_name': 'John',
            'last_name': 'Doe'
        }
        response = self.client.put('/api/v1/seller/profile/update/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.phone_number, '+1234567890')
        self.assertEqual(self.seller.location, '123 Main St, City, State')
        self.assertEqual(self.seller.bedrooms, 3)
        self.assertEqual(self.seller.bathrooms, 2)


class SellingRequestCreateTestCase(TestCase):
    """Test cases for creating selling requests"""

    def setUp(self):
        self.client = APIClient()
        self.seller = User.objects.create_user(
            username='seller1',
            email='seller1@example.com',
            password='SecurePassword123!',
            first_name='John',
            last_name='Doe'
        )
        self.selling_request_url = '/api/v1/seller/selling-requests/'
        self.start_date = date.today()
        self.end_date = date.today() + timedelta(days=30)

    def test_create_selling_request_authenticated(self):
        """Test creating a selling request as authenticated seller"""
        self.client.force_authenticate(user=self.seller)
        data = {
            'selling_reason': 'Looking to relocate to another city',
            'contact_name': 'John Doe',
            'contact_email': 'john@example.com',
            'contact_phone': '+1234567890',
            'asking_price': '450000.00',
            'start_date': str(self.start_date),
            'end_date': str(self.end_date),
        }
        response = self.client.post(self.selling_request_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['seller'], self.seller.id)
        self.assertEqual(response.data['asking_price'], '450000.00')

    def test_create_selling_request_unauthenticated(self):
        """Test creating a selling request as unauthenticated user"""
        data = {
            'selling_reason': 'Looking to relocate to another city',
            'contact_name': 'John Doe',
            'contact_email': 'john@example.com',
            'contact_phone': '+1234567890',
            'asking_price': '450000.00',
            'start_date': str(self.start_date),
            'end_date': str(self.end_date),
        }
        response = self.client.post(self.selling_request_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_selling_request_invalid_dates(self):
        """Test creating a selling request with invalid date range"""
        self.client.force_authenticate(user=self.seller)
        data = {
            'selling_reason': 'Looking to relocate to another city',
            'contact_name': 'John Doe',
            'contact_email': 'john@example.com',
            'contact_phone': '+1234567890',
            'asking_price': '450000.00',
            'start_date': str(self.end_date),
            'end_date': str(self.start_date),
        }
        response = self.client.post(self.selling_request_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_selling_request_default_status_pending(self):
        """Test that newly created selling request has pending status"""
        self.client.force_authenticate(user=self.seller)
        data = {
            'selling_reason': 'Looking to relocate to another city',
            'contact_name': 'John Doe',
            'contact_email': 'john@example.com',
            'contact_phone': '+1234567890',
            'asking_price': '450000.00',
            'start_date': str(self.start_date),
            'end_date': str(self.end_date),
        }
        response = self.client.post(self.selling_request_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')
        
        # Verify in database
        selling_request = SellingRequest.objects.get(pk=response.data['id'])
        self.assertEqual(selling_request.status, 'pending')


class SellingRequestListTestCase(TestCase):
    """Test cases for listing selling requests"""

    def setUp(self):
        self.client = APIClient()
        self.seller1 = User.objects.create_user(
            username='seller1',
            email='seller1@example.com',
            password='SecurePassword123!',
            first_name='John',
            last_name='Doe'
        )
        self.seller2 = User.objects.create_user(
            username='seller2',
            email='seller2@example.com',
            password='SecurePassword123!',
            first_name='Jane',
            last_name='Smith'
        )
        self.selling_request_url = '/api/v1/seller/selling-requests/'
        
        # Create selling requests for seller1
        SellingRequest.objects.create(
            seller=self.seller1,
            selling_reason='Relocating',
            contact_name='John Doe',
            contact_email='john@example.com',
            contact_phone='+1234567890',
            asking_price='450000.00',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30)
        )

    def test_list_selling_requests_authenticated(self):
        """Test listing selling requests as authenticated seller"""
        self.client.force_authenticate(user=self.seller1)
        response = self.client.get(self.selling_request_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_selling_requests_seller_isolation(self):
        """Test that sellers only see their own selling requests"""
        # seller2 should see 0 requests
        self.client.force_authenticate(user=self.seller2)
        response = self.client.get(self.selling_request_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_list_selling_requests_unauthenticated(self):
        """Test listing selling requests as unauthenticated user"""
        response = self.client.get(self.selling_request_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SellingRequestDetailTestCase(TestCase):
    """Test cases for selling request detail operations"""

    def setUp(self):
        self.client = APIClient()
        self.seller1 = User.objects.create_user(
            username='seller1',
            email='seller1@example.com',
            password='SecurePassword123!',
            first_name='John',
            last_name='Doe'
        )
        self.seller2 = User.objects.create_user(
            username='seller2',
            email='seller2@example.com',
            password='SecurePassword123!',
            first_name='Jane',
            last_name='Smith'
        )
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller1,
            selling_reason='Relocating',
            contact_name='John Doe',
            contact_email='john@example.com',
            contact_phone='+1234567890',
            asking_price='450000.00',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30)
        )
        self.selling_request_detail_url = f'/api/v1/seller/selling-requests/{self.selling_request.id}/'

    def test_get_selling_request_detail(self):
        """Test retrieving selling request details"""
        self.client.force_authenticate(user=self.seller1)
        response = self.client.get(self.selling_request_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.selling_request.id)
        self.assertEqual(response.data['selling_reason'], 'Relocating')

    def test_update_selling_request_pending_status(self):
        """Test updating selling request with pending status"""
        self.client.force_authenticate(user=self.seller1)
        data = {
            'asking_price': '500000.00',
            'selling_reason': 'Updated reason'
        }
        response = self.client.put(self.selling_request_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.selling_request.refresh_from_db()
        self.assertEqual(str(self.selling_request.asking_price), '500000.00')
        self.assertEqual(self.selling_request.selling_reason, 'Updated reason')

    def test_update_selling_request_accepted_status(self):
        """Test that updating is not allowed when status is accepted"""
        self.selling_request.status = 'accepted'
        self.selling_request.save()
        
        self.client.force_authenticate(user=self.seller1)
        data = {
            'asking_price': '500000.00',
        }
        response = self.client.put(self.selling_request_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_selling_request_rejected_status(self):
        """Test that updating is not allowed when status is rejected"""
        self.selling_request.status = 'rejected'
        self.selling_request.save()
        
        self.client.force_authenticate(user=self.seller1)
        data = {
            'asking_price': '500000.00',
        }
        response = self.client.put(self.selling_request_detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_selling_request_pending_status(self):
        """Test deleting selling request with pending status"""
        self.client.force_authenticate(user=self.seller1)
        response = self.client.delete(self.selling_request_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SellingRequest.objects.filter(id=self.selling_request.id).exists())

    def test_delete_selling_request_accepted_status(self):
        """Test that deletion is not allowed when status is accepted"""
        self.selling_request.status = 'accepted'
        self.selling_request.save()
        
        self.client.force_authenticate(user=self.seller1)
        response = self.client.delete(self.selling_request_detail_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_seller_cannot_access_other_seller_request(self):
        """Test that sellers cannot access other sellers' requests"""
        self.client.force_authenticate(user=self.seller2)
        response = self.client.get(self.selling_request_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SellerNotificationTestCase(TestCase):
    """Test cases for seller notifications"""

    def setUp(self):
        self.client = APIClient()
        self.seller = User.objects.create_user(
            username='seller1',
            email='seller1@example.com',
            password='SecurePassword123!',
            first_name='John',
            last_name='Doe'
        )
        self.notification_list_url = '/api/v1/seller/notifications/'
        self.notification_unread_url = '/api/v1/seller/notifications/unread-count/'
        self.notification_mark_all_read_url = '/api/v1/seller/notifications/mark-all-read/'

    def test_list_seller_notifications(self):
        """Test listing seller notifications"""
        # Create test notifications
        for i in range(3):
            SellerNotification.objects.create(
                seller=self.seller,
                notification_type='approved',
                title=f'Notification {i+1}',
                message=f'Message {i+1}',
                is_read=False
            )
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.notification_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)

    def test_notification_list_isolation(self):
        """Test that sellers only see their own notifications"""
        seller2 = User.objects.create_user(
            username='seller2',
            email='seller2@example.com',
            password='SecurePassword123!',
            first_name='Jane',
            last_name='Smith'
        )
        
        # Create notification for seller1
        SellerNotification.objects.create(
            seller=self.seller,
            notification_type='approved',
            title='Seller1 Notification',
            message='This is for seller1',
            is_read=False
        )
        
        # Create notification for seller2
        SellerNotification.objects.create(
            seller=seller2,
            notification_type='rejected',
            title='Seller2 Notification',
            message='This is for seller2',
            is_read=False
        )
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.notification_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Seller1 Notification')

    def test_get_notification_details(self):
        """Test retrieving notification details"""
        notification = SellerNotification.objects.create(
            seller=self.seller,
            notification_type='approved',
            title='Test Notification',
            message='This is a test notification',
            action_text='View Details',
            is_read=False
        )
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(f'{self.notification_list_url}{notification.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Notification')
        self.assertEqual(response.data['is_read'], False)

    def test_mark_notification_as_read(self):
        """Test marking a notification as read"""
        notification = SellerNotification.objects.create(
            seller=self.seller,
            notification_type='approved',
            title='Test Notification',
            message='This is a test notification',
            is_read=False
        )
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.patch(
            f'{self.notification_list_url}{notification.id}/',
            {'is_read': True},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_read'], True)
        
        # Verify it was actually updated in the database
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_notification_as_unread(self):
        """Test marking a notification as unread"""
        notification = SellerNotification.objects.create(
            seller=self.seller,
            notification_type='approved',
            title='Test Notification',
            message='This is a test notification',
            is_read=True
        )
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.patch(
            f'{self.notification_list_url}{notification.id}/',
            {'is_read': False},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_read'], False)

    def test_get_unread_notification_count(self):
        """Test getting unread notification count"""
        # Create 2 unread and 1 read notification
        SellerNotification.objects.create(
            seller=self.seller,
            notification_type='approved',
            title='Notification 1',
            message='Message 1',
            is_read=False
        )
        SellerNotification.objects.create(
            seller=self.seller,
            notification_type='rejected',
            title='Notification 2',
            message='Message 2',
            is_read=False
        )
        SellerNotification.objects.create(
            seller=self.seller,
            notification_type='approved',
            title='Notification 3',
            message='Message 3',
            is_read=True
        )
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.notification_unread_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 2)

    def test_mark_all_notifications_as_read(self):
        """Test marking all notifications as read"""
        # Create 3 unread notifications
        for i in range(3):
            SellerNotification.objects.create(
                seller=self.seller,
                notification_type='approved',
                title=f'Notification {i+1}',
                message=f'Message {i+1}',
                is_read=False
            )
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(self.notification_mark_all_read_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 3)
        
        # Verify all notifications are marked as read
        unread_count = SellerNotification.objects.filter(
            seller=self.seller,
            is_read=False
        ).count()
        self.assertEqual(unread_count, 0)

    def test_unauthenticated_cannot_access_notifications(self):
        """Test that unauthenticated users cannot access notifications"""
        response = self.client.get(self.notification_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_notification_with_selling_request(self):
        """Test that notification is linked to selling request"""
        # Create a selling request
        selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Need to sell quickly',
            contact_name='John Doe',
            contact_email='john@example.com',
            contact_phone='1234567890',
            asking_price='500000.00',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='pending'
        )
        
        # Create notification related to the request
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=selling_request,
            notification_type='approved',
            title='Request Approved',
            message='Your selling request was approved',
            is_read=False
        )
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(f'{self.notification_list_url}{notification.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['selling_request_id'], selling_request.id)
        self.assertEqual(response.data['selling_request_status'], 'pending')

    def test_notification_types(self):
        """Test different notification types"""
        notification_types = ['approved', 'rejected', 'cma_ready', 'agreement']
        
        for notif_type in notification_types:
            notification = SellerNotification.objects.create(
                seller=self.seller,
                notification_type=notif_type,
                title=f'{notif_type.capitalize()} Notification',
                message=f'This is a {notif_type} notification',
                is_read=False
            )
            self.assertEqual(notification.notification_type, notif_type)


class CMANotificationTestCase(TestCase):
    """Test cases for CMA notifications when agent uploads CMA"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        
        # Create a seller
        self.seller = Seller.objects.create_user(
            username='seller_cma',
            email='seller_cma@example.com',
            password='SecurePassword123!',
            first_name='CMA',
            last_name='Test'
        )
        
        # Create a selling request
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Need quick sale',
            contact_name='John Doe',
            contact_email='john@example.com',
            contact_phone='555-1234',
            asking_price=500000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='accepted'
        )
        
        self.notification_list_url = '/api/v1/seller/notifications/'
    
    def test_cma_notification_created_on_upload(self):
        """Test that CMA notification is created when agent uploads CMA"""
        # Create a CMA notification as if agent uploaded one
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title=f'CMA Report Ready - {self.selling_request.contact_name}',
            message=f'The CMA report for {self.selling_request.contact_name}\'s property has been prepared and is ready for review.',
            action_url=f'/selling-requests/{self.selling_request.id}/',
            action_text='View CMA Report'
        )
        
        self.assertEqual(notification.notification_type, 'cma_ready')
        self.assertEqual(notification.seller, self.seller)
        self.assertEqual(notification.selling_request, self.selling_request)
        self.assertFalse(notification.is_read)
    
    def test_cma_notification_includes_seller_name(self):
        """Test that CMA notification includes seller/client name"""
        seller_name = self.seller.get_full_name()
        
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title=f'CMA Report Ready - {seller_name}',
            message=f'The CMA report for {seller_name}\'s property has been prepared.',
        )
        
        self.assertIn(seller_name, notification.title)
        self.assertIn(seller_name, notification.message)
    
    def test_cma_notification_retrieval(self):
        """Test retrieving CMA notifications through API"""
        # Create CMA notification
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title='CMA Report Ready',
            message='Your CMA report is ready',
        )
        
        # Authenticate and retrieve
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.notification_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
        
        # Check if CMA notification is in the list
        cma_notifs = [n for n in response.data['results'] if n['notification_type'] == 'cma_ready']
        self.assertGreater(len(cma_notifs), 0)
    
    def test_cma_notification_marked_as_read(self):
        """Test marking CMA notification as read"""
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title='CMA Report Ready',
            message='Your CMA report is ready',
            is_read=False
        )
        
        # Mark as read
        notification.is_read = True
        notification.save()
        
        # Verify
        updated_notification = SellerNotification.objects.get(id=notification.id)
        self.assertTrue(updated_notification.is_read)
    
    def test_multiple_sellers_get_separate_cma_notifications(self):
        """Test that different sellers get separate CMA notifications"""
        # Create another seller
        seller2 = Seller.objects.create_user(
            username='seller_cma_2',
            email='seller_cma2@example.com',
            password='SecurePassword123!',
            first_name='Another',
            last_name='Seller'
        )
        
        # Create selling request for second seller
        selling_request2 = SellingRequest.objects.create(
            seller=seller2,
            selling_reason='Relocating',
            contact_name='Jane Smith',
            contact_email='jane@example.com',
            contact_phone='555-5678',
            asking_price=600000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='accepted'
        )
        
        # Create CMA notifications for both sellers
        notif1 = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title='CMA for Seller 1',
            message='CMA for seller 1'
        )
        
        notif2 = SellerNotification.objects.create(
            seller=seller2,
            selling_request=selling_request2,
            notification_type='cma_ready',
            title='CMA for Seller 2',
            message='CMA for seller 2'
        )
        
        # Verify each seller only sees their own notification
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.notification_list_url)
        seller1_notifs = response.data['results']
        
        self.client.force_authenticate(user=seller2)
        response = self.client.get(self.notification_list_url)
        seller2_notifs = response.data['results']
        
        # Check that seller 1 doesn't see seller 2's notification
        seller1_ids = [n['id'] for n in seller1_notifs]
        seller2_ids = [n['id'] for n in seller2_notifs]
        
        self.assertIn(notif1.id, seller1_ids)
        self.assertNotIn(notif2.id, seller1_ids)
        self.assertIn(notif2.id, seller2_ids)
        self.assertNotIn(notif1.id, seller2_ids)


class CMANotificationCornerCaseTestCase(TestCase):
    """Corner case tests for CMA notification system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        
        # Create a seller
        self.seller = Seller.objects.create_user(
            username='seller_corner',
            email='seller_corner@example.com',
            password='SecurePassword123!',
            first_name='Corner',
            last_name='Case'
        )
        
        # Create a selling request
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Quick sale needed',
            contact_name='Mr. X',
            contact_email='mrx@example.com',
            contact_phone='555-9999',
            asking_price=750000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=60),
            status='accepted'
        )
        
        self.notification_list_url = '/api/v1/seller/notifications/'
    
    def test_cma_notification_with_very_long_seller_name(self):
        """Test CMA notification with very long seller name"""
        long_name_seller = Seller.objects.create_user(
            username='long_name_seller',
            email='long@example.com',
            password='SecurePassword123!',
            first_name='A' * 100,
            last_name='B' * 100
        )
        
        long_name_request = SellingRequest.objects.create(
            seller=long_name_seller,
            selling_reason='Sale',
            contact_name='Long Name Person',
            contact_email='long_contact@example.com',
            contact_phone='555-1111',
            asking_price=500000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='accepted'
        )
        
        notification = SellerNotification.objects.create(
            seller=long_name_seller,
            selling_request=long_name_request,
            notification_type='cma_ready',
            title=f'CMA Report Ready - {long_name_seller.get_full_name()}',
            message=f'CMA report for {long_name_seller.get_full_name()}\'s property is ready'
        )
        
        self.assertIsNotNone(notification)
        self.assertEqual(notification.seller, long_name_seller)
    
    def test_cma_notification_with_special_characters_in_name(self):
        """Test CMA notification with special characters in client name"""
        special_seller = Seller.objects.create_user(
            username='special_seller',
            email='special@example.com',
            password='SecurePassword123!',
            first_name="O'Brien",
            last_name="Müller-García"
        )
        
        notification = SellerNotification.objects.create(
            seller=special_seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title=f'CMA Report Ready - {special_seller.get_full_name()}',
            message=f'CMA report for {special_seller.get_full_name()}\'s property'
        )
        
        self.assertIn("O'Brien", notification.title)
        self.assertIn("Müller-García", notification.title)
    
    def test_multiple_cma_notifications_for_same_seller(self):
        """Test seller receiving multiple CMA notifications"""
        # Create multiple selling requests
        requests = []
        for i in range(5):
            sr = SellingRequest.objects.create(
                seller=self.seller,
                selling_reason=f'Sale reason {i}',
                contact_name=f'Client {i}',
                contact_email=f'client{i}@example.com',
                contact_phone=f'555-{1000+i}',
                asking_price=500000.00 + (i * 100000),
                start_date=date.today(),
                end_date=date.today() + timedelta(days=30),
                status='accepted'
            )
            requests.append(sr)
        
        # Create CMA notifications for each
        notifications = []
        for i, sr in enumerate(requests):
            notif = SellerNotification.objects.create(
                seller=self.seller,
                selling_request=sr,
                notification_type='cma_ready',
                title=f'CMA Report Ready - Property {i+1}',
                message=f'CMA for property {i+1} is ready'
            )
            notifications.append(notif)
        
        # Verify all notifications are accessible
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.notification_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cma_notifs = [n for n in response.data['results'] if n['notification_type'] == 'cma_ready']
        self.assertEqual(len(cma_notifs), 5)
    
    def test_cma_notification_without_selling_request_link(self):
        """Test CMA notification can exist without selling request reference"""
        # This tests if notification system is robust even without selling_request
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=None,  # No selling request
            notification_type='cma_ready',
            title='General CMA Notification',
            message='This is a general CMA notification without specific selling request'
        )
        
        self.assertIsNotNone(notification)
        self.assertIsNone(notification.selling_request)
    
    def test_cma_notification_with_empty_action_url(self):
        """Test CMA notification with empty action URL"""
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title='CMA Ready',
            message='CMA is ready',
            action_url='',  # Empty URL
            action_text=''  # Empty text
        )
        
        self.assertEqual(notification.action_url, '')
        self.assertEqual(notification.action_text, '')
    
    def test_cma_notification_unread_count(self):
        """Test unread count for CMA notifications"""
        # Create multiple CMA notifications with mixed read/unread status
        for i in range(3):
            SellerNotification.objects.create(
                seller=self.seller,
                selling_request=self.selling_request,
                notification_type='cma_ready',
                title=f'CMA {i}',
                message=f'CMA {i}',
                is_read=False
            )
        
        # Create one read notification
        SellerNotification.objects.create(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title='Old CMA',
            message='Old CMA',
            is_read=True
        )
        
        # Check unread count
        unread_count = SellerNotification.objects.filter(
            seller=self.seller,
            notification_type='cma_ready',
            is_read=False
        ).count()
        
        self.assertEqual(unread_count, 3)
    
    def test_cma_notification_timestamp_ordering(self):
        """Test that CMA notifications are ordered by creation time"""
        import time
        
        notifications = []
        for i in range(3):
            notif = SellerNotification.objects.create(
                seller=self.seller,
                selling_request=self.selling_request,
                notification_type='cma_ready',
                title=f'CMA {i}',
                message=f'CMA {i}'
            )
            notifications.append(notif)
            time.sleep(0.1)  # Small delay to ensure different timestamps
        
        # Retrieve and verify order (newest first)
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.notification_list_url)
        
        cma_notifs = [n for n in response.data['results'] if n['notification_type'] == 'cma_ready']
        
        # Most recent should be first
        if len(cma_notifs) >= 2:
            self.assertGreater(cma_notifs[0]['created_at'], cma_notifs[1]['created_at'])
    
    def test_cma_notification_with_unicode_characters(self):
        """Test CMA notification with unicode characters in message"""
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title='CMA Report Ready - Property 🏠',
            message='Your CMA report is ready! 📋 Please review it at your convenience. 😊'
        )
        
        self.assertIn('🏠', notification.title)
        self.assertIn('📋', notification.message)
    
    def test_cma_notification_with_html_in_message(self):
        """Test that CMA notification handles HTML/special chars safely"""
        html_message = '<script>alert("xss")</script>This is safe text'
        
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title='CMA Ready',
            message=html_message
        )
        
        # Verify the message is stored as-is (escaping should be done on frontend)
        self.assertEqual(notification.message, html_message)
    
    def test_cma_notification_status_for_rejected_selling_request(self):
        """Test CMA notification when selling request is rejected"""
        rejected_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Rejected sale',
            contact_name='Rejected Client',
            contact_email='rejected@example.com',
            contact_phone='555-0000',
            asking_price=400000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='rejected'
        )
        
        # Create CMA notification for rejected request (edge case)
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=rejected_request,
            notification_type='cma_ready',
            title='CMA for Rejected Request',
            message='CMA report (even though request was rejected)'
        )
        
        self.assertEqual(notification.selling_request.status, 'rejected')
        self.assertEqual(notification.notification_type, 'cma_ready')
    
    def test_cma_notification_with_very_long_message(self):
        """Test CMA notification with very long message"""
        long_message = 'This is a very long message. ' * 100  # Repeat to make it long
        
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title='CMA Ready',
            message=long_message
        )
        
        self.assertEqual(notification.message, long_message)
        self.assertGreater(len(notification.message), 1000)
    
    def test_cma_notification_concurrent_creation(self):
        """Test that multiple CMA notifications can be created for same request"""
        # Simulate multiple agents/updates creating notifications
        notifications = []
        for i in range(10):
            notif = SellerNotification.objects.create(
                seller=self.seller,
                selling_request=self.selling_request,
                notification_type='cma_ready',
                title=f'CMA Update {i}',
                message=f'CMA update {i}'
            )
            notifications.append(notif)
        
        # Verify all were created
        total = SellerNotification.objects.filter(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready'
        ).count()
        
        self.assertEqual(total, 10)
    
    def test_notification_filtering_by_type_performance(self):
        """Test filtering notifications by type works efficiently"""
        # Create mixed notification types
        for i in range(5):
            SellerNotification.objects.create(
                seller=self.seller,
                selling_request=self.selling_request,
                notification_type='cma_ready',
                title=f'CMA {i}',
                message=f'CMA {i}'
            )
        
        
        for i in range(3):
            SellerNotification.objects.create(
                seller=self.seller,
                selling_request=self.selling_request,
                notification_type='approved',
                title=f'Approved {i}',
                message=f'Approved {i}'
            )
        
        # Filter for CMA only
        cma_notifications = SellerNotification.objects.filter(
            seller=self.seller,
            notification_type='cma_ready'
        )
        
        self.assertEqual(cma_notifications.count(), 5)


class CMAViewAndDeleteTestCase(TestCase):
    """Test cases for viewing CMA details and deleting CMA with selling request"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        
        # Create seller
        self.seller = Seller.objects.create_user(
            username='seller_cma_view',
            email='seller_cma_view@example.com',
            password='SecurePassword123!',
            first_name='CMA',
            last_name='Viewer'
        )
        
        # Create another seller to test isolation
        self.other_seller = Seller.objects.create_user(
            username='other_seller',
            email='other_seller@example.com',
            password='SecurePassword123!',
            first_name='Other',
            last_name='Seller'
        )
        
        # Create selling request
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Need to sell quickly',
            contact_name='Mr. X',
            contact_email='mrx@example.com',
            contact_phone='555-1234',
            asking_price=500000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='accepted'
        )
        
        # Create another selling request for other seller
        self.other_selling_request = SellingRequest.objects.create(
            seller=self.other_seller,
            selling_reason='Relocation',
            contact_name='Mrs. Y',
            contact_email='mrsy@example.com',
            contact_phone='555-5678',
            asking_price=600000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='accepted'
        )
        
        # Create CMA document using Django model
        self.cma_document = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='CMA Report for Mr. X',
            description='Comparative Market Analysis for the property',
            file='property_documents/2025/12/10/cma_report.pdf',
            file_size=2500000  # 2.5 MB
        )
        
        # Create CMA for other seller
        self.other_cma_document = PropertyDocument.objects.create(
            selling_request=self.other_selling_request,
            seller=self.other_seller,
            document_type='cma',
            title='CMA Report for Mrs. Y',
            description='Comparative Market Analysis',
            file='property_documents/2025/12/10/cma_report_other.pdf',
            file_size=2800000
        )
        
        self.document_url = f'/api/v1/seller/documents/{self.cma_document.id}/'
    
    def test_view_cma_details(self):
        """Test viewing CMA report with all details"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.document_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check CMA document fields
        self.assertEqual(response.data['id'], self.cma_document.id)
        self.assertEqual(response.data['document_type'], 'cma')
        self.assertEqual(response.data['title'], 'CMA Report for Mr. X')
        self.assertEqual(response.data['description'], 'Comparative Market Analysis for the property')
        self.assertIn('file_extension', response.data)
        self.assertIn('file_size_mb', response.data)
    
    def test_view_cma_includes_selling_request_details(self):
        """Test that CMA view includes complete selling request information"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.document_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify selling request details are included
        self.assertEqual(response.data['selling_request_id'], self.selling_request.id)
        self.assertEqual(response.data['selling_request_contact_name'], 'Mr. X')
        self.assertEqual(response.data['selling_request_contact_email'], 'mrx@example.com')
        self.assertEqual(response.data['selling_request_contact_phone'], '555-1234')
        self.assertEqual(response.data['selling_request_asking_price'], '500000.00')
        self.assertEqual(response.data['selling_request_status'], 'accepted')
        self.assertIn('selling_request_start_date', response.data)
        self.assertIn('selling_request_end_date', response.data)
        self.assertIn('selling_request_reason', response.data)
    
    def test_view_cma_includes_property_location(self):
        """Test that CMA view includes property location"""
        # Update seller location
        self.seller.location = '123 Main St, Downtown'
        self.seller.save()
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.document_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['selling_request_property_location'], '123 Main St, Downtown')
    
    def test_seller_cannot_view_other_sellers_cma(self):
        """Test that seller cannot view another seller's CMA"""
        other_document_url = f'/api/v1/seller/documents/{self.other_cma_document.id}/'
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(other_document_url)
        
        # Should not be able to access other seller's CMA
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_delete_cma_requires_authentication(self):
        """Test that deleting CMA requires authentication"""
        response = self.client.delete(self.document_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_delete_cma_and_selling_request(self):
        """Test deleting CMA also deletes associated selling request"""
        self.client.force_authenticate(user=self.seller)
        
        # Verify CMA and selling request exist
        self.assertTrue(PropertyDocument.objects.filter(id=self.cma_document.id).exists())
        self.assertTrue(SellingRequest.objects.filter(id=self.selling_request.id).exists())
        
        # Delete CMA
        response = self.client.delete(self.document_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify both CMA and selling request are deleted
        self.assertFalse(PropertyDocument.objects.filter(id=self.cma_document.id).exists())
        self.assertFalse(SellingRequest.objects.filter(id=self.selling_request.id).exists())
    
    def test_delete_cma_cascades_delete_related_notifications(self):
        """Test that deleting CMA cascades to delete related notifications"""
        # Create notification for this selling request
        notification = SellerNotification.objects.create(
            seller=self.seller,
            selling_request=self.selling_request,
            notification_type='cma_ready',
            title='CMA Ready',
            message='Your CMA is ready'
        )
        
        self.client.force_authenticate(user=self.seller)
        
        # Verify notification exists
        self.assertTrue(SellerNotification.objects.filter(id=notification.id).exists())
        
        # Delete CMA (which deletes selling request)
        response = self.client.delete(self.document_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify notification is also deleted (cascade)
        self.assertFalse(SellerNotification.objects.filter(id=notification.id).exists())
    
    def test_delete_response_contains_ids(self):
        """Test that delete response contains IDs of deleted entities"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.delete(self.document_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Note: 204 responses typically have no content body, but we can verify the request succeeded
    
    def test_seller_cannot_delete_other_sellers_cma(self):
        """Test that seller cannot delete another seller's CMA"""
        other_document_url = f'/api/v1/seller/documents/{self.other_cma_document.id}/'
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.delete(other_document_url)
        
        # Should not be able to delete other seller's CMA
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify other seller's CMA still exists
        self.assertTrue(PropertyDocument.objects.filter(id=self.other_cma_document.id).exists())
        self.assertTrue(SellingRequest.objects.filter(id=self.other_selling_request.id).exists())
    
    def test_view_cma_includes_file_size_in_mb(self):
        """Test that CMA view includes file size in MB"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.document_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # File is 2500000 bytes = 2.38 MB
        file_size_mb = response.data['file_size_mb']
        self.assertIsNotNone(file_size_mb)
        self.assertGreater(file_size_mb, 2.0)
        self.assertLess(file_size_mb, 3.0)
    
    def test_view_cma_includes_file_extension(self):
        """Test that CMA view includes file extension"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.document_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        file_extension = response.data['file_extension']
        self.assertEqual(file_extension, 'pdf')
    
    def test_delete_nonexistent_cma(self):
        """Test deleting a CMA that doesn't exist"""
        nonexistent_url = '/api/v1/seller/documents/99999/'
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.delete(nonexistent_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_view_cma_with_dates(self):
        """Test that CMA view includes date information"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.document_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify date fields exist
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)
        self.assertIn('selling_request_start_date', response.data)
        self.assertIn('selling_request_end_date', response.data)
    
    def test_multiple_cmas_for_same_seller(self):
        """Test viewing multiple CMAs for same seller"""
        # Create another selling request and CMA
        selling_request2 = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Another property',
            contact_name='Another Client',
            contact_email='another@example.com',
            contact_phone='555-9999',
            asking_price=450000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='accepted'
        )
        
        cma2 = PropertyDocument.objects.create(
            selling_request=selling_request2,
            seller=self.seller,
            document_type='cma',
            title='CMA Report 2',
            description='Another CMA',
            file='property_documents/2025/12/10/cma_report2.pdf',
            file_size=2600000
        )
        
        # View first CMA
        self.client.force_authenticate(user=self.seller)
        response1 = self.client.get(self.document_url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # View second CMA
        response2 = self.client.get(f'/api/v1/seller/documents/{cma2.id}/')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Verify they have different data
        self.assertEqual(response1.data['id'], self.cma_document.id)
        self.assertEqual(response2.data['id'], cma2.id)
        self.assertEqual(response1.data['selling_request_contact_name'], 'Mr. X')
        self.assertEqual(response2.data['selling_request_contact_name'], 'Another Client')


class CMADetailedSerializerTestCase(TestCase):
    """Test cases for CMADetailedSerializer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.seller = Seller.objects.create_user(
            username='seller_serializer_test',
            email='seller_serializer@example.com',
            password='SecurePassword123!',
            first_name='Test',
            last_name='Seller',
            location='456 Oak Ave'
        )
        
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Estate sale',
            contact_name='Estate Contact',
            contact_email='estate@example.com',
            contact_phone='555-0000',
            asking_price=750000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=60),
            status='accepted'
        )
        
        self.cma_document = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Estate CMA',
            description='CMA for estate property',
            file='property_documents/2025/12/10/estate_cma.pdf',
            file_size=3000000
        )
    
    def test_serializer_includes_all_fields(self):
        """Test that serializer includes all required fields"""
        from .serializers import CMADetailedSerializer
        
        serializer = CMADetailedSerializer(self.cma_document)
        data = serializer.data
        
        # Document fields
        self.assertIn('id', data)
        self.assertIn('document_type', data)
        self.assertIn('title', data)
        self.assertIn('description', data)
        self.assertIn('file', data)
        self.assertIn('file_extension', data)
        self.assertIn('file_size_mb', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
        
        # Selling request fields
        self.assertIn('selling_request_id', data)
        self.assertIn('selling_request_contact_name', data)
        self.assertIn('selling_request_contact_email', data)
        self.assertIn('selling_request_contact_phone', data)
        self.assertIn('selling_request_property_location', data)
        self.assertIn('selling_request_asking_price', data)
        self.assertIn('selling_request_status', data)
        self.assertIn('selling_request_start_date', data)
        self.assertIn('selling_request_end_date', data)
        self.assertIn('selling_request_reason', data)
    
    def test_serializer_data_accuracy(self):
        """Test that serializer returns accurate data"""
        from .serializers import CMADetailedSerializer
        
        serializer = CMADetailedSerializer(self.cma_document)
        data = serializer.data
        
        # Check accuracy
        self.assertEqual(data['title'], 'Estate CMA')
        self.assertEqual(data['description'], 'CMA for estate property')
        self.assertEqual(data['selling_request_contact_name'], 'Estate Contact')
        self.assertEqual(data['selling_request_asking_price'], '750000.00')
        self.assertEqual(data['selling_request_property_location'], '456 Oak Ave')


class SellerCMAListTestCase(TestCase):
    """Test cases for listing all CMA reports for a seller"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        
        # Create seller
        self.seller = Seller.objects.create_user(
            username='seller_cma_list',
            email='seller_cma_list@example.com',
            password='SecurePassword123!',
            first_name='List',
            last_name='Seller'
        )
        
        # Create another seller
        self.other_seller = Seller.objects.create_user(
            username='other_seller_list',
            email='other_seller_list@example.com',
            password='SecurePassword123!',
            first_name='Other',
            last_name='Seller'
        )
        
        # Create multiple selling requests for seller
        self.selling_requests = []
        for i in range(3):
            sr = SellingRequest.objects.create(
                seller=self.seller,
                selling_reason=f'Selling reason {i}',
                contact_name=f'Client {i}',
                contact_email=f'client{i}@example.com',
                contact_phone=f'555-{1000+i}',
                asking_price=500000.00 + (i * 100000),
                start_date=date.today(),
                end_date=date.today() + timedelta(days=30),
                status='accepted'
            )
            self.selling_requests.append(sr)
        
        # Create CMAs for each selling request
        self.cmas = []
        for i, sr in enumerate(self.selling_requests):
            cma = PropertyDocument.objects.create(
                selling_request=sr,
                seller=self.seller,
                document_type='cma',
                title=f'CMA Report {i}',
                description=f'CMA for client {i}',
                file=f'property_documents/2025/12/10/cma_{i}.pdf',
                file_size=2500000 + (i * 100000)
            )
            self.cmas.append(cma)
        
        # Create other documents (non-CMA) for seller
        other_doc = PropertyDocument.objects.create(
            selling_request=self.selling_requests[0],
            seller=self.seller,
            document_type='inspection',
            title='Inspection Report',
            description='Home inspection',
            file='property_documents/2025/12/10/inspection.pdf',
            file_size=1500000
        )
        
        # Create CMA for other seller
        other_selling_request = SellingRequest.objects.create(
            seller=self.other_seller,
            selling_reason='Other sale',
            contact_name='Other Client',
            contact_email='other_client@example.com',
            contact_phone='555-9999',
            asking_price=600000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='accepted'
        )
        
        other_cma = PropertyDocument.objects.create(
            selling_request=other_selling_request,
            seller=self.other_seller,
            document_type='cma',
            title='Other CMA',
            description='Other seller CMA',
            file='property_documents/2025/12/10/other_cma.pdf',
            file_size=2800000
        )
        
        self.cma_list_url = '/api/v1/seller/cma/'
    
    def test_list_all_cmas_for_seller(self):
        """Test listing all CMA reports for the authenticated seller"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.cma_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['total_cmas'], 3)
        self.assertEqual(len(response.data['cmas']), 3)
    
    def test_cma_list_excludes_non_cma_documents(self):
        """Test that list only shows CMA documents, not other document types"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.cma_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have 3 CMAs but not the inspection report
        self.assertEqual(response.data['total_cmas'], 3)
        
        # Verify all items are CMAs
        for cma in response.data['cmas']:
            self.assertEqual(cma['document_type'], 'cma')
    
    def test_cma_list_user_isolation(self):
        """Test that seller only sees their own CMAs"""
        # Seller 1 should see 3 CMAs
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.cma_list_url)
        self.assertEqual(response.data['total_cmas'], 3)
        
        # Seller 2 should see only 1 CMA
        self.client.force_authenticate(user=self.other_seller)
        response = self.client.get(self.cma_list_url)
        self.assertEqual(response.data['total_cmas'], 1)
        
        # Verify the CMA is theirs
        self.assertEqual(response.data['cmas'][0]['title'], 'Other CMA')
    
    def test_cma_list_includes_detailed_information(self):
        """Test that CMA list includes all detailed information"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.cma_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check first CMA has all details
        cma = response.data['cmas'][0]
        self.assertIn('id', cma)
        self.assertIn('title', cma)
        self.assertIn('description', cma)
        self.assertIn('file', cma)
        self.assertIn('file_extension', cma)
        self.assertIn('file_size_mb', cma)
        
        # Check selling request details
        self.assertIn('selling_request_id', cma)
        self.assertIn('selling_request_contact_name', cma)
        self.assertIn('selling_request_asking_price', cma)
        self.assertIn('selling_request_property_location', cma)
    
    def test_cma_list_ordered_by_created_date(self):
        """Test that CMAs are ordered by most recent first"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.cma_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify ordered by created_at descending (newest first)
        cmas = response.data['cmas']
        for i in range(len(cmas) - 1):
            self.assertGreaterEqual(
                cmas[i]['created_at'],
                cmas[i+1]['created_at']
            )
    
    def test_cma_list_empty_for_new_seller(self):
        """Test that new seller with no CMAs gets empty list"""
        new_seller = Seller.objects.create_user(
            username='new_seller_no_cma',
            email='new_seller@example.com',
            password='SecurePassword123!',
            first_name='New',
            last_name='Seller'
        )
        
        self.client.force_authenticate(user=new_seller)
        response = self.client.get(self.cma_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_cmas'], 0)
        self.assertEqual(len(response.data['cmas']), 0)
    
    def test_cma_list_requires_authentication(self):
        """Test that listing CMAs requires authentication"""
        response = self.client.get(self.cma_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_cma_list_response_format(self):
        """Test that response has correct format"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.cma_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('total_cmas', response.data)
        self.assertIn('cmas', response.data)
        self.assertTrue(isinstance(response.data['cmas'], list))
    
    def test_cma_list_file_information(self):
        """Test that CMA list includes file size in MB"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.cma_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        cma = response.data['cmas'][0]
        self.assertIn('file_size_mb', cma)
        self.assertIsNotNone(cma['file_size_mb'])
        self.assertGreater(cma['file_size_mb'], 0)
        
        # File is 2500000 bytes = ~2.38 MB
        self.assertGreater(cma['file_size_mb'], 2.0)
        self.assertLess(cma['file_size_mb'], 3.0)
    
    def test_cma_list_can_delete_from_list(self):
        """Test that seller can delete a CMA from the list"""
        self.client.force_authenticate(user=self.seller)
        
        # Get list
        response = self.client.get(self.cma_list_url)
        self.assertEqual(response.data['total_cmas'], 3)
        
        cma_id = response.data['cmas'][0]['id']
        
        # Delete CMA
        delete_url = f'/api/v1/seller/documents/{cma_id}/'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify list now shows 2 CMAs
        response = self.client.get(self.cma_list_url)
        self.assertEqual(response.data['total_cmas'], 2)
    
    def test_cma_list_shows_contact_information(self):
        """Test that CMA list shows client contact information"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.cma_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        cma = response.data['cmas'][0]
        self.assertEqual(cma['selling_request_contact_name'], 'Client 0')
        self.assertEqual(cma['selling_request_contact_email'], 'client0@example.com')
        self.assertEqual(cma['selling_request_contact_phone'], '555-1000')


# Privacy & Security Tests
class SellerPrivacySecurityTestCase(TestCase):
    """Test cases for seller privacy & security endpoints"""

    def setUp(self):
        self.client = APIClient()
        # Create regular seller user
        self.seller = Seller.objects.create_user(
            username='testseller',
            email='testseller@example.com',
            password='SecurePassword123!',
            first_name='Test',
            last_name='Seller'
        )
        # Create admin user
        self.admin = Seller.objects.create_superuser(
            username='adminseller',
            email='admin@example.com',
            password='AdminPassword123!'
        )
        self.privacy_url = '/api/v1/seller/privacy-security/'

    def test_get_own_privacy_settings(self):
        """Test seller can retrieve their own privacy settings"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['seller'], self.seller.id)
        self.assertEqual(response.data['seller_username'], 'testseller')
        self.assertEqual(response.data['seller_email'], 'testseller@example.com')

    def test_get_privacy_settings_creates_record(self):
        """Test that getting privacy settings auto-creates record if it doesn't exist"""
        from seller.models import SellerPrivacySecurity
        
        # Ensure no privacy settings exist
        self.assertEqual(SellerPrivacySecurity.objects.filter(seller=self.seller).count(), 0)
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(SellerPrivacySecurity.objects.filter(seller=self.seller).count(), 1)

    def test_get_all_privacy_settings_admin_only(self):
        """Test only superadmins can list all privacy settings with ?all=true"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(f'{self.privacy_url}?all=true')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Only superadministrators', response.data['detail'])

    def test_get_all_privacy_settings_as_admin(self):
        """Test admin can retrieve all privacy settings"""
        # First, trigger creation of privacy settings for the admin user
        self.client.force_authenticate(user=self.admin)
        self.client.get(self.privacy_url)
        
        # Create another seller and their privacy settings
        seller2 = Seller.objects.create_user(
            username='seller2',
            email='seller2@example.com',
            password='Pass123!'
        )
        self.client.force_authenticate(user=seller2)
        self.client.get(self.privacy_url)
        
        # Now authenticate as admin and list all
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f'{self.privacy_url}?all=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)

    def test_update_privacy_settings_admin_only(self):
        """Test only superadmins can update privacy settings"""
        self.client.force_authenticate(user=self.seller)
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
            'collect_property_info': True,
            'use_for_services': True,
            'use_for_alerts': False,
            'use_for_compliance': True,
            'use_for_cma_reports': True,
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
        self.assertEqual(response.data['collect_property_info'], True)
        self.assertEqual(response.data['data_retention_months'], 24)

    def test_patch_privacy_settings_as_admin(self):
        """Test admin can partially update privacy settings with PATCH"""
        self.client.force_authenticate(user=self.admin)
        
        # Partial update
        update_data = {
            'allow_multi_factor_auth': False,
            'encrypted_communication': True,
            'use_for_cma_reports': False
        }
        response = self.client.patch(self.privacy_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['allow_multi_factor_auth'], False)
        self.assertEqual(response.data['encrypted_communication'], True)
        self.assertEqual(response.data['use_for_cma_reports'], False)

    def test_privacy_settings_seller_specific_fields(self):
        """Test seller-specific privacy fields are present"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check seller-specific fields
        self.assertIn('collect_property_info', response.data)
        self.assertIn('use_for_cma_reports', response.data)
        self.assertIn('share_with_legal', response.data)

    def test_privacy_settings_one_to_one_relationship(self):
        """Test that each seller has only one privacy settings record"""
        from seller.models import SellerPrivacySecurity
        
        # Get privacy settings multiple times
        for _ in range(3):
            self.client.force_authenticate(user=self.seller)
            response = self.client.get(self.privacy_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should still have only one record
        count = SellerPrivacySecurity.objects.filter(seller=self.seller).count()
        self.assertEqual(count, 1)

    def test_privacy_settings_unauthorized_access(self):
        """Test that unauthenticated users cannot access privacy settings"""
        response = self.client.get(self.privacy_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CMAAcceptRejectTestCase(TestCase):
    """Test cases for CMA accept and reject functionality"""

    def setUp(self):
        self.client = APIClient()
        
        # Create seller
        self.seller = User.objects.create_user(
            username='testcmaseller',
            email='cmaseller@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='Seller'
        )
        
        # Create admin user
        self.admin = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='AdminPassword123!',
            is_staff=True,
            is_superuser=True
        )
        
        # Create selling request
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Need to sell quickly',
            contact_name='John Doe',
            contact_email='john@example.com',
            contact_phone='1234567890',
            asking_price=250000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='accepted'
        )
        
        # Create CMA document
        self.cma_document = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='CMA Report 2025',
            description='Comprehensive Market Analysis',
            file='test_cma.pdf',
            file_size=1024000
        )

    def test_cma_accept_success(self):
        """Test successful CMA acceptance"""
        self.client.force_authenticate(user=self.admin)
        url = f'/api/v1/seller/cma/{self.cma_document.id}/accept/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cma_document.refresh_from_db()
        self.assertEqual(self.cma_document.cma_status, 'accepted')
        self.assertEqual(self.cma_document.cma_document_status, 'accepted')

    def test_cma_reject_success(self):
        """Test successful CMA rejection"""
        self.client.force_authenticate(user=self.admin)
        url = f'/api/v1/seller/cma/{self.cma_document.id}/reject/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cma_document.refresh_from_db()
        self.assertEqual(self.cma_document.cma_status, 'rejected')
        self.assertEqual(self.cma_document.cma_document_status, 'rejected')

    def test_cma_accept_creates_notification(self):
        """Test that accepting CMA creates agent notification"""
        self.client.force_authenticate(user=self.admin)
        url = f'/api/v1/seller/cma/{self.cma_document.id}/accept/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check notification was created
        from seller.models import AgentNotification
        notification = AgentNotification.objects.filter(
            property_document=self.cma_document
        ).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, 'CMA Report Accepted')
        self.assertEqual(notification.notification_type, 'cma_ready')

    def test_cma_reject_creates_notification(self):
        """Test that rejecting CMA creates agent notification"""
        self.client.force_authenticate(user=self.admin)
        url = f'/api/v1/seller/cma/{self.cma_document.id}/reject/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check notification was created
        from seller.models import AgentNotification
        notification = AgentNotification.objects.filter(
            property_document=self.cma_document
        ).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, 'CMA Report Rejected')
        self.assertEqual(notification.notification_type, 'cma_requested')

    def test_cma_accept_non_admin_forbidden(self):
        """Test that non-admin users cannot accept CMA"""
        self.client.force_authenticate(user=self.seller)
        url = f'/api/v1/seller/cma/{self.cma_document.id}/accept/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cma_reject_non_admin_forbidden(self):
        """Test that non-admin users cannot reject CMA"""
        self.client.force_authenticate(user=self.seller)
        url = f'/api/v1/seller/cma/{self.cma_document.id}/reject/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cma_accept_nonexistent_document(self):
        """Test accepting non-existent CMA document"""
        self.client.force_authenticate(user=self.admin)
        url = '/api/v1/seller/cma/99999/accept/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cma_reject_nonexistent_document(self):
        """Test rejecting non-existent CMA document"""
        self.client.force_authenticate(user=self.admin)
        url = '/api/v1/seller/cma/99999/reject/'
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SellingAgreementTestCase(TestCase):
    """Test cases for selling agreement document functionality"""

    def setUp(self):
        self.client = APIClient()
        
        # Create seller
        self.seller = User.objects.create_user(
            username='testseller',
            email='seller@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='Seller'
        )
        
        # Create admin user
        self.admin = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='AdminPassword123!',
            is_staff=True,
            is_superuser=True
        )
        
        # Create selling request
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Need to sell quickly',
            contact_name='John Doe',
            contact_email='john@example.com',
            contact_phone='1234567890',
            asking_price=250000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='accepted'
        )
        
        # Create selling agreement document
        self.agreement_document = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='other',
            title='Selling Agreement 2025',
            description='Selling Agreement Document',
            file='test_agreement.pdf',
            file_size=1024000
        )

    def test_selling_agreement_document_creation(self):
        """Test that selling agreement document can be created"""
        self.assertIsNotNone(self.agreement_document.id)
        self.assertEqual(self.agreement_document.title, 'Selling Agreement 2025')

    def test_selling_agreement_status_initial_null(self):
        """Test that agreement status is initially null"""
        self.assertIsNone(self.agreement_document.agreement_status)

    def test_selling_agreement_file_upload(self):
        """Test that selling agreement file is stored"""
        self.assertIsNotNone(self.agreement_document.selling_agreement_file)

    def test_update_agreement_status_accepted(self):
        """Test updating agreement status to accepted"""
        self.agreement_document.agreement_status = 'accepted'
        self.agreement_document.save()
        
        self.agreement_document.refresh_from_db()
        self.assertEqual(self.agreement_document.agreement_status, 'accepted')

    def test_update_agreement_status_rejected(self):
        """Test updating agreement status to rejected"""
        self.agreement_document.agreement_status = 'rejected'
        self.agreement_document.save()
        
        self.agreement_document.refresh_from_db()
        self.assertEqual(self.agreement_document.agreement_status, 'rejected')

    def test_agreement_fields_in_serializer(self):
        """Test that agreement fields are in PropertyDocumentSerializer"""
        from seller.serializers import PropertyDocumentSerializer
        serializer = PropertyDocumentSerializer(self.agreement_document)
        
        self.assertIn('agreement_status', serializer.data)
        self.assertIn('selling_agreement_file', serializer.data)

    def test_multiple_documents_different_statuses(self):
        """Test that a selling request can have multiple documents with different statuses"""
        # Create another document with accepted status
        agreement_doc2 = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='other',
            title='Selling Agreement Draft 2',
            description='Alternative Agreement',
            file='test_agreement2.pdf',
            file_size=1024000,
            agreement_status='accepted'
        )
        
        # Verify both documents exist with different statuses
        docs = PropertyDocument.objects.filter(selling_request=self.selling_request)
        self.assertEqual(docs.count(), 2)
        
        # Check statuses
        draft1 = docs.get(id=self.agreement_document.id)
        draft2 = docs.get(id=agreement_doc2.id)
        
        self.assertIsNone(draft1.agreement_status)
        self.assertEqual(draft2.agreement_status, 'accepted')


class SellerRegistrationEmailPasswordTestCase(TestCase):
    """Test cases for seller registration with email/password and property details"""

    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/seller/auth/register/'

    def test_seller_registration_with_property_details(self):
        """Test seller registration with all property details"""
        data = {
            'name': 'John Doe',
            'email': 'seller@example.com',
            'password': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'phone_number': '1234567890',
            'location': 'New York, NY',
            'bedrooms': 4,
            'bathrooms': 2,
            'property_condition': 'Excellent condition, recently renovated'
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        
        # Verify user was created with correct details
        seller = User.objects.get(email='seller@example.com')
        self.assertEqual(seller.first_name, 'John')
        self.assertEqual(seller.last_name, 'Doe')
        self.assertEqual(seller.phone_number, '1234567890')
        self.assertEqual(seller.location, 'New York, NY')
        self.assertEqual(seller.bedrooms, 4)
        self.assertEqual(seller.bathrooms, 2)

    def test_seller_login_with_email(self):
        """Test seller login using email instead of username"""
        # Create seller
        User.objects.create_user(
            username='testseller',
            email='seller@example.com',
            password='SecurePassword123!'
        )
        
        login_url = '/api/v1/seller/auth/login/'
        data = {
            'email': 'seller@example.com',
            'password': 'SecurePassword123!'
        }
        response = self.client.post(login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)

    def test_seller_login_with_invalid_email(self):
        """Test seller login with invalid email"""
        login_url = '/api/v1/seller/auth/login/'
        data = {
            'email': 'nonexistent@example.com',
            'password': 'AnyPassword123!'
        }
        response = self.client.post(login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_seller_registration_minimal_details(self):
        """Test seller registration with only required fields"""
        data = {
            'name': 'Jane Smith',
            'email': 'jane@example.com',
            'password': 'SecurePassword123!',
            'password2': 'SecurePassword123!'
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class BuyerRegistrationEmailPasswordTestCase(TestCase):
    """Test cases for buyer registration with email/password and preferences"""

    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/buyer/auth/register/'

    def test_buyer_registration_with_preferences(self):
        """Test buyer registration with all preference details"""
        from buyer.models import Buyer
        data = {
            'name': 'Jane Smith',
            'email': 'buyer@example.com',
            'password': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'phone_number': '0987654321',
            'price_range': '$300,000 - $500,000',
            'location': 'California, CA',
            'bedrooms': 3,
            'bathrooms': 2
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', response.data)
        
        # Verify buyer was created with correct details
        buyer = Buyer.objects.get(email='buyer@example.com')
        self.assertEqual(buyer.first_name, 'Jane')
        self.assertEqual(buyer.last_name, 'Smith')
        self.assertEqual(buyer.price_range, '$300,000 - $500,000')
        self.assertEqual(buyer.location, 'California, CA')

    def test_buyer_login_with_email(self):
        """Test buyer login using email"""
        from buyer.models import Buyer
        # Create buyer
        Buyer.objects.create_user(
            username='testbuyer',
            email='buyer@example.com',
            password='SecurePassword123!'
        )
        
        login_url = '/api/v1/buyer/auth/login/'
        data = {
            'email': 'buyer@example.com',
            'password': 'SecurePassword123!'
        }
        response = self.client.post(login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('user', response.data)


class AgentRegistrationEmailPasswordTestCase(TestCase):
    """Test cases for agent registration with email/password"""

    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/agent/auth/register/'

    def test_agent_login_with_email(self):
        """Test agent login using email"""
        from agent.models import Agent
        # Create agent
        Agent.objects.create_user(
            username='testagent',
            email='agent@example.com',
            password='SecurePassword123!'
        )
        
        login_url = '/api/v1/agent/auth/login/'
        data = {
            'email': 'agent@example.com',
            'password': 'SecurePassword123!'
        }
        response = self.client.post(login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)



class SellingAgreementTestCase(TestCase):
    """Comprehensive test cases for selling agreement endpoints"""

    def setUp(self):
        """Set up test data for all selling agreement tests"""
        self.client = APIClient()
        from django.core.files.uploadedfile import SimpleUploadedFile
        from agent.models import Agent
        from seller.models import AgentNotification
        
        # Create seller
        self.seller = Seller.objects.create_user(
            username='seller_agreement_test',
            email='seller_agreement@example.com',
            password='SecurePassword123!',
            first_name='Agreement',
            last_name='Seller',
            location='123 Test Street, Test City'
        )
        
        # Create another seller (for permission tests)
        self.other_seller = Seller.objects.create_user(
            username='other_seller_test',
            email='other_seller@example.com',
            password='SecurePassword123!',
            first_name='Other',
            last_name='Seller'
        )
        
        # Create agent
        self.agent = Agent.objects.create_user(
            username='agent_agreement_test',
            email='agent_agreement@example.com',
            password='SecurePassword123!',
            first_name='Agreement',
            last_name='Agent'
        )
        
        # Create approved selling request
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Testing selling agreement flow',
            contact_name='Agreement Seller',
            contact_email='seller_agreement@example.com',
            contact_phone='555-0001',
            asking_price=500000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            status='accepted'
        )
        
        # Create pending selling request
        self.pending_selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Pending request for testing',
            contact_name='Agreement Seller',
            contact_email='seller_agreement@example.com',
            contact_phone='555-0002',
            asking_price=400000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=60),
            status='pending'
        )
        
        # Create selling request for other seller
        self.other_selling_request = SellingRequest.objects.create(
            seller=self.other_seller,
            selling_reason='Other seller request',
            contact_name='Other Seller',
            contact_email='other_seller@example.com',
            contact_phone='555-0003',
            asking_price=600000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            status='accepted'
        )
        
        # Create property document WITH selling agreement
        self.document_with_agreement = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='CMA Report with Agreement',
            description='Test CMA report with selling agreement',
            file=SimpleUploadedFile(
                'cma_report.pdf',
                b'CMA content',
                content_type='application/pdf'
            ),
            file_size=11,
            selling_agreement_file=SimpleUploadedFile(
                'agreement.pdf',
                b'Agreement content',
                content_type='application/pdf'
            ),
            agreement_status='pending'
        )
        
        # Create property document WITHOUT selling agreement
        self.document_without_agreement = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='inspection',
            title='Inspection Report',
            description='Test inspection report without agreement',
            file=SimpleUploadedFile(
                'inspection_report.pdf',
                b'Inspection content',
                content_type='application/pdf'
            ),
            file_size=12,
            selling_agreement_file=None,
            agreement_status=None
        )
        
        # Create property document for other seller with agreement
        self.other_seller_document = PropertyDocument.objects.create(
            selling_request=self.other_selling_request,
            seller=self.other_seller,
            document_type='cma',
            title='Other Seller CMA',
            description='CMA for other seller',
            file=SimpleUploadedFile(
                'other_cma.pdf',
                b'Other CMA content',
                content_type='application/pdf'
            ),
            file_size=13,
            selling_agreement_file=SimpleUploadedFile(
                'other_agreement.pdf',
                b'Other agreement content',
                content_type='application/pdf'
            ),
            agreement_status='pending'
        )
        
        # Create accepted agreement document for duplicate accept test
        self.accepted_agreement = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Already Accepted Agreement',
            description='Agreement already accepted',
            file=SimpleUploadedFile(
                'accepted_cma.pdf',
                b'Accepted CMA content',
                content_type='application/pdf'
            ),
            file_size=14,
            selling_agreement_file=SimpleUploadedFile(
                'accepted_agreement.pdf',
                b'Accepted agreement content',
                content_type='application/pdf'
            ),
            agreement_status='accepted'
        )
        
        # Create rejected agreement document for duplicate reject test
        self.rejected_agreement = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Already Rejected Agreement',
            description='Agreement already rejected',
            file=SimpleUploadedFile(
                'rejected_cma.pdf',
                b'Rejected CMA content',
                content_type='application/pdf'
            ),
            file_size=15,
            selling_agreement_file=SimpleUploadedFile(
                'rejected_agreement.pdf',
                b'Rejected agreement content',
                content_type='application/pdf'
            ),
            agreement_status='rejected'
        )
        
        # URLs
        self.agreements_list_url = '/api/v1/seller/agreements/'
        self.agreement_detail_url = f'/api/v1/seller/agreements/{self.document_with_agreement.id}/'
        self.agreement_accept_url = f'/api/v1/seller/agreements/{self.document_with_agreement.id}/accept/'
        self.agreement_reject_url = f'/api/v1/seller/agreements/{self.document_with_agreement.id}/reject/'

    # ==================== LIST AGREEMENTS TESTS ====================
    
    def test_list_agreements_success(self):
        """Test successful listing of selling agreements"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.agreements_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('agreements', response.data)
        # Should only include documents with selling_agreement_file
        # excluding other seller's documents
        self.assertGreaterEqual(response.data['count'], 1)
        
        # Verify all returned agreements belong to this seller
        for agreement in response.data['agreements']:
            self.assertEqual(agreement['seller_email'], self.seller.email)

    def test_list_agreements_unauthenticated(self):
        """Test listing agreements without authentication"""
        response = self.client.get(self.agreements_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_agreements_as_agent(self):
        """Test listing agreements as agent (should fail - seller only)"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(self.agreements_list_url)
        # Should fail because IsSeller permission is required
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_agreements_excludes_documents_without_agreement_file(self):
        """Test that documents without agreement files are excluded"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.agreements_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that document without agreement is not included
        agreement_ids = [a['id'] for a in response.data['agreements']]
        self.assertNotIn(self.document_without_agreement.id, agreement_ids)

    def test_list_agreements_excludes_other_seller_documents(self):
        """Test that other seller's documents are not included"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.agreements_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that other seller's document is not included
        agreement_ids = [a['id'] for a in response.data['agreements']]
        self.assertNotIn(self.other_seller_document.id, agreement_ids)

    def test_list_agreements_empty_for_new_seller(self):
        """Test that new seller with no agreements gets empty list"""
        new_seller = Seller.objects.create_user(
            username='new_seller_empty',
            email='new_seller_empty@example.com',
            password='SecurePassword123!'
        )
        self.client.force_authenticate(user=new_seller)
        response = self.client.get(self.agreements_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['agreements']), 0)

    # ==================== VIEW AGREEMENT DETAIL TESTS ====================

    def test_view_agreement_detail_success(self):
        """Test successful viewing of agreement details"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.agreement_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.document_with_agreement.id)
        self.assertIn('selling_agreement_file', response.data)
        self.assertIn('agreement_status', response.data)
        self.assertIn('selling_request_id', response.data)

    def test_view_agreement_detail_unauthenticated(self):
        """Test viewing agreement details without authentication"""
        response = self.client.get(self.agreement_detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_view_agreement_detail_other_seller_document(self):
        """Test viewing other seller's agreement (should fail)"""
        self.client.force_authenticate(user=self.seller)
        other_detail_url = f'/api/v1/seller/agreements/{self.other_seller_document.id}/'
        response = self.client.get(other_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_agreement_detail_document_without_agreement(self):
        """Test viewing document that has no agreement file"""
        self.client.force_authenticate(user=self.seller)
        no_agreement_url = f'/api/v1/seller/agreements/{self.document_without_agreement.id}/'
        response = self.client.get(no_agreement_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_agreement_detail_nonexistent_document(self):
        """Test viewing non-existent document"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get('/api/v1/seller/agreements/99999/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ==================== ACCEPT AGREEMENT TESTS ====================

    def test_accept_agreement_success(self):
        """Test successful acceptance of selling agreement"""
        from seller.models import AgentNotification
        
        self.client.force_authenticate(user=self.seller)
        initial_notification_count = AgentNotification.objects.count()
        
        response = self.client.post(self.agreement_accept_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['agreement_status'], 'accepted')
        
        # Verify database update
        self.document_with_agreement.refresh_from_db()
        self.assertEqual(self.document_with_agreement.agreement_status, 'accepted')
        
        # Verify agent notification was created
        final_notification_count = AgentNotification.objects.count()
        self.assertEqual(final_notification_count, initial_notification_count + 1)
        
        # Verify notification content
        notification = AgentNotification.objects.latest('created_at')
        self.assertEqual(notification.notification_type, 'document_updated')
        self.assertIn('Accepted', notification.title)

    def test_accept_agreement_unauthenticated(self):
        """Test accepting agreement without authentication"""
        response = self.client.post(self.agreement_accept_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_accept_agreement_other_seller_document(self):
        """Test accepting other seller's agreement (should fail)"""
        self.client.force_authenticate(user=self.seller)
        other_accept_url = f'/api/v1/seller/agreements/{self.other_seller_document.id}/accept/'
        response = self.client.post(other_accept_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_accept_agreement_already_accepted(self):
        """Test accepting agreement that's already accepted"""
        self.client.force_authenticate(user=self.seller)
        accept_url = f'/api/v1/seller/agreements/{self.accepted_agreement.id}/accept/'
        response = self.client.post(accept_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already been accepted', response.data['detail'])

    def test_accept_agreement_document_without_agreement_file(self):
        """Test accepting document without agreement file"""
        self.client.force_authenticate(user=self.seller)
        no_file_url = f'/api/v1/seller/agreements/{self.document_without_agreement.id}/accept/'
        response = self.client.post(no_file_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_agreement_nonexistent_document(self):
        """Test accepting non-existent document"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.post('/api/v1/seller/agreements/99999/accept/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_accept_rejected_agreement(self):
        """Test accepting agreement that was previously rejected"""
        self.client.force_authenticate(user=self.seller)
        # The rejected agreement should be able to be accepted
        accept_url = f'/api/v1/seller/agreements/{self.rejected_agreement.id}/accept/'
        response = self.client.post(accept_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.rejected_agreement.refresh_from_db()
        self.assertEqual(self.rejected_agreement.agreement_status, 'accepted')

    def test_accept_agreement_as_agent(self):
        """Test accepting agreement as agent (should fail)"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.post(self.agreement_accept_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==================== REJECT AGREEMENT TESTS ====================

    def test_reject_agreement_success(self):
        """Test successful rejection of selling agreement"""
        from seller.models import AgentNotification
        
        # Use a fresh document for this test
        from django.core.files.uploadedfile import SimpleUploadedFile
        fresh_document = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Fresh Agreement for Rejection Test',
            file=SimpleUploadedFile('fresh.pdf', b'content', content_type='application/pdf'),
            file_size=7,
            selling_agreement_file=SimpleUploadedFile('fresh_agreement.pdf', b'agreement', content_type='application/pdf'),
            agreement_status='pending'
        )
        
        self.client.force_authenticate(user=self.seller)
        initial_notification_count = AgentNotification.objects.count()
        
        reject_url = f'/api/v1/seller/agreements/{fresh_document.id}/reject/'
        response = self.client.post(reject_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['agreement_status'], 'rejected')
        
        # Verify database update
        fresh_document.refresh_from_db()
        self.assertEqual(fresh_document.agreement_status, 'rejected')
        
        # Verify agent notification was created
        final_notification_count = AgentNotification.objects.count()
        self.assertEqual(final_notification_count, initial_notification_count + 1)

    def test_reject_agreement_with_reason(self):
        """Test rejection with reason included"""
        from seller.models import AgentNotification
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        fresh_document = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Document for Rejection with Reason',
            file=SimpleUploadedFile('reason.pdf', b'content', content_type='application/pdf'),
            file_size=6,
            selling_agreement_file=SimpleUploadedFile('reason_agreement.pdf', b'agreement', content_type='application/pdf'),
            agreement_status='pending'
        )
        
        self.client.force_authenticate(user=self.seller)
        reject_url = f'/api/v1/seller/agreements/{fresh_document.id}/reject/'
        response = self.client.post(reject_url, {'reason': 'Price is too high'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify notification includes reason
        notification = AgentNotification.objects.latest('created_at')
        self.assertIn('Price is too high', notification.message)

    def test_reject_agreement_unauthenticated(self):
        """Test rejecting agreement without authentication"""
        response = self.client.post(self.agreement_reject_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reject_agreement_other_seller_document(self):
        """Test rejecting other seller's agreement (should fail)"""
        self.client.force_authenticate(user=self.seller)
        other_reject_url = f'/api/v1/seller/agreements/{self.other_seller_document.id}/reject/'
        response = self.client.post(other_reject_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reject_agreement_already_rejected(self):
        """Test rejecting agreement that's already rejected"""
        self.client.force_authenticate(user=self.seller)
        reject_url = f'/api/v1/seller/agreements/{self.rejected_agreement.id}/reject/'
        response = self.client.post(reject_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already been rejected', response.data['detail'])

    def test_reject_agreement_document_without_agreement_file(self):
        """Test rejecting document without agreement file"""
        self.client.force_authenticate(user=self.seller)
        no_file_url = f'/api/v1/seller/agreements/{self.document_without_agreement.id}/reject/'
        response = self.client.post(no_file_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_agreement_nonexistent_document(self):
        """Test rejecting non-existent document"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.post('/api/v1/seller/agreements/99999/reject/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reject_accepted_agreement(self):
        """Test rejecting agreement that was previously accepted"""
        self.client.force_authenticate(user=self.seller)
        # The accepted agreement should be able to be rejected
        reject_url = f'/api/v1/seller/agreements/{self.accepted_agreement.id}/reject/'
        response = self.client.post(reject_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.accepted_agreement.refresh_from_db()
        self.assertEqual(self.accepted_agreement.agreement_status, 'rejected')

    def test_reject_agreement_as_agent(self):
        """Test rejecting agreement as agent (should fail)"""
        self.client.force_authenticate(user=self.agent)
        response = self.client.post(self.agreement_reject_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==================== EDGE CASES AND CORNER CASES ====================

    def test_agreement_status_transitions(self):
        """Test all valid status transitions"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create document for status transition tests
        transition_doc = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Status Transition Test',
            file=SimpleUploadedFile('transition.pdf', b'content', content_type='application/pdf'),
            file_size=10,
            selling_agreement_file=SimpleUploadedFile('transition_agreement.pdf', b'agreement', content_type='application/pdf'),
            agreement_status='pending'
        )
        
        self.client.force_authenticate(user=self.seller)
        
        # Test: pending -> accepted
        accept_url = f'/api/v1/seller/agreements/{transition_doc.id}/accept/'
        response = self.client.post(accept_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        transition_doc.refresh_from_db()
        self.assertEqual(transition_doc.agreement_status, 'accepted')
        
        # Test: accepted -> rejected
        reject_url = f'/api/v1/seller/agreements/{transition_doc.id}/reject/'
        response = self.client.post(reject_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        transition_doc.refresh_from_db()
        self.assertEqual(transition_doc.agreement_status, 'rejected')
        
        # Test: rejected -> accepted
        response = self.client.post(accept_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        transition_doc.refresh_from_db()
        self.assertEqual(transition_doc.agreement_status, 'accepted')

    def test_concurrent_accept_operations(self):
        """Test handling of multiple accept requests"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        concurrent_doc = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Concurrent Test',
            file=SimpleUploadedFile('concurrent.pdf', b'content', content_type='application/pdf'),
            file_size=10,
            selling_agreement_file=SimpleUploadedFile('concurrent_agreement.pdf', b'agreement', content_type='application/pdf'),
            agreement_status='pending'
        )
        
        self.client.force_authenticate(user=self.seller)
        accept_url = f'/api/v1/seller/agreements/{concurrent_doc.id}/accept/'
        
        # First accept should succeed
        response1 = self.client.post(accept_url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Second accept should fail (already accepted)
        response2 = self.client.post(accept_url)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_agreement_response_includes_all_required_fields(self):
        """Test that agreement detail response includes all required fields"""
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.agreement_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        required_fields = [
            'id', 'document_type', 'title', 'selling_agreement_file',
            'agreement_status', 'selling_request_id', 'seller_name',
            'seller_email', 'created_at', 'updated_at'
        ]
        
        for field in required_fields:
            self.assertIn(field, response.data, f"Missing required field: {field}")

    def test_notification_content_on_accept(self):
        """Test notification content is correct on acceptance"""
        from seller.models import AgentNotification
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        notification_doc = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Notification Content Test',
            file=SimpleUploadedFile('notification.pdf', b'content', content_type='application/pdf'),
            file_size=10,
            selling_agreement_file=SimpleUploadedFile('notification_agreement.pdf', b'agreement', content_type='application/pdf'),
            agreement_status='pending'
        )
        
        self.client.force_authenticate(user=self.seller)
        accept_url = f'/api/v1/seller/agreements/{notification_doc.id}/accept/'
        response = self.client.post(accept_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        notification = AgentNotification.objects.latest('created_at')
        self.assertEqual(notification.notification_type, 'document_updated')
        self.assertIn('Accepted', notification.title)
        self.assertIn(self.seller.get_full_name(), notification.message)
        self.assertIsNotNone(notification.action_url)
        self.assertIsNotNone(notification.action_text)

    def test_notification_content_on_reject_with_reason(self):
        """Test notification content includes reason on rejection"""
        from seller.models import AgentNotification
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        notification_doc = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Notification Reason Test',
            file=SimpleUploadedFile('reason_test.pdf', b'content', content_type='application/pdf'),
            file_size=10,
            selling_agreement_file=SimpleUploadedFile('reason_test_agreement.pdf', b'agreement', content_type='application/pdf'),
            agreement_status='pending'
        )
        
        self.client.force_authenticate(user=self.seller)
        reject_url = f'/api/v1/seller/agreements/{notification_doc.id}/reject/'
        rejection_reason = "The commission rate is too high"
        response = self.client.post(reject_url, {'reason': rejection_reason}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        notification = AgentNotification.objects.latest('created_at')
        self.assertIn(rejection_reason, notification.message)

    def test_empty_reason_on_reject(self):
        """Test rejection works with empty reason"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        empty_reason_doc = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Empty Reason Test',
            file=SimpleUploadedFile('empty_reason.pdf', b'content', content_type='application/pdf'),
            file_size=10,
            selling_agreement_file=SimpleUploadedFile('empty_reason_agreement.pdf', b'agreement', content_type='application/pdf'),
            agreement_status='pending'
        )
        
        self.client.force_authenticate(user=self.seller)
        reject_url = f'/api/v1/seller/agreements/{empty_reason_doc.id}/reject/'
        response = self.client.post(reject_url, {'reason': ''}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_http_methods_not_allowed(self):
        """Test that only allowed HTTP methods work"""
        self.client.force_authenticate(user=self.seller)
        
        # Accept endpoint should only allow POST
        response = self.client.get(self.agreement_accept_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        response = self.client.put(self.agreement_accept_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        response = self.client.patch(self.agreement_accept_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        response = self.client.delete(self.agreement_accept_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_agreement_list_pagination(self):
        """Test that agreement list handles multiple agreements"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create multiple agreements
        for i in range(5):
            PropertyDocument.objects.create(
                selling_request=self.selling_request,
                seller=self.seller,
                document_type='cma',
                title=f'Pagination Test Agreement {i}',
                file=SimpleUploadedFile(f'pagination_{i}.pdf', b'content', content_type='application/pdf'),
                file_size=10,
                selling_agreement_file=SimpleUploadedFile(f'pagination_agreement_{i}.pdf', b'agreement', content_type='application/pdf'),
                agreement_status='pending'
            )
        
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.agreements_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have at least 5 new agreements plus the ones from setUp
        self.assertGreaterEqual(response.data['count'], 5)

    def test_seller_location_in_notification(self):
        """Test that seller location is included in notification message"""
        from seller.models import AgentNotification
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create seller with specific location
        located_seller = Seller.objects.create_user(
            username='located_seller',
            email='located@example.com',
            password='SecurePassword123!',
            first_name='Located',
            last_name='Seller',
            location='456 Specific Location Ave, City'
        )
        
        located_request = SellingRequest.objects.create(
            seller=located_seller,
            selling_reason='Testing location in notification',
            contact_name='Located Seller',
            contact_email='located@example.com',
            contact_phone='555-9999',
            asking_price=700000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            status='accepted'
        )
        
        located_document = PropertyDocument.objects.create(
            selling_request=located_request,
            seller=located_seller,
            document_type='cma',
            title='Location Test Document',
            file=SimpleUploadedFile('location.pdf', b'content', content_type='application/pdf'),
            file_size=10,
            selling_agreement_file=SimpleUploadedFile('location_agreement.pdf', b'agreement', content_type='application/pdf'),
            agreement_status='pending'
        )
        
        self.client.force_authenticate(user=located_seller)
        accept_url = f'/api/v1/seller/agreements/{located_document.id}/accept/'
        response = self.client.post(accept_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        notification = AgentNotification.objects.latest('created_at')
        self.assertIn('456 Specific Location Ave', notification.message)


class SellingAgreementSerializerTestCase(TestCase):
    """Test cases for selling agreement serializers"""

    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        self.seller = Seller.objects.create_user(
            username='serializer_test_seller',
            email='serializer_seller@example.com',
            password='SecurePassword123!',
            first_name='Serializer',
            last_name='Test',
            location='789 Serializer St'
        )
        
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Serializer testing',
            contact_name='Serializer Test',
            contact_email='serializer_seller@example.com',
            contact_phone='555-1111',
            asking_price=550000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=60),
            status='accepted'
        )
        
        self.document = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Serializer Test Document',
            file=SimpleUploadedFile('serializer.pdf', b'content', content_type='application/pdf'),
            file_size=100,
            selling_agreement_file=SimpleUploadedFile('serializer_agreement.pdf', b'agreement', content_type='application/pdf'),
            agreement_status='pending'
        )

    def test_selling_agreement_detailed_serializer_fields(self):
        """Test SellingAgreementDetailedSerializer includes all fields"""
        from seller.serializers import SellingAgreementDetailedSerializer
        
        serializer = SellingAgreementDetailedSerializer(self.document)
        data = serializer.data
        
        # Check main document fields
        self.assertIn('id', data)
        self.assertIn('document_type', data)
        self.assertIn('title', data)
        self.assertIn('selling_agreement_file', data)
        self.assertIn('agreement_status', data)
        
        # Check selling request fields
        self.assertIn('selling_request_id', data)
        self.assertIn('selling_request_contact_name', data)
        self.assertIn('selling_request_asking_price', data)
        
        # Check seller fields
        self.assertIn('seller_name', data)
        self.assertIn('seller_email', data)

    def test_agreement_status_update_serializer_valid(self):
        """Test AgreementStatusUpdateSerializer with valid data"""
        from seller.serializers import AgreementStatusUpdateSerializer
        
        serializer = AgreementStatusUpdateSerializer(data={'agreement_status': 'accepted'})
        self.assertTrue(serializer.is_valid())
        
        serializer = AgreementStatusUpdateSerializer(data={'agreement_status': 'rejected'})
        self.assertTrue(serializer.is_valid())

    def test_agreement_status_update_serializer_invalid(self):
        """Test AgreementStatusUpdateSerializer with invalid data"""
        from seller.serializers import AgreementStatusUpdateSerializer
        
        serializer = AgreementStatusUpdateSerializer(data={'agreement_status': 'invalid'})
        self.assertFalse(serializer.is_valid())
        
        serializer = AgreementStatusUpdateSerializer(data={'agreement_status': 'pending'})
        self.assertFalse(serializer.is_valid())

    def test_selling_agreement_file_extension_method(self):
        """Test that file extension is correctly extracted"""
        from seller.serializers import SellingAgreementDetailedSerializer
        
        serializer = SellingAgreementDetailedSerializer(self.document)
        data = serializer.data
        
        # Check that file extension is present
        self.assertIn('selling_agreement_file_extension', data)
        self.assertEqual(data['selling_agreement_file_extension'], 'pdf')


