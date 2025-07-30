import json
import requests
from decouple import config
from django.http import JsonResponse

APP_ID = config('APP_ID')
APP_SECRET = config('APP_SECRET')
REDIRECT_URI = config('REDIRECT_URI')
APP_ACCESS_TOKEN = config('APP_ACCESS_TOKEN')
AUTHORIZATION_CODE = config('AUTHORIZATION_CODE')
USER_ACCESS_TOKEN = config('USER_ACCESS_TOKEN')


# GET THAT URL FROM 'Customize use case' > 'API set up with Instagram Log In' > 'Set Up Instagram Business Log In'
def get_authorization_code_url(request):
    scopes = [
        'instagram_business_basic',
        'instagram_business_content_publish',
        'instagram_business_manage_messages',
        'instagram_business_manage_comments',
        'instagram_business_manage_insights'
    ]
    scope_str = '%2C'.join(scopes)
    url = (
        "https://www.instagram.com/oauth/authorize"
        f"?force_reauth=true"
        f"&client_id={APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope_str}"
    )
    # You have to visit that url, allow permissions and copy the next url that appears
    # after visiting redirected uri website
    data = {
        'url': url
    }
    return JsonResponse(data)


def get_authorization_code(request, returned_url=None):
    authorization_code = returned_url.replace(REDIRECT_URI + '?code=', '')
    data = {
        'authorization_code': authorization_code
    }
    return JsonResponse(data)


def get_user_access_token(request):
    url = f'https://api.instagram.com/oauth/access_token'
    form_data = {
        'client_id': {APP_ID},
        'client_secret': APP_SECRET,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI,
        'code': AUTHORIZATION_CODE
    }
    response = requests.post(url, data=form_data)
    data = response.json()
    print(json.dumps(data, indent=4))
    user_access_token = data['access_token']
    data = {
        'User Access Token': user_access_token
    }
    return JsonResponse(data)


def get_long_user_access_token(request):
    url = f'https://graph.instagram.com/access_token'
    payload = {
        'grant_type': 'ig_exchange_token',
        'client_secret': APP_SECRET,
        'access_token': USER_ACCESS_TOKEN
    }
    response = requests.get(url, params=payload)
    data = response.json()
    long_user_access_token = data['access_token']

    data = {
        'Long User Access Token': long_user_access_token
    }
    return JsonResponse(data)
