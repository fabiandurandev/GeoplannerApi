from rest_framework import viewsets, status, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import models
from .models import (
    Usuario,
    ActividadeAgenda,
    Publicacion,
    UbicacionEvento,
    Inscripciones,
    LikePublicacion,
    ComentarioPublicacion,
)
from .serializers import (
    UsuarioSerializer,
    ActividadAgendaSerializer,
    PublicacionSerializer,
    UbicacionEventoSerializer,
    LoginSerializer,
    InscripcionSerializer,
    LikePublicacionSerializer,
    ComentarioPublicacionSerializer,
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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        usuario_id = self.request.query_params.get("usuario_id")
        context["usuario_id"] = usuario_id  # Guardamos el usuario actual
        return context

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


# Vista para Login
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        nombre_usuario = serializer.validated_data["nombre_usuario"]
        password = serializer.validated_data["password"]

        try:
            usuario = Usuario.objects.get(nombre_usuario=nombre_usuario)
        except Usuario.DoesNotExist:
            return Response(
                {"error": "El usuario no existe."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Aquí podrías usar hashing (por ahora, comparación directa)
        if usuario.password_hash != password:
            return Response(
                {"error": "Contraseña incorrecta."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Si todo está bien, devolver datos del usuario
        return Response(
            {
                "id": usuario.id,
                "nombre_usuario": usuario.nombre_usuario,
                "nombre": usuario.nombre,
                "apellido": usuario.apellido,
                "email": usuario.email,
                "foto_perfil": usuario.foto_perfil.url if usuario.foto_perfil else None,
                "mensaje": "Inicio de sesión exitoso.",
            },
            status=status.HTTP_200_OK,
        )


# Vista de inscripciones
class InscripcionViewSet(viewsets.ModelViewSet):
    queryset = Inscripciones.objects.all()
    serializer_class = InscripcionSerializer
    lookup_field = "id"

    def create(self, request, *args, **kwargs):
        """
        Crea una inscripción. Si el usuario ya está inscrito a la publicación,
        devuelve un error 400.
        """
        id_usuario = request.data.get("id_usuario")
        id_publicacion = request.data.get("id_publicacion")

        # Verificar si ya existe una inscripción
        if Inscripciones.objects.filter(
            id_usuario=id_usuario, id_publicacion=id_publicacion
        ).exists():
            return Response(
                {"detail": "El usuario ya está inscrito en esta publicación."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Crear inscripción normalmente
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        Permite actualizar solo el estado de asistencia.
        """
        instance = self.get_object()
        estado = request.data.get("estado_asistencia", None)

        if estado is None:
            return Response(
                {"detail": "Debe enviar el campo 'estado_asistencia'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.estado_asistencia = estado
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# Vista para likes en publicaciones
class LikePublicacionViewSet(viewsets.ModelViewSet):
    queryset = LikePublicacion.objects.all()
    serializer_class = LikePublicacionSerializer
    lookup_field = "id"

    def create(self, request, *args, **kwargs):
        """Un usuario solo puede dar like una vez por publicación."""
        id_usuario = request.data.get("id_usuario")
        id_publicacion = request.data.get("id_publicacion")

        if LikePublicacion.objects.filter(
            id_usuario=id_usuario, id_publicacion=id_publicacion
        ).exists():
            return Response(
                {"detail": "El usuario ya dio 'me gusta' a esta publicación."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Registrar like
        response = super().create(request, *args, **kwargs)

        # Incrementar contador de likes en Publicacion
        Publicacion.objects.filter(id=id_publicacion).update(
            me_gusta=models.F("me_gusta") + 1
        )
        return response

    def destroy(self, request, *args, **kwargs):
        """Al eliminar un like, restar 1 al contador."""
        instance = self.get_object()
        id_publicacion = instance.id_publicacion.id
        response = super().destroy(request, *args, **kwargs)
        Publicacion.objects.filter(id=id_publicacion).update(
            me_gusta=models.F("me_gusta") - 1
        )
        return response


# Vista para comentarios en publicaciones
class ComentarioPublicacionViewSet(viewsets.ModelViewSet):
    queryset = ComentarioPublicacion.objects.all()
    serializer_class = ComentarioPublicacionSerializer
    lookup_field = "id"

    def create(self, request, *args, **kwargs):
        """Registrar un comentario y aumentar contador."""
        id_publicacion = request.data.get("id_publicacion")

        response = super().create(request, *args, **kwargs)

        # Incrementar contador de comentarios
        Publicacion.objects.filter(id=id_publicacion).update(
            comentarios=models.F("comentarios") + 1
        )
        return response

    def destroy(self, request, *args, **kwargs):
        """Eliminar comentario y restar contador."""
        instance = self.get_object()
        id_publicacion = instance.id_publicacion.id

        response = super().destroy(request, *args, **kwargs)

        Publicacion.objects.filter(id=id_publicacion).update(
            comentarios=models.F("comentarios") - 1
        )
        return response
