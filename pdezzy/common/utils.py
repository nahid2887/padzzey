from django.core.mail import send_mail
from django.conf import settings


def send_otp_email(email, otp, user_type):
    """Send OTP via email"""
    subject = f"Password Reset OTP - {user_type.capitalize()} Account"
    message = f"""
    Hello,

    You requested a password reset for your {user_type.capitalize()} account.
    
    Your verification code is: {otp}
    
    This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.
    
    If you didn't request this, please ignore this email.
    
    Best regards,
    Pdezzy Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


def send_password_reset_confirmation(email, user_type):
    """Send confirmation that password has been reset"""
    subject = f"Password Reset Confirmation - {user_type.capitalize()} Account"
    message = f"""
    Hello,

    Your password for your {user_type.capitalize()} account has been successfully reset.
    
    If you didn't perform this action, please contact support immediately.
    
    Best regards,
    Pdezzy Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False
