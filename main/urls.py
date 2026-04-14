from django.urls import path
from .views import (
    QuizResultView, QuizTakeView, QuizListView, QuizDetailView,
    StudentDashboardView, HomeView, StudentProfileView,
    StudentStatisticsView, ResultsHistoryView,
    PsychologicalTestsView, PsychologicalResultsView,
    AdminPsychologicalStatisticsView,
)


urlpatterns = [
    path("dashboard/", StudentDashboardView.as_view(), name="dashboard"),
    path('', HomeView.as_view(), name='home'),
    path('profile/', StudentProfileView.as_view(), name='profile'),
    path('statistics/', StudentStatisticsView.as_view(), name='statistics'),
    path('results/', ResultsHistoryView.as_view(), name='results'),
    path('psychological-results/', PsychologicalResultsView.as_view(), name='psychological_results'),


    path('quiz/', QuizListView.as_view(), name='quiz_list'),
    path('quiz/<int:pk>/', QuizDetailView.as_view(), name='quiz_detail'),
    path('quiz/<int:pk>/take/', QuizTakeView.as_view(), name='quiz_take'),
    path('quiz/<int:attempt_id>/result/', QuizResultView.as_view(), name='quiz_result'),
    path('quiz/psychological/', PsychologicalTestsView.as_view(), name='psychological_tests'),
    path('admin-stats/psychological/', AdminPsychologicalStatisticsView.as_view(), name='admin_psychological_stats'),
]