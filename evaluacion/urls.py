from django.urls import path

from . import views

app_name = 'evaluacion'
urlpatterns = [
    path('', views.ingreso, name='ingreso'),
    path('prueba/', views.responder, name='responder'),
    path('finalizado/', views.finalizado, name='finalizado'),
    path('salir/', views.salir, name='salir'),
]
