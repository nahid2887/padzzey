from django.core.management.base import BaseCommand
from buyer.models import ShowingSchedule, ShowingAgreement
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Create showing agreements for testing'

    def handle(self, *args, **options):
        # Get all showing schedules without agreements
        schedules = ShowingSchedule.objects.filter(agreement__isnull=True)
        
        if not schedules.exists():
            self.stdout.write(self.style.WARNING('No pending schedules found'))
            return
        
        created_count = 0
        for schedule in schedules[:3]:  # Create for first 3 schedules
            try:
                agreement = ShowingAgreement.objects.create(
                    showing_schedule=schedule,
                    buyer=schedule.buyer,
                    agent=schedule.property_listing.agent,
                    duration_type='one_property',
                    property_address=f"{schedule.property_listing.street_address}, {schedule.property_listing.city}",
                    showing_date=schedule.requested_date or datetime.now().date(),
                    agreement_accepted=True,
                    terms_text='This is a test showing agreement',
                    signed_at=datetime.now()
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created showing agreement {agreement.id} for schedule {schedule.id}'
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating agreement for schedule {schedule.id}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} showing agreements'))
