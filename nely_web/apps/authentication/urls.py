from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('auth/', obtain_auth_token, name='auth'),
]