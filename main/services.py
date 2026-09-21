"""Test attemptlari bilan bog'liq umumiy servislar."""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import QuizAttempt


def expire_overdue_attempts(*, student=None, limit=None):
    """Muddati tugagan faol attemptlarni yopadi va natijasini hisoblaydi.

    Bu servis cron command va foydalanuvchi sahifani ochgandagi zaxira
    tekshiruv tomonidan bir xil ishlatiladi. Har bir attempt alohida lock
    bilan olinadi, shuning uchun parallel ishga tushishlarda ikki marta natija
    hisoblanmaydi.
    """
    now = timezone.now()
    candidates = QuizAttempt.objects.filter(status='in_progress')

    if student is not None:
        candidates = candidates.filter(student=student)

    # Yangi attemptlarda expires_at indexlangan bo'ladi. Eski attemptlar
    # uchun expires_at null bo'lishi mumkin, ularni ham zaxira sifatida tekshiramiz.
    candidates = candidates.filter(
        Q(expires_at__lte=now) | Q(expires_at__isnull=True)
    ).order_by('expires_at', 'started_at')

    candidate_ids = candidates.values_list('id', flat=True)
    if limit is not None:
        candidate_ids = candidate_ids[:limit]

    expired_count = 0

    for attempt_id in candidate_ids:
        with transaction.atomic():
            attempt = (
                QuizAttempt.objects
                .select_for_update()
                .select_related('quiz')
                .filter(pk=attempt_id, status='in_progress')
                .first()
            )

            if attempt is None or not attempt.is_time_expired():
                continue

            attempt.expire_attempt()
            expired_count += 1

    return expired_count
