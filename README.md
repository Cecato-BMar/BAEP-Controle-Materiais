# 🛡️ SIS LOGÍSTICA 2º BAEP

> **Sistema Integrado de Controle Logístico, Material Bélico e Patrimônio**  
> *2º Batalhão de Ações Especiais de Polícia (2º BAEP) — Polícia Militar do Estado de São Paulo*

---

## 📌 Visão Geral

O **SIS LOGÍSTICA 2º BAEP** é uma plataforma corporativa desenvolvida para controle rigoroso, rastreabilidade e gestão de todo o ciclo de vida dos materiais, frotas, armamentos e munições de uma unidade de operações especiais.

Projetado para ambientes com alta demanda operacional, o sistema oferece suporte a controle em tempo real de cautelas e devoluções, auditoria semestral com conferência por divergências, integração com PWA para mobilidade e arquitetura de segurança reforçada para produção.

---

## ✨ Módulos do Sistema

| Módulo | Descrição |
|---|---|
| 🔫 **Material Bélico & Reserva** | Controle de armamento longo e curto, número de série, localização em cofre e status operacional. |
| 📦 **Cautelas & Movimentações** | Registro de cautelas, empréstimos e devoluções vinculados ao policial por RE e assinatura digital/conferência. |
| 🎯 **Munições** | Gestão quantitativa por lote, calibre, dotação operacional e controle de consumo em treinamento/serviço. |
| 🚓 **Frota (Viaturas)** | Gestão de viaturas, hodômetro, controle de escala, manutenções preventivas e revisões. |
| 🏷️ **Patrimônio** | Tombamento, carga patrimonial, localização física e termos de responsabilidade. |
| 📡 **Telemática** | Rádios comunicadores, terminais portáteis, câmeras operacionais e acessórios. |
| 📋 **Inventário Semestral** | Ciclos de contagem física, conferência cega, relatório de divergências e aprovação de comissão. |
| 📦 **Almoxarifado & Estoque** | Itens de consumo, ponto de pedido, estoque mínimo e requisições internas. |
| 🎓 **Tutorial & Onboarding** | Módulo de capacitação interativa para novos operadores e armeiros. |
| 🔐 **Licenciamento & Auditoria** | Verificação criptográfica de integridade de licença (RSA) e histórico de ações via `simple-history`. |

---

## 🏗️ Arquitetura e Tecnologias

- **Backend:** Python 3.12 + Django 5.x
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla), Bootstrap 5, Crispy Forms
- **Arquivos Estáticos:** WhiteNoise (`CompressedManifestStaticFilesStorage`)
- **Auditoria:** `django-simple-history` para rastreamento de alterações em todos os modelos críticos
- **Segurança:** Criptografia RSA-2048 para licenciamento, proteção CSRF com whitelist, controle estrito de `ALLOWED_HOSTS` e autenticação baseada em grupos/permissões (`require_module_permission`)
- **Servidor WSGI de Produção:** Gunicorn (3 workers, timeout 120s)
- **Containerização:** Docker (imagem base `python:3.12-slim-bookworm`)

---

## ⚙️ Pré-requisitos

- Python 3.12+
- Docker e Docker Compose (para implantação em containers)
- PostgreSQL (recomendado para produção) ou SQLite3 (desenvolvimento/homologação)

---

## 🚀 Instalação e Execução

### 1. Clonando o Repositório

```bash
git clone https://github.com/Cecato-BMar/BAEP-Controle-Materiais.git
cd BAEP-Controle-Materiais
```

### 2. Configurando o Ambiente Virtual

```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate
```

### 3. Instalando Dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configuração das Variáveis de Ambiente

Copie o arquivo de exemplo e ajuste os valores:

```bash
cp .env.example .env
```

Configure as variáveis fundamentais no `.env`:

```ini
SECRET_KEY=sua-chave-secreta-forte-aqui
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,10.43.19.224,10.43.19.225
CSRF_TRUSTED_ORIGINS=http://10.43.19.224:8002,https://10.43.19.224:8002
```

> **Dica:** Para gerar uma `SECRET_KEY` segura:
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

### 5. Banco de Dados e Estáticos

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 6. Executando o Servidor

**Desenvolvimento:**
```bash
python manage.py runserver 0.0.0.0:8000
```

**Produção com Gunicorn:**
```bash
gunicorn reserva_baep.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
```

---

## 🐳 Executando com Docker

O repositório já inclui um `Dockerfile` otimizado:

```bash
# Construir a imagem
docker build -t sis-logistica-baep .

# Executar o container
docker run -d \
  --name sis-logistica \
  -p 8002:8000 \
  --env-file .env \
  --restart unless-stopped \
  sis-logistica-baep
```

---

## 🔒 Diretrizes de Segurança para Produção

1. **`DEBUG` deve ser sempre `False`** em ambientes de produção.
2. **`SECRET_KEY`** nunca deve ser versionada no Git nem compartilhada.
3. **Chaves Privadas RSA** para emissão de licenças devem permanecer isoladas em ambiente seguro de desenvolvimento.
4. **HTTPS / SSL:** Em produção exposta ou intranet corporativa, recomenda-se usar um proxy reverso (Nginx, Traefik ou Caddy) com terminação SSL antes do Gunicorn.

---

## 📄 Licença

Uso restrito e institucional autorizado ao **2º Batalhão de Ações Especiais de Polícia (2º BAEP)**. Todos os direitos reservados.
