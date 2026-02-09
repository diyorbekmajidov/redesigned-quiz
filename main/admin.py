# ============================================
# ADMIN PANEL - PSIXOLOGIK VA STANDART TESTLAR
# ============================================

"""
main/admin.py - To'liq admin interface
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Quiz, Question, QuestionText, Option,
    QuizAttempt, UserResponse, Result,
    PsychologicalScale, PsychologicalCategory,
    PsychologicalResult, PsychologicalScaleResult
)


# ==================== INLINE ADMINS ====================

class PsychologicalScaleInline(admin.TabularInline):
    """Quiz ichida shkalalarni ko'rsatish"""
    model = PsychologicalScale
    extra = 1
    fields = ('name', 'description', 'order')


class PsychologicalCategoryInline(admin.TabularInline):
    """Shkala ichida kategoriyalarni ko'rsatish"""
    model = PsychologicalCategory
    extra = 1
    fields = ('name', 'min_score', 'max_score', 'color', 'order', 'description')


class OptionInline(admin.TabularInline):
    """Question ichida javoblarni ko'rsatish"""
    model = Option
    extra = 4
    fields = ('option_text', 'is_correct', 'psychological_score', 'order')
    
    def get_formset(self, request, obj=None, **kwargs):
        """Dinamik fieldlar - test turiga qarab"""
        formset = super().get_formset(request, obj, **kwargs)
        
        # Agar quiz mavjud bo'lsa
        if obj and obj.quiz:
            if obj.quiz.is_psychological():
                # Psixologik testda faqat psychological_score
                self.fields = ('option_text', 'psychological_score', 'order')
            else:
                # Standart testda faqat is_correct
                self.fields = ('option_text', 'is_correct', 'order')
        
        return formset


class QuestionInline(admin.TabularInline):
    """Quiz ichida savollarni ko'rsatish (small preview)"""
    model = Question
    extra = 0
    fields = ('question_text', 'score', 'psychological_scale', 'order')
    show_change_link = True  # Savolga o'tish uchun


class PsychologicalScaleResultInline(admin.TabularInline):
    """Psixologik natija ichida shkala natijalarini ko'rsatish"""
    model = PsychologicalScaleResult
    extra = 0
    readonly_fields = ('scale', 'total_score', 'category', 'category_color')
    can_delete = False
    
    def category_color(self, obj):
        """Kategoriya rangini ko'rsatish"""
        if obj.category:
            colors = {
                'green': '#10B981',
                'yellow': '#F59E0B',
                'orange': '#F97316',
                'red': '#EF4444',
            }
            color = colors.get(obj.category.color, '#6B7280')
            return format_html(
                '<span style="display:inline-block;width:20px;height:20px;'
                'background:{};border-radius:50%;"></span> {}',
                color,
                obj.category.name
            )
        return '-'
    
    category_color.short_description = 'Kategoriya'


# ==================== MAIN ADMINS ====================

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Quiz admin"""
    
    list_display = (
        'quiz_icon',
        'title',
        'quiz_type',
        'time_limit',
        'passing_score',
        'questions_count',
        'attempts_count',
        'is_active',
        'created_at'
    )
    
    list_filter = (
        'quiz_type',
        'is_active',
        'created_at',
    )
    
    search_fields = ('title', 'description')
    
    fieldsets = (
        ('Asosiy Ma\'lumotlar', {
            'fields': ('title', 'description', 'quiz_type', 'is_active')
        }),
        ('Test Sozlamalari', {
            'fields': ('time_limit', 'passing_score'),
            'description': 'passing_score faqat standart testlar uchun ishlatiladi'
        }),
        ('Texnik Ma\'lumotlar', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PsychologicalScaleInline, QuestionInline]
    
    def save_model(self, request, obj, form, change):
        """Yaratuvchini avtomatik o'rnatish"""
        if not change:  # Yangi quiz
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def quiz_icon(self, obj):
        """Test turi ikonasi"""
        if obj.is_psychological():
            return format_html('<span style="font-size:20px;">🧠</span>')
        return format_html('<span style="font-size:20px;">📝</span>')
    
    quiz_icon.short_description = ''
    
    def questions_count(self, obj):
        """Savollar soni"""
        count = obj.get_total_questions()
        return format_html(
            '<strong style="color:#4F46E5;">{}</strong> ta',
            count
        )
    
    questions_count.short_description = 'Savollar'
    
    def attempts_count(self, obj):
        """Urinishlar soni"""
        count = obj.attempts.count()
        return format_html(
            '<span style="color:#10B981;">{}</span> urinish',
            count
        )
    
    attempts_count.short_description = 'Urinishlar'


@admin.register(PsychologicalScale)
class PsychologicalScaleAdmin(admin.ModelAdmin):
    """Psixologik shkala admin"""
    
    list_display = ('name', 'quiz', 'categories_count', 'order')
    list_filter = ('quiz',)
    search_fields = ('name', 'description')
    
    inlines = [PsychologicalCategoryInline]
    
    def categories_count(self, obj):
        """Kategoriyalar soni"""
        return obj.categories.count()
    
    categories_count.short_description = 'Kategoriyalar'


@admin.register(PsychologicalCategory)
class PsychologicalCategoryAdmin(admin.ModelAdmin):
    """Kategoriya admin"""
    
    list_display = ('name', 'scale', 'score_range', 'color_display', 'order')
    list_filter = ('scale', 'color')
    search_fields = ('name', 'description')
    
    def score_range(self, obj):
        """Ball oralig'i"""
        return f"{obj.min_score} - {obj.max_score}"
    
    score_range.short_description = 'Ball oralig\'i'
    
    def color_display(self, obj):
        """Rang ko'rsatish"""
        colors = {
            'green': '#10B981',
            'yellow': '#F59E0B',
            'orange': '#F97316',
            'red': '#EF4444',
        }
        color = colors.get(obj.color, '#6B7280')
        return format_html(
            '<span style="display:inline-block;width:50px;height:20px;'
            'background:{};border-radius:4px;"></span>',
            color
        )
    
    color_display.short_description = 'Rang'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Savol admin"""
    
    list_display = (
        'quiz',
        'question_preview',
        'quiz_type_display',
        'score',
        'psychological_scale',
        'options_count',
        'order'
    )
    
    list_filter = (
        'quiz__quiz_type',
        'quiz',
        'psychological_scale',
    )
    
    search_fields = ('question_text',)
    
    inlines = [OptionInline]
    
    fieldsets = (
        ('Savol', {
            'fields': ('quiz', 'question_text', 'order')
        }),
        ('Ball va Shkala', {
            'fields': ('score', 'psychological_scale'),
            'description': (
                'Standart testda faqat "score" ishlatiladi. '
                'Psixologik testda "psychological_scale" tanlash majburiy.'
            )
        }),
    )
    
    def question_preview(self, obj):
        """Savol previewi"""
        text = obj.question_text[:100]
        if len(obj.question_text) > 100:
            text += '...'
        return text
    
    question_preview.short_description = 'Savol'
    
    def quiz_type_display(self, obj):
        """Test turi"""
        if obj.quiz.is_psychological():
            return format_html('<span style="color:#7C3AED;">🧠 Psixologik</span>')
        return format_html('<span style="color:#4F46E5;">📝 Standart</span>')
    
    quiz_type_display.short_description = 'Test turi'
    
    def options_count(self, obj):
        """Javoblar soni"""
        return obj.options.count()
    
    options_count.short_description = 'Javoblar'


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    """Javob varianti admin"""
    
    list_display = (
        'option_text',
        'question',
        'quiz_type_display',
        'is_correct',
        'psychological_score',
        'order'
    )
    
    list_filter = (
        'question__quiz__quiz_type',
        'is_correct',
    )
    
    search_fields = ('option_text', 'question__question_text')
    
    def quiz_type_display(self, obj):
        """Test turi"""
        if obj.question.quiz.is_psychological():
            return format_html(
                '<span style="color:#7C3AED;">🧠 Psixologik ({} ball)</span>',
                obj.psychological_score
            )
        
        status = '✓ To\'g\'ri' if obj.is_correct else '✗ Noto\'g\'ri'
        color = '#10B981' if obj.is_correct else '#EF4444'
        return format_html(
            '<span style="color:{};">📝 {} </span>',
            color,
            status
        )
    
    quiz_type_display.short_description = 'Holat'


@admin.register(QuestionText)
class QuestionTextAdmin(admin.ModelAdmin):
    """Bulk upload admin"""
    
    list_display = ('quiz', 'status_display', 'score', 'created_at')
    list_filter = ('is_processed', 'quiz')
    readonly_fields = ('is_processed',)
    
    def status_display(self, obj):
        """Holat"""
        if obj.is_processed:
            return format_html(
                '<span style="color:#10B981;font-weight:bold;">✓ Qayta ishlangan</span>'
            )
        return format_html(
            '<span style="color:#F59E0B;font-weight:bold;">⏳ Kutilmoqda</span>'
        )
    
    status_display.short_description = 'Holat'


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    """Urinish admin"""
    
    list_display = (
        'student',
        'quiz',
        'quiz_type_display',
        'status',
        'started_at',
        'completed_at',
        'time_display',
        'view_result'
    )
    
    list_filter = (
        'status',
        'quiz__quiz_type',
        'quiz',
        'started_at',
    )
    
    search_fields = (
        'student__student_name',
        'student__student_id_number',
        'quiz__title'
    )
    
    readonly_fields = (
        'started_at',
        'completed_at',
        'time_taken'
    )
    
    def quiz_type_display(self, obj):
        """Test turi"""
        if obj.quiz.is_psychological():
            return '🧠 Psixologik'
        return '📝 Standart'
    
    quiz_type_display.short_description = 'Tur'
    
    def time_display(self, obj):
        """Vaqt ko'rsatish"""
        if obj.time_taken:
            minutes = obj.time_taken // 60
            seconds = obj.time_taken % 60
            return f"{minutes}m {seconds}s"
        return '-'
    
    time_display.short_description = 'Vaqt'
    
    def view_result(self, obj):
        """Natijani ko'rish"""
        if obj.status == 'completed':
            if obj.quiz.is_standard() and hasattr(obj, 'result'):
                return format_html(
                    '<a href="/admin/main/result/{}/change/" '
                    'style="color:#4F46E5;font-weight:bold;">📊 Natija</a>',
                    obj.result.id
                )
            elif obj.quiz.is_psychological() and hasattr(obj, 'psychological_result'):
                return format_html(
                    '<a href="/admin/main/psychologicalresult/{}/change/" '
                    'style="color:#7C3AED;font-weight:bold;">🧠 Natija</a>',
                    obj.psychological_result.id
                )
        return '-'
    
    view_result.short_description = 'Natija'


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    """Standart test natijasi admin"""
    
    list_display = (
        'student_name',
        'quiz',
        'percentage_display',
        'grade_display',
        'passed_display',
        'created_at'
    )
    
    list_filter = (
        'passed',
        'attempt__quiz',
        'created_at',
    )
    
    search_fields = (
        'attempt__student__student_name',
        'attempt__quiz__title'
    )
    
    readonly_fields = (
        'attempt',
        'total_questions',
        'correct_answers',
        'wrong_answers',
        'unanswered',
        'total_score',
        'max_score',
        'percentage',
        'passed'
    )
    
    def student_name(self, obj):
        """Talaba ismi"""
        return obj.attempt.student.student_name
    
    student_name.short_description = 'Talaba'
    
    def quiz(self, obj):
        """Test nomi"""
        return obj.attempt.quiz.title
    
    quiz.short_description = 'Test'
    
    def percentage_display(self, obj):
        """Foiz ko'rsatish"""
        color = '#10B981' if obj.passed else '#EF4444'
        return format_html(
            '<strong style="color:{}; font-size:16px;">{:.1f}%</strong>',
            color,
            obj.percentage
        )
    
    percentage_display.short_description = 'Natija'
    
    def grade_display(self, obj):
        """Baho"""
        grade = obj.get_grade()
        colors = {5: '#10B981', 4: '#3B82F6', 3: '#F59E0B', 2: '#EF4444'}
        return format_html(
            '<span style="background:{}; color:white; padding:4px 12px; '
            'border-radius:12px; font-weight:bold;">{}</span>',
            colors.get(grade, '#6B7280'),
            grade
        )
    
    grade_display.short_description = 'Baho'
    
    def passed_display(self, obj):
        """O'tdi/O'tmadi"""
        if obj.passed:
            return format_html(
                '<span style="color:#10B981;font-weight:bold;">✓ O\'tdi</span>'
            )
        return format_html(
            '<span style="color:#EF4444;font-weight:bold;">✗ O\'tmadi</span>'
        )
    
    passed_display.short_description = 'Holat'


@admin.register(PsychologicalResult)
class PsychologicalResultAdmin(admin.ModelAdmin):
    """Psixologik test natijasi admin"""
    
    list_display = (
        'student_name',
        'quiz',
        'answered_display',
        'scales_summary',
        'created_at'
    )
    
    list_filter = (
        'attempt__quiz',
        'created_at',
    )
    
    search_fields = (
        'attempt__student__student_name',
        'attempt__quiz__title'
    )
    
    readonly_fields = (
        'attempt',
        'total_questions',
        'answered_questions',
        'unanswered'
    )
    
    inlines = [PsychologicalScaleResultInline]
    
    def student_name(self, obj):
        """Talaba ismi"""
        return obj.attempt.student.student_name
    
    student_name.short_description = 'Talaba'
    
    def quiz(self, obj):
        """Test nomi"""
        return obj.attempt.quiz.title
    
    quiz.short_description = 'Test'
    
    def answered_display(self, obj):
        """Javob berilgan savollar"""
        return format_html(
            '<strong>{}</strong> / {} ta',
            obj.answered_questions,
            obj.total_questions
        )
    
    answered_display.short_description = 'Javoblar'
    
    def scales_summary(self, obj):
        """Shkalalar qisqacha"""
        results = obj.scale_results.select_related('scale', 'category')
        if not results:
            return '-'
        
        summary = []
        for sr in results:
            if sr.category:
                summary.append(f"{sr.scale.name}: {sr.total_score} ({sr.category.name})")
        
        return ', '.join(summary) if summary else '-'
    
    scales_summary.short_description = 'Natijalar'


# ==================== USER RESPONSE ====================

@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    """Javob admin (faqat ko'rish uchun)"""
    
    list_display = (
        'student_name',
        'quiz_name',
        'question_preview',
        'response_display',
        'answered_at'
    )
    
    list_filter = (
        'attempt__quiz__quiz_type',
        'is_correct',
        'answered_at'
    )
    
    search_fields = (
        'attempt__student__student_name',
        'question__question_text'
    )
    
    readonly_fields = (
        'attempt',
        'question',
        'selected_option',
        'is_correct',
        'earned_score',
        'answered_at'
    )
    
    def student_name(self, obj):
        return obj.attempt.student.student_name
    
    student_name.short_description = 'Talaba'
    
    def quiz_name(self, obj):
        return obj.attempt.quiz.title
    
    quiz_name.short_description = 'Test'
    
    def question_preview(self, obj):
        text = obj.question.question_text[:50]
        if len(obj.question.question_text) > 50:
            text += '...'
        return text
    
    question_preview.short_description = 'Savol'
    
    def response_display(self, obj):
        """Javob ko'rsatish"""
        if not obj.selected_option:
            return format_html('<span style="color:#6B7280;">-</span>')
        
        if obj.attempt.quiz.is_psychological():
            return format_html(
                '<span style="color:#7C3AED;">{} ({} ball)</span>',
                obj.selected_option.option_text[:30],
                obj.earned_score
            )
        else:
            color = '#10B981' if obj.is_correct else '#EF4444'
            icon = '✓' if obj.is_correct else '✗'
            return format_html(
                '<span style="color:{};font-weight:bold;">{} {}</span>',
                color,
                icon,
                obj.selected_option.option_text[:30]
            )
    
    response_display.short_description = 'Javob'