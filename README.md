# Sistema FreeFlow

Protótipo de sistema de cobrança automática de pedágio Free Flow desenvolvido para TCC, utilizando IoT, FastAPI, banco de dados e Inteligência Artificial com Isolation Forest.

## Estrutura do projeto

```text
SistemaFreeFlow/
├── app/
│   ├── templates/              # Dashboard, portal e páginas de cobrança
│   ├── main.py                 # API FastAPI e rotas principais
│   ├── models.py               # Modelos do banco de dados
│   ├── schemas.py              # Schemas da API
│   ├── crud.py                 # Operações no banco
│   ├── database.py             # Conexão com banco
│   ├── config.py               # Configurações e variáveis de ambiente
│   ├── anomaly.py              # Detecção de anomalias
│   └── modelo_anomalia.joblib  # Modelo Isolation Forest treinado
│
├── data/
│   └── treino_normal.csv       # Dados utilizados no treinamento
│
├── scripts/
│   ├── banco/
│   │   ├── cadastro_veic_teste.py
│   │   ├── gerar_dados_portal.py
│   │   └── sincronizar_cobrancas.py
│   │
│   ├── ia/
│   │   ├── gerar_dados_treino.py
│   │   ├── treinar_modelo.py
│   │   └── testar_modelo.py
│   │
│   ├── esp32/
│   │   ├── esp32.ino
│   │   └── secrets.example.h
│   │
│   └── simulador.py
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Executando localmente

Python recomendado: **3.11**

Instale as dependências:

```bash
pip install -r requirements.txt
```

Crie o arquivo `.env` baseado em `.env.example`.

Para desenvolvimento local:

```env
APP_ENV=local
DATABASE_URL=sqlite:///./data/freeflow.db
```

Inicie a API:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

Dashboard:

```text
http://localhost:8002/dashboard
```

## Inteligência Artificial

O projeto utiliza **Isolation Forest** para detectar comportamentos anômalos nos eventos.

Modelo utilizado pela API:

```text
app/modelo_anomalia.joblib
```

Scripts de IA:

```bash
python -m scripts.ia.gerar_dados_treino
python -m scripts.ia.treinar_modelo
python -m scripts.ia.testar_modelo
```

## Scripts de banco

Executar a partir da raiz do projeto:

```bash
python -m scripts.banco.cadastro_veic_teste
python -m scripts.banco.gerar_dados_portal
python -m scripts.banco.sincronizar_cobrancas
```

## ESP32

Firmware:

```text
scripts/esp32/esp32.ino
```

Criar localmente:

```text
scripts/esp32/secrets.h
```

usando `secrets.example.h` como modelo.

As credenciais reais não são enviadas ao GitHub.

## Banco de dados / AWS

Localmente o sistema utiliza SQLite.

Para produção, o banco pode ser substituído por PostgreSQL através da variável:

```env
DATABASE_URL=postgresql://USUARIO:SENHA@HOST:5432/BANCO
```

O acesso ao banco é feito com SQLAlchemy.

O `.env`, o banco SQLite local, ambiente virtual e credenciais reais dos ESP32 não fazem parte do repositório.