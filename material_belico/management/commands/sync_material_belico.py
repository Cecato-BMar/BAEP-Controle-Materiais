from django.core.management.base import BaseCommand
from material_belico.models import (
    Fuzil, EspingardaCal12, PistolaGlock, PistolaTaurus, 
    ColeteBalistico, EscudoBalistico, CapaceteBalistico, 
    TASER, RadioHT, AM640
)
from material_belico.sync import sync_fuzil, sync_espingarda, sync_glock, sync_taurus, sync_colete, sync_escudo, sync_capacete, sync_taser, sync_radio, sync_am640

class Command(BaseCommand):
    help = 'Sincroniza o módulo material_belico com o módulo de reserva de armas (materiais)'

    def handle(self, *args, **options):
        self.stdout.write("Sincronizando Fuzis...")
        for obj in Fuzil.objects.all():
            sync_fuzil(Fuzil, obj)
            
        self.stdout.write("Sincronizando Espingardas Cal.12...")
        for obj in EspingardaCal12.objects.all():
            sync_espingarda(EspingardaCal12, obj)
            
        self.stdout.write("Sincronizando Pistolas Glock...")
        for obj in PistolaGlock.objects.all():
            sync_glock(PistolaGlock, obj)
            
        self.stdout.write("Sincronizando Pistolas Taurus...")
        for obj in PistolaTaurus.objects.all():
            sync_taurus(PistolaTaurus, obj)
            
        self.stdout.write("Sincronizando Coletes Balísticos...")
        for obj in ColeteBalistico.objects.all():
            sync_colete(ColeteBalistico, obj)
            
        self.stdout.write("Sincronizando Escudos Balísticos...")
        for obj in EscudoBalistico.objects.all():
            sync_escudo(EscudoBalistico, obj)
            
        self.stdout.write("Sincronizando Capacetes Balísticos...")
        for obj in CapaceteBalistico.objects.all():
            sync_capacete(CapaceteBalistico, obj)
            
        self.stdout.write("Sincronizando TASERs...")
        for obj in TASER.objects.all():
            sync_taser(TASER, obj)
            
        self.stdout.write("Sincronizando Rádios HT...")
        for obj in RadioHT.objects.all():
            sync_radio(RadioHT, obj)
            
        self.stdout.write("Sincronizando AM-640...")
        for obj in AM640.objects.all():
            sync_am640(AM640, obj)

        self.stdout.write(self.style.SUCCESS("Sincronização concluída com sucesso!"))
