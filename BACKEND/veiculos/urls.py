from django.urls import path

from .views import (
    VeiculoListCreateView,
    VeiculoDetailView,
    VeiculoImagemView,
    MarcaListView,
    ModeloListView,
    AnoListView,
    DetalhesFipeView,
)


urlpatterns = [
    path(
        '',
        VeiculoListCreateView.as_view(),
        name='veiculo-list-create',
    ),

    path(
        'marcas/',
        MarcaListView.as_view(),
        name='marca-list',
    ),

    path(
        'marcas/<int:codigo_marca>/modelos/',
        ModeloListView.as_view(),
        name='modelo-list',
    ),

    path(
        'marcas/<int:codigo_marca>/modelos/<int:codigo_modelo>/anos/',
        AnoListView.as_view(),
        name='ano-list',
    ),

    path(
        '<int:pk>/',
        VeiculoDetailView.as_view(),
        name='veiculo-detail',
    ),

    path(
        '<int:pk>/imagem/',
        VeiculoImagemView.as_view(),
        name='veiculo-imagem',
    ),

    path(
        'marcas/<int:codigo_marca>/modelos/<int:codigo_modelo>/anos/<str:codigo_ano>/',
        DetalhesFipeView.as_view(),
        name='detalhes-fipe',
    ),
]