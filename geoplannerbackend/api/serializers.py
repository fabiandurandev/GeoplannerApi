from rest_framework import serializers
from .models import Usuario, ActividadeAgenda, Publicacion, UbicacionEvento, Inscripcion


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


# Serializer para el modelo Publicacion
class PublicacionSerializer(serializers.ModelSerializer):
    # Para crear publicación con ubicaciones
    ubicaciones = UbicacionEventoSerializer(many=True, required=False, write_only=True)
    # Mostrar ubicaciones al listar
    ubicaciones_list = UbicacionEventoSerializer(
        many=True, source="ubicacion", read_only=True
    )

    class Meta:
        model = Publicacion
        fields = "__all__"
        read_only_fields = (
            "id",
            "fecha_creacion",
        )

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

# class InscripcionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Inscripcion
#         fields = '__all__'  # Incluye todos los campos del modelo
