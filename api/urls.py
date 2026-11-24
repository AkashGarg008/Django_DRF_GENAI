from django.urls import path
from . import views

urlpatterns = [
    path('register', views.register, name='register'),
    path('login', views.login, name='login'),
    path('documents', views.documents, name='documents'),
    path('documents/<int:pk>', views.document_detail, name='document-detail'),
    path('query', views.query, name='query'),
    path('queries', views.queries, name='queries'),
]
