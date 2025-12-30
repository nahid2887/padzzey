from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from seller.models import Seller
from buyer.models import Buyer
from agent.models import Agent
import logging

logger = logging.getLogger(__name__)


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that loads the correct user model based on user_type claim
    """

    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        Uses the user_type claim to determine which model to query.
        """
        from rest_framework_simplejwt.settings import api_settings
        
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError as e:
            raise InvalidToken(
                "Token contained no recognizable user identification"
            ) from e
        
        user_type = validated_token.get('user_type')
        logger.debug(f"get_user: user_id={user_id}, user_type={user_type}")
        
        try:
            # Determine which model to query based on user_type
            if user_type == 'seller':
                user = Seller.objects.get(id=user_id)
                logger.debug(f"Found Seller: {user.username}")
            elif user_type == 'buyer':
                user = Buyer.objects.get(id=user_id)
                logger.debug(f"Found Buyer: {user.username}")
            elif user_type == 'agent':
                user = Agent.objects.get(id=user_id)
                logger.debug(f"Found Agent: {user.username}")
            else:
                # If no user_type, try the default user model
                logger.debug(f"No user_type found, using default user model")
                user = self.user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except (Seller.DoesNotExist, Buyer.DoesNotExist, Agent.DoesNotExist) as e:
            logger.error(f"User not found: {user_type} with id={user_id}")
            raise AuthenticationFailed('User not found', code='user_not_found') from e
        except self.user_model.DoesNotExist as e:
            logger.error(f"Default user not found with id={user_id}")
            raise AuthenticationFailed('User not found', code='user_not_found') from e
        
        # Check if user is active
        if api_settings.CHECK_USER_IS_ACTIVE and not user.is_active:
            raise AuthenticationFailed('User is inactive', code='user_inactive')
        
        return user

    def authenticate(self, request):
        """
        Authenticate JWT token and load the correct user model
        """
        result = super().authenticate(request)
        return result


