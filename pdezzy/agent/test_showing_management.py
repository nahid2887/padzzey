"""
Test cases for Agent Showing Schedule Management
Tests notifications, accept/decline functionality, and showing list views
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import date, time, timedelta
from decimal import Decimal

from buyer.models import Buyer, ShowingSchedule
from agent.models import Agent, PropertyListing
from seller.models import Seller, PropertyDocument, SellingRequest, AgentNotification


class AgentShowingNotificationTestCase(TestCase):
    """Test cases for agent showing notifications"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create agent
        self.agent = Agent.objects.create_user(
            username='testagent',
            email='agent@example.com',
            password='AgentPass123!',
            first_name='Jane',
            last_name='Agent',
            license_number='AG123456'
        )
        
        # Create buyer
        self.buyer = Buyer.objects.create_user(
            username='testbuyer',
            email='buyer@example.com',
            password='BuyerPass123!',
            first_name='John',
            last_name='Buyer'
        )
        
        # Create seller
        self.seller = Seller.objects.create_user(
            username='testseller',
            email='seller@example.com',
            password='SellerPass123!'
        )
        
        # Create selling request
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Testing',
            contact_name='Test Seller',
            contact_email='seller@example.com',
            contact_phone='+1234567890',
            asking_price=Decimal('350000.00'),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=90),
            status='accepted'
        )
        
        # Create property document
        from django.core.files.uploadedfile import SimpleUploadedFile
        temp_file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        
        self.property_doc = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Test CMA',
            file=temp_file,
            file_size=100,
            agreement_status='accepted'
        )
        
        # Create published property listing
        self.listing = PropertyListing.objects.create(
            agent=self.agent,
            property_document=self.property_doc,
            title='Beautiful Family Home',
            street_address='123 Main St',
            city='Springfield',
            state='IL',
            zip_code='62701',
            property_type='house',
            bedrooms=3,
            bathrooms=Decimal('2.0'),
            square_feet=2000,
            price=Decimal('350000.00'),
            description='Beautiful home',
            status='published',
            published_at=timezone.now()
        )
        
        self.future_date = date.today() + timedelta(days=7)

    def test_notification_created_on_showing_request(self):
        """Test that notification is automatically created when buyer requests showing"""
        initial_count = AgentNotification.objects.count()
        
        # Buyer creates showing request
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        # Check notification was created
        self.assertEqual(AgentNotification.objects.count(), initial_count + 1)
        
        # Get the notification
        notification = AgentNotification.objects.latest('created_at')
        self.assertEqual(notification.agent, self.agent)
        self.assertEqual(notification.showing_schedule, showing)
        self.assertEqual(notification.notification_type, 'showing_requested')
        self.assertEqual(notification.title, 'New Showing Request')
        self.assertIn(self.buyer.get_full_name(), notification.message)
        self.assertIn(self.listing.title, notification.message)
        self.assertFalse(notification.is_read)

    def test_agent_can_view_showing_list(self):
        """Test agent can view all showing requests for their listings"""
        self.client.force_authenticate(user=self.agent)
        
        # Create multiple showings
        ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='pending'
        )
        ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date + timedelta(days=1),
            preferred_time='afternoon',
            status='pending'
        )
        
        response = self.client.get('/api/v1/agent/showings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn('buyer', response.data[0])
        self.assertIn('property_listing', response.data[0])

    def test_agent_cannot_view_other_agent_showings(self):
        """Test agent can only see showings for their own listings"""
        # Create another agent with a listing
        other_agent = Agent.objects.create_user(
            username='otheragent',
            email='other@example.com',
            password='Pass123!',
            license_number='AG999'
        )
        
        # Create separate property document for other agent
        from django.core.files.uploadedfile import SimpleUploadedFile
        other_file = SimpleUploadedFile("other.pdf", b"other_content", content_type="application/pdf")
        
        other_selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Other',
            contact_name='Other Seller',
            contact_email='other@example.com',
            contact_phone='+9876543210',
            asking_price=Decimal('200000.00'),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=90),
            status='accepted'
        )
        
        other_property_doc = PropertyDocument.objects.create(
            selling_request=other_selling_request,
            seller=self.seller,
            document_type='cma',
            title='Other CMA',
            file=other_file,
            file_size=100,
            agreement_status='accepted'
        )
        
        other_listing = PropertyListing.objects.create(
            agent=other_agent,
            property_document=other_property_doc,
            title='Other Property',
            street_address='456 Oak Ave',
            city='Springfield',
            state='IL',
            zip_code='62702',
            property_type='condo',
            price=Decimal('200000.00'),
            status='published',
            published_at=timezone.now()
        )
        
        # Create showing for other agent's listing
        ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=other_listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='pending'
        )
        
        # Create showing for our agent's listing
        ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        # Agent should only see their own listing's showings
        self.client.force_authenticate(user=self.agent)
        response = self.client.get('/api/v1/agent/showings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['property_listing']['id'], self.listing.id)

    def test_agent_filter_showings_by_status(self):
        """Test agent can filter showings by status"""
        self.client.force_authenticate(user=self.agent)
        
        # Create showings with different statuses
        ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='pending'
        )
        ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date + timedelta(days=1),
            preferred_time='afternoon',
            status='accepted',
            confirmed_date=self.future_date + timedelta(days=1),
            confirmed_time=time(14, 0)
        )
        
        # Filter for pending only
        response = self.client.get('/api/v1/agent/showings/?status=pending')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'pending')

    def test_agent_accept_showing_request(self):
        """Test agent can accept a showing request"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        data = {
            'status': 'accepted',
            'agent_response': 'Looking forward to showing you the property!',
            'confirmed_date': self.future_date.isoformat(),
            'confirmed_time': '14:00:00'
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'accepted')
        self.assertEqual(response.data['agent_response'], 'Looking forward to showing you the property!')
        self.assertIsNotNone(response.data['responded_at'])
        self.assertEqual(response.data['confirmed_date'], self.future_date.isoformat())
        
        # Verify in database
        showing.refresh_from_db()
        self.assertEqual(showing.status, 'accepted')
        self.assertIsNotNone(showing.responded_at)

    def test_agent_decline_showing_request(self):
        """Test agent can decline a showing request"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='pending'
        )
        
        data = {
            'status': 'declined',
            'agent_response': 'Sorry, that time is not available.'
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'declined')
        self.assertEqual(response.data['agent_response'], 'Sorry, that time is not available.')
        self.assertIsNone(response.data['confirmed_date'])
        self.assertIsNone(response.data['confirmed_time'])

    def test_accept_requires_confirmed_datetime(self):
        """Test that accepting requires confirmed date and time"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        # Missing confirmed_time
        data = {
            'status': 'accepted',
            'agent_response': 'Sure!',
            'confirmed_date': self.future_date.isoformat()
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirmed_time', response.data)

    def test_cannot_respond_to_non_pending_showing(self):
        """Test agent cannot respond to already accepted/declined showings"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='accepted',
            confirmed_date=self.future_date,
            confirmed_time=time(14, 0)
        )
        
        data = {
            'status': 'declined',
            'agent_response': 'Changed my mind'
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_agent_view_showing_detail(self):
        """Test agent can view showing request details"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='evening',
            additional_notes='Would like to see the garage',
            status='pending'
        )
        
        response = self.client.get(f'/api/v1/agent/showings/{showing.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], showing.id)
        self.assertEqual(response.data['additional_notes'], 'Would like to see the garage')
        self.assertIn('buyer', response.data)
        self.assertEqual(response.data['buyer']['username'], 'testbuyer')

    def test_unauthenticated_cannot_access(self):
        """Test unauthenticated users cannot access agent showing endpoints"""
        response = self.client.get('/api/v1/agent/showings/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_buyer_cannot_access_agent_endpoints(self):
        """Test buyers cannot access agent showing management endpoints"""
        self.client.force_authenticate(user=self.buyer)
        
        response = self.client.get('/api/v1/agent/showings/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_notification_in_agent_notification_list(self):
        """Test showing notification appears in agent notification list"""
        self.client.force_authenticate(user=self.agent)
        
        # Create showing to trigger notification
        ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        response = self.client.get('/api/v1/agent/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Find showing notification
        showing_notifications = [n for n in response.data['results'] if n['notification_type'] == 'showing_requested']
        self.assertGreater(len(showing_notifications), 0)
        
        notification = showing_notifications[0]
        self.assertEqual(notification['title'], 'New Showing Request')
        self.assertIsNotNone(notification['showing_schedule_id'])
        self.assertEqual(notification['buyer_name'], 'John Buyer')
        self.assertEqual(notification['property_title'], 'Beautiful Family Home')

    def test_buyer_sees_agent_response(self):
        """Test buyer can see agent's response after agent responds"""
        # Agent accepts showing
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        data = {
            'status': 'accepted',
            'agent_response': 'See you then!',
            'confirmed_date': self.future_date.isoformat(),
            'confirmed_time': '14:00:00'
        }
        
        self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        
        # Buyer checks their showings
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get('/api/v1/buyer/showings/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        buyer_showing = response.data[0]
        self.assertEqual(buyer_showing['status'], 'accepted')
        self.assertEqual(buyer_showing['agent_response'], 'See you then!')
        self.assertIsNotNone(buyer_showing['confirmed_date'])

    def test_multiple_buyers_multiple_showings(self):
        """Test multiple buyers can request showings for same listing"""
        buyer2 = Buyer.objects.create_user(
            username='buyer2',
            email='buyer2@example.com',
            password='Pass123!'
        )
        
        # Both buyers request showings
        ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='pending'
        )
        ShowingSchedule.objects.create(
            buyer=buyer2,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        # Agent should see both
        self.client.force_authenticate(user=self.agent)
        response = self.client.get('/api/v1/agent/showings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_notification_message_format(self):
        """Test notification message contains correct information"""
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        notification = AgentNotification.objects.latest('created_at')
        
        # Check message contains key information
        self.assertIn('John Buyer', notification.message)
        self.assertIn('Beautiful Family Home', notification.message)
        self.assertIn('Afternoon', notification.message)
        self.assertIn(self.future_date.strftime('%B'), notification.message)
