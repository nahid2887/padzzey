"""
Custom WebSocket authentication middleware that extracts JWT token from query parameters
"""
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_string):
    """
    Get user from JWT token string using user_type claim
    """
    try:
        token = AccessToken(token_string)
        user_id = token['user_id']
        user_type = token.get('user_type', None)
        
        # Import here to avoid circular imports
        from agent.models import Agent
        from seller.models import Seller
        from buyer.models import Buyer
        
        logger.info(f"Authenticating user: id={user_id}, type={user_type}")
        
        # Use user_type claim if available for direct lookup
        if user_type == 'buyer':
            try:
                user = Buyer.objects.get(id=user_id)
                logger.info(f"User authenticated: Buyer {user_id}")
                return user
            except Buyer.DoesNotExist:
                logger.error(f"Buyer not found with id {user_id}")
                return None
        elif user_type == 'seller':
            try:
                user = Seller.objects.get(id=user_id)
                logger.info(f"User authenticated: Seller {user_id}")
                return user
            except Seller.DoesNotExist:
                logger.error(f"Seller not found with id {user_id}")
                return None
        elif user_type == 'agent':
            try:
                user = Agent.objects.get(id=user_id)
                logger.info(f"User authenticated: Agent {user_id}")
                return user
            except Agent.DoesNotExist:
                logger.error(f"Agent not found with id {user_id}")
                return None
        else:
            # Fallback: Try all user types if user_type claim is missing
            logger.warning(f"No user_type claim in token, trying all user types")
            
            # Try Agent first
            try:
                user = Agent.objects.get(id=user_id)
                logger.info(f"User authenticated: Agent {user_id}")
                return user
            except Agent.DoesNotExist:
                pass
            
            # Try Seller
            try:
                user = Seller.objects.get(id=user_id)
                logger.info(f"User authenticated: Seller {user_id}")
                return user
            except Seller.DoesNotExist:
                pass
            
            # Try Buyer
            try:
                user = Buyer.objects.get(id=user_id)
                logger.info(f"User authenticated: Buyer {user_id}")
                return user
            except Buyer.DoesNotExist:
                logger.warning(f"No user found with id {user_id}")
                return None
            
    except (InvalidToken, TokenError) as e:
        logger.error(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error authenticating token: {e}")
        return None


class TokenAuthMiddleware(BaseMiddleware):
    """
    Custom middleware that extracts JWT token from query parameters
    and authenticates the user.
    """
    
    async def __call__(self, scope, receive, send):
        # Get the token from query string
        query_string = scope.get('query_string', b'').decode()
        token = None
        
        # Parse query string to extract token
        if 'token=' in query_string:
            for param in query_string.split('&'):
                if param.startswith('token='):
                    token = param.split('=', 1)[1]
                    break
        
        # Authenticate user if token is provided
        if token:
            user = await get_user_from_token(token)
            scope['user'] = user if user else AnonymousUser()
        else:
            logger.warning("No token provided in WebSocket connection")
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
