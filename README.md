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
├── scripts/
│   └── simulador.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
