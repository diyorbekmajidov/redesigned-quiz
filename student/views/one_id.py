from django.shortcuts import render
from django.shortcuts import redirect
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect

from rest_framework.views import APIView
from django.shortcuts import redirect
from dotenv import load_dotenv

import requests
import os

load_dotenv()

auth_url = os.getenv("auth_url")
url_hemis = os.getenv("url_hemis")
url_employee = os.getenv("url_employee")

response_type = os.getenv("response_type")
client_id = os.getenv("client_id")
redirect_url = os.getenv("redirect_uri")
scope = os.getenv("scope")
state = os.getenv("state")


class One_code(APIView):
    def get(self, request):
        params = {
            "response_type": "one_code",
            "client_id": "uzfi_uz",
            "redirect_uri": "https://interactive.uzfi.uz/auth-code/",
            "scope": "uzfi_uz",
            "state": "testState",
        }
        print(params)
        response = requests.get(auth_url, params=params)
        print(response)
        return redirect(response.url)

# def One_code(request):
#     params = {
#         "response_type": response_type,
#         "client_id": client_id,
#         "redirect_uri": redirect_url,
#         "scope": scope,
#         "state": state,
#     }
#     print(params)

#     res = requests.get(auth_url, params = params)
#     print(res)

#     return redirect(res.url)
