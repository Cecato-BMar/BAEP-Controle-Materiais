Página 9 de 9



2º BATALHÃO DE AÇÕES ESPECIAIS DE POLÍCIA

SETOR DE LOGÍSTICA

PROCEDIMENTO ADMINISTRATIVO PADRÃO (PAP)



CONTROLE DE ESTOQUE



OBJETIVO: Garantir a disponibilidade de materiais de consumo e evitar desperdícios.



1. PARTE GERAL

1.1. RECEBIMENTO E CONFERÊNCIA

Ação: Receber o material do fornecedor confrontando com a Nota Fiscal (NF).

Critérios de Verificação:

Quantidade: O número de fardos/caixas confere com o pedido?

Integridade: As embalagens de álcool estão lacradas? O papel está seco e sem amassados?

Validade: Itens como álcool e produtos de limpeza estão dentro do prazo?

Decisão:

Se houver divergência: Recusar a entrega ou ressalvar na NF e notificar compras.

Se estiver correto: Assinar canhoto e seguir para registro.



1.2. REGISTRO DE ENTRADA

Ação: Lançar a entrada no sistema ou planilha de controle.

Dados Necessários: Data, Fornecedor, Quantidade, Valor Unitário e Lote (se aplicável).

Atualização de Saldo: O estoque virtual deve refletir exatamente o estoque físico após esta etapa.



1.3. ARMAZENAMENTO (MÉTODO PEPS)

Ação: Organizar os materiais nas prateleiras designadas.

Regra de Ouro: Primeiro que Entra, Primeiro que Sai. Coloque os itens novos atrás dos antigos para evitar que materiais percam a validade ou fiquem obsoletos no fundo da prateleira.

Setorização:

Papelaria: Papel A4, canetas, grampos.

Higiene/Limpeza: Papel higiênico, álcool, sabonete.



1.4. REQUISIÇÃO E SAÍDA

Ação: O material só deve ser entregue mediante solicitação formal (e-mail, formulário ou sistema).

Controle de Consumo: Registrar para qual setor o material foi enviado (Ex: "05 Resmas para o Financeiro").

Baixa Imediata: Retirou da prateleira? Dê a baixa no controle no mesmo instante.



1.5. MONITORAMENTO E PONTO DE PEDIDO

Ação: Verificação diária ou semanal do saldo residual.

Cálculo de Segurança: Quando o estoque atingir o Estoque Mínimo (ex: apenas 2 galões de álcool restantes), o responsável deve disparar o pedido de compra.

Inventário Rotativo: Uma vez por mês, conte fisicamente os itens (papel, canetas, etc.) para garantir que o saldo do sistema bate com a realidade.



Exemplo de Fluxo Lógico (Para desenhar no PDF):

[ENTRADA] → [CONFERÊNCIA] → [REGISTRO] → [ARMAZENAGEM] → [USO/SAÍDA] → [ESTOQUE MÍNIMO?] → [COMPRA]



1.6. FLUXOGRAMA





ANEXO I

PROJETO PARA CONTROLE DE ESTOQUE

DADOS NECESSÁRIOS

FLUXOGRAMA



1. TABELAS PARA PADRONIZAÇÃO DE INFORMAÇÕES



Entrada/Saída: (não permitir cadastro)

Entrada:

Compra Nova (+ soma ao estoque)

Devolução (+ soma ao estoque)

Saída

Requisição (- subtrai do estoque)

Descarte (-)



 Cadastro de Materiais de Consumo: (permitir cadastro do usuário)

Subcategoria (ex. papel sulfite A4, HD Externo 2T, Café)

Categoria (extrair informações da tabela categoria)

Código SIAFÍSICO (conforme Termo de Referência para otimizar novas aquisições)

Código CAT MAT (conforme Termo de Referência para otimizar novas aquisições)

Descrição (conforme Termo de Referência para otimizar novas aquisições)

Preço Médio

Data da Cotação

Data de Início do Projeto de Aquisição

Tempo de Reposição

Termo de Referência nº

Processo SEI nº

OBSERVAÇÃO: inserir campo de atualização da subcategoria.



 Cor (permitir cadastro)

Amarelo

Azul

Vermelho

Preto

Branco

Cinza

Verde

Etc.



 Unidade de Medida do Item (permitir cadastro)

Pacote 100 g

Pacote 200 g

Pacote 1kg

Galão 1 l

Galão 500 ml

Etc.



 Unidade de Fornecimento. criar tabela com item único para evitar confusão com a unidade de medida do item (permitir cadastro somente para administradores).

Unidade



 Conta Patrimonial (permitir cadastro)

Descrição da Conta Patrimonial

Código da Conta Patrimonial



 Órgão Requisitante (permitir cadastro)

CMD

SUBCMD

EM/P1

EM/P2

EM/P3

EM/P4

EM/P5

SPJMD

1ª CIA

2ª CIA

3ª CIA

Etc.



 Militar Requisitante

RE

QRA



 Localização Física (permitir cadastro de locais)

Prateleira A

Prateleira B

Etc.



2. TABELA DE ENTRADA DE MATERIAIS DE CONSUMO



CAMPOS:



2.1. Subcategoria (extrair informações da tabela subcategoria, consulta por lista suspensa)



2.2. Tipo de entrada (extrair informações da tabela entrada em lista suspensa)



2.3.  Data entrada (inserir por calendário)



2.4. Cor (extrair informações da tabela cor em lista suspensa)



2.5. Unidade de Medida do Item (extrair informações da tabela unidade de medida em lista suspensa)

Ex. caixa com 03 itens de “30 ml”, cadastrar a unidade de medida correspondente a cada item, ou seja, “ml”.



2.6. Unidade de Fornecimento por Unidade (extrair informações da tabela Unidade de Fornecimento em lista suspensa)

Será sempre Unidade, a fim de que a baixa no estoque possa ocorrer por unidade. Ex. o requisitante solicita item que foi entregue em caixas com 03 itens. Deve ser cadastrada a baixa de 



2.7. Quantidade de Unidades

Ex. caixa com 03 itens de 30 ml, inserir a quantidade de “03”, que corresponde, a fim de que a baixa no estoque possa ocorrer por unidade de 30ml e não somente por caixa com 03.



Conta Patrimonial (extrair informações da tabela contra patrimonial e preencher demais colunas automaticamente)



3. TABELA DE SAÍDA DE MATERIAIS DE CONSUMO



CAMPOS:



3.1. Material (subcategoria) – pesquisa na tabela subcategoria por nome.



3.1.1. Unidade de Fornecimento: retorno automático (sempre UNIDADE).



3.2. Tipo de saída (extrair informações da tabela saída):



 Órgão Requisitante (extrair informações da tabela Órgão Requisitante)



 Militar Requisitante

Incluir pesquisa por RE com retorno automático do QRA. (extrair informações da tabela Unidade de Medida)



 Data da saída (por calendário) 



 Quantidade



 Valor Total da Saída

FORMULÁRIO DE CONTROLE DE ESTOQUE (SOMENTE LEITURA)

CAMPOS:

4.1. Material (subcategoria) - (Ao selecionar o material, o sistema deve apresentar todos os dados vinculados da tabela “entrada de materiais de consumo”).

4.2. Categoria (retorna automaticamente) - (extrair informações da tabela “entrada de materiais de consumo)

4.3. Quantidade em Estoque:

Cálculo: Saldo = SOMA {Entradas: Compras + Devoluções}) - SOMA{Saídas: Requisições + Descartes})

4.4. Unidade de Medida do Item (extrair informações da tabela “entrada de materiais de consumo).

4.5. Consumo Médio.

Inserir campos de calendário para cálculo de consumo médio em determinados períodos.

Campos de Calendário (Filtro): * Data Início e Data Fim.

Lógica do Cálculo:



4.6. Autonomia de Estoque:

Calcular autonomia automaticamente (retorna a duração do estoque).

Cálculo: quantidade em estoque / consumo médio.



4.7. Estoque Mínimo





4.8. Tempo de Reposição

Data da Entrada - Data de Início do Projeto de Aquisição



4.8. Data da Última Cotação:

Incluir alerta após 180 dias da data.



4.9. Proposta de Layout de Visualização



OBSERVAÇÕES:

Códigos Únicos: Atribua um código único para cada material diferente. Por exemplo, "caneta azul" e "caneta vermelha" devem ter códigos distintos.

Treinamento: Treine a equipe responsável pelo recebimento e registro para que preencham os campos corretamente.

Uso de Tecnologia: Considere o uso de leitores de código de barras para agilizar o registro de itens padronizados.

Regra de Negócio: O sistema não deve permitir que a Quantidade de Saída seja maior que o Saldo em Estoque.

Data: O calendário deve vir travado na data atual para evitar retroativos sem autorização superior.

Baixa no Estoque: No momento do "Salvar", o cálculo de subtração ocorre em tempo real no banco de dados.



RELATÓRIOS



5.1. RELATÓRIO DE ESTOQUE DE MATERIAIS

COLUNAS:

5.1.1. MATERIAL (SUBCATEGORIA)

5.1.2. SALDO EM ESTOQUE

5.1.3. UNIDADE DE MEDIDA

5.1.4. ESTOQUE MÍNIMO

5.1.5. CONSUMO MÉDIO

5.1.6. DATA DA EMISSÃO

5.1.2. RESPONSÁVEL PELO INVENTÁRIO



ASSINATURAS:

CHEFE DO SETOR DE LOGÍSTICA

ENCARREGADO DO SETOR DE INTENDÊNCIA

2º BATALHÃO DE AÇÕES ESPECIAIS DE POLÍCIA

SETOR DE LOGÍSTICA

123666-A