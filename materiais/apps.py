from django.apps import AppConfig


class MateriaisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'materiais'

    def ready(self):
        import materiais.sync_to_belico  # noqa: F401 — registra signals de sync reversa

