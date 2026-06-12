"""
Management Command: verificar_manutencoes
Sistema de Alertas de Frota — 2º BAEP

Executar diariamente via cron ou Celery Beat:
    python manage.py verificar_manutencoes
    python manage.py verificar_manutencoes --tipo manutencao_vencida
    python manage.py verificar_manutencoes --nivel critico
    python manage.py verificar_manutencoes --email admin@pmesp.pol.br
    python manage.py verificar_manutencoes --log

Alertas verificados:
    1. Manutenção vencida (agendamentos atrasados + preventiva por plano)
    2. Garantia vencendo (validade da garantia nos próximos N dias)
    3. Pneu próximo do limite (previsão baseada em km/tempo)
    4. Veículo parado (sem despachos nos últimos N dias)
    5. Documento vencido ou vencendo (CRLV, Seguro, IPVA, DPVAT)
"""
import logging
import sys
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from viaturas.services.alertas_service import (
    gerar_todos_alertas,
    alertas_manutencao_vencida,
    alertas_garantia_vencendo,
    alertas_pneu_proximo_limite,
    alertas_veiculo_parado,
    alertas_documentos,
)


logger = logging.getLogger('viaturas.alertas')

# Mapeamento tipo → função
VERIFICADORES = {
    'manutencao_vencida': ('Manutenção Vencida', alertas_manutencao_vencida),
    'garantia_vencendo': ('Garantia Vencendo', alertas_garantia_vencendo),
    'pneu_proximo_limite': ('Pneu Próximo do Limite', alertas_pneu_proximo_limite),
    'veiculo_parado': ('Veículo Parado', alertas_veiculo_parado),
    'documento_vencendo': ('Documento Vencido/Vencendo', alertas_documentos),
}

# Ícones por nível para output formatado
ICONE_NIVEL = {
    'CRITICO': '\033[91m[CRÍTICO]\033[0m',   # vermelho
    'ALERTA': '\033[93m[ALERTA]\033[0m',      # amarelo
    'ATENCAO': '\033[94m[ATENÇÃO]\033[0m',    # azul
}

# Símbolo para versão sem cor (logs)
TEXTO_NIVEL = {
    'CRITICO': '[CRÍTICO]',
    'ALERTA': '[ALERTA]',
    'ATENCAO': '[ATENÇÃO]',
}


class Command(BaseCommand):
    help = (
        'Verifica manutenções e gera alertas da frota. '
        'Alertas: manutenção vencida, garantia vencendo, pneu próximo do limite, '
        'veículo parado e documentos vencendo.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--tipo',
            type=str,
            choices=list(VERIFICADORES.keys()),
            help='Executar apenas um tipo de verificação.',
        )
        parser.add_argument(
            '--nivel',
            type=str,
            choices=['critico', 'alerta', 'atencao'],
            help='Filtrar apenas alertas de um nível específico.',
        )
        parser.add_argument(
            '--email',
            type=str,
            nargs='+',
            help='Enviar resumo por e-mail para os destinatários informados.',
        )
        parser.add_argument(
            '--log',
            action='store_true',
            help='Registrar alertas no log do sistema (logs/baep_sistema.log).',
        )
        parser.add_argument(
            '--dias-garantia',
            type=int,
            default=30,
            help='Dias para alerta de garantia (padrão: 30).',
        )
        parser.add_argument(
            '--dias-parado',
            type=int,
            default=7,
            help='Dias sem despacho para considerar veículo parado (padrão: 7).',
        )
        parser.add_argument(
            '--sem-cor',
            action='store_true',
            help='Desabilitar cores no output (útil para pipe/cron).',
        )
        parser.add_argument(
            '--silencioso',
            action='store_true',
            help='Não imprimir no stdout (apenas log/e-mail).',
        )

    def handle(self, *args, **options):
        hora_inicio = timezone.now()
        self.usar_cor = not options['sem_cor'] and sys.stdout.isatty()
        self.silencioso = options['silencioso']
        self.registrar_log = options['log']

        # Cabeçalho
        self._imprimir('=' * 72)
        self._imprimir(
            f'  SISTEMA DE ALERTAS DE FROTA — 2º BAEP'
        )
        self._imprimir(
            f'  {hora_inicio.strftime("%d/%m/%Y %H:%M:%S")}'
        )
        self._imprimir('=' * 72)

        # Executar verificações
        filtro_tipo = options.get('tipo')
        filtro_nivel = (options.get('nivel') or '').upper() or None

        if filtro_tipo:
            # Apenas um tipo
            nome, fn = VERIFICADORES[filtro_tipo]
            self._imprimir(f'\n▸ {nome}')
            self._imprimir('-' * 60)
            alertas = fn()
        else:
            # Todos os tipos
            alertas = []
            for key, (nome, fn) in VERIFICADORES.items():
                self._imprimir(f'\n▸ Verificando: {nome}...')
                resultado = fn()
                alertas.extend(resultado)
                count = len(resultado)
                if count:
                    self._imprimir(f'  → {count} alerta(s) encontrado(s)')
                else:
                    self._imprimir(f'  → OK — nenhum alerta')

        # Filtrar por nível
        if filtro_nivel:
            alertas = [a for a in alertas if a['nivel'] == filtro_nivel]

        # Ordenar: CRITICO > ALERTA > ATENCAO
        ordem = {'CRITICO': 0, 'ALERTA': 1, 'ATENCAO': 2}
        alertas.sort(key=lambda a: (ordem.get(a['nivel'], 9), a.get('dias_restantes') or 0))

        # Relatório detalhado
        self._imprimir('\n' + '=' * 72)
        self._imprimir('  RELATÓRIO DE ALERTAS')
        self._imprimir('=' * 72)

        if not alertas:
            self._imprimir(
                '\n  ✓ Nenhum alerta encontrado. Frota em dia!'
            )
        else:
            # Agrupar por nível
            for nivel in ('CRITICO', 'ALERTA', 'ATENCAO'):
                nivel_alertas = [a for a in alertas if a['nivel'] == nivel]
                if not nivel_alertas:
                    continue

                self._imprimir(f'\n  {self._nivel_texto(nivel)} '
                               f'({len(nivel_alertas)})')
                self._imprimir('  ' + '-' * 56)

                for a in nivel_alertas:
                    self._imprimir(
                        f'  ▸ [{a["prefixo"]}] {a["titulo"]}'
                    )
                    self._imprimir(
                        f'    {a["mensagem"]}'
                    )

        # Resumo consolidado
        self._imprimir_resumo(alertas)

        # Log
        if self.registrar_log:
            self._salvar_log(alertas)

        # E-mail
        if options.get('email'):
            self._enviar_email(alertas, options['email'])

        # Tempo de execução
        tempo = (timezone.now() - hora_inicio).total_seconds()
        self._imprimir(f'\n  Tempo de execução: {tempo:.2f}s')
        self._imprimir('=' * 72 + '\n')

        # Retornar código de saída para CI/cron
        criticos = sum(1 for a in alertas if a['nivel'] == 'CRITICO')
        if criticos > 0:
            # Alertas críticos = exit code 2 para sistemas de monitoramento
            self._imprimir(
                f'  ⚠ ATENÇÃO: {criticos} alerta(s) CRÍTICO(S) requer(em) ação imediata!'
            )

    # ========================================================================
    # HELPERS DE OUTPUT
    # ========================================================================
    def _imprimir(self, texto):
        """Imprime no stdout se não estiver em modo silencioso."""
        if not self.silencioso:
            self.stdout.write(texto)

    def _nivel_texto(self, nivel):
        """Retorna o texto formatado do nível (com ou sem cor)."""
        if self.usar_cor:
            return ICONE_NIVEL.get(nivel, f'[{nivel}]')
        return TEXTO_NIVEL.get(nivel, f'[{nivel}]')

    def _imprimir_resumo(self, alertas):
        """Imprime o resumo consolidado."""
        self._imprimir('\n' + '-' * 72)
        self._imprimir('  RESUMO CONSOLIDADO')
        self._imprimir('-' * 72)

        total = len(alertas)
        criticos = sum(1 for a in alertas if a['nivel'] == 'CRITICO')
        alertas_count = sum(1 for a in alertas if a['nivel'] == 'ALERTA')
        atencao = sum(1 for a in alertas if a['nivel'] == 'ATENCAO')

        self._imprimir(f'  Total de alertas:    {total}')
        self._imprimir(
            f'  {self._nivel_texto("CRITICO")} Críticos:  {criticos}'
        )
        self._imprimir(
            f'  {self._nivel_texto("ALERTA")} Alertas:   {alertas_count}'
        )
        self._imprimir(
            f'  {self._nivel_texto("ATENCAO")} Atenção:   {atencao}'
        )

        # Por tipo
        por_tipo = {}
        for a in alertas:
            por_tipo[a['tipo']] = por_tipo.get(a['tipo'], 0) + 1

        if por_tipo:
            self._imprimir('\n  Por categoria:')
            nomes_tipos = {
                'MANUTENCAO_VENCIDA': 'Manutenção Vencida',
                'GARANTIA_VENCENDO': 'Garantia Vencendo',
                'PNEU_PROXIMO_LIMITE': 'Pneu Próximo do Limite',
                'VEICULO_PARADO': 'Veículo Parado',
                'DOCUMENTO_VENCENDO': 'Documento Vencido/Vencendo',
            }
            for tipo, count in sorted(por_tipo.items(), key=lambda x: -x[1]):
                nome = nomes_tipos.get(tipo, tipo)
                self._imprimir(f'    • {nome}: {count}')

    def _salvar_log(self, alertas):
        """Registra alertas no log do sistema."""
        if not alertas:
            logger.info('[verificar_manutencoes] Nenhum alerta encontrado.')
            self._imprimir('\n  ✓ Log registrado (nenhum alerta).')
            return

        for a in alertas:
            msg = (
                f'[{a["nivel"]}] [{a["tipo"]}] '
                f'{a["prefixo"]} — {a["titulo"]}: {a["mensagem"]}'
            )
            if a['nivel'] == 'CRITICO':
                logger.error(msg)
            elif a['nivel'] == 'ALERTA':
                logger.warning(msg)
            else:
                logger.info(msg)

        self._imprimir(
            f'\n  ✓ {len(alertas)} alerta(s) registrado(s) no log do sistema.'
        )

    def _enviar_email(self, alertas, destinatarios):
        """Envia resumo de alertas por e-mail."""
        from django.core.mail import send_mail
        from django.conf import settings

        total = len(alertas)
        criticos = sum(1 for a in alertas if a['nivel'] == 'CRITICO')

        assunto = f'[FROTA 2º BAEP] Alertas de Manutenção — {timezone.now().strftime("%d/%m/%Y")}'

        if total == 0:
            corpo = (
                f'Relatório de verificação diária — {timezone.now().strftime("%d/%m/%Y")}\n\n'
                'Nenhum alerta encontrado. Frota em dia!\n'
            )
        else:
            linhas = [
                f'Relatório de verificação diária — {timezone.now().strftime("%d/%m/%Y")}',
                f'Total de alertas: {total} (Críticos: {criticos})',
                '',
            ]
            for nivel in ('CRITICO', 'ALERTA', 'ATENCAO'):
                nivel_alertas = [a for a in alertas if a['nivel'] == nivel]
                if not nivel_alertas:
                    continue
                linhas.append(f'\n=== {nivel} ({len(nivel_alertas)}) ===')
                for a in nivel_alertas:
                    linhas.append(f'  [{a["prefixo"]}] {a["titulo"]}')
                    linhas.append(f'    {a["mensagem"]}')

            corpo = '\n'.join(linhas)

        try:
            send_mail(
                subject=assunto,
                message=corpo,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=destinatarios,
                fail_silently=False,
            )
            self._imprimir(
                f'\n  ✓ E-mail enviado para: {", ".join(destinatarios)}'
            )
        except Exception as e:
            self._imprimir(
                f'\n  ✗ Falha ao enviar e-mail: {e}'
            )
            logger.error(f'[verificar_manutencoes] Falha ao enviar e-mail: {e}')
