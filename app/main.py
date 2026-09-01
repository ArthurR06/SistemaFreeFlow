# ==========================================
# FREEFLOW - API PRINCIPAL
# ==========================================

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import numpy as np
import csv
import io

from datetime import datetime
from starlette.middleware.sessions import SessionMiddleware
from app.database import Base, engine, get_db
from app import schemas, crud, anomaly, models

from app.config import (
    VALOR_PASSAGEM,
    TEMPO_SEM_DADOS_ALERTA,
    REFRESH_SEGUNDOS,
    SESSION_SECRET,
    CONCESSIONARIAS_ADMIN
)


# ==========================================
# BANCO DE DADOS
# ==========================================

Base.metadata.create_all(
    bind=engine
)


# ==========================================
# APLICAÇÃO FASTAPI
# ==========================================

app = FastAPI(
    title="FreeFlow"
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET
)

# ==========================================
# TEMPLATES HTML
# ==========================================

templates = Jinja2Templates(
    directory="app/templates"
)
# ==========================================

# ==========================================
# CLIENTES DEMONSTRATIVOS
# ==========================================

CLIENTES_DEMO = [
    {"nome": "Cliente Demo 01", "cpf": "10000000001"},
    {"nome": "Cliente Demo 02", "cpf": "10000000002"},
    {"nome": "Cliente Demo 03", "cpf": "10000000003"},
    {"nome": "Cliente Demo 04", "cpf": "10000000004"},
    {"nome": "Cliente Demo 05", "cpf": "10000000005"},
    {"nome": "Cliente Demo 06", "cpf": "10000000006"},
    {"nome": "Cliente Demo 07", "cpf": "10000000007"},
    {"nome": "Cliente Demo 08", "cpf": "10000000008"},
    {"nome": "Cliente Demo 09", "cpf": "10000000009"},
    {"nome": "Cliente Demo 10", "cpf": "10000000010"},
]

CPF_DEMO_ANTIGO = "12345678900"


def obter_proprietario_demo_disponivel(
    db: Session
):
    for dados in CLIENTES_DEMO:

        proprietario = (
            db.query(models.Proprietario)
            .filter(
                models.Proprietario.cpf == dados["cpf"]
            )
            .first()
        )

        # Cliente ainda não existe
        if not proprietario:
            proprietario = models.Proprietario(
                nome=dados["nome"],
                cpf=dados["cpf"]
            )

            db.add(proprietario)
            db.commit()
            db.refresh(proprietario)

            return proprietario

        # Cliente existe, mas ainda não tem veículo
        veiculo_existente = (
            db.query(models.Veiculo)
            .filter(
                models.Veiculo.proprietario_id
                == proprietario.id
            )
            .first()
        )

        if not veiculo_existente:
            return proprietario

    return None


def obter_ou_criar_veiculo_demo(
    db: Session,
    uid: str
):
    uid = uid.strip().upper()

    # Procura a placa/UID
    veiculo = (
        db.query(models.Veiculo)
        .filter(
            models.Veiculo.uid_rfid == uid
        )
        .first()
    )

    # ======================================
    # VEÍCULO JÁ CADASTRADO
    # ======================================

    if veiculo:

        if veiculo.placa != uid:
            veiculo.placa = uid

        # Corrige os veículos antigos que
        # estavam todos no mesmo CPF demo
        if (
            veiculo.proprietario
            and veiculo.proprietario.cpf
            == CPF_DEMO_ANTIGO
        ):
            novo_proprietario = (
                obter_proprietario_demo_disponivel(db)
            )

            if novo_proprietario:
                veiculo.proprietario_id = (
                    novo_proprietario.id
                )

        db.commit()
        db.refresh(veiculo)

        return veiculo

    # ======================================
    # NOVA PLACA / UID
    # ======================================

    proprietario = (
        obter_proprietario_demo_disponivel(db)
    )

    if not proprietario:
        raise HTTPException(
            status_code=409,
            detail=(
                "Não há clientes demonstrativos "
                "disponíveis para vincular."
            )
        )

    veiculo = models.Veiculo(
        placa=uid,
        uid_rfid=uid,
        proprietario_id=proprietario.id
    )

    db.add(veiculo)
    db.commit()
    db.refresh(veiculo)

    print("")
    print("==============================")
    print("NOVO VEÍCULO CADASTRADO")
    print("==============================")
    print(f"Placa/UID: {uid}")
    print(f"Cliente: {proprietario.nome}")
    print(f"CPF: {proprietario.cpf}")
    print("==============================")

    return veiculo

# ==========================================
# FUNÇÃO AUXILIAR DE TEMPO
# ==========================================

def formatar_tempo(
    segundos: int
) -> str:

    if segundos < 60:

        return (
            f"{segundos} segundo(s)"
        )

    elif segundos < 3600:

        minutos = (
            segundos // 60
        )

        return (
            f"{minutos} minuto(s)"
        )

    else:

        horas = (
            segundos // 3600
        )

        return (
            f"{horas} hora(s)"
        )


# ==========================================
# ROTA PRINCIPAL
# ==========================================

@app.get("/")
def raiz():

    return {
        "mensagem":
            "API FreeFlow funcionando"
    }


# ==========================================
# EVENTOS RFID
# ==========================================

@app.post(
    "/evento",
    response_model=schemas.EventoResponse
)
def criar_evento(
    evento: schemas.EventoCreate,
    db: Session = Depends(get_db)
):

    # ======================================
    # 1. SALVA A PASSAGEM
    # ======================================

    novo_evento = crud.criar_evento(
        db,
        evento
    )


    # ======================================
    # 2. ANALISA IMEDIATAMENTE
    # ======================================

    anomaly.analisar_eventos(
        db
    )

    db.refresh(
        novo_evento
    )


    # ======================================
    # 3. SOMENTE DUPLICIDADE NÃO PODE COBRAR
    # ======================================

    if novo_evento.anomalia != "duplicidade":

        uid = (
            novo_evento.id_veiculo
            .strip()
            .upper()
        )


        # Descobre ou cria o veículo
        veiculo = obter_ou_criar_veiculo_demo(
            db,
            uid
        )


        # Evita cobrança duplicada
        cobranca_existente = (
            db.query(models.Cobranca)
            .filter(
                models.Cobranca.evento_id
                == novo_evento.id
            )
            .first()
        )


        if not cobranca_existente:

            nova_cobranca = models.Cobranca(
                evento_id=novo_evento.id,
                veiculo_id=veiculo.id,
                valor=novo_evento.valor,
                status="pendente",
                timestamp_criacao=(
                    datetime.now()
                    .isoformat(
                        timespec="seconds"
                    )
                )
            )


            db.add(
                nova_cobranca
            )

            db.commit()


            print("")
            print("==============================")
            print("COBRANÇA GERADA")
            print("==============================")
            print(f"Placa: {veiculo.placa}")
            print(
                f"Valor: R$ {novo_evento.valor:.2f}"
            )
            print("Status: PENDENTE")
            print("==============================")


    else:

        print("")
        print("==============================")
        print("COBRANÇA NÃO GERADA")
        print("==============================")
        print(
            f"Motivo: {novo_evento.anomalia}"
        )
        print("==============================")


    return novo_evento


# ==========================================
# ANÁLISE MANUAL
# ==========================================

@app.post("/analisar")
def analisar(
    db: Session = Depends(get_db)
):

    anomaly.analisar_eventos(
        db
    )

    return {
        "mensagem":
            "Análise concluída"
    }


# ==========================================
# LISTA EVENTOS
# ==========================================

@app.get(
    "/eventos",
    response_model=list[
        schemas.EventoResponse
    ]
)
def listar_eventos(
    db: Session = Depends(get_db)
):

    return crud.listar_eventos(
        db
    )


# ==========================================
# PÁGINA DASHBOARD
# ==========================================

@app.get(
    "/dashboard",
    response_class=HTMLResponse
)
def dashboard(
    request: Request
):

    if not request.session.get(
        "admin_logado"
    ):
        return RedirectResponse(
            url="/admin/login",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "concessionaria_nome":
                request.session.get(
                    "concessionaria_nome"
                )
        }
    )

# ==========================================
# PÁGINA PORTAL DO CLIENTE
# ==========================================

@app.get(
    "/portal",
    response_class=HTMLResponse
)
def portal_cliente(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="portal.html"
    )

# ==========================================
# ÁREA ADMINISTRATIVA - LOGIN
# ==========================================

@app.get(
    "/admin/login",
    response_class=HTMLResponse
)
def admin_login_page(
    request: Request
):
    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={
            "erro": None
        }
    )


@app.post(
    "/admin/login"
)
async def admin_login(
    request: Request
):
    form = await request.form()

    usuario = form.get("usuario")
    senha = form.get("senha")

    credencial = CONCESSIONARIAS_ADMIN.get(
        usuario
    )

    if (
        credencial
        and senha == credencial["senha"]
    ):
        request.session["admin_logado"] = True

        request.session[
            "concessionaria_id"
        ] = credencial["id"]

        request.session[
            "concessionaria_nome"
        ] = credencial["nome"]

        request.session[
            "faixas_permitidas"
        ] = credencial["faixas"]

        return RedirectResponse(
            url="/dashboard",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={
            "erro": "Usuário ou senha inválidos."
        },
        status_code=401
    )

    # ==========================================
# LOGOUT ADMINISTRATIVO
# ==========================================

@app.get(
    "/admin/logout"
)
def admin_logout(
    request: Request
):

    request.session.clear()

    return RedirectResponse(
        url="/admin/login",
        status_code=303
    )

# ==========================================
# PÁGINA DE COBRANÇAS
# ==========================================

@app.get(
    "/cobrancas",
    response_class=HTMLResponse
)
def portal_cobrancas(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="cobrancas.html"
    )

# ==========================================
# PÁGINA PIX
# ==========================================

@app.get(
    "/pix",
    response_class=HTMLResponse
)
def pagina_pix(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="pix.html"
    )



# ==========================================
# PÁGINA BOLETO
# ==========================================

@app.get(
    "/boleto",
    response_class=HTMLResponse
)
def pagina_boleto(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="boleto.html"
    )

# ==========================================
# CONSULTA PORTAL
# ==========================================

@app.post(
    "/portal/consultar"
)
def consultar_portal(
    consulta: schemas.PortalConsulta,
    db: Session = Depends(get_db)
):

    # Normaliza CPF
    cpf = (
        consulta.cpf
        .replace(".", "")
        .replace("-", "")
        .strip()
    )

    # Normaliza placa
    placa = (
        consulta.placa
        .strip()
        .upper()
    )


    # ======================================
    # PROPRIETÁRIO
    # ======================================

    proprietario = (
        crud.buscar_proprietario_por_cpf(
            db,
            cpf
        )
    )


    if not proprietario:

        raise HTTPException(
            status_code=404,
            detail="CPF não encontrado."
        )


    # ======================================
    # VEÍCULO
    # ======================================

    veiculo = (
        crud.buscar_veiculo_por_placa(
            db,
            placa
        )
    )


    if not veiculo:

        raise HTTPException(
            status_code=404,
            detail="Veículo não encontrado."
        )


    # Verifica se pertence ao CPF
    if (
        veiculo.proprietario_id
        != proprietario.id
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "A placa informada "
                "não pertence a este CPF."
            )
        )


    # ======================================
    # COBRANÇAS DO VEÍCULO
    # ======================================

    cobrancas = [

        cobranca

        for cobranca
        in crud.listar_cobrancas(db)

        if (
            cobranca.veiculo_id
            == veiculo.id
        )

    ]


    total_pendentes = sum(

        1

        for cobranca
        in cobrancas

        if (
            cobranca.status
            == "pendente"
        )

    )


    total_pagas = sum(

        1

        for cobranca
        in cobrancas

        if (
            cobranca.status
            == "pago"
        )

    )


    valor_pendente = sum(

        cobranca.valor

        for cobranca
        in cobrancas

        if (
            cobranca.status
            == "pendente"
        )

    )


    # ======================================
    # CPF MASCARADO
    # ======================================

    cpf_mascarado = (

        f"***.***.***-{cpf[-2:]}"

        if len(cpf) == 11

        else "***"

    )


    # ======================================
    # RESPOSTA
    # ======================================

    return {

        "proprietario": {

            "nome":
                proprietario.nome,

            "cpf":
                cpf_mascarado

        },


        "veiculo": {

            "placa":
                veiculo.placa

        },


        "valor_pendente":
            valor_pendente,


        "total_pendentes":
            total_pendentes,


        "total_pagas":
            total_pagas,


        "cobrancas": [

            {

                "id":
                    cobranca.id,


                "timestamp_evento": (

                    cobranca.evento
                    .timestamp_evento

                    if cobranca.evento

                    else "-"

                ),


                "faixa": (

                    cobranca.evento.faixa

                    if cobranca.evento

                    else "-"

                ),


                "valor":
                    cobranca.valor,


                "status":
                    cobranca.status

            }

            for cobranca
            in cobrancas

        ]

    }


# ==========================================
# PAGAMENTO SIMULADO
# ==========================================

@app.post(
    "/portal/cobrancas/{cobranca_id}/pagar"
)
def pagar_cobranca(
    cobranca_id: int,
    pagamento: schemas.PortalPagamento,
    db: Session = Depends(get_db)
):

    # Normaliza CPF
    cpf = (
        pagamento.cpf
        .replace(".", "")
        .replace("-", "")
        .strip()
    )


    # Normaliza placa
    placa = (
        pagamento.placa
        .strip()
        .upper()
    )


    proprietario = (
        crud.buscar_proprietario_por_cpf(
            db,
            cpf
        )
    )


    veiculo = (
        crud.buscar_veiculo_por_placa(
            db,
            placa
        )
    )


    if (
        not proprietario
        or not veiculo
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Cliente ou veículo "
                "não encontrado."
            )
        )


    # ======================================
    # SEGURANÇA DO PORTAL
    # ======================================

    if (
        veiculo.proprietario_id
        != proprietario.id
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Veículo não pertence "
                "ao CPF informado."
            )
        )


    # ======================================
    # COBRANÇA
    # ======================================

    cobranca = (

        db.query(
            models.Cobranca
        )

        .filter(
            models.Cobranca.id
            == cobranca_id
        )

        .first()

    )


    if not cobranca:

        raise HTTPException(
            status_code=404,
            detail=(
                "Cobrança não encontrada."
            )
        )


    # Impede pagar cobrança
    # de outro veículo
    if (
        cobranca.veiculo_id
        != veiculo.id
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Esta cobrança não pertence "
                "ao veículo informado."
            )
        )


    # Já estava paga
    if (
        cobranca.status
        == "pago"
    ):

        return {

            "mensagem":
                "Cobrança já estava paga.",

            "cobranca_id":
                cobranca.id,

            "status":
                cobranca.status

        }


    # Marca como pago
    cobranca.status = "pago"


    db.commit()

    db.refresh(
        cobranca
    )


    return {

        "mensagem":
            "Pagamento realizado com sucesso.",

        "cobranca_id":
            cobranca.id,

        "status":
            cobranca.status

    }

# ==========================================
# COBRANÇAS DA CONCESSIONÁRIA
# ==========================================

@app.get(
    "/admin/cobrancas",
    response_class=HTMLResponse
)
def admin_cobrancas(
    request: Request,
    db: Session = Depends(get_db)
):

    # ======================================
    # PROTEÇÃO
    # ======================================

    if not request.session.get(
        "admin_logado"
    ):
        return RedirectResponse(
            url="/admin/login",
            status_code=303
        )


    faixas_permitidas = (
        request.session.get(
            "faixas_permitidas",
            []
        )
    )


    # ======================================
    # COBRANÇAS DA CONCESSIONÁRIA
    # ======================================

    cobrancas = (
        db.query(
            models.Cobranca
        )
        .join(
            models.EventoPassagem,
            models.Cobranca.evento_id
            == models.EventoPassagem.id
        )
        .filter(
            models.EventoPassagem.faixa.in_(
                faixas_permitidas
            )
        )
        .order_by(
            models.Cobranca.id.desc()
        )
        .all()
    )


    # ======================================
    # AGRUPA POR VEÍCULO
    # ======================================

    resumo = {}


    for cobranca in cobrancas:

        veiculo = cobranca.veiculo

        if not veiculo:
            continue


        proprietario = (
            veiculo.proprietario
        )


        if veiculo.id not in resumo:

            cpf = (
                proprietario.cpf
                if proprietario
                else ""
            )


            cpf_mascarado = (
                f"***.***.***-{cpf[-2:]}"
                if len(cpf) == 11
                else "***"
            )


            resumo[veiculo.id] = {

                "id":
                    veiculo.id,

                "placa":
                    veiculo.placa,

                "proprietario": (
                    proprietario.nome
                    if proprietario
                    else "-"
                ),

                "cpf":
                    cpf_mascarado,

                "total_gerado":
                    0.0,

                "total_pago":
                    0.0,

                "total_pendente":
                    0.0,

                "pagas":
                    0,

                "pendentes":
                    0,

                "cobrancas":
                    []

            }


        item = resumo[
            veiculo.id
        ]


        item["total_gerado"] += (
            cobranca.valor
        )


        if cobranca.status == "pago":

            item["pagas"] += 1

            item["total_pago"] += (
                cobranca.valor
            )

        else:

            item["pendentes"] += 1

            item["total_pendente"] += (
                cobranca.valor
            )


        item["cobrancas"].append(
            {
                "id":
                    cobranca.id,

                "data": (
                    cobranca.evento
                    .timestamp_evento

                    if cobranca.evento

                    else "-"
                ),

                "faixa": (
                    cobranca.evento.faixa

                    if cobranca.evento

                    else "-"
                ),

                "valor":
                    cobranca.valor,

                "status":
                    cobranca.status
            }
        )


    veiculos = sorted(
        resumo.values(),
        key=lambda item:
            item["placa"]
    )


    # ======================================
    # TOTAIS
    # ======================================

    total_veiculos = len(
        veiculos
    )


    total_gerado = sum(
        cobranca.valor
        for cobranca in cobrancas
    )


    total_pendente = sum(
        cobranca.valor
        for cobranca in cobrancas
        if cobranca.status == "pendente"
    )


    total_recebido = sum(
        cobranca.valor
        for cobranca in cobrancas
        if cobranca.status == "pago"
    )


    # ======================================
    # PÁGINA
    # ======================================

    return templates.TemplateResponse(
        request=request,
        name="admin_cobrancas.html",
        context={

            "concessionaria_nome":
                request.session.get(
                    "concessionaria_nome"
                ),

            "veiculos":
                veiculos,

            "total_veiculos":
                total_veiculos,

            "total_gerado":
                total_gerado,

            "total_pendente":
                total_pendente,

            "total_recebido":
                total_recebido

        }
    )

# ==========================================
# DADOS DO DASHBOARD
# ==========================================

@app.get(
    "/dashboard-data"
)
def dashboard_data(
    request: Request,
    db: Session = Depends(get_db)
):

    # Protege os dados do monitoramento
    if not request.session.get(
        "admin_logado"
    ):
        raise HTTPException(
            status_code=401,
            detail="Acesso não autorizado."
        )

    # Faixas permitidas para a concessionária logada
    faixas_permitidas = (
        request.session.get(
            "faixas_permitidas",
            []
        )
    )

    # Todos os eventos apenas das faixas permitidas
    eventos_todos = (
        db.query(
            models.EventoPassagem
        )
        .filter(
            models.EventoPassagem.faixa.in_(
                faixas_permitidas
            )
        )
        .order_by(
            models.EventoPassagem.id.desc()
        )
        .all()
    )

    # Últimos 20 eventos para a tabela
    eventos = eventos_todos[:20]

    # Quantidade de veículos diferentes
    total_eventos = len(
        {
            evento.id_veiculo
            for evento in eventos_todos
        }
    )

    # Duplicidades somente desta concessionária
    total_duplicidades = sum(
        1
        for evento in eventos_todos
        if evento.anomalia == "duplicidade"
    )

    # Valor gerado somente por passagens normais
    total_gerado = sum(
        evento.valor
        for evento in eventos_todos
        if evento.anomalia is None
    )

    # Últimas duplicidades desta concessionária
    duplicidades_recentes = [
        evento
        for evento in eventos_todos
        if evento.anomalia == "duplicidade"
    ][:5]

    # ======================================
    # ÚLTIMA PASSAGEM NORMAL
    # ======================================

    ultimo_evento_ok = next(

        (
            evento

            for evento
            in eventos

            if evento.anomalia
            is None
        ),

        None

    )


    ultimo_evento = (

        ultimo_evento_ok

        if ultimo_evento_ok

        else (
            eventos[0]
            if eventos
            else None
        )

    )


    # ======================================
    # MONITORAMENTO
    # ======================================

    status_operacao = (
        "Recebendo dados normalmente"
    )


    segundos_sem_evento = 0


    nivel_atualizacao = "ok"


    mensagem_atualizacao = (
        "✅ Última atualização "
        "há 0 segundo(s)"
    )


    if eventos:

        try:

            horario_ultimo_evento = (
                datetime.fromisoformat(
                    eventos[
                        0
                    ].timestamp_evento
                )
            )


            agora = (
                datetime.now()
            )


            segundos_sem_evento = int(

                (
                    agora
                    - horario_ultimo_evento
                )
                .total_seconds()

            )


            tempo_formatado = (
                formatar_tempo(
                    segundos_sem_evento
                )
            )


            if (
                segundos_sem_evento
                <= 30
            ):

                nivel_atualizacao = (
                    "ok"
                )


                mensagem_atualizacao = (

                    "✅ Última atualização há "
                    f"{tempo_formatado}"

                )


                status_operacao = (
                    "Recebendo dados normalmente"
                )


            elif (
                segundos_sem_evento
                <= TEMPO_SEM_DADOS_ALERTA
            ):

                nivel_atualizacao = (
                    "atencao"
                )


                mensagem_atualizacao = (

                    "⚠️ Atenção: "
                    "última atualização há "
                    f"{tempo_formatado}"

                )


                status_operacao = (
                    "Atenção: atraso na atualização"
                )


            else:

                nivel_atualizacao = (
                    "alerta"
                )


                mensagem_atualizacao = (

                    "🚨 Alerta: "
                    "última atualização há "
                    f"{tempo_formatado}"

                )


                status_operacao = (
                    "Alerta: sem dados recentes"
                )


        except ValueError:

            nivel_atualizacao = (
                "alerta"
            )


            mensagem_atualizacao = (
                "🚨 Alerta: horário inválido "
                "no último evento"
            )


            status_operacao = (
                "Alerta: horário inválido "
                "no último evento"
            )


    else:

        nivel_atualizacao = (
            "alerta"
        )


        mensagem_atualizacao = (
            "🚨 Alerta: nenhum evento recebido"
        )


        status_operacao = (
            "Alerta: nenhum evento recebido"
        )


    # ======================================
    # RETORNO DASHBOARD
    # ======================================

    return {

        "total_veiculos":
            total_eventos,


        "total_gerado":
            total_gerado,


        "valor_por_passagem":
            VALOR_PASSAGEM,


        "refresh_segundos":
            REFRESH_SEGUNDOS,


        "ultima_passagem": {

            "id_veiculo": (

                ultimo_evento.id_veiculo

                if ultimo_evento

                else "-"

            ),


            "faixa": (

                ultimo_evento.faixa

                if ultimo_evento

                else "-"

            ),


            "timestamp_evento": (

                ultimo_evento.timestamp_evento

                if ultimo_evento

                else "-"

            ),


            "valor": (

                ultimo_evento.valor

                if ultimo_evento

                else VALOR_PASSAGEM

            ),


            "anomalia": (

                ultimo_evento.anomalia

                if ultimo_evento

                else None

            )

        },


        "eventos": [

            {

                "id_veiculo":
                    evento.id_veiculo,

                "faixa":
                    evento.faixa,

                "timestamp_evento":
                    evento.timestamp_evento,

                "valor":
                    evento.valor,

                "anomalia":
                    evento.anomalia

            }

            for evento
            in eventos

        ],


        "total_duplicidades":
            total_duplicidades,


        "duplicidades_recentes": [

            {

                "id_veiculo":
                    evento.id_veiculo,

                "timestamp_evento":
                    evento.timestamp_evento

            }

            for evento
            in duplicidades_recentes

        ],


        "status_operacao":
            status_operacao,


        "segundos_sem_evento":
            segundos_sem_evento,


        "nivel_atualizacao":
            nivel_atualizacao,


        "mensagem_atualizacao":
            mensagem_atualizacao

    }


# ==========================================
# EXPORTAÇÃO CSV
# ==========================================

@app.get(
    "/exportar-csv"
)
def exportar_csv(
    request: Request,
    anomalia: str = "todos",
    db: Session = Depends(get_db)
):

    # ======================================
    # PROTEÇÃO
    # ======================================

    if not request.session.get(
        "admin_logado"
    ):
        raise HTTPException(
            status_code=401,
            detail="Acesso não autorizado."
        )


    # ======================================
    # FAIXAS DA CONCESSIONÁRIA
    # ======================================

    faixas_permitidas = (
        request.session.get(
            "faixas_permitidas",
            []
        )
    )


    eventos = (
        db.query(
            models.EventoPassagem
        )
        .filter(
            models.EventoPassagem.faixa.in_(
                faixas_permitidas
            )
        )
        .order_by(
            models.EventoPassagem.id.desc()
        )
        .all()
    )


    # ======================================
    # FILTROS
    # ======================================

    if anomalia == "duplicidade":

        eventos = [
            evento
            for evento in eventos
            if evento.anomalia
            == "duplicidade"
        ]


    elif anomalia == "ok":

        eventos = [
            evento
            for evento in eventos
            if evento.anomalia
            != "duplicidade"
        ]


    # ======================================
    # CSV
    # ======================================

    output = io.StringIO()

    writer = csv.writer(
        output
    )


    writer.writerow(
        [
            "Placa do Veículo",
            "Faixa",
            "Data/Hora",
            "Valor",
            "Status"
        ]
    )


    for evento in eventos:

        status = (
            "Duplicidade"
            if evento.anomalia
            == "duplicidade"
            else "OK"
        )

        writer.writerow(
            [
                evento.id_veiculo,
                evento.faixa,
                evento.timestamp_evento,
                evento.valor,
                status
            ]
        )


    output.seek(0)


    concessionaria_id = (
        request.session.get(
            "concessionaria_id",
            "admin"
        )
    )


    nome_arquivo = (
        "relatorio_freeflow_"
        f"concessionaria_{concessionaria_id}_"
        f"{anomalia}.csv"
    )


    return StreamingResponse(
        iter(
            [
                output.getvalue()
            ]
        ),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                (
                    "attachment; "
                    f"filename={nome_arquivo}"
                )
        }
    )


# ==========================================
# TESTE DO MODELO DE IA
# ==========================================

@app.get(
    "/ia/teste"
)
def testar_ia_api():

    # Usa o modelo que já está
    # carregado em memória pelo anomaly.py
    modelo = (
        anomaly.MODELO_IA
    )


    evento_normal = np.array(
        [
            [
                1,
                120,
                14
            ]
        ]
    )


    evento_atipico = np.array(
        [
            [
                9,
                10000,
                100
            ]
        ]
    )


    resultado_normal = (
        modelo.predict(
            evento_normal
        )[0]
    )


    resultado_atipico = (
        modelo.predict(
            evento_atipico
        )[0]
    )


    return {

        "modelo":
            "Isolation Forest",


        "status":
            "carregado",


        "teste_normal": (

            "NORMAL"

            if resultado_normal
            == 1

            else "ANOMALIA"

        ),


        "teste_atipico": (

            "NORMAL"

            if resultado_atipico
            == 1

            else "ANOMALIA"

        )

    }