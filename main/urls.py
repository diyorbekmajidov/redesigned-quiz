from django.urls import path, include
from .views import  QuizResultView, QuizTakeView, QuizListView, QuizDetailView, QuizListView, StudentDashboardView, HomeView, StudentProfileView, StudentStatisticsView,ResultsHistoryView


urlpatterns = [
    path("dashboard/", StudentDashboardView.as_view(), name="dashboard"),
    path('', HomeView.as_view(), name='home'),
    path('profile/', StudentProfileView.as_view(), name='profile'),
    path('statistics/', StudentStatisticsView.as_view(), name='statistics'),
    path('results/', ResultsHistoryView.as_view(), name='results'),
    path('quizzes/', QuizListView.as_view(), name='list'),
    path('quizzes/<int:pk>/', QuizDetailView.as_view(), name='detail'),
    path('quizzes/<int:pk>/take/', QuizTakeView.as_view(), name='take'),
    path('<int:attempt_id>/result/', QuizResultView.as_view(),name='result'),
]