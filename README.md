# Sistema FreeFlow

Protótipo de sistema de cobrança automática de pedágio Free Flow desenvolvido para TCC, utilizando **IoT, FastAPI, banco de dados e Inteligência Artificial com Isolation Forest**.

O sistema recebe eventos enviados por ESP32 com leitores RFID, registra as passagens, analisa duplicidades e comportamentos anômalos, gera cobranças e disponibiliza interfaces separadas para clientes e concessionárias.

---

## Estrutura do projeto

SistemaFreeFlow/

├── app/
│   ├── templates/
│   │   ├── dashboard.html
│   │   ├── portal.html
│   │   ├── cobrancas.html
│   │   ├── pix.html
│   │   ├── boleto.html
│   │   └── admin_login.html
│   │
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── database.py
│   ├── config.py
│   ├── anomaly.py
│   └── modelo_anomalia.joblib
│
├── data/
│   └── treino_normal.csv
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

---

## Requisitos

Recomendado:

* Python 3.11
* Git
* Arduino IDE
* ESP32
* Leitor RFID RC522
* Tags RFID compatíveis

---

## Executando localmente

Crie um ambiente virtual:

python -m venv .venv

Ative o ambiente virtual no Windows:

```powershell
.\.venv\Scripts\Activate.ps1

Instale as dependências:

```bash
pip install -r requirements.txt
```

Crie um arquivo `.env` baseado no `.env.example`.

Exemplo para execução local:

APP_ENV=local

DATABASE_URL=sqlite:///./data/freeflow.db

VALOR_PASSAGEM=5.0
TEMPO_DUPLICIDADE=60
TEMPO_SEM_DADOS_ALERTA=120
REFRESH_SEGUNDOS=5

SESSION_SECRET=troque-por-uma-chave-secreta

CONCESSIONARIA_A_USER=concessionaria_a
CONCESSIONARIA_A_PASSWORD=admin_a

CONCESSIONARIA_B_USER=concessionaria_b
CONCESSIONARIA_B_PASSWORD=admin_b

O arquivo `.env` real não é enviado ao GitHub.

---

## Iniciando a API

Na raiz do projeto:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

Com o servidor iniciado, as principais páginas ficam disponíveis em:

Portal do cliente:
http://localhost:8002/portal

Portal da concessionária:
http://localhost:8002/admin/login

---

## Portal do cliente

O portal permite consultar cobranças utilizando:

CPF + Placa

O sistema verifica se a placa informada pertence ao CPF antes de liberar as informações.

Fluxo:

/portal
   ↓
CPF + placa
   ↓
/cobrancas
   ↓
PIX ou boleto

O cliente visualiza apenas dados relacionados aos seus próprios veículos e cobranças.

---

## Portal da concessionária

O sistema possui uma interface administrativa separada do portal destinado ao cliente.

O acesso é realizado em:

http://localhost:8002/admin/login

Após a autenticação, a concessionária é direcionada ao dashboard:

/admin/login
      ↓
/dashboard

Cada usuário administrativo está associado a uma concessionária e às faixas que ela pode visualizar.

No ambiente demonstrativo existem dois acessos:

Concessionária A
Usuário: concessionaria_a
Senha: admin_a

Concessionária B
Usuário: concessionaria_b
Senha: admin_b

As credenciais podem ser configuradas por variáveis de ambiente:

CONCESSIONARIA_A_USER=
CONCESSIONARIA_A_PASSWORD=

CONCESSIONARIA_B_USER=
CONCESSIONARIA_B_PASSWORD=

SESSION_SECRET=

As credenciais apresentadas são destinadas apenas ao protótipo acadêmico.

Em uma implementação de produção deve ser utilizado um mecanismo de autenticação apropriado.

---

## Dashboard administrativo

O dashboard é destinado às concessionárias e apresenta dados operacionais das passagens registradas.

Entre as informações disponíveis estão:

* veículos identificados;
* faixa utilizada;
* data e horário das passagens;
* valor das passagens;
* total de valores gerados;
* duplicidades identificadas;
* últimas passagens;
* exportação dos dados em CSV.

Cada concessionária possui seu próprio acesso administrativo.

No protótipo atual, a separação dos dados é simulada pelas faixas:

Concessionária A → Faixa 1
Concessionária B → Faixa 2

Dessa forma, uma concessionária não visualiza nem exporta os eventos pertencentes à outra.

Essa associação entre uma concessionária e uma única faixa é uma simplificação utilizada no protótipo acadêmico.

Em uma implementação real, uma concessionária poderia administrar diversas faixas.

---

## Exportação CSV

O dashboard permite exportar os eventos em formato CSV.

A exportação respeita a concessionária autenticada.

Exemplo:

Concessionária A
→ exporta somente eventos da Faixa 1

Concessionária B
→ exporta somente eventos da Faixa 2

Também é possível utilizar filtros para exportar:

Todos os eventos

Somente eventos OK

Somente duplicidades

---

## Clientes demonstrativos

O protótipo possui uma lista de clientes demonstrativos.

Quando uma nova placa ou UID é recebida em uma passagem válida, o sistema pode associá-la automaticamente ao próximo cliente demonstrativo disponível.

Exemplo:

1ª placa → Cliente Demo 01 → CPF 10000000001

2ª placa → Cliente Demo 02 → CPF 10000000002

3ª placa → Cliente Demo 03 → CPF 10000000003

...

10ª placa → Cliente Demo 10 → CPF 10000000010


Depois que uma placa é vinculada, ela continua associada ao mesmo proprietário.

---

## Regra de duplicidade

A identificação de duplicidades utiliza uma regra determinística.

No protótipo:

Mesmo veículo em intervalo inferior a 60 segundos
→ Duplicidade

A regra operacional é:

Evento normal
→ gera cobrança

Duplicidade
→ não gera nova cobrança

Exemplo:

14:00:00 → OK → gera cobrança

14:02:00 → OK → gera cobrança

14:04:00 → OK → gera cobrança

14:04:10 → Duplicidade → não gera cobrança

---

## Inteligência Artificial

O projeto utiliza **Isolation Forest** como mecanismo auxiliar de análise de comportamento dos eventos de passagem.

O modelo busca identificar eventos que apresentam características fora do padrão observado nos dados utilizados durante o treinamento.

A identificação de duplicidades não depende do modelo de Inteligência Artificial.

A duplicidade utiliza a regra determinística de intervalo inferior a 60 segundos.

A análise realizada pelo Isolation Forest permanece como componente experimental de Inteligência Artificial da arquitetura.

O modelo treinado utilizado pela aplicação está em:

app/modelo_anomalia.joblib

Os scripts relacionados à IA ficam em:

scripts/ia/


Para gerar dados de treinamento:

```bash
python -m scripts.ia.gerar_dados_treino
```

Para treinar o modelo:

```bash
python -m scripts.ia.treinar_modelo
```

Para testar o modelo já treinado:

```bash
python -m scripts.ia.testar_modelo
```

Os scripts devem ser executados a partir da raiz do projeto.

---

## Scripts auxiliares do banco

Os scripts relacionados a dados de teste e cobranças estão em:

scripts/banco/

Exemplos:

```bash
python -m scripts.banco.cadastro_veic_teste

python -m scripts.banco.gerar_dados_portal

python -m scripts.banco.sincronizar_cobrancas
```

Esses scripts alteram dados do banco e devem ser utilizados apenas quando necessário.

---

## ESP32 e RFID

O firmware disponível no repositório está em:

scripts/esp32/esp32.ino

O sistema utiliza dois ESP32, um para cada faixa do protótipo.

O mesmo firmware pode ser utilizado nos dois dispositivos, pois a faixa é identificada através do endereço MAC do ESP32.

Os leitores utilizados são RC522.

Pinagem utilizada:

SDA / SS → GPIO 5

SCK      → GPIO 18

MOSI     → GPIO 23

MISO     → GPIO 19

RST      → GPIO 2

3.3V     → 3.3V

GND      → GND

---

## Testando os ESP32

Para testar fisicamente os ESP32 é recomendado utilizar o **Arduino IDE**.

No Arduino IDE:

1. Instalar o suporte para placas ESP32 da Espressif.
2. Instalar a biblioteca `MFRC522`.
3. Abrir o arquivo `.ino`.
4. Configurar a rede Wi-Fi.
5. Configurar a URL da API.
6. Fazer upload do firmware no ESP32.
7. Abrir o Monitor Serial em `115200`.

Para testes locais, o computador e os ESP32 devem estar conectados à mesma rede Wi-Fi.

No Windows, descubra o IPv4 do computador:

powershell
ipconfig

Exemplo:

IPv4 do computador:
192.168.1.50

A URL configurada no ESP32 ficaria semelhante a:

http://192.168.1.50:8002/evento


O FastAPI deve estar rodando com:

python -m uvicorn app.main:app --host 0.0.0.0 --port 8002

Fluxo:

Tag RFID
   ↓
RC522
   ↓
ESP32
   ↓
POST /evento
   ↓
FastAPI
   ↓
Banco de dados
   ↓
Análise de duplicidade
   ↓
Análise auxiliar por IA
   ↓
Cobrança
   ↓
Portal do Cliente / Portal da Concessionária

Ao aproximar uma tag do leitor, o Monitor Serial deve mostrar o UID detectado e o resultado da requisição HTTP.

O evento também deve aparecer no dashboard da concessionária correspondente.

---

## Credenciais dos ESP32

O repositório contém:

scripts/esp32/secrets.example.h

As credenciais reais podem ser colocadas em:

scripts/esp32/secrets.h

O `secrets.h` está ignorado pelo Git e não deve ser enviado ao repositório público.

---

## Banco de dados

Durante o desenvolvimento local, o sistema pode utilizar SQLite:


DATABASE_URL=sqlite:///./data/freeflow.db

O arquivo do banco local:

data/freeflow.db

não é enviado ao GitHub.

A aplicação utiliza SQLAlchemy, permitindo configurar outro banco através da variável:

DATABASE_URL=

---

## Arquitetura de acesso

A solução utiliza interfaces separadas por perfil de usuário.

Cliente
   ↓
Portal do Cliente
   ↓
Visualiza seus próprios veículos e cobranças


Concessionária
   ↓
Portal Administrativo
   ↓
Visualiza apenas seus próprios dados operacionais


O backend, o banco de dados e os componentes de análise permanecem compartilhados.

A separação ocorre através das regras de autenticação e controle de acesso.

Essa estrutura permite que um mesmo cliente possa possuir passagens relacionadas a diferentes concessionárias, enquanto cada concessionária visualiza apenas os eventos sob sua responsabilidade.

---

## AWS / Produção

A aplicação foi desenvolvida de forma a permitir futura implantação em ambiente de nuvem.

Para implantação na AWS, o banco SQLite local pode ser substituído por PostgreSQL.

Exemplo:

env
DATABASE_URL=postgresql://USUARIO:SENHA@HOST:5432/BANCO


As configurações de produção devem ser definidas através de variáveis de ambiente.

Exemplo:

env
APP_ENV=production

DATABASE_URL=

SESSION_SECRET=

CONCESSIONARIA_A_USER=
CONCESSIONARIA_A_PASSWORD=

CONCESSIONARIA_B_USER=
CONCESSIONARIA_B_PASSWORD=


As credenciais utilizadas no protótipo são demonstrativas.

Em uma implantação real, recomenda-se substituir a autenticação simplificada por um mecanismo apropriado de gerenciamento de identidade e acesso.

A infraestrutura AWS pode ser utilizada para hospedar a aplicação FastAPI e conectar o sistema a um banco PostgreSQL.

Após a aplicação estar publicada, a URL configurada nos ESP32 deve ser alterada do IP local para o endpoint HTTPS disponibilizado na nuvem.

---

## Arquivos que não devem ser enviados ao Git

O `.gitignore` protege arquivos locais ou sensíveis.

Entre eles:
.env

.venv/

data/freeflow.db

scripts/esp32/secrets.h

__pycache__/

.vscode/

---

## Resumo do fluxo

RFID
 ↓
ESP32
 ↓
FastAPI
 ↓
Registro da passagem
 ↓
Análise de duplicidade
 ↓
Análise auxiliar por IA
 ↓
Duplicidade?
 ├── Sim → registra evento sem nova cobrança
 │
 └── Não → identifica veículo e gera cobrança
 ↓
Banco de dados
 ↓
Portal do Cliente / Portal da Concessionária

O projeto foi desenvolvido como protótipo acadêmico de uma arquitetura de cobrança automática Free Flow baseada em IoT, banco de dados, computação em nuvem e Inteligência Artificial.

A solução utiliza interfaces separadas por perfil de acesso: o cliente consulta exclusivamente seus próprios veículos e cobranças, enquanto cada concessionária acessa apenas os dados operacionais associados às suas faixas.

