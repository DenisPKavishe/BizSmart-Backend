from django.core.management.base import BaseCommand
from core.email_service import EmailService
from core.models import User

class Command(BaseCommand):
    help = 'Test email sending'
    
    def handle(self, *args, **options):
        user = User.objects.first()
        if user:
            EmailService.send_welcome_email(user, "TestPassword123")
            self.stdout.write(self.style.SUCCESS(f'Test email sent to {user.email}'))
        else:
            self.stdout.write(self.style.ERROR('No user found'))