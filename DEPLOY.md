# Guia de Implantação: Ubuntu Server + Coolify + PostgreSQL

Este guia descreve como implantar o **SIS LOGÍSTICA 2º BAEP** em produção utilizando um servidor **Ubuntu Server** rodando o painel **Coolify** e banco de dados **PostgreSQL**.

---

## 1. Preparação do Servidor (Ubuntu Server)

Caso ainda não possua o Coolify instalado, execute o comando de instalação oficial no seu terminal do Ubuntu Server (como usuário `root` ou via `sudo`):

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

*O Coolify instalará automaticamente todas as dependências necessárias, incluindo o Docker e o proxy reverso Traefik.*

---

## 2. Configurando o Banco de Dados PostgreSQL no Coolify

1. Acesse o painel do Coolify no seu navegador (geralmente porta `8000`, ex: `http://ip-do-servidor:8000`).
2. Vá em **Sources** ➔ **Projects** e selecione ou crie um projeto (ex: `SIS LOGÍSTICA`).
3. Crie um novo ambiente (ex: `production`).
4. Clique em **+ Add New Resource** e selecione **PostgreSQL**.
5. Configure o nome do banco como `baep_logistica`, defina um usuário e senha seguros e salve.
6. O banco de dados será inicializado e o Coolify fornecerá uma URL de conexão (Internal Connection String), similar a:
   `postgresql://postgres:senha@postgresql:5432/baep_logistica`

---

## 3. Configurando a Aplicação no Coolify

1. No mesmo projeto/ambiente do Coolify, clique em **+ Add New Resource** e selecione **Git Repository** (GitHub, GitLab ou repositório público/privado).
2. Escolha o repositório do projeto `BAEP-Controle-Materiais` e a branch `main`.
3. Nas configurações básicas da aplicação:
   * **Build Pack:** Selecione **Dockerfile** (isso fará o Coolify usar o arquivo `Dockerfile` personalizado na raiz do projeto).
   * **Ports:** Defina a porta interna como `8000`.
   * **Domains:** Digite o domínio ou IP onde o sistema ficará acessível (ex: `https://logistica.2baep.com` ou `http://10.43.19.224`). *Atenção: O uso de HTTPS com SSL é obrigatório para que a instalação do PWA funcione.*

---

## 4. Variáveis de Ambiente (Environment Variables)

Na aba **Environment Variables** da aplicação no Coolify, cadastre as seguintes variáveis:

| Variável | Valor Recomendado | Descrição |
| :--- | :--- | :--- |
| `DATABASE_URL` | *Vincule à String de Conexão Interna do Postgres criado acima* | URL de conexão automática com o Postgres |
| `DEBUG` | `False` | Desativa o modo debug para segurança e performance |
| `SECRET_KEY` | *Gere uma chave longa e aleatória* | Chave de segurança criptográfica do Django |
| `ALLOWED_HOSTS` | `*` ou `seu-dominio.com,10.43.19.224` | Hosts autorizados a responder requisições |
| `CSRF_TRUSTED_ORIGINS` | `https://seu-dominio.com` | Origens confiáveis para validação anti-CSRF |

---

## 5. Armazenamento Persistente (Volume de Mídia)

Como os containers do Docker são recriados a cada nova atualização, **todos os arquivos de recibo assinados e documentos enviados serão perdidos** se não configurarmos um volume persistente.

1. No Coolify, abra as configurações da aplicação do SIS LOGÍSTICA.
2. Acesse a aba **Storage** (ou *Volumes*).
3. Adicione um novo volume persistente para manter a pasta de mídia segura:
   * **Source Volume:** `baep-media` (ou o nome que preferir)
   * **Destination Path:** `/app/media`
4. Salve a configuração. Agora, todas as imagens e PDFs salvos no diretório `/app/media` serão gravados diretamente no disco do servidor Ubuntu, imunes a reinicializações.

---

## 6. Primeiros Passos Pós-Implantação

Quando você clicar em **Deploy**, o Coolify irá:
1. Compilar a imagem Docker do projeto.
2. Executar automaticamente o `docker-entrypoint.sh` que roda `python manage.py migrate --noinput` para criar as tabelas no PostgreSQL.
3. Coletar os arquivos estáticos e iniciar o servidor de produção Gunicorn.

Caso precise criar o primeiro usuário Administrador no banco PostgreSQL recém-criado, você pode acessar o terminal do container pelo Coolify (aba **Terminal**) e executar:

```bash
python manage.py createsuperuser
```
Siga as instruções na tela para cadastrar o RE do administrador e a respectiva senha.
