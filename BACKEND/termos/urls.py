from django.urls import path
from .views import (
    TermoListCreateView, TermoDetailView, TermoDecisaoView, meu_status
)

urlpatterns = [
    path('', TermoListCreateView.as_view(), name='termo-list-create'),
    path('meu-status/', meu_status, name='termo-meu-status'),
    path('<int:pk>/', TermoDetailView.as_view(), name='termo-detail'),
    path('<int:pk>/decisao/', TermoDecisaoView.as_view(), name='termo-decisao'),
]
