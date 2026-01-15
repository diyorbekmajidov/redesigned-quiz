from django.db import models
import uuid

# Create your models here.

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True, null=True)
    password = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Student(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    student_name = models.CharField(max_length=56, blank=True, null=True, verbose_name="Talaba_Ismi")
    phone_number = models.CharField(max_length=56, blank=True, null=True, verbose_name="Telfon-raqam")
    student_imeg = models.ImageField(upload_to='media/', verbose_name="rasm")
    student_id_number = models.CharField(max_length=16, unique=True, blank=True, null=True)
    email = models.CharField(max_length=86)
    passport_number = models.CharField(max_length=12, verbose_name="passport raqami")
    birth_date = models.CharField(max_length=50, verbose_name="Tug'ilgan-kun-sanasi")
    groups = models.JSONField()
    studentStatus = models.CharField(max_length=86, verbose_name="talaba-holati")
    paymentForm = models.CharField(max_length=86, verbose_name="to'lov shakli")
    faculty = models.CharField(max_length=86, verbose_name="fakultet")
    level = models.CharField(max_length=86, verbose_name="kurs")
    avg_gpa = models.CharField(max_length=86, verbose_name="Gpa-bali")

    date_created = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f''

class Tutor(models.Model):
    pass
