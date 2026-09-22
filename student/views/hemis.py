"""
Yangilangan OAuth Views - Session Management bilan
"""
from django.views import View
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from urllib.parse import urlencode
from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation
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

_SENSITIVE_HEMIS_KEYS = {
    'passport_number', 'passport_pin', 'passportpin',
    'password', 'hash', 'hash2', 'access_token', 'refresh_token',
    'client_secret', 'secret', 'token',
}


def _clean_identifier(value):
    """HEMIS identifikatorini xavfsiz va izchil stringga aylantiradi."""
    if value is None:
        return ''
    return str(value).strip()


def _hemis_label(value):
    """HEMIS'dagi code/name obyektidan foydalanuvchiga mos label oladi."""
    if isinstance(value, dict):
        return str(
            value.get('name')
            or value.get('short_name')
            or value.get('code')
            or ''
        ).strip()
    return str(value or '').strip()


def _normalize_birth_date(value):
    """HEMIS timestamp yoki sana stringini DateField qiymatiga aylantiradi."""
    if value in (None, ''):
        return None

    raw_value = str(value).strip()
    if raw_value.isdigit():
        timestamp = int(raw_value)
        if timestamp > 10**11:
            timestamp //= 1000
        try:
            return datetime.fromtimestamp(
                timestamp,
                tz=datetime_timezone.utc,
            ).date()
        except (OverflowError, OSError, ValueError):
            return None

    for date_format in ('%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y'):
        try:
            return datetime.strptime(raw_value, date_format).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(raw_value.replace('Z', '+00:00')).date()
    except ValueError:
        return None


def _normalize_gpa(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _normalize_image_url(value):
    if not value:
        return ''
    return str(value).strip().replace('https: //', 'https://').replace('http: //', 'http://')


def _sanitize_hemis_payload(value):
    """JSON snapshotdan credential va maxfiy passport qiymatlarini olib tashlaydi."""
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if str(key).lower() in _SENSITIVE_HEMIS_KEYS:
                continue
            sanitized[str(key)] = _sanitize_hemis_payload(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_hemis_payload(item) for item in value]
    return value


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
    
    @transaction.atomic
    def _get_or_create_student(self, user_details):
        """Student yaratish yoki yangilash"""
        from student.models import Student, StudentGroup

        data = user_details.get('data') if isinstance(user_details.get('data'), dict) else {}
        raw_groups = user_details.get('groups')
        group_data = raw_groups if isinstance(raw_groups, list) else []
        group_payload = group_data[0] if group_data and isinstance(group_data[0], dict) else {}

        hemis_id = _clean_identifier(data.get('id'))
        hemis_uuid = _clean_identifier(user_details.get('uuid'))
        hemis_login = _clean_identifier(user_details.get('login'))
        student_id_number = _clean_identifier(
            user_details.get('student_id_number') or data.get('student_id_number')
        )

        # data.id asosiy HEMIS ID hisoblanadi. Fallback faqat HEMIS javobida
        # id vaqtincha bo'lmasa ishlatiladi; keyingi sync uni to'g'rilaydi.
        if not hemis_id:
            hemis_id = hemis_uuid or student_id_number
        if not hemis_id:
            raise ValueError("HEMIS javobida student uchun barqaror identifikator topilmadi")

        group = None
        group_code = _clean_identifier(group_payload.get('id'))
        if group_code:
            semester_data = data.get('semester') if isinstance(data.get('semester'), dict) else {}
            education_year = semester_data.get('education_year')
            group, _ = StudentGroup.objects.update_or_create(
                group_code=group_code,
                defaults={
                    'group_name': _hemis_label(group_payload.get('name')) or 'Noma’lum guruh',
                    'group_faculty': _hemis_label(data.get('faculty')),
                    'group_level': _hemis_label(data.get('level')),
                    'group_year': _hemis_label(education_year),
                    'education_form': _hemis_label(group_payload.get('education_form')),
                    'education_lang': _hemis_label(group_payload.get('education_lang')),
                },
            )

        # Avval UUID, keyin HEMIS ID, so'ng student ID orqali mavjud studentni topamiz.
        student = None
        if hemis_uuid:
            student = Student.objects.filter(hemis_uuid=hemis_uuid).first()
        if student is None:
            student = Student.objects.filter(hemis_id=hemis_id).first()
        if student is None and student_id_number:
            student = Student.objects.filter(student_id_number=student_id_number).first()

        created = student is None
        if created:
            student = Student(hemis_id=hemis_id)

        gender_data = data.get('gender') if isinstance(data.get('gender'), dict) else {}
        semester_data = data.get('semester') if isinstance(data.get('semester'), dict) else {}
        image_url = _normalize_image_url(
            user_details.get('picture_full')
            or user_details.get('picture')
            or data.get('image')
        )

        student.student_name = data.get('full_name') or user_details.get('name') or ''
        student.phone_number = data.get('phone') or user_details.get('phone') or student.phone_number
        student.faculty = _hemis_label(data.get('faculty'))
        student.level = _hemis_label(data.get('level'))
        student.paymentForm = _hemis_label(data.get('paymentForm')) or 'Noma’lum'
        student.studentStatus = _hemis_label(data.get('studentStatus')) or 'Noma’lum'
        student.gender = _hemis_label(gender_data)
        student.education_type = _hemis_label(group_payload.get('education_type')) or _hemis_label(data.get('educationType'))
        student.semester = _hemis_label(semester_data)
        student.group = group
        student.hemis_id = hemis_id
        student.hemis_synced_at = timezone.now()
        student.hemis_extra = _sanitize_hemis_payload(user_details)

        if student_id_number:
            student.student_id_number = student_id_number
        if hemis_uuid:
            student.hemis_uuid = hemis_uuid
        if hemis_login:
            student.hemis_login = hemis_login
        if image_url:
            student.student_image_url = image_url
        if data.get('email') or user_details.get('email'):
            student.email = data.get('email') or user_details.get('email')
        if user_details.get('passport_number'):
            student.passport_number = user_details.get('passport_number')

        birth_date = _normalize_birth_date(
            user_details.get('birth_date') or data.get('birth_date')
        )
        if birth_date:
            student.birth_date = birth_date

        gpa = _normalize_gpa(data.get('avg_gpa'))
        if gpa is not None:
            student.avg_gpa = gpa

        student.save()

        action = "yaratildi" if created else "yangilandi"
        logger.info(f"Student {action}: {student.student_name}")
        return student
    
    def _get_or_create_student_girl(self, user_details, student):
        """Qiz talaba qo'shimcha ma'lumotlari"""
        from student.models import StudentGirls
        
        data = user_details.get('data') if isinstance(user_details.get('data'), dict) else {}

        gender = data.get('gender') if isinstance(data.get('gender'), dict) else {}
        if str(gender.get('code')) == '11':
            return None

        girl, created = StudentGirls.objects.get_or_create(student=student)
        updates = {}
        address = _hemis_label(data.get('address'))
        district = _hemis_label(data.get('district'))
        province = _hemis_label(data.get('province'))
        place_of_birth = _hemis_label(data.get('place_of_birth'))

        if address:
            updates['current_address'] = address
        if district:
            updates['district'] = district
        if province:
            updates['province'] = province
        if place_of_birth:
            updates['place_of_birth'] = place_of_birth

        if updates:
            for field, value in updates.items():
                setattr(girl, field, value)
            girl.save(update_fields=[*updates, 'date_updated'])
        
        action = "yaratildi" if created else "topildi"
        logger.info(f"StudentGirl {action}: {student.student_name}")
        
        return girl


class LogoutView(View):
    """Tizimdan chiqish"""
    
    def get(self, request):
        try:
            student_id = request.session.get('student_id')
            user_session_id = request.session.get('user_session_id')
            
            if user_session_id:
                from UserSession.models import UserSession, LoginHistory
                
                try:
                    user_session = UserSession.objects.get(id=user_session_id)
                    user_session.deactivate()
                    
                    from django.utils import timezone
                    LoginHistory.objects.filter(
                        session=user_session,
                        logout_time__isnull=True
                    ).update(logout_time=timezone.now())
                    
                except UserSession.DoesNotExist:
                    pass
            
            request.session.flush()
            
            logger.info("Foydalanuvchi tizimdan chiqdi")
            
            return redirect('home')
            
        except Exception as e:
            logger.error(f"Logout xatolik: {e}")
            request.session.flush()
            return redirect('home')
