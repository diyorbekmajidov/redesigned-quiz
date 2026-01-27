from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import (
    Quiz, Question, QuizAttempt, Result, 
    Option, UserResponse, QuestionText
)


# ============ INLINE CLASSES ============

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4
    fields = ['option_text', 'is_correct']


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ['question_text', 'score', 'order']
    readonly_fields = []
    show_change_link = True  # Question'ga o'tish uchun


class UserResponseInline(admin.TabularInline):
    model = UserResponse
    extra = 0
    readonly_fields = ['question', 'selected_option', 'is_correct', 'answered_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


# ============ ADMIN CLASSES ============

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = [
        'title', 
        'question_count',
        'time_limit', 
        'passing_score', 
        'is_active_display',
        'attempt_count',
        'created_by', 
        'created_at'
    ]
    list_filter = ['is_active', 'created_at', 'created_by']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [QuestionInline]
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('title', 'description', 'created_by', 'is_active')
        }),
        ('Sozlamalar', {
            'fields': ('time_limit', 'passing_score')
        }),
        ('Vaqt ma\'lumotlari', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Yangi yaratilayotgan bo'lsa
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def question_count(self, obj):
        count = obj.get_total_questions()
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    question_count.short_description = 'Savollar'
    
    def attempt_count(self, obj):
        count = obj.attempts.count()
        color = 'green' if count > 0 else 'gray'
        return format_html(
            '<span style="color: {};">{} ta</span>',
            color, count
        )
    attempt_count.short_description = 'Urinishlar'
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Faol</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Nofaol</span>'
        )
    is_active_display.short_description = 'Holat'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'question_text_short', 'score', 'order', 'option_count']
    list_filter = ['quiz', 'score']
    search_fields = ['question_text']
    inlines = [OptionInline]
    ordering = ['quiz', 'order']
    list_editable = ['order']  # Tartibni o'zgartirish uchun
    
    def question_text_short(self, obj):
        text = obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
        return format_html('<span title="{}">{}</span>', obj.question_text, text)
    question_text_short.short_description = 'Savol'
    
    def option_count(self, obj):
        count = obj.options.count()
        correct = obj.options.filter(is_correct=True).count()
        return format_html(
            '{} ta (✓ {})',
            count, correct
        )
    option_count.short_description = 'Variantlar'


@admin.register(QuestionText)
class QuestionTextAdmin(admin.ModelAdmin):
    """Bulk yuklash uchun admin"""
    list_display = ['quiz', 'is_processed', 'created_at', 'preview']
    list_filter = ['is_processed', 'quiz', 'created_at']
    search_fields = ['quiz__title']
    readonly_fields = ['is_processed', 'created_at']
    
    fieldsets = (
        ('Test tanlash', {
            'fields': ('quiz', 'score')
        }),
        ('Savollar', {
            'fields': ('question_text',),
            'description': '''
                <strong>Format:</strong><br>
                Savol matni?<br>
                =====<br>
                Variant 1<br>
                =====<br>
                Variant 2<br>
                =====<br>
                #To'g'ri variant (# belgisi bilan)<br>
                =====<br>
                Variant 4<br>
                +++++<br>
                Keyingi savol...
            '''
        }),
        ('Holat', {
            'fields': ('is_processed', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def preview(self, obj):
        text = obj.question_text[:100] + '...' if len(obj.question_text) > 100 else obj.question_text
        return text
    preview.short_description = 'Ko\'rinish'
    
    def has_change_permission(self, request, obj=None):
        # Qayta ishlangan QuestionText'ni tahrirlashga ruxsat bermaslik
        if obj and obj.is_processed:
            return False
        return super().has_change_permission(request, obj)


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['question_short', 'option_text', 'is_correct_display']
    search_fields = ['option_text', 'question__question_text']
    list_filter = ['is_correct', 'question__quiz']
    
    def question_short(self, obj):
        return f"{obj.question.quiz.title} - {obj.question.question_text[:30]}..."
    question_short.short_description = 'Savol'
    
    def is_correct_display(self, obj):
        if obj.is_correct:
            return format_html('<span style="color: green; font-weight: bold;">✓ To\'g\'ri</span>')
        return format_html('<span style="color: red;">✗ Noto\'g\'ri</span>')
    is_correct_display.short_description = 'Holat'


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'student_name',
        'quiz', 
        'status_display',
        'progress',
        'started_at', 
        'completed_at', 
        'time_taken_display'
    ]
    list_filter = ['status', 'quiz', 'started_at']
    search_fields = ['student__student_name', 'quiz__title']
    readonly_fields = ['started_at', 'completed_at', 'time_taken', 'status']
    inlines = [UserResponseInline]
    
    def student_name(self, obj):
        return obj.student.student_name
    student_name.short_description = 'Talaba'
    
    def status_display(self, obj):
        colors = {
            'in_progress': 'orange',
            'completed': 'green',
            'expired': 'red'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_display.short_description = 'Holat'
    
    def progress(self, obj):
        total = obj.quiz.get_total_questions()
        answered = obj.responses.count()
        percent = (answered / total * 100) if total > 0 else 0
        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background: #4CAF50; height: 20px; border-radius: 3px; '
            'text-align: center; color: white; font-size: 11px; line-height: 20px;">{}/{}</div>'
            '</div>',
            percent, answered, total
        )
    progress.short_description = 'Jarayon'
    
    def time_taken_display(self, obj):
        if obj.time_taken:
            minutes = obj.time_taken // 60
            seconds = obj.time_taken % 60
            return f"{minutes}m {seconds}s"
        elif obj.status == 'in_progress':
            return format_html('<span style="color: orange;">⏱ Davom etmoqda</span>')
        return '-'
    time_taken_display.short_description = 'Sarflangan vaqt'


@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = [
        'student_name',
        'question_short', 
        'selected_option', 
        'is_correct_display',
        'answered_at'
    ]
    list_filter = ['is_correct', 'answered_at', 'attempt__quiz']
    search_fields = [
        'attempt__student__student_name', 
        'question__question_text'
    ]
    readonly_fields = ['answered_at', 'is_correct']
    
    def student_name(self, obj):
        return obj.attempt.student.student_name
    student_name.short_description = 'Talaba'
    
    def question_short(self, obj):
        return obj.question.question_text[:50] + '...' if len(obj.question.question_text) > 50 else obj.question.question_text
    question_short.short_description = 'Savol'
    
    def is_correct_display(self, obj):
        if obj.is_correct:
            return format_html('<span style="color: green; font-weight: bold;">✓</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗</span>')
    is_correct_display.short_description = 'Natija'


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = [
        'student_name',
        'quiz_name', 
        'percentage_display',
        'grade_display',
        'passed_display',
        'correct_answers', 
        'total_questions', 
        'created_at'
    ]
    list_filter = ['passed', 'created_at', 'attempt__quiz']
    search_fields = [
        'attempt__student__student_name', 
        'attempt__quiz__title'
    ]
    readonly_fields = [
        'attempt', 'total_questions', 'correct_answers', 'wrong_answers',
        'unanswered', 'total_score', 'max_score', 'percentage', 
        'passed', 'created_at'
    ]
    
    def student_name(self, obj):
        return obj.attempt.student.student_name
    student_name.short_description = 'Talaba'
    
    def quiz_name(self, obj):
        return obj.attempt.quiz.title
    quiz_name.short_description = 'Test'
    
    def percentage_display(self, obj):
        color = 'green' if obj.passed else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, obj.percentage
        )
    percentage_display.short_description = 'Foiz'
    
    def grade_display(self, obj):
        grade = obj.get_grade()
        colors = {5: 'green', 4: 'blue', 3: 'orange', 2: 'red'}
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 16px;">{}</span>',
            colors.get(grade, 'gray'), grade
        )
    grade_display.short_description = 'Baho'
    
    def passed_display(self, obj):
        if obj.passed:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ O\'tdi</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ O\'tmadi</span>'
        )
    passed_display.short_description = 'Holat'
    
    def has_add_permission(self, request):
        return False  # Natijalar avtomatik yaratiladi