from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SellingRequest, AgentNotification


@receiver(post_save, sender=SellingRequest)
def create_agent_notification(sender, instance, created, **kwargs):
    """
    Create a notification for the agent when they are assigned to a selling request.
    This handles both new selling requests with an agent and when an agent is assigned later.
    """
    # Only create notification if agent is assigned
    if not instance.agent:
        return
    
    # Create a unique notification for this agent and selling request
    # Check if we should create a notification
    notification_type = 'new_selling_request'
    title = 'New Selling Request Assigned'
    message = f"You have been assigned a new selling request from {instance.seller.get_full_name()} for {instance.contact_name}."
    
    # Check if notification already exists for this selling request and agent
    existing_notification = AgentNotification.objects.filter(
        agent=instance.agent,
        selling_request=instance,
        notification_type=notification_type
    ).exists()
    
    if not existing_notification:
        # Create the notification
        AgentNotification.objects.create(
            agent=instance.agent,
            notification_type=notification_type,
            selling_request=instance,
            title=title,
            message=message,
            action_url=f'/api/v1/agent/selling-requests/{instance.id}/',
            action_text='View Request'
        )

