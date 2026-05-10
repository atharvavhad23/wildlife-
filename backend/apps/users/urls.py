from django.urls import path

from .views import send_otp_view, verify_otp_view


urlpatterns = [
    path('send-otp/', send_otp_view, name='send-otp'),
    path('verify-otp/', verify_otp_view, name='verify-otp'),
]