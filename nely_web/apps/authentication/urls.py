from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    RefreshView,
    LogoutView,
    MeView,
    ChangePasswordView,
    ValidateTokenView,
    SendVerificationEmailView,
    VerifyEmailView,
    RequestPasswordResetView,
    ResetPasswordView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/",    LoginView.as_view(),    name="auth-login"),
    path("refresh/",  RefreshView.as_view(),  name="auth-refresh"),
    path("logout/",   LogoutView.as_view(),   name="auth-logout"),
    path("me/",       MeView.as_view(),       name="auth-me"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("validate/", ValidateTokenView.as_view(), name="auth-validate"),
    
    #Email sending
    path("send-verification/", SendVerificationEmailView.as_view(), name="send-verification"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("request-password-reset/", RequestPasswordResetView.as_view(), name="request-password-reset"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]
