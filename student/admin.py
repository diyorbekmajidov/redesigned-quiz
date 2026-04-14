from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import Student, StudentGirls, StudentGroup


# ─────────────────────────────────────────────
# StudentsGroup Admin
# ─────────────────────────────────────────────
class StudentGroupsAdmin(admin.ModelAdmin):
    list_display = (
        'group_name', 'group_code', 'get_student_count',
        'group_faculty', 'group_level', 'group_year'
    )
    search_fields = ('group_name', 'group_code')
    list_filter = ('group_faculty', 'group_level', 'group_year')


# ─────────────────────────────────────────────
# StudentGirls Admin
# ─────────────────────────────────────────────
class StudentGirlsAdmin(admin.ModelAdmin):
    list_display = ('place_of_birth', 'current_address', 'marital_status', 'pregnancy_status')
    search_fields = ('place_of_birth', 'current_address')
    list_filter = ('marital_status', 'ethics_status', 'orphan_status')


# ─────────────────────────────────────────────
# Student Admin
# ─────────────────────────────────────────────
class StudentAdmin(admin.ModelAdmin):
    change_form_template = 'admin/student/student/change_form.html'

    list_display = (
        'photo_thumbnail',
        'student_name',
        'student_id_number',
        'faculty',
        'group_display',
        'level',
        'gender_display',
        'tests_count_display',
        'overall_result_display',
    )

    search_fields = ('student_name', 'student_id_number', 'email', 'hemis_id')
    list_filter = ('faculty', 'level', 'gender', 'studentStatus', 'group')
    readonly_fields = ('date_created', 'date_update')

    fieldsets = (
        ("📋 Asosiy Ma'lumotlar", {
            'fields': (
                'student_name', 'student_id_number', 'hemis_id',
                'email', 'phone_number', 'student_imeg',
            )
        }),
        ("🎓 Ta'lim Ma'lumotlari", {
            'fields': (
                'faculty', 'group', 'level', 'semester',
                'education_type', 'paymentForm', 'avg_gpa',
            )
        }),
        ("👤 Shaxsiy Ma'lumotlar", {
            'fields': (
                'gender', 'birth_date', 'passport_number',
                'studentStatus',
            )
        }),
        ("🕐 Sistema", {
            'fields': ('date_created', 'date_update'),
            'classes': ('collapse',),
        }),
    )

    # ── List display helpers ──────────────────

    def photo_thumbnail(self, obj):
        if obj.student_imeg:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;border-radius:50%;'
                'object-fit:cover;border:2px solid #7C3AED;" />',
                obj.student_imeg
            )
        initials = (obj.student_name or 'T')[:1].upper()
        return format_html(
            '<div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#7C3AED,#6D28D9);'
            'display:flex;align-items:center;justify-content:center;'
            'color:white;font-weight:bold;font-size:16px;">{}</div>',
            initials
        )

    photo_thumbnail.short_description = ''

    def group_display(self, obj):
        if obj.group:
            return format_html(
                '<span style="background:#EDE9FE;color:#7C3AED;padding:2px 8px;'
                'border-radius:10px;font-size:12px;font-weight:600;">{}</span>',
                obj.group.group_name
            )
        return '-'

    group_display.short_description = 'Guruh'

    def gender_display(self, obj):
        if obj.gender in ('female', 'ayol', 'Ayol', 'F'):
            return format_html('<span style="color:#EC4899;">♀ Ayol</span>')
        elif obj.gender in ('male', 'erkak', 'Erkak', 'M'):
            return format_html('<span style="color:#3B82F6;">♂ Erkak</span>')
        return obj.gender or '-'

    gender_display.short_description = 'Jins'

    def tests_count_display(self, obj):
        """Talaba topshirgan testlar soni"""
        from main.models import QuizAttempt
        count = QuizAttempt.objects.filter(
            student=obj, status='completed'
        ).count()
        if count == 0:
            return format_html('<span style="color:#9CA3AF;">0 ta</span>')
        return format_html(
            '<span style="background:#DBEAFE;color:#1D4ED8;padding:2px 8px;'
            'border-radius:10px;font-weight:600;">{} ta</span>',
            count
        )

    tests_count_display.short_description = 'Testlar'

    def overall_result_display(self, obj):
        """Umumiy natija (psixologik + standart, eng yomon rang bo'yicha)"""
        from main.models import PsychologicalScaleResult, Result, QuizAttempt

        COLOR_PRIORITY = {'red': 0, 'orange': 1, 'yellow': 2, 'green': 3}
        COLOR_HEX = {
            'red': ('#FEE2E2', '#EF4444', '🔴', 'Qizil'),
            'orange': ('#FFEDD5', '#F97316', '🟠', "To'q sariq"),
            'yellow': ('#FEF9C3', '#CA8A04', '🟡', 'Sariq'),
            'green': ('#DCFCE7', '#16A34A', '🟢', 'Yashil'),
        }

        # Psixologik natijalar
        scale_results = PsychologicalScaleResult.objects.filter(
            result__attempt__student=obj
        ).select_related('category')

        worst_color = None
        for sr in scale_results:
            if sr.category:
                c = sr.category.color
                if worst_color is None or COLOR_PRIORITY.get(c, 99) < COLOR_PRIORITY.get(worst_color, 99):
                    worst_color = c

        if worst_color and worst_color in COLOR_HEX:
            bg, text, icon, label = COLOR_HEX[worst_color]
            return format_html(
                '<span style="background:{};color:{};padding:3px 10px;'
                'border-radius:12px;font-weight:600;font-size:12px;">{} {}</span>',
                bg, text, icon, label
            )

        # Standart test natijalari
        std_results = Result.objects.filter(attempt__student=obj)
        if std_results.exists():
            avg = std_results.aggregate(Avg('percentage'))['percentage__avg'] or 0
            if avg >= 86:
                bg, text, icon, label = '#DCFCE7', '#16A34A', '🟢', "A'lo"
            elif avg >= 71:
                bg, text, icon, label = '#DBEAFE', '#1D4ED8', '🔵', 'Yaxshi'
            elif avg >= 56:
                bg, text, icon, label = '#FEF9C3', '#CA8A04', '🟡', "Qoniqarli"
            else:
                bg, text, icon, label = '#FEE2E2', '#EF4444', '🔴', "Qoniqarsiz"
            return format_html(
                '<span style="background:{};color:{};padding:3px 10px;'
                'border-radius:12px;font-weight:600;font-size:12px;">{} {}</span>',
                bg, text, icon, label
            )

        return format_html('<span style="color:#9CA3AF;font-size:12px;">— Test yo\'q</span>')

    overall_result_display.short_description = 'Umumiy natija'

    # ── Change form extra context ─────────────

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        try:
            student = Student.objects.get(pk=object_id)
            extra_context['quiz_results'] = self._get_quiz_results(student)
            extra_context['overall_summary'] = self._get_overall_summary(student)
        except Student.DoesNotExist:
            pass
        return super().change_view(request, object_id, form_url, extra_context)

    def _get_quiz_results(self, student):
        """Talabaning barcha test natijalarini qaytaradi"""
        from main.models import QuizAttempt, Result, PsychologicalScaleResult

        results = []
        attempts = QuizAttempt.objects.filter(
            student=student, status='completed'
        ).select_related('quiz').order_by('-completed_at')

        COLOR_HEX = {
            'red': ('#FEE2E2', '#EF4444', '🔴', 'Qizil'),
            'orange': ('#FFEDD5', '#F97316', '🟠', "To'q sariq"),
            'yellow': ('#FEF9C3', '#CA8A04', '🟡', 'Sariq'),
            'green': ('#DCFCE7', '#16A34A', '🟢', 'Yashil'),
        }
        COLOR_PRIORITY = {'red': 0, 'orange': 1, 'yellow': 2, 'green': 3}

        for attempt in attempts:
            quiz = attempt.quiz
            entry = {
                'attempt_id': attempt.id,
                'quiz_title': quiz.title,
                'quiz_type': 'psychological' if quiz.is_psychological() else 'standard',
                'completed_at': attempt.completed_at,
                'scales': [],
                'standard': None,
                'worst_color': None,
                'worst_bg': '#F3F4F6',
                'worst_text': '#6B7280',
                'worst_icon': '⚪',
                'worst_label': '—',
            }

            if quiz.is_psychological():
                try:
                    psy_result = attempt.psychological_result
                    scale_results = PsychologicalScaleResult.objects.filter(
                        result=psy_result
                    ).select_related('scale', 'category')

                    worst = None
                    for sr in scale_results:
                        cat = sr.category
                        color_info = COLOR_HEX.get(cat.color, ('#F3F4F6', '#6B7280', '⚪', cat.name)) if cat else None
                        entry['scales'].append({
                            'scale_name': sr.scale.name,
                            'score': sr.total_score,
                            'category_name': cat.name if cat else '—',
                            'color': cat.color if cat else 'none',
                            'bg': color_info[0] if color_info else '#F3F4F6',
                            'text': color_info[1] if color_info else '#6B7280',
                            'icon': color_info[2] if color_info else '⚪',
                        })
                        if cat and (worst is None or COLOR_PRIORITY.get(cat.color, 99) < COLOR_PRIORITY.get(worst, 99)):
                            worst = cat.color

                    if worst and worst in COLOR_HEX:
                        bg, text, icon, label = COLOR_HEX[worst]
                        entry.update(
                            worst_color=worst,
                            worst_bg=bg,
                            worst_text=text,
                            worst_icon=icon,
                            worst_label=label,
                        )
                except Exception:
                    pass

            else:
                try:
                    std = attempt.result
                    pct = float(std.percentage)
                    grade = std.get_grade()
                    passed = std.passed
                    if pct >= 86:
                        bg, text, icon, label = '#DCFCE7', '#16A34A', '🟢', f"A'lo ({grade})"
                    elif pct >= 71:
                        bg, text, icon, label = '#DBEAFE', '#1D4ED8', '🔵', f'Yaxshi ({grade})'
                    elif pct >= 56:
                        bg, text, icon, label = '#FEF9C3', '#CA8A04', '🟡', f'Qoniqarli ({grade})'
                    else:
                        bg, text, icon, label = '#FEE2E2', '#EF4444', '🔴', f'Qoniqarsiz ({grade})'
                    entry['standard'] = {
                        'percentage': round(pct, 1),
                        'grade': grade,
                        'passed': passed,
                        'correct': std.correct_answers,
                        'wrong': std.wrong_answers,
                        'total': std.total_questions,
                    }
                    entry.update(
                        worst_bg=bg,
                        worst_text=text,
                        worst_icon=icon,
                        worst_label=label,
                    )
                except Exception:
                    pass

            results.append(entry)

        return results

    def _get_overall_summary(self, student):
        """Umumiy natija summarysi"""
        from main.models import PsychologicalScaleResult, Result, QuizAttempt

        COLOR_PRIORITY = {'red': 0, 'orange': 1, 'yellow': 2, 'green': 3}
        color_counts = {'green': 0, 'yellow': 0, 'orange': 0, 'red': 0}

        scale_results = PsychologicalScaleResult.objects.filter(
            result__attempt__student=student
        ).select_related('category')

        worst_color = None
        for sr in scale_results:
            if sr.category:
                c = sr.category.color
                if c in color_counts:
                    color_counts[c] += 1
                if worst_color is None or COLOR_PRIORITY.get(c, 99) < COLOR_PRIORITY.get(worst_color, 99):
                    worst_color = c

        total_psy = sum(color_counts.values())
        std_results = Result.objects.filter(attempt__student=student)
        total_std = std_results.count()
        avg_pct = None
        if std_results.exists():
            avg_pct = round(
                std_results.aggregate(Avg('percentage'))['percentage__avg'] or 0, 1
            )

        completed = QuizAttempt.objects.filter(student=student, status='completed').count()

        COLOR_HEX = {
            'red': ('#FEE2E2', '#EF4444', '🔴', 'Qizil - Yordam talab etadi'),
            'orange': ('#FFEDD5', '#F97316', '🟠', "To'q sariq - Diqqat talab etadi"),
            'yellow': ('#FEF9C3', '#CA8A04', '🟡', 'Sariq - Kuzatish zarur'),
            'green': ('#DCFCE7', '#16A34A', '🟢', 'Yashil - Muammo yo\'q'),
        }

        overall = None
        if worst_color and worst_color in COLOR_HEX:
            bg, text, icon, label = COLOR_HEX[worst_color]
            overall = {'bg': bg, 'text': text, 'icon': icon, 'label': label}
        elif avg_pct is not None:
            if avg_pct >= 86:
                overall = {'bg': '#DCFCE7', 'text': '#16A34A', 'icon': '🟢', 'label': "A'lo daraja"}
            elif avg_pct >= 71:
                overall = {'bg': '#DBEAFE', 'text': '#1D4ED8', 'icon': '🔵', 'label': 'Yaxshi daraja'}
            elif avg_pct >= 56:
                overall = {'bg': '#FEF9C3', 'text': '#CA8A04', 'icon': '🟡', 'label': 'Qoniqarli daraja'}
            else:
                overall = {'bg': '#FEE2E2', 'text': '#EF4444', 'icon': '🔴', 'label': 'Qoniqarsiz daraja'}

        return {
            'total_tests': completed,
            'psy_tests': total_psy,
            'std_tests': total_std,
            'avg_percentage': avg_pct,
            'color_counts': color_counts,
            'overall': overall,
        }


admin.site.register(Student, StudentAdmin)
admin.site.register(StudentGirls, StudentGirlsAdmin)
admin.site.register(StudentGroup, StudentGroupsAdmin)
