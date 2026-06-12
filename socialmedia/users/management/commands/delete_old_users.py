from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Delete old users and all their associated details/records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--preserve',
            nargs='+',
            default=['admin', 'sakthi_07'],
            help='Usernames to preserve from deletion'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        preserve_list = options['preserve']
        dry_run = options['dry_run']

        self.stdout.write(self.style.WARNING(f"Preserving users: {', '.join(preserve_list)}"))

        # Find users to delete (excluding preserved list and any superusers just in case)
        users_to_delete = User.objects.exclude(username__in=preserve_list).exclude(is_superuser=True)

        if not users_to_delete.exists():
            self.stdout.write(self.style.SUCCESS("No users to delete."))
            return

        self.stdout.write(self.style.WARNING(f"Found {users_to_delete.count()} users to delete:"))
        for u in users_to_delete:
            self.stdout.write(f"  - {u.username} (ID: {u.id}, Email: {u.email or 'None'}, Joined: {u.date_joined})")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("[Dry Run] No database changes were made."))
            return

        # Perform deletion
        total_deleted = 0
        deleted_details = {}
        
        for user in users_to_delete:
            username = user.username
            deleted_count, details = user.delete()
            total_deleted += deleted_count
            
            for key, val in details.items():
                deleted_details[key] = deleted_details.get(key, 0) + val
                
            self.stdout.write(self.style.SUCCESS(f"Deleted user '{username}' and associated records."))

        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {total_deleted} total records across models:"))
        for model_name, count in deleted_details.items():
            self.stdout.write(f"  - {model_name}: {count}")
