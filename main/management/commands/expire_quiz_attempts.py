from django.core.management.base import BaseCommand

from main.services import expire_overdue_attempts


class Command(BaseCommand):
    help = "Muddati tugagan test attemptlarini avtomatik yakunlaydi"

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=500,
            help="Bir ishga tushishda ko'rib chiqiladigan maksimal attemptlar soni",
        )

    def handle(self, *args, **options):
        expired_count = expire_overdue_attempts(limit=options['limit'])
        self.stdout.write(
            self.style.SUCCESS(
                f"{expired_count} ta muddati tugagan attempt yopildi."
            )
        )
