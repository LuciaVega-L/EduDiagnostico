from django.db import migrations


def crear_asignaturas(apps, schema_editor):
    Asignatura = apps.get_model('evaluacion', 'Asignatura')
    for codigo in ('ESP', 'MAT', 'NAT', 'SOC'):
        Asignatura.objects.using(schema_editor.connection.alias).get_or_create(codigo=codigo)


class Migration(migrations.Migration):
    dependencies = [('evaluacion', '0001_initial')]
    operations = [migrations.RunPython(crear_asignaturas, migrations.RunPython.noop)]
