"""
Test cases for the complete showing agreement workflow
Tests: buyer notification -> signature upload -> agreement completion
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


class ShowingAgreementWorkflowTestCase(TestCase):
    """Test complete showing agreement workflow"""

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

    def test_buyer_notification_on_agent_accept(self):
        """Test buyer receives notification when agent accepts showing"""
        self.client.force_authenticate(user=self.buyer)
        
        # Buyer creates showing request
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        # Agent accepts
        showing.status = 'accepted'
        showing.confirmed_date = self.future_date
        showing.confirmed_time = time(14, 0)
        showing.responded_at = timezone.now()
        showing.save()
        
        # Check buyer notification created
        notifications = BuyerNotification.objects.filter(
            buyer=self.buyer,
            showing_schedule=showing,
            notification_type='showing_accepted'
        )
        self.assertEqual(notifications.count(), 1)
        
        notification = notifications.first()
        self.assertEqual(notification.title, 'Showing Request Accepted! ✓')
        self.assertIn('accepted', notification.message.lower())
        self.assertFalse(notification.is_read)

    def test_buyer_notification_on_agent_decline(self):
        """Test buyer receives notification when agent declines showing"""
        self.client.force_authenticate(user=self.buyer)
        
        # Buyer creates showing request
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        # Agent declines
        showing.status = 'declined'
        showing.agent_response = 'Not available that day'
        showing.responded_at = timezone.now()
        showing.save()
        
        # Check buyer notification created
        notifications = BuyerNotification.objects.filter(
            buyer=self.buyer,
            showing_schedule=showing,
            notification_type='showing_declined'
        )
        self.assertEqual(notifications.count(), 1)
        
        notification = notifications.first()
        self.assertEqual(notification.title, 'Showing Request Declined')
        self.assertIn('declined', notification.message.lower())

    def test_buyer_can_view_notifications(self):
        """Test buyer can view their notifications"""
        self.client.force_authenticate(user=self.buyer)
        
        # Create showing and accept it
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        showing.status = 'accepted'
        showing.confirmed_date = self.future_date
        showing.confirmed_time = time(14, 0)
        showing.responded_at = timezone.now()
        showing.save()
        
        # Get notifications
        response = self.client.get('/api/v1/buyer/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertGreater(len(response.data['results']), 0)
        self.assertEqual(response.data['unread_count'], 1)

    def test_buyer_mark_notification_as_read(self):
        """Test buyer can mark notification as read"""
        self.client.force_authenticate(user=self.buyer)
        
        # Create notification
        notification = BuyerNotification.objects.create(
            buyer=self.buyer,
            notification_type='general',
            title='Test Notification',
            message='Test message'
        )
        
        self.assertFalse(notification.is_read)
        
        # Mark as read
        response = self.client.patch(f'/api/v1/buyer/notifications/{notification.id}/read/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify notification is read
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_buyer_sign_agreement_after_acceptance(self):
        """Test buyer can sign agreement after agent accepts"""
        self.client.force_authenticate(user=self.buyer)
        
        # Create and accept showing
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='accepted',
            confirmed_date=self.future_date,
            confirmed_time=time(14, 0)
        )
        
        # Generate fake signature (base64) - make it long enough
        signature_data = base64.b64encode(b'fake signature image data' * 10).decode('utf-8')
        
        # Sign agreement
        data = {
            'duration_type': 'one_property',
            'property_address': '123 Main St, Springfield, IL',
            'signature': signature_data,
            'agreement_accepted': True
        }
        
        response = self.client.post(
            f'/api/v1/buyer/showings/{showing.id}/sign-agreement/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['showing_schedule_id'], showing.id)
        self.assertTrue(response.data['agreement_accepted'])
        
        # Verify showing status updated to completed
        showing.refresh_from_db()
        self.assertEqual(showing.status, 'completed')
        
        # Verify agreement exists
        self.assertTrue(hasattr(showing, 'agreement'))
        agreement = showing.agreement
        self.assertEqual(agreement.buyer, self.buyer)
        self.assertEqual(agreement.agent, self.agent)

    def test_cannot_sign_agreement_for_pending_showing(self):
        """Test cannot sign agreement if showing not accepted"""
        self.client.force_authenticate(user=self.buyer)
        
        # Create pending showing
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        signature_data = base64.b64encode(b'fake signature').decode('utf-8')
        
        data = {
            'signature': signature_data,
            'agreement_accepted': True
        }
        
        response = self.client.post(
            f'/api/v1/buyer/showings/{showing.id}/sign-agreement/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_cannot_sign_agreement_twice(self):
        """Test cannot sign agreement if already signed"""
        self.client.force_authenticate(user=self.buyer)
        
        # Create accepted showing
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='accepted',
            confirmed_date=self.future_date,
            confirmed_time=time(14, 0)
        )
        
        # Create agreement
        ShowingAgreement.objects.create(
            showing_schedule=showing,
            buyer=self.buyer,
            agent=self.agent,
            duration_type='one_property',
            showing_date=self.future_date,
            signature='existing_signature',
            agreement_accepted=True
        )
        
        signature_data = base64.b64encode(b'new signature').decode('utf-8')
        
        data = {
            'signature': signature_data,
            'agreement_accepted': True
        }
        
        response = self.client.post(
            f'/api/v1/buyer/showings/{showing.id}/sign-agreement/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already signed', response.data['error'].lower())

    def test_agreement_requires_acceptance(self):
        """Test agreement validation requires acceptance"""
        self.client.force_authenticate(user=self.buyer)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='accepted',
            confirmed_date=self.future_date,
            confirmed_time=time(14, 0)
        )
        
        signature_data = base64.b64encode(b'signature').decode('utf-8')
        
        data = {
            'signature': signature_data,
            'agreement_accepted': False  # Not accepted
        }
        
        response = self.client.post(
            f'/api/v1/buyer/showings/{showing.id}/sign-agreement/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_agreement_requires_valid_signature(self):
        """Test agreement requires valid signature"""
        self.client.force_authenticate(user=self.buyer)
        
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
            'signature': '',  # Empty signature
            'agreement_accepted': True
        }
        
        response = self.client.post(
            f'/api/v1/buyer/showings/{showing.id}/sign-agreement/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_showing_list_includes_agreement_status(self):
        """Test showing list includes agreement status"""
        self.client.force_authenticate(user=self.buyer)
        
        # Create showing with agreement
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='completed',
            confirmed_date=self.future_date,
            confirmed_time=time(14, 0)
        )
        
        ShowingAgreement.objects.create(
            showing_schedule=showing,
            buyer=self.buyer,
            agent=self.agent,
            duration_type='one_property',
            showing_date=self.future_date,
            signature='signature_data',
            agreement_accepted=True
        )
        
        response = self.client.get('/api/v1/buyer/showings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        showing_data = response.data[0]
        self.assertIn('has_agreement', showing_data)
        self.assertTrue(showing_data['has_agreement'])
        self.assertIsNotNone(showing_data['agreement_signed_at'])

    def test_complete_workflow_end_to_end(self):
        """Test complete workflow from request to signed agreement"""
        # Step 1: Buyer creates showing request
        self.client.force_authenticate(user=self.buyer)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        self.assertEqual(showing.status, 'pending')
        
        # Step 2: Agent accepts showing
        showing.status = 'accepted'
        showing.confirmed_date = self.future_date
        showing.confirmed_time = time(14, 0)
        showing.agent_response = 'Looking forward to it!'
        showing.responded_at = timezone.now()
        showing.save()
        
        # Step 3: Verify buyer notification created
        notifications = BuyerNotification.objects.filter(
            buyer=self.buyer,
            showing_schedule=showing,
            notification_type='showing_accepted'
        )
        self.assertEqual(notifications.count(), 1)
        
        # Step 4: Buyer views notification
        response = self.client.get('/api/v1/buyer/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 1)
        
        # Step 5: Buyer signs agreement
        signature_data = base64.b64encode(b'buyer signature data for showing' * 10).decode('utf-8')
        data = {
            'duration_type': '7_days',
            'signature': signature_data,
            'agreement_accepted': True
        }
        
        response = self.client.post(
            f'/api/v1/buyer/showings/{showing.id}/sign-agreement/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 6: Verify showing completed
        showing.refresh_from_db()
        self.assertEqual(showing.status, 'completed')
        self.assertTrue(hasattr(showing, 'agreement'))
        
        # Step 7: Verify showing appears in list with agreement
        response = self.client.get('/api/v1/buyer/showings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        showing_data = response.data[0]
        self.assertEqual(showing_data['status'], 'completed')
        self.assertTrue(showing_data['has_agreement'])

    def test_buyer_can_view_agreement_details(self):
        """Test buyer can view signed agreement details"""
        self.client.force_authenticate(user=self.buyer)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='completed',
            confirmed_date=self.future_date,
            confirmed_time=time(14, 0)
        )
        
        agreement = ShowingAgreement.objects.create(
            showing_schedule=showing,
            buyer=self.buyer,
            agent=self.agent,
            duration_type='7_days',
            property_address='123 Main St',
            showing_date=self.future_date,
            signature='signature_data',
            agreement_accepted=True
        )
        
        response = self.client.get(f'/api/v1/buyer/showings/{showing.id}/agreement/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], agreement.id)
        self.assertEqual(response.data['duration_type'], '7_days')
        self.assertIn('buyer_name', response.data)
        self.assertIn('agent_name', response.data)

    def test_notification_filter_by_read_status(self):
        """Test filtering notifications by read status"""
        self.client.force_authenticate(user=self.buyer)
        
        # Create read and unread notifications
        BuyerNotification.objects.create(
            buyer=self.buyer,
            notification_type='general',
            title='Unread Notification',
            message='Unread',
            is_read=False
        )
        
        BuyerNotification.objects.create(
            buyer=self.buyer,
            notification_type='general',
            title='Read Notification',
            message='Read',
            is_read=True,
            read_at=timezone.now()
        )
        
        # Filter unread
        response = self.client.get('/api/v1/buyer/notifications/?is_read=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Unread Notification')
        
        # Filter read
        response = self.client.get('/api/v1/buyer/notifications/?is_read=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Read Notification')
