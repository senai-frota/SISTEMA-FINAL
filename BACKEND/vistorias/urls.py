from django.urls import path
from .views import (
    VistoriaListCreateView, VistoriaDetailView,
    FotoVistoriaListCreateView, FotoVistoriaDetailView,
    upload_multiplas_fotos, registrar_vistoria, ultima_quilometragem
)

urlpatterns = [
    path('', VistoriaListCreateView.as_view(), name='vistoria-list-create'),
    # Check-in / check-out completo (vistoria + fotos + status) em 1 requisição atômica
    path('registrar/', registrar_vistoria, name='vistoria-registrar'),
    # Km inicial herdado do último check-out do veículo
    path('ultima-quilometragem/', ultima_quilometragem, name='vistoria-ultima-km'),
    path('fotos/', FotoVistoriaListCreateView.as_view(), name='foto-list-create'),
    path('fotos/<int:pk>/', FotoVistoriaDetailView.as_view(), name='foto-detail'),
    path('<int:pk>/', VistoriaDetailView.as_view(), name='vistoria-detail'),
    path('<int:vistoria_id>/upload-fotos/', upload_multiplas_fotos, name='vistoria-upload-fotos'),
]