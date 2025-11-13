from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UsuarioViewSet,
    ActividadAgendaViewSet,
    PublicacionViewSet,
    UbicacionEventoViewSet,
    LoginView,
    InscripcionViewSet,
    LikePublicacionViewSet,
    ComentarioPublicacionViewSet,
    chatbot_view,
)

router = DefaultRouter()
router.register(r"usuarios", UsuarioViewSet, basename="usuario")
router.register(r"actividades", ActividadAgendaViewSet, basename="actividad")
router.register(r"publicaciones", PublicacionViewSet, basename="publicacion")
router.register(r"ubicaciones", UbicacionEventoViewSet, basename="ubicacion")
router.register(r"inscripciones", InscripcionViewSet, basename="inscripcion")
router.register(r"likes", LikePublicacionViewSet, basename="likes")
router.register(r"comentarios", ComentarioPublicacionViewSet, basename="comentarios")

urlpatterns = [
    path("", include(router.urls)),
    path("login/", LoginView.as_view(), name="login"),
    path("chatbot/", chatbot_view, name="chatbot"),
]
