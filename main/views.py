from django.views.generic import TemplateView, ListView, DetailView
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Avg
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from collections import defaultdict
import json


class StudentLoginRequiredMixin:
    """Custom mixin - request.student borligini tekshirish"""
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, 'student') or not request.student:
            messages.warning(request, "Iltimos, tizimga kiring")
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


class HomeView(TemplateView):
    """Asosiy sahifa - Login qilmagan foydalanuvchilar uchun"""
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Psixologik Test Tizimi"
        
        # Testlar statistikasi (umumiy)
        from main.models import Quiz
        context['total_quizzes'] = Quiz.objects.filter(is_active=True).count()
        context['psychological_tests'] = Quiz.objects.filter(
            is_active=True,
            quiz_type='psychological'
        ).count()
        context['standard_tests'] = Quiz.objects.filter(
            is_active=True,
            quiz_type='standard'
        ).count()
        
        return context


class StudentDashboardView(StudentLoginRequiredMixin, TemplateView):
    """Student dashboard - Asosiy sahifa"""
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.student
        
        from main.models import Quiz, QuizAttempt, Result, PsychologicalResult
        
        # Student ma'lumotlari
        context['student'] = student
        
        # Mavjud testlar (faol)
        available_quizzes = Quiz.objects.filter(is_active=True).order_by('-created_at')[:6]
        context['available_quizzes'] = available_quizzes
        context['total_quizzes'] = Quiz.objects.filter(is_active=True).count()
        
        # Student urinishlari
        attempts = QuizAttempt.objects.filter(student=student)
        context['total_attempts'] = attempts.count()
        context['completed_attempts'] = attempts.filter(status='completed').count()
        
        # Joriy test (in_progress)
        in_progress = QuizAttempt.objects.filter(
            student=student,
            status='in_progress'
        ).select_related('quiz').first()
        context['current_attempt'] = in_progress
        
        # Standart testlar natijalari
        standard_results = Result.objects.filter(attempt__student=student)
        context['standard_results_count'] = standard_results.count()
        context['standard_passed_count'] = standard_results.filter(passed=True).count()
        context['standard_failed_count'] = standard_results.filter(passed=False).count()
        
        # Psixologik testlar natijalari
        psychological_results = PsychologicalResult.objects.filter(attempt__student=student)
        context['psychological_results_count'] = psychological_results.count()
        
        # O'rtacha ball (faqat standart testlar uchun)
        if standard_results.exists():
            avg_percentage = standard_results.aggregate(Avg('percentage'))['percentage__avg']
            context['average_percentage'] = round(avg_percentage, 2)
        else:
            context['average_percentage'] = 0
        
        # Oxirgi natijalar (aralash)
        recent_standard = list(standard_results.select_related(
            'attempt__quiz'
        ).order_by('-created_at')[:3])
        
        recent_psychological = list(psychological_results.select_related(
            'attempt__quiz'
        ).order_by('-created_at')[:2])
        
        # Aralashtirib, vaqt bo'yicha saralash
        all_recent = recent_standard + recent_psychological
        all_recent.sort(key=lambda x: x.created_at, reverse=True)
        context['recent_results'] = all_recent[:5]
        
        return context


class StudentProfileView(StudentLoginRequiredMixin, TemplateView):
    """Student profil sahifasi"""
    template_name = 'profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.student
        
        context['student'] = student
        
        # Qo'shimcha ma'lumotlar (agar qiz talaba bo'lsa)
        if hasattr(student, 'girl_details'):
            context['girl_details'] = student.girl_details
        
        # Guruhlar
        if student.group:
            context['group'] = student.group
        
        # Login tarixi
        from UserSession.models import LoginHistory
        context['login_history'] = LoginHistory.objects.filter(
            student=student
        ).order_by('-login_time')[:10]
        
        # Faol sessionlar
        from UserSession.models import UserSession
        context['active_sessions'] = UserSession.objects.filter(
            student=student,
            is_active=True
        ).order_by('-last_activity')
        
        # Test statistikasi
        from main.models import QuizAttempt
        total_attempts = QuizAttempt.objects.filter(student=student).count()
        completed = QuizAttempt.objects.filter(
            student=student,
            status='completed'
        ).count()
        
        context['total_attempts'] = total_attempts
        context['completed_attempts'] = completed
        
        return context


class QuizListView(StudentLoginRequiredMixin, ListView):
    """Barcha testlar ro'yxati"""
    template_name = 'quiz_list.html'
    context_object_name = 'quizzes'
    paginate_by = 12
    
    def get_queryset(self):
        from main.models import Quiz
        return Quiz.objects.filter(is_active=True).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.student
        
        # Har bir test uchun student urinishini qo'shish
        from main.models import QuizAttempt
        quizzes = context['quizzes']
        
        for quiz in quizzes:
            quiz.student_attempt = QuizAttempt.objects.filter(
                student=student,
                quiz=quiz
            ).order_by('-started_at').first()
        
        return context


class QuizDetailView(StudentLoginRequiredMixin, DetailView):
    """Test tafsilotlari"""
    template_name = 'quiz_detail.html'
    context_object_name = 'quiz'
    
    def get_object(self):
        from main.models import Quiz
        return get_object_or_404(Quiz, pk=self.kwargs['pk'], is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.student
        quiz = self.object
        
        from main.models import QuizAttempt, Result, PsychologicalResult
        
        # Student urinishlari
        attempts = QuizAttempt.objects.filter(
            student=student,
            quiz=quiz
        ).order_by('-started_at')
        
        context['attempts'] = attempts
        context['total_attempts'] = attempts.count()
        
        # Faol urinish
        current_attempt = attempts.filter(status='in_progress').first()
        context['current_attempt'] = current_attempt
        
        # Eng yaxshi natija
        best_result = None
        if quiz.is_standard():
            # Standart test
            if attempts.filter(status='completed').exists():
                best_result = Result.objects.filter(
                    attempt__in=attempts
                ).order_by('-percentage').first()
        else:
            # Psixologik test - so'nggi natija
            if attempts.filter(status='completed').exists():
                best_result = PsychologicalResult.objects.filter(
                    attempt__in=attempts
                ).order_by('-created_at').first()
        
        context['best_result'] = best_result
        context['is_psychological'] = quiz.is_psychological()
        
        # Urinish imkoni borligini tekshirish
        if quiz.is_standard():
            context['can_attempt'] = quiz.can_attempt(student)
        else:
            context['can_attempt'] = True  # Psixologik testlar uchun cheklov yo'q
        
        return context


class QuizTakeView(StudentLoginRequiredMixin, TemplateView):
    """Test topshirish"""
    template_name = 'take_quiz.html'
    
    def get(self, request, pk):
        from main.models import Quiz, QuizAttempt
        
        student = request.student
        quiz = get_object_or_404(Quiz, pk=pk, is_active=True)
        
        # Faol urinish borligini tekshirish
        attempt = QuizAttempt.objects.filter(
            student=student,
            quiz=quiz,
            status='in_progress'
        ).first()
        
        if not attempt:
            if not quiz.can_attempt(student):
                messages.error(
                    request,
                    f"Siz bu testga maksimal urinishlar soniga ({quiz.attempt_limit}) yetdingiz. "
                    f"Boshqa urinish qila olmaysiz."
                )
                return redirect('quiz_detail', pk=quiz.pk)
            
            attempt = QuizAttempt.objects.create(
                student=student,
                quiz=quiz
            )
            messages.success(request, f"Test boshlandi: {quiz.title}")
        
        if attempt.is_time_expired():
            attempt.expire_attempt()
            messages.warning(request, "Vaqt tugadi! Test avtomatik yakunlandi.")
            return redirect('quiz_result', attempt_id=attempt.id)
        
        questions = quiz.questions.prefetch_related('options').order_by('order')
        
        from main.models import UserResponse
        responses = {
            r.question_id: r.selected_option_id
            for r in UserResponse.objects.filter(attempt=attempt)
        }
        
        context = {
            'quiz': quiz,
            'attempt': attempt,
            'questions': questions,
            'responses': responses,
            'remaining_time': attempt.get_remaining_time(),
            'total_questions': questions.count(),
            'answered_count': len(responses),
            'is_psychological': quiz.is_psychological(),
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        """Javoblarni saqlash"""
        from main.models import Quiz, QuizAttempt, Question, Option, UserResponse
        
        student = request.student
        quiz = get_object_or_404(Quiz, pk=pk)
        
        # Faol urinishni topish
        attempt = QuizAttempt.objects.filter(
            student=student,
            quiz=quiz,
            status='in_progress'
        ).first()
        
        if not attempt:
            return JsonResponse({
                'error': 'Urinish topilmadi'
            }, status=404)
        
        # Vaqt tugaganligini tekshirish
        if attempt.is_time_expired():
            attempt.expire_attempt()
            return JsonResponse({
                'error': 'Vaqt tugadi',
                'redirect': f'/quiz/{attempt.id}/result/'
            }, status=400)
        
        # Javoblarni saqlash
        action = request.POST.get('action', 'save')
        saved_count = 0
        
        for key, value in request.POST.items():
            if key.startswith('question_'):
                question_id = key.split('_')[1]
                option_id = value
                
                if not option_id:
                    continue
                
                try:
                    question = Question.objects.get(id=question_id, quiz=quiz)
                    option = Option.objects.get(id=option_id, question=question)
                    
                    UserResponse.objects.update_or_create(
                        attempt=attempt,
                        question=question,
                        defaults={'selected_option': option}
                    )
                    saved_count += 1
                    
                except (Question.DoesNotExist, Option.DoesNotExist):
                    continue
        
        # Agar "Yakunlash" bosilgan bo'lsa
        if action == 'submit':
            attempt.complete_attempt()
            messages.success(request, "Test muvaffaqiyatli yakunlandi!")
            return redirect('quiz_result', attempt_id=attempt.id)
        
        # Agar "Saqlash" bosilgan bo'lsa
        return JsonResponse({
            'success': True,
            'message': f'{saved_count} ta javob saqlandi',
            'saved_count': saved_count
        })


class QuizResultView(StudentLoginRequiredMixin, DetailView):
    """Test natijasi - Standart va Psixologik"""
    template_name = 'result.html'
    context_object_name = 'attempt'
    
    def get_object(self):
        from main.models import QuizAttempt
        attempt_id = self.kwargs['attempt_id']
        return get_object_or_404(
            QuizAttempt.objects.select_related('quiz', 'student'),
            id=attempt_id,
            student=self.request.student
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempt = self.object
        quiz = attempt.quiz
        
        from main.models import UserResponse
        
        context['quiz'] = quiz
        context['is_psychological'] = quiz.is_psychological()
        
        if quiz.is_standard():
            context['result'] = attempt.result
            responses = UserResponse.objects.filter(
                attempt=attempt
            ).select_related(
                'question',
                'selected_option'
            ).order_by('question__order')
            
            context['responses'] = responses
            
            correct_count = responses.filter(is_correct=True).count()
            wrong_count = responses.filter(
                is_correct=False,
                selected_option__isnull=False
            ).count()
            total_questions = quiz.get_total_questions()
            unanswered = total_questions - responses.count()
            
            context['correct_count'] = correct_count
            context['wrong_count'] = wrong_count
            context['unanswered_count'] = unanswered
            context['total_questions'] = total_questions
            
        else:
            from main.models import PsychologicalScaleResult
            
            psychological_result = attempt.psychological_result
            context['psychological_result'] = psychological_result
            
            scale_results = PsychologicalScaleResult.objects.filter(
                result=psychological_result
            ).select_related('scale', 'category')
            
            context['scale_results'] = scale_results
            
            responses = UserResponse.objects.filter(
                attempt=attempt
            ).select_related(
                'question',
                'question__psychological_scale',
                'selected_option'
            ).order_by('question__order')
            
            context['responses'] = responses
            
            total_questions = quiz.get_total_questions()
            answered = responses.count()
            unanswered = total_questions - answered
            
            context['total_questions'] = total_questions
            context['answered_count'] = answered
            context['unanswered_count'] = unanswered
        
        return context


class ResultsHistoryView(StudentLoginRequiredMixin, ListView):
    """Barcha natijalar tarixi"""
    template_name = 'results_history.html'
    context_object_name = 'results'
    paginate_by = 10
    
    def get_queryset(self):
        from main.models import QuizAttempt
        
        return QuizAttempt.objects.filter(
            student=self.request.student,
            status='completed'
        ).select_related('quiz').order_by('-completed_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from main.models import Result, PsychologicalResult
        
        standard_results = Result.objects.filter(
            attempt__student=self.request.student
        )
        
        if standard_results.exists():
            context['total_standard_tests'] = standard_results.count()
            context['passed_tests'] = standard_results.filter(passed=True).count()
            context['failed_tests'] = standard_results.filter(passed=False).count()
            context['average_score'] = round(
                standard_results.aggregate(Avg('percentage'))['percentage__avg'],
                2
            )
        else:
            context['total_standard_tests'] = 0
            context['passed_tests'] = 0
            context['failed_tests'] = 0
            context['average_score'] = 0
        
        psychological_results = PsychologicalResult.objects.filter(
            attempt__student=self.request.student
        )
        context['total_psychological_tests'] = psychological_results.count()
        
        return context


class StudentStatisticsView(StudentLoginRequiredMixin, TemplateView):
    """Student statistikasi - Standart testlar uchun"""
    template_name = 'statistics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.student
        
        from main.models import Result
        
        results = Result.objects.filter(
            attempt__student=student
        ).select_related('attempt__quiz').order_by('created_at')
        
        chart_data = {
            'labels': [],
            'scores': [],
            'passed': []
        }
        
        for result in results:
            quiz_title = result.attempt.quiz.title
            short_title = (quiz_title[:20] + '...') if len(quiz_title) > 20 else quiz_title
            
            chart_data['labels'].append(short_title)
            chart_data['scores'].append(float(result.percentage))
            chart_data['passed'].append(1 if result.passed else 0)
        
        context['chart_data'] = json.dumps(chart_data)
        
        context['total_tests'] = results.count()
        context['passed_tests'] = results.filter(passed=True).count()
        context['failed_tests'] = results.filter(passed=False).count()
        
        if results.exists():
            context['average_score'] = round(
                results.aggregate(Avg('percentage'))['percentage__avg'],
                2
            )
            context['highest_score'] = results.order_by('-percentage').first()
            context['lowest_score'] = results.order_by('percentage').first()
        else:
            context['average_score'] = 0
            context['highest_score'] = None
            context['lowest_score'] = None
        
        from main.models import PsychologicalResult
        context['psychological_tests_count'] = PsychologicalResult.objects.filter(
            attempt__student=student
        ).count()
        
        return context


class PsychologicalTestsView(StudentLoginRequiredMixin, ListView):
    """Faqat psixologik testlar"""
    template_name = 'psychological_tests.html'
    context_object_name = 'quizzes'
    paginate_by = 12
    
    def get_queryset(self):
        from main.models import Quiz
        return Quiz.objects.filter(
            is_active=True,
            quiz_type='psychological'
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.student
        
        # Har bir test uchun student urinishini qo'shish
        from main.models import QuizAttempt
        quizzes = context['quizzes']
        
        for quiz in quizzes:
            quiz.student_attempt = QuizAttempt.objects.filter(
                student=student,
                quiz=quiz
            ).order_by('-started_at').first()
        
        return context


class PsychologicalResultsView(StudentLoginRequiredMixin, ListView):
    """Psixologik testlar natijalari"""
    template_name = 'psychological_results.html'
    context_object_name = 'results'
    paginate_by = 10
    
    def get_queryset(self):
        from main.models import PsychologicalResult
        
        return PsychologicalResult.objects.filter(
            attempt__student=self.request.student
        ).select_related('attempt__quiz').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Har bir natija uchun shkalalarni qo'shish
        from main.models import PsychologicalScaleResult
        
        for result in context['results']:
            result.scale_results_list = PsychologicalScaleResult.objects.filter(
                result=result
            ).select_related('scale', 'category')
        
        return context


# =========================================================
#  ADMIN: Psixologik natijalar statistikasi (grafiklar)
# =========================================================

@method_decorator(staff_member_required, name='dispatch')
class AdminPsychologicalStatisticsView(TemplateView):
    """
    Admin panel uchun psixologik natijalar statistikasi
    - Rang taqsimoti donut chart
    - Vaqt bo'yicha stacked bar
    - Shkalalar bo'yicha horizontal bar
    - Fakultet va guruh bo'yicha grafiklar
    """
    template_name = 'admin_psychological_stats.html'

    # ─── Rang ikonlari ───
    COLOR_ICONS = {
        'green': '🟢',
        'yellow': '🟡',
        'orange': '🟠',
        'red': '🔴',
    }
    COLOR_LABELS = {
        'green': 'Yashil',
        'yellow': 'Sariq',
        'orange': "To'q sariq",
        'red': 'Qizil',
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from main.models import (
            PsychologicalResult, PsychologicalScaleResult,
            Quiz
        )
        from student.models import Student, StudentGroup

        # ── GET params ──
        selected_quiz_id  = self.request.GET.get('quiz', '')
        selected_faculty  = self.request.GET.get('faculty', '')
        selected_group_id = self.request.GET.get('group', '')

        # ── Base queryset ──
        qs = PsychologicalResult.objects.select_related(
            'attempt__student__group',
            'attempt__quiz',
        ).prefetch_related(
            'scale_results__category',
            'scale_results__scale',
        ).order_by('-created_at')

        if selected_quiz_id:
            qs = qs.filter(attempt__quiz__id=selected_quiz_id)
        if selected_faculty:
            qs = qs.filter(attempt__student__faculty=selected_faculty)
        if selected_group_id:
            qs = qs.filter(attempt__student__group__id=selected_group_id)

        total_results = qs.count()

        # ── Color counts ──
        color_counts = defaultdict(int)
        for result in qs:
            for sr in result.scale_results.all():
                if sr.category:
                    color_counts[sr.category.color] += 1

        total_color = sum(color_counts.values()) or 1

        def pct(val):
            return round(val / total_color * 100, 1)

        # ── Color chart data (donut) ──
        color_chart_data = {
            'labels': ['Yashil', 'Sariq', "To'q sariq", 'Qizil'],
            'values': [
                color_counts['green'],
                color_counts['yellow'],
                color_counts['orange'],
                color_counts['red'],
            ],
            'percentages': [
                pct(color_counts['green']),
                pct(color_counts['yellow']),
                pct(color_counts['orange']),
                pct(color_counts['red']),
            ],
        }

        # ── Timeline data (last 10 months) ──
        from django.utils import timezone
        from datetime import timedelta

        timeline_labels = []
        tl_green = []
        tl_yellow = []
        tl_orange = []
        tl_red = []

        now = timezone.now()
        for i in range(9, -1, -1):
            month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            if i == 0:
                month_end = now
            else:
                next_month = (month_start.replace(day=28) + timedelta(days=4))
                month_end = next_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            label = month_start.strftime('%b %Y')
            timeline_labels.append(label)

            month_qs = qs.filter(created_at__gte=month_start, created_at__lt=month_end)

            mc = defaultdict(int)
            for r in month_qs.prefetch_related('scale_results__category'):
                for sr in r.scale_results.all():
                    if sr.category:
                        mc[sr.category.color] += 1

            tl_green.append(mc['green'])
            tl_yellow.append(mc['yellow'])
            tl_orange.append(mc['orange'])
            tl_red.append(mc['red'])

        timeline_chart_data = {
            'labels': timeline_labels,
            'green': tl_green,
            'yellow': tl_yellow,
            'orange': tl_orange,
            'red': tl_red,
        }

        # ── Scale stats ──
        quizzes_qs = Quiz.objects.filter(quiz_type='psychological')
        if selected_quiz_id:
            quizzes_qs = quizzes_qs.filter(id=selected_quiz_id)

        scale_stats = []
        scale_bar_labels = []
        scale_bar_avg = []

        for quiz in quizzes_qs:
            for scale in quiz.psychological_scales.prefetch_related('categories').all():
                sr_qs = PsychologicalScaleResult.objects.filter(
                    scale=scale,
                    result__in=qs,
                ).select_related('category')

                total_sr = sr_qs.count()
                if total_sr == 0:
                    continue

                avg_score = sr_qs.aggregate(a=Avg('total_score'))['a'] or 0
                scale_bar_labels.append(f"{scale.name[:25]}")
                scale_bar_avg.append(round(avg_score, 1))

                cat_counts = defaultdict(int)
                for sr in sr_qs:
                    cat_name = sr.category.name if sr.category else 'Nomalum'
                    cat_color = sr.category.color if sr.category else 'none'
                    cat_counts[(cat_name, cat_color)] += 1

                cat_stats_list = []
                for (name, color), count in sorted(cat_counts.items(), key=lambda x: -x[1]):
                    cat_stats_list.append({
                        'category_name': name,
                        'color': color,
                        'count': count,
                        'pct': round(count / total_sr * 100, 1),
                    })

                scale_stats.append({
                    'scale_name': scale.name,
                    'total_results': total_sr,
                    'avg_score': round(avg_score, 1),
                    'category_stats': cat_stats_list,
                })

        scale_chart_data = {
            'labels': scale_bar_labels,
            'avg_scores': scale_bar_avg,
        }

        # ── Faculty stats ──
        faculties_list = list(
            Student.objects.values_list('faculty', flat=True)
            .distinct().exclude(faculty__isnull=True).exclude(faculty='')
        )
        faculty_labels = []
        fac_green = []; fac_yellow = []; fac_orange = []; fac_red = []

        for faculty in faculties_list:
            fac_qs = qs.filter(attempt__student__faculty=faculty)
            if not fac_qs.exists():
                continue
            fmc = defaultdict(int)
            for r in fac_qs.prefetch_related('scale_results__category'):
                for sr in r.scale_results.all():
                    if sr.category:
                        fmc[sr.category.color] += 1
            if sum(fmc.values()) == 0:
                continue
            short = faculty[:15] + '…' if len(faculty) > 15 else faculty
            faculty_labels.append(short)
            fac_green.append(fmc['green'])
            fac_yellow.append(fmc['yellow'])
            fac_orange.append(fmc['orange'])
            fac_red.append(fmc['red'])

        faculty_chart_data = {
            'labels': faculty_labels,
            'green': fac_green,
            'yellow': fac_yellow,
            'orange': fac_orange,
            'red': fac_red,
        }
        faculty_stats = bool(faculty_labels)

        # ── Group stats ──
        groups_qs = StudentGroup.objects.all()
        group_labels = []; group_values = []
        for g in groups_qs:
            cnt = qs.filter(attempt__student__group=g).count()
            if cnt > 0:
                group_labels.append(g.group_name[:12])
                group_values.append(cnt)

        group_chart_data = {
            'labels': group_labels,
            'values': group_values,
        }

        # ── Recent results (last 30) ──
        recent_list = []
        for r in qs[:30]:
            student = r.attempt.student
            grp = student.group

            tags = []
            for sr in r.scale_results.all():
                if sr.category:
                    tags.append({
                        'color': sr.category.color,
                        'icon': self.COLOR_ICONS.get(sr.category.color, '⚪'),
                        'label': sr.category.name,
                    })

            recent_list.append({
                'id': r.id,
                'student_name': student.student_name or '-',
                'faculty': student.faculty or '-',
                'group_name': grp.group_name if grp else '-',
                'quiz_title': r.attempt.quiz.title,
                'color_tags': tags[:4],
                'created_at': r.created_at.strftime('%d.%m.%Y %H:%M') if r.created_at else '-',
            })

        # ── Filter selects ──
        context.update({
            # filter options
            'quizzes': Quiz.objects.filter(quiz_type='psychological', is_active=True),
            'faculties': faculties_list,
            'groups': StudentGroup.objects.all(),
            # selected values
            'selected_quiz_id': selected_quiz_id,
            'selected_faculty': selected_faculty,
            'selected_group_id': selected_group_id,
            # summary
            'total_results': total_results,
            'color_counts': dict(color_counts),
            'green_pct': pct(color_counts['green']),
            'yellow_pct': pct(color_counts['yellow']),
            'orange_pct': pct(color_counts['orange']),
            'red_pct': pct(color_counts['red']),
            # chart JSON
            'color_chart_data': json.dumps(color_chart_data),
            'timeline_chart_data': json.dumps(timeline_chart_data),
            'scale_chart_data': json.dumps(scale_chart_data),
            'faculty_chart_data': json.dumps(faculty_chart_data),
            'group_chart_data': json.dumps(group_chart_data),
            'timeline_labels': timeline_labels,
            # scale cards
            'scale_stats': scale_stats,
            'faculty_stats': faculty_stats,
            # table
            'recent_results': recent_list,
        })
        return context