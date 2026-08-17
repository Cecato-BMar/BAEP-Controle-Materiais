# Homologação isolada do fluxo de inventário

Esta branch não deve ser conectada ao recurso de produção no Coolify.

## Ambiente separado

Crie uma nova aplicação no Coolify vinculada à branch `feature/inventario-fluxo-completo` e configure:

- URL exclusiva de homologação;
- serviço PostgreSQL exclusivo e uma `DATABASE_URL` diferente da produção;
- volume exclusivo para `/app/media`;
- `SECRET_KEY` exclusiva;
- `DEBUG=False`;
- backend de e-mail de console ou uma caixa de teste.

Não copie volumes, banco de dados ou variáveis secretas da produção. Para testar dados reais, use somente uma cópia anonimizada e restaurada no banco de homologação.

## Sequência de validação

1. Fazer o deploy da branch no recurso de homologação.
2. Confirmar no log que `inventario.0002_fluxo_auditoria_e_divergencias` foi aplicada.
3. Executar `python manage.py test inventario` no container.
4. Validar login e as rotas dos módulos existentes.
5. Criar um ciclo de teste e designar membros da comissão pelo Django Admin.
6. Registrar conferência conforme, não localizada e com número de série divergente.
7. Confirmar criação das divergências, do histórico e o bloqueio após homologação.
8. Emitir PDF/Excel e validar os totais.

## Critérios para promoção

- testes automatizados verdes;
- checklist funcional aprovado pelo responsável do inventário;
- backup de produção confirmado;
- pull request revisado e aprovado;
- autorização explícita antes de mergear na `main`.

## Retorno seguro

As migrations desta fase são apenas aditivas: criam tabelas e ampliam o tamanho de uma coluna. Se uma versão for reprovada, reimplante o commit anterior; não restaure o banco de produção sem evidência de corrupção de dados.
