# Recria a tabela veiculos_veiculobackup quando ela estiver ausente.
#
# Diagnóstico (PostgreSQL/Supabase):
# - 0002_veiculobackup criou a tabela e permanece registrada.
# - Depois, 0003_delete_veiculobackup (arquivo removido do repo, mas ainda
#   presente em django_migrations) dropou a tabela.
# - O model VeiculoBackup continua no código e no estado das migrations
#   em disco (via 0002), porém a tabela física sumiu.
#
# Esta migration NÃO altera o estado do model (já existe desde 0002).
# No banco, cria a tabela somente se ela ainda não existir — assim
# ambientes limpos (onde 0002 já criou a tabela) e o PostgreSQL
# inconsistente ficam ambos corretos.

from django.db import connection, migrations


def recreate_veiculobackup_if_missing(apps, schema_editor):
    table_name = 'veiculos_veiculobackup'
    existing = set(connection.introspection.table_names())
    if table_name in existing:
        return
    VeiculoBackup = apps.get_model('veiculos', 'VeiculoBackup')
    schema_editor.create_model(VeiculoBackup)


class Migration(migrations.Migration):

    dependencies = [
        ('veiculos', '0003_veiculo_data_ultima_manutencao_veiculo_km_atual_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(
                    recreate_veiculobackup_if_missing,
                    migrations.RunPython.noop,
                ),
            ],
        ),
    ]
