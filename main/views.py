from django.views.generic import TemplateView, ListView, DetailView
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Avg
from django.contrib import messages
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