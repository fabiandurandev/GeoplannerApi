from rest_framework import viewsets, status, mixins
from rest_framework.decorators import api_view
from django.db.models import Count
from datetime import datetime
from rest_framework.response import Response
from .models import Usuario, ActividadeAgenda, Publicacion, UbicacionEvento, Inscripcion
from .serializers import (
    UsuarioSerializer,
    ActividadAgendaSerializer,
    PublicacionSerializer,
    UbicacionEventoSerializer,
    InscripcionSerializer
)
from geopy import Nominatim
from functools import lru_cache
import numpy as np
from sklearn.linear_model import LinearRegression
import os


# Vista para el modelo Usuario
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    lookup_field = "id"  # Para que los endpoints usen UUID en lugar de pk

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

# class InscripcionViewSet(viewsets.ModelViewSet):
#     queryset = Inscripcion.objects.all()
#     serializer_class = InscripcionSerializer
#     lookup_field = "id"

#     def create(self, request, *args, **kwargs):
#         """
#         Crea una inscripción. Si el usuario ya está inscrito a la publicación,
#         devuelve un error 400.
#         """
#         id_usuario = request.data.get("id_usuario")
#         id_publicacion = request.data.get("id_publicacion")

#         # Verificar si ya existe una inscripción
#         if Inscripcion.objects.filter(
#             id_usuario=id_usuario, id_publicacion=id_publicacion
#         ).exists():
#             return Response(
#                 {"detail": "El usuario ya está inscrito en esta publicación."},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         # Crear inscripción normalmente
#         return super().create(request, *args, **kwargs)

#     def partial_update(self, request, *args, **kwargs):
#         """
#         Permite actualizar solo el estado de asistencia.
#         """
#         instance = self.get_object()
#         estado = request.data.get("estado_asistencia", None)

#         if estado is None:
#             return Response(
#                 {"detail": "Debe enviar el campo 'estado_asistencia'."},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         instance.estado_asistencia = estado
#         instance.save()
#         serializer = self.get_serializer(instance)
#         return Response(serializer.data)

@lru_cache(maxsize=100)  # para evitar repetir búsquedas a las mismas coordenadas
def obtener_direccion(lat, lon):
    geolocator = Nominatim(user_agent="geoplanner")
    try:
        location = geolocator.reverse(f"{lat}, {lon}", language="es", timeout=10)
        if location and location.address:
            partes = location.address.split(",")
            if len(partes) >= 3:
                # Ejemplo: "Plaza Bolívar, Maracaibo, Venezuela"
                return f"{partes[0].strip()}, {partes[-3].strip()}"
            return location.address
        else:
            return f"{lat}, {lon}"
    except Exception:
        return f"{lat}, {lon}"

@api_view(['GET'])
def estadisticas_admin(request):
    ## Endpoint combinado para el dashboard de administradores

    #@ Eventos por categoria
    CATEGORIA_NOMBRES = dict(Publicacion.CATEGORIA_OPCIONES)

    categorias = (
        Publicacion.objects.values('categoria')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    categorias_dict = {
        CATEGORIA_NOMBRES.get(c['categoria'], c['categoria']): c['total']
        for c in categorias
    }

    #@ Inscripciones por categoria
    CATEGORIA_NOMBRES = dict(Publicacion.CATEGORIA_OPCIONES)
    inscripciones_por_categoria = (
        Inscripcion.objects.values('publicacion__categoria')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    inscripciones_categoria_dict = {
        CATEGORIA_NOMBRES.get(i['publicacion__categoria'], i['publicacion__categoria']): i['total']
        for i in inscripciones_por_categoria
    }

    # Imprimir para ver los datos de inscripciones por categoria
    print(inscripciones_categoria_dict)

    #@ Eventos por estado (vigente, finalizado, cancelado)
    estados = (
        Publicacion.objects.values('estado')
        .annotate(total=Count('id'))
    )
    estados_dict = {
        e['estado']: e['total'] for e in estados
    }

    #@ Usuarios registrados por mes
    usuarios_por_mes = [0] * 12
    for u in Usuario.objects.all():
        mes = u.fecha_registro.month - 1
        usuarios_por_mes[mes] += 1

    #@ Ubicaciones mas usadas
    ubicaciones = (
        UbicacionEvento.objects.values('latitud', 'longitud')
        .annotate(total=Count('id'))
    )
    ubicaciones_dict = {}
    for u in ubicaciones:
        direccion = obtener_direccion(u['latitud'], u['longitud'])
        ubicaciones_dict[direccion] = u['total']
    
    ## Crecimiento de usuarios (usuarios por mes)
    usuarios_por_mes = [0] * 12
    for u in Usuario.objects.all():
        mes = u.fecha_registro.month - 1
        usuarios_por_mes[mes] += 1

    meses = np.array(range(1, 13)).reshape(-1, 1)
    modelo_usuarios = LinearRegression()
    modelo_usuarios.fit(meses, usuarios_por_mes)
    prediccion_usuarios = modelo_usuarios.predict(meses).tolist()

    ## Relación entre cantidad de eventos y usuarios
    total_usuarios = Usuario.objects.count()
    total_eventos = Publicacion.objects.count()
    eventos_vs_usuarios = {"usuarios": total_usuarios, "eventos": total_eventos}

    ## Relación entre “me gusta” y número de inscripciones
    likes = list(Publicacion.objects.values_list("me_gusta", flat=True))
    inscripciones = [
        Inscripcion.objects.filter(publicacion=p).count()
        for p in Publicacion.objects.all()
    ]

    if likes and inscripciones:
        modelo_likes = LinearRegression()
        X = np.array(likes).reshape(-1, 1)
        y = np.array(inscripciones)
        modelo_likes.fit(X, y)
        predicciones_likes = modelo_likes.predict(X).tolist()
    else:
        predicciones_likes = []

    #@ RESPUESTA JSON
    data = {
        "categorias": categorias_dict,
        "estados": estados_dict,
        "usuarios_por_mes": usuarios_por_mes,
        "ubicaciones": ubicaciones_dict,
        "inscripciones_por_categoria": inscripciones_categoria_dict, 
    }

    data.update({
        "regresion_usuarios": {
            "meses": list(range(1, 13)),
            "reales": usuarios_por_mes,
            "prediccion": prediccion_usuarios,
        },
        "eventos_vs_usuarios": eventos_vs_usuarios,
        "likes_vs_inscripciones": {
            "likes": likes,
            "inscripciones": inscripciones,
            "prediccion": predicciones_likes,
        },
    })

    return Response(data)