from rest_framework import viewsets, status, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import models
import requests
from .models import (
    Usuario,
    ActividadeAgenda,
    Publicacion,
    UbicacionEvento,
    Inscripciones,
    LikePublicacion,
    ComentarioPublicacion,
    Conversacion,
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
from rest_framework.decorators import api_view
from geopy import Nominatim
from functools import lru_cache
import numpy as np
from sklearn.linear_model import LinearRegression
from django.db.models import Count

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


# Vista para el chatbot
## ENDPOINT DE LA CONVERSACION
@api_view(["POST"])
def chatbot_view(request):
    """
    Chatbot con historial persistente en base de datos
    """
    user_id = request.data.get("usuario_id")
    mensaje_usuario = request.data.get("mensaje")

    if not user_id or not mensaje_usuario:
        return Response({"error": "Datos incompletos."}, status=400)

    try:
        usuario = Usuario.objects.get(id=user_id)
    except Usuario.DoesNotExist:
        return Response({"error": "Usuario no encontrado."}, status=404)

    # Guardar mensaje del usuario
    Conversacion.objects.create(
        usuario=usuario, remitente="usuario", mensaje=mensaje_usuario
    )

    # Obtener historial (últimos 10 mensajes)
    historial = Conversacion.objects.filter(usuario=usuario).order_by("-fecha")[:10]
    contexto = "\n".join(
        [f"{msg.remitente.upper()}: {msg.mensaje}" for msg in reversed(historial)]
    )

    # Llamar a la API de Gemini
    GEMINI_API_KEY = (
        "AIzaSyDz5L6yyl3vsYXHq_HX5wZjMDLUlG8BcBw"  ## <-- CLAVE DE FRANGER... OJITO
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Eres Geo IA, el asistente oficial de la aplicación móvil GeoPlanner "
                            "la cual es una aplicacion tipo red social que ayuda a los usuarios a "
                            "subir eventos, ver ubicaciones de eventos, hacer publicaciones de eventos, "
                            "cambiar la privacidad de dichos eventos, inscribirse a eventos publicos o de amigos, etc..., "
                            "desarrollada por los estudiantes de URBE: Franger Alastre, Valeria Socorro, Luis Villalobos, Fabian Duran, y pueden ser contactados por medio de "
                            "f.alastre@urbe.edu.ve ."
                            "NO tienes relación con ArcGIS GeoPlanner "
                            "ni con ningún producto de Esri.\n\n"
                            "REGLAS ESTRICTAS:\n"
                            "1. SOLO puedes responder preguntas relacionadas con la aplicación móvil GeoPlanner.\n"
                            "2. Tambien puedes responder a preguntas relacionadas con la hora, la fecha actual y a saludos cordiales.\n"
                            "3. Si el usuario pregunta algo que NO sea sobre GeoPlanner, sobre la hora y fecha, o si no es un saludo, sobre quienes son los creadores o desarrolladores de GeoPlanner y como contactarlos, o sobre que es Geoplanner debes responder:\n"
                            '"Lo siento mucho, pero solo puedo ayudarte a usar GeoPlanner. '
                            'Te recomiendo usar otras fuentes para ese tipo de preguntas."\n'
                            "4. Tus respuestas deben ser cortas, claras y prácticas.\n"
                            "5. Responde siempre como un asistente amable y útil.\n"
                            "6. Cuando el usuario pregunte sobre funcionalidades, guíalo paso a paso.\n"
                            "7. Nunca hables de ArcGIS, Esri, o cualquier software externo.\n"
                            "8. No inventes información de funcionalidades que no existen.\n\n"
                            "Aquí tienes el historial para contexto:\n"
                            f"{contexto}\n\n"
                            "Ahora responde la última pregunta del usuario:\n"
                            f"{mensaje_usuario}"
                        )
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        data = response.json()
        print("🔹 Respuesta de Gemini:", data)
        respuesta_bot = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("❌ Error al procesar Gemini:", e)
        respuesta_bot = "Lo siento, hubo un error al procesar tu mensaje."

    # Guardar respuesta del bot
    Conversacion.objects.create(usuario=usuario, remitente="bot", mensaje=respuesta_bot)

    return Response({"respuesta": respuesta_bot})


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


@api_view(["GET"])
def estadisticas_admin(request):
    ## Endpoint combinado para el dashboard de administradores

    # @ Eventos por categoria
    CATEGORIA_NOMBRES = dict(Publicacion.CATEGORIA_OPCIONES)

    categorias = (
        Publicacion.objects.values("categoria")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    categorias_dict = {
        CATEGORIA_NOMBRES.get(c["categoria"], c["categoria"]): c["total"]
        for c in categorias
    }

    # @ Inscripciones por categoria
    CATEGORIA_NOMBRES = dict(Publicacion.CATEGORIA_OPCIONES)
    inscripciones_por_categoria = (
        Inscripciones.objects.values("id_publicacion__categoria")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    inscripciones_categoria_dict = {
        CATEGORIA_NOMBRES.get(
            i["publicacion__categoria"], i["publicacion__categoria"]
        ): i["total"]
        for i in inscripciones_por_categoria
    }

    # Imprimir para ver los datos de inscripciones por categoria
    print(inscripciones_categoria_dict)

    # @ Eventos por estado (vigente, finalizado, cancelado)
    estados = Publicacion.objects.values("estado").annotate(total=Count("id"))
    estados_dict = {e["estado"]: e["total"] for e in estados}

    # @ Usuarios registrados por mes
    usuarios_por_mes = [0] * 12
    for u in Usuario.objects.all():
        mes = u.fecha_registro.month - 1
        usuarios_por_mes[mes] += 1

    # @ Ubicaciones mas usadas
    ubicaciones = UbicacionEvento.objects.values("latitud", "longitud").annotate(
        total=Count("id")
    )
    ubicaciones_dict = {}
    for u in ubicaciones:
        direccion = obtener_direccion(u["latitud"], u["longitud"])
        ubicaciones_dict[direccion] = u["total"]

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
        Inscripciones.objects.filter(id_publicacion=p).count()
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

    # @ RESPUESTA JSON
    data = {
        "categorias": categorias_dict,
        "estados": estados_dict,
        "usuarios_por_mes": usuarios_por_mes,
        "ubicaciones": ubicaciones_dict,
        "inscripciones_por_categoria": inscripciones_categoria_dict,
    }

    data.update(
        {
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
        }
    )

    return Response(data)
