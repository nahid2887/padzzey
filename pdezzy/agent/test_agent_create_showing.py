"""
Test cases for agent-initiated showing schedules
Tests: agent creates showing -> buyer notification -> buyer signs agreement
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import date, time, timedelta
from decimal import Decimal
import base64

from buyer.models import Buyer, ShowingSchedule, BuyerNotification, ShowingAgreement
from agent.models import Agent, PropertyListing
from seller.models import Seller, PropertyDocument, SellingRequest


class AgentCreateShowingTestCase(TestCase):
    """Test cases for agent-initiated showing schedules"""

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
        self.future_time = time(14, 0)

    def test_agent_can_create_showing(self):
        """Test agent can create a showing schedule for a buyer"""
        self.client.force_authenticate(user=self.agent)
        
        data = {
            'buyer_id': self.buyer.id,
            'property_listing_id': self.listing.id,
            'scheduled_date': self.future_date.isoformat(),
            'scheduled_time': self.future_time.isoformat(),
            'agent_notes': 'Looking forward to showing you the property!'
        }
        
        response = self.client.post('/api/v1/agent/showings/create/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'accepted')
        self.assertEqual(response.data['confirmed_date'], self.future_date.isoformat())
        
        # Verify showing was created in database
        showing = ShowingSchedule.objects.get(id=response.data['id'])
        self.assertEqual(showing.buyer, self.buyer)
        self.assertEqual(showing.property_listing, self.listing)
        self.assertEqual(showing.status, 'accepted')
        self.assertEqual(showing.confirmed_date, self.future_date)
        self.assertEqual(showing.confirmed_time, self.future_time)

    def test_buyer_receives_notification_when_agent_creates_showing(self):
        """Test buyer gets notification when agent creates showing"""
        self.client.force_authenticate(user=self.agent)
        
        data = {
            'buyer_id': self.buyer.id,
            'property_listing_id': self.listing.id,
            'scheduled_date': self.future_date.isoformat(),
            'scheduled_time': self.future_time.isoformat()
        }
        
        response = self.client.post('/api/v1/agent/showings/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        showing_id = response.data['id']
        
        # Check buyer notification was created
        notifications = BuyerNotification.objects.filter(
            buyer=self.buyer,
            showing_schedule_id=showing_id,
            notification_type='showing_accepted'
        )
        
        self.assertEqual(notifications.count(), 1)
        notification = notifications.first()
        self.assertEqual(notification.title, 'Showing Scheduled by Agent ✓')
        self.assertIn('scheduled a showing', notification.message.lower())
        self.assertFalse(notification.is_read)

    def test_buyer_can_sign_agreement_after_agent_creates_showing(self):
        """Test complete workflow: agent creates -> buyer signs"""
        # Agent creates showing
        self.client.force_authenticate(user=self.agent)
        
        data = {
            'buyer_id': self.buyer.id,
            'property_listing_id': self.listing.id,
            'scheduled_date': self.future_date.isoformat(),
            'scheduled_time': self.future_time.isoformat(),
            'agent_notes': 'See you then!'
        }
        
        response = self.client.post('/api/v1/agent/showings/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        showing_id = response.data['id']
        
        # Buyer signs agreement
        self.client.force_authenticate(user=self.buyer)
        
        signature_data = base64.b64encode(b'buyer signature data' * 10).decode('utf-8')
        sign_data = {
            'duration_type': 'one_property',
            'signature': signature_data,
            'agreement_accepted': True
        }
        
        response = self.client.post(
            f'/api/v1/buyer/showings/{showing_id}/sign-agreement/',
            sign_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify showing is completed
        showing = ShowingSchedule.objects.get(id=showing_id)
        self.assertEqual(showing.status, 'completed')
        self.assertTrue(hasattr(showing, 'agreement'))

    def test_cannot_create_showing_for_nonexistent_buyer(self):
        """Test validation for non-existent buyer"""
        self.client.force_authenticate(user=self.agent)
        
        data = {
            'buyer_id': 99999,
            'property_listing_id': self.listing.id,
            'scheduled_date': self.future_date.isoformat(),
            'scheduled_time': self.future_time.isoformat()
        }
        
        response = self.client.post('/api/v1/agent/showings/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('buyer_id', response.data)

    def test_cannot_create_showing_for_other_agents_listing(self):
        """Test agent cannot create showing for another agent's listing"""
        # Create another agent with a listing
        other_agent = Agent.objects.create_user(
            username='otheragent',
            email='other@example.com',
            password='Pass123!',
            license_number='AG999'
        )
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        temp_file = SimpleUploadedFile("other.pdf", b"content", content_type="application/pdf")
        
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
            file=temp_file,
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
        
        # Try to create showing for other agent's listing
        self.client.force_authenticate(user=self.agent)
        
        data = {
            'buyer_id': self.buyer.id,
            'property_listing_id': other_listing.id,
            'scheduled_date': self.future_date.isoformat(),
            'scheduled_time': self.future_time.isoformat()
        }
        
        response = self.client.post('/api/v1/agent/showings/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_create_showing_with_past_date(self):
        """Test cannot schedule showing in the past"""
        self.client.force_authenticate(user=self.agent)
        
        past_date = date.today() - timedelta(days=1)
        
        data = {
            'buyer_id': self.buyer.id,
            'property_listing_id': self.listing.id,
            'scheduled_date': past_date.isoformat(),
            'scheduled_time': self.future_time.isoformat()
        }
        
        response = self.client.post('/api/v1/agent/showings/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_agent_created_showing_appears_in_agent_list(self):
        """Test agent-created showing appears in agent's showing list"""
        self.client.force_authenticate(user=self.agent)
        
        data = {
            'buyer_id': self.buyer.id,
            'property_listing_id': self.listing.id,
            'scheduled_date': self.future_date.isoformat(),
            'scheduled_time': self.future_time.isoformat()
        }
        
        create_response = self.client.post('/api/v1/agent/showings/create/', data, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        # Get agent's showing list
        list_response = self.client.get('/api/v1/agent/showings/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        
        showing_ids = [s['id'] for s in list_response.data]
        self.assertIn(create_response.data['id'], showing_ids)

    def test_agent_created_showing_appears_in_buyer_list(self):
        """Test agent-created showing appears in buyer's showing list"""
        self.client.force_authenticate(user=self.agent)
        
        data = {
            'buyer_id': self.buyer.id,
            'property_listing_id': self.listing.id,
            'scheduled_date': self.future_date.isoformat(),
            'scheduled_time': self.future_time.isoformat()
        }
        
        create_response = self.client.post('/api/v1/agent/showings/create/', data, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        # Get buyer's showing list
        self.client.force_authenticate(user=self.buyer)
        list_response = self.client.get('/api/v1/buyer/showings/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        
        showing_ids = [s['id'] for s in list_response.data]
        self.assertIn(create_response.data['id'], showing_ids)

    def test_buyer_cannot_create_agent_initiated_showing(self):
        """Test buyers cannot access agent showing creation endpoint"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'buyer_id': self.buyer.id,
            'property_listing_id': self.listing.id,
            'scheduled_date': self.future_date.isoformat(),
            'scheduled_time': self.future_time.isoformat()
        }
        
        response = self.client.post('/api/v1/agent/showings/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_complete_agent_workflow_end_to_end(self):
        """Test complete agent-initiated workflow"""
        # Step 1: Agent creates showing
        self.client.force_authenticate(user=self.agent)
        
        data = {
            'buyer_id': self.buyer.id,
            'property_listing_id': self.listing.id,
            'scheduled_date': self.future_date.isoformat(),
            'scheduled_time': self.future_time.isoformat(),
            'agent_notes': 'Property tour scheduled'
        }
        
        response = self.client.post('/api/v1/agent/showings/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'accepted')
        showing_id = response.data['id']
        
        # Step 2: Verify buyer notification
        notifications = BuyerNotification.objects.filter(
            buyer=self.buyer,
            showing_schedule_id=showing_id
        )
        self.assertEqual(notifications.count(), 1)
        
        # Step 3: Buyer views notifications
        self.client.force_authenticate(user=self.buyer)
        notif_response = self.client.get('/api/v1/buyer/notifications/')
        self.assertEqual(notif_response.status_code, status.HTTP_200_OK)
        self.assertEqual(notif_response.data['unread_count'], 1)
        
        # Step 4: Buyer signs agreement
        signature_data = base64.b64encode(b'signature' * 20).decode('utf-8')
        sign_data = {
            'duration_type': '7_days',
            'signature': signature_data,
            'agreement_accepted': True
        }
        
        sign_response = self.client.post(
            f'/api/v1/buyer/showings/{showing_id}/sign-agreement/',
            sign_data,
            format='json'
        )
        self.assertEqual(sign_response.status_code, status.HTTP_201_CREATED)
        
        # Step 5: Verify completed in both lists
        buyer_list = self.client.get('/api/v1/buyer/showings/')
        self.assertEqual(buyer_list.status_code, status.HTTP_200_OK)
        buyer_showing = [s for s in buyer_list.data if s['id'] == showing_id][0]
        self.assertEqual(buyer_showing['status'], 'completed')
        self.assertTrue(buyer_showing['has_agreement'])
        
        self.client.force_authenticate(user=self.agent)
        agent_list = self.client.get('/api/v1/agent/showings/')
        self.assertEqual(agent_list.status_code, status.HTTP_200_OK)
        agent_showing = [s for s in agent_list.data if s['id'] == showing_id][0]
        self.assertEqual(agent_showing['status'], 'completed')
        self.assertTrue(agent_showing['has_agreement'])

    def test_agent_notes_are_stored(self):
        """Test agent notes are saved correctly"""
        self.client.force_authenticate(user=self.agent)
        
        notes = 'Please arrive 5 minutes early'
        data = {
            'buyer_id': self.buyer.id,
            'property_listing_id': self.listing.id,
            'scheduled_date': self.future_date.isoformat(),
            'scheduled_time': self.future_time.isoformat(),
            'agent_notes': notes
        }
        
        response = self.client.post('/api/v1/agent/showings/create/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        showing = ShowingSchedule.objects.get(id=response.data['id'])
        self.assertEqual(showing.agent_response, notes)
