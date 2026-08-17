from django.apps import AppConfig


class TutorialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tutorial'
    verbose_name = 'Tutorial de Uso'

    def ready(self):
        """Sincroniza o conteúdo padrão do tutorial após as migrações."""
        import tutorial.seeder  # noqa: F401