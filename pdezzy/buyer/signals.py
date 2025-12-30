"""
Signals for buyer app
Automatically create notifications for agent when showing schedules are created
and for buyer when agent responds
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import ShowingSchedule, BuyerNotification


@receiver(post_save, sender=ShowingSchedule)
def create_showing_notification(sender, instance, created, **kwargs):
    """
    Create agent notification when a new showing schedule is requested by buyer
    Create buyer notification when agent creates a showing schedule
    """
    if created:
        # Check if showing was created by agent (status is 'accepted' on creation)
        if instance.status == 'accepted' and instance.confirmed_date and instance.confirmed_time:
            # Agent created this showing - notify buyer
            from .models import BuyerNotification
            
            buyer = instance.buyer
            agent = instance.property_listing.agent
            listing = instance.property_listing
            
            BuyerNotification.objects.create(
                buyer=buyer,
                showing_schedule=instance,
                notification_type='showing_accepted',
                title='Showing Scheduled by Agent ✓',
                message=f'{agent.get_full_name() or agent.username} has scheduled a showing for {listing.title} on {instance.confirmed_date.strftime("%B %d, %Y")} at {instance.confirmed_time.strftime("%I:%M %p")}. Please upload your signature to complete the showing agreement.',
                action_url=f'/api/v1/buyer/showings/{instance.id}/sign-agreement/',
                action_text='Sign Agreement'
            )
        else:
            # Buyer created this showing - notify agent
            from seller.models import AgentNotification
            
            agent = instance.property_listing.agent
            buyer = instance.buyer
            listing = instance.property_listing
            
            AgentNotification.objects.create(
                agent=agent,
                notification_type='showing_requested',
                showing_schedule=instance,
                title='New Showing Request',
                message=f'{buyer.get_full_name() or buyer.username} has requested a showing for {listing.title} on {instance.requested_date.strftime("%B %d, %Y")} ({instance.get_preferred_time_display()}).',
                action_url=f'/api/v1/agent/showings/{instance.id}/',
                action_text='View Request'
            )


# Track previous status to detect changes
_showing_schedule_previous_status = {}


@receiver(pre_save, sender=ShowingSchedule)
def track_showing_status_change(sender, instance, **kwargs):
    """Track previous status before save"""
    if instance.pk:
        try:
            old_instance = ShowingSchedule.objects.get(pk=instance.pk)
            _showing_schedule_previous_status[instance.pk] = old_instance.status
        except ShowingSchedule.DoesNotExist:
            pass


@receiver(post_save, sender=ShowingSchedule)
def notify_buyer_on_agent_response(sender, instance, created, **kwargs):
    """
    Create buyer notification when agent accepts or declines showing
    Also notify when showings are rescheduled by either party
    """
    # Check for reschedule by buyer -> notify agent
    if hasattr(instance, '_is_rescheduled_by') and instance._is_rescheduled_by == 'buyer':
        from seller.models import AgentNotification
        
        agent = instance.property_listing.agent
        buyer = instance.buyer
        listing = instance.property_listing
        old_date = getattr(instance, '_old_date', None)
        old_time = getattr(instance, '_old_time', None)
        
        message = f'{buyer.get_full_name() or buyer.username} has requested to reschedule the showing for {listing.title}. '
        if old_date and old_time:
            message += f'Original: {old_date.strftime("%B %d, %Y")} ({old_time}). '
        message += f'New request: {instance.requested_date.strftime("%B %d, %Y")} ({instance.get_preferred_time_display()}).'
        
        AgentNotification.objects.create(
            agent=agent,
            notification_type='showing_requested',
            showing_schedule=instance,
            title='Showing Reschedule Request',
            message=message,
            action_url=f'/api/v1/agent/showings/{instance.id}/',
            action_text='Review Request'
        )
        return
    
    # Check for reschedule by agent -> notify buyer
    if hasattr(instance, '_is_rescheduled_by') and instance._is_rescheduled_by == 'agent':
        agent = instance.property_listing.agent
        buyer = instance.buyer
        listing = instance.property_listing
        old_date = getattr(instance, '_old_date', None)
        old_time = getattr(instance, '_old_time', None)
        
        message = f'{agent.get_full_name() or agent.username} has rescheduled your showing for {listing.title}. '
        if old_date and old_time:
            message += f'Original: {old_date.strftime("%B %d, %Y")} at {old_time.strftime("%I:%M %p")}. '
        message += f'New time: {instance.confirmed_date.strftime("%B %d, %Y")} at {instance.confirmed_time.strftime("%I:%M %p")}.'
        
        BuyerNotification.objects.create(
            buyer=buyer,
            showing_schedule=instance,
            notification_type='showing_accepted',
            title='Showing Rescheduled by Agent',
            message=message,
            action_url=f'/api/v1/buyer/showings/{instance.id}/',
            action_text='View Details'
        )
        return
    
    # Original logic: status change notifications
    if not created and instance.pk in _showing_schedule_previous_status:
        old_status = _showing_schedule_previous_status[instance.pk]
        new_status = instance.status
        
        # Check if status changed to accepted or declined
        if old_status == 'pending' and new_status in ['accepted', 'declined']:
            buyer = instance.buyer
            agent = instance.property_listing.agent
            listing = instance.property_listing
            
            if new_status == 'accepted':
                notification_type = 'showing_accepted'
                title = 'Showing Request Accepted! ✓'
                message = f'{agent.get_full_name() or agent.username} has accepted your showing request for {listing.title}. '
                
                # Only add confirmed date/time if they exist
                if instance.confirmed_date and instance.confirmed_time:
                    message += f'Confirmed for {instance.confirmed_date.strftime("%B %d, %Y")} at {instance.confirmed_time.strftime("%I:%M %p")}. '
                else:
                    message += 'Please coordinate the showing time with the agent. '
                
                message += 'Please upload your signature to complete the showing agreement.'
                action_url = f'/api/v1/buyer/showings/{instance.id}/sign-agreement/'
                action_text = 'Sign Agreement'
            else:  # declined
                notification_type = 'showing_declined'
                title = 'Showing Request Declined'
                message = f'{agent.get_full_name() or agent.username} has declined your showing request for {listing.title}.'
                if instance.agent_response:
                    message += f' Reason: {instance.agent_response}'
                action_url = f'/api/v1/buyer/showings/{instance.id}/'
                action_text = 'View Details'
            
            BuyerNotification.objects.create(
                buyer=buyer,
                showing_schedule=instance,
                notification_type=notification_type,
                title=title,
                message=message,
                action_url=action_url,
                action_text=action_text
            )
            
            # Also create agent notification for the showing status change
            agent_notification_type = 'showing_accepted' if new_status == 'accepted' else 'showing_declined'
            if new_status == 'accepted':
                agent_title = f'Showing Accepted - {buyer.get_full_name() or buyer.username}'
                agent_message = f'{buyer.get_full_name() or buyer.username} has accepted the showing request for {listing.title}.'
                if instance.confirmed_date and instance.confirmed_time:
                    agent_message += f' Confirmed for {instance.confirmed_date.strftime("%B %d, %Y")} at {instance.confirmed_time.strftime("%I:%M %p")}.'
            else:  # declined
                agent_title = f'Showing Declined - {buyer.get_full_name() or buyer.username}'
                agent_message = f'{buyer.get_full_name() or buyer.username} has declined the showing request for {listing.title}.'
            
            from seller.models import AgentNotification
            AgentNotification.objects.create(
                agent=agent,
                showing_schedule=instance,
                notification_type=agent_notification_type,
                title=agent_title,
                message=agent_message,
                action_url=f'/api/v1/agent/showings/{instance.id}/',
                action_text='View Showing'
            )
        
        # Clean up tracking
        del _showing_schedule_previous_status[instance.pk]
