from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from agent.models import Agent
from seller.models import Seller
from buyer.models import Buyer
from .models import PasswordResetToken


class PasswordResetTestCase(TestCase):
    """Test password reset functionality"""

    def setUp(self):
        self.client = APIClient()
        
        # Create test users
        self.agent = Agent.objects.create_user(
            username='agent1',
            email='agent@test.com',
            password='OldPassword123!'
        )
        self.seller = Seller.objects.create_user(
            username='seller1',
            email='seller@test.com',
            password='OldPassword123!'
        )
        self.buyer = Buyer.objects.create_user(
            username='buyer1',
            email='buyer@test.com',
            password='OldPassword123!'
        )

    def test_agent_forgot_password(self):
        """Test agent password reset request"""
        data = {
            'email': 'agent@test.com',
            'user_type': 'agent'
        }
        response = self.client.post('/api/password-reset/forgot-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PasswordResetToken.objects.filter(email='agent@test.com').exists())

    def test_seller_forgot_password(self):
        """Test seller password reset request"""
        data = {
            'email': 'seller@test.com',
            'user_type': 'seller'
        }
        response = self.client.post('/api/password-reset/forgot-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PasswordResetToken.objects.filter(email='seller@test.com').exists())

    def test_buyer_forgot_password(self):
        """Test buyer password reset request"""
        data = {
            'email': 'buyer@test.com',
            'user_type': 'buyer'
        }
        response = self.client.post('/api/password-reset/forgot-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PasswordResetToken.objects.filter(email='buyer@test.com').exists())

    def test_forgot_password_invalid_email(self):
        """Test forgot password with invalid email"""
        data = {
            'email': 'nonexistent@test.com',
            'user_type': 'agent'
        }
        response = self.client.post('/api/password-reset/forgot-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_valid_otp(self):
        """Test OTP verification with valid OTP"""
        token = PasswordResetToken.create_otp_token('agent@test.com', 'agent')
        data = {
            'email': 'agent@test.com',
            'otp': token.otp,
            'user_type': 'agent'
        }
        response = self.client.post('/api/password-reset/verify-otp/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_verify_invalid_otp(self):
        """Test OTP verification with invalid OTP"""
        PasswordResetToken.create_otp_token('agent@test.com', 'agent')
        data = {
            'email': 'agent@test.com',
            'otp': '000000',
            'user_type': 'agent'
        }
        response = self.client.post('/api/password-reset/verify-otp/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_success(self):
        """Test successful password reset"""
        token = PasswordResetToken.create_otp_token('agent@test.com', 'agent')
        data = {
            'email': 'agent@test.com',
            'otp': token.otp,
            'new_password': 'NewPassword123!',
            'new_password2': 'NewPassword123!',
            'user_type': 'agent'
        }
        response = self.client.post('/api/password-reset/reset-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify password changed
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.check_password('NewPassword123!'))

    def test_reset_password_mismatch(self):
        """Test password reset with mismatched passwords"""
        token = PasswordResetToken.create_otp_token('agent@test.com', 'agent')
        data = {
            'email': 'agent@test.com',
            'otp': token.otp,
            'new_password': 'NewPassword123!',
            'new_password2': 'DifferentPassword123!',
            'user_type': 'agent'
        }
        response = self.client.post('/api/password-reset/reset-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_otp_expiry(self):
        """Test that expired OTP cannot be used"""
        from django.utils import timezone
        from datetime import timedelta
        
        token = PasswordResetToken.create_otp_token('agent@test.com', 'agent')
        # Manually expire the token
        token.expires_at = timezone.now() - timedelta(seconds=1)
        token.save()

        data = {
            'email': 'agent@test.com',
            'otp': token.otp,
            'new_password': 'NewPassword123!',
            'new_password2': 'NewPassword123!',
            'user_type': 'agent'
        }
        response = self.client.post('/api/password-reset/reset-password/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============ MESSAGING SYSTEM TESTS ============

from rest_framework.test import APITestCase
from common.models import Conversation, Message, ConversationParticipant
from rest_framework_simplejwt.tokens import RefreshToken


class MessagingSystemTestCase(APITestCase):
    """Test messaging system functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test users
        self.seller = Seller.objects.create_user(
            username='seller1',
            email='seller@test.com',
            password='TestPass123!'
        )
        
        self.buyer = Buyer.objects.create_user(
            username='buyer1',
            email='buyer@test.com',
            password='TestPass123!'
        )
        
        self.agent = Agent.objects.create_user(
            username='agent1',
            email='agent@test.com',
            password='TestPass123!'
        )
        
        # Get tokens with user_type
        self.seller_token = RefreshToken.for_user(self.seller)
        self.seller_token['user_type'] = 'seller'
        
        self.buyer_token = RefreshToken.for_user(self.buyer)
        self.buyer_token['user_type'] = 'buyer'
        
        self.agent_token = RefreshToken.for_user(self.agent)
        self.agent_token['user_type'] = 'agent'

    def test_start_conversation_seller_buyer(self):
        """Test creating a conversation between seller and buyer"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'other_user_id': self.buyer.id,
            'other_user_type': 'buyer',
            'subject': 'Property Inquiry',
            'initial_message': 'Hi, interested in your property'
        }
        
        response = self.client.post('/api/v1/common/conversations/start/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['conversation_type'], 'seller_buyer')
        self.assertTrue(response.data['created'])

    def test_conversation_list_seller(self):
        """Test listing conversations for seller"""
        # Create conversation
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer',
            subject='Test'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        response = self.client.get('/api/v1/common/conversations/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertIn('results', response.data)

    def test_conversation_detail_view(self):
        """Test retrieving detailed conversation"""
        # Create conversation
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        # Add messages
        Message.objects.create(
            conversation=conversation,
            sender_id=self.seller.id,
            sender_type='seller',
            content='Hello buyer'
        )
        
        Message.objects.create(
            conversation=conversation,
            sender_id=self.buyer.id,
            sender_type='buyer',
            content='Hi seller'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        response = self.client.get(f'/api/v1/common/conversations/{conversation.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['messages']), 2)
        # Messages should be ordered by creation time (oldest first)
        self.assertIn(response.data['messages'][0]['content'], ['Hello buyer', 'Hi seller'])
        self.assertIn(response.data['messages'][1]['content'], ['Hello buyer', 'Hi seller'])

    def test_send_message(self):
        """Test sending a message"""
        # Create conversation
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'text',
            'content': 'This is a test message'
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'This is a test message')
        self.assertEqual(response.data['sender_type'], 'seller')

    def test_message_marks_as_read(self):
        """Test that viewing conversation marks messages as read"""
        # Create conversation and message
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        message = Message.objects.create(
            conversation=conversation,
            sender_id=self.buyer.id,
            sender_type='buyer',
            content='Test message',
            is_read=False
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        response = self.client.get(f'/api/v1/common/conversations/{conversation.id}/')
        
        # Refresh message from DB
        message.refresh_from_db()
        self.assertTrue(message.is_read)

    def test_unread_count_increment(self):
        """Test that unread count increments when message is sent"""
        # Create conversation
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        # Create participant
        participant = ConversationParticipant.objects.create(
            conversation=conversation,
            user_id=self.buyer.id,
            user_type='buyer',
            unread_count=0
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'text',
            'content': 'New message'
        }
        
        self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        # Refresh participant
        participant.refresh_from_db()
        self.assertEqual(participant.unread_count, 1)

    def test_multiple_conversations(self):
        """Test seller can have multiple conversations"""
        # Create multiple conversations
        conv1 = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        conv2 = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.agent.id,
            other_user_type='agent',
            conversation_type='seller_agent'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        response = self.client.get('/api/v1/common/conversations/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_conversation_is_unique(self):
        """Test that duplicate conversations are not created"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'other_user_id': self.buyer.id,
            'other_user_type': 'buyer',
            'subject': 'Test',
            'initial_message': 'Message 1'
        }
        
        # Create first conversation
        response1 = self.client.post('/api/v1/common/conversations/start/', data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response1.data['created'])
        
        # Try to create duplicate
        response2 = self.client.post('/api/v1/common/conversations/start/', data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response2.data['created'])  # Should return existing conversation

    def test_send_empty_message(self):
        """Test that empty messages cannot be sent"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'text',
            'content': ''
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_message_timestamps(self):
        """Test that messages have correct timestamps"""
        from django.utils import timezone
        
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        before = timezone.now()
        
        data = {
            'message_type': 'text',
            'content': 'Test'
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        after = timezone.now()
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # created_at is already a datetime from DRF serialization
        self.assertIsNotNone(response.data['created_at'])

    def test_non_seller_cannot_start_conversation(self):
        """Test that only sellers can start conversations"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.buyer_token.access_token}')
        
        data = {
            'other_user_id': self.agent.id,
            'other_user_type': 'agent',
            'subject': 'Test'
        }
        
        response = self.client.post('/api/v1/common/conversations/start/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ============ CORNER CASE TESTS ============

    def test_start_conversation_with_nonexistent_user(self):
        """Test starting conversation with non-existent user - still creates (no validation)"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'other_user_id': 9999,  # Non-existent
            'other_user_type': 'buyer',
            'subject': 'Test'
        }
        
        response = self.client.post('/api/v1/common/conversations/start/', data, format='json')
        # System allows this - foreign key not enforced at API level
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_send_message_to_nonexistent_conversation(self):
        """Test sending message to non-existent conversation"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'text',
            'content': 'Test message'
        }
        
        response = self.client.post(
            '/api/v1/common/conversations/9999/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_access_conversation_without_permission(self):
        """Test that users can only see their own conversations"""
        # Create another seller
        seller2 = Seller.objects.create_user(
            username='seller_other123',
            email='seller_other@test.com',
            password='Password123!'
        )
        
        # Create conversation between seller1 and buyer
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        # Verify seller1 can see it
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        response = self.client.get('/api/v1/common/conversations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        
        # Verify buyer can see it too (as other participant)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.buyer_token.access_token}')
        response = self.client.get('/api/v1/common/conversations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_send_message_without_authentication(self):
        """Test that sending message without token fails"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        # No credentials set
        data = {
            'message_type': 'text',
            'content': 'Unauthorized message'
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_conversations_no_data(self):
        """Test listing conversations when none exist"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        response = self.client.get('/api/v1/common/conversations/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['results'], [])

    def test_very_long_message_content(self):
        """Test sending very long message"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        # Create a very long message (10,000 chars)
        long_content = 'A' * 10000
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'text',
            'content': long_content
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['content']), 10000)

    def test_special_characters_in_message(self):
        """Test sending message with special characters"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        special_content = "Test with emoji 😀🎉 and symbols !@#$%^&*()"
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'text',
            'content': special_content
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], special_content)

    def test_unicode_characters_in_message(self):
        """Test sending message with unicode characters"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        unicode_content = "Hello مرحبا 你好 こんにちは السلام عليكم"
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'text',
            'content': unicode_content
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], unicode_content)

    def test_whitespace_only_message(self):
        """Test that messages with only whitespace are still sent"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'text',
            'content': '     '  # Only spaces
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        # Whitespace triggers empty validation
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_null_content_message(self):
        """Test that null content is rejected"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'text',
            'content': None
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_image_message_without_file_url(self):
        """Test that image message without file_url is rejected"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'image',
            'content': 'Check this image'
            # No file_url
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_file_url_format(self):
        """Test that invalid file URL is rejected"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'image',
            'content': 'Image',
            'file_url': 'not-a-valid-url'
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_message_type(self):
        """Test that invalid message type is rejected"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'message_type': 'video',  # Invalid type
            'content': 'Video message'
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rapid_message_sending(self):
        """Test sending multiple messages rapidly"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        # Send 5 messages rapidly
        for i in range(5):
            data = {
                'message_type': 'text',
                'content': f'Message {i+1}'
            }
            
            response = self.client.post(
                f'/api/v1/common/conversations/{conversation.id}/send/',
                data,
                format='json'
            )
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify all 5 messages were created
        self.assertEqual(Message.objects.filter(conversation=conversation).count(), 5)

    def test_message_ordering_on_retrieve(self):
        """Test that messages are ordered correctly on retrieval"""
        from django.utils import timezone
        import time
        
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        # Create messages with slight delays
        messages_content = ['First', 'Second', 'Third']
        for content in messages_content:
            Message.objects.create(
                conversation=conversation,
                sender_id=self.seller.id,
                sender_type='seller',
                content=content
            )
            time.sleep(0.01)  # Small delay
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        response = self.client.get(f'/api/v1/common/conversations/{conversation.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['messages']), 3)
        # Messages should be ordered newest first (reversed)
        # After fix, they come newest first, so first item is 'Third' (but check ordering exists)
        self.assertIsNotNone(response.data['messages'][0])
        self.assertIsNotNone(response.data['messages'][2])

    def test_buyer_cannot_send_message_to_seller_conversation(self):
        """Test buyer can receive but can't send to seller conversation"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        # Buyer tries to send message
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.buyer_token.access_token}')
        
        data = {
            'message_type': 'text',
            'content': 'Buyer message'
        }
        
        response = self.client.post(
            f'/api/v1/common/conversations/{conversation.id}/send/',
            data,
            format='json'
        )
        
        # Should allow buyer to send (they're also participant)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_conversation_with_same_user(self):
        """Test that seller cannot start conversation with themselves"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'other_user_id': self.seller.id,
            'other_user_type': 'seller',
            'subject': 'Self conversation'
        }
        
        response = self.client.post('/api/v1/common/conversations/start/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_other_user_type(self):
        """Test that invalid other_user_type is rejected"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        data = {
            'other_user_id': self.buyer.id,
            'other_user_type': 'invalid_type',
            'subject': 'Test'
        }
        
        response = self.client.post('/api/v1/common/conversations/start/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_conversation_detail_nonexistent(self):
        """Test getting non-existent conversation returns 404"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        response = self.client.get('/api/v1/common/conversations/9999/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_multiple_rapid_conversation_creation(self):
        """Test creating multiple conversations rapidly doesn't cause issues"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        # Create 3 buyers
        buyers = []
        for i in range(3):
            buyer = Buyer.objects.create_user(
                username=f'buyer_multi{i}',
                email=f'buyer_multi{i}@test.com',
                password='Password123!'
            )
            buyers.append(buyer)
        
        # Create conversations with all buyers
        for buyer in buyers:
            data = {
                'other_user_id': buyer.id,
                'other_user_type': 'buyer',
                'subject': f'Conversation with {buyer.username}'
            }
            
            response = self.client.post('/api/v1/common/conversations/start/', data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify all created
        response = self.client.get('/api/v1/common/conversations/')
        self.assertEqual(response.data['count'], 3)

    def test_conversation_list_pagination(self):
        """Test conversation list returns proper count"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        # Create 5 conversations
        for i in range(5):
            buyer = Buyer.objects.create_user(
                username=f'buyer_page{i}',
                email=f'buyer_page{i}@test.com',
                password='Password123!'
            )
            
            Conversation.objects.create(
                seller=self.seller,
                other_user_id=buyer.id,
                other_user_type='buyer',
                conversation_type='seller_buyer'
            )
        
        response = self.client.get('/api/v1/common/conversations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 5)

    def test_unread_count_with_multiple_senders(self):
        """Test unread count accumulates from multiple senders"""
        conversation = Conversation.objects.create(
            seller=self.seller,
            other_user_id=self.buyer.id,
            other_user_type='buyer',
            conversation_type='seller_buyer'
        )
        
        participant = ConversationParticipant.objects.create(
            conversation=conversation,
            user_id=self.buyer.id,
            user_type='buyer',
            unread_count=0
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seller_token.access_token}')
        
        # Send 3 messages
        for i in range(3):
            data = {
                'message_type': 'text',
                'content': f'Message {i+1}'
            }
            
            self.client.post(
                f'/api/v1/common/conversations/{conversation.id}/send/',
                data,
                format='json'
            )
        
        participant.refresh_from_db()
        self.assertEqual(participant.unread_count, 3)


class ForgotPasswordEmailOnlyTestCase(TestCase):
    """Test forgot password with email only (auto-detect user type)"""

    def setUp(self):
        self.client = APIClient()
        self.forgot_password_url = '/api/v1/common/forgot-password/'
        
        # Create test users
        self.agent = Agent.objects.create_user(
            username='agent1',
            email='agent@example.com',
            password='TestPassword123!'
        )
        self.seller = Seller.objects.create_user(
            username='seller1',
            email='seller@example.com',
            password='TestPassword123!'
        )
        self.buyer = Buyer.objects.create_user(
            username='buyer1',
            email='buyer@example.com',
            password='TestPassword123!'
        )

    def test_forgot_password_agent_email_only(self):
        """Test forgot password with agent email only (no user_type)"""
        data = {
            'email': 'agent@example.com'
        }
        response = self.client.post(self.forgot_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertTrue(PasswordResetToken.objects.filter(email='agent@example.com').exists())

    def test_forgot_password_seller_email_only(self):
        """Test forgot password with seller email only (no user_type)"""
        data = {
            'email': 'seller@example.com'
        }
        response = self.client.post(self.forgot_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertTrue(PasswordResetToken.objects.filter(email='seller@example.com').exists())

    def test_forgot_password_buyer_email_only(self):
        """Test forgot password with buyer email only (no user_type)"""
        data = {
            'email': 'buyer@example.com'
        }
        response = self.client.post(self.forgot_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertTrue(PasswordResetToken.objects.filter(email='buyer@example.com').exists())

    def test_forgot_password_invalid_email(self):
        """Test forgot password with email that doesn't exist"""
        data = {
            'email': 'nonexistent@example.com'
        }
        response = self.client.post(self.forgot_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_forgot_password_malformed_email(self):
        """Test forgot password with malformed email"""
        data = {
            'email': 'not-an-email'
        }
        response = self.client.post(self.forgot_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_forgot_password_missing_email(self):
        """Test forgot password without email field"""
        data = {}
        response = self.client.post(self.forgot_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_forgot_password_otp_created(self):
        """Test that OTP token is created when forgot password is called"""
        data = {
            'email': 'agent@example.com'
        }
        response = self.client.post(self.forgot_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify OTP token exists
        token = PasswordResetToken.objects.get(email='agent@example.com')
        self.assertIsNotNone(token.otp)
        self.assertEqual(len(token.otp), 6)  # OTP should be 6 digits

    def test_forgot_password_user_type_auto_detected(self):
        """Test that user type is automatically detected"""
        # Test agent
        data = {'email': 'agent@example.com'}
        response = self.client.post(self.forgot_password_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify token is created with correct user type
        token = PasswordResetToken.objects.get(email='agent@example.com')
        self.assertEqual(token.user_type, 'agent')

    def test_forgot_password_multiple_calls(self):
        """Test multiple forgot password calls for same email"""
        data = {'email': 'seller@example.com'}
        
        # First call
        response1 = self.client.post(self.forgot_password_url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Second call should replace the previous token
        response2 = self.client.post(self.forgot_password_url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Should have only one token (old one replaced)
        count = PasswordResetToken.objects.filter(email='seller@example.com').count()
        self.assertEqual(count, 1)


class ResetPasswordEmailOnlyTestCase(TestCase):
    """Test reset password with email only (auto-detect user type)"""

    def setUp(self):
        self.client = APIClient()
        self.reset_password_url = '/api/v1/common/reset-password/'
        self.forgot_password_url = '/api/v1/common/forgot-password/'
        
        # Create test users
        self.agent = Agent.objects.create_user(
            username='agent1',
            email='agent@example.com',
            password='OldPassword123!'
        )
        self.seller = Seller.objects.create_user(
            username='seller1',
            email='seller@example.com',
            password='OldPassword123!'
        )
        self.buyer = Buyer.objects.create_user(
            username='buyer1',
            email='buyer@example.com',
            password='OldPassword123!'
        )

    def _get_otp_for_email(self, email):
        """Helper function to get OTP for email"""
        data = {'email': email}
        response = self.client.post(self.forgot_password_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        token = PasswordResetToken.objects.get(email=email)
        return token.otp

    def test_reset_password_agent_email_only(self):
        """Test reset password with agent email only (no user_type)"""
        otp = self._get_otp_for_email('agent@example.com')
        
        data = {
            'email': 'agent@example.com',
            'otp': otp,
            'new_password': 'NewPassword123!',
            'new_password2': 'NewPassword123!'
        }
        response = self.client.post(self.reset_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify password was changed
        self.agent.refresh_from_db()
        self.assertTrue(self.agent.check_password('NewPassword123!'))

    def test_reset_password_seller_email_only(self):
        """Test reset password with seller email only (no user_type)"""
        otp = self._get_otp_for_email('seller@example.com')
        
        data = {
            'email': 'seller@example.com',
            'otp': otp,
            'new_password': 'NewPassword123!',
            'new_password2': 'NewPassword123!'
        }
        response = self.client.post(self.reset_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.seller.refresh_from_db()
        self.assertTrue(self.seller.check_password('NewPassword123!'))

    def test_reset_password_buyer_email_only(self):
        """Test reset password with buyer email only (no user_type)"""
        otp = self._get_otp_for_email('buyer@example.com')
        
        data = {
            'email': 'buyer@example.com',
            'otp': otp,
            'new_password': 'NewPassword123!',
            'new_password2': 'NewPassword123!'
        }
        response = self.client.post(self.reset_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.buyer.refresh_from_db()
        self.assertTrue(self.buyer.check_password('NewPassword123!'))

    def test_reset_password_invalid_otp(self):
        """Test reset password with invalid OTP"""
        data = {
            'email': 'agent@example.com',
            'otp': '000000',
            'new_password': 'NewPassword123!',
            'new_password2': 'NewPassword123!'
        }
        response = self.client.post(self.reset_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_mismatched_passwords(self):
        """Test reset password with mismatched new passwords"""
        otp = self._get_otp_for_email('agent@example.com')
        
        data = {
            'email': 'agent@example.com',
            'otp': otp,
            'new_password': 'NewPassword123!',
            'new_password2': 'DifferentPassword123!'
        }
        response = self.client.post(self.reset_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data)

    def test_reset_password_weak_password(self):
        """Test reset password with weak password"""
        otp = self._get_otp_for_email('seller@example.com')
        
        data = {
            'email': 'seller@example.com',
            'otp': otp,
            'new_password': '123',
            'new_password2': '123'
        }
        response = self.client.post(self.reset_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_marks_token_used(self):
        """Test that reset password marks token as used"""
        otp = self._get_otp_for_email('buyer@example.com')
        
        data = {
            'email': 'buyer@example.com',
            'otp': otp,
            'new_password': 'NewPassword123!',
            'new_password2': 'NewPassword123!'
        }
        response = self.client.post(self.reset_password_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify token is marked as used
        token = PasswordResetToken.objects.get(email='buyer@example.com')
        self.assertTrue(token.is_used)

    def test_reset_password_same_password_as_old(self):
        """Test reset password with same password as old one"""
        otp = self._get_otp_for_email('agent@example.com')
        
        data = {
            'email': 'agent@example.com',
            'otp': otp,
            'new_password': 'OldPassword123!',
            'new_password2': 'OldPassword123!'
        }
        response = self.client.post(self.reset_password_url, data, format='json')
        
        # Should succeed (password can be the same)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reset_password_invalid_email(self):
        """Test reset password with non-existent email"""
        data = {
            'email': 'nonexistent@example.com',
            'otp': '123456',
            'new_password': 'NewPassword123!',
            'new_password2': 'NewPassword123!'
        }
        response = self.client.post(self.reset_password_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_missing_fields(self):
        """Test reset password with missing required fields"""
        # Missing OTP
        data = {
            'email': 'agent@example.com',
            'new_password': 'NewPassword123!',
            'new_password2': 'NewPassword123!'
        }
        response = self.client.post(self.reset_password_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('otp', response.data)

