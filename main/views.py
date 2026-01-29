"""
Student Portal Views - grant.uzfi.uz kabi
"""
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Avg, Q
from django.utils import timezone


class StudentLoginRequiredMixin:
    """Custom mixin - request.student borligini tekshirish"""
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, 'student') or not request.student:
            return redirect('auth:login')
        return super().dispatch(request, *args, **kwargs)


class HomeView(TemplateView):
    """Asosiy sahifa - Login qilmagan foydalanuvchilar uchun"""
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Psixologik Test Tizimi"
        return context


class StudentDashboardView(StudentLoginRequiredMixin, TemplateView):
    """Student dashboard - Asosiy sahifa"""
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.student
        
        # Student ma'lumotlari
        context['student'] = student
        
        # Statistika
        from main.models import Quiz, QuizAttempt, Result
        
        # Mavjud testlar
        available_quizzes = Quiz.objects.filter(is_active=True)
        context['available_quizzes'] = available_quizzes
        context['total_quizzes'] = available_quizzes.count()
        
        # Student urinishlari
        attempts = QuizAttempt.objects.filter(student=student)
        context['total_attempts'] = attempts.count()
        context['completed_attempts'] = attempts.filter(status='completed').count()
        context['in_progress_attempts'] = attempts.filter(status='in_progress')
        
        # Natijalar
        results = Result.objects.filter(attempt__student=student)
        context['total_results'] = results.count()
        context['passed_count'] = results.filter(passed=True).count()
        context['failed_count'] = results.filter(passed=False).count()
        
        # O'rtacha ball
        if results.exists():
            avg_percentage = results.aggregate(Avg('percentage'))['percentage__avg']
            context['average_percentage'] = round(avg_percentage, 2)
        else:
            context['average_percentage'] = 0
        
        # Oxirgi natijalar
        context['recent_results'] = results.select_related(
            'attempt__quiz'
        ).order_by('-created_at')[:5]
        
        # Joriy test (agar mavjud bo'lsa)
        in_progress = QuizAttempt.objects.filter(
            student=student,
            status='in_progress'
        ).select_related('quiz').first()
        context['current_attempt'] = in_progress
        
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
        context['groups'] = student.group
        
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
        
        return context


class QuizListView(StudentLoginRequiredMixin, ListView):
    """Barcha testlar ro'yxati"""
    model = None  # Keyin qo'shamiz
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
        
        # Student urinishlari
        from main.models import QuizAttempt
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
        if attempts.filter(status='completed').exists():
            from main.models import Result
            best_result = Result.objects.filter(
                attempt__in=attempts
            ).order_by('-percentage').first()
        
        context['best_result'] = best_result
        
        return context


class QuizTakeView(StudentLoginRequiredMixin, TemplateView):
    """Test topshirish"""
    template_name = 'take_quiz.html'
    
    def get(self, request, pk):
        from main.models import Quiz, QuizAttempt, Question
        
        student = request.student
        quiz = get_object_or_404(Quiz, pk=pk, is_active=True)
        
        # Faol urinish borligini tekshirish
        attempt = QuizAttempt.objects.filter(
            student=student,
            quiz=quiz,
            status='in_progress'
        ).first()
        
        if not attempt:
            # Yangi urinish yaratish
            attempt = QuizAttempt.objects.create(
                student=student,
                quiz=quiz
            )
        
        # Vaqt tugaganligini tekshirish
        if attempt.is_time_expired():
            attempt.expire_attempt()
            return redirect('quiz:result', attempt_id=attempt.id)
        
        # Savollar (random tartibda)
        questions = quiz.questions.prefetch_related('options').order_by('order')
        
        # Student javoblari
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
            'answered_count': len(responses)
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
                except (Question.DoesNotExist, Option.DoesNotExist):
                    continue
        
        # Agar "Yakunlash" bosilgan bo'lsa
        if action == 'submit':
            attempt.complete_attempt()
            return redirect('result', attempt_id=attempt.id)
        
        # Agar "Saqlash" bosilgan bo'lsa
        return JsonResponse({
            'success': True,
            'message': 'Javoblar saqlandi'
        })


class QuizResultView(StudentLoginRequiredMixin, DetailView):
    """Test natijasi"""
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
        
        # Natija
        context['result'] = attempt.result
        
        # Barcha javoblar
        from main.models import UserResponse
        responses = UserResponse.objects.filter(
            attempt=attempt
        ).select_related('question', 'selected_option').order_by('question__order')
        
        context['responses'] = responses
        
        # Statistika
        correct_count = responses.filter(is_correct=True).count()
        wrong_count = responses.filter(is_correct=False, selected_option__isnull=False).count()
        total_questions = attempt.quiz.get_total_questions()
        unanswered = total_questions - responses.count()
        
        context['correct_count'] = correct_count
        context['wrong_count'] = wrong_count
        context['unanswered_count'] = unanswered
        context['total_questions'] = total_questions
        
        return context


class ResultsHistoryView(StudentLoginRequiredMixin, ListView):
    """Barcha natijalar tarixi"""
    template_name = 'results_history.html'
    context_object_name = 'results'
    paginate_by = 10
    
    def get_queryset(self):
        from main.models import Result
        return Result.objects.filter(
            attempt__student=self.request.student
        ).select_related(
            'attempt__quiz'
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistika
        from main.models import Result
        results = Result.objects.filter(attempt__student=self.request.student)
        
        if results.exists():
            context['total_tests'] = results.count()
            context['passed_tests'] = results.filter(passed=True).count()
            context['failed_tests'] = results.filter(passed=False).count()
            context['average_score'] = round(results.aggregate(
                Avg('percentage')
            )['percentage__avg'], 2)
        else:
            context['total_tests'] = 0
            context['passed_tests'] = 0
            context['failed_tests'] = 0
            context['average_score'] = 0
        
        return context


class StudentStatisticsView(StudentLoginRequiredMixin, TemplateView):
    """Student statistikasi"""
    template_name = 'statistics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.student
        
        from main.models import QuizAttempt, Result
        import json
        
        # Barcha natijalar
        results = Result.objects.filter(
            attempt__student=student
        ).select_related('attempt__quiz').order_by('created_at')
        
        # Chart uchun ma'lumotlar
        chart_data = {
            'labels': [],
            'scores': [],
            'passed': []
        }
        
        for result in results:
            chart_data['labels'].append(
                result.attempt.quiz.title[:20] + '...' 
                if len(result.attempt.quiz.title) > 20 
                else result.attempt.quiz.title
            )
            chart_data['scores'].append(float(result.percentage))
            chart_data['passed'].append(1 if result.passed else 0)
        
        context['chart_data'] = json.dumps(chart_data)
        
        # Umumiy statistika
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
        
        return context