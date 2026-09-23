from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from student.models import Student
from .models import Option, Question, Quiz, QuizAttempt, UserResponse


class QuizIntegrityTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username='test-admin', is_staff=True)
        self.student = Student.objects.create(
            student_name='Test Student',
            hemis_id='hemis-test-1',
            student_id_number='student-test-1',
            studentStatus='active',
            paymentForm='grant',
            faculty='Test Faculty',
            level='1-kurs',
            education_type='Bakalavr',
            gender='Ayol',
            semester='1-semestr',
        )
        self.quiz = Quiz.objects.create(
            title='Test quiz',
            created_by=self.admin_user,
        )
        self.question = Question.objects.create(
            quiz=self.quiz,
            question_text='Test question',
            score=1,
            order=1,
        )
        self.option = Option.objects.create(
            question=self.question,
            option_text='Correct option',
            is_correct=True,
        )

    def test_psychological_passport_works_without_test_result(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('admin_psychological_passports'))
        detail_response = self.client.get(
            reverse(
                'admin_psychological_passport_detail',
                kwargs={'student_id': self.student.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Barcha talabalar')
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Hali psixologik test topshirilmagan')

    def test_response_rejects_question_from_another_quiz(self):
        other_quiz = Quiz.objects.create(
            title='Other quiz',
            created_by=self.admin_user,
        )
        other_question = Question.objects.create(
            quiz=other_quiz,
            question_text='Other question',
            score=1,
            order=1,
        )
        other_option = Option.objects.create(
            question=other_question,
            option_text='Other option',
            is_correct=True,
        )
        attempt = QuizAttempt.objects.create(student=self.student, quiz=self.quiz)

        with self.assertRaises(ValidationError):
            UserResponse.objects.create(
                attempt=attempt,
                question=other_question,
                selected_option=other_option,
            )

    def test_completed_attempt_calculates_result_inside_lifecycle(self):
        attempt = QuizAttempt.objects.create(student=self.student, quiz=self.quiz)
        UserResponse.objects.create(
            attempt=attempt,
            question=self.question,
            selected_option=self.option,
        )

        self.assertTrue(attempt.complete_attempt())
        attempt.refresh_from_db()

        self.assertEqual(attempt.status, 'completed')
        self.assertEqual(attempt.result.correct_answers, 1)
        self.assertEqual(attempt.result.total_score, 1)
