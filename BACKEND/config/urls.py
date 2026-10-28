"""
URL configuration for projeto_frota_senai project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/usuarios/', include('usuarios.urls')),
    path('api/veiculos/', include('veiculos.urls')),
    path('api/reservas/', include('reservas.urls')),
    path('api/vistorias/', include('vistorias.urls')),
    path('api/termos/', include('termos.urls')),
    path('api/auditoria/', include('auditoria.urls')),
    path('api/relatorios/', include('relatorios.urls')),
]

# Frontend agora é o app React separado (frota-senai-frontend),
# rodando em http://localhost:5173 e consumindo essa API.

# Com storage local, o Django precisa servir /media/ para CNH, termos e
# fotos de vistoria serem abertos depois do upload (também com DEBUG=False).
# Com Supabase Storage, as URLs apontam para o bucket (assinadas) e esta
# rota não é necessária.
if not getattr(settings, 'USE_SUPABASE_STORAGE', False):
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
