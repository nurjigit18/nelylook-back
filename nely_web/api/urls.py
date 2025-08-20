from rest_framework.routers import DefaultRouter
from . import views
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    path('add/',views.ItemCreate.as_view(),name='add-view-create',),
    path('add/<int:pk>/',views.ItemRetrieveUpdateDestroy.as_view(),name='add-view-update-destroy',),
    path('api/token/', TokenObtainPairView.as_view(),name='token_obtain_pair'),
    path('api/token/refresh/',TokenRefreshView.as_view(),name='token_refresh'),
]