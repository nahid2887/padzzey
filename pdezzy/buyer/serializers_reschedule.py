"""
Serializers for rescheduling showing schedules
"""
from rest_framework import serializers
from datetime import date
from .models import ShowingSchedule


class BuyerRescheduleShowingSerializer(serializers.Serializer):
    """Serializer for buyer to reschedule a showing"""
    preferred_date = serializers.DateField(required=True, help_text="New preferred date for showing")
    preferred_time = serializers.ChoiceField(
        choices=ShowingSchedule.PREFERRED_TIME_CHOICES,
        required=True,
        help_text="New preferred time slot"
    )
    additional_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Optional notes about rescheduling"
    )
    
    def validate_preferred_date(self, value):
        """Ensure date is in the future"""
        if value < date.today():
            raise serializers.ValidationError("Cannot reschedule to a past date")
        return value
    
    def validate(self, attrs):
        """Additional validation"""
        showing = self.context.get('showing')
        
        if not showing:
            raise serializers.ValidationError("Showing schedule not found")
        
        # Check if showing can be rescheduled
        if showing.status == 'completed':
            raise serializers.ValidationError("Cannot reschedule a completed showing")
        
        if showing.status == 'cancelled':
            raise serializers.ValidationError("Cannot reschedule a cancelled showing")
        
        return attrs


class AgentRescheduleShowingSerializer(serializers.Serializer):
    """Serializer for agent to reschedule a showing"""
    confirmed_date = serializers.DateField(required=True, help_text="New confirmed date for showing")
    confirmed_time = serializers.TimeField(required=True, help_text="New confirmed time for showing")
    agent_response = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Optional notes about rescheduling"
    )
    
    def validate_confirmed_date(self, value):
        """Ensure date is in the future"""
        if value < date.today():
            raise serializers.ValidationError("Cannot reschedule to a past date")
        return value
    
    def validate(self, attrs):
        """Additional validation"""
        showing = self.context.get('showing')
        
        if not showing:
            raise serializers.ValidationError("Showing schedule not found")
        
        # Check if showing can be rescheduled
        if showing.status == 'completed':
            raise serializers.ValidationError("Cannot reschedule a completed showing")
        
        if showing.status == 'cancelled':
            raise serializers.ValidationError("Cannot reschedule a cancelled showing")
        
        # Agent must own the property listing
        agent = self.context.get('agent')
        if showing.property_listing.agent != agent:
            raise serializers.ValidationError("You can only reschedule showings for your own listings")
        
        return attrs
