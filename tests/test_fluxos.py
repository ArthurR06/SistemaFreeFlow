import os
import socket
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path

import requests
import uvicorn


TEMP_DIR = tempfile.TemporaryDirectory()
DATABASE_PATH = Path(TEMP_DIR.name) / "freeflow-test.db"
os.environ["APP_ENV"] = "local"
os.environ["DATABASE_URL"] = "sqlite:///" + DATABASE_PATH.as_posix()
os.environ["SESSION_SECRET"] = "segredo-de-teste-com-tamanho-adequado"
os.environ["ESP32_API_KEY"] = "chave-de-teste"
os.environ["VALOR_PASSAGEM_A"] = "5.0"
os.environ["VALOR_PASSAGEM_B"] = "7.5"
os.environ["TEMPO_DUPLICIDADE"] = "30"

from app import models  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import (  # noqa: E402
    app,
    formatar_tempo,
    obter_ou_criar_veiculo_demo,
)
from app.security import gerar_hash_senha  # noqa: E402


class FluxosFreeFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            proprietario = models.Proprietario(
                nome="Cliente Teste",
                cpf="12345678901",
            )
            db.add(proprietario)
            db.flush()
            veiculo = models.Veiculo(
                placa="ABC1D23",
                uid_rfid="ABC1D23",
                proprietario_id=proprietario.id,
            )
            db.add(veiculo)
            db.flush()

            proprietario_sem_debito = models.Proprietario(
                nome="Cliente Sem Débito",
                cpf="98765432100",
            )
            db.add(proprietario_sem_debito)
            db.flush()
            db.add(
                models.Veiculo(
                    placa="SEM0D00",
                    uid_rfid="SEM0D00",
                    proprietario_id=proprietario_sem_debito.id,
                )
            )

            for faixa, valor in ((1, 5.0), (2, 7.5)):
                evento = models.EventoPassagem(
                    id_veiculo=veiculo.placa,
                    faixa=faixa,
                    timestamp_evento=datetime.now().isoformat(timespec="seconds"),
                    valor=valor,
                    processado=1,
                )
                db.add(evento)
                db.flush()
                db.add(
                    models.Cobranca(
                        evento_id=evento.id,
                        veiculo_id=veiculo.id,
                        valor=valor,
                        status="pendente",
                        timestamp_criacao=datetime.now().isoformat(timespec="seconds"),
                    )
                )
            evento_anomalo = models.EventoPassagem(
                id_veiculo=veiculo.placa,
                faixa=1,
                timestamp_evento=datetime.now().isoformat(timespec="seconds"),
                valor=5.0,
                processado=1,
                anomalia="ia_anomalia",
            )
            db.add(evento_anomalo)
            db.flush()
            cobranca_anomala = models.Cobranca(
                evento_id=evento_anomalo.id,
                veiculo_id=veiculo.id,
                valor=5.0,
                status="pendente",
                timestamp_criacao=datetime.now().isoformat(timespec="seconds"),
            )
            db.add(cobranca_anomala)
            db.flush()
            cls.cobranca_anomala_id = cobranca_anomala.id
            db.add(
                models.UsuarioConcessionaria(
                    usuario="conectavia",
                    senha_hash=gerar_hash_senha("senha-teste-conectavia"),
                    concessionaria_id="A",
                    concessionaria_nome="ConectaVia",
                    faixas_permitidas="1",
                    ativo=1,
                    criado_em=datetime.now().isoformat(timespec="seconds"),
                )
            )
            db.add(
                models.UsuarioConcessionaria(
                    usuario="rotalink",
                    senha_hash=gerar_hash_senha("senha-teste-rotalink"),
                    concessionaria_id="B",
                    concessionaria_nome="RotaLink",
                    faixas_permitidas="2",
                    ativo=1,
                    criado_em=datetime.now().isoformat(timespec="seconds"),
                )
            )
            db.commit()

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=cls.port,
                log_level="warning",
            )
        )
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        for _ in range(50):
            try:
                if requests.get(f"{cls.base_url}/health", timeout=1).ok:
                    break
            except requests.RequestException:
                time.sleep(0.1)
        else:
            raise RuntimeError("Servidor de teste não iniciou.")

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=5)
        engine.dispose()
        TEMP_DIR.cleanup()

    def test_duracao_completa(self):
        self.assertEqual(formatar_tempo(159010), "1 dia, 20h, 10min e 10s")

    def test_geracao_proprietarios_demo_segue_ordem_de_chegada(self):
        esperados = [
            ("Arthur Rodrigues", "10000000001"),
            ("Camila Eiko", "10000000002"),
            ("Joice Jardim", "10000000003"),
            ("Leticia Moura", "10000000004"),
            ("Bruno Almeida", "10000000005"),
            ("Fernanda Souza", "10000000006"),
            ("Gabriel Santos", "10000000007"),
            ("Mariana Oliveira", "10000000008"),
            ("Rafael Lima", "10000000009"),
            ("Renata Costa", "10000000010"),
        ]

        with SessionLocal() as db:
            associados = []
            for ordem in range(1, 11):
                veiculo = obter_ou_criar_veiculo_demo(
                    db,
                    f"DEMOSEQ{ordem:02d}",
                )
                proprietario = db.get(
                    models.Proprietario,
                    veiculo.proprietario_id,
                )
                associados.append((proprietario.nome, proprietario.cpf))

            decimo_primeiro = obter_ou_criar_veiculo_demo(
                db,
                "DEMOSEQ11",
            )
            proprietario_extra = db.get(
                models.Proprietario,
                decimo_primeiro.proprietario_id,
            )

        self.assertEqual(associados, esperados)
        self.assertEqual(proprietario_extra.nome, "Cliente Demo 11")
        self.assertEqual(proprietario_extra.cpf, "10000000011")

    def test_ia_classifica_duplicidade_e_bloqueia_cobranca(self):
        with SessionLocal() as db:
            proprietario = models.Proprietario(
                nome="Cliente IA Duplicidade",
                cpf="11111111111",
            )
            db.add(proprietario)
            db.flush()
            db.add(
                models.Veiculo(
                    placa="IA30DUP",
                    uid_rfid="IA30DUP",
                    proprietario_id=proprietario.id,
                )
            )
            db.commit()

        cabecalhos = {"X-API-Key": "chave-de-teste"}
        primeira = requests.post(
            f"{self.base_url}/evento",
            headers=cabecalhos,
            json={
                "id_veiculo": "IA30DUP",
                "faixa": 1,
                "timestamp_evento": "2026-09-23T14:00:00",
                "sensor_id": "sensor-teste-ia",
                "origem": "teste-automatizado",
            },
            timeout=5,
        )
        self.assertEqual(primeira.status_code, 200)
        self.assertIsNone(primeira.json()["anomalia"])

        repeticao = requests.post(
            f"{self.base_url}/evento",
            headers=cabecalhos,
            json={
                "id_veiculo": "IA30DUP",
                "faixa": 1,
                "timestamp_evento": "2026-09-23T14:00:29",
                "sensor_id": "sensor-teste-ia",
                "origem": "teste-automatizado",
            },
            timeout=5,
        )
        self.assertEqual(repeticao.status_code, 200)
        self.assertEqual(repeticao.json()["anomalia"], "duplicidade")

        with SessionLocal() as db:
            cobrancas = (
                db.query(models.Cobranca)
                .join(models.EventoPassagem)
                .filter(models.EventoPassagem.id_veiculo == "IA30DUP")
                .count()
            )
            self.assertEqual(cobrancas, 1)

    def test_ia_bloqueia_anomalia_fora_da_janela_de_duplicidade(self):
        with SessionLocal() as db:
            proprietario = models.Proprietario(
                nome="Cliente IA Anomalia",
                cpf="22222222222",
            )
            db.add(proprietario)
            db.flush()
            db.add(
                models.Veiculo(
                    placa="IAANOM1",
                    uid_rfid="IAANOM1",
                    proprietario_id=proprietario.id,
                )
            )
            db.commit()

        cabecalhos = {"X-API-Key": "chave-de-teste"}
        primeira = requests.post(
            f"{self.base_url}/evento",
            headers=cabecalhos,
            json={
                "id_veiculo": "IAANOM1",
                "faixa": 2,
                "timestamp_evento": "2026-09-23T01:58:00",
                "sensor_id": "sensor-teste-ia",
                "origem": "teste-automatizado",
            },
            timeout=5,
        )
        self.assertEqual(primeira.status_code, 200)
        self.assertIsNone(primeira.json()["anomalia"])

        evento_anomalo = requests.post(
            f"{self.base_url}/evento",
            headers=cabecalhos,
            json={
                "id_veiculo": "IAANOM1",
                "faixa": 2,
                "timestamp_evento": "2026-09-23T02:00:00",
                "sensor_id": "sensor-teste-ia",
                "origem": "teste-automatizado",
            },
            timeout=5,
        )
        self.assertEqual(evento_anomalo.status_code, 200)
        self.assertEqual(evento_anomalo.json()["anomalia"], "ia_anomalia")

        with SessionLocal() as db:
            cobrancas = (
                db.query(models.Cobranca)
                .join(models.EventoPassagem)
                .filter(models.EventoPassagem.id_veiculo == "IAANOM1")
                .count()
            )
            self.assertEqual(cobrancas, 1)

    def test_consulta_portal_avisa_sem_debitos_e_dados_incorretos(self):
        sem_debitos = requests.post(
            f"{self.base_url}/portal/consultar",
            json={
                "cpf": "98765432100",
                "placa": "SEM0D00",
                "registrar_acesso": True,
            },
            timeout=5,
        )
        self.assertEqual(sem_debitos.status_code, 200)
        self.assertEqual(sem_debitos.json()["total_pendentes"], 0)
        self.assertFalse(sem_debitos.json()["possui_debitos"])

        dados_incorretos = requests.post(
            f"{self.base_url}/portal/consultar",
            json={
                "cpf": "00000000000",
                "placa": "ERR0D00",
                "registrar_acesso": True,
            },
            timeout=5,
        )
        self.assertEqual(dados_incorretos.status_code, 404)
        self.assertEqual(
            dados_incorretos.json()["detail"],
            (
                "CPF ou veículo informados estão incorretos. "
                "Confira os dados e tente novamente."
            ),
        )

        pagina = requests.get(f"{self.base_url}/portal", timeout=5)
        self.assertIn('id="modalAviso"', pagina.text)
        self.assertIn("Nenhum débito encontrado", pagina.text)

        with SessionLocal() as db:
            logs_cliente = (
                db.query(models.LogAcesso)
                .filter(models.LogAcesso.tipo_usuario == "cliente")
                .all()
            )
            self.assertTrue(any(log.sucesso for log in logs_cliente))
            self.assertTrue(any(not log.sucesso for log in logs_cliente))
            self.assertTrue(
                any(
                    log.proprietario_id is not None
                    and log.veiculo_id is not None
                    for log in logs_cliente
                    if log.sucesso
                )
            )

    def test_portal_pagamento_qrcode_e_codigo_barras(self):
        consulta = requests.post(
            f"{self.base_url}/portal/consultar",
            json={"cpf": "12345678901", "placa": "ABC1D23"},
            timeout=5,
        )
        self.assertEqual(consulta.status_code, 200)
        self.assertEqual(
            {item["concessionaria"] for item in consulta.json()["cobrancas"]},
            {"ConectaVia", "RotaLink"},
        )
        self.assertTrue(
            all(item["concessionaria_logo"] for item in consulta.json()["cobrancas"])
        )
        pendentes = [
            item["id"]
            for item in consulta.json()["cobrancas"]
            if item["status"] == "pendente"
        ]
        self.assertEqual(len(pendentes), 2)

        tentativa_anomala = requests.post(
            f"{self.base_url}/portal/pagamento/iniciar",
            json={
                "cpf": "12345678901",
                "placa": "ABC1D23",
                "cobrancas": [self.cobranca_anomala_id],
                "metodo": "pix",
            },
            timeout=5,
        )
        self.assertEqual(tentativa_anomala.status_code, 409)

        inicio = requests.post(
            f"{self.base_url}/portal/pagamento/iniciar",
            json={
                "cpf": "12345678901",
                "placa": "ABC1D23",
                "cobrancas": [pendentes[0]],
                "metodo": "pix",
            },
            timeout=5,
        )
        self.assertEqual(inicio.status_code, 200)
        pagamento = inicio.json()
        self.assertTrue(requests.get(pagamento["confirmacao_url"], timeout=5).ok)
        qr = requests.get(pagamento["qrcode_url"], timeout=5)
        self.assertEqual(qr.headers["content-type"], "image/png")
        barras = requests.get(pagamento["codigo_barras_url"], timeout=5)
        self.assertEqual(barras.headers["content-type"], "image/svg+xml")

        status_pendente = requests.get(
            f"{self.base_url}/portal/pagamento/status",
            params={"token": pagamento["token"]},
            timeout=5,
        )
        self.assertFalse(status_pendente.json()["confirmado"])

        confirmacao = requests.post(
            f"{self.base_url}/portal/pagamento/confirmar",
            json={"token": pagamento["token"]},
            timeout=5,
        )
        self.assertEqual(confirmacao.status_code, 200)
        self.assertEqual(confirmacao.json()["atualizadas"], 1)
        self.assertTrue(
            confirmacao.json()["success_url"].startswith(
                "/pagamento/confirmado?token="
            )
        )

        status_confirmado = requests.get(
            f"{self.base_url}/portal/pagamento/status",
            params={"token": pagamento["token"]},
            timeout=5,
        )
        self.assertTrue(status_confirmado.json()["confirmado"])
        pagina_sucesso = requests.get(
            f"{self.base_url}{confirmacao.json()['success_url']}",
            timeout=5,
        )
        self.assertIn("Pagamento confirmado", pagina_sucesso.text)
        self.assertIn("Negociar outros débitos", pagina_sucesso.text)
        self.assertIn("/cobrancas?cpf=12345678901", pagina_sucesso.text)

        segundo_pagamento = requests.post(
            f"{self.base_url}/portal/pagamento/iniciar",
            json={
                "cpf": "12345678901",
                "placa": "ABC1D23",
                "cobrancas": [pendentes[1]],
                "metodo": "boleto",
            },
            timeout=5,
        ).json()
        segunda_confirmacao = requests.post(
            f"{self.base_url}/portal/pagamento/confirmar",
            json={"token": segundo_pagamento["token"]},
            timeout=5,
        )
        self.assertEqual(segunda_confirmacao.status_code, 200)
        pagina_final = requests.get(
            f"{self.base_url}{segunda_confirmacao.json()['success_url']}",
            timeout=5,
        )
        self.assertNotIn("Negociar outros débitos", pagina_final.text)
        self.assertIn(">Encerrar<", pagina_final.text)

        atualizada = requests.post(
            f"{self.base_url}/portal/consultar",
            json={"cpf": "12345678901", "placa": "ABC1D23"},
            timeout=5,
        ).json()
        self.assertTrue(all(item["status"] == "pago" for item in atualizada["cobrancas"]))

    def test_raiz_separa_portal_cliente_e_gestao(self):
        resposta_cliente = requests.get(
            f"{self.base_url}/",
            headers={"Host": "portal-free-flow.vercel.app"},
            allow_redirects=False,
            timeout=5,
        )
        self.assertEqual(resposta_cliente.status_code, 307)
        self.assertEqual(resposta_cliente.headers["location"], "/portal")

        resposta_gestao = requests.get(
            f"{self.base_url}/",
            headers={"Host": "gestao-free-flow.vercel.app"},
            allow_redirects=False,
            timeout=5,
        )
        self.assertEqual(resposta_gestao.status_code, 307)
        self.assertEqual(resposta_gestao.headers["location"], "/admin/login")

    def test_portal_gestao_unificado(self):
        sessao = requests.Session()
        login = sessao.post(
            f"{self.base_url}/admin/login",
            data={"usuario": "ConectaVia", "senha": "senha-teste-conectavia"},
            allow_redirects=False,
            timeout=5,
        )
        self.assertEqual(login.status_code, 303)

        login_invalido = requests.post(
            f"{self.base_url}/admin/login",
            data={"usuario": "ConectaVia", "senha": "senha-incorreta"},
            allow_redirects=False,
            timeout=5,
        )
        self.assertEqual(login_invalido.status_code, 401)

        with SessionLocal() as db:
            logs_admin = (
                db.query(models.LogAcesso)
                .filter(models.LogAcesso.tipo_usuario == "administrador")
                .all()
            )
            self.assertTrue(any(log.sucesso for log in logs_admin))
            self.assertTrue(any(not log.sucesso for log in logs_admin))

        passagens = sessao.get(f"{self.base_url}/dashboard", timeout=5)
        recebiveis = sessao.get(f"{self.base_url}/admin/cobrancas", timeout=5)
        self.assertIn("Monitoramento de passagens", passagens.text)
        self.assertIn("Monitoria de Recebíveis", passagens.text)
        self.assertIn("Monitoria de Recebíveis", recebiveis.text)
        self.assertIn("Portal de Gestão FreeFlow", recebiveis.text)
        self.assertIn('id="filtroDataInicial"', passagens.text)
        self.assertIn('id="filtroDataFinal"', passagens.text)
        self.assertIn('name="data_inicial" type="date"', recebiveis.text)
        self.assertIn('name="data_final" type="date"', recebiveis.text)
        self.assertIn("ConectaVia", passagens.text)
        self.assertIn("/static/logos/conectavia-simbolo.png", passagens.text)
        logo = sessao.get(
            f"{self.base_url}/static/logos/conectavia-simbolo.png",
            timeout=5,
        )
        self.assertEqual(logo.status_code, 200)
        self.assertEqual(logo.headers["content-type"], "image/png")

        with SessionLocal() as db:
            for id_veiculo, timestamp_evento in (
                ("FORAANT", "2026-08-24T23:59:59"),
                ("INICIO", "2026-08-25T00:00:00"),
                ("FINAL", "2026-09-29T23:59:59"),
                ("FORAPOS", "2026-09-30T00:00:00"),
            ):
                db.add(
                    models.EventoPassagem(
                        id_veiculo=id_veiculo,
                        faixa=1,
                        timestamp_evento=timestamp_evento,
                        valor=5.0,
                        processado=1,
                    )
                )
            db.commit()

        data_inicial = "2026-08-25"
        data_final = "2026-09-29"
        dashboard_filtrado = sessao.get(
            f"{self.base_url}/dashboard-data",
            params={
                "data_inicial": data_inicial,
                "data_final": data_final,
            },
            timeout=5,
        )
        self.assertEqual(dashboard_filtrado.status_code, 200)
        ids_filtrados = {
            evento["id_veiculo"]
            for evento in dashboard_filtrado.json()["eventos"]
        }
        self.assertIn("INICIO", ids_filtrados)
        self.assertIn("FINAL", ids_filtrados)
        self.assertNotIn("FORAANT", ids_filtrados)
        self.assertNotIn("FORAPOS", ids_filtrados)

        dashboard_sem_resultado = sessao.get(
            f"{self.base_url}/dashboard-data",
            params={
                "data_inicial": "2100-01-01",
                "data_final": "2100-01-31",
            },
            timeout=5,
        )
        self.assertEqual(dashboard_sem_resultado.json()["total_passagens"], 0)

        recebiveis_filtrados = sessao.get(
            f"{self.base_url}/admin/cobrancas",
            params={
                "data_inicial": data_inicial,
                "data_final": data_final,
            },
            timeout=5,
        )
        self.assertIn(f'value="{data_inicial}"', recebiveis_filtrados.text)
        self.assertIn(f'value="{data_final}"', recebiveis_filtrados.text)

        csv_filtrado = sessao.get(
            f"{self.base_url}/exportar-csv",
            params={
                "data_inicial": data_inicial,
                "data_final": data_final,
                "anomalia": "todos",
            },
            timeout=5,
        )
        self.assertEqual(csv_filtrado.status_code, 200)
        self.assertIn("2026-08-25T00:00:00", csv_filtrado.text)
        self.assertIn("2026-09-29T23:59:59", csv_filtrado.text)
        self.assertNotIn("2026-08-24T23:59:59", csv_filtrado.text)
        self.assertNotIn("2026-09-30T00:00:00", csv_filtrado.text)

        data_invalida = sessao.get(
            f"{self.base_url}/dashboard-data",
            params={"data_inicial": "23/09/2026"},
            timeout=5,
        )
        self.assertEqual(data_invalida.status_code, 400)

        periodo_invertido = sessao.get(
            f"{self.base_url}/dashboard-data",
            params={
                "data_inicial": "2026-09-29",
                "data_final": "2026-08-25",
            },
            timeout=5,
        )
        self.assertEqual(periodo_invertido.status_code, 400)

        sessao_b = requests.Session()
        login_b = sessao_b.post(
            f"{self.base_url}/admin/login",
            data={"usuario": "RotaLink", "senha": "senha-teste-rotalink"},
            allow_redirects=False,
            timeout=5,
        )
        self.assertEqual(login_b.status_code, 303)
        passagens_b = sessao_b.get(f"{self.base_url}/dashboard", timeout=5)
        self.assertIn("RotaLink", passagens_b.text)
        self.assertIn("/static/logos/rotalink-simbolo.png", passagens_b.text)


if __name__ == "__main__":
    unittest.main()
