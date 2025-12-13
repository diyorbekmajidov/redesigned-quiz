from django.urls import path, include
from .views.one_id import One_code

urlpatterns = [
    path("one_code/", One_code.as_view(), name="one_code")
]
