# ==========================================
# FREEFLOW - API PRINCIPAL
# ==========================================

from fastapi import FastAPI, Depends, Header, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

import barcode
import csv
import io
import qrcode
import secrets

from datetime import datetime
from urllib.parse import urlencode
from barcode.writer import SVGWriter
from starlette.middleware.sessions import SessionMiddleware
from app.database import get_db
from app import schemas, crud, anomaly, models

from app.config import (
    VALOR_PASSAGEM,
    TEMPO_DUPLICIDADE,
    TEMPO_SEM_DADOS_ALERTA,
    REFRESH_SEGUNDOS,
    SESSION_SECRET,
    ESP32_API_KEY,
    COOKIE_SECURE,
    BASE_DIR,
    CONCESSIONARIAS_ADMIN,
    valor_passagem_por_faixa,
)


# ==========================================
# APLICAÇÃO FASTAPI
# ==========================================

app = FastAPI(
    title="FreeFlow"
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "app" / "static")),
    name="static",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=COOKIE_SECURE,
)


def exigir_admin(request: Request) -> None:
    if not request.session.get("admin_logado"):
        raise HTTPException(
            status_code=401,
            detail="Acesso não autorizado.",
        )


def validar_chave_esp32(
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
    ),
) -> None:
    if not ESP32_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Integração com ESP32 não configurada.",
        )

    if not x_api_key or not secrets.compare_digest(
        x_api_key,
        ESP32_API_KEY,
    ):
        raise HTTPException(
            status_code=401,
            detail="Chave do dispositivo inválida.",
        )

# ==========================================
# TEMPLATES HTML
# ==========================================

templates = Jinja2Templates(
    directory=str(BASE_DIR / "app" / "templates")
)

PAGAMENTO_MAX_AGE = 60 * 60 * 24
pagamento_serializer = URLSafeTimedSerializer(
    SESSION_SECRET,
    salt="freeflow-pagamento-simulado",
)


def configuracao_concessionaria(
    concessionaria_id: str = "",
    usuario: str = "",
    faixas: list[int] | None = None,
) -> dict:
    concessionaria_id = str(concessionaria_id or "").casefold()
    usuario = str(usuario or "").casefold()
    faixas = {int(faixa) for faixa in (faixas or [])}

    aliases = {
        "a": "A",
        "1": "A",
        "concessionaria_a": "A",
        "b": "B",
        "2": "B",
        "concessionaria_b": "B",
    }
    id_canonico = aliases.get(usuario) or aliases.get(concessionaria_id)
    if id_canonico:
        return next(
            (
                dados
                for dados in CONCESSIONARIAS_ADMIN.values()
                if dados["id"] == id_canonico
            ),
            {},
        )

    configuracao = next(
        (
            dados
            for usuario_configurado, dados in CONCESSIONARIAS_ADMIN.items()
            if (
                str(dados["id"]).casefold() == concessionaria_id
                or str(usuario_configurado).casefold() == concessionaria_id
                or str(usuario_configurado).casefold() == usuario
            )
        ),
        None,
    )
    if configuracao:
        return configuracao

    return next(
        (
            dados
            for dados in CONCESSIONARIAS_ADMIN.values()
            if faixas.intersection(dados["faixas"])
        ),
        {},
    )


def identidade_concessionaria(request: Request) -> dict:
    concessionaria_id = request.session.get("concessionaria_id", "")
    configuracao = configuracao_concessionaria(
        concessionaria_id=concessionaria_id,
        faixas=request.session.get("faixas_permitidas", []),
    )
    return {
        "concessionaria_id": concessionaria_id,
        "concessionaria_nome": configuracao.get(
            "nome",
            request.session.get("concessionaria_nome", "Concessionária"),
        ),
        "concessionaria_sigla": configuracao.get("sigla", "FF"),
        "concessionaria_logo_url": configuracao.get("logo_url", ""),
    }


def concessionaria_por_faixa(faixa: int) -> dict:
    return next(
        (
            dados
            for dados in CONCESSIONARIAS_ADMIN.values()
            if faixa in dados["faixas"]
        ),
        {
            "id": "",
            "nome": "Concessionária",
            "sigla": "FF",
            "logo_url": "",
        },
    )


def carregar_token_pagamento(token: str) -> dict:
    try:
        dados = pagamento_serializer.loads(
            token,
            max_age=PAGAMENTO_MAX_AGE,
        )
    except SignatureExpired as exc:
        raise HTTPException(
            status_code=410,
            detail="Este pagamento expirou. Gere uma nova cobrança.",
        ) from exc
    except BadSignature as exc:
        raise HTTPException(
            status_code=400,
            detail="Pagamento inválido.",
        ) from exc

    if dados.get("v") != 1 or not dados.get("cobrancas"):
        raise HTTPException(status_code=400, detail="Pagamento inválido.")

    return dados


def validar_data_filtro(valor: str | None) -> str | None:
    if not valor:
        return None

    try:
        return datetime.strptime(valor, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Data inválida. Use o formato AAAA-MM-DD.",
        ) from exc


def url_sucesso_pagamento(token: str) -> str:
    return "/pagamento/confirmado?" + urlencode({"token": token})
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
    segundos = max(0, int(segundos))
    dias, restante = divmod(segundos, 86400)
    horas, restante = divmod(restante, 3600)
    minutos, segundos = divmod(restante, 60)
    partes = []

    if dias:
        partes.append(f"{dias} dia" + ("s" if dias != 1 else ""))
    if horas:
        partes.append(f"{horas}h")
    if minutos:
        partes.append(f"{minutos}min")
    if segundos or not partes:
        partes.append(f"{segundos}s")

    if len(partes) == 1:
        return partes[0]

    return ", ".join(partes[:-1]) + " e " + partes[-1]


# ==========================================
# ROTA PRINCIPAL
# ==========================================

@app.get("/", include_in_schema=False)
def raiz(request: Request):
    if request.url.hostname == "gestao-free-flow.vercel.app":
        return RedirectResponse(url="/admin/login", status_code=307)

    return RedirectResponse(url="/portal", status_code=307)


# ==========================================
# EVENTOS RFID
# ==========================================

@app.post(
    "/evento",
    response_model=schemas.EventoResponse
)
def criar_evento(
    evento: schemas.EventoCreate,
    _dispositivo: None = Depends(validar_chave_esp32),
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
    # 3. SOMENTE PASSAGEM NORMAL PODE GERAR COBRANÇA
    # ======================================

    if novo_evento.anomalia is None:

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
    _admin: None = Depends(exigir_admin),
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
    _admin: None = Depends(exigir_admin),
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
        context=identidade_concessionaria(request),
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
    request: Request,
    db: Session = Depends(get_db)
):
    form = await request.form()

    usuario = form.get("usuario")
    senha = form.get("senha")

    credencial = crud.autenticar_usuario_concessionaria(
        db,
        usuario,
        senha
    )

    if credencial:
        request.session["admin_logado"] = True

        faixas_permitidas = crud.obter_faixas_usuario_concessionaria(
            credencial
        )
        configuracao = configuracao_concessionaria(
            concessionaria_id=credencial.concessionaria_id,
            usuario=usuario,
            faixas=faixas_permitidas,
        )

        request.session[
            "concessionaria_id"
        ] = configuracao.get("id", credencial.concessionaria_id)

        request.session[
            "concessionaria_nome"
        ] = configuracao.get("nome", credencial.concessionaria_nome)

        request.session[
            "faixas_permitidas"
        ] = configuracao.get("faixas", faixas_permitidas)

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


def localizar_cobrancas_pagamento(
    db: Session,
    cpf: str,
    placa: str,
    cobranca_ids: list[int],
):
    cpf_normalizado = (
        cpf.replace(".", "").replace("-", "").strip()
    )
    placa_normalizada = placa.strip().upper()
    ids = sorted({int(item) for item in cobranca_ids if int(item) > 0})

    if not ids or len(ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="Selecione entre 1 e 100 débitos.",
        )

    proprietario = crud.buscar_proprietario_por_cpf(db, cpf_normalizado)
    veiculo = crud.buscar_veiculo_por_placa(db, placa_normalizada)

    if (
        not proprietario
        or not veiculo
        or veiculo.proprietario_id != proprietario.id
    ):
        raise HTTPException(
            status_code=403,
            detail="CPF e veículo não correspondem ao mesmo cliente.",
        )

    cobrancas = (
        db.query(models.Cobranca)
        .join(
            models.EventoPassagem,
            models.Cobranca.evento_id == models.EventoPassagem.id,
        )
        .filter(
            models.Cobranca.id.in_(ids),
            models.Cobranca.veiculo_id == veiculo.id,
            models.Cobranca.status == "pendente",
            models.EventoPassagem.anomalia.is_(None),
        )
        .order_by(models.Cobranca.id.asc())
        .all()
    )

    if len(cobrancas) != len(ids):
        raise HTTPException(
            status_code=409,
            detail="Um ou mais débitos já foram pagos ou não pertencem ao veículo.",
        )

    return veiculo, cobrancas


@app.post("/portal/pagamento/iniciar")
def iniciar_pagamento(
    pagamento: schemas.PortalPagamentoIniciar,
    request: Request,
    db: Session = Depends(get_db),
):
    metodo = pagamento.metodo.strip().lower()
    if metodo not in {"pix", "boleto"}:
        raise HTTPException(status_code=400, detail="Forma de pagamento inválida.")

    veiculo, cobrancas = localizar_cobrancas_pagamento(
        db,
        pagamento.cpf,
        pagamento.placa,
        pagamento.cobrancas,
    )
    token = pagamento_serializer.dumps(
        {
            "v": 1,
            "placa": veiculo.placa,
            "veiculo_id": veiculo.id,
            "cobrancas": [cobranca.id for cobranca in cobrancas],
            "metodo": metodo,
        }
    )
    query = urlencode({"token": token})
    confirmacao_url = f"{request.url_for('confirmar_pagamento_page')}?{query}"

    return {
        "token": token,
        "confirmacao_url": confirmacao_url,
        "qrcode_url": f"{request.url_for('qrcode_pagamento')}?{query}",
        "codigo_barras_url": f"{request.url_for('codigo_barras_pagamento')}?{query}",
    }


@app.get("/pagamento/confirmar", response_class=HTMLResponse)
def confirmar_pagamento_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):
    dados = carregar_token_pagamento(token)
    cobrancas = (
        db.query(models.Cobranca)
        .join(
            models.EventoPassagem,
            models.Cobranca.evento_id == models.EventoPassagem.id,
        )
        .filter(
            models.Cobranca.id.in_(dados["cobrancas"]),
            models.Cobranca.veiculo_id == dados["veiculo_id"],
            models.EventoPassagem.anomalia.is_(None),
        )
        .order_by(models.Cobranca.id.asc())
        .all()
    )
    if len(cobrancas) != len(set(dados["cobrancas"])):
        raise HTTPException(status_code=404, detail="Débitos não encontrados.")

    veiculo = cobrancas[0].veiculo

    return templates.TemplateResponse(
        request=request,
        name="confirmar_pagamento.html",
        context={
            "token": token,
            "placa": dados["placa"],
            "metodo": dados["metodo"],
            "cobrancas": cobrancas,
            "total": sum(float(cobranca.valor or 0) for cobranca in cobrancas),
            "ja_pago": all(cobranca.status == "pago" for cobranca in cobrancas),
            "success_url": url_sucesso_pagamento(token),
            "redirect_url": (
                "/cobrancas?"
                + urlencode(
                    {
                        "cpf": veiculo.proprietario.cpf,
                        "placa": dados["placa"],
                    }
                )
            ),
        },
    )


@app.post("/portal/pagamento/confirmar")
def confirmar_pagamento(
    pagamento: schemas.PortalPagamentoConfirmar,
    db: Session = Depends(get_db),
):
    dados = carregar_token_pagamento(pagamento.token)
    ids = sorted(set(int(item) for item in dados["cobrancas"]))
    cobrancas = (
        db.query(models.Cobranca)
        .join(
            models.EventoPassagem,
            models.Cobranca.evento_id == models.EventoPassagem.id,
        )
        .filter(
            models.Cobranca.id.in_(ids),
            models.Cobranca.veiculo_id == dados["veiculo_id"],
            models.EventoPassagem.anomalia.is_(None),
        )
        .with_for_update()
        .all()
    )

    if len(cobrancas) != len(ids):
        raise HTTPException(status_code=404, detail="Débitos não encontrados.")

    veiculo = cobrancas[0].veiculo

    atualizadas = 0
    for cobranca in cobrancas:
        if cobranca.status == "pendente":
            cobranca.status = "pago"
            atualizadas += 1

    db.commit()
    return {
        "mensagem": "Pagamento confirmado com sucesso.",
        "atualizadas": atualizadas,
        "success_url": url_sucesso_pagamento(pagamento.token),
    }


@app.get("/portal/pagamento/status")
def status_pagamento(
    token: str,
    response: Response,
    db: Session = Depends(get_db),
):
    dados = carregar_token_pagamento(token)
    ids = sorted(set(int(item) for item in dados["cobrancas"]))
    cobrancas = (
        db.query(models.Cobranca)
        .join(
            models.EventoPassagem,
            models.Cobranca.evento_id == models.EventoPassagem.id,
        )
        .filter(
            models.Cobranca.id.in_(ids),
            models.Cobranca.veiculo_id == dados["veiculo_id"],
            models.EventoPassagem.anomalia.is_(None),
        )
        .all()
    )

    if len(cobrancas) != len(ids):
        raise HTTPException(status_code=404, detail="Débitos não encontrados.")

    confirmado = all(cobranca.status == "pago" for cobranca in cobrancas)
    response.headers["Cache-Control"] = "no-store"
    return {
        "confirmado": confirmado,
        "success_url": url_sucesso_pagamento(token),
    }


@app.get(
    "/pagamento/confirmado",
    response_class=HTMLResponse,
    name="pagamento_confirmado_page",
)
def pagamento_confirmado_page(
    request: Request,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    retorno_debitos_url = None
    quantidade_outros_debitos = 0

    if token:
        dados = carregar_token_pagamento(token)
        veiculo = (
            db.query(models.Veiculo)
            .filter(models.Veiculo.id == dados["veiculo_id"])
            .first()
        )

        if veiculo and veiculo.proprietario:
            quantidade_outros_debitos = (
                db.query(models.Cobranca)
                .join(
                    models.EventoPassagem,
                    models.Cobranca.evento_id == models.EventoPassagem.id,
                )
                .filter(
                    models.Cobranca.veiculo_id == veiculo.id,
                    models.Cobranca.status == "pendente",
                    models.EventoPassagem.anomalia.is_(None),
                )
                .count()
            )

            if quantidade_outros_debitos:
                retorno_debitos_url = "/cobrancas?" + urlencode(
                    {
                        "cpf": veiculo.proprietario.cpf,
                        "placa": veiculo.placa,
                    }
                )

    return templates.TemplateResponse(
        request=request,
        name="pagamento_confirmado.html",
        context={
            "retorno_debitos_url": retorno_debitos_url,
            "quantidade_outros_debitos": quantidade_outros_debitos,
        },
    )


@app.get("/pagamento/qrcode", name="qrcode_pagamento")
def qrcode_pagamento(
    request: Request,
    token: str,
):
    carregar_token_pagamento(token)
    confirmacao_url = (
        f"{request.url_for('confirmar_pagamento_page')}?"
        + urlencode({"token": token})
    )
    imagem = qrcode.make(confirmacao_url)
    arquivo = io.BytesIO()
    imagem.save(arquivo, format="PNG")
    arquivo.seek(0)
    return StreamingResponse(
        arquivo,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/pagamento/codigo-barras", name="codigo_barras_pagamento")
def codigo_barras_pagamento(
    request: Request,
    token: str,
):
    carregar_token_pagamento(token)
    confirmacao_url = (
        f"{request.url_for('confirmar_pagamento_page')}?"
        + urlencode({"token": token})
    )
    arquivo = io.BytesIO()
    codigo = barcode.get("code128", confirmacao_url, writer=SVGWriter())
    codigo.write(
        arquivo,
        options={
            "write_text": False,
            "module_width": 0.22,
            "module_height": 18,
            "quiet_zone": 3,
        },
    )
    return Response(
        content=arquivo.getvalue(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
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
            detail=(
                "CPF ou veículo informados estão incorretos. "
                "Confira os dados e tente novamente."
            )
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
            detail=(
                "CPF ou veículo informados estão incorretos. "
                "Confira os dados e tente novamente."
            )
        )


    # Verifica se pertence ao CPF
    if (
        veiculo.proprietario_id
        != proprietario.id
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "CPF ou veículo informados estão incorretos. "
                "Confira os dados e tente novamente."
            )
        )


    # ======================================
    # COBRANÇAS DO VEÍCULO
    # ======================================

    cobrancas = (
        db.query(models.Cobranca)
        .join(
            models.EventoPassagem,
            models.Cobranca.evento_id == models.EventoPassagem.id,
        )
        .filter(
            models.Cobranca.veiculo_id == veiculo.id,
            models.EventoPassagem.anomalia.is_(None),
        )
        .order_by(models.Cobranca.id.desc())
        .all()
    )


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


        "possui_debitos":
            total_pendentes > 0,


        "total_pagas":
            total_pagas,


       "cobrancas": [
    {
        "id": cobranca.id,

        "timestamp_evento": (
            cobranca.evento.timestamp_evento
            if cobranca.evento
            else "-"
        ),

        "faixa": (
            cobranca.evento.faixa
            if cobranca.evento
            else "-"
        ),

        "concessionaria": concessionaria_por_faixa(
            cobranca.evento.faixa if cobranca.evento else 0
        )["nome"],

        "concessionaria_logo": concessionaria_por_faixa(
            cobranca.evento.faixa if cobranca.evento else 0
        )["logo_url"],

        "valor": cobranca.valor,

        "status": cobranca.status
    }

    for cobranca in cobrancas
]}

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

    if cobranca.evento and cobranca.evento.anomalia is not None:
        raise HTTPException(
            status_code=409,
            detail="Uma passagem anômala não pode ser paga.",
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
    data: str | None = None,
    db: Session = Depends(get_db)
):

    # ======================================
    # PROTEÇÃO DA ÁREA ADMIN
    # ======================================

    if not request.session.get(
        "admin_logado"
    ):

        return RedirectResponse(
            url="/admin/login",
            status_code=303
        )


    # ======================================
    # DADOS DA CONCESSIONÁRIA LOGADA
    # ======================================

    identidade = identidade_concessionaria(request)
    concessionaria_nome = identidade["concessionaria_nome"]


    faixas_permitidas = (
        request.session.get(
            "faixas_permitidas",
            []
        )
    )

    data_filtrada = validar_data_filtro(data)


    # ======================================
    # COBRANÇAS SOMENTE DAS FAIXAS
    # DA CONCESSIONÁRIA LOGADA
    # ======================================

    consulta_cobrancas = (

        db.query(
            models.Cobranca
        )

        .join(
            models.EventoPassagem,
            models.Cobranca.evento_id
            ==
            models.EventoPassagem.id
        )

        .filter(
            models.EventoPassagem.faixa.in_(
                faixas_permitidas
            ),
            models.EventoPassagem.anomalia.is_(None),
        )

    )

    if data_filtrada:
        consulta_cobrancas = consulta_cobrancas.filter(
            models.EventoPassagem.timestamp_evento.like(
                f"{data_filtrada}%"
            )
        )

    cobrancas = (
        consulta_cobrancas
        .order_by(models.Cobranca.id.desc())
        .all()
    )


    # ======================================
    # AGRUPA POR VEÍCULO
    # ======================================

    veiculos_resumo = {}


    for cobranca in cobrancas:

        veiculo = cobranca.veiculo

        evento = cobranca.evento


        if not veiculo:
            continue


        proprietario = (
            veiculo.proprietario
        )


        veiculo_id = (
            veiculo.id
        )


        # ==================================
        # CRIA O VEÍCULO NO RESUMO
        # ==================================

        if (
            veiculo_id
            not in veiculos_resumo
        ):


            # CPF mascarado

            cpf_original = (
                proprietario.cpf
                if proprietario
                else ""
            )


            if (
                cpf_original
                and len(cpf_original) >= 2
            ):

                cpf_mascarado = (
                    "***.***.***-"
                    + cpf_original[-2:]
                )

            else:

                cpf_mascarado = "***"


            veiculos_resumo[
                veiculo_id
            ] = {

                "placa":
                    veiculo.placa,

                "nome_proprietario":
                    (
                        proprietario.nome
                        if proprietario
                        else "Não informado"
                    ),

                "cpf":
                    cpf_mascarado,

                "uid_rfid":
                    (
                        veiculo.uid_rfid
                        if veiculo.uid_rfid
                        else "-"
                    ),

                "quantidade_pendentes":
                    0,

                "valor_pendente":
                    0.0,

                "quantidade_pagas":
                    0,

                "valor_pago":
                    0.0,

                "total_gerado":
                    0.0,

                "historico":
                    []

            }


        resumo = (
            veiculos_resumo[
                veiculo_id
            ]
        )


        valor = float(
            cobranca.valor
            or 0
        )


        # ==================================
        # TOTAL GERADO
        # ==================================

        if cobranca.status in {"pendente", "pago"}:
            resumo[
                "total_gerado"
            ] += valor


        # ==================================
        # PENDENTE / PAGO
        # ==================================

        if (
            cobranca.status
            == "pago"
        ):

            resumo[
                "quantidade_pagas"
            ] += 1


            resumo[
                "valor_pago"
            ] += valor

        else:

            resumo[
                "quantidade_pendentes"
            ] += 1


            resumo[
                "valor_pendente"
            ] += valor


        # ==================================
        # HISTÓRICO
        # ==================================

        resumo[
            "historico"
        ].append(
            {

                "id":
                    cobranca.id,

                "timestamp_evento":
                    (
                        evento.timestamp_evento
                        if evento
                        else "-"
                    ),

                "faixa":
                    (
                        evento.faixa
                        if evento
                        else "-"
                    ),

                "valor":
                    valor,

                "status":
                    cobranca.status

            }
        )


    # ======================================
    # TRANSFORMA EM LISTA
    # ======================================

    resumo = list(
        veiculos_resumo.values()
    )


    # ======================================
    # TOTAIS DA CONCESSIONÁRIA
    # ======================================

    total_veiculos = len(
        resumo
    )


    total_gerado = sum(
        item[
            "total_gerado"
        ]
        for item
        in resumo
    )


    total_pendente = sum(
        item[
            "valor_pendente"
        ]
        for item
        in resumo
    )


    total_recebido = sum(
        item[
            "valor_pago"
        ]
        for item
        in resumo
    )


    # ======================================
    # TEMPLATE
    # ======================================

    return templates.TemplateResponse(

        request=request,

        name="admin_cobrancas.html",

        context={

            "concessionaria_nome":
                concessionaria_nome,

            "concessionaria_id":
                identidade["concessionaria_id"],

            "concessionaria_sigla":
                identidade["concessionaria_sigla"],

            "concessionaria_logo_url":
                identidade["concessionaria_logo_url"],

            "resumo":
                resumo,

            "total_veiculos":
                total_veiculos,

            "total_gerado":
                total_gerado,

            "total_pendente":
                total_pendente,

            "total_recebido":
                total_recebido,

            "data_filtro":
                data_filtrada or ""

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
    data: str | None = None,
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

    data_filtrada = validar_data_filtro(data)

    # Todos os eventos apenas das faixas permitidas
    consulta_eventos = (
        db.query(
            models.EventoPassagem
        )
        .filter(
            models.EventoPassagem.faixa.in_(
                faixas_permitidas
            )
        )
    )

    if data_filtrada:
        consulta_eventos = consulta_eventos.filter(
            models.EventoPassagem.timestamp_evento.like(
                f"{data_filtrada}%"
            )
        )

    eventos_todos = (
        consulta_eventos
        .order_by(
            models.EventoPassagem.id.desc()
        )
        .all()
    )

    # Últimos 20 eventos para a tabela
    eventos = eventos_todos[:20]

    # Quantidade de veículos diferentes
    total_veiculos = len(
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

    total_passagens = len(eventos_todos)

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


            segundos_sem_evento = max(0, int(

                (
                    agora
                    - horario_ultimo_evento
                )
                .total_seconds()

            ))


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
            total_veiculos,

        "total_passagens":
            total_passagens,


        "total_gerado":
            total_gerado,


        "valor_por_passagem":
            (
                valor_passagem_por_faixa(faixas_permitidas[0])
                if faixas_permitidas
                else VALOR_PASSAGEM
            ),

        "valor_a_receber_corrigido":
            total_gerado,


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

        "tempo_sem_evento_formatado":
            formatar_tempo(segundos_sem_evento),


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
    data: str | None = None,
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

    data_filtrada = validar_data_filtro(data)

    consulta_eventos = (
        db.query(
            models.EventoPassagem
        )
        .filter(
            models.EventoPassagem.faixa.in_(
                faixas_permitidas
            )
        )
    )

    if data_filtrada:
        consulta_eventos = consulta_eventos.filter(
            models.EventoPassagem.timestamp_evento.like(
                f"{data_filtrada}%"
            )
        )

    eventos = (
        consulta_eventos
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
            if evento.anomalia is None
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
            "Veículo",
            "Concessionária",
            "Data/Hora",
            "Valor",
            "Status"
        ]
    )


    for evento in eventos:

        status = (
            "OK"
            if evento.anomalia is None
            else evento.anomalia.replace("_", " ").title()
        )

        concessionaria = concessionaria_por_faixa(evento.faixa)["nome"]

        writer.writerow(
            [
                evento.id_veiculo,
                concessionaria,
                evento.timestamp_evento,
                evento.valor,
                status,
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
        f"{data_filtrada or 'todas-as-datas'}_"
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
def testar_ia_api(
    _admin: None = Depends(exigir_admin),
):
    casos = {
        "normal": anomaly.classificar_com_ia(1, 120, 14),
        "duplicidade": anomaly.classificar_com_ia(1, 29, 14),
        "anomalia": anomaly.classificar_com_ia(2, 120, 2),
    }

    return {
        "modelo": "Isolation Forest",
        "status": "carregado",
        "janela_duplicidade_segundos": TEMPO_DUPLICIDADE,
        "regra_janela": f"intervalo < {TEMPO_DUPLICIDADE}",
        "casos": casos,
    }


@app.get("/health")
def healthcheck(
    db: Session = Depends(get_db),
):
    db.execute(text("select 1"))
    return {
        "status": "ok",
        "database": "connected",
    }
