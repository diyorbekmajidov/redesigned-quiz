from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from student.models import Student
import random

class Quiz(models.Model):
    title = models.CharField(max_length=200, verbose_name="Test nomi")
    description = models.TextField(blank=True, verbose_name="Tavsif")
    time_limit = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Daqiqalarda",
        verbose_name="Vaqt chegarasi"
    )
    passing_score = models.IntegerField(
        default=60,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Foizda",
        verbose_name="O'tish bali"
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_quizzes',
        verbose_name="Yaratuvchi"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_total_questions(self):
        """Jami savollar soni"""
        return self.questions.count()

    def get_total_score(self):
        """Maksimal ball"""
        return sum(q.score for q in self.questions.all())
    
class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="Test"
    )
    question_text = models.TextField(verbose_name="Savol matni")
    score = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Ball"
    )
    order = models.IntegerField(default=0, verbose_name="Tartib raqami")  # YANGI: Savollar tartibini saqlash
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        ordering = ['quiz', 'order']  # Tartib bo'yicha

    def __str__(self):
        return f"{self.quiz.title} - {self.question_text[:50]}"
    

class QuestionText(models.Model):
    """
    FAQAT admin orqali ko'plab savollarni birdaniga yuklash uchun!
    Format:
    Savol matni?
    =====
    Variant 1
    =====
    Variant 2
    =====
    #To'g'ri variant (# bilan)
    =====
    Variant 4
    +++++
    Keyingi savol...
    """
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
    score = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Ball"
    )
    is_processed = models.BooleanField(
        default=False, 
        verbose_name="Qayta ishlangan",
        editable=False
    )  # YANGI: Duplikatsiyani oldini olish
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Savol yuklash (bulk)"
        verbose_name_plural = "Savollar yuklash (bulk)"

    def save(self, *args, **kwargs):
        # Agar allaqachon qayta ishlangan bo'lsa, yangi Question yaratmaslik
        if self.pk and self.is_processed:
            super().save(*args, **kwargs)
            return
            
        # Avval QuestionText obyektini saqlash
        super().save(*args, **kwargs)
        
        # Keyin Question va Option yaratish
        try:
            questions = self.question_text.split('+++++')
            current_order = self.quiz.questions.count()  # Oxirgi savol tartibidan davom etish

            for q_text in questions:
                q_text = q_text.strip()
                if not q_text:
                    continue
                    
                parts = q_text.split('=====')
                if len(parts) < 2:  # Kamida savol va 1 ta variant bo'lishi kerak
                    continue
                    
                question_text = parts[0].strip()
                options = parts[1:]
                
                if not options:  # Variant bo'lmasa, o'tkazib yuborish
                    continue
                
                # Option'larni tayyorlash
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
                
                # Agar to'g'ri javob bo'lmasa, o'tkazib yuborish
                if not has_correct or not options_list:
                    continue
                
                # Variantlarni aralashtirish
                random.shuffle(options_list)

                # Question yaratish
                question = Question.objects.create(
                    quiz=self.quiz,
                    question_text=question_text,
                    score=self.score,
                    order=current_order
                )
                current_order += 1
                
                # Option'larni yaratish
                for option_text, is_correct in options_list:
                    Option.objects.create(
                        question=question,
                        option_text=option_text,
                        is_correct=is_correct
                    )
            
            # Muvaffaqiyatli qayta ishlangan deb belgilash
            self.is_processed = True
            super().save(update_fields=['is_processed'])
            
        except Exception as e:
            # Xatolik yuz bersa, yaratilgan savollarni o'chirish
            print(f"Xatolik: {e}")
            # Bu yerda logging qo'shish kerak
            raise

    def __str__(self):
        status = "✓ Qayta ishlangan" if self.is_processed else "⏳ Kutilmoqda"
        return f"{self.quiz.title} - {status}"


class Option(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name="Savol"
    )
    option_text = models.CharField(max_length=255, verbose_name="Javob varianti")
    is_correct = models.BooleanField(default=False, verbose_name="To'g'ri javob")

    class Meta:
        verbose_name = "Javob varianti"
        verbose_name_plural = "Javob variantlari"

    def __str__(self):
        return f"{self.option_text} ({'✓' if self.is_correct else '✗'})"
    
    
class QuizAttempt(models.Model):
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
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name="Test"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress',
        verbose_name="Holat"
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Boshlangan")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugatilgan")
    time_taken = models.IntegerField(
        null=True,
        blank=True,
        help_text="Soniyalarda",
        verbose_name="Sarflangan vaqt"
    )
    
    class Meta:
        verbose_name = "Test urinishi"
        verbose_name_plural = "Test urinishlari"
        ordering = ['-started_at']
        # YANGI: Bir talaba bir testni bir vaqtda faqat bir marta topshirishi mumkin
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
        elapsed = (timezone.now() - self.started_at).total_seconds() / 60
        return elapsed > self.quiz.time_limit

    def get_remaining_time(self):
        """Qolgan vaqt (soniyalarda)"""
        if self.status != 'in_progress':
            return 0
        elapsed = (timezone.now() - self.started_at).total_seconds()
        total_seconds = self.quiz.time_limit * 60
        remaining = total_seconds - elapsed
        return max(0, int(remaining))
    
    def complete_attempt(self):
        """Testni tugatish va natijani hisoblash"""
        if self.status == 'in_progress':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.time_taken = int((self.completed_at - self.started_at).total_seconds())
            self.save()
            
            # Natijani hisoblash
            Result.calculate_result(self)
    
    def expire_attempt(self):
        """Vaqt tugaganda testni yakunlash"""
        if self.status == 'in_progress':
            self.status = 'expired'
            self.completed_at = timezone.now()
            self.time_taken = self.quiz.time_limit * 60
            self.save()
            
            # Natijani hisoblash
            Result.calculate_result(self)


class UserResponse(models.Model):
    """Foydalanuvchi javobi modeli"""
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
    is_correct = models.BooleanField(default=False, verbose_name="To'g'ri")
    answered_at = models.DateTimeField(auto_now_add=True, verbose_name="Javob berilgan")

    class Meta:
        verbose_name = "Foydalanuvchi javobi"
        verbose_name_plural = "Foydalanuvchi javoblari"
        unique_together = ['attempt', 'question']
        indexes = [
            models.Index(fields=['attempt', 'is_correct']),  # YANGI: Tezroq qidirish uchun
        ]

    def __str__(self):
        return f"{self.attempt.student.student_name} - {self.question.question_text[:30]}"

    def save(self, *args, **kwargs):
        """Javob to'g'ri yoki noto'g'riligini tekshirish"""
        if self.selected_option:
            self.is_correct = self.selected_option.is_correct
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validatsiya"""
        from django.core.exceptions import ValidationError
        
        # Tanlangan option shu savolga tegishli ekanligini tekshirish
        if self.selected_option and self.selected_option.question != self.question:
            raise ValidationError("Tanlangan variant bu savolga tegishli emas!")


class Result(models.Model):
    """Yakuniy natija modeli"""
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
        verbose_name = "Natija"
        verbose_name_plural = "Natijalar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['passed', '-created_at']),  # YANGI: O'tganlarni tez topish
        ]

    def __str__(self):
        status = "✓ O'tdi" if self.passed else "✗ O'tmadi"
        return f"{self.attempt.student.student_name} - {self.percentage}% ({status})"

    @classmethod
    def calculate_result(cls, attempt):
        """Natijani hisoblash"""
        responses = attempt.responses.select_related('question')  # YANGI: Optimizatsiya
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