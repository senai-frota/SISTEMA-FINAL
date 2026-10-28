"""Cancela reservas sem check-in e registra check-outs atrasados.

Uso:
  python manage.py rotina_operacional
  python manage.py rotina_operacional --loop --intervalo 60
"""
import time

from django.core.management.base import BaseCommand

from reservas.operacoes import executar_rotina


class Command(BaseCommand):
    help = (
        'Cancela automaticamente reservas sem check-in (meia-noite civil do dia '
        'seguinte ao fim da janela) e registra alertas de check-out atrasado.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--loop',
            action='store_true',
            help='Executa em ciclo contínuo (serviço Compose / systemd).',
        )
        parser.add_argument(
            '--intervalo',
            type=int,
            default=60,
            help='Intervalo em segundos entre execuções no modo --loop (padrão: 60).',
        )

    def handle(self, *args, **options):
        if options['loop']:
            intervalo = max(15, int(options['intervalo']))
            self.stdout.write(f'Rotina operacional em loop a cada {intervalo}s.')
            while True:
                self._executar()
                time.sleep(intervalo)
        else:
            self._executar()

    def _executar(self):
        resultado = executar_rotina()
        self.stdout.write(
            self.style.SUCCESS(
                'Rotina operacional: '
                f'{len(resultado["canceladas"])} cancelamento(s), '
                f'{len(resultado["checkouts_atrasados"])} check-out(s) atrasado(s).'
            )
        )
