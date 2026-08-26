from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.database import engine
from app import models


NOME = "Cliente FreeFlow"
CPF = "12345678900"


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


db = SessionLocal()


try:

    print("")
    print("==============================")
    print("SINCRONIZANDO COBRANÇAS")
    print("==============================")


    # ======================================
    # CLIENTE DEMONSTRATIVO
    # ======================================

    proprietario = (
        db.query(models.Proprietario)
        .filter(
            models.Proprietario.cpf == CPF
        )
        .first()
    )


    if not proprietario:

        proprietario = models.Proprietario(
            nome=NOME,
            cpf=CPF
        )

        db.add(proprietario)
        db.commit()
        db.refresh(proprietario)

    else:

        proprietario.nome = NOME

        db.commit()
        db.refresh(proprietario)


    # ======================================
    # EVENTOS NORMAIS
    # ======================================

    eventos = (
        db.query(models.EventoPassagem)
        .filter(
            models.EventoPassagem.processado == 1,
            models.EventoPassagem.anomalia.is_(None)
        )
        .order_by(
            models.EventoPassagem.id.asc()
        )
        .all()
    )


    criadas = 0


    for evento in eventos:

        uid = (
            evento.id_veiculo
            .strip()
            .upper()
        )


        veiculo = (
            db.query(models.Veiculo)
            .filter(
                models.Veiculo.uid_rfid == uid
            )
            .first()
        )


        if not veiculo:

            veiculo = models.Veiculo(
                placa=uid,
                uid_rfid=uid,
                proprietario_id=proprietario.id
            )

            db.add(veiculo)
            db.commit()
            db.refresh(veiculo)

        else:

            # Placa = UID no protótipo
            veiculo.placa = uid

            veiculo.proprietario_id = (
                proprietario.id
            )

            db.commit()
            db.refresh(veiculo)


        cobranca = (
            db.query(models.Cobranca)
            .filter(
                models.Cobranca.evento_id
                == evento.id
            )
            .first()
        )


        if not cobranca:

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

            db.add(cobranca)

            criadas += 1


    db.commit()


    print("")
    print(f"Novas cobranças criadas: {criadas}")
    print("")
    print("Cliente: Cliente FreeFlow")
    print("CPF: 12345678900")
    print("")
    print("Use como placa o UID mostrado no dashboard.")
    print("==============================")


finally:

    db.close()