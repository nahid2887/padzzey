from django.core.management.base import BaseCommand
from buyer.models import ShowingSchedule
from django.utils import timezone


class Command(BaseCommand):
    help = 'Reset all showing schedules to pending status for testing'

    def handle(self, *args, **options):
        # Reset all showings to pending status
        updated_count = ShowingSchedule.objects.all().update(
            status='pending',
            agent_response='',
            responded_at=None,
            confirmed_date=None,
            confirmed_time=None
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully reset {updated_count} showing schedules to pending status'
            )
        )
