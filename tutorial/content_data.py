# -*- coding: utf-8 -*-
"""Conteúdo padrão do Tutorial de Uso.

Estrutura: MODULOS = [ {icone, nome, slug, descricao, grupo, ordem,
                        secoes: [ {titulo, tipo, conteudo(html)}, ... ] } ]

Tipos de seção (tipo): TEXTO | PASSO | DICA | ALERTA | TABELA
O conteúdo aceita HTML básico e classes Bootstrap (alert, table, ul, code...).
"""

MODULOS = [
    # ======================================================================
    # 1) VISÃO GERAL E PRIMEIROS PASSOS
    # ======================================================================
    {
        'icone': 'fa-solid fa-compass',
        'nome': 'Visão Geral e Primeiros Passos',
        'slug': 'visao-geral',
        'descricao': 'Como acessar, navegar e entender o controle de acesso '
                     'do sistema. O ponto de partida para todo novo usuário.',
        'grupo': '',
        'ordem': 1,
        'secoes': [
            {
                'titulo': 'Como acessar o sistema',
                'tipo': 'PASSO',
                'conteudo': '''
<ol class="mb-3">
    <li>Abra o navegador (Chrome ou Edge recomendados) e acesse o endereço do sistema informado pela seção de T.I. da unidade (ex.: <code>http://10.43.19.224:8000/</code>).</li>
    <li>Você verá a tela de <strong>Login</strong>. Informe seu <strong>nome de usuário</strong> e <strong>senha</strong> fornecidos pelo administrador.</li>
    <li>Clique em <strong>Entrar</strong>.</li>
    <li>Ao acessar, você cai no <strong>Painel Geral</strong>, o seletor de módulos que dá acesso a cada área do sistema conforme sua permissão.</li>
    <li>Para sair com segurança, clique no seu nome (canto superior direito) e escolha <strong>Sair</strong>.</li>
</ol>
<div class="alert alert-warning">
    <i class="fas fa-key me-2"></i><strong>Licença:</strong> o sistema é protegido por licença contratual.
    Se a licença estiver em período de tolerência (grace period), um aviso aparece no topo — procure o administrador para renovar.
</div>
''',
            },
            {
                'titulo': 'Conhecendo a tela inicial',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O sistema possui um layout fixo com três áreas principais:</p>
<ul>
    <li><strong>Barra superior (navbar)</strong> — identidade do sistema, acesso ao seu perfil, alteração de senha e saída.</li>
    <li><strong>Menu lateral (sidebar)</strong> — navegação por módulos. Menus com seta <i class="fas fa-chevron-right"></i> abrem submenus. O menu exibido depende do seu grupo de acesso.</li>
    <li><strong>Área de conteúdo</strong> — onde as telas, listagens, formulários e relatórios são exibidos.</li>
</ul>
<p>O <strong>Painel Geral</strong> (tela após o login) apresenta cartões com os módulos que você pode acessar. A seção <strong>Serviços ao Policial</strong> está disponível para todos: <em>Solicitar Material</em>, <em>Suporte de T.I.</em> e <em>Baixa de Viatura</em>.</p>
''',
            },
            {
                'titulo': 'Controle de acesso por grupos (permissões)',
                'tipo': 'ALERTA',
                'conteudo': '''
<p>O acesso é baseado em <strong>grupos de permissão (RBAC)</strong>. Para operar um módulo, o usuário precisa pertencer ao grupo correspondente:</p>
<table class="table table-sm table-bordered">
    <thead><tr><th>Módulo</th><th>Grupo</th></tr></thead>
    <tbody>
        <tr><td>Reserva de Armas / Cautelas</td><td><code>reserva_armas</code></td></tr>
        <tr><td>Estoque de Consumo / Gestão de Pedidos</td><td><code>materiais</code></td></tr>
        <tr><td>Frota de Viaturas</td><td><code>frota</code></td></tr>
        <tr><td>Patrimônio</td><td><code>patrimonio</code></td></tr>
        <tr><td>Telemática e T.I.</td><td><code>telematica</code></td></tr>
        <tr><td>Material Bélico</td><td><code>material_belico</code></td></tr>
        <tr><td>Usuários e Administração</td><td><code>administracao</code></td></tr>
    </tbody>
</table>
<div class="alert alert-danger">
    <i class="fas fa-ban me-2"></i>Se o menu de um módulo não aparece para você, sua conta não possui o grupo necessário.
    Solicite ao administrador do sistema a inclusão do seu usuário no grupo adequado.
</div>
<p>O usuário <strong>superusuário</strong> (administrador geral) tem acesso liberado a tudo. O acesso de cada módulo é validado em todas as telas — não basta conhecer o endereço da URL.</p>
''',
            },
            {
                'titulo': 'Fluxo geral de trabalho',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O sistema segue um ciclo lógico em todos os módulos:</p>
<ol>
    <li><strong>Cadastro</strong> — materiais, armas, viaturas, patrimônio, efetivo e usuários são cadastrados uma única vez.</li>
    <li><strong>Estoque</strong> — entradas (compras, devoluções, importações) e saídas (requisições, cautelas, descartes) atualizam o saldo automaticamente.</li>
    <li><strong>Movimentação</strong> — retiradas, devoluções, despachos e transferências geram histórico com usuário e data.</li>
    <li><strong>Relatório</strong> — qualquer período pode ser consolidado em PDF ou Excel para registro oficial e assinatura.</li>
</ol>
<p>Cada módulo deste tutorial detalha essas etapas na prática. Navegue na ordem sugerida para uma formação completa.</p>
''',
            },
            {
                'titulo': 'Dicas de uso diário',
                'tipo': 'DICA',
                'conteudo': '''
<ul>
    <li><strong>Formulários em janela:</strong> vários cadastros abrem em pop-up. Ao fechar a janela, a página de origem é atualizada automaticamente — não clique em "atualizar" manualmente antes de fechar.</li>
    <li><strong>Buscas:</strong> quase todas as listagens têm barra de busca (ex.: por RE, prefixo, placa, hostname) e filtros por status.</li>
    <li><strong>Datas:</strong> os calendários vêm travados na data atual. Datas retrógradas exigem autorização superior.</li>
    <li><strong>Aplicação móvel (PWA):</strong> o sistema pode ser instalado como aplicativo no celular (manifest e service worker).</li>
    <li><strong>Período de treino:</strong> crie dados de exemplo no ambiente de testes antes de usar o ambiente de produção.</li>
</ul>
''',
            },
        ],
    },

    # ======================================================================
    # 2) RESERVA DE ARMAS
    # ======================================================================
    {
        'icone': 'fa-solid fa-gun',
        'nome': 'Reserva de Armas (Cautelas)',
        'slug': 'reserva-armas',
        'descricao': 'Controle de armamentos, coletes, rádios e equipamentos: '
                     'cadastro, cautela (retirada), devolução e recibo oficial.',
        'grupo': 'reserva_armas',
        'ordem': 2,
        'secoes': [
            {
                'titulo': 'Visão geral do módulo',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O módulo de <strong>Reserva de Armas</strong> controla o arsenal individual e o fluxo de <strong>cautelas</strong> (retiradas) e <strong>devoluções</strong> de materiais como armas, coletes, rádios, algemas e equipamentos de choque.</p>
<p>Principais conceitos do cadastro de material:</p>
<ul>
    <li><strong>Tipo</strong> — Arma, Munição, Colete, Rádio, Algema, Outros.</li>
    <li><strong>Categoria</strong> — Pistola, Fuzil, Calibre 12, Submetralhadora, Lançador, Choque.</li>
    <li><strong>Status</strong> — Disponível, Em Uso, Manutenção, Apreendido, Baixado.</li>
    <li><strong>Quantidades</strong> — total, disponível e em uso; o sistema atualiza automaticamente a cada cautela/devolução.</li>
</ul>
''',
            },
            {
                'titulo': 'Dashboard da Reserva de Armas',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>Acessível pelo menu <strong>Reserva de Armas &gt; Visão Geral</strong>, reúne:</p>
<ul>
    <li>KPIs de materiais (total, disponíveis, em uso, manutenção) e de efetivo.</li>
    <li><strong>Monitor de Fluxo Recente</strong> — últimas movimentações do dia/mês.</li>
    <li><strong>Materiais mais movimentados do mês</strong> e <strong>policiais com mais retiradas</strong>.</li>
    <li><strong>Documentos recentes</strong> — últimos relatórios gerados.</li>
</ul>
''',
            },
            {
                'titulo': 'Cadastrar um material (armamento)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Reserva de Armas &gt; Armamentos</strong> e clique em <strong>Novo Material</strong>.</li>
    <li>Preencha: <strong>Tipo</strong>, <strong>Categoria</strong>, <strong>Nome</strong> (ex.: "Pistola Glock 9mm"), <strong>Número</strong> (série, único), <strong>Quantidade Total</strong>, <strong>Estado</strong> (Novo/Bom/Regular/Ruim/Péssimo) e <strong>Status</strong>.</li>
    <li>Campos opcionais: observações, imagem e localização física.</li>
    <li>Salve. A <strong>quantidade disponível</strong> é iniciada automaticamente igual à quantidade total.</li>
</ol>
<div class="alert alert-info">
    <i class="fas fa-info-circle me-2"></i>O número do material é único no sistema. Cadastros duplicados são bloqueados.
</div>
''',
            },
            {
                'titulo': 'Importar armas em lote (XML)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Armamentos &gt; Importar XML</strong>.</li>
    <li>Anexe o arquivo XML gerado pelo sistema oficial (estrutura <em>Subunidade &gt; Arma</em>).</li>
    <li>Confirme a importação. O sistema faz a <strong>triagem automática</strong>, criando os materiais por subunidade e evitando duplicidades.</li>
    <li>Revise o resumo da importação na listagem.</li>
</ol>
''',
            },
            {
                'titulo': 'Fazer uma cautela (retirada)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Cautelas &gt; Nova Retirada</strong>.</li>
    <li>Selecione o <strong>policial</strong> (o sistema exige policial com situação ATIVO).</li>
    <li>Adicione os <strong>materiais</strong> desejados e as quantidades. A seleção múltipla é feita no próprio formulário.</li>
    <li>Confirme. O sistema valida a quantidade em estoque e, se houver lote de munição vinculado, o saldo do lote.</li>
    <li>Ao salvar, o estoque é <strong>deduzido automaticamente</strong> e o material passa a <strong>Em Uso</strong>.</li>
    <li>Imprima o <strong>Recibo de Cautela</strong> gerado automaticamente em PDF para assinatura.</li>
</ol>
<div class="alert alert-warning">
    <i class="fas fa-exclamation-triangle me-2"></i>Não é possível retirar quantidade maior que o saldo disponível.
</div>
''',
            },
            {
                'titulo': 'Registrar uma devolução',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Cautelas &gt; Nova Devolução</strong>.</li>
    <li>Informe a cautela/material a devolver e as quantidades devolvidas.</li>
    <li>Se houver <strong>diferença</strong> (disparos ou extravios), informe a quantidade correspondente. O sistema exigirá <strong>justificativa</strong> e, para munição disparada, o <strong>número do B.O.</strong>.</li>
    <li>Confirme. O estoque é reposto e o material volta a <strong>Disponível</strong>.</li>
</ol>
<p>Devoluções com divergência geram automaticamente um <strong>Registro de Disparo de Munição</strong> para auditoria.</p>
''',
            },
            {
                'titulo': 'Recibo oficial (PDF)',
                'tipo': 'DICA',
                'conteudo': '''
<p>O recibo de cautela é gerado no formato <strong>A5</strong> com o cabeçalho oficial da PMESP e blocos de assinatura (retirada e devolução).</p>
<ul>
    <li>Para <strong>reimprimir</strong> um recibo antigo: Cautelas &gt; ícone de detalhes da movimentação &gt; <strong>Gerar Recibo Oficial (PDF)</strong>.</li>
    <li>O histórico de movimentações é <strong>inalterável</strong> — todas as alterações ficam registradas com usuário e data.</li>
</ul>
''',
            },
            {
                'titulo': 'Regras e boas práticas',
                'tipo': 'ALERTA',
                'conteudo': '''
<ul>
    <li>O estoque nunca pode ficar negativo — a saída maior que o saldo é bloqueada.</li>
    <li>Os status (Disponível / Em Uso / Manutenção) são controlados automaticamente pelas movimentações.</li>
    <li>Exclusão de material só é permitida quando não há movimentações vinculadas.</li>
    <li>Mantenha o cadastro de <strong>efetivo</strong> atualizado: cautela só pode ser feita para policial ATIVO.</li>
</ul>
''',
            },
        ],
    },

    # ======================================================================
    # 3) MUNIÇÕES
    # ======================================================================
    {
        'icone': 'fa-solid fa-layer-group',
        'nome': 'Munições',
        'slug': 'municoes',
        'descricao': 'Controle de lotes de munição, retiradas operacionais e de '
                     'instrução, devoluções com estojos, disparos e devolução à CPI.',
        'grupo': 'reserva_armas',
        'ordem': 3,
        'secoes': [
            {
                'titulo': 'Visão geral do módulo',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O módulo de <strong>Munições</strong> gerencia lotes por calibre, retiradas e devoluções com conciliação de <strong>estojos</strong>, registro de <strong>disparos</strong> e <strong>devolução à CPI</strong>.</p>
<p>Menu lateral (dentro de Reserva de Armas): <strong>Dashboard</strong>, <strong>Lotes</strong>, <strong>Movimentações</strong>, <strong>Relatórios</strong> e <strong>Devolução CPI</strong>.</p>
<ul>
    <li><strong>Tipos de munição</strong> — Real, Treinamento, Festim, Elastômero.</li>
    <li><strong>Calibre</strong> e <strong>marca</strong> identificam o lote; número do lote é único por material.</li>
</ul>
''',
            },
            {
                'titulo': 'Cadastrar um lote de munição',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Munições &gt; Lotes &gt; Novo Lote</strong>.</li>
    <li>Informe: <strong>material</strong> (tipo Munição), <strong>calibre</strong>, <strong>marca/fabricante</strong>, <strong>número do lote</strong>, <strong>tipo de munição</strong>.</li>
    <li>Preencha <strong>data de fabricação</strong> e <strong>data de validade</strong> — essenciais para o alerta de vencidos.</li>
    <li>Informe a <strong>quantidade inicial</strong> (a atual é preenchida automaticamente) e, se aplicável, a quantidade de <strong>estojos</strong>.</li>
    <li>Salve. O lote passa a compor o saldo de munição do material.</li>
</ol>
<div class="alert alert-info">
    <i class="fas fa-info-circle me-2"></i>Lotes vencidos são sinalizados na listagem e devem ser tratados conforme a norma.
</div>
''',
            },
            {
                'titulo': 'Realizar uma retirada de munição',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Munições &gt; Nova Retirada</strong>.</li>
    <li>Informe o <strong>lote</strong> (com saldo disponível), o <strong>policial</strong> (busca rápida) e a <strong>quantidade</strong>.</li>
    <li>Selecione o <strong>tipo de uso</strong>: <strong>OPERACIONAL</strong> ou <strong>INSTRUÇÃO</strong>.</li>
    <li>Confirme. A baixa no lote e no estoque do material ocorre em transação segura (sem risco de duplicidade).</li>
</ol>
''',
            },
            {
                'titulo': 'Registrar a devolução de munição',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Munições &gt; Nova Devolução</strong>.</li>
    <li>Selecione a retirada pendente. O sistema mostra a <strong>quantidade pendente</strong> de devolução.</li>
    <li>Informe a quantidade devolvida e a quantidade de <strong>estojos</strong>.</li>
    <li>Se houver diferença (munição não devolvida), o formulário exigirá <strong>justificativa</strong> e, conforme o caso, <strong>sindicância</strong> ou <strong>B.O.</strong> — regras de negócio validadas automaticamente.</li>
    <li>Confirme. O lote é reabastecido.</li>
</ol>
''',
            },
            {
                'titulo': 'Devolução à CPI',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Munições &gt; Devolução CPI</strong>.</li>
    <li>Informe os quantitativos de <strong>cartuchos</strong> e <strong>estojos</strong> a devolver à CPI.</li>
    <li>Registre as referências da remessa e confirme para gerar o registro e o histórico da movimentação.</li>
</ol>
''',
            },
            {
                'titulo': 'Relatórios e fechamento',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O módulo gera relatórios de auditoria em PDF:</p>
<ul>
    <li><strong>Relatório de munições</strong> — consolidação de lotes, retiradas, devoluções, disparos e CPI em um período.</li>
    <li><strong>Fechamento de retirada</strong> — conciliação por retirada (documento de fechamento oficial).</li>
    <li><strong>Relatório por lote</strong> — histórico completo de um lote (entradas, saídas, saldo).</li>
</ul>
<p>A <strong>linha do tempo unificada</strong> (Movimentações) reúne retiradas, devoluções e devoluções à CPI em ordem cronológica.</p>
''',
            },
            {
                'titulo': 'Regras do módulo',
                'tipo': 'ALERTA',
                'conteudo': '''
<ul>
    <li>Toda <strong>munição disparada</strong> é registrada com movimentação de disparo e justificativa.</li>
    <li>Diferenças de estojo ou munição na devolução exigem <strong>justificativa formal</strong>; casos de instrução seguem regra específica de estojos.</li>
    <li>O saldo de um lote nunca pode ser ultrapassado numa retirada.</li>
    <li>Lotes com validade vencida aparecem destacados e não devem ser movimentados sem autorização.</li>
</ul>
''',
            },
        ],
    },

    # ======================================================================
    # 4) MATERIAL BÉLICO
    # ======================================================================
    {
        'icone': 'fa-solid fa-crosshairs',
        'nome': 'Material Bélico',
        'slug': 'material-belico',
        'descricao': 'Base completa do arsenal: armas longas, pistolas, acessórios, '
                     'kits operacionais, munição química e proteção balística, com '
                     'alertas normativos e relatórios por categoria.',
        'grupo': 'material_belico',
        'ordem': 4,
        'secoes': [
            {
                'titulo': 'Visão geral do módulo',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O módulo de <strong>Material Bélico</strong> é a fonte oficial do arsenal do batalhão, organizada por categoria com rastreabilidade completa (histórico de alterações em cada item).</p>
<p>Principais blocos disponíveis no menu:</p>
<ul>
    <li><strong>Dashboard</strong> — KPIs e alertas normativos (RN).</li>
    <li><strong>Importar Excel</strong> — planilha oficial do batalhão.</li>
    <li>Armamentos: fuzis, espingardas, pistolas, mosquetões e transferências.</li>
    <li>Acessórios: red dots, magnificadores, supressores e vinculações.</li>
    <li>Rádios (HT e móveis), TASER, algemas e munição (convencional e química).</li>
    <li>Proteção balística: coletes, escudos e capacetes.</li>
    <li><strong>Kits Operacionais</strong> — kits de prontidão com composição padronizada.</li>
</ul>
''',
            },
            {
                'titulo': 'Dashboard e alertas normativos',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O dashboard concentra a situação do arsenal e alertas automáticos:</p>
<ul>
    <li><strong>RN-02</strong> — composição e situação dos kits operacionais.</li>
    <li><strong>RN-03</strong> — validade da munição química e convencional.</li>
    <li><strong>RN-07</strong> — baterias/troca dos TASER.</li>
</ul>
<p>Os alertas orientam a manutenção preventiva antes que os itens saiam do padrão.</p>
''',
            },
            {
                'titulo': 'Importar planilha Excel oficial',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Material Bélico &gt; Importar Excel</strong>.</li>
    <li>Anexe a planilha oficial do batalhão (colunas padronizadas). O sistema <strong>normaliza os cabeçalhos</strong> automaticamente.</li>
    <li>Confirme. Os itens são criados ou atualizados por categoria (fuzis, espingardas, pistolas, rádios, kits, etc.).</li>
    <li>Acompanhe o resumo da importação e revise na listagem correspondente.</li>
</ol>
''',
            },
            {
                'titulo': 'Armamentos e acessórios',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>Cada categoria tem sua <strong>listagem, cadastro, edição e exclusão</strong> específicos:</p>
<ul>
    <li><strong>Fuzis</strong> e <strong>Espingardas</strong> — armas longas (cada item com seus campos de série e situação).</li>
    <li><strong>Pistolas Glock</strong> e <strong>Taurus</strong> — armas curtas com numeração própria.</li>
    <li><strong>Mosquetões</strong> e <strong>transferências pendentes</strong> de armas.</li>
    <li><strong>Red dot, magnificador e supressor</strong> — acessórios de pontaria.</li>
    <li><strong>Vinculações</strong> — associação de acessório a um fuzil específico (rastreabilidade do conjunto).</li>
</ul>
''',
            },
            {
                'titulo': 'Kits operacionais (RN-01)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Material Bélico &gt; Kits Operacionais</strong>.</li>
    <li>Cadastre um kit (nome e composição). A regra RN-01 define os itens de prontidão.</li>
    <li>No detalhe do kit, visualize seus itens por número de série.</li>
    <li>Pode-se usar o kit como atalho na cautela: o sistema localiza os materiais correspondentes pelos números de série.</li>
</ol>
''',
            },
            {
                'titulo': 'Rádios, menos letais e munição',
                'tipo': 'TEXTO',
                'conteudo': '''
<ul>
    <li><strong>Rádios HT</strong>, <strong>AM640</strong> e <strong>AM600</strong> — rádios portáteis e móveis com controle de série.</li>
    <li><strong>TASER</strong> — alerta de <strong>bateria</strong> conforme RN-07; controle de disparos.</li>
    <li><strong>Algemas</strong> — estoque por par.</li>
    <li><strong>Munição química</strong> — controle de validade (RN-03).</li>
    <li><strong>Munição convencional</strong> — distribuição aos kits conforme RN-05.</li>
</ul>
''',
            },
            {
                'titulo': 'Proteção balística',
                'tipo': 'TEXTO',
                'conteudo': '''
<ul>
    <li><strong>Coletes balísticos</strong> — controle individual por série.</li>
    <li><strong>Escudos balísticos</strong> e <strong>capacetes balísticos</strong> — inventário do equipamento de proteção.</li>
</ul>
<p>Todo item do módulo mantém <strong>histórico de alterações</strong> (quem alterou, quando e o quê) para auditoria.</p>
''',
            },
            {
                'titulo': 'Relatórios detalhados por categoria',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>No <strong>Dashboard do Material Bélico</strong>, use o seletor de relatório para escolher categoria e formato (<strong>PDF</strong> ou <strong>Excel</strong>).</li>
    <li>Alternativamente, na listagem de fuzis ou espingardas, clique no botão de <strong>relatório da categoria</strong>.</li>
    <li>Há ainda relatórios de <strong>todo o arsenal</strong>: <em>Relatório Detalhado</em> em Excel e em PDF.</li>
    <li>Baixe e imprima para controle e assinatura.</li>
</ol>
''',
            },
            {
                'titulo': 'Sincronização com a Reserva de Armas',
                'tipo': 'DICA',
                'conteudo': '''
<p>O Material Bélico é <strong>sincronizado automaticamente</strong> com o módulo de Reserva de Armas: ao cadastrar ou alterar o status de um item bélico, o material correspondente na Reserva de Armas é atualizado (e vice-versa), inclusive o status <strong>Em Uso</strong>.</p>
<div class="alert alert-warning">
    <i class="fas fa-sync-alt me-2"></i>Use um único módulo como referência de cadastro para evitar divergência; o sistema faz a ponte entre eles automaticamente.
</div>
''',
            },
        ],
    },

    # ======================================================================
    # 5) ESTOQUE DE CONSUMO
    # ======================================================================
    {
        'icone': 'fa-solid fa-warehouse',
        'nome': 'Estoque de Consumo',
        'slug': 'estoque-consumo',
        'descricao': 'Materiais de consumo (papelaria, limpeza, informática, etc.): '
                     'entradas, saídas, lotes, validade, inventário e relatórios.',
        'grupo': 'materiais',
        'ordem': 5,
        'secoes': [
            {
                'titulo': 'Visão geral e conceito de saldo',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O <strong>Estoque de Consumo</strong> controla os materiais de consumo da unidade com base no normativo de materiais de consumo. O ponto central: <strong>o saldo jamais é digitado</strong> — ele é sempre <strong>calculado a partir das movimentações</strong>.</p>
<div class="alert alert-success">
    <i class="fas fa-calculator me-2"></i><strong>Saldo = Entradas (Compra Nova + Devolução) − Saídas (Requisição + Descarte) + Ajustes.</strong>
</div>
<p>Tipos de movimentação: <strong>ENTRADA</strong>, <strong>SAÍDA</strong> e <strong>AJUSTE</strong>.</p>
''',
            },
            {
                'titulo': 'Tabelas de padronização',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>Antes de cadastrar materiais, as tabelas abaixo devem estar preenchidas (menu <strong>Gestão Técnica</strong>):</p>
<ul>
    <li><strong>Categoria</strong> e <strong>Subcategoria</strong> — classificação (ex.: Papelaria &gt; Caneta Azul).</li>
    <li><strong>Cor</strong>, <strong>Unidade de Medida do Item</strong> (ml, kg, pacote 100g) e <strong>Unidade de Fornecimento</strong> (padrão UNIDADE).</li>
    <li><strong>Conta Patrimonial</strong>, <strong>Órgão Requisitante</strong> e <strong>Militar Requisitante</strong> (busca por RE com retorno do QRA).</li>
    <li><strong>Localização Física</strong> (prateleiras do almoxarifado) e <strong>Fornecedores</strong>.</li>
</ul>
''',
            },
            {
                'titulo': 'Cadastrar um material de consumo',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Estoque de Consumo &gt; Materiais &gt; Novo Material</strong>.</li>
    <li>Preencha os campos de identificação: <strong>Código Único</strong> (ex.: MAT-001), <strong>Nome</strong> e <strong>Descrição</strong>.</li>
    <li>Complete a classificação: <strong>Categoria</strong>, <strong>Subcategoria</strong>, <strong>Código SIAFÍSICO</strong> e <strong>Código CAT MAT</strong> (auxiliam novas aquisições).</li>
    <li>Dados de aquisição: <strong>Empenho</strong>, <strong>Preço Médio</strong>, <strong>Data da Cotação</strong>, <strong>Data de Início do Projeto</strong>, <strong>Tempo de Reposição</strong>, <strong>Termo de Referência nº</strong> e <strong>Processo SEI nº</strong>.</li>
    <li>Unidades: <strong>Unidade de Medida do Item</strong> e <strong>Unidade de Fornecimento</strong>.</li>
    <li>Controle: <strong>Estoque Mínimo</strong>, <strong>Estoque Máximo</strong>, opções de <strong>controle de validade</strong> e <strong>número de série</strong>.</li>
    <li>Salve. O sistema gera automaticamente o <strong>QR Code</strong> do material.</li>
</ol>
''',
            },
            {
                'titulo': 'Registrar a entrada de materiais',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Estoque de Consumo &gt; Movimentações &gt; Nova Entrada</strong>.</li>
    <li>Escolha o subtipo: <strong>Compra Nova</strong> ou <strong>Devolução</strong>.</li>
    <li>Informe: <strong>material</strong>, <strong>data</strong> (calendário), <strong>cor</strong>, unidades, <strong>quantidade de embalagens</strong> e <strong>itens por embalagem</strong>.</li>
    <li>Complete com <strong>fornecedor</strong>, <strong>nota fiscal</strong>, <strong>conta patrimonial</strong> e <strong>valor unitário</strong>.</li>
    <li>Se o material controla validade, vincule o <strong>lote</strong> (com data de fabricação e validade).</li>
    <li>Salve. O saldo do material é recalculado e o valor total calculado automaticamente.</li>
</ol>
''',
            },
            {
                'titulo': 'Registrar a saída de materiais',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Estoque de Consumo &gt; Movimentações &gt; Nova Saída</strong>.</li>
    <li>Escolha o subtipo: <strong>Requisição</strong> ou <strong>Descarte</strong>.</li>
    <li>Informe o <strong>material</strong> e a <strong>quantidade</strong>. O sistema bloqueia a saída se a quantidade ultrapassar o <strong>saldo disponível</strong>.</li>
    <li>Preencha o <strong>órgão requisitante</strong> e o <strong>militar requisitante</strong> (RE com retorno automático do QRA) e o <strong>documento de referência</strong>.</li>
    <li>Salve. O saldo é reduzido <strong>em tempo real</strong>.</li>
</ol>
<div class="alert alert-warning">
    <i class="fas fa-exclamation-triangle me-2"></i>Regra obrigatória do normativo: <strong>não é permitido emitir saída maior que o saldo em estoque</strong>.
</div>
''',
            },
            {
                'titulo': 'Lotes, validade e controle PEPS',
                'tipo': 'TEXTO',
                'conteudo': '''
<ul>
    <li><strong>Lotes</strong> — cada entrada com validade gera um lote com quantidade inicial e atual.</li>
    <li><strong>Vencidos e próximos do vencimento</strong> — o sistema destaca lotes vencidos e com validade a vencer em até 30 dias.</li>
    <li><strong>PEPS</strong> (primeiro que entra, primeiro que sai) — o saldo é controlado lote a lote, priorizando o material mais antigo.</li>
    <li><strong>Número de série</strong> — materiais com controle de série (ex.: equipamentos) rastreiam o item individualmente, com patrimônio e responsável.</li>
</ul>
''',
            },
            {
                'titulo': 'Inventário e ajustes de estoque',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Estoque de Consumo &gt; Inventários &gt; Novo Inventário</strong>.</li>
    <li>Configure o tipo (Completo, Parcial, Rotativo, Sorteio) e a data prevista de fim.</li>
    <li>Durante a contagem, registre a <strong>quantidade contada</strong> de cada item; a <strong>diferença</strong> é calculada automaticamente.</li>
    <li>Divergências geram <strong>Ajustes de Estoque</strong> com tipo (Acréscimo/Débito), motivo e <strong>aprovação obrigatória</strong> por usuário autorizado.</li>
</ol>
''',
            },
            {
                'titulo': 'Relatórios do estoque',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>Níveis de informação disponíveis (menu Estoque de Consumo &gt; Relatórios):</p>
<ul>
    <li><strong>Situação do estoque</strong> — saldo calculado, unidade, estoque mínimo, consumo médio e autonomia.</li>
    <li><strong>Estoque baixo</strong> — itens que atingiram o estoque mínimo (reposição).</li>
    <li><strong>Movimentações por período</strong> — entradas e saídas com filtro de datas.</li>
    <li><strong>Inventários</strong> e <strong>baixas de materiais</strong>.</li>
    <li><strong>Alertas</strong> — cotação vencida há mais de 180 dias e tempo de reposição.</li>
</ul>
''',
            },
            {
                'titulo': 'Regras de negócio do estoque',
                'tipo': 'ALERTA',
                'conteudo': '''
<ul>
    <li>Saída maior que o saldo é <strong>bloqueada</strong> (regra normativa).</li>
    <li>O calendário vem <strong>travado na data atual</strong>; registros retrógrados exigem autorização.</li>
    <li>A baixa no estoque ocorre <strong>no momento do salvar</strong>, em tempo real.</li>
    <li>Exclusões de material ficam registradas em <strong>log</strong> (código, saldo na exclusão, usuário e motivo).</li>
    <li><strong>Código único</strong> obrigatório: cada material distinto tem um código próprio.</li>
</ul>
''',
            },
        ],
    },

    # ======================================================================
    # 6) SOLICITAÇÕES DE MATERIAL
    # ======================================================================
    {
        'icone': 'fa-solid fa-cart-shopping',
        'nome': 'Solicitações de Material',
        'slug': 'solicitacoes',
        'descricao': 'Portal de pedidos de material de consumo: catálogo, carrinho, '
                     'acompanhamento pelo solicitante e gestão pela logística.',
        'grupo': '',
        'ordem': 6,
        'secoes': [
            {
                'titulo': 'Visão geral do fluxo',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>As <strong>Solicitações de Material</strong> ligam o policial ao almoxarifado. Um pedido passa pelos status:</p>
<table class="table table-sm table-bordered">
    <thead><tr><th>Status</th><th>Significado</th></tr></thead>
    <tbody>
        <tr><td><span class="badge bg-warning text-dark">Pendente</span></td><td>Aguardando análise da logística.</td></tr>
        <tr><td><span class="badge bg-info text-dark">Em separação</span></td><td>Almoxarifado separando os itens.</td></tr>
        <tr><td><span class="badge bg-primary">Pronto para retirada</span></td><td>Disponível para o solicitante buscar.</td></tr>
        <tr><td><span class="badge bg-success">Entregue</span></td><td>Pedido finalizado.</td></tr>
        <tr><td><span class="badge bg-secondary">Cancelado</span></td><td>Pedido não atendido.</td></tr>
    </tbody>
</table>
''',
            },
            {
                'titulo': 'Solicitar material (portal do policial)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>No Painel Geral, clique em <strong>Solicitar Material</strong> (menu <strong>Serviços &amp; Solicitações</strong>).</li>
    <li>No catálogo, use a busca/filtros e clique em <strong>Adicionar ao carrinho</strong> nos itens desejados.</li>
    <li>Acesse o <strong>Carrinho</strong>, ajuste as quantidades e clique em <strong>Finalizar Solicitação</strong>.</li>
    <li>Preencha os dados requisitantes (órgão/seção) e as observações, se houver.</li>
    <li>Confirme. Sua solicitação entra no status <strong>Pendente</strong>.</li>
</ol>
<div class="alert alert-info">
    <i class="fas fa-info-circle me-2"></i>A visibilidade da quantidade disponível pode ser ligada/desligada pela logística (menu de configuração de pedidos).
</div>
''',
            },
            {
                'titulo': 'Acompanhar suas solicitações',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Solicitações &gt; Minhas Solicitações</strong>.</li>
    <li>A lista mostra o status e a data de cada pedido.</li>
    <li>Clique no pedido para ver os <strong>itens</strong>, as <strong>notas do almoxarifado</strong> e o andamento.</li>
    <li>Quando o status chegar a <strong>Pronto para retirada</strong>, retire presencialmente no almoxarifado.</li>
</ol>
''',
            },
            {
                'titulo': 'Gestão dos pedidos (logística)',
                'tipo': 'PASSO',
                'conteudo': '''
<p>Usuários com o grupo <code>materiais</code> gerenciam os pedidos:</p>
<ol>
    <li>Acesse <strong>Estoque de Consumo &gt; Gestão de Pedidos</strong>.</li>
    <li>Filtre os pedidos pendentes e abra cada um para análise.</li>
    <li>Registre as <strong>notas do almoxarifado</strong> e avance o status: <em>Em separação</em> &rarr; <em>Pronto para retirada</em> &rarr; <em>Entregue</em>.</li>
    <li>Ao marcar como entregue, informe o responsável pela entrega.</li>
    <li>Pedidos inválidos podem ser <strong>cancelados</strong> com justificativa.</li>
</ol>
''',
            },
            {
                'titulo': 'Recibo da solicitação (PDF)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Abra o detalhe da solicitação (gestão ou solicitante).</li>
    <li>Clique em <strong>Gerar Recibo</strong> ou <strong>Visualizar Recibo</strong>.</li>
    <li>O PDF da solicitação é aberto para impressão e arquivamento.</li>
</ol>
''',
            },
        ],
    },

    # ======================================================================
    # 7) FROTA DE VIATURAS
    # ======================================================================
    {
        'icone': 'fa-solid fa-car-side',
        'nome': 'Frota de Viaturas',
        'slug': 'frota',
        'descricao': 'Gestão completa da frota: despachos, abastecimento, manutenção '
                     'com histórico, checklists, baixas e almoxarifado de peças.',
        'grupo': 'frota',
        'ordem': 7,
        'secoes': [
            {
                'titulo': 'Visão geral do módulo',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O módulo <strong>Frota de Viaturas</strong> acompanha cada viatura desde o cadastro até a baixa. O menu cobre: <strong>Visão Geral</strong> (dashboard), <strong>Viaturas</strong>, <strong>Despachos</strong>, <strong>Manutenções</strong> e <strong>Agendamentos</strong>, além de abastecimentos, checklists, baixas, peças e oficinas.</p>
<p>Status da viatura: <strong>Disponível</strong>, <strong>Em Uso</strong>, <strong>Manutenção</strong>, <strong>Vistoria</strong>, <strong>Pregão</strong> e <strong>Baixada</strong>. O status muda automaticamente conforme as operações.</p>
''',
            },
            {
                'titulo': 'Cadastrar uma viatura',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Frota &gt; Viaturas &gt; Nova Viatura</strong>.</li>
    <li>Preencha: <strong>prefixo</strong> (único, ex.: E-10201), <strong>placa</strong>, <strong>chassi</strong>, <strong>renavam</strong> e <strong>número de patrimônio</strong>.</li>
    <li>Selecione o <strong>modelo</strong> (marca + modelo + tipo) — cadastre antes se necessário.</li>
    <li>Informe <strong>hodômetro atual</strong>, <strong>tipo de combustível</strong> e <strong>capacidade do tanque</strong>.</li>
    <li>Defina <strong>status</strong> e <strong>localização</strong> (Cia/Setor, MOTOMEC, OFICINA...).</li>
    <li>Salve. A viatura também pode ser criada em lote pela <strong>importação (XML/XLSX)</strong>.</li>
</ol>
''',
            },
            {
                'titulo': 'Despacho (saída) e retorno',
                'tipo': 'PASSO',
                'conteudo': '''
<p><strong>Registrar saída (Serviço Administrativo):</strong></p>
<ol>
    <li>Acesse <strong>Frota &gt; Despachos &gt; Novo Despacho</strong>.</li>
    <li>Escolha a viatura (só são listadas as <strong>disponíveis</strong>), o <strong>motorista</strong>, o <strong>encarregado</strong> (comandante de equipe) e a <strong>km de saída</strong>.</li>
    <li>Salve. A viatura passa a <strong>Em Uso</strong>.</li>
</ol>
<p><strong>Registrar retorno:</strong></p>
<ol>
    <li>No despacho aberto, clique em <strong>Registrar Retorno</strong>.</li>
    <li>Informe a <strong>km de retorno</strong> e observações.</li>
    <li>Salve. A viatura volta a <strong>Disponível</strong> e o odômetro é atualizado automaticamente.</li>
</ol>
''',
            },
            {
                'titulo': 'Abastecimento',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Frota &gt; Abastecimentos &gt; Novo Abastecimento</strong>.</li>
    <li>Informe a viatura, data/hora, <strong>odômetro</strong>, tipo de <strong>combustível</strong>, <strong>quantidade de litros</strong> e <strong>valor total</strong>.</li>
    <li>Complete com <strong>cupom fiscal</strong> e <strong>posto/fornecedor</strong>.</li>
    <li>Salve. O odômetro da viatura é atualizado.</li>
</ol>
''',
            },
            {
                'titulo': 'Manutenções e oficinas',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Frota &gt; Manutenções &gt; Nova Manutenção</strong> (ou converta um agendamento).</li>
    <li>Escolha o tipo: <strong>Preventiva</strong> ou <strong>Corretiva</strong>. Informe a <strong>oficina</strong> (ou MOTOMEC), a <strong>localização física</strong> da viatura, datas, odômetro e descrição.</li>
    <li>Preencha custos, número da <strong>ordem de serviço</strong>, <strong>nota fiscal</strong> e <strong>termo de garantia</strong> (data/km de garantia).</li>
    <li>Durante o serviço, cadastre <strong>serviços executados</strong> (imutáveis, com custos) e <strong>evidências</strong> (fotos antes/depois, orçamentos, laudos).</li>
    <li>Para concluir, o formulário exige marcar a aprovação dos serviços executados e registrar o parecer (<strong>aprovado por</strong>).</li>
    <li>Ao concluir, a viatura volta a <strong>Disponível</strong> (ou MOTOMEC, se ainda houver necessidade).</li>
</ol>
<div class="alert alert-info">
    <i class="fas fa-history me-2"></i>Toda manutenção mantém uma <strong>linha do tempo de auditoria</strong>: abertura, serviços, alterações, conclusão e cancelamentos com motivo obrigatório.
</div>
''',
            },
            {
                'titulo': 'Agendamentos (preventiva)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Frota &gt; Agendamentos &gt; Novo Agendamento</strong>.</li>
    <li>Escolha viatura, tipo, <strong>data agendada</strong>, oficina e motivo.</li>
    <li>No painel, agendamentos <strong>atrasados</strong> são destacados para priorização.</li>
    <li>Ao chegar a hora, converta o agendamento em manutenção (<strong>Iniciar</strong>) ou cancele-o com justificativa.</li>
</ol>
''',
            },
            {
                'titulo': 'Checklists operacionais',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Frota &gt; Checklists &gt; Novo Checklist</strong>.</li>
    <li>Selecione a <strong>viatura</strong> e o tipo (<strong>Saída</strong>, <strong>Retorno</strong> ou <strong>Rotina</strong>). O odômetro é pré-preenchido.</li>
    <li>Confira os blocos: <em>Limpeza</em>, <em>Mecânica</em>, <em>Elétrica</em>, <em>Equipamentos</em> e <em>Danos/Avarias</em>.</li>
    <li>Registre <strong>avarias de lataria</strong> e observações gerais. Salve e imprima o relatório.</li>
</ol>
''',
            },
            {
                'titulo': 'Baixa de viatura',
                'tipo': 'PASSO',
                'conteudo': '''
<p>A <strong>solicitação de baixa</strong> é aberta por qualquer policial (portal); a <strong>destinação</strong> é decidida pelo gestor de frota.</p>
<ol>
    <li><strong>Solicitar:</strong> Painel &gt; Solicitar Baixa de Viatura. Informe a viatura, categoria do motivo (Quebra, Acidente, Preventiva, Substituição, Inservível...), quilometragem e justificativa.</li>
    <li><strong>Analisar (gestor):</strong> em Frota &gt; Baixas, abra a solicitação e defina a destinação:
        <ul>
            <li><strong>Manutenção</strong> — o sistema <strong>abre automaticamente a Ordem de Serviço</strong> corretiva.</li>
            <li><strong>Oficina</strong>, <strong>Aguardar Vistoria</strong>, <strong>MOTOMEC</strong>, <strong>Pregão</strong> ou <strong>Descarga</strong> (baixa efetiva).</li>
            <li><strong>Negada</strong> — com parecer do gestor.</li>
        </ul>
    </li>
</ol>
''',
            },
            {
                'titulo': 'Almoxarifado de peças',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Cadastre a peça em <strong>Frota &gt; Peças</strong>: nome, código, categoria (Motor, Freios, Elétrica...), <strong>estoque</strong>, <strong>limite mínimo</strong> e valor.</li>
    <li>Para retirar peças para uma viatura: <strong>Frota &gt; Retiradas de Peças &gt; Nova Retirada</strong>. Informe a viatura, o policial e os itens no formulário.</li>
    <li>O sistema <strong>baixa o estoque</strong> de cada peça automaticamente (bloqueia se insuficiente).</li>
    <li>Ao salvar, o <strong>recibo de retirada (PDF)</strong> é gerado; depois, clique em <strong>Anexar Recibo</strong> para guardar a versão assinada.</li>
</ol>
<div class="alert alert-warning">
    <i class="fas fa-exclamation-triangle me-2"></i>O dashboard alerta peças com estoque abaixo do mínimo.
</div>
''',
            },
            {
                'titulo': 'Planos de manutenção preventiva',
                'tipo': 'TEXTO',
                'conteudo': '''
<p><strong>Planos Preventivos</strong> definem regras por modelo (ex.: troca de óleo a cada 10.000 km ou 6 meses). Com base no odômetro e no histórico, o sistema calcula alertas inteligentes de <strong>próximas revisões</strong> por viatura — visíveis na ficha da viatura e no dashboard.</p>
''',
            },
            {
                'titulo': 'Regras do módulo',
                'tipo': 'ALERTA',
                'conteudo': '''
<ul>
    <li>Só viaturas <strong>Disponíveis</strong> podem ser despachadas.</li>
    <li>Status são mantidos automaticamente: saída &rarr; Em Uso; retorno &rarr; Disponível; manutenção aberta &rarr; Manutenção.</li>
    <li>Manutenção e viatura mantêm <strong>histórico completo</strong> (simple history + linha do tempo própria).</li>
    <li>Cancelamento de manutenção/agendamento exige <strong>motivo</strong>.</li>
    <li>A garantia (data/km) é monitorada e utilizada nas decisões de manutenção.</li>
</ul>
''',
            },
        ],
    },

    # ======================================================================
    # 8) PATRIMÔNIO
    # ======================================================================
    {
        'icone': 'fa-solid fa-barcode',
        'nome': 'Patrimônio (Permanente)',
        'slug': 'patrimonio',
        'descricao': 'Bens permanentes da unidade: catálogo, itens com número de '
                     'patrimônio, cautelas, transferências e importação oficial.',
        'grupo': 'patrimonio',
        'ordem': 8,
        'secoes': [
            {
                'titulo': 'Visão geral do módulo',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O módulo <strong>Patrimônio</strong> controla os bens permanentes (móveis, eletrônicos, equipamentos), separados em dois níveis:</p>
<ul>
    <li><strong>Catálogo (Bem Patrimonial)</strong> — o "tipo" de bem (ex.: "Computador Desktop"). Pode existir muitos itens de um mesmo bem.</li>
    <li><strong>Item Patrimonial</strong> — cada unidade física com <strong>número de patrimônio único</strong> (ex.: PM-123456) e número de série.</li>
</ul>
<p>Estados de conservação: Novo, Bom, Regular, Ruim, Inservível. Status: Disponível, Em Uso, Manutenção, Baixado, Extraviado.</p>
''',
            },
            {
                'titulo': 'Cadastrar bens no catálogo',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Patrimônio &gt; Catálogo &gt; Novo Bem</strong>.</li>
    <li>Informe <strong>nome</strong>, <strong>categoria</strong>, <strong>marca</strong>, <strong>modelo de referência</strong> e <strong>valor unitário estimado</strong>.</li>
    <li>Salve. O catálogo mostra quantos itens existem de cada bem.</li>
</ol>
''',
            },
            {
                'titulo': 'Cadastrar um item patrimonial',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Patrimônio &gt; Itens Inventariados &gt; Novo Item</strong>.</li>
    <li>Selecione o <strong>bem</strong> do catálogo (ou use a busca por nome).</li>
    <li>Informe <strong>número de patrimônio</strong> e <strong>número de série</strong> (únicos), <strong>estado de conservação</strong>, <strong>status</strong> e <strong>localização</strong>.</li>
    <li>Campos opcionais: responsável, data de aquisição, nota fiscal e observações.</li>
    <li>Salve. O item entra no inventário patrimonial.</li>
</ol>
''',
            },
            {
                'titulo': 'Movimentar os itens (cautela, devolução, manutenção)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Patrimônio &gt; Registrar Movimentação</strong>.</li>
    <li>Selecione o <strong>item</strong> (é possível pré-selecionar vindo da ficha do item).</li>
    <li>Escolha o <strong>tipo</strong>: <em>Cautela</em>, <em>Devolução</em>, <em>Transferência</em>, <em>Início de Manutenção</em>, <em>Fim de Manutenção</em> ou <em>Baixa</em>.</li>
    <li>Informe o <strong>policial</strong> (na cautela) e/ou a <strong>localização de destino</strong>.</li>
    <li>Salve. O item é atualizado automaticamente (status, responsável e localização).</li>
</ol>
<div class="alert alert-info">
    <i class="fas fa-history me-2"></i>Cada ficha de item preserva o <strong>histórico completo</strong> de movimentações com usuário e data.
</div>
''',
            },
            {
                'titulo': 'Importar patrimônio (SILP/Excel)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Patrimônio &gt; Catálogo &gt; Importar</strong>.</li>
    <li>Anexe o <strong>XML SILP</strong> oficial (estrutura Categoria &gt; Subcategoria &gt; Item) ou uma planilha Excel genérica.</li>
    <li>O sistema cria <strong>categorias, bens e itens</strong> automaticamente, convertendo valores corretamente (centavos).</li>
    <li>Revise o resumo do último import na tela de catálogo.</li>
</ol>
''',
            },
            {
                'titulo': 'Regras do módulo',
                'tipo': 'ALERTA',
                'conteudo': '''
<ul>
    <li><strong>Número de patrimônio</strong> é único — duplicidades são bloqueadas.</li>
    <li>Responsável (cautela) é vinculado ao cadastro de <strong>policial</strong>.</li>
    <li>Baixa de item afeta a contagem patrimonial e o valor total estimado do dashboard.</li>
    <li>Itens <strong>Extraviados</strong> precisam de tratativa e registro no histórico.</li>
</ul>
''',
            },
        ],
    },

    # ======================================================================
    # 9) INVENTÁRIO SEMESTRAL
    # ======================================================================
    {
        'icone': 'fa-solid fa-clipboard-check',
        'nome': 'Inventário Semestral',
        'slug': 'inventario',
        'descricao': 'Conferência patrimonial semestral: importação da planilha '
                     'oficial, comissão, conferência física, divergências e termo PDF.',
        'grupo': '',
        'ordem': 9,
        'secoes': [
            {
                'titulo': 'Visão geral do módulo',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O <strong>Inventário Semestral</strong> conduz a conferência física do patrimônio da unidade dentro de um <strong>ciclo</strong> (ano/semestre) com metadados oficiais: <em>termo nº</em>, <em>detentor executivo</em>, <em>códigos de OPM</em> e <em>contas contábeis</em>.</p>
<p>O ciclo percorre uma máquina de estados controlada, com <strong>histórico de transições</strong>, comissão de inventário por papéis e emissão de <strong>Termo de Inventário em PDF</strong> (base I-23, art. 96 da Lei 4.320/64).</p>
''',
            },
            {
                'titulo': 'Importar a planilha oficial',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Inventário Semestral &gt; Importar</strong> (link <code>/inventario/importar/</code> no menu/atalho).</li>
    <li>Anexe a <strong>planilha oficial</strong> (.xlsx/.xls) do batalhão e informe título, termo nº, ano e semestre.</li>
    <li>A importação identifica as <strong>contas contábeis</strong>, seções/subunidades e itens com patrimônio, criando o ciclo em <strong>Em Andamento</strong> com milhares de itens em segundos.</li>
    <li>Você passa a ser <strong>presidente</strong> da comissão do ciclo.</li>
</ol>
''',
            },
            {
                'titulo': 'Ciclo de vida (máquina de estados)',
                'tipo': 'TEXTO',
                'conteudo': '''
<table class="table table-sm table-bordered">
    <thead><tr><th>Fase</th><th>Descrição</th></tr></thead>
    <tbody>
        <tr><td>Rascunho</td><td>Preparação inicial.</td></tr>
        <tr><td>Em Preparação</td><td>Organização da comissão e dados.</td></tr>
        <tr><td>Em Andamento</td><td>Conferência física dos itens.</td></tr>
        <tr><td>Em Análise</td><td>Tratamento das divergências.</td></tr>
        <tr><td>Aguardando Aprovação</td><td>Revisão final pelos gestores.</td></tr>
        <tr><td>Concluído</td><td>Conferência encerrada.</td></tr>
        <tr><td>Homologado</td><td>Aprovação formal (bloqueia edição).</td></tr>
        <tr><td>Arquivado</td><td>Histórico definitivo.</td></tr>
    </tbody>
</table>
<p>As <strong>transições</strong> são permitidas apenas na ordem correta e exigem <strong>justificativa</strong>, registrada em histórico auditável.</p>
''',
            },
            {
                'titulo': 'Comissão e papéis',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>Os integrantes da comissão possuem papéis por ciclo:</p>
<ul>
    <li><strong>Presidente</strong> — gestão e transições.</li>
    <li><strong>Membro</strong> e <strong>Conferente</strong> — realizam as conferências.</li>
    <li><strong>Supervisor</strong> — gestão e reabertura de conferências.</li>
    <li><strong>Homologador</strong> — homologação do ciclo.</li>
</ul>
<div class="alert alert-warning">
    <i class="fas fa-user-shield me-2"></i>Conferir itens exige papel de gestão (Presidente, Membro, Conferente ou Supervisor). A conferência é bloqueada fora da fase <strong>Em Andamento</strong>.
</div>
''',
            },
            {
                'titulo': 'Realizar a conferência',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse o detalhe do <strong>ciclo</strong>. Use filtros (busca por patrimônio/série/material, conta, seção, conferido).</li>
    <li>Confira cada item individualmente ou marque o <strong>lote completo</strong> como conferido.</li>
    <li>Registre o resultado: <em>Confirmado</em>, <em>Com Ressalva</em>, <em>Não Localizado</em>, <em>Outra Seção</em>, <em>Excedente</em>, <em>Avariado</em> ou <em>Em Baixa</em>.</li>
    <li>Se o resultado for divergente, o sistema <strong>cria automaticamente a divergência</strong> correspondente.</li>
    <li>Acompanhe o <strong>painel de progresso</strong> (percentual conferido) no dashboard do inventário.</li>
</ol>
''',
            },
            {
                'titulo': 'Tratar as divergências',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>No ciclo, abra a lista de <strong>divergências</strong> (tipos: Não Localizado, Excedente, Outra Seção, Série Divergente, Avariado, Em Baixa, Conta Divergente, Duplicidade).</li>
    <li>Cada divergência segue o status: <em>Aberta</em> &rarr; <em>Em Apuração</em> &rarr; <em>Aguardando Documento</em> &rarr; <em>Regularizada</em> (ou <em>Confirmada para Baixa</em> / <em>Improcedente</em>).</li>
    <li>Registre providências, responsável e prazo; a conclusão é feita por gestores com resolução.</li>
</ol>
''',
            },
            {
                'titulo': 'Termo e exportação',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>No ciclo, clique em <strong>Gerar Termo (PDF)</strong> — documento oficial com cabeçalho PMESP, fundamentos legais, resumo por contas, bens em exclusão e quadro de assinaturas.</li>
    <li>Use <strong>Exportar Excel</strong> para a planilha analítica do ciclo (contas, seção, patrimônio, série, situação, valor, conferido).</li>
</ol>
''',
            },
        ],
    },

    # ======================================================================
    # 10) TELEMÁTICA E T.I.
    # ======================================================================
    {
        'icone': 'fa-solid fa-satellite-dish',
        'nome': 'Telemática e T.I.',
        'slug': 'telematica',
        'descricao': 'Inventário de equipamentos de TI, rede (IP/MAC), rádio, '
                     'linhas móveis, serviços de rede e atendimento de suporte técnico.',
        'grupo': 'telematica',
        'ordem': 10,
        'secoes': [
            {
                'titulo': 'Visão geral do módulo',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O módulo <strong>Telemática e T.I.</strong> concentra o parque de informática, comunicação e rede:</p>
<ul>
    <li><strong>Inventário de TI</strong> — computadores e equipamentos com rede, responsáveis e garantia.</li>
    <li><strong>Suporte Técnico</strong> — chamados unificados (abertos pelo usuário ou internamente).</li>
    <li><strong>Redes &amp; Links</strong> — serviços de internet/VPN/sistema com contratos e vencimentos.</li>
    <li><strong>Categorias</strong> — tipificação dos equipamentos.</li>
</ul>
''',
            },
            {
                'titulo': 'Cadastrar um equipamento',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Telemática &gt; Inventário de TI &gt; Novo Equipamento</strong>.</li>
    <li>Informe a <strong>categoria</strong> (Notebook, Desktop, Rádio...), <strong>marca</strong>, <strong>modelo</strong>, <strong>número de série</strong> e <strong>patrimônio</strong>.</li>
    <li>Hardware: processador, memória, armazenamento e sistema operacional.</li>
    <li>Rede: <strong>hostname</strong>, <strong>IP</strong>, <strong>MAC</strong>, VLAN e porta do switch.</li>
    <li>Localização: setor, unidade, policial/responsável e usuário.</li>
    <li>Status inicial <strong>Operacional</strong>, data de aquisição e vencimento da garantia.</li>
    <li>Salve. A ficha técnica permite vínculo com chamados e atalhos de ação.</li>
</ol>
''',
            },
            {
                'titulo': 'Equipamentos especiais',
                'tipo': 'TEXTO',
                'conteudo': '''
<ul>
    <li><strong>Configuração de Rádio</strong> — para a categoria Rádio, campos específicos: <em>ISSI</em>, <em>TEI</em>, grupo principal, criptografia e firmware.</li>
    <li><strong>Linhas móveis (chips)</strong> — número, operadora, ICCID, IMEI(s), plano de dados e vínculo com o equipamento/policial.</li>
    <li><strong>Serviços de rede</strong> — tipo (Internet/VPN/Sistema/Storage/Rede), fornecedor, contrato, vencimento, IP público e velocidade.</li>
</ul>
''',
            },
            {
                'titulo': 'Abrir um chamado de suporte (portal)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>No Painel Geral, clique em <strong>Solicitar Suporte de TI</strong>.</li>
    <li>Selecione o <strong>tipo de serviço</strong> (Hardware, Software, Rede, Rádio, Celular, Sistema BAEP, Preventiva, Corretiva), o <strong>equipamento</strong> (busca inteligente) e a <strong>prioridade</strong>.</li>
    <li>Descreva o <strong>problema</strong> com detalhes.</li>
    <li>Envie. O chamado entra <strong>Pendente</strong>.</li>
</ol>
''',
            },
            {
                'titulo': 'Acompanhar e atender chamados',
                'tipo': 'PASSO',
                'conteudo': '''
<p><strong>Solicitante:</strong> em <em>Minhas Solicitações</em> (Suporte de TI), visualize o histórico dos seus chamados e o status.</p>
<p><strong>Técnico (grupo telematica):</strong></p>
<ol>
    <li>Acesse <strong>Telemática &gt; Suporte Técnico</strong> para ver todos os chamados (busca e filtro por status).</li>
    <li>Abra o chamado e clique em <strong>Atender</strong>: defina status (<em>Em Atendimento</em>, <em>Aguardando Peça</em>, <em>Concluída</em>, <em>Cancelada</em>), o <strong>técnico responsável</strong>, a <strong>solução técnica</strong> e o <strong>custo</strong>.</li>
    <li>Ao iniciar o atendimento, o horário é registrado automaticamente.</li>
</ol>
<div class="alert alert-info">
    <i class="fas fa-sync-alt me-2"></i>O <strong>status do equipamento</strong> é sincronizado automaticamente: em atendimento &rarr; Manutenção; concluído e sem outros chamados &rarr; Operacional.
</div>
''',
            },
            {
                'titulo': 'Regras e boas práticas',
                'tipo': 'ALERTA',
                'conteudo': '''
<ul>
    <li>Garantias com vencimento em até <strong>30 dias</strong> são alertadas no dashboard de Telemática.</li>
    <li>Equipamentos só podem ser excluídos com confirmação; exclusões comprometem o histórico.</li>
    <li>Mantenha IP/hostname corretos para não conflitar na rede.</li>
    <li>Categoria com equipamentos não pode ser excluída.</li>
</ul>
''',
            },
        ],
    },

    # ======================================================================
    # 11) EFETIVO (POLICIAIS)
    # ======================================================================
    {
        'icone': 'fa-solid fa-user-shield',
        'nome': 'Efetivo (Policiais)',
        'slug': 'efetivo',
        'descricao': 'Cadastro central do efetivo (RE e QRA), utilizado por todos '
                     'os módulos: motoristas, requisitantes, cautelas e suporte.',
        'grupo': 'reserva_armas',
        'ordem': 11,
        'secoes': [
            {
                'titulo': 'Visão geral do módulo',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O cadastro de <strong>Policiais</strong> é a <strong>base de dados central</strong> de pessoas do sistema. Todos os módulos consultam este cadastro: motorista de viatura, militar requisitante de material, policial de cautela, responsável de patrimônio e técnico de suporte.</p>
<p>Por isso a manutenção deste cadastro é crítica — mantenha <strong>RE</strong>, <strong>posto</strong> e <strong>situação</strong> sempre atualizados.</p>
''',
            },
            {
                'titulo': 'Cadastrar um policial',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Reserva de Armas &gt; Efetivo &gt; Novo Policial</strong>.</li>
    <li>Informe o <strong>RE</strong> (registro único), <strong>nome completo</strong> e <strong>posto</strong> (SD, CB, SGTs, SUBTEN, Oficiais).</li>
    <li>Defina a <strong>situação</strong>: Ativo, Inativo, Afastado ou Transferido.</li>
    <li>Campos opcionais: observações e foto.</li>
    <li>Salve. O policial já fica disponível para os demais módulos.</li>
</ol>
''',
            },
            {
                'titulo': 'Importar o efetivo em lote (Excel)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Efetivo &gt; Importar</strong>.</li>
    <li>Anexe o arquivo .xls (ou use o arquivo padrão <code>Efetivo - Março.xls</code>).</li>
    <li>O sistema <strong>mapeia os postos</strong> automaticamente (ex.: "1º TEN PM" &rarr; 1TEN_PM) e limpa a formatação do RE.</li>
    <li>Confirme. Registros são <strong>criados ou atualizados</strong> por RE em transação única, com contadores de resultado.</li>
</ol>
''',
            },
            {
                'titulo': 'Consultar o efetivo',
                'tipo': 'TEXTO',
                'conteudo': '''
<ul>
    <li>Listagem com <strong>busca por nome ou RE</strong>, filtros por posto e situação, paginação.</li>
    <li>Na ficha do policial, visualiza-se as <strong>últimas cautelas</strong> (materiais em uso).</li>
    <li>A exclusão é <strong>bloqueada</strong> se o policial possui movimentações — nesse caso, marque-o como <strong>Inativo</strong>.</li>
</ul>
''',
            },
        ],
    },

    # ======================================================================
    # 12) CENTRAL DE RELATÓRIOS
    # ======================================================================
    {
        'icone': 'fa-solid fa-file-pdf',
        'nome': 'Central de Relatórios',
        'slug': 'relatorios',
        'descricao': 'Emissão de relatórios oficiais em PDF e Excel para todos os '
                     'módulos, com filtros, histórico e relatórios individuais.',
        'grupo': 'relatorios',
        'ordem': 12,
        'secoes': [
            {
                'titulo': 'Visão geral da Central de Relatórios',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>A <strong>Central de Relatórios</strong> (menu <strong>Inteligência &amp; Relatórios</strong>) centraliza a emissão de documentos. O motor de PDF inclui cabeçalho oficial e é compatível com dispositivos móveis (abre dentro do ambiente seguro do sistema, sem pop-ups).</p>
<p>Todo relatório gerado fica registrado como <strong>documento</strong> (data, tipo e módulo) e pode ser baixado novamente pelo histórico.</p>
''',
            },
            {
                'titulo': 'Gerar um relatório',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Central de Relatórios</strong>.</li>
    <li>Escolha o tipo de relatório (por módulo):
        <ul>
            <li><strong>Situação Atual</strong> — situação geral do arsenal em tempo real.</li>
            <li><strong>Materiais</strong> — inventário de armamentos.</li>
            <li><strong>Movimentações</strong> — retiradas/devoluções (materiais e estoque).</li>
            <li><strong>Estoque</strong> — movimentações e situação do material de consumo.</li>
            <li><strong>Patrimônio</strong>, <strong>Frota</strong>, <strong>Manutenções</strong> e <strong>Telemática</strong>.</li>
        </ul>
    </li>
    <li>Aplique os <strong>filtros</strong> (período, status, categoria...).</li>
    <li>Clique em <strong>Gerar</strong>. O sistema cria o documento e disponibiliza o <strong>download</strong>.</li>
</ol>
''',
            },
            {
                'titulo': 'Relatórios individuais',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>Além dos relatórios gerais, existem <strong>fichas individuais</strong> geradas a partir das próprias telas:</p>
<ul>
    <li><strong>Ficha por viatura</strong> — na ficha da viatura.</li>
    <li><strong>Histórico por item de patrimônio</strong> — na ficha do item.</li>
    <li><strong>Registro de manutenção</strong> — na manutenção específica.</li>
</ul>
<p>No <strong>Material Bélico</strong>, há relatórios <em>detalhado</em> (todo o arsenal) em Excel e PDF, e <em>por categoria</em> (fuzis, espingardas, etc.) nos dois formatos.</p>
''',
            },
            {
                'titulo': 'Dicas para uso prático',
                'tipo': 'DICA',
                'conteudo': '''
<ul>
    <li>Gere o relatório no <strong>período correto</strong> para conferir os dados antes da assinatura.</li>
    <li>No mobile, aguarde o download concluir (o arquivo abre no leitor de PDF do dispositivo).</li>
    <li>Use a <strong>Central de Relatórios</strong> para conferência diária e os botões de relatório das listagens para documentos pontuais.</li>
</ul>
''',
            },
        ],
    },

    # ======================================================================
    # 13) USUÁRIOS E PERMISSÕES
    # ======================================================================
    {
        'icone': 'fa-solid fa-user-cog',
        'nome': 'Usuários e Permissões',
        'slug': 'usuarios',
        'descricao': 'Gestão de contas de usuário, grupos de permissão, alteração '
                     'de senha, redefinição e perfil.',
        'grupo': 'administracao',
        'ordem': 13,
        'secoes': [
            {
                'titulo': 'Visão geral',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>A administração de <strong>Usuários</strong> define quem acessa o sistema e o que cada usuário consegue ver. O menu de Usuários é acessível para quem possui o grupo <code>administracao</code> (ou superuser).</p>
<p>Cada conta é vinculada a <strong>grupos</strong> que liberam os módulos (ver módulo "Visão Geral — Controle de acesso por grupos").</p>
''',
            },
            {
                'titulo': 'Criar e editar usuários',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Apoio &amp; Sistema &gt; Usuários</strong> e clique em <strong>Registrar Usuário</strong> (ou edite um existente).</li>
    <li>Informe nome de usuário, nome completo, e-mail e <strong>senha</strong>.</li>
    <li>Vincule os <strong>grupos</strong> conforme a função do usuário (ex.: <code>frota</code> para quem trabalha na frota).</li>
    <li>Salve. O usuário já pode acessar os módulos liberados.</li>
</ol>
''',
            },
            {
                'titulo': 'Perfil, senha e recuperação',
                'tipo': 'PASSO',
                'conteudo': '''
<ul>
    <li><strong>Perfil</strong> — o próprio usuário edita seus dados em "Meu Perfil" (menu superior).</li>
    <li><strong>Alterar Senha</strong> — cada usuário altera sua própria senha (menu superior).</li>
    <li><strong>Redefinição de senha</strong> — na tela de login, "Esqueci minha senha": o sistema envia o link de redefinição por e-mail.</li>
    <li>Administradores podem editar senhas e grupos de qualquer usuário.</li>
</ul>
''',
            },
            {
                'titulo': 'Segurança',
                'tipo': 'ALERTA',
                'conteudo': '''
<div class="alert alert-danger">
    <ul class="mb-0">
        <li>Não compartilhe seu usuário/senha — o sistema registra quem executou cada operação.</li>
        <li>A sessão expira em <strong>8 horas</strong> de inatividade por segurança.</li>
        <li>Use senhas fortes (mistura de letras, números e símbolos).</li>
        <li>Peça ao administrador para ajustar seus <strong>grupos</strong> quando mudar de função.</li>
    </ul>
</div>
''',
            },
        ],
    },

    # ======================================================================
    # 14) ADMINISTRAÇÃO & CONSULTAS
    # ======================================================================
    {
        'icone': 'fa-solid fa-search-location',
        'nome': 'Administração e Consultas',
        'slug': 'administracao',
        'descricao': 'Painel administrativo com consultas dinâmicas sobre os dados '
                     'do sistema, exportação em Excel e impressão.',
        'grupo': 'administracao',
        'ordem': 14,
        'secoes': [
            {
                'titulo': 'Visão geral',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O módulo <strong>Administração</strong> (grupo <code>administracao</code>) disponibiliza o <strong>Painel Administrativo</strong> e as <strong>Consultas</strong> sobre os dados operacionais — indicado para chefia, oficiais e auditoria.</p>
''',
            },
            {
                'titulo': 'Executar uma consulta dinâmica',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Acesse <strong>Inteligência &amp; Relatórios &gt; Consultas Administrativas</strong>.</li>
    <li>Selecione a <strong>consulta/modelo</strong> desejada e aplique os <strong>filtros</strong> (parâmetros, datas, status).</li>
    <li>Visualize o resultado na tela.</li>
    <li>Exporte para <strong>Excel</strong> ou <strong>imprima</strong> o relatório quando precisar deste registro.</li>
</ol>
''',
            },
        ],
    },

    # ======================================================================
    # 15) LICENCIAMENTO
    # ======================================================================
    {
        'icone': 'fa-solid fa-key',
        'nome': 'Licenciamento do Sistema',
        'slug': 'licenciamento',
        'descricao': 'Como funciona a licença de uso (token JWT), ativação, '
                     'período de tolerância e o painel do desenvolvedor.',
        'grupo': '',
        'ordem': 15,
        'secoes': [
            {
                'titulo': 'Como o licenciamento funciona',
                'tipo': 'TEXTO',
                'conteudo': '''
<p>O sistema é protegido por <strong>licença de uso</strong> baseada em um token assinado digitalmente (JWT RS256). A licença define o <strong>cliente</strong> e a <strong>data de validade</strong>.</p>
<p>Status possíveis da licença:</p>
<ul>
    <li><strong>Válida</strong> — sistema opera normalmente.</li>
    <li><strong>Período de tolerância (grace period)</strong> — licença vencida há até 3 dias; o sistema continua funcionando e exibe aviso de renovação no topo.</li>
    <li><strong>Expirada</strong> — após o período de tolerância, o sistema é <strong>bloqueado</strong>.</li>
</ul>
''',
            },
            {
                'titulo': 'Ativar ou renovar a licença',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>Com a tela de <strong>bloqueio</strong> aberta (ou pelo aviso de renovação), acesse o menu <strong>Ativar Licença</strong>.</li>
    <li>Cole o <strong>token</strong> fornecido pelo desenvolvedor.</li>
    <li>Confirme. O sistema valida o token e libera o acesso até a nova validade.</li>
</ol>
''',
            },
            {
                'titulo': 'Painel Master (desenvolvedor/administrador)',
                'tipo': 'PASSO',
                'conteudo': '''
<ol>
    <li>O usuário <strong>master</strong> acessa o <strong>Painel Master</strong> (menu "Área do Criador").</li>
    <li>Lá é possível <strong>gerar novos tokens</strong> de licença para o cliente, definindo nome e quantidade de dias de validade.</li>
    <li>Também é possível acompanhar o status atual da licença instalada.</li>
</ol>
<div class="alert alert-warning">
    <i class="fas fa-lock me-2"></i>O Painel Master é restrito ao superusuário. A chave privada de assinatura é de responsabilidade exclusiva do desenvolvedor.
</div>
''',
            },
            {
                'titulo': 'O que fazer se o sistema bloquear',
                'tipo': 'ALERTA',
                'conteudo': '''
<ol class="mb-2">
    <li>Acione o setor de T.I./administrador do sistema.</li>
    <li>O administrador solicita novo token ao desenvolvedor com justificativa da renovação.</li>
    <li>Cole o novo token na tela <strong>Ativar Licença</strong> e confirme.</li>
</ol>
<p>Enquanto a licença não for renovada, somente a rota de ativação (e o usuário master) continuam acessíveis para evitar um ciclo de bloqueio.</p>
''',
            },
        ],
    },
]
