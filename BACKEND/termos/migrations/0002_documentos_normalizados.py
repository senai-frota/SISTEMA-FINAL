from django.db import migrations, models
import re


def normalizar_documentos_existentes(apps, schema_editor):
    TermoResponsabilidade = apps.get_model('termos', 'TermoResponsabilidade')
    for termo in TermoResponsabilidade.objects.all().iterator():
        termo.cpf_normalizado = re.sub(r'\D', '', termo.cpf or '')
        termo.cnh_normalizada = re.sub(r'\D', '', termo.cnh or '')
        termo.save(update_fields=['cpf_normalizado', 'cnh_normalizada'])


class Migration(migrations.Migration):

    dependencies = [
        ('termos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='termoresponsabilidade',
            name='cpf_normalizado',
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=11),
        ),
        migrations.AddField(
            model_name='termoresponsabilidade',
            name='cnh_normalizada',
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=11),
        ),
        migrations.RunPython(normalizar_documentos_existentes, migrations.RunPython.noop),
    ]