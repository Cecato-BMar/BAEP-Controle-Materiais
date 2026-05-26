#!/bin/bash
set -e

echo "🚀 [ENTRYPOINT] Iniciando aplicação BAEP..."
echo "🔍 [ENTRYPOINT] Aguardando banco de dados ficar disponível..."

# Aguarda o banco estar pronto (até 30 tentativas de 2 segundos = 60 segundos)
MAX_ATTEMPTS=30
attempt=0
until python -c "
import os, sys, time
try:
    import dj_database_url
    url = os.environ.get('DJANGO_DATABASE_URL') or os.environ.get('DATABASE_URL', '')
    if url.startswith('http'):
        url = ''
    if not url:
        print('Sem DATABASE_URL configurada, pulando aguardo.')
        sys.exit(0)
    config = dj_database_url.parse(url)
    import psycopg2
    conn = psycopg2.connect(
        host=config['HOST'],
        port=config.get('PORT', 5432),
        dbname=config['NAME'],
        user=config['USER'],
        password=config['PASSWORD'],
        connect_timeout=3
    )
    conn.close()
    print('Banco de dados disponível!')
    sys.exit(0)
except Exception as e:
    print(f'Banco não disponível ainda: {e}')
    sys.exit(1)
" 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $MAX_ATTEMPTS ]; then
        echo "⚠️ [ENTRYPOINT] Banco não ficou disponível após $MAX_ATTEMPTS tentativas. Iniciando mesmo assim..."
        break
    fi
    echo "⏳ [ENTRYPOINT] Tentativa $attempt/$MAX_ATTEMPTS - aguardando 2 segundos..."
    sleep 2
done

echo "📦 [ENTRYPOINT] Aplicando migrations..."
python manage.py migrate --noinput && echo "✅ [ENTRYPOINT] Migrations aplicadas com sucesso!" || echo "⚠️ [ENTRYPOINT] Erro ao aplicar migrations, verifique os logs."

echo "📁 [ENTRYPOINT] Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear 2>/dev/null || python manage.py collectstatic --noinput || true

echo "🟢 [ENTRYPOINT] Iniciando Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 reserva_baep.wsgi:application
