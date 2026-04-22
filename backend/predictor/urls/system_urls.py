"""
System URL routing: authentication, home page, and photo proxy.
"""

from django.urls import path
from predictor.views.system_views import (
    send_email_otp,
    verify_email_otp,
    index,
    photo_proxy,
)

urlpatterns = [
    path('auth/send-otp/', send_email_otp, name='send_email_otp'),
    path('auth/verify-otp/', verify_email_otp, name='verify_email_otp'),
    path('', index, name='home'),
    path('photo-proxy/', photo_proxy, name='photo_proxy'),
]
