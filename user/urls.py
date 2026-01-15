from django.urls import path, include
from .views.one_id import One_code
from .views.hemis import AuthCallbackView, AuthLoginView

urlpatterns = [
    path("one_code/", One_code.as_view(), name="one_code"),

    path('auth/', AuthLoginView.as_view(), name='oauth_login'),
    path('callback/', AuthCallbackView.as_view(), name='oauth_callback'),
]
