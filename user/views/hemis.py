from django.views import View
from dotenv import load_dotenv
from django.http import HttpResponseRedirect, JsonResponse
from urllib.parse import urlencode
import requests
import os

load_dotenv()
client_id = os.getenv('CLIENT_ID_HEMIS')
client_secret = os.getenv('CLIENT_SECRET_HEMIS')
redirect_uri = os.getenv('REDIRECT_URI_HEMIS')
authorize_url = os.getenv('AUTHORIZE_URL_HEMIS')
token_url = os.getenv('TOKEN_URL_HEMIS')
resource_owner_url = os.getenv('RESOURCE_OWNER_URL')




class oAuth2Client:
    def __init__(self, client_id, client_secret, redirect_uri, authorize_url, token_url, resource_owner_url):
        self.client_secret = client_secret
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.resource_owner_url = resource_owner_url

    def get_authorization_url(self):
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
        }

        url = self.authorize_url + "?" + urlencode(payload)

        return url

    def get_access_token(self, auth_code):
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        response = requests.post(self.token_url, data=payload)
        
        return response.json()

    def get_user_details(self, access_token):
        response = requests.get(self.resource_owner_url, headers={'Authorization': f'Bearer {access_token}'})
        return response.json()


class AuthLoginView(View):
    def get(self, request):
        client = oAuth2Client(
            client_id = client_id,
            client_secret = client_secret,
            redirect_uri = redirect_uri,
            authorize_url = authorize_url,
            token_url = token_url,
            resource_owner_url = resource_owner_url
        )
        authorization_url = client.get_authorization_url()

        return HttpResponseRedirect(authorization_url)
    
class AuthCallbackView(View):
    def get(self, request):

        code = request.GET.get('code')
        if code is None: return JsonResponse({'error': 'code is missing!'})

        client = oAuth2Client(
            client_id = client_id,
            client_secret = client_secret,
            redirect_uri = redirect_uri,
            authorize_url = authorize_url,
            token_url = token_url,
            resource_owner_url = resource_owner_url
        )
        access_token_response = client.get_access_token(code)

        print(access_token_response)

        return JsonResponse({"ok", access_token_response})