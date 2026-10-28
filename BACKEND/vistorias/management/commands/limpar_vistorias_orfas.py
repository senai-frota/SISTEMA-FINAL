from django.core.management.base import BaseCommand
from django.db.models import Count

from vistorias.models import Vistoria


class Command(BaseCommand):
    """
    Lista ou remove vistorias sem fotos associadas.

    Registros nessa condição bloqueiam novo check-in/check-out pela
    constraint única (reserva, tipo).

    Uso:
      python manage.py limpar_vistorias_orfas          # dry-run
      python manage.py limpar_vistorias_orfas --apagar
    """

    help = 'Remove vistorias sem fotos que estão travando check-in/check-out.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apagar',
            action='store_true',
            help='Sem essa flag, o comando só lista o que seria removido (dry-run).',
        )

    def handle(self, *args, **options):
        orfas = Vistoria.objects.annotate(n_fotos=Count('fotos')).filter(n_fotos=0)

        if not orfas.exists():
            self.stdout.write(self.style.SUCCESS('Nenhuma vistoria órfã encontrada.'))
            return

        self.stdout.write(f'Encontradas {orfas.count()} vistoria(s) sem fotos:')
        for v in orfas:
            self.stdout.write(
                f'  - Vistoria #{v.id} | {v.get_tipo_display()} | '
                f'Reserva #{v.reserva_id} | criada em {v.data_hora}'
            )

        if options['apagar']:
            total, _ = orfas.delete()
            self.stdout.write(self.style.SUCCESS(f'Removidas. ({total} registro(s) apagado(s) no total)'))
        else:
            self.stdout.write(self.style.WARNING(
                'Nada foi apagado (dry-run). Rode novamente com --apagar para remover de fato.'
            ))
