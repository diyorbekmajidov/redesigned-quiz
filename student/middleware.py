class StudentAuthMiddleware:
    """
    Har bir request'da student'ning session'ini tekshirish middleware
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Student'ni request'ga qo'shish
        student_id = request.session.get('student_id')
        user_session_id = request.session.get('user_session_id')
        
        request.student = None
        request.user_session = None
        
        if student_id and user_session_id:
            try:
                from UserSession.models import UserSession
                from student.models import Student
                
                # UserSession olish
                user_session = UserSession.objects.select_related('student').get(
                    id=user_session_id,
                    is_active=True
                )
                
                # Token hali ham validmi?
                if not user_session.is_valid():
                    # Token muddati tugagan, refresh qilib ko'rish
                    if user_session.refresh_if_needed():
                        user_session.refresh_from_db()
                    else:
                        # Refresh ham muvaffaqiyatsiz, logout
                        request.session.flush()
                        return self.get_response(request)
                
                # Student va session'ni request'ga qo'shish
                request.student = user_session.student
                request.user_session = user_session
                
                # Activity'ni yangilash (har 5 daqiqada)
                from django.utils import timezone
                from datetime import timedelta
                if timezone.now() - user_session.last_activity > timedelta(minutes=5):
                    user_session.update_activity()
                
            except (UserSession.DoesNotExist, Student.DoesNotExist):
                # Session topilmadi, tozalash
                request.session.flush()
        
        response = self.get_response(request)
        return response