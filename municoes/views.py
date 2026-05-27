from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .forms import LoteMunicaoForm, RetiradaMunicaoForm, DevolucaoMunicaoForm
from .models import LoteMunicao, RetiradaMunicao, DevolucaoMunicao, RegistroDisparoMunicao
from materiais.models import Material


@login_required
def lista_lotes(request):
    lotes = LoteMunicao.objects.filter(ativo=True).select_related('material').order_by('-data_validade', 'material__nome')
    return render(request, 'municoes/lista_lotes.html', {'lotes': lotes})


@login_required
def novo_lote(request):
    if request.method == 'POST':
        form = LoteMunicaoForm(request.POST)
        if form.is_valid():
            lote = form.save()
            messages.success(request, 'Lote de munição criado com sucesso.')
            return redirect('municoes:lista_lotes')
    else:
        form = LoteMunicaoForm()
    return render(request, 'municoes/form_lote.html', {'form': form})


@login_required
@transaction.atomic
def nova_retirada(request):
    if request.method == 'POST':
        form = RetiradaMunicaoForm(request.POST)
        if form.is_valid():
            retirada = form.save(commit=False)
            lote = retirada.lote
            material = retirada.material

            if lote.material != material:
                form.add_error('lote', 'O lote selecionado não pertence ao material informado.')
            elif lote.quantidade_atual < retirada.quantidade:
                form.add_error('quantidade', 'Quantidade maior do que saldo disponível no lote.')
            elif material.tipo != 'MUNICAO':
                form.add_error('material', 'O material precisa ser do tipo Munição.')
            else:
                lote.quantidade_atual -= retirada.quantidade
                lote.save()

                material.quantidade_disponivel -= retirada.quantidade
                material.quantidade_em_uso += retirada.quantidade
                material.save()

                retirada.registrado_por = request.user
                retirada.save()

                messages.success(request, 'Retirada de munição registrada com sucesso.')
                return redirect('municoes:lista_lotes')
    else:
        form = RetiradaMunicaoForm()
    return render(request, 'municoes/form_retirada.html', {'form': form})


@login_required
@transaction.atomic
def nova_devolucao(request):
    if request.method == 'POST':
        form = DevolucaoMunicaoForm(request.POST)
        if form.is_valid():
            devolucao = form.save(commit=False)
            retirada = devolucao.retirada
            material = retirada.material
            lote = retirada.lote
            disparos = form.cleaned_data.get('disparos') or 0
            extravios = form.cleaned_data.get('extravios') or 0
            justificativa = form.cleaned_data.get('justificativa', '').strip()
            boletim = form.cleaned_data.get('boletim_ocorrencia', '').strip()

            if devolucao.quantidade > retirada.quantidade_pendente:
                form.add_error('quantidade', 'A quantidade não pode exceder o pendente da retirada selecionada.')
            elif disparos + extravios > devolucao.quantidade:
                form.add_error('quantidade', 'A soma de disparos e extravios não pode passar da quantidade devolvida.')
            elif (disparos > 0 or extravios > 0) and not justificativa:
                form.add_error('justificativa', 'Informe justificativa quando houver disparos ou extravios.')
            elif disparos > 0 and not boletim:
                form.add_error('boletim_ocorrencia', 'Informe o número do B.O. quando houver disparos.')
            else:
                devolucao.save()
                if disparos > 0 or extravios > 0:
                    RegistroDisparoMunicao.objects.create(
                        devolucao=devolucao,
                        quantidade_disparada=disparos,
                        quantidade_extraviada=extravios,
                        justificativa=justificativa,
                        boletim_ocorrencia=boletim,
                    )

                lote.quantidade_atual += devolucao.quantidade - (disparos + extravios)
                lote.save()

                material.quantidade_disponivel += devolucao.quantidade - (disparos + extravios)
                material.quantidade_em_uso = max(material.quantidade_em_uso - devolucao.quantidade, 0)
                material.save()

                messages.success(request, 'Devolução de munição registrada com sucesso.')
                return redirect('municoes:lista_lotes')
    else:
        form = DevolucaoMunicaoForm()
    return render(request, 'municoes/form_devolucao.html', {'form': form})
