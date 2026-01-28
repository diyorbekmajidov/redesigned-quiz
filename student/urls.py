from django.urls import path, include
from .views.one_id import One_code
from .views.hemis import AuthCallbackView, AuthLoginView, LogoutView

urlpatterns = [
    path("one_code/", One_code.as_view(), name="one_code"),

    path('login/', AuthLoginView.as_view(), name='login'),
    path('callback/', AuthCallbackView.as_view(), name='oauth_callback'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
