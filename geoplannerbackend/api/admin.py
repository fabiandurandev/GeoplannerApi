from django.contrib import admin
from .models import Usuario


# Register your models here.


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("nombre_usuario", "email", "rol", "verificado")
    readonly_fields = ("rol",)  # Para que no sea editable desde formularios genéricos

    # Para permitir cambiar rol solo dentro de admin:
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()  # superuser puede editar todo
        return ("rol",)  # otros usuarios no pueden modificar rol
