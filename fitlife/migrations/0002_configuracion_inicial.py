from django.db import migrations


def crear_configuracion(apps, schema_editor):
    configuracion = apps.get_model("fitlife", "Configuracion")
    configuracion.objects.using(schema_editor.connection.alias).get_or_create(pk=1, defaults={"capacidad": 100})


class Migration(migrations.Migration):
    dependencies = [("fitlife", "0001_initial")]
    operations = [migrations.RunPython(crear_configuracion, migrations.RunPython.noop)]
