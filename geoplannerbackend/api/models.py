from django.db import models
import uuid
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation


# Create your models here.


# Tabla Usuario
class Usuario(models.Model):
    GENERO_OPCIONES = [
        ("M", "Masculino"),
        ("F", "Femenino"),
        ("O", "Otro"),
        ("N", "Prefiero no decirlo"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_usuario = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    genero = models.CharField(max_length=1, choices=GENERO_OPCIONES, default="N")
    foto_perfil = models.ImageField(upload_to="fotos_perfil/", null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    biografia = models.TextField(blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    ciudad = models.CharField(max_length=100, null=True, blank=True)
    pais = models.CharField(max_length=100, null=True, blank=True)
    tema_prefefrido = models.CharField(max_length=100, blank=True)
    verificado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


# Tabla de actividades en la agenda de un usuario
class ActividadeAgenda(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    ubicacion = GenericRelation("UbicacionEvento")
    descripcion = models.TextField()
    fecha_activiad = models.DateField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)


# Tabla para crear eventos y publicaciones
class Publicacion(models.Model):
    CATEGORIA_OPCIONES = [
        ("SOC", "Social"),
        ("CUL", "Cultural"),
        ("DEP", "Deportivo"),
        ("ACA", "Académico"),
        ("OTR", "Otro"),
    ]

    PRIVACIDAD_OPCIONES = [
        ("PUB", "Público"),
        ("PRI", "Privado"),
        ("AMI", "Amigos"),
    ]

    ESTADO_EVENTO_OPCIONES = [
        ("VIG", "Vigente"),
        ("FIN", "Finalizado"),
        ("CAN", "Cancelado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    categoria = models.CharField(
        choices=CATEGORIA_OPCIONES, max_length=50, default="OTR"
    )
    privacidad = models.CharField(
        choices=PRIVACIDAD_OPCIONES, max_length=50, default="PUB"
    )
    estado = models.CharField(
        choices=ESTADO_EVENTO_OPCIONES, max_length=50, default="VIG"
    )
    terminos_condiciones = models.TextField()
    capacidad_maxima = models.IntegerField()
    ubicacion = GenericRelation("UbicacionEvento")
    fecha_evento = models.DateTimeField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    me_gusta = models.IntegerField(default=0)
    comentarios = models.IntegerField(default=0)

    def __str__(self):
        return f"Publicación de {self.id_usuario.nombre_usuario} en {self.fecha_evento}"


# Tabla donde se almacenan las imagenes de las publicaciones
class ImagenPublicacion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    publicacion = models.ForeignKey(
        Publicacion, on_delete=models.CASCADE, related_name="imagenes"
    )
    imagen = models.ImageField(upload_to="publicaciones/")


# Tabla de ubicaciones para eventos y publicaciones
class UbicacionEvento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
