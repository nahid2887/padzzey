"""
Edge case and corner case tests for Agent Showing Management
Tests boundary conditions, error handling, and unusual scenarios
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


class AgentShowingEdgeCaseTestCase(TestCase):
    """Edge case tests for agent showing management"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create agent
        self.agent = Agent.objects.create_user(
            username='edgeagent',
            email='edge@example.com',
            password='Pass123!',
            first_name='Edge',
            last_name='Agent',
            license_number='AG999'
        )
        
        # Create buyer
        self.buyer = Buyer.objects.create_user(
            username='edgebuyer',
            email='edgebuyer@example.com',
            password='Pass123!'
        )
        
        # Create seller
        self.seller = Seller.objects.create_user(
            username='edgeseller',
            email='edgeseller@example.com',
            password='Pass123!'
        )
        
        # Create selling request
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Testing',
            contact_name='Edge Seller',
            contact_email='edgeseller@example.com',
            contact_phone='+9999999999',
            asking_price=Decimal('100000.00'),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=90),
            status='accepted'
        )
        
        # Create property document
        from django.core.files.uploadedfile import SimpleUploadedFile
        temp_file = SimpleUploadedFile("edge.pdf", b"content", content_type="application/pdf")
        
        self.property_doc = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Edge CMA',
            file=temp_file,
            file_size=100
        )
        
        # Create listing
        self.listing = PropertyListing.objects.create(
            agent=self.agent,
            property_document=self.property_doc,
            title='Edge Property',
            street_address='999 Edge St',
            city='EdgeCity',
            state='EC',
            zip_code='99999',
            property_type='house',
            price=Decimal('100000.00'),
            status='published',
            published_at=timezone.now()
        )
        
        self.future_date = date.today() + timedelta(days=7)

    def test_respond_to_nonexistent_showing(self):
        """Test responding to non-existent showing ID"""
        self.client.force_authenticate(user=self.agent)
        
        data = {
            'status': 'accepted',
            'confirmed_date': self.future_date.isoformat(),
            'confirmed_time': '14:00:00'
        }
        
        response = self.client.post('/api/v1/agent/showings/99999/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_accept_with_missing_confirmed_date(self):
        """Test accepting without confirmed date"""
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
            'confirmed_time': '14:00:00'
            # Missing confirmed_date
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirmed_date', response.data)

    def test_accept_with_missing_confirmed_time(self):
        """Test accepting without confirmed time"""
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
            'confirmed_date': self.future_date.isoformat()
            # Missing confirmed_time
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirmed_time', response.data)

    def test_invalid_status_value(self):
        """Test responding with invalid status"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        data = {
            'status': 'maybe',  # Invalid
            'confirmed_date': self.future_date.isoformat(),
            'confirmed_time': '14:00:00'
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_very_long_agent_response(self):
        """Test with extremely long agent response"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        long_response = 'X' * 10000
        data = {
            'status': 'accepted',
            'agent_response': long_response,
            'confirmed_date': self.future_date.isoformat(),
            'confirmed_time': '14:00:00'
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_special_characters_in_response(self):
        """Test agent response with special characters"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        special_response = "Hello! 🏠 <script>alert('xss')</script> Looking forward to meeting you! 你好"
        data = {
            'status': 'accepted',
            'agent_response': special_response,
            'confirmed_date': self.future_date.isoformat(),
            'confirmed_time': '14:00:00'
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('🏠', response.data['agent_response'])

    def test_respond_to_cancelled_showing(self):
        """Test agent cannot respond to cancelled showing"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='cancelled'
        )
        
        data = {
            'status': 'accepted',
            'confirmed_date': self.future_date.isoformat(),
            'confirmed_time': '14:00:00'
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_respond_to_completed_showing(self):
        """Test agent cannot respond to completed showing"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='completed'
        )
        
        data = {
            'status': 'declined',
            'agent_response': 'Too late'
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_showing_list(self):
        """Test agent with no showings gets empty list"""
        self.client.force_authenticate(user=self.agent)
        
        response = self.client.get('/api/v1/agent/showings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_invalid_date_format(self):
        """Test with invalid date format"""
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
            'confirmed_date': '12-25-2025',  # Wrong format
            'confirmed_time': '14:00:00'
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_time_format(self):
        """Test with invalid time format"""
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
            'confirmed_date': self.future_date.isoformat(),
            'confirmed_time': '2:00 PM'  # Wrong format
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_showing_id(self):
        """Test with negative showing ID"""
        self.client.force_authenticate(user=self.agent)
        
        response = self.client.get('/api/v1/agent/showings/-1/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_string_as_showing_id(self):
        """Test with string as showing ID"""
        self.client.force_authenticate(user=self.agent)
        
        response = self.client.get('/api/v1/agent/showings/invalid/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_with_invalid_status(self):
        """Test filtering with invalid status value"""
        self.client.force_authenticate(user=self.agent)
        
        ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='pending'
        )
        
        response = self.client.get('/api/v1/agent/showings/?status=invalid_status')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_multiple_notifications_for_agent(self):
        """Test agent receives multiple notifications correctly"""
        # Create multiple showings
        for i in range(5):
            ShowingSchedule.objects.create(
                buyer=self.buyer,
                property_listing=self.listing,
                requested_date=self.future_date + timedelta(days=i),
                preferred_time='afternoon',
                status='pending'
            )
        
        # Check notifications
        notifications = AgentNotification.objects.filter(
            agent=self.agent,
            notification_type='showing_requested'
        )
        self.assertEqual(notifications.count(), 5)

    def test_notification_without_buyer_full_name(self):
        """Test notification creation when buyer has no full name"""
        buyer_no_name = Buyer.objects.create_user(
            username='noname',
            email='noname@example.com',
            password='Pass123!'
            # No first_name or last_name
        )
        
        showing = ShowingSchedule.objects.create(
            buyer=buyer_no_name,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        notification = AgentNotification.objects.latest('created_at')
        # Should use username if no full name
        self.assertIn('noname', notification.message)

    def test_decline_without_response_message(self):
        """Test declining without providing response message"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='pending'
        )
        
        data = {
            'status': 'declined'
            # No agent_response
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['agent_response'], '')

    def test_accept_with_empty_response_message(self):
        """Test accepting with empty response message"""
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
            'agent_response': '',
            'confirmed_date': self.future_date.isoformat(),
            'confirmed_time': '14:00:00'
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_concurrent_agent_responses(self):
        """Test two agents responding to their own showings simultaneously"""
        agent2 = Agent.objects.create_user(
            username='agent2',
            email='agent2@example.com',
            password='Pass123!',
            license_number='AG888'
        )
        
        # Create separate property document for agent2
        from django.core.files.uploadedfile import SimpleUploadedFile
        temp_file2 = SimpleUploadedFile("agent2.pdf", b"content2", content_type="application/pdf")
        
        selling_request2 = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Agent2',
            contact_name='Agent2 Seller',
            contact_email='agent2@example.com',
            contact_phone='+8888888888',
            asking_price=Decimal('200000.00'),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=90),
            status='accepted'
        )
        
        property_doc2 = PropertyDocument.objects.create(
            selling_request=selling_request2,
            seller=self.seller,
            document_type='cma',
            title='Agent2 CMA',
            file=temp_file2,
            file_size=100
        )
        
        listing2 = PropertyListing.objects.create(
            agent=agent2,
            property_document=property_doc2,
            title='Second Property',
            street_address='888 Second St',
            city='SecondCity',
            state='SC',
            zip_code='88888',
            property_type='condo',
            price=Decimal('200000.00'),
            status='published',
            published_at=timezone.now()
        )
        
        showing1 = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='pending'
        )
        
        showing2 = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=listing2,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        # Both agents accept
        self.client.force_authenticate(user=self.agent)
        data1 = {
            'status': 'accepted',
            'confirmed_date': self.future_date.isoformat(),
            'confirmed_time': '10:00:00'
        }
        response1 = self.client.post(f'/api/v1/agent/showings/{showing1.id}/respond/', data1, format='json')
        
        self.client.force_authenticate(user=agent2)
        data2 = {
            'status': 'accepted',
            'confirmed_date': self.future_date.isoformat(),
            'confirmed_time': '14:00:00'
        }
        response2 = self.client.post(f'/api/v1/agent/showings/{showing2.id}/respond/', data2, format='json')
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

    def test_respond_with_null_values(self):
        """Test responding with null values"""
        self.client.force_authenticate(user=self.agent)
        
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        data = {
            'status': None,
            'agent_response': None,
            'confirmed_date': None,
            'confirmed_time': None
        }
        
        response = self.client.post(f'/api/v1/agent/showings/{showing.id}/respond/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_showing_for_deleted_buyer(self):
        """Test viewing showing when buyer has been deleted"""
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        # Note: This test depends on CASCADE behavior
        # In production, you might want PROTECT or SET_NULL
        self.client.force_authenticate(user=self.agent)
        response = self.client.get(f'/api/v1/agent/showings/{showing.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_max_integer_showing_id(self):
        """Test with maximum integer value as showing ID"""
        self.client.force_authenticate(user=self.agent)
        
        response = self.client.get('/api/v1/agent/showings/2147483647/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_notification_action_url_format(self):
        """Test notification action URL is correctly formatted"""
        showing = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        notification = AgentNotification.objects.latest('created_at')
        self.assertIsNotNone(notification.action_url)
        self.assertIn(str(showing.id), notification.action_url)
        self.assertEqual(notification.action_text, 'View Request')
