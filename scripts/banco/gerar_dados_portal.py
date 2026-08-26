from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.database import engine
from app import models


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

db = SessionLocal()


try:

    print("")
    print("==============================")
    print("GERANDO DADOS PARA O PORTAL")
    print("==============================")

    # ==========================================
    # PROPRIETÁRIO
    # ==========================================

    cpf = "12345678900"

    proprietario = (
        db.query(models.Proprietario)
        .filter(models.Proprietario.cpf == cpf)
        .first()
    )

    if not proprietario:

        proprietario = models.Proprietario(
            nome="João da Silva",
            cpf=cpf
        )

        db.add(proprietario)
        db.commit()
        db.refresh(proprietario)

        print("Proprietário criado.")

    else:

        print("Proprietário já existente.")


    # ==========================================
    # VEÍCULO
    # ==========================================

    placa = "ABC1D23"

    veiculo = (
        db.query(models.Veiculo)
        .filter(models.Veiculo.placa == placa)
        .first()
    )

    if not veiculo:

        veiculo = models.Veiculo(
            placa=placa,
            uid_rfid=None,
            proprietario_id=proprietario.id
        )

        db.add(veiculo)
        db.commit()
        db.refresh(veiculo)

        print("Veículo criado.")

    else:

        print("Veículo já existente.")


    # ==========================================
    # VERIFICA SE JÁ CRIOU COBRANÇAS DE TESTE
    # ==========================================

    cobrancas_existentes = (
        db.query(models.Cobranca)
        .filter(
            models.Cobranca.veiculo_id == veiculo.id
        )
        .count()
    )

    if cobrancas_existentes == 0:

        agora = datetime.now()

        dados = [
            {
                "data": agora - timedelta(days=2),
                "faixa": 1,
                "status": "pendente"
            },
            {
                "data": agora - timedelta(days=1),
                "faixa": 2,
                "status": "pendente"
            },
            {
                "data": agora - timedelta(hours=3),
                "faixa": 1,
                "status": "pago"
            }
        ]

        for item in dados:

            evento = models.EventoPassagem(
                id_veiculo=placa,
                faixa=item["faixa"],
                timestamp_evento=item["data"].isoformat(
                    timespec="seconds"
                ),
                sensor_id=f"rfid_faixa_{item['faixa']}",
                origem="teste_portal",
                valor=5.0,
                processado=1,
                anomalia=None
            )

            db.add(evento)
            db.commit()
            db.refresh(evento)


            cobranca = models.Cobranca(
                evento_id=evento.id,
                veiculo_id=veiculo.id,
                valor=5.0,
                status=item["status"],
                timestamp_criacao=datetime.now().isoformat(
                    timespec="seconds"
                )
            )

            db.add(cobranca)

        db.commit()

        print("3 cobranças criadas.")

    else:

        print(
            "Este veículo já possui cobranças."
        )


    print("")
    print("==============================")
    print("DADOS PRONTOS")
    print("==============================")
    print("Nome: João da Silva")
    print("CPF: 12345678900")
    print("Placa: ABC1D23")
    print("==============================")


finally:

    db.close()
    