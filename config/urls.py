from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from pedidos import views_publicos

handler404 = 'django.views.defaults.page_not_found'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='usuarios:post_login'), name='home'),
    # Catálogo público (HU-13): sin login, pensado para compartir por link.
    path('catalogo/', include('pedidos.urls')),
    # Tienda online pública por negocio (/t/<slug>/).
    path('t/<slug:slug>/', views_publicos.catalogo_negocio, name='catalogo_negocio'),
    path('t/<slug:slug>/agregar/', views_publicos.pedido_agregar_publico, name='pedido_agregar_publico'),
    path('t/<slug:slug>/quitar/', views_publicos.pedido_quitar_publico, name='pedido_quitar_publico'),
    path('t/<slug:slug>/carrito/', views_publicos.pedido_carrito_publico, name='pedido_carrito_publico'),
    path('t/<slug:slug>/confirmar/', views_publicos.pedido_confirmar_publico, name='pedido_confirmar_publico'),
    path('usuarios/', include('usuarios.urls')),
    path('clientes/', include('clientes.urls')),
    path('ventas/', include('ventas.urls')),
    path('administracion/', include('administracion.urls')),
    # Panel de superadmin (solo is_superuser=True).
    path('superadmin/', include('administracion.urls_superadmin')),
]
