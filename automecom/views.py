from datetime import datetime, date

from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.forms import forms
from django.http import HttpResponseRedirect, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from .forms import ServicoForm, UtilizadorForm, UserForm, PasswordForm, RegisterForm, MarcacaoForm, VeiculoForm, \
    MarcacaoEditForm, MarcacaoEditFormClient, OrcamentoForm, OrcamentoEditForm, OrcamentoEditFormClient, ContatoForm, \
    ObraEditForm, conselhoForm
from .models import Servico, Utilizador, Veiculo, Marcacao, Orcamento, Obra, Conselho
from django import template

from .templatetags.custom_tags import is_administrador

register = template.Library()


def is_superuser(user):
    return user.is_superuser


def home_view(request):
    return render(request, 'automecom/home.html')
def listar_orcamentos(request):
    utilizador = None
    orcamentos = None

    if request.user.is_authenticated:  # Verifica se o usuário está autenticado
        try:
            utilizador = Utilizador.objects.get(user=request.user)
        except Utilizador.DoesNotExist:
            messages.error(request, "Usuário não encontrado.")
            return redirect('automecom:login')  # Ou outra lógica para lidar com erro

        if is_administrador(request.user):  # Usuário é administrador
            orcamentos = Orcamento.objects.all()
        else:  # Usuário autenticado e não administrador
            orcamentos = Orcamento.objects.filter(user=request.user)



    return render(request, 'automecom/orcamentos.html', {
        'orcamentos': orcamentos
    })
def pedido_orcamento(request):
    is_authenticated = request.user.is_authenticated

    if request.method == 'POST':
        form = OrcamentoForm(request.POST)
        veiculo_form = VeiculoForm(request.POST)


        form.fields['nome'].required = not is_authenticated
        form.fields['email'].required = not is_authenticated
        form.fields['telefone'].required = not is_authenticated
        if 'apelido' in form.fields: # Verifique se o campo 'apelido' existe no seu OrcamentoForm
            form.fields['apelido'].required = not is_authenticated

        if form.is_valid() and veiculo_form.is_valid():
            orcamento = form.save(commit=False)
            orcamento.veiculo = veiculo_form.save() # Cria e associa o veículo

            if is_authenticated:
                orcamento.user = request.user
                orcamento.nome = request.user.first_name
                orcamento.apelido = request.user.last_name
                orcamento.email = request.user.email

                try:
                    utilizador_perfil = Utilizador.objects.get(user=request.user)
                    if utilizador_perfil.telefone:
                        orcamento.telefone = utilizador_perfil.telefone
                    else:
                        orcamento.telefone = form.cleaned_data.get('telefone')
                except Utilizador.DoesNotExist:
                    orcamento.telefone = form.cleaned_data.get('telefone')
            else:
                # utilizador não autenticado
                orcamento.telefone = form.cleaned_data.get('telefone')

            orcamento.save()
            form.save_m2m() # Salva as relações ManyToMany (ex: Servicos)

            messages.success(request, "Seu pedido de orçamento foi enviado com sucesso!")
            return redirect('automecom:orcamentos')

        else:
            messages.error(request, "Houve um erro ao enviar o pedido. Por favor, verifique os dados.")

    else: # request.method == 'GET'
        initial_data_orcamento = {}
        if is_authenticated:
            # Pré-popular os campos do formulário para usuários logados
            initial_data_orcamento = {
                'nome': request.user.first_name,
                'apelido': request.user.last_name,
                'email': request.user.email,
            }
            # Tenta buscar o telefone do modelo Utilizador para pré-popular
            try:
                utilizador_perfil = Utilizador.objects.get(user=request.user)
                initial_data_orcamento['telefone'] = utilizador_perfil.telefone
            except Utilizador.DoesNotExist:
                pass
            except AttributeError:
                pass # Se o atributo 'telefone' não existe em Utilizador

        form = OrcamentoForm(initial=initial_data_orcamento)
        veiculo_form = VeiculoForm() # Veículo não é pré-populado por padrão, mas você pode adicionar lógica aqui

    return render(request, 'automecom/orcamento.html', {
        'form': form,
        'veiculo_form': veiculo_form
    })

@login_required
def view_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('automecom:Home'))


def view_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(
            request,
            username=username,
            password=password)

        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse('automecom:Home'))
        else:
            return render(request, 'automecom/login.html', {
                'message': 'Credenciais invalidas.'
            })

    return render(request, 'automecom/login.html')


def servico_view(request):
    servicos = Servico.objects.all()
    return render(request, 'automecom/servico.html', {
        'servicos': servicos,
        'administrador': is_administrador(request.user)
    })


def servico_create(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('automecom:login'))

    if not is_administrador(request.user):
        return HttpResponseRedirect(reverse('automecom:Home'))

    if request.method == 'POST':
        form = ServicoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('automecom:Servico'))
    form = ServicoForm()

    context = {'form': form}
    return render(request, 'automecom/create.html', context)


def conselho_create(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('automecom:login'))

    if not is_administrador(request.user):
        return HttpResponseRedirect(reverse('automecom:Home'))

    if request.method == 'POST':
        form = conselhoForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('automecom:Conselho'))
    form = conselhoForm()

    context = {'form': form}
    return render(request, 'automecom/criarConselho.html', context)


def servico_edit(request, post_id):
    if not is_administrador(request.user):
        return HttpResponseRedirect(reverse('automecom:Home'))

    post = Servico.objects.get(id=post_id)
    if request.method == 'POST':
        form = ServicoForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('automecom:Servico'))
    else:
        form = ServicoForm(instance=post)
    context = {'form': form, 'post_id': post_id}
    return render(request, 'automecom/edit.html', context)


@login_required
def servico_delete(request, post_id):
    if Servico.objects.filter(pk=post_id).exists():
        Servico.objects.get(pk=post_id).delete()
    return HttpResponseRedirect(reverse('automecom:Servico'))


def conselho_view(request):
    conselhos = Conselho.objects.all()
    return render(request, 'automecom/conselhos.html', {
        'conselhos': conselhos,
        'administrador': is_administrador(request.user)
    })

@login_required
def conselho_delete(request, post_id):
    if Conselho.objects.filter(pk=post_id).exists():
        Conselho.objects.get(pk=post_id).delete()
    return HttpResponseRedirect(reverse('automecom:Conselho'))




def contacto_view(request):
    form = ContatoForm(request.POST)
    if request.method == "POST":
        if request.user.is_authenticated:

            primeiro_nome = request.user.first_name
            ultimo_nome = request.user.last_name
            email = request.user.email
            telemovel = request.POST.get("telemovel", "")
            mensagem = request.POST.get("mensagem", "")
            print(primeiro_nome)
            print(email)
            print(mensagem)

            # Verificação de campos obrigatórios
            if not mensagem.strip():
                messages.error(request, "Por favor preencha todos os campos obrigatórios.")
                return redirect("automecom:Contacto")  # ou render(request, "...", {...}) se quiseres manter os dados

            # Corpo do e-mail
            corpo_email = f"""
               Nome: {primeiro_nome + " " + ultimo_nome}
               E-mail: {email}
               Telefone: {telemovel}

               Mensagem:
               {mensagem}
               """

            # Enviar e-mail
            send_mail(
                subject=f"Nova mensagem de {primeiro_nome} {ultimo_nome}",
                message=corpo_email,
                from_email="envioemailautomecom@gmail.com",
                recipient_list=["geral@automecom.com"],
            )

            print("a bia vai passar")
            messages.success(request, "Sua mensagem foi enviada com sucesso!")
        else:
            primeiro_nome = request.POST.get("primeiro_nome", "")
            ultimo_nome = request.POST.get("ultimo_nome", "")
            email = request.POST.get("email", "")
            telemovel = request.POST.get("telemovel", "")
            mensagem = request.POST.get("mensagem", "")
            print(primeiro_nome)
            print(email)
            print(mensagem)

            # Verificação de campos obrigatórios
            if not mensagem.strip():
                messages.error(request, "Por favor preencha todos os campos obrigatórios.")
                return redirect("automecom:Contacto")  # ou render(request, "...", {...}) se quiseres manter os dados

            # Corpo do e-mail
            corpo_email = f"""
               Nome: {primeiro_nome + " " + ultimo_nome}
               E-mail: {email}
               Telefone: {telemovel}

               Mensagem:
               {mensagem}
               """

            # Enviar e-mail
            send_mail(
                subject=f"Nova mensagem de {primeiro_nome} {ultimo_nome}",
                message=corpo_email,
                from_email="envioemailautomecom@gmail.com",
                recipient_list=["beatrizmneves@gmail.com"],
            )
            messages.success(request, "Sua mensagem foi enviada com sucesso!")


        # return redirect("automeom:contactos")  # para limpar o formulário após envio

    return render(request, "automecom/contactos.html", {'form': form})


def garantia_view(request):
    return render(request, 'automecom/garantia.html')


def privacidade_view(request):
    return render(request, 'automecom/privacidade.html')


def obras_view(request):
    # Verifica se o utilizador existe (boa prática)
    if not Utilizador.objects.filter(user=request.user).exists():
        messages.error(request, "Perfil de utilizador não encontrado. Por favor, contate o suporte.")

    ordenar_por = request.GET.get('filtro', '-data')

    if is_administrador(request.user):
        marcacoes_realizadas = Marcacao.objects.filter(estado='Terminada')
    else:
        try:
            utilizador = Utilizador.objects.get(user=request.user)
            marcacoes_realizadas = Marcacao.objects.filter(utilizador=utilizador, estado='Terminada')
        except Utilizador.DoesNotExist:
            # Caso o utilizador não seja encontrado (mesmo após a verificação inicial, para segurança)
            messages.error(request, "Perfil de utilizador não encontrado para filtragem. Por favor, contate o suporte.")
            marcacoes_realizadas = Marcacao.objects.none()



    marcacoes_realizadas = marcacoes_realizadas.order_by(ordenar_por)

    context = {
        "marcacoes": marcacoes_realizadas,
        "ordenar_por": ordenar_por,  # Passa o valor de ordenação para o template manter a seleção
    }
    return render(request, 'automecom/obras.html', context)

def sobre_view(request):
    return render(request, 'automecom/sobre.html')

def marcacoes_view(request):
    # Obter o utilizador logado
    utilizador = Utilizador.objects.get(user=request.user)

    filtro = request.GET.get('filtro', 'todos')  # Padrão é 'todos'


    if is_administrador(request.user):
        marcacoes = Marcacao.objects.all().order_by('data', 'hora')
        marcacoes = marcacoes.exclude(estado='Terminada')

    else:
        marcacoes = Marcacao.objects.filter(utilizador=utilizador).order_by('data', 'hora')
        marcacoes = marcacoes.exclude(estado='Terminada')

    if filtro != 'todos':
        marcacoes = marcacoes.filter(estado=filtro)

        # Passar as marcações e outros dados necessários para o contexto
    context = {
        "marcacoes": marcacoes,
        "filtro": filtro,  # Passando o filtro para o template
    }

    return render(request, 'automecom/marcacoes.html', context)
def register_view(request):
    if request.method == 'GET':
        form = RegisterForm()
        return render(request, 'automecom/register.html', {'form': form})

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username
            utilizador = Utilizador()
            utilizador.nome = user.username
            utilizador.user = user
            utilizador.telefone = form.cleaned_data['telefone']

            user.save()
            utilizador.save()
            login(request, user)
            return redirect('automecom:Home')
        else:
            return render(request, 'automecom/register.html', {'form': form})


def perfil_view(request):

        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('automecom:login'))

        # Verifica se o Utilizador existe, e se não, cria um novo ou apenas prossegue
        post, created = Utilizador.objects.get_or_create(user=request.user)

        if request.method == 'POST':
            form = UserForm(request.POST, request.FILES, instance=request.user)
            form2 = UtilizadorForm(request.POST, request.FILES, instance=post)
            form3 = PasswordForm(request.user, request.POST)
            if form.is_valid() and form2.is_valid() and form3.is_valid():
                form.save()
                form2.save()
                form3.save()
                return HttpResponseRedirect(reverse('automecom:perfil'))
        else:
            form = UserForm(instance=request.user)
            form2 = UtilizadorForm(instance=post)
            form3 = PasswordForm(request.user)
            context = {'form': form, 'form2': form2, 'form3': form3}

        return render(request, 'automecom/perfil.html',context)

@login_required
def utilizador_delete(request, post_id):
    if Utilizador.objects.filter(pk=post_id).exists():
        logout(request)
        Utilizador.objects.get(pk=post_id).user.delete()
    return HttpResponseRedirect(reverse('automecom:Home'))


def marcacao_view(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('automecom:login'))



    if request.method == 'GET':
        form = MarcacaoForm()
        form2 = VeiculoForm()
        if request.user.is_authenticated:
            del form.fields['nome']
            del form.fields['apelido']
            del form.fields['email']
        return render(request, 'automecom/marcacao.html', {'form': form, 'form2': form2})

    if request.method == 'POST':
        form = MarcacaoForm(request.POST)
        form2 = VeiculoForm(request.POST)

        if form2.is_valid():

            veiculo = form2.save()

            if request.user.is_authenticated:
                marcacao = Marcacao(
                    nome=request.user.first_name,
                    apelido=request.user.last_name,
                    email=request.user.email,
                    imagem=request.POST['imagem'],
                    veiculo=veiculo,
                    data=request.POST['data'],
                    hora=request.POST['hora'],
                    descricao=request.POST['descricao']
                )
                utilizador = Utilizador.objects.get(user=request.user)
                marcacao.utilizador = utilizador
                marcacao.save()

                # Adicionar os serviços à marcação
                servicos_ids = request.POST.getlist('servicos')  # Obtém os IDs dos serviços
                marcacao.servicos.set(servicos_ids)  # Define os serviços usando o método set()
            else:
                marcacao = Marcacao(
                    nome=request.POST['nome'],
                    apelido=request.POST['apelido'],
                    email=request.POST['email'],
                    imagem=request.POST['imagem'],
                    veiculo=veiculo,
                    data=request.POST['data'],
                    hora=request.POST['hora'],
                    descricao=request.POST['descricao']
                )
                marcacao.save()

                # Adicionar os serviços à marcação
                servicos_ids = request.POST.getlist('servicos')  # Obtém os IDs dos serviços
                marcacao.servicos.set(servicos_ids)  # Define os serviços usando o método set()
            return redirect('automecom:marcacoes')

        else:
            return render(request, 'automecom/marcacao.html', {'form': form, 'form2': form2})


def marcacao_edit(request, post_id):
    post = get_object_or_404(Marcacao, id=post_id)

    # Verifica se o usuário tem permissão para editar
    if not is_administrador(request.user) and post.utilizador.user != request.user:
        return HttpResponseRedirect(reverse('automecom:Home'))

    # POST: Atualizar os dados
    if request.method == 'POST':
        if is_administrador(request.user):
            form = MarcacaoEditForm(request.POST, request.FILES, instance=post)
        else:
            form = MarcacaoEditFormClient(request.POST, request.FILES, instance=post)

        if form.is_valid():
            form.save()
            messages.success(request, "A marcação foi alterada com sucesso!")
            return HttpResponseRedirect(reverse('automecom:marcacoes'))
        else:
            # Retornar o formulário com erros se não for válido
            print(form.errors)  # Loga os erros no console
            messages.error(request, "Erro ao salvar a marcação. Por favor, corrija os erros abaixo.")
            context = {'form': form, 'post_id': post_id}
            return render(request, 'automecom/editmarcacao.html', context)

    # GET: Exibir o formulário com os dados atuais
    else:
        if is_administrador(request.user):
            form = MarcacaoEditForm(instance=post)
        else:
            form = MarcacaoEditFormClient(instance=post)
        context = {'form': form, 'post_id': post_id}
        return render(request, 'automecom/editmarcacao.html', context)



def alterar_estado_marcacao(request, marcacao_id, novo_estado):
    if not is_administrador(request.user):
        return HttpResponseForbidden("Acesso negado.")

    print("bia")
    marcacao = get_object_or_404(Marcacao, id=marcacao_id)
    print(marcacao_id)
    if novo_estado == "Aceite":
        print("aceitou")
        marcacao.estado = "Confirmado"
        marcacao.save()
    else:
        print("recusado")
        marcacao.estado = "Recusado"
        marcacao.save()

    return redirect('automecom:marcacoes')


def orcamento_edit(request, post_id):
    post = get_object_or_404(Orcamento, id=post_id)

    # Verifica se o usuário tem permissão para editar
    if not is_administrador(request.user) and post.user != request.user:
        return HttpResponseRedirect(reverse('automecom:Home'))

    # POST: Atualizar os dados
    if request.method == 'POST':
        if is_administrador(request.user):
            form = OrcamentoEditForm(request.POST, request.FILES, instance=post)
        else:
            form = OrcamentoEditFormClient(request.POST, request.FILES, instance=post)

        if form.is_valid():
            form.save()
            messages.success(request, "Orçamento editado com sucesso!")
            return HttpResponseRedirect(reverse('automecom:orcamentos'))
        else:
            # Retornar o formulário com erros se não for válido
            print(form.errors)  # Loga os erros no console
            messages.error(request, "Erro ao salvar o orçamento. Por favor, corrija os erros abaixo.")
            context = {'form': form, 'post_id': post_id}
            return render(request, 'automecom/editorcamento.html', context)

    # GET: Exibir o formulário com os dados atuais
    else:
        if is_administrador(request.user):
            form = OrcamentoEditForm(instance=post)
        else:
            form = OrcamentoEditFormClient(instance=post)
        context = {'form': form, 'post_id': post_id}
        return render(request, 'automecom/editorcamento.html', context)


def marcacao_delete(request, post_id):
    if Marcacao.objects.filter(pk=post_id).exists():
        Marcacao.objects.get(pk=post_id).delete()
        messages.success(request, "Marcação apagada com sucesso!")
    return HttpResponseRedirect(reverse('automecom:marcacoes'))

def orcamento_delete(request, post_id):
    if Orcamento.objects.filter(pk=post_id).exists():
        Orcamento.objects.get(pk=post_id).delete()
        messages.success(request, "Orçamento apagado com sucesso!")
    return HttpResponseRedirect(reverse('automecom:orcamentos'))

def editar_obra(request, obra_id):
    post = get_object_or_404(Marcacao, id=obra_id)
    # Verifica se o usuário tem permissão para editar
    if not is_administrador(request.user) and post.utilizador.user != request.user:
        return HttpResponseRedirect(reverse('automecom:Home'))
    # POST: Atualizar os dados
    if request.method == 'POST':
        if is_administrador(request.user):
            form = MarcacaoEditForm(request.POST, request.FILES, instance=post)
        else:
            form = MarcacaoEditFormClient(request.POST, request.FILES, instance=post)

        if form.is_valid():
            form.save()
            messages.success(request, "A obra foi alterada com sucesso!")
            return HttpResponseRedirect(reverse('automecom:obras'))
        else:
            # Retornar o formulário com erros se não for válido
            print(form.errors)  # Loga os erros no console
            messages.error(request, "Erro ao salvar a obra. Por favor, corrija os erros abaixo.")
            context = {'form': form, 'post_id': obra_id}
            return render(request, 'automecom/editobras.html', context)

    # GET: Exibir o formulário com os dados atuais
    else:
         form = MarcacaoEditForm(instance=post)

    return render(request, 'automecom/editobras.html', {'form': form, 'obra': post})

from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages



def marcacao(request):
    return render(request, 'automecom/marcacao.html')


