"""
Test cases for Buyer Showing Schedule functionality
Tests the showing schedule system for buyers to request showings on agent listings
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import date, time, timedelta
from decimal import Decimal

from buyer.models import Buyer, ShowingSchedule
from agent.models import Agent, PropertyListing
from seller.models import Seller, PropertyDocument


class ShowingScheduleTestCase(TestCase):
    """Test cases for showing schedule creation and management"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create buyer
        self.buyer = Buyer.objects.create_user(
            username='testbuyer',
            email='buyer@example.com',
            password='BuyerPass123!',
            first_name='John',
            last_name='Buyer'
        )
        
        # Create agent
        self.agent = Agent.objects.create_user(
            username='testagent',
            email='agent@example.com',
            password='AgentPass123!',
            first_name='Jane',
            last_name='Agent',
            license_number='AG123456'
        )
        
        # Create seller for property document
        self.seller = Seller.objects.create_user(
            username='testseller',
            email='seller@example.com',
            password='SellerPass123!'
        )
        
        # Create selling request
        from seller.models import SellingRequest
        self.selling_request = SellingRequest.objects.create(
            seller=self.seller,
            selling_reason='Moving to new city',
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
            description='Beautiful home in great location',
            status='published',
            published_at=timezone.now()
        )
        
        # URLs
        self.listing_detail_url = f'/api/v1/buyer/agent-listings/{self.listing.id}/'
        self.showing_create_url = '/api/v1/buyer/showings/create/'
        self.showing_list_url = '/api/v1/buyer/showings/'
        
        # Future date for showing
        self.future_date = date.today() + timedelta(days=7)

    def test_get_agent_listing_detail_public(self):
        """Test that anyone can view agent listing details"""
        response = self.client.get(self.listing_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.listing.id)
        self.assertEqual(response.data['title'], 'Beautiful Family Home')
        self.assertEqual(response.data['city'], 'Springfield')
        self.assertIn('agent', response.data)
        self.assertEqual(response.data['agent']['license_number'], 'AG123456')

    def test_get_nonexistent_listing(self):
        """Test getting a listing that doesn't exist"""
        url = '/api/v1/buyer/agent-listings/99999/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_draft_listing_not_visible(self):
        """Test that draft listings are not visible to buyers"""
        draft_listing = PropertyListing.objects.create(
            agent=self.agent,
            property_document=self.property_doc,
            title='Draft Listing',
            street_address='456 Oak Ave',
            city='Springfield',
            state='IL',
            zip_code='62702',
            property_type='condo',
            price=Decimal('200000.00'),
            status='draft'  # Not published
        )
        url = f'/api/v1/buyer/agent-listings/{draft_listing.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_showing_schedule_success(self):
        """Test successful creation of showing schedule"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': self.future_date.isoformat(),
            'preferred_time': 'afternoon',
            'additional_notes': 'Would like to see the backyard and garage'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['preferred_time'], 'afternoon')
        self.assertIn('buyer', response.data)
        self.assertIn('property_listing', response.data)
        
        # Verify in database
        schedule = ShowingSchedule.objects.get(id=response.data['id'])
        self.assertEqual(schedule.buyer, self.buyer)
        self.assertEqual(schedule.property_listing, self.listing)
        self.assertEqual(schedule.status, 'pending')

    def test_create_showing_unauthenticated(self):
        """Test that unauthenticated users cannot create showings"""
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': self.future_date.isoformat(),
            'preferred_time': 'morning'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_showing_past_date(self):
        """Test that showing cannot be scheduled for past date"""
        self.client.force_authenticate(user=self.buyer)
        
        past_date = date.today() - timedelta(days=1)
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': past_date.isoformat(),
            'preferred_time': 'afternoon'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('requested_date', response.data)

    def test_create_showing_invalid_listing(self):
        """Test creating showing for non-existent listing"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': 99999,
            'requested_date': self.future_date.isoformat(),
            'preferred_time': 'evening'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_showing_invalid_time_slot(self):
        """Test creating showing with invalid time slot"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': self.future_date.isoformat(),
            'preferred_time': 'midnight'  # Invalid
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_showing_list(self):
        """Test getting list of buyer's showings"""
        self.client.force_authenticate(user=self.buyer)
        
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
            status='accepted',
            agent_response='Confirmed!',
            responded_at=timezone.now()
        )
        
        response = self.client.get(self.showing_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_showing_by_status(self):
        """Test filtering showings by status"""
        self.client.force_authenticate(user=self.buyer)
        
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
            status='accepted'
        )
        
        # Filter for pending only
        response = self.client.get(f'{self.showing_list_url}?status=pending')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'pending')

    def test_get_showing_detail(self):
        """Test getting details of a specific showing"""
        self.client.force_authenticate(user=self.buyer)
        
        schedule = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='evening',
            additional_notes='Special request'
        )
        
        url = f'/api/v1/buyer/showings/{schedule.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], schedule.id)
        self.assertEqual(response.data['additional_notes'], 'Special request')

    def test_cannot_view_other_buyer_showing(self):
        """Test that buyer cannot view another buyer's showing"""
        # Create another buyer
        other_buyer = Buyer.objects.create_user(
            username='otherbuyer',
            email='other@example.com',
            password='Pass123!'
        )
        
        # Create showing for other buyer
        schedule = ShowingSchedule.objects.create(
            buyer=other_buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning'
        )
        
        # Try to access as first buyer
        self.client.force_authenticate(user=self.buyer)
        url = f'/api/v1/buyer/showings/{schedule.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_showing_success(self):
        """Test successfully cancelling a showing"""
        self.client.force_authenticate(user=self.buyer)
        
        schedule = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='pending'
        )
        
        url = f'/api/v1/buyer/showings/{schedule.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify status changed
        schedule.refresh_from_db()
        self.assertEqual(schedule.status, 'cancelled')

    def test_cancel_accepted_showing(self):
        """Test that accepted showings can also be cancelled"""
        self.client.force_authenticate(user=self.buyer)
        
        schedule = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='accepted',
            agent_response='See you then!',
            responded_at=timezone.now()
        )
        
        url = f'/api/v1/buyer/showings/{schedule.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        schedule.refresh_from_db()
        self.assertEqual(schedule.status, 'cancelled')

    def test_cannot_cancel_completed_showing(self):
        """Test that completed showings cannot be cancelled"""
        self.client.force_authenticate(user=self.buyer)
        
        schedule = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='completed'
        )
        
        url = f'/api/v1/buyer/showings/{schedule.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Status should remain unchanged
        schedule.refresh_from_db()
        self.assertEqual(schedule.status, 'completed')

    def test_cannot_cancel_declined_showing(self):
        """Test that declined showings cannot be cancelled"""
        self.client.force_authenticate(user=self.buyer)
        
        schedule = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning',
            status='declined',
            agent_response='Not available',
            responded_at=timezone.now()
        )
        
        url = f'/api/v1/buyer/showings/{schedule.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_showing_schedule_model_str(self):
        """Test string representation of ShowingSchedule model"""
        schedule = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='afternoon',
            status='pending'
        )
        
        expected = f"testbuyer - Beautiful Family Home (pending)"
        self.assertEqual(str(schedule), expected)

    def test_multiple_showings_same_listing(self):
        """Test that buyer can create multiple showings for same listing"""
        self.client.force_authenticate(user=self.buyer)
        
        # Create first showing
        data1 = {
            'property_listing_id': self.listing.id,
            'requested_date': self.future_date.isoformat(),
            'preferred_time': 'morning'
        }
        response1 = self.client.post(self.showing_create_url, data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Create second showing for different date
        data2 = {
            'property_listing_id': self.listing.id,
            'requested_date': (self.future_date + timedelta(days=3)).isoformat(),
            'preferred_time': 'evening'
        }
        response2 = self.client.post(self.showing_create_url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        
        # Verify both exist
        count = ShowingSchedule.objects.filter(buyer=self.buyer).count()
        self.assertEqual(count, 2)

    def test_showing_with_empty_notes(self):
        """Test creating showing without additional notes"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': self.future_date.isoformat(),
            'preferred_time': 'afternoon'
            # No additional_notes
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['additional_notes'], '')

    def test_showing_ordering(self):
        """Test that showings are ordered by creation date (newest first)"""
        self.client.force_authenticate(user=self.buyer)
        
        # Create three showings
        schedule1 = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date,
            preferred_time='morning'
        )
        schedule2 = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date + timedelta(days=1),
            preferred_time='afternoon'
        )
        schedule3 = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=self.future_date + timedelta(days=2),
            preferred_time='evening'
        )
        
        response = self.client.get(self.showing_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should be in reverse chronological order (newest first)
        self.assertEqual(response.data[0]['id'], schedule3.id)
        self.assertEqual(response.data[1]['id'], schedule2.id)
        self.assertEqual(response.data[2]['id'], schedule1.id)
