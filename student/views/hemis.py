"""
Yangilangan OAuth Views - Session Management bilan
"""
from django.views import View
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.contrib import messages
from urllib.parse import urlencode
import requests
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# HEMIS OAuth2 sozlamalari
CLIENT_ID = os.getenv('CLIENT_ID_HEMIS')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI_HEMIS')
AUTHORIZE_URL = os.getenv('AUTHORIZE_URL_HEMIS')
TOKEN_URL = os.getenv('TOKEN_URL_HEMIS')
RESOURCE_OWNER_URL = os.getenv('RESOURCE_OWNER_URL')


class OAuth2Client:
    """HEMIS OAuth2 integratsiyasi uchun client"""
    
    def __init__(self, client_id, client_secret, redirect_uri, authorize_url, token_url, resource_owner_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.resource_owner_url = resource_owner_url
        self._validate_config()
    
    def _validate_config(self):
        required = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'authorize_url': self.authorize_url,
            'token_url': self.token_url,
            'resource_owner_url': self.resource_owner_url
        }
        
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"OAuth2 konfiguratsiyasida quyidagi parametrlar yo'q: {', '.join(missing)}"
            )
    
    def get_authorization_url(self, state=None):
        payload = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
        }
        
        if state:
            payload['state'] = state
        
        url = f"{self.authorize_url}?{urlencode(payload)}"
        logger.info(f"Authorization URL yaratildi")
        return url
    
    def get_access_token(self, auth_code):
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post(self.token_url, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info("Access token muvaffaqiyatli olindi")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Access token olishda xatolik: {e}")
            return {'error': str(e)}
    
    def get_user_details(self, access_token):
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(self.resource_owner_url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info("Foydalanuvchi ma'lumotlari olindi")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Foydalanuvchi ma'lumotlarini olishda xatolik: {e}")
            return {'error': str(e)}
    
    def refresh_access_token(self, refresh_token):
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(self.token_url, data=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Token yangilashda xatolik: {e}")
            return {'error': str(e)}


class AuthLoginView(View):
    """HEMIS orqali login qilish"""
    
    def get(self, request):
        try:
            client = OAuth2Client(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                authorize_url=AUTHORIZE_URL,
                token_url=TOKEN_URL,
                resource_owner_url=RESOURCE_OWNER_URL
            )
            
            import secrets
            state = secrets.token_urlsafe(32)
            request.session['oauth_state'] = state
            
            authorization_url = client.get_authorization_url(state=state)
            logger.info(f"Foydalanuvchi HEMIS'ga yo'naltirilmoqda")
            
            return HttpResponseRedirect(authorization_url)
            
        except ValueError as e:
            logger.error(f"Konfiguratsiya xatosi: {e}")
            return JsonResponse({
                'error': 'OAuth2 konfiguratsiyasi to\'liq emas',
                'message': str(e)
            }, status=500)
        except Exception as e:
            logger.error(f"Kutilmagan xatolik: {e}")
            return JsonResponse({
                'error': 'Tizimda xatolik yuz berdi',
                'message': str(e)
            }, status=500)


class AuthCallbackView(View):
    """HEMIS'dan qaytish callback - SESSION BILAN"""
    
    def get(self, request):
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        if error:
            logger.error(f"HEMIS xatolik qaytardi: {error}")
            return self._error_response(
                'Avtorizatsiya xatolik',
                error,
                request.GET.get('error_description', '')
            )
        
        if not code:
            return self._error_response('Authorization code topilmadi')
        
        saved_state = request.session.get('oauth_state')
        if saved_state and saved_state != state:
            logger.error("State parametri mos kelmadi")
            return self._error_response('Xavfsizlik xatosi: state mos kelmadi')
        
        try:
            client = OAuth2Client(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                authorize_url=AUTHORIZE_URL,
                token_url=TOKEN_URL,
                resource_owner_url=RESOURCE_OWNER_URL
            )
            
            # Token olish
            token_response = client.get_access_token(code)
            
            if 'error' in token_response:
                return self._error_response('Token olishda xatolik', token_response['error'])
            
            access_token = token_response.get('access_token')
            if not access_token:
                return self._error_response('Access token topilmadi')
            
            # User ma'lumotlari
            user_details = client.get_user_details(access_token)
            
            if 'error' in user_details:
                return self._error_response(
                    'Foydalanuvchi ma\'lumotlari olishda xatolik',
                    user_details['error']
                )
            
            # Student yaratish/yangilash
            student = self._get_or_create_student(user_details)
            self._get_or_create_student_girl(user_details, student)
            
            # ⭐ SESSION YARATISH - BU ENG MUHIM QISM!
            from UserSession.models import UserSession, LoginHistory
            
            # Eski sessionlarni tozalash
            UserSession.cleanup_expired(days=7)
            
            # Yangi session yaratish
            user_session = UserSession.get_or_create_session(
                student=student,
                request=request,
                token_data=token_response
            )
            
            # Django session'ga qo'shish (optional, lekin qulaylik uchun)
            request.session['student_id'] = str(student.id)
            request.session['user_session_id'] = user_session.id
            
            # Login tarixiga yozish
            LoginHistory.objects.create(
                student=student,
                session=user_session,
                ip_address=UserSession._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True
            )
            
            # State'ni tozalash
            if 'oauth_state' in request.session:
                del request.session['oauth_state']
            
            logger.info(f"Talaba tizimga kirdi: {student.student_name}")
            
            # Dashboard'ga redirect
            return redirect('dashboard')
            
        except ValueError as e:
            logger.error(f"Konfiguratsiya xatosi: {e}")
            return self._error_response('OAuth2 konfiguratsiyasi to\'liq emas', str(e))
        except Exception as e:
            logger.error(f"Kutilmagan xatolik: {e}", exc_info=True)
            
            # Xatolikli login'ni yozish
            try:
                from UserSession.models import LoginHistory
                if 'student' in locals():
                    LoginHistory.objects.create(
                        student=student,
                        ip_address=UserSession._get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        success=False,
                        failure_reason=str(e)
                    )
            except:
                pass
            
            return self._error_response('Tizimda xatolik yuz berdi', str(e))
    
    def _error_response(self, error, message='', description=''):
        """Xatolik response'i"""
        return JsonResponse({
            'error': error,
            'message': message,
            'description': description
        }, status=400)
    
    def _get_or_create_student(self, user_details):
        """Student yaratish yoki yangilash"""
        from student.models import Student, StudentGroup
        
        data = user_details.get('data', {})
        group_data = user_details.get('groups', [])
        
        # Guruh yaratish/yangilash
        group = None
        if group_data:
            group, _ = StudentGroup.objects.get_or_create(
                group_code=group_data[0].get('id', 'Unknown'),
                defaults={
                    'group_name': group_data[0].get('name', 'Unknown Group'),
                    'faculty': data.get('faculty', {}).get('name', ''),
                    'level': data.get('level', {}).get('name', ''),
                    'academic_year': data.get('semester', {}).get('education_year', {}).get('name', ''),
                }
            )
        
        # Student yaratish/yangilash
        student_id_number = user_details.get('student_id_number') or data.get('student_id_number', '')
        
        student, created = Student.objects.update_or_create(
            student_id_number=student_id_number,
            defaults={
                'student_name': data.get('full_name', ''),
                'email': data.get('email', ''),
                'phone_number': data.get('phone', ''),
                'passport_number': data.get('passport_number', ''),
                'birth_date': data.get('birth_date', '2000-01-01'),
                'faculty': data.get('faculty', {}).get('name', ''),
                'level': str(data.get('level', {}).get('code', '1')),
                'payment_form': data.get('paymentForm', {}).get('name', 'contract'),
                'student_status': data.get('studentStatus', {}).get('name', 'active'),
                'avg_gpa': data.get('avg_gpa', 0),
                'hemis_id': data.get('id', ''),
            }
        )
        
        action = "yaratildi" if created else "yangilandi"
        logger.info(f"Student {action}: {student.student_name}")
        
        return student
    
    def _get_or_create_student_girl(self, user_details, student):
        """Qiz talaba qo'shimcha ma'lumotlari"""
        from student.models import StudentGirls
        
        data = user_details.get('data', {})
        
        # Faqat qiz talabalar uchun
        gender = data.get('gender', {}).get('code')
        if gender != 11:  # 11 = qiz (HEMIS'da)
            return None
        
        girl, created = StudentGirls.objects.get_or_create(
            student=student,
            defaults={
                'place_of_birth': data.get('address', ''),
                'current_address': data.get('accommodation', {}).get('name', ''),
            }
        )
        
        action = "yaratildi" if created else "topildi"
        logger.info(f"StudentGirl {action}: {student.student_name}")
        
        return girl


class LogoutView(View):
    """Tizimdan chiqish"""
    
    def get(self, request):
        try:
            # UserSession'ni deaktivatsiya qilish
            student_id = request.session.get('student_id')
            user_session_id = request.session.get('user_session_id')
            
            if user_session_id:
                from UserSession.models import UserSession, LoginHistory
                
                try:
                    user_session = UserSession.objects.get(id=user_session_id)
                    user_session.deactivate()
                    
                    # Login history'ni yangilash
                    from django.utils import timezone
                    LoginHistory.objects.filter(
                        session=user_session,
                        logout_time__isnull=True
                    ).update(logout_time=timezone.now())
                    
                except UserSession.DoesNotExist:
                    pass
            
            # Session tozalash
            request.session.flush()
            
            logger.info("Foydalanuvchi tizimdan chiqdi")
            
            return redirect('home')
            
        except Exception as e:
            logger.error(f"Logout xatolik: {e}")
            request.session.flush()
            return redirect('home')


# ============ MIDDLEWARE ============

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