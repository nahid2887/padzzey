"""
Edge case and corner case tests for Buyer Showing Schedule
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
from seller.models import Seller, PropertyDocument


class ShowingScheduleEdgeCaseTestCase(TestCase):
    """Edge case tests for showing schedule functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create buyer
        self.buyer = Buyer.objects.create_user(
            username='edgebuyer',
            email='edge@example.com',
            password='Pass123!',
            phone_number='+1234567890'
        )
        
        # Create agent
        self.agent = Agent.objects.create_user(
            username='edgeagent',
            email='edgeagent@example.com',
            password='Pass123!',
            license_number='AG999'
        )
        
        # Create seller
        self.seller = Seller.objects.create_user(
            username='edgeseller',
            email='edgeseller@example.com',
            password='Pass123!'
        )
        
        # Create selling request
        from seller.models import SellingRequest
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
        temp_file = SimpleUploadedFile("edge_test.pdf", b"file_content", content_type="application/pdf")
        
        self.property_doc = PropertyDocument.objects.create(
            selling_request=self.selling_request,
            seller=self.seller,
            document_type='cma',
            title='Edge Test CMA',
            file=temp_file,
            file_size=100,
            agreement_status='accepted'
        )
        
        # Create published listing
        self.listing = PropertyListing.objects.create(
            agent=self.agent,
            property_document=self.property_doc,
            title='Edge Case Property',
            street_address='999 Edge St',
            city='TestCity',
            state='TS',
            zip_code='99999',
            property_type='house',
            price=Decimal('100000.00'),
            status='published',
            published_at=timezone.now()
        )
        
        self.showing_create_url = '/api/v1/buyer/showings/create/'
        self.showing_list_url = '/api/v1/buyer/showings/'

    def test_schedule_today(self):
        """Test scheduling for today's date (edge of valid date range)"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': date.today().isoformat(),
            'preferred_time': 'afternoon'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        # Should succeed - today is not in the past
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_schedule_far_future(self):
        """Test scheduling for date far in the future"""
        self.client.force_authenticate(user=self.buyer)
        
        far_future = date.today() + timedelta(days=365)
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': far_future.isoformat(),
            'preferred_time': 'morning'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_very_long_additional_notes(self):
        """Test with extremely long additional notes"""
        self.client.force_authenticate(user=self.buyer)
        
        long_notes = 'X' * 10000  # Very long text
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'evening',
            'additional_notes': long_notes
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['additional_notes']), 10000)

    def test_special_characters_in_notes(self):
        """Test additional notes with special characters"""
        self.client.force_authenticate(user=self.buyer)
        
        special_notes = "Hello! 🏡 Looking for: \n- Garage\n- Backyard\n- $$ good price <script>alert('xss')</script>"
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'afternoon',
            'additional_notes': special_notes
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('🏡', response.data['additional_notes'])

    def test_missing_required_fields(self):
        """Test creating showing with missing required fields"""
        self.client.force_authenticate(user=self.buyer)
        
        # Missing property_listing_id
        data = {
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'afternoon'
        }
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('property_listing_id', response.data)

    def test_invalid_date_format(self):
        """Test with invalid date format"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': '12-25-2025',  # Wrong format
            'preferred_time': 'morning'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_string_date(self):
        """Test with empty string as date"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': '',
            'preferred_time': 'afternoon'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_null_property_listing_id(self):
        """Test with null property listing ID"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': None,
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'morning'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_listing_id(self):
        """Test with negative listing ID"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': -1,
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'afternoon'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_zero_listing_id(self):
        """Test with zero as listing ID"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': 0,
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'evening'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_string_as_listing_id(self):
        """Test with string as listing ID"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': 'not_a_number',
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'morning'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_case_sensitive_time_slot(self):
        """Test that preferred_time is case sensitive"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'MORNING'  # Uppercase
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_whitespace_in_time_slot(self):
        """Test time slot with extra whitespace"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': ' morning '  # Extra spaces
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_multiple_concurrent_showings_same_time(self):
        """Test creating multiple showings for same listing and time"""
        self.client.force_authenticate(user=self.buyer)
        
        request_date = date.today() + timedelta(days=1)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': request_date.isoformat(),
            'preferred_time': 'afternoon'
        }
        
        # Create first showing
        response1 = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Create second showing with same data
        response2 = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        
        # Both should be created (no uniqueness constraint)
        count = ShowingSchedule.objects.filter(
            buyer=self.buyer,
            requested_date=request_date
        ).count()
        self.assertEqual(count, 2)

    def test_cancel_already_cancelled(self):
        """Test cancelling an already cancelled showing"""
        self.client.force_authenticate(user=self.buyer)
        
        schedule = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=date.today() + timedelta(days=1),
            preferred_time='morning',
            status='cancelled'
        )
        
        url = f'/api/v1/buyer/showings/{schedule.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_showing_with_invalid_id(self):
        """Test getting showing with non-numeric ID"""
        self.client.force_authenticate(user=self.buyer)
        
        url = '/api/v1/buyer/showings/invalid_id/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_agent_as_buyer_cannot_access(self):
        """Test that agent user cannot access buyer showing endpoints"""
        self.client.force_authenticate(user=self.agent)
        
        response = self.client.get(self.showing_list_url)
        # Should fail because agent is not a buyer
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_showing_archived_listing(self):
        """Test creating showing for archived listing"""
        self.listing.status = 'archived'
        self.listing.save()
        
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'morning'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        # Should fail because listing is not published
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_showing_sold_listing(self):
        """Test creating showing for sold listing"""
        self.listing.status = 'sold'
        self.listing.save()
        
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'afternoon'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        # Should fail because listing is not published
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_showing_list(self):
        """Test getting showing list when buyer has no showings"""
        self.client.force_authenticate(user=self.buyer)
        
        response = self.client.get(self.showing_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
        self.assertIsInstance(response.data, list)

    def test_filter_with_invalid_status(self):
        """Test filtering with invalid status value"""
        self.client.force_authenticate(user=self.buyer)
        
        ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=date.today() + timedelta(days=1),
            preferred_time='morning',
            status='pending'
        )
        
        response = self.client.get(f'{self.showing_list_url}?status=invalid_status')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return empty list for invalid status
        self.assertEqual(len(response.data), 0)

    def test_showing_response_fields_null(self):
        """Test that optional fields are properly null"""
        self.client.force_authenticate(user=self.buyer)
        
        schedule = ShowingSchedule.objects.create(
            buyer=self.buyer,
            property_listing=self.listing,
            requested_date=date.today() + timedelta(days=1),
            preferred_time='evening',
            status='pending'
        )
        
        url = f'/api/v1/buyer/showings/{schedule.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['agent_response'])
        self.assertIsNone(response.data['responded_at'])
        self.assertIsNone(response.data['confirmed_date'])
        self.assertIsNone(response.data['confirmed_time'])

    def test_buyer_with_no_phone_number(self):
        """Test creating showing when buyer has no phone number"""
        buyer_no_phone = Buyer.objects.create_user(
            username='nophone',
            email='nophone@example.com',
            password='Pass123!'
            # No phone_number
        )
        
        self.client.force_authenticate(user=buyer_no_phone)
        
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'morning'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['buyer']['phone_number'])

    def test_listing_with_no_photos(self):
        """Test viewing listing detail when listing has no photos"""
        url = f'/api/v1/buyer/agent-listings/{self.listing.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['photos']), 0)
        self.assertIsInstance(response.data['photos'], list)

    def test_listing_with_no_documents(self):
        """Test viewing listing detail when listing has no documents"""
        url = f'/api/v1/buyer/agent-listings/{self.listing.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['documents']), 0)
        self.assertIsInstance(response.data['documents'], list)

    def test_max_integer_listing_id(self):
        """Test with maximum integer value as listing ID"""
        self.client.force_authenticate(user=self.buyer)
        
        data = {
            'property_listing_id': 2147483647,  # Max 32-bit int
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'afternoon'
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_rapid_showing_creation(self):
        """Test creating multiple showings rapidly"""
        self.client.force_authenticate(user=self.buyer)
        
        base_date = date.today() + timedelta(days=1)
        
        # Create 10 showings rapidly
        for i in range(10):
            data = {
                'property_listing_id': self.listing.id,
                'requested_date': (base_date + timedelta(days=i)).isoformat(),
                'preferred_time': 'afternoon'
            }
            response = self.client.post(self.showing_create_url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify all created
        count = ShowingSchedule.objects.filter(buyer=self.buyer).count()
        self.assertEqual(count, 10)

    def test_unicode_in_additional_notes(self):
        """Test additional notes with various Unicode characters"""
        self.client.force_authenticate(user=self.buyer)
        
        unicode_notes = "你好 مرحبا Привет 🏠 Ñoño café résumé"
        data = {
            'property_listing_id': self.listing.id,
            'requested_date': (date.today() + timedelta(days=1)).isoformat(),
            'preferred_time': 'morning',
            'additional_notes': unicode_notes
        }
        
        response = self.client.post(self.showing_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['additional_notes'], unicode_notes)
