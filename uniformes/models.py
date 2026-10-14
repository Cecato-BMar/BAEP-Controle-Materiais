from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from dateutil.relativedelta import relativedelta
from simple_history.models import HistoricalRecords


class TipoUniforme(models.Model):
    """
    Catálogo de tipos de uniforme (ex: Calça Tática, Camisa Manga Longa, Coturno).
    NOTA: Alterações no campo prazo_meses afetam apenas entregas futuras;
    entregas já registradas mantêm sua data_vencimento_calc original.
    """
    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome do Uniforme"
    )
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição"
    )
    prazo_meses = models.PositiveIntegerField(
        verbose_name="Prazo de Renovação (Meses)",
        help_text="Vida útil em meses antes de renovação. Afeta apenas novos registros de entrega."
    )
    dias_alerta = models.PositiveIntegerField(
        default=30,
        verbose_name="Dias de Alerta Prévio",
        help_text="Quantidade de dias antes do vencimento para disparar alerta."
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo"
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Tipo de Uniforme"
        verbose_name_plural = "Tipos de Uniforme"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.prazo_meses} meses)"


class EntregaUniforme(models.Model):
    """
    Registro individual de entrega de peça de uniforme a um policial.
    NOTA sobre o campo 'ativa':
    - ativa=True: Entrega regular e válida em vigor.
    - ativa=False: Desmarque apenas caso o registro tenha sido lançado incorretamente
      ou cancelado administrativamente. Não deve ser usado como 'devolução'.
    """
    policial = models.ForeignKey(
        'policiais.Policial',
        on_delete=models.PROTECT,
        related_name="entregas_uniforme",
        verbose_name="Policial"
    )
    tipo_uniforme = models.ForeignKey(
        TipoUniforme,
        on_delete=models.PROTECT,
        related_name="entregas",
        verbose_name="Tipo de Uniforme"
    )
    quantidade = models.PositiveIntegerField(
        default=1,
        verbose_name="Quantidade"
    )
    data_entrega = models.DateField(
        default=timezone.localdate,
        verbose_name="Data da Entrega"
    )
    data_vencimento_calc = models.DateField(
        editable=False,
        verbose_name="Data de Vencimento Calculada"
    )
    observacoes = models.TextField(
        blank=True,
        verbose_name="Observações"
    )
    entregue_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uniformes_entregues",
        verbose_name="Entregue por"
    )
    ativa = models.BooleanField(
        default=True,
        verbose_name="Ativa",
        help_text="Indica se a entrega está em vigor. Desmarque somente em cancelamento ou erro de lançamento."
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Entrega de Uniforme"
        verbose_name_plural = "Entregas de Uniforme"
        ordering = ["-data_entrega", "-criado_em"]

    def __str__(self):
        policial_str = str(self.policial) if self.policial else "Policial Desconhecido"
        tipo_str = self.tipo_uniforme.nome if self.tipo_uniforme else "Uniforme"
        return f"{tipo_str} (x{self.quantidade}) - {policial_str} ({self.data_entrega.strftime('%d/%m/%Y')})"

    def save(self, *args, **kwargs):
        # Cálculo automático da data de vencimento com guarda para carregamento postergado
        if self.data_entrega:
            prazo_meses = None
            try:
                if self.tipo_uniforme:
                    prazo_meses = self.tipo_uniforme.prazo_meses
            except (ObjectDoesNotExist, TipoUniforme.DoesNotExist):
                if self.tipo_uniforme_id:
                    prazo_meses = TipoUniforme.objects.filter(
                        pk=self.tipo_uniforme_id
                    ).values_list('prazo_meses', flat=True).first()

            if prazo_meses is not None:
                self.data_vencimento_calc = self.data_entrega + relativedelta(months=prazo_meses)

        super().save(*args, **kwargs)

    @property
    def dias_restantes(self):
        if not self.data_vencimento_calc:
            return None
        hoje = timezone.localdate()
        return (self.data_vencimento_calc - hoje).days

    @property
    def esta_vencido(self):
        dias = self.dias_restantes
        return dias is not None and dias < 0

    @property
    def esta_em_alerta(self):
        dias = self.dias_restantes
        if dias is None or dias < 0:
            return False
        limite = self.tipo_uniforme.dias_alerta if self.tipo_uniforme else 30
        return dias <= limite


class AlertaUniforme(models.Model):
    """
    Alerta in-app gerado diariamente pelo comando check_uniform_deadlines.
    A idempotência é garantida na lógica do comando (evitando UniqueConstraint
    com condition que é incompatível com SQLite).
    """
    entrega = models.ForeignKey(
        EntregaUniforme,
        on_delete=models.CASCADE,
        related_name="alertas",
        verbose_name="Entrega de Uniforme"
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    lido = models.BooleanField(
        default=False,
        verbose_name="Lido"
    )
    lido_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Lido em"
    )
    lido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alertas_uniforme_lidos",
        verbose_name="Lido por"
    )

    class Meta:
        verbose_name = "Alerta de Uniforme"
        verbose_name_plural = "Alertas de Uniforme"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["lido", "criado_em"])
        ]

    def __str__(self):
        status = "Lido" if self.lido else "Pendente"
        return f"Alerta [{status}] - {self.entrega}"

    def marcar_como_lido(self, user=None):
        self.lido = True
        self.lido_em = timezone.now()
        if user and user.is_authenticated:
            self.lido_por = user
        self.save(update_fields=['lido', 'lido_em', 'lido_por'])
