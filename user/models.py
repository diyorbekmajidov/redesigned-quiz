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
    

class StudentGirls(models.Model):
    place_of_birth = models.CharField(max_length=100, verbose_name="Tug'ilgan joyi")
    current_address = models.CharField(max_length=256, verbose_name="Hozirgi manzili")
    marital_status = models.CharField(max_length=56, verbose_name="Oilaviy holati")
    pregancy_status = models.CharField(max_length=56, verbose_name="Homiladorlik holati")
    number_of_children = models.CharField(max_length=56, verbose_name="Bolalar soni")
    disability_status = models.CharField(max_length=56, verbose_name="Nogironlik holati")
    orphan_type = models.Choices('Chin yetim', 'Yarim yetim', 'Yetim emas')
    orphan_status = models.CharField(max_length=56, choices=orphan_type, verbose_name="Yetim holati")
    parentless_status = models.CharField(max_length=56, verbose_name="Ota-ona qaramog’idan mahrum bo’lganlar")
    social_registry_status = models.CharField(max_length=56, verbose_name="Ijtimoiy ro’yxatda turadigan (ayollar daftari)")
    ethics_type = models.Choices('Qizil', 'Sariq', 'Yashil')
    ethics_status = models.CharField(max_length=56, choices=ethics_type, verbose_name="Axloqi")
    special_status = models.CharField(max_length=56, verbose_name="Imtiyoz bilan talaba bo’lganlar")
    lens = models.FileField(upload_to='media/', verbose_name="Obyektivka")

    date_created = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.student_name}'
    
class StudentGroups(models.Model):
    group_name = models.CharField(max_length=56, verbose_name="Guruh nomi")
    group_code = models.CharField(max_length=56, verbose_name="Guruh kodi")
    group_faculty = models.CharField(max_length=56,  verbose_name="Guruh fakulteti")
    group_level = models.CharField(max_length=56, verbose_name="Guruh kursi")
    group_year = models.CharField(max_length=56, verbose_name="Guruh yili")
    student = models.ManyToManyField(Student, related_name='student_groups')

    date_created = models.DateTimeField(auto_now_add=True)
    date_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.group_name}'

class Tutor(models.Model):
    pass
