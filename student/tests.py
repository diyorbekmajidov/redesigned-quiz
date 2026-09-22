import json

from django.test import TestCase

from .models import Student, StudentGirls
from .views.hemis import AuthCallbackView


class HEMISStudentSyncTests(TestCase):
    def payload(self):
        return {
            'id': 'hemis-user-uuid',
            'uuid': 'hemis-uuid-1',
            'login': 'student-login',
            'student_id_number': '320251100001',
            'passport_number': 'AA1234567',
            'passport_pin': 'must-not-be-saved',
            'hash': 'must-not-be-saved',
            'birth_date': '14-11-2005',
            'data': {
                'id': 12345,
                'student_id_number': '320251100001',
                'full_name': 'Test Student',
                'email': 'student@example.com',
                'phone': '+998900000000',
                'birth_date': '1110758400',
                'avg_gpa': '3.67',
                'image': 'https: //example.com/student.jpg',
                'faculty': {'name': 'Test Faculty'},
                'level': {'name': '3-kurs'},
                'paymentForm': {'name': 'Grant'},
                'studentStatus': {'name': 'Active'},
                'gender': {'code': 12, 'name': 'Ayol'},
                'semester': {'name': '6-semestr'},
            },
            'groups': [{
                'id': 'group-1',
                'name': 'Test Group',
                'education_form': {'name': 'Kunduzgi'},
                'education_lang': {'name': 'O\'zbek'},
                'education_type': {'name': 'Bakalavr'},
            }],
        }

    def test_sync_separates_identity_and_sanitizes_snapshot(self):
        student = AuthCallbackView()._get_or_create_student(self.payload())

        self.assertEqual(student.hemis_id, '12345')
        self.assertEqual(student.student_id_number, '320251100001')
        self.assertEqual(student.hemis_uuid, 'hemis-uuid-1')
        self.assertEqual(student.birth_date.isoformat(), '2005-11-14')
        self.assertEqual(str(student.avg_gpa), '3.67')
        self.assertEqual(student.student_image_url, 'https://example.com/student.jpg')

        snapshot = json.dumps(student.hemis_extra)
        self.assertNotIn('must-not-be-saved', snapshot)
        self.assertNotIn('passport_pin', snapshot)
        self.assertNotIn('hash', snapshot)

    def test_address_is_not_saved_as_place_of_birth(self):
        payload = self.payload()
        payload['data'].update({
            'address': 'Current address',
            'district': {'name': 'Test district'},
            'province': {'name': 'Test province'},
            'accommodation': {'name': 'Yotoqxona'},
        })
        student = AuthCallbackView()._get_or_create_student(payload)
        girl = AuthCallbackView()._get_or_create_student_girl(payload, student)

        self.assertIsInstance(girl, StudentGirls)
        self.assertEqual(girl.current_address, 'Current address')
        self.assertEqual(girl.district, 'Test district')
        self.assertEqual(girl.province, 'Test province')
        self.assertIsNone(girl.place_of_birth)
