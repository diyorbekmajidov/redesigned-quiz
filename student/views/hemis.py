from django.views import View
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.contrib import messages
from urllib.parse import urlencode
import requests
import os
import logging
from dotenv import load_dotenv

# Logging sozlash
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
        
        # Parametrlarni tekshirish
        self._validate_config()
    
    def _validate_config(self):
        """Konfiguratsiyani tekshirish"""
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
        """Authorization URL yaratish"""
        payload = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
        }
        
        if state:
            payload['state'] = state
        
        url = f"{self.authorize_url}?{urlencode(payload)}"
        logger.info(f"Authorization URL yaratildi: {url}")
        return url
    
    def get_access_token(self, auth_code):
        """Authorization code orqali access token olish"""
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        try:
            logger.info("Access token so'ralmoqda...")
            response = requests.post(
                self.token_url, 
                data=payload,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info("Access token muvaffaqiyatli olindi")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Access token olishda xatolik: {e}")
            return {'error': str(e)}
    
    def get_user_details(self, access_token):
        """Access token orqali foydalanuvchi ma'lumotlarini olish"""
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            logger.info("Foydalanuvchi ma'lumotlari so'ralmoqda...")
            response = requests.get(
                self.resource_owner_url, 
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info("Foydalanuvchi ma'lumotlari olindi")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Foydalanuvchi ma'lumotlarini olishda xatolik: {e}")
            return {'error': str(e)}
    
    def refresh_access_token(self, refresh_token):
        """Access token'ni yangilash"""
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(
                self.token_url, 
                data=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Token yangilashda xatolik: {e}")
            return {'error': str(e)}


class AuthLoginView(View):
    """HEMIS orqali login qilish"""
    
    def get(self, request):
        try:
            # OAuth2 client yaratish
            client = OAuth2Client(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                authorize_url=AUTHORIZE_URL,
                token_url=TOKEN_URL,
                resource_owner_url=RESOURCE_OWNER_URL
            )
            
            # State parametri (CSRF himoyasi uchun)
            import secrets
            state = secrets.token_urlsafe(32)
            request.session['oauth_state'] = state
            
            # Authorization URL olish
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
    """HEMIS'dan qaytish callback"""
    
    def get(self, request):
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        if error:
            logger.error(f"HEMIS xatolik qaytardi: {error}")
            return JsonResponse({
                'error': 'Avtorizatsiya xatolik',
                'message': error,
                'description': request.GET.get('error_description', '')
            }, status=400)
        
        if not code:
            logger.error("Authorization code topilmadi")
            return JsonResponse({
                'error': 'Authorization code topilmadi'
            }, status=400)
        
        saved_state = request.session.get('oauth_state')
        if saved_state and saved_state != state:
            logger.error("State parametri mos kelmadi (CSRF hujum?)")
            return JsonResponse({
                'error': 'Xavfsizlik xatosi: state mos kelmadi'
            }, status=400)
        
        try:
            client = OAuth2Client(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                authorize_url=AUTHORIZE_URL,
                token_url=TOKEN_URL,
                resource_owner_url=RESOURCE_OWNER_URL
            )
            
            logger.info(f"Authorization code bilan token so'ralmoqda")
            token_response = client.get_access_token(code)
            
            if 'error' in token_response:
                logger.error(f"Token olishda xatolik: {token_response['error']}")
                return JsonResponse({
                    'error': 'Token olishda xatolik',
                    'message': token_response['error']
                }, status=400)
            
            access_token = token_response.get('access_token')
            if not access_token:
                logger.error("Access token topilmadi")
                return JsonResponse({
                    'error': 'Access token topilmadi'
                }, status=400)
            
            user_details = client.get_user_details(access_token)
            student =self._get_or_create_student(user_details)
            self._get_or_create_student_girl(user_details, student)

            
            if 'error' in user_details:
                logger.error(f"Foydalanuvchi ma'lumotlari olishda xatolik: {user_details['error']}")
                return JsonResponse({
                    'error': 'Foydalanuvchi ma\'lumotlari olishda xatolik',
                    'message': user_details['error']
                }, status=400)
            
            request.session['access_token'] = access_token
            request.session['refresh_token'] = token_response.get('refresh_token')
            request.session['user_details'] = user_details
            
            # State'ni tozalash
            if 'oauth_state' in request.session:
                del request.session['oauth_state']
            
            logger.info(f"Foydalanuvchi muvaffaqiyatli tizimga kirdi: {user_details.get('email')}")
            
            return JsonResponse({
                'success': True,
                'message': 'Muvaffaqiyatli tizimga kirdingiz',
                'user': user_details,
                'token': {
                    'access_token': access_token,
                    'token_type': token_response.get('token_type'),
                    'expires_in': token_response.get('expires_in')
                }
            })
            
        except ValueError as e:
            logger.error(f"Konfiguratsiya xatosi: {e}")
            return JsonResponse({
                'error': 'OAuth2 konfiguratsiyasi to\'liq emas',
                'message': str(e)
            }, status=500)
        
        except Exception as e:
            logger.error(f"Kutilmagan xatolik: {e}", exc_info=True)
            return JsonResponse({
                'error': 'Tizimda xatolik yuz berdi',
                'message': str(e)
            }, status=500)

    def _get_or_create_student(self, user_details, student_group=None):
        """HEMIS ma'lumotlaridan Student yaratish yoki olish"""
        from student.models import Student, StudentGroup
        
        student_id_number = user_details.get('student_id_number') or user_details.get('student_id')

        data = user_details['data']
        group_data = user_details.get('groups', [])

        group, _ = StudentGroup.objects.get_or_create(
            group_code=group_data[0]['id'] if group_data else 'Unknown Group',
            defaults={
                'group_name': group_data[0]['name'] if group_data else 'Unknown Group',
                'group_faculty': data['faculty']['name'],
                'group_level': data['level']['name'],
                'group_code': group_data[0]['id'] if group_data else 'N/A',
                'group_year': data['semester']['education_year']['name'],
                'education_form': group_data[0]['education_form']['name'] if group_data else 'N/A',
                'education_lang': group_data[0]['education_lang']['name'] if group_data else 'N/A',
            }
        )
        
        student, created = Student.objects.get_or_create(
            student_id_number=student_id_number,
            defaults={
                'student_name': data['full_name'],
                'email': data['email'],
                'phone_number': data,
                'student_id_number': user_details.get('student_id_number', ''),
                'passport_number': user_details.get('passport_number', ''),
                'birth_date': user_details.get('birth_date', ''),
                'student_imeg': user_details.get('picture_full', ''),
                'faculty': data['faculty']['name'],
                'level': data['level']['name'],
                'paymentForm': data['paymentForm']['name'],
                'studentStatus': data['studentStatus']['name'],
                'avg_gpa': data.get('avg_gpa', ''),
                'education_type': data['educationType']['name'],
                "gender": data['gender']['name'],
                "semester": data['semester']['name'],
                'group': group,
            }
        )
        
        if created:
            logger.info(f"Yangi talaba yaratildi: {student.student_name}")
        else:
            logger.info(f"Mavjud talaba topildi: {student.student_name}")
        
        return student
        
    def _get_or_create_student_girl(self, user_details, student):
        from student.models import StudentGirls
        data = user_details['data']
        girl, _ = StudentGirls.objects.get_or_create(
            student=student,
            defaults={
                'place_of_birth': data['address'],
                'current_address': data['accommodation']['name'],
                'district': data['district']['name'],
                'province': data['province']['name'],
            }
        )

        if _:
            logger.info(f"Yangi talaba yaratildi: {student.student_name}")
        else:
            logger.info(f"Mavjud talaba topildi: {student.student_name}")
        
        return girl

class LogoutView(View):
    """Tizimdan chiqish"""
    
    def get(self, request):
        request.session.flush()
        logger.info("Foydalanuvchi tizimdan chiqdi")
        
        return JsonResponse({
            'success': True,
            'message': 'Tizimdan chiqdingiz'
        })
    

class StudentInfoDowland(View):
    """Talaba ma'lumotlarini yuklab olish"""
    
    def get(self, request):
        access_token = request.session.get('access_token')
        pass