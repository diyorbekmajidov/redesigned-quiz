from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from student.models import Student
import logging
import random


logger = logging.getLogger(__name__)


class Quiz(models.Model):
    """Test modeli - Standart va Psixologik testlar uchun"""
    
    QUIZ_TYPE_CHOICES = [
        ('standard', 'Standart Test'),
        ('psychological', 'Psixologik Test'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Test nomi")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    
    quiz_type = models.CharField(max_length=20, choices=QUIZ_TYPE_CHOICES, default='standard', verbose_name="Test turi")
    
    time_limit = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Daqiqalarda",
        verbose_name="Vaqt chegarasi"
    )
    
    passing_score = models.IntegerField(default=60, validators=[MinValueValidator(0), MaxValueValidator(100)],help_text="Foizda (faqat standart testlar uchun)", verbose_name="O'tish bali")
    
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_quizzes', verbose_name="Yaratuvchi")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")
    attempt_limit = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="Urinishlar soni")

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"
        ordering = ['-created_at']

    def __str__(self):
        quiz_type_icon = "🧠" if self.quiz_type == 'psychological' else "📝"
        return f"{quiz_type_icon} {self.title}"

    def get_total_questions(self):
        """Jami savollar soni"""
        return self.questions.count()

    def get_total_score(self):
        """Maksimal ball"""
        return sum(q.score for q in self.questions.all())
    
    def is_psychological(self):
        """Psixologik testmi?"""
        return self.quiz_type == 'psychological'
    
    def is_standard(self):
        """Standart testmi?"""
        return self.quiz_type == 'standard'
    def can_attempt(self, student):
        """Talaba bu testni urinishlar soni"""
        student_attempts = QuizAttempt.objects.filter(student=student, quiz=self).count()
        return student_attempts < self.attempt_limit


class PsychologicalScale(models.Model):
    """
    Psixologik test uchun shkala (masalan: Depressiya darajasi)
    """
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='psychological_scales',
        verbose_name="Test",
        limit_choices_to={'quiz_type': 'psychological'}
    )
    
    name = models.CharField(
        max_length=200,
        verbose_name="Shkala nomi"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Tavsif"
    )
    
    order = models.IntegerField(
        default=0,
        verbose_name="Tartib"
    )
    
    class Meta:
        verbose_name = "Psixologik shkala"
        verbose_name_plural = "Psixologik shkalalar"
        ordering = ['quiz', 'order']
    
    def __str__(self):
        return f"{self.quiz.title} - {self.name}"

    def clean(self):
        if self.quiz and not self.quiz.is_psychological():
            raise ValidationError("Psixologik shkala faqat psixologik testga tegishli bo'lishi mumkin.")


class PsychologicalCategory(models.Model):
    """
    Psixologik shkala bo'yicha kategoriyalar
    Masalan: 0-7 ball = "Xavotir va depressiya yo'q"
    """
    scale = models.ForeignKey(PsychologicalScale, on_delete=models.CASCADE, related_name='categories', verbose_name="Shkala")
    
    name = models.CharField(max_length=200, verbose_name="Kategoriya nomi")
    
    description = models.TextField(blank=True, verbose_name="Tavsif/Izoh")
    
    min_score = models.IntegerField(verbose_name="Minimal ball")
    
    max_score = models.IntegerField(verbose_name="Maksimal ball")
    
    color = models.CharField(
        max_length=50,
        default='green',
        choices=[
            ('green', 'Yashil'),
            ('yellow', 'Sariq'),
            ('orange', 'To\'q sariq'),
            ('red', 'Qizil'),
        ],
        verbose_name="Rang"
    )
    
    order = models.IntegerField(default=0, verbose_name="Tartib")
    
    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['scale', 'order']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(min_score__lte=models.F('max_score')),
                name='psych_category_min_lte_max',
            ),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.min_score}-{self.max_score})"

    def clean(self):
        if self.min_score > self.max_score:
            raise ValidationError("Minimal ball maksimal balldan katta bo'lishi mumkin emas.")

        if self.scale_id and self.scale.quiz_id:
            if self.scale.quiz.quiz_type != 'psychological':
                raise ValidationError("Kategoriya faqat psixologik test shkalasiga tegishli bo'lishi mumkin.")
    
    def matches_score(self, score):
        """Ball bu kategoriyaga mos keladimi?"""
        return self.min_score <= score <= self.max_score


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="Test"
    )
    
    question_text = models.TextField(verbose_name="Savol matni")
    
    score = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="Ball (standart testlar uchun)")
    
    # ✨ YANGI: Psixologik testlar uchun shkala
    psychological_scale = models.ForeignKey(
        PsychologicalScale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='questions',
        verbose_name="Psixologik shkala"
    )
    
    order = models.IntegerField(default=0, verbose_name="Tartib raqami")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        ordering = ['quiz', 'order']

    def __str__(self):
        return f"{self.quiz.title} - {self.question_text[:50]}"
    
    def clean(self):
        """Validatsiya"""
        if self.quiz and self.quiz.is_psychological() and not self.psychological_scale:
            raise ValidationError(
                "Psixologik testda har bir savol shkala bilan bog'lanishi kerak!"
            )
        
        if self.quiz and self.quiz.is_standard() and self.psychological_scale:
            raise ValidationError(
                "Standart testda shkala ishlatilmaydi!"
            )

        if self.psychological_scale and self.quiz_id != self.psychological_scale.quiz_id:
            raise ValidationError("Savol shkalasi aynan shu testga tegishli bo'lishi kerak.")


class QuestionText(models.Model):
    """Bulk question upload"""
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='question_texts',
        verbose_name="Test"
    )
    question_text = models.TextField(
        verbose_name="Savol matni va javoblar",
        help_text="Format: Savol===Variant1===Variant2===#To'g'riVariant+++KeyingiSavol"
    )
    score = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="Ball")
    is_processed = models.BooleanField(default=False, verbose_name="Qayta ishlangan", editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Savol yuklash (bulk)"
        verbose_name_plural = "Savollar yuklash (bulk)"

    def save(self, *args, **kwargs):
        if self.pk and self.is_processed:
            super().save(*args, **kwargs)
            return

        with transaction.atomic():
            super().save(*args, **kwargs)

            try:
                questions = self.question_text.split('+++++')
                current_order = self.quiz.questions.count()

                for q_text in questions:
                    q_text = q_text.strip()
                    if not q_text:
                        continue

                    parts = q_text.split('=====')
                    if len(parts) < 2:
                        continue

                    question_text = parts[0].strip()
                    options = parts[1:]

                    if not options:
                        continue

                    options_list = []
                    has_correct = False
                    for option in options:
                        option_text = option.strip()
                        if not option_text:
                            continue

                        is_correct = option_text.startswith('#')
                        if is_correct:
                            option_text = option_text[1:].strip()
                            has_correct = True
                        options_list.append((option_text, is_correct))

                    if not has_correct or not options_list:
                        continue

                    random.shuffle(options_list)

                    question = Question.objects.create(
                        quiz=self.quiz,
                        question_text=question_text,
                        score=self.score,
                        order=current_order
                    )
                    current_order += 1

                    for option_text, is_correct in options_list:
                        Option.objects.create(
                            question=question,
                            option_text=option_text,
                            is_correct=is_correct
                        )

                self.is_processed = True
                super().save(update_fields=['is_processed'])

            except Exception:
                logger.exception("Bulk savollarni qayta ishlashda xatolik yuz berdi")
                raise

    def __str__(self):
        status = "✓ Qayta ishlangan" if self.is_processed else "⏳ Kutilmoqda"
        return f"{self.quiz.title} - {status}"


class Option(models.Model):
    """Javob varianti - standart va psixologik testlar uchun"""
    
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options', verbose_name="Savol")
    
    option_text = models.CharField(max_length=255, verbose_name="Javob varianti")
    
    is_correct = models.BooleanField(default=False, verbose_name="To'g'ri javob (standart testlar)")
    
    psychological_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Ball (psixologik testlar)",
        help_text="0, 1, 2, 3 yoki boshqa ball"
    )
    
    order = models.IntegerField(default=0, verbose_name="Tartib")

    class Meta:
        verbose_name = "Javob varianti"
        verbose_name_plural = "Javob variantlari"
        ordering = ['question', 'order']

    def __str__(self):
        if self.question.quiz.is_psychological():
            return f"{self.option_text} ({self.psychological_score} ball)"
        else:
            return f"{self.option_text} ({'✓' if self.is_correct else '✗'})"
    
    def clean(self):
        """Validatsiya"""
        # Psixologik testda is_correct ishlatilmasligi kerak
        if self.question.quiz.is_psychological() and self.is_correct:
            raise ValidationError(
                "Psixologik testda 'to'g'ri javob' ishlatilmaydi! "
                "O'rniga 'psychological_score' foydalaning."
            )
        
        # Standart testda psychological_score ishlatilmasligi kerak
        if self.question.quiz.is_standard() and self.psychological_score > 0:
            raise ValidationError(
                "Standart testda 'psychological_score' ishlatilmaydi! "
                "O'rniga 'is_correct' foydalaning."
            )


class QuizAttempt(models.Model):
    """Test urinishi"""
    
    STATUS_CHOICES = [
        ('in_progress', 'Jarayonda'),
        ('completed', 'Yakunlangan'),
        ('expired', 'Vaqti tugagan'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='quiz_attempts',
        verbose_name="Talaba"
    )
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts', verbose_name="Test")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress', verbose_name="Holat")
    
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Boshlangan")
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Muddati tugash vaqti",
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugatilgan")
    
    time_taken = models.IntegerField(null=True, blank=True, help_text="Soniyalarda", verbose_name="Sarflangan vaqt")
    
    class Meta:
        verbose_name = "Test urinishi"
        verbose_name_plural = "Test urinishlari"
        ordering = ['-started_at']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'quiz'],
                condition=models.Q(status='in_progress'),
                name='unique_active_attempt'
            )
        ]

    def __str__(self):
        return f"{self.student.student_name} - {self.quiz.title} ({self.get_status_display()})"

    def is_time_expired(self):
        """Vaqt tugaganmi tekshirish"""
        if self.status != 'in_progress':
            return False
        return timezone.now() >= self.get_expiration_time()

    def get_expiration_time(self):
        """Attempt tugaydigan vaqtni qaytaradi.

        Eski attemptlar uchun expires_at hali to'ldirilmagan bo'lishi mumkin,
        shuning uchun started_at va quiz.time_limit orqali zaxira hisoblanadi.
        """
        if self.expires_at:
            return self.expires_at
        return self.started_at + timedelta(minutes=self.quiz.time_limit)

    def get_remaining_time(self):
        """Qolgan vaqt (soniyalarda)"""
        if self.status != 'in_progress':
            return 0
        remaining = (self.get_expiration_time() - timezone.now()).total_seconds()
        return max(0, int(remaining))

    def save(self, *args, **kwargs):
        """Yangi attempt uchun tugash vaqtini avtomatik saqlaydi."""
        if self.expires_at is None and self.status == 'in_progress':
            start_time = self.started_at or timezone.now()
            self.expires_at = start_time + timedelta(minutes=self.quiz.time_limit)
        super().save(*args, **kwargs)
    
    @transaction.atomic
    def complete_attempt(self):
        """Testni tugatish va natijani hisoblash"""
        attempt = type(self).objects.select_for_update().select_related('quiz').get(pk=self.pk)
        if attempt.status != 'in_progress':
            return False

        attempt.status = 'completed'
        attempt.completed_at = timezone.now()
        attempt.time_taken = int((attempt.completed_at - attempt.started_at).total_seconds())
        attempt.save(update_fields=['status', 'completed_at', 'time_taken'])

        if attempt.quiz.is_standard():
            Result.calculate_result(attempt)
        else:
            PsychologicalResult.calculate_result(attempt)

        self.status = attempt.status
        self.completed_at = attempt.completed_at
        self.time_taken = attempt.time_taken
        return True

    @transaction.atomic
    def expire_attempt(self):
        """Vaqt tugaganda testni yakunlash"""
        attempt = type(self).objects.select_for_update().select_related('quiz').get(pk=self.pk)
        if attempt.status != 'in_progress':
            return False

        attempt.status = 'expired'
        attempt.completed_at = timezone.now()
        attempt.time_taken = max(
            0,
            int((attempt.get_expiration_time() - attempt.started_at).total_seconds()),
        )
        attempt.save(update_fields=['status', 'completed_at', 'time_taken'])

        if attempt.quiz.is_standard():
            Result.calculate_result(attempt)
        else:
            PsychologicalResult.calculate_result(attempt)

        self.status = attempt.status
        self.completed_at = attempt.completed_at
        self.time_taken = attempt.time_taken
        return True


class UserResponse(models.Model):
    """Foydalanuvchi javobi"""
    
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name="Urinish"
    )
    
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        verbose_name="Savol"
    )
    
    selected_option = models.ForeignKey(
        Option,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Tanlangan variant"
    )
    
    # Standart testlar uchun
    is_correct = models.BooleanField(
        default=False,
        verbose_name="To'g'ri"
    )
    
    # ✨ Psixologik testlar uchun
    earned_score = models.IntegerField(
        default=0,
        verbose_name="Olingan ball"
    )
    
    answered_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Javob berilgan"
    )

    class Meta:
        verbose_name = "Foydalanuvchi javobi"
        verbose_name_plural = "Foydalanuvchi javoblari"
        unique_together = ['attempt', 'question']
        indexes = [
            models.Index(fields=['attempt', 'is_correct']),
        ]

    def __str__(self):
        return f"{self.attempt.student.student_name} - {self.question.question_text[:30]}"

    def save(self, *args, **kwargs):
        """Javobni tekshirish"""
        if self.selected_option:
            if self.attempt.quiz.is_standard():
                # Standart test
                self.is_correct = self.selected_option.is_correct
                self.earned_score = self.question.score if self.is_correct else 0
            else:
                # Psixologik test
                self.is_correct = False  # Psixologik testda to'g'ri/noto'g'ri yo'q
                self.earned_score = self.selected_option.psychological_score

        # Django save() clean()ni avtomatik chaqirmaydi. Javoblar admin yoki
        # boshqa service orqali yozilganda ham quiz chegaralari tekshirilsin.
        self.full_clean()
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validatsiya"""
        if self.attempt_id and self.question_id:
            if self.question.quiz_id != self.attempt.quiz_id:
                raise ValidationError("Javob savolining testi attempt testiga mos kelmaydi.")

        if self.selected_option and self.selected_option.question != self.question:
            raise ValidationError("Tanlangan variant bu savolga tegishli emas!")


class Result(models.Model):
    """Standart test natijasi"""
    
    attempt = models.OneToOneField(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='result',
        verbose_name="Urinish"
    )
    
    total_questions = models.IntegerField(verbose_name="Jami savollar")
    correct_answers = models.IntegerField(verbose_name="To'g'ri javoblar")
    wrong_answers = models.IntegerField(verbose_name="Noto'g'ri javoblar")
    unanswered = models.IntegerField(default=0, verbose_name="Javobsiz")
    total_score = models.IntegerField(verbose_name="Umumiy ball")
    max_score = models.IntegerField(verbose_name="Maksimal ball")
    
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Foiz"
    )
    
    passed = models.BooleanField(verbose_name="O'tdi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")

    class Meta:
        verbose_name = "Natija (Standart)"
        verbose_name_plural = "Natijalar (Standart)"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['passed', '-created_at']),
        ]

    def __str__(self):
        status = "✓ O'tdi" if self.passed else "✗ O'tmadi"
        return f"{self.attempt.student.student_name} - {self.percentage}% ({status})"

    @classmethod
    def calculate_result(cls, attempt):
        """Standart test natijasini hisoblash"""
        responses = attempt.responses.select_related('question')
        total_questions = attempt.quiz.get_total_questions()
        correct_answers = responses.filter(is_correct=True).count()
        wrong_answers = responses.filter(
            is_correct=False, 
            selected_option__isnull=False
        ).count()
        unanswered = total_questions - responses.count()

        # Ball hisoblash
        total_score = sum(
            r.question.score for r in responses.filter(is_correct=True)
        )
        max_score = attempt.quiz.get_total_score()
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        passed = percentage >= attempt.quiz.passing_score

        # Natijani saqlash
        result, created = cls.objects.update_or_create(
            attempt=attempt,
            defaults={
                'total_questions': total_questions,
                'correct_answers': correct_answers,
                'wrong_answers': wrong_answers,
                'unanswered': unanswered,
                'total_score': total_score,
                'max_score': max_score,
                'percentage': round(percentage, 2),
                'passed': passed,
            }
        )
        return result
    
    def get_grade(self):
        """Baho olish (5-bahollik tizim)"""
        if self.percentage >= 86:
            return 5
        elif self.percentage >= 71:
            return 4
        elif self.percentage >= 60:
            return 3
        else:
            return 2


class PsychologicalResult(models.Model):
    """Psixologik test natijasi"""
    
    attempt = models.OneToOneField(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='psychological_result',
        verbose_name="Urinish"
    )
    
    total_questions = models.IntegerField(verbose_name="Jami savollar")
    answered_questions = models.IntegerField(verbose_name="Javob berilgan")
    unanswered = models.IntegerField(verbose_name="Javobsiz")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    
    class Meta:
        verbose_name = "Natija (Psixologik)"
        verbose_name_plural = "Natijalar (Psixologik)"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.attempt.student.student_name} - {self.attempt.quiz.title}"
    
    @classmethod
    def calculate_result(cls, attempt):
        """Psixologik test natijasini hisoblash"""
        responses = attempt.responses.select_related('question', 'question__psychological_scale')
        total_questions = attempt.quiz.get_total_questions()
        answered = responses.count()
        unanswered = total_questions - answered
        
        # Asosiy natija
        result, created = cls.objects.update_or_create(
            attempt=attempt,
            defaults={
                'total_questions': total_questions,
                'answered_questions': answered,
                'unanswered': unanswered,
            }
        )
        
        # Har bir shkala bo'yicha ballni hisoblash
        scales = attempt.quiz.psychological_scales.all()
        
        for scale in scales:
            # Shu shkalaga tegishli javoblar
            scale_responses = responses.filter(
                question__psychological_scale=scale
            )
            
            # Umumiy ball
            total_score = sum(r.earned_score for r in scale_responses)
            
            # Kategoriyani aniqlash
            category = None
            for cat in scale.categories.all():
                if cat.matches_score(total_score):
                    category = cat
                    break
            
            # Shkala natijasini saqlash
            PsychologicalScaleResult.objects.update_or_create(
                result=result,
                scale=scale,
                defaults={
                    'total_score': total_score,
                    'category': category,
                }
            )
        
        return result


class PsychologicalScaleResult(models.Model):
    """Har bir shkala bo'yicha natija"""
    
    result = models.ForeignKey(
        PsychologicalResult,
        on_delete=models.CASCADE,
        related_name='scale_results',
        verbose_name="Natija"
    )
    
    scale = models.ForeignKey(
        PsychologicalScale,
        on_delete=models.CASCADE,
        verbose_name="Shkala"
    )
    
    total_score = models.IntegerField(
        verbose_name="Umumiy ball"
    )
    
    category = models.ForeignKey(
        PsychologicalCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Kategoriya"
    )
    
    class Meta:
        verbose_name = "Shkala natijasi"
        verbose_name_plural = "Shkala natijalari"
        unique_together = ['result', 'scale']

    def clean(self):
        if self.result_id and self.scale_id:
            if self.result.attempt.quiz_id != self.scale.quiz_id:
                raise ValidationError("Shkala natijadagi attempt testi bilan bir xil bo'lishi kerak.")

        if self.category_id and self.category.scale_id != self.scale_id:
            raise ValidationError("Kategoriya tanlangan shkalaga tegishli emas.")
    
    def __str__(self):
        return f"{self.scale.name}: {self.total_score} ball"
