from django.core.management.base import BaseCommand
from django.apps import apps
from django.contrib.auth.models import User # Keep User
from users.models import UserProfile # Keep UserProfile

# List of models to KEEP (their data will not be deleted)
MODELS_TO_KEEP = [
    User,
    UserProfile,
    # Add any other critical models you want to preserve, e.g.,
    # from django.contrib.admin.models import LogEntry # If you want to keep admin logs
    # from django.contrib.contenttypes.models import ContentType # Usually keep
    # from django.contrib.sessions.models import Session # Usually keep for active sessions
]

class Command(BaseCommand):
    help = 'Deletes most application data but keeps Users, UserProfiles, and other specified models. USE WITH CAUTION IN DEV ONLY.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_false',
            dest='interactive',
            help='Tells Django to NOT prompt the user for input of any kind.',
        )

    def handle(self, *args, **options):
        interactive = options['interactive']
        models_to_keep_str = [f"{m._meta.app_label}.{m._meta.model_name}" for m in MODELS_TO_KEEP]

        if interactive:
            self.stdout.write(self.style.WARNING(
                "\nThis command will delete data from MOST of your application's tables, but will attempt to keep:"
            ))
            for model_name in models_to_keep_str:
                self.stdout.write(self.style.WARNING(f" - {model_name}"))
            
            confirm = input(
                "\nAre you sure you want to proceed? This action CANNOT be undone. "
                "Type 'yes' to continue, or anything else to cancel: "
            )
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR("Operation cancelled by user."))
                return

        self.stdout.write(self.style.NOTICE("Starting data deletion..."))

        # Get all installed models
        all_models = apps.get_models()
        
        # We need to delete in an order that respects ForeignKey constraints.
        # This is a simplified approach. For complex relationships, you might need a more
        # sophisticated topological sort or handle IntegrityError.
        # A common strategy is to delete models that are "pointed to" last.
        # Or, iterate multiple times.

        # For simplicity, we'll iterate a few times. This often works for basic cases.
        # For a robust solution, a proper dependency graph traversal is needed.
        
        # Store models that couldn't be deleted due to IntegrityError to retry
        deferred_models = [] 

        for model in all_models:
            model_identifier = f"{model._meta.app_label}.{model._meta.model_name}"
            if model in MODELS_TO_KEEP or model_identifier in models_to_keep_str:
                self.stdout.write(self.style.SUCCESS(f"Skipping {model_identifier}..."))
                continue

            # Skip Django's internal models that are often dependencies or part of auth/admin setup
            # ContentType and Session are often good to keep, but can be cleared if desired.
            if model._meta.app_label in ['admin', 'contenttypes', 'sessions', 'auth'] and \
               model_identifier not in models_to_keep_str: # Unless explicitly in MODELS_TO_KEEP
                # For auth, only User is kept by default in MODELS_TO_KEEP.
                # Group and Permission might be cleared if not careful.
                # If you want to keep all auth models:
                # if model._meta.app_label == 'auth' and model != User: continue
                if model._meta.model_name in ['permission', 'group', 'logentry', 'contenttype', 'session']: # More specific skip
                     self.stdout.write(self.style.SUCCESS(f"Skipping Django internal model {model_identifier}..."))
                     continue


            try:
                count, _ = model.objects.all().delete()
                if count > 0:
                    self.stdout.write(self.style.SUCCESS(f"Deleted {count} objects from {model_identifier}"))
                else:
                    self.stdout.write(f"No objects to delete from {model_identifier}")
            except Exception as e: # Catch broader exceptions like IntegrityError
                self.stdout.write(self.style.WARNING(f"Could not delete from {model_identifier} in the first pass (possibly due to FK constraints: {e}). Deferring..."))
                deferred_models.append(model)
        
        # Retry deferred models (simple retry, might need more passes for complex schemas)
        if deferred_models:
            self.stdout.write(self.style.NOTICE("\nRetrying deferred models..."))
            retried_deferred = []
            for model in deferred_models:
                model_identifier = f"{model._meta.app_label}.{model._meta.model_name}"
                try:
                    count, _ = model.objects.all().delete()
                    if count > 0:
                        self.stdout.write(self.style.SUCCESS(f"Deleted {count} objects from {model_identifier} on retry"))
                    else:
                         self.stdout.write(f"No objects to delete from {model_identifier} on retry")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to delete from {model_identifier} even on retry: {e}"))
                    retried_deferred.append(model) # Add to list of models that still couldn't be deleted
            deferred_models = retried_deferred


        if deferred_models:
            self.stdout.write(self.style.ERROR("\nSome models could not be fully cleared due to persistent ForeignKey constraints:"))
            for model in deferred_models:
                self.stdout.write(self.style.ERROR(f" - {model._meta.app_label}.{model._meta.model_name}"))
            self.stdout.write(self.style.WARNING("You may need to manually clear them or improve the deletion order in the command."))
        else:
            self.stdout.write(self.style.SUCCESS("\nData deletion process completed."))

        self.stdout.write(self.style.WARNING(
            "\nRemember to re-create any necessary initial data (e.g., default genres) if needed."
        ))