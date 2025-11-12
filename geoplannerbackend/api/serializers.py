from rest_framework import serializers
from .models import (
    Usuario,
    ActividadeAgenda,
    Publicacion,
    UbicacionEvento,
    Inscripciones,
    LikePublicacion,
    ComentarioPublicacion,
)


# Serializer para el modelo Usuario
class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = "__all__"  # Incluye todos los campos

    # Para ocultar el password en las respuestas si quieres
    extra_kwargs = {"password_hash": {"write_only": True}}


# Serializer para el modelo UbicacionEvento
class UbicacionEventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UbicacionEvento
        fields = ("id", "latitud", "longitud", "content_type", "object_id")
        read_only_fields = ("id", "content_type", "object_id")


# Serializer para el modelo ActividadAgenda
class ActividadAgendaSerializer(serializers.ModelSerializer):
    # Para crear la actividad con ubicaciones
    ubicaciones = UbicacionEventoSerializer(many=True, required=False, write_only=True)
    # Para listar las ubicaciones asociadas
    ubicaciones_list = UbicacionEventoSerializer(
        many=True, source="ubicacion", read_only=True
    )

    class Meta:
        model = ActividadeAgenda
        fields = "__all__"
        read_only_fields = ("id", "fecha_creacion")  # No se pueden modificar

    def create(self, validated_data):
        ubicaciones_data = validated_data.pop("ubicaciones", [])
        actividad = ActividadeAgenda.objects.create(**validated_data)

        # Crear filas en UbicacionEvento
        for ubic_data in ubicaciones_data:
            UbicacionEvento.objects.create(
                content_object=actividad,
                latitud=ubic_data["latitud"],
                longitud=ubic_data["longitud"],
            )

        return actividad

    def update(self, instance, validated_data):
        # Solo actualizar campos de la actividad (sin tocar ubicaciones)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# Serializer para likes en publicaciones
class LikePublicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LikePublicacion
        fields = "__all__"
        read_only_fields = ("id", "fecha_like")


# Serializer para comentarios en publicaciones
class ComentarioPublicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComentarioPublicacion
        fields = "__all__"
        read_only_fields = ("id", "fecha_comentario")


# Serializer para el modelo Publicacion
class PublicacionSerializer(serializers.ModelSerializer):
    # Para crear publicación con ubicaciones
    ubicaciones = UbicacionEventoSerializer(many=True, required=False, write_only=True)
    # Mostrar ubicaciones al listar
    ubicaciones_list = UbicacionEventoSerializer(
        many=True, source="ubicacion", read_only=True
    )
    likes = LikePublicacionSerializer(many=True, read_only=True)
    comentarios_publicacion = ComentarioPublicacionSerializer(many=True, read_only=True)
    ya_dio_like = serializers.SerializerMethodField()

    class Meta:
        model = Publicacion
        fields = "__all__"
        extra_fields = ["ya_dio_like"]
        read_only_fields = (
            "id",
            "fecha_creacion",
        )

    def get_ya_dio_like(self, obj):
        usuario_id = self.context.get("usuario_id")
        if usuario_id:
            return LikePublicacion.objects.filter(
                id_usuario=usuario_id, id_publicacion=obj.id
            ).exists()
        return False

    def create(self, validated_data):
        ubicaciones_data = validated_data.pop("ubicaciones", [])
        publicacion = Publicacion.objects.create(**validated_data)

        # Crear filas en UbicacionEvento
        for ubic_data in ubicaciones_data:
            UbicacionEvento.objects.create(
                content_object=publicacion,
                latitud=ubic_data["latitud"],
                longitud=ubic_data["longitud"],
            )

        return publicacion

    def update(self, instance, validated_data):
        # Actualización solo de los campos de la publicación
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# Serializer para Login
class LoginSerializer(serializers.Serializer):
    nombre_usuario = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


# Serializer para inscripciones
class InscripcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inscripciones
        fields = "__all__"
        read_only_fields = ("id",)
