from django.contrib import admin

# Register your models here.
from .models import User, Student, StudentGirls, StudentGroups

class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'student_id_number', 'email', 'faculty', 'level', 'studentStatus')
    search_fields = ('student_name', 'student_id_number', 'email')
    list_filter = ('faculty', 'level', 'studentStatus')


class StudentGirlsAdmin(admin.ModelAdmin):
    list_display = ('place_of_birth', 'current_address', 'marital_status', 'pregancy_status')
    search_fields = ('place_of_birth', 'current_address')
    list_filter = ('marital_status', 'pregancy_status')

class StudentGroupsAdmin(admin.ModelAdmin):
    list_display = ('group_name', 'group_code')
    search_fields = ('group_name', 'group_code')
    list_filter = ('group_faculty', 'group_level', 'group_year')

admin.site.register(Student, StudentAdmin)
admin.site.register(StudentGirls, StudentGirlsAdmin)
admin.site.register(StudentGroups, StudentGroupsAdmin)
admin.site.register(User)
