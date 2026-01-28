from django.db import models
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator

class StudentGroup(models.Model):
    """Talabalar guruhi"""
    group_name = models.CharField(max_length=56, verbose_name="Guruh nomi")
    group_code = models.CharField(max_length=56, unique=True, verbose_name="Guruh kodi")
    group_faculty = models.CharField(max_length=56, verbose_name="Fakultet")
    group_level = models.CharField(max_length=56, verbose_name="Kurs")
    group_year = models.CharField(max_length=56, verbose_name="O'quv yili")
    education_form = models.CharField(max_length=56, verbose_name="Ta'lim shakli")
    education_lang = models.CharField(max_length=56, verbose_name="Ta'lim tili")
    
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"
        ordering = ['group_name']

    def __str__(self):
        return f"{self.group_name} ({self.group_code})"
    
    def get_student_count(self):
        return self.students.count()
class Student(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    student_name = models.CharField(max_length=56, blank=True, null=True, verbose_name="Talaba_Ismi")
    phone_number = models.CharField(max_length=56, blank=True, null=True, verbose_name="Telfon-raqam")
    student_imeg = models.URLField(blank=True, null=True)
    student_id_number = models.CharField(max_length=16, unique=True, blank=True, null=True)
    email = models.CharField(max_length=86)
    passport_number = models.CharField(max_length=12, verbose_name="passport raqami")
    birth_date = models.CharField(max_length=50, verbose_name="Tug'ilgan-kun-sanasi")
    studentStatus = models.CharField(max_length=86, verbose_name="talaba-holati")
    paymentForm = models.CharField(max_length=86, verbose_name="to'lov shakli")
    faculty = models.CharField(max_length=86, verbose_name="fakultet")
    level = models.CharField(max_length=86, verbose_name="kurs")
    avg_gpa = models.CharField(max_length=86, verbose_name="Gpa-bali")
    education_type = models.CharField(max_length=86, verbose_name="ta'lim-turi")
    gender = models.CharField(max_length=56, verbose_name="jinsi")
    semester = models.CharField(max_length=56, verbose_name="semestr")

    group = models.ForeignKey(
        StudentGroup,
        on_delete=models.SET_NULL,
        null=True,
        related_name='students'
    )

    date_created = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f''
    
    
class StudentGirls(models.Model):
    """Qiz talabalar uchun qo'shimcha ma'lumotlar"""
    
    ORPHAN_TYPES = [
        ('chin_yetim', 'Chin yetim'),
        ('yarim_yetim', 'Yarim yetim'),
        ('yetim_emas', 'Yetim emas'),
    ]
    
    ETHICS_TYPES = [
        ('qizil', 'Qizil'),
        ('sariq', 'Sariq'),
        ('yashil', 'Yashil'),
    ]
    
    MARITAL_STATUS = [
        ('turmush_qurgan', 'Turmush qurgan'),
        ('turmush_qurmagan', 'Turmush qurmagan'),
        ('ajrashgan', 'Ajrashgan'),
    ]
    
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='girl_details',
        verbose_name="Talaba"
    )
    
    place_of_birth = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tug'ilgan joyi")
    current_address = models.CharField(max_length=256, blank=True, null=True, verbose_name="Hozirgi manzili")
    district = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tuman")
    province = models.CharField(max_length=100, blank=True, null=True, verbose_name="Viloyat")
    
    marital_status = models.CharField(
        max_length=56, 
        choices=MARITAL_STATUS,
        default='turmush_qurmagan',
        verbose_name="Oilaviy holati"
    )
    pregnancy_status = models.BooleanField(default=False, verbose_name="Homiladorlik holati")
    number_of_children = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Bolalar soni")
    
    disability_status = models.BooleanField(default=False, verbose_name="Nogironlik holati")
    disability_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nogironlik turi")
    
    orphan_status = models.CharField(
        max_length=56, 
        choices=ORPHAN_TYPES,
        default='yetim_emas',
        verbose_name="Yetim holati"
    )
    parentless_status = models.BooleanField(default=False, verbose_name="Ota-ona qaramog'idan mahrum")
    social_registry_status = models.BooleanField(default=False, verbose_name="Ijtimoiy ro'yxatda")
    
    ethics_status = models.CharField(
        max_length=56, 
        choices=ETHICS_TYPES,
        default='yashil',
        verbose_name="Axloqi"
    )
    
    special_status = models.BooleanField(default=False, verbose_name="Imtiyozli talaba")
    special_status_description = models.TextField(blank=True, null=True, verbose_name="Imtiyoz tavsifi")
    
    lens_document = models.FileField(upload_to='documents/lens/', blank=True, null=True, verbose_name="Obyektivka")
    
    notes = models.TextField(blank=True, null=True, verbose_name="Izohlar")
    
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan")
    date_updated = models.DateTimeField(auto_now=True, verbose_name="Yangilangan")

    class Meta:
        verbose_name = "Qiz talaba ma'lumotlari"
        verbose_name_plural = "Qiz talabalar ma'lumotlari"

    def __str__(self):
        return f"{self.student.student_name} - Qiz talaba"
    
    

class Tutor(models.Model):
    pass
