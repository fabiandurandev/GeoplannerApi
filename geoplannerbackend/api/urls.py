from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UsuarioViewSet,
    ActividadAgendaViewSet,
    PublicacionViewSet,
    UbicacionEventoViewSet,
    InscripcionViewSet,
    estadisticas_admin
)

router = DefaultRouter()
router.register(r"usuarios", UsuarioViewSet, basename="usuario")
router.register(r"actividades", ActividadAgendaViewSet, basename="actividad")
router.register(r"publicaciones", PublicacionViewSet, basename="publicacion")
router.register(r"ubicaciones", UbicacionEventoViewSet, basename="ubicacion")
router.register(r'inscripciones', InscripcionViewSet, basename='inscripcion')

urlpatterns = [
    path("", include(router.urls)),
    path("estadisticas/", estadisticas_admin, name="estadisticas_admin")
]
