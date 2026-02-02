"""
User Session Management - Access Token saqlash uchun model
"""
from django.db import models
from django.utils import timezone
from student.models import Student
from datetime import timedelta


class UserSession(models.Model):
    """
    Har bir talabaning session va access token'ini saqlash
    
    Bu model:
    - Har bir talaba uchun alohida access token saqlaydi
    - Token muddati tugaganligini tekshiradi
    - Refresh token bilan yangilaydi
    - Eski session'larni avtomatik tozalaydi
    """

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='sessions', verbose_name="Talaba")
    session_key = models.CharField(max_length=100, unique=True, verbose_name="Session key")
    access_token = models.TextField(verbose_name="Access token")
    refresh_token = models.TextField(blank=True, null=True, verbose_name="Refresh token")
    token_type = models.CharField(max_length=100, default='Bearer', verbose_name="Token turi")
    expires_at = models.DateTimeField(verbose_name="Token muddati")
    user_agent = models.TextField(blank=True, verbose_name="User agent")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP manzil")

    device_info = models.JSONField(default=dict, blank=True, verbose_name="Device ma'lumotlari")

    is_active = models.BooleanField(default=True, verbose_name="Faol")
    last_activity = models.DateTimeField(auto_now=True, verbose_name="Oxirgi faollik")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    
    class Meta:
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['student', '-last_activity']),
            models.Index(fields=['session_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.student.student_name} - {self.session_key[:10]}..."
    
    def is_expired(self):
        """Token muddati tugaganmi?"""
        return timezone.now() >= self.expires_at
    
    def is_valid(self):
        """Token hali ham ishlatilishi mumkinmi?"""
        return self.is_active and not self.is_expired()
    
    def refresh_if_needed(self):
        """
        Agar token muddati tugagan bo'lsa, refresh token bilan yangilash
        
        Returns:
            bool: Muvaffaqiyatli yangilangan bo'lsa True
        """
        if not self.is_expired():
            return True
        
        if not self.refresh_token:
            return False
        
        try:
            from student.views.hemis import OAuth2Client
            import os
            
            client = OAuth2Client(
                client_id=os.getenv('CLIENT_ID_HEMIS'),
                client_secret=os.getenv('CLIENT_SECRET'),
                redirect_uri=os.getenv('REDIRECT_URI_HEMIS'),
                authorize_url=os.getenv('AUTHORIZE_URL_HEMIS'),
                token_url=os.getenv('TOKEN_URL_HEMIS'),
                resource_owner_url=os.getenv('RESOURCE_OWNER_URL')
            )
            
            new_tokens = client.refresh_access_token(self.refresh_token)
            
            if 'access_token' in new_tokens:
                self.access_token = new_tokens['access_token']
                
                if 'refresh_token' in new_tokens:
                    self.refresh_token = new_tokens['refresh_token']
                
                expires_in = new_tokens.get('expires_in', 3600)
                self.expires_at = timezone.now() + timedelta(seconds=expires_in)
                
                self.save()
                return True
            
            return False
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Token yangilashda xatolik: {e}")
            return False
    
    def deactivate(self):
        """Session'ni deaktivatsiya qilish"""
        self.is_active = False
        self.save()
    
    @classmethod
    def cleanup_expired(cls, days=7):
        """
        Eski va muddati tugagan session'larni tozalash
        
        Args:
            days: Necha kundan eski session'larni o'chirish
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        expired = cls.objects.filter(
            models.Q(expires_at__lt=timezone.now()) |
            models.Q(last_activity__lt=cutoff_date)
        )
        count = expired.count()
        expired.delete()
        return count
    
    @classmethod
    def get_or_create_session(cls, student, request, token_data):
        """
        Student uchun session yaratish yoki yangilash
        
        Args:
            student: Student obyekti
            request: Django request obyekti
            token_data: OAuth2 token ma'lumotlari
        
        Returns:
            UserSession: Yaratilgan yoki yangilangan session
        """
        from datetime import timedelta
        
        # Session key
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        # Device ma'lumotlari
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip_address = cls._get_client_ip(request)
        
        # Token muddati
        expires_in = token_data.get('expires_in', 3600)
        expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        # Session yaratish yoki yangilash
        session, created = cls.objects.update_or_create(
            session_key=session_key,
            defaults={
                'student': student,
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token', ''),
                'token_type': token_data.get('token_type', 'Bearer'),
                'expires_at': expires_at,
                'user_agent': user_agent,
                'ip_address': ip_address,
                'is_active': True,
            }
        )
        
        return session
    
    @staticmethod
    def _get_client_ip(request):
        """Request'dan client IP manzilini olish"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def update_activity(self):
        """Oxirgi faollik vaqtini yangilash"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])


class LoginHistory(models.Model):
    """
    Login tarixi - Auditlash uchun
    """
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='login_history',
        verbose_name="Talaba"
    )
    
    session = models.ForeignKey(
        UserSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Session"
    )
    
    # Login ma'lumotlari
    login_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Login vaqti"
    )
    logout_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Logout vaqti"
    )
    
    # Device ma'lumotlari
    ip_address = models.GenericIPAddressField(
        verbose_name="IP manzil"
    )
    user_agent = models.TextField(
        verbose_name="User agent"
    )
    device_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Device turi"
    )
    
    # Login holati
    success = models.BooleanField(
        default=True,
        verbose_name="Muvaffaqiyatli"
    )
    failure_reason = models.TextField(
        blank=True,
        verbose_name="Xatolik sababi"
    )
    
    class Meta:
        verbose_name = "Login Tarixi"
        verbose_name_plural = "Login Tarixi"
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['student', '-login_time']),
        ]
    
    def __str__(self):
        return f"{self.student.student_name} - {self.login_time}"
    
    def get_duration(self):
        """Login davomiyligi"""
        if self.logout_time:
            return self.logout_time - self.login_time
        return timezone.now() - self.login_time