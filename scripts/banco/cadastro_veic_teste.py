from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.database import engine
from app import models


# ==========================================
# DADOS DO TESTE
# ==========================================

NOME = "Cliente Teste"
CPF = "12345678900"

PLACA = "ABC1D23"

UID_RFID = "805FF758"


# ==========================================
# BANCO
# ==========================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

db = SessionLocal()


try:

    print("")
    print("==============================")
    print("CADASTRO DO VEÍCULO")
    print("==============================")

    # ======================================
    # PROPRIETÁRIO
    # ======================================

    proprietario = (
        db.query(models.Proprietario)
        .filter(
            models.Proprietario.cpf
            == CPF
        )
        .first()
    )


    if not proprietario:

        proprietario = models.Proprietario(
            nome=NOME,
            cpf=CPF
        )

        db.add(
            proprietario
        )

        db.commit()

        db.refresh(
            proprietario
        )

        print(
            "Proprietário criado."
        )

    else:

        print(
            "Proprietário já existe."
        )


    # ======================================
    # VERIFICA UID
    # ======================================

    veiculo_com_uid = (
        db.query(models.Veiculo)
        .filter(
            models.Veiculo.uid_rfid
            == UID_RFID
        )
        .first()
    )


    # ======================================
    # VEÍCULO
    # ======================================

    veiculo = (
        db.query(models.Veiculo)
        .filter(
            models.Veiculo.placa
            == PLACA
        )
        .first()
    )


    if not veiculo:

        if veiculo_com_uid:

            raise Exception(
                "Este UID já pertence a outro veículo."
            )


        veiculo = models.Veiculo(
            placa=PLACA,
            uid_rfid=UID_RFID,
            proprietario_id=proprietario.id
        )

        db.add(
            veiculo
        )

        db.commit()

        db.refresh(
            veiculo
        )

        print(
            "Veículo criado."
        )

    else:

        veiculo.proprietario_id = (
            proprietario.id
        )

        veiculo.uid_rfid = (
            UID_RFID
        )

        db.commit()

        db.refresh(
            veiculo
        )

        print(
            "Veículo atualizado."
        )


    print(
        f"TAG {UID_RFID} vinculada à placa {PLACA}."
    )


    # ======================================
    # CRIA COBRANÇAS DOS EVENTOS NORMAIS
    # JÁ EXISTENTES
    # ======================================

    eventos_normais = (
        db.query(
            models.EventoPassagem
        )
        .filter(
            models.EventoPassagem.id_veiculo
            == UID_RFID,
            models.EventoPassagem.processado
            == 1,
            models.EventoPassagem.anomalia
            .is_(None)
        )
        .all()
    )


    novas_cobrancas = 0


    for evento in eventos_normais:

        existente = (
            db.query(models.Cobranca)
            .filter(
                models.Cobranca.evento_id
                == evento.id
            )
            .first()
        )


        if existente:
            continue


        cobranca = models.Cobranca(
            evento_id=evento.id,
            veiculo_id=veiculo.id,
            valor=evento.valor,
            status="pendente",
            timestamp_criacao=(
                datetime.now()
                .isoformat(
                    timespec="seconds"
                )
            )
        )


        db.add(
            cobranca
        )

        novas_cobrancas += 1


    db.commit()


    print("")
    print("==============================")
    print("CADASTRO CONCLUÍDO")
    print("==============================")
    print(
        f"Nome: {NOME}"
    )
    print(
        f"CPF: {CPF}"
    )
    print(
        f"Placa: {PLACA}"
    )
    print(
        f"UID RFID: {UID_RFID}"
    )
    print(
        f"Novas cobranças: {novas_cobrancas}"
    )
    print("==============================")


finally:

    db.close()