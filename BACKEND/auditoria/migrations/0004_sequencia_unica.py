from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auditoria', '0003_selar_registros_existentes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registroauditoria',
            name='sequencia',
            field=models.PositiveBigIntegerField(editable=False, unique=True, verbose_name='Sequência'),
        ),
    ]
