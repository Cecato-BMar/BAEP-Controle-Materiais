from django.apps import AppConfig


class MaterialBelicoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'material_belico'
    verbose_name = 'Material Bélico'

    def ready(self):
        import material_belico.signals  # noqa: F401
        from material_belico.signals import setup_on_startup
        setup_on_startup()
