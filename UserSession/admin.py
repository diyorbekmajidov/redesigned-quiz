from django.contrib import admin

from .models import UserSession, LoginHistory


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Session metadata is visible, but OAuth token values are never exposed."""

    list_display = (
        'student', 'token_type', 'is_active',
        'expires_at', 'last_activity', 'created_at',
    )
    list_filter = ('is_active', 'token_type', 'expires_at')
    search_fields = ('student__student_name', 'student__student_id_number', 'session_key')
    list_select_related = ('student',)
    readonly_fields = (
        'student', 'session_key', 'token_type', 'expires_at',
        'user_agent', 'ip_address', 'device_info', 'is_active',
        'last_activity', 'created_at', 'updated_at',
        'access_token_status', 'refresh_token_status',
    )
    exclude = ('access_token', 'refresh_token')

    fieldsets = (
        ('Session ma\'lumotlari', {
            'fields': (
                'student', 'session_key', 'token_type', 'expires_at',
                'is_active', 'last_activity', 'created_at', 'updated_at',
            ),
        }),
        ('Device ma\'lumotlari', {
            'fields': ('user_agent', 'ip_address', 'device_info'),
            'classes': ('collapse',),
        }),
        ('OAuth tokenlar', {
            'fields': ('access_token_status', 'refresh_token_status'),
            'description': 'Token qiymatlari xavfsizlik sababli admin panelda ko\'rsatilmaydi.',
            'classes': ('collapse',),
        }),
    )

    def access_token_status(self, obj):
        return 'Saqlangan (qiymat yashirilgan)' if obj.access_token else 'Mavjud emas'

    access_token_status.short_description = 'Access token'

    def refresh_token_status(self, obj):
        return 'Saqlangan (qiymat yashirilgan)' if obj.refresh_token else 'Mavjud emas'

    refresh_token_status.short_description = 'Refresh token'

    def has_add_permission(self, request):
        return False


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('student', 'login_time', 'logout_time', 'success', 'device_type', 'ip_address')
    list_filter = ('success', 'device_type', 'login_time')
    search_fields = ('student__student_name', 'student__student_id_number', 'ip_address')
    list_select_related = ('student', 'session')
    readonly_fields = (
        'student', 'session', 'login_time', 'logout_time', 'ip_address',
        'user_agent', 'device_type', 'success', 'failure_reason',
    )

    def has_add_permission(self, request):
        return False
