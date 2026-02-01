import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create or update the single editor user from environment variables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Do not prompt for input; use env vars only.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get("EDITOR_USERNAME", "admin")
        password = os.environ.get("EDITOR_PASSWORD", "changeme")
        email = os.environ.get("EDITOR_EMAIL", "admin@example.com")

        if not password or password == "changeme":
            self.stdout.write(
                self.style.WARNING(
                    "EDITOR_PASSWORD not set or still 'changeme'; skipping user creation."
                )
            )
            return

        user, created = User.objects.update_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user '{username}'."))
        else:
            if os.environ.get("EDITOR_PASSWORD"):
                user.set_password(password)
                user.save()
            self.stdout.write(self.style.SUCCESS(f"User '{username}' already exists."))
