from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

handler404 = 'django.views.defaults.page_not_found'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='usuarios:post_login'), name='home'),
    path('usuarios/', include('usuarios.urls')),
    path('ventas/', include('ventas.urls')),
    path('administracion/', include('administracion.urls')),
]
