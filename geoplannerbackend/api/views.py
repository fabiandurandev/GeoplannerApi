from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from .models import Usuario, ActividadeAgenda, Publicacion, UbicacionEvento
from .serializers import (
    UsuarioSerializer,
    ActividadAgendaSerializer,
    PublicacionSerializer,
    UbicacionEventoSerializer,
)
import os


# Vista para el modelo Usuario
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    lookup_field = "id"  # Para que los endpoints usen UUID en lugar de pk

    def create(self, request, *args, **kwargs):
        nombre_usuario = request.data.get("nombre_usuario")
        email = request.data.get("email")

        # Validar si ya existe el usuario
        if Usuario.objects.filter(nombre_usuario=nombre_usuario).exists():
            return Response(
                {"error": "El nombre de usuario ya está en uso."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar si ya existe el email
        if Usuario.objects.filter(email=email).exists():
            return Response(
                {"error": "El correo electrónico ya está registrado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Si pasa las validaciones, crear el usuario normalmente
        return super().create(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # Eliminar imagen de perfil de la BDD al borrar usuario
        if instance.foto_perfil and os.path.isfile(instance.foto_perfil.path):
            os.remove(instance.foto_perfil.path)
        instance.delete()

    def perform_update(self, serializer):
        # Eliminar imagen anterior si se sube una nueva
        instance = self.get_object()
        new_image = self.request.FILES.get("foto_perfil")
        if (
            new_image
            and instance.foto_perfil
            and os.path.isfile(instance.foto_perfil.path)
        ):
            os.remove(instance.foto_perfil.path)
        serializer.save()


# Vista para el modelo ActividadeAgenda
class ActividadAgendaViewSet(viewsets.ModelViewSet):
    queryset = ActividadeAgenda.objects.all()
    serializer_class = ActividadAgendaSerializer
    lookup_field = "id"  # Usamos UUID en la URL

    def perform_destroy(self, instance):
        # Eliminar todas las ubicaciones asociadas
        instance.ubicacion.all().delete()
        # Luego eliminar la actividad
        instance.delete()


# Vista para el modelo Publicacion
class PublicacionViewSet(viewsets.ModelViewSet):
    queryset = Publicacion.objects.all()
    serializer_class = PublicacionSerializer
    lookup_field = "id"

    def perform_destroy(self, instance):
        # Borrar todas las ubicaciones asociadas al eliminar la publicación
        instance.ubicacion.all().delete()
        instance.delete()


# Vista para el modelo UbicacionEvento
class UbicacionEventoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Endpoint de Ubicaciones:
    - Listar ubicaciones
    - Consultar una ubicación
    - Actualizar una ubicación existente
    - Eliminar una ubicación existente
    - No se permite crear aquí
    """

    queryset = UbicacionEvento.objects.all()
    serializer_class = UbicacionEventoSerializer
    lookup_field = "id"
