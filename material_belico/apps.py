from django.apps import AppConfig


class MaterialBelicoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'material_belico'
    verbose_name = 'Material Bélico'

    def ready(self):
        import material_belico.signals  # noqa: F401
        self._setup_grupo_e_master()

    def _setup_grupo_e_master(self):
        """Garante que o grupo material_belico exista e promove master a superuser."""
        try:
            from django.contrib.auth.models import Group, User
            # Cria o grupo se não existir
            Group.objects.get_or_create(name='material_belico')
            # Promove master a superuser se existir
            try:
                master = User.objects.get(username='master')
                if not master.is_superuser:
                    master.is_superuser = True
                    master.is_staff = True
                    master.save(update_fields=['is_superuser', 'is_staff'])
                    grupo = Group.objects.get(name='material_belico')
                    master.groups.add(grupo)
            except User.DoesNotExist:
                pass
        except Exception:
            pass  # Falha silenciosa durante makemigrations/migrate
