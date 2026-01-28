from django.contrib import admin

# Register your models here.
from .models import UserSession, LoginHistory
admin.site.register(UserSession)
admin.site.register(LoginHistory)