from django.db import migrations


def criar_dados_iniciais(apps, schema_editor):
    Cor = apps.get_model('estoque', 'Cor')
    UnidadeFornecimento = apps.get_model('estoque', 'UnidadeFornecimento')
    UnidadeMedida = apps.get_model('estoque', 'UnidadeMedida')
    OrgaoRequisitante = apps.get_model('estoque', 'OrgaoRequisitante')
    LocalizacaoFisica = apps.get_model('estoque', 'LocalizacaoFisica')

    # === Cores MATERIAL DE CONSUMO §1 ===
    cores = ['Amarelo', 'Azul', 'Vermelho', 'Preto', 'Branco', 'Cinza', 'Verde', 'Laranja', 'Rosa', 'Marrom']
    for nome in cores:
        Cor.objects.get_or_create(nome=nome)

    # === Unidade de Fornecimento MATERIAL DE CONSUMO §1 (padrão: UNIDADE) ===
    uf, _ = UnidadeFornecimento.objects.get_or_create(
        nome='Unidade',
        defaults={'padrao': True, 'descricao': 'Unidade consumível padrão (MATERIAL DE CONSUMO §2.6)'}
    )
    if not uf.padrao:
        uf.padrao = True
        uf.save()

    # Outras unidades de fornecimento comuns
    outras_uf = [
        ('Caixa', 'Caixa com múltiplas unidades'),
        ('Pacote', 'Pacote com múltiplas unidades'),
        ('Resma', 'Resma (papel A4 — 500 folhas)'),
        ('Galão', 'Galão de líquido'),
        ('Fardo', 'Fardo'),
    ]
    for nome, desc in outras_uf:
        UnidadeFornecimento.objects.get_or_create(nome=nome, defaults={'descricao': desc})

    # === Unidades de Medida do Item MATERIAL DE CONSUMO §1 ===
    umdms = [
        ('UN', 'Unidade', 'Unidade avulsa'),
        ('PCT100G', 'Pacote 100g', 'Pacote de 100 gramas'),
        ('PCT200G', 'Pacote 200g', 'Pacote de 200 gramas'),
        ('PCT1KG', 'Pacote 1kg', 'Pacote de 1 quilograma'),
        ('GAL1L', 'Galão 1L', 'Galão de 1 litro'),
        ('GAL500ML', 'Galão 500ml', 'Galão de 500 mililitros'),
        ('ML', 'Mililitro (ml)', 'Mililitro'),
        ('L', 'Litro (l)', 'Litro'),
        ('G', 'Grama (g)', 'Grama'),
        ('KG', 'Quilograma (kg)', 'Quilograma'),
        ('M', 'Metro (m)', 'Metro'),
        ('CM', 'Centímetro (cm)', 'Centímetro'),
        ('FLH', 'Folha', 'Folha avulsa'),
        ('CX', 'Caixa', 'Caixa'),
        ('RESMA', 'Resma (500 fls)', 'Resma de papel A4 com 500 folhas'),
        ('RLO', 'Rolo', 'Rolo'),
        ('PAR', 'Par', 'Par'),
    ]
    for sigla, nome, desc in umdms:
        UnidadeMedida.objects.get_or_create(sigla=sigla, defaults={'nome': nome, 'descricao': desc})

    # === Órgãos Requisitantes MATERIAL DE CONSUMO §1 ===
    orgaos = [
        ('CMD', '2º BAEP — Comando'),
        ('SUBCMD', '2º BAEP — Subcomando'),
        ('EM/P1', 'Estado Maior / P1 — Pessoal'),
        ('EM/P2', 'Estado Maior / P2 — Inteligência'),
        ('EM/P3', 'Estado Maior / P3 — Operações'),
        ('EM/P4', 'Estado Maior / P4 — Logística'),
        ('EM/P5', 'Estado Maior / P5 — Comunicação Social'),
        ('SPJMD', 'Seção de Policiamento Judiciário Militar e Disciplinar'),
        ('1CIA', '1ª CIA'),
        ('2CIA', '2ª CIA'),
        ('3CIA', '3ª CIA'),
        ('SL', 'Setor de Logística'),
        ('SF', 'Setor Financeiro'),
        ('ADMIN', 'Administração'),
    ]
    for sigla, nome in orgaos:
        OrgaoRequisitante.objects.get_or_create(sigla=sigla, defaults={'nome': nome})

    # === Localizações Físicas MATERIAL DE CONSUMO §1 ===
    locais = [
        ('Prateleira A', 'Prateleira A do almoxarifado'),
        ('Prateleira B', 'Prateleira B do almoxarifado'),
        ('Prateleira C', 'Prateleira C do almoxarifado'),
        ('Armário 1', 'Armário 1'),
        ('Armário 2', 'Armário 2'),
        ('Almoxarifado Central', 'Almoxarifado central do BAEP'),
        ('Depósito', 'Depósito de materiais'),
    ]
    for nome, desc in locais:
        LocalizacaoFisica.objects.get_or_create(nome=nome, defaults={'descricao': desc})


def reverter_dados_iniciais(apps, schema_editor):
    # Reversão apenas limpa os dados criados por esta migration
    Cor = apps.get_model('estoque', 'Cor')
    OrgaoRequisitante = apps.get_model('estoque', 'OrgaoRequisitante')
    LocalizacaoFisica = apps.get_model('estoque', 'LocalizacaoFisica')

    nomes_cor = ['Amarelo', 'Azul', 'Vermelho', 'Preto', 'Branco', 'Cinza', 'Verde', 'Laranja', 'Rosa', 'Marrom']
    Cor.objects.filter(nome__in=nomes_cor).delete()

    siglas_orgao = ['CMD', 'SUBCMD', 'EM/P1', 'EM/P2', 'EM/P3', 'EM/P4', 'EM/P5',
                    'SPJMD', '1CIA', '2CIA', '3CIA', 'SL', 'SF', 'ADMIN']
    OrgaoRequisitante.objects.filter(sigla__in=siglas_orgao).delete()

    nomes_local = ['Prateleira A', 'Prateleira B', 'Prateleira C',
                   'Armário 1', 'Armário 2', 'Almoxarifado Central', 'Depósito']
    LocalizacaoFisica.objects.filter(nome__in=nomes_local).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0005_pap_novos_models_cadastros_mestres'),
    ]

    operations = [
        migrations.RunPython(criar_dados_iniciais, reverter_dados_iniciais),
    ]
