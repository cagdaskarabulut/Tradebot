from django.contrib import admin
from django.urls import path
from django.conf.urls import url, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    url(r'^',include('trade.apps.binance.urls')), 
    url(r'^admin/', admin.site.urls),
]
