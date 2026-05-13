# Sistema Free Flow - MVP TCC

Este repositório contém o MVP funcional desenvolvido para o Trabalho de Conclusão de Curso com o tema:

**Proposta de arquitetura resiliente para sistemas de cobrança automática de pedágio Free Flow no Brasil, baseada em IoT, computação em nuvem e inteligência artificial.**

O sistema simula o funcionamento de um pedágio no modelo **Free Flow**, onde eventos de passagem de veículos são registrados, armazenados, analisados e exibidos em um dashboard web.

---

## Objetivo do Projeto

O objetivo do projeto é demonstrar, em ambiente controlado, o fluxo básico de um sistema de cobrança automática de pedágio sem cancelas físicas.

O MVP contempla:

- Recebimento de eventos de passagem de veículos;
- Armazenamento dos eventos em banco de dados;
- Detecção simples de anomalias por duplicidade;
- Dashboard para monitoramento;
- Exportação de relatórios em CSV;
- Simulação de eventos para testes.

---

## Tecnologias Utilizadas

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- HTML
- CSS
- JavaScript
- Uvicorn
- Python-dotenv

---

## Estrutura do Projeto

```txt
SistemaFreeFlow/
├── app/
│   ├── templates/
│   │   └── dashboard.html
│   ├── anomaly.py
│   ├── config.py
│   ├── crud.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── data/

Funcionalidades
API

A API permite registrar eventos de passagem, listar eventos armazenados e executar a análise de anomalias.

Principais rotas:

GET /
POST /evento
POST /analisar
GET /eventos
GET /dashboard
GET /dashboard-data
GET /exportar-csv
Dashboard

O sistema possui um dashboard web para visualização dos dados registrados.

O dashboard exibe:

Total de veículos registrados;
Valor total gerado;
Valor por passagem;
Total de duplicidades;
Últimos eventos;
Últimas duplicidades;
Status de atualização;
Filtro por anomalia;
Exportação CSV.

Acesse pelo navegador:

http://127.0.0.1:8000/dashboard
Detecção de Anomalias

A detecção de anomalias atual é baseada em regra simples.

O sistema considera uma duplicidade quando o mesmo veículo passa pela mesma faixa em um intervalo menor que o tempo configurado.

Exemplo:

Mesmo veículo + mesma faixa + curto intervalo de tempo = duplicidade

O tempo de duplicidade pode ser configurado no arquivo .env.

Configuração do Ambiente

Crie um arquivo .env na raiz do projeto com base no arquivo .env.example.

Exemplo:

APP_ENV=local
DATABASE_URL=sqlite:///./data/freeflow.db
VALOR_PASSAGEM=5.0
TEMPO_DUPLICIDADE=60
TEMPO_SEM_DADOS_ALERTA=120
REFRESH_SEGUNDOS=5
Instalação

Clone o repositório:

git clone https://github.com/ArthurR06/SistemaFreeFlow.git

Acesse a pasta do projeto:

cd SistemaFreeFlow

Crie o ambiente virtual:

python -m venv venv

Ative o ambiente virtual no Windows:

venv\Scripts\activate

Instale as dependências:

pip install -r requirements.txt
Como Executar o Sistema

Execute a API com o Uvicorn:

uvicorn app.main:app --reload

Depois acesse:

http://127.0.0.1:8000

Para abrir o dashboard:

http://127.0.0.1:8000/dashboard
Como Simular Eventos

Com a API rodando, execute o simulador:

python scripts/simulador.py

O simulador envia eventos fictícios para a API e depois executa a análise de anomalias.

Exportação de CSV

O dashboard permite exportar os eventos em formato CSV.

Também é possível acessar diretamente:

http://127.0.0.1:8000/exportar-csv?anomalia=todos

Filtros disponíveis:

todos
duplicidade
ok
Relação com o TCC

Este sistema representa o MVP prático da arquitetura proposta no TCC.

Ele demonstra o fluxo principal de um sistema Free Flow:

Dispositivo IoT / Simulador
        ↓
Backend FastAPI
        ↓
Banco de Dados
        ↓
Módulo de Anomalias
        ↓
Dashboard

A versão atual roda localmente e tem como foco a validação acadêmica do fluxo de dados, da persistência, do monitoramento e da detecção inicial de anomalias.

Em uma evolução futura, o sistema pode ser integrado a:

ESP32;
Sensor RFID;
AWS IoT Core;
Banco de dados em nuvem;
Serviços de monitoramento;
Algoritmos reais de inteligência artificial.
Observações

Este projeto é um MVP acadêmico e não representa uma solução pronta para uso em ambiente real de produção.

O objetivo é validar os conceitos de:

Free Flow;
IoT;
Backend;
Banco de dados;
Dashboard;
Resiliência;
Detecção de anomalias.
Autores

Projeto desenvolvido para fins acadêmicos no curso de Ciência da Computação da Universidade Paulista - UNIP.

Autores:

Arthur Gomes Rodrigues de Lima
Camila Eiko Honda Martins
Joice Oliveira Jardim
Leticia Costa Moura


├── scripts/
│   └── simulador.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
