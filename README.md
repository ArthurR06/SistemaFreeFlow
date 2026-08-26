# Sistema FreeFlow

Protótipo de sistema de cobrança automática de pedágio Free Flow desenvolvido para TCC, utilizando **IoT, FastAPI, banco de dados e Inteligência Artificial com Isolation Forest**.

O sistema recebe eventos enviados por ESP32 com leitores RFID, registra as passagens, analisa possíveis anomalias, gera cobranças e disponibiliza páginas de monitoramento, consulta de débitos e administração.

---

## Estrutura do projeto

```text
SistemaFreeFlow/
├── app/
│   ├── templates/
│   │   ├── dashboard.html
│   │   ├── portal.html
│   │   ├── cobrancas.html
│   │   ├── pix.html
│   │   ├── boleto.html
│   │   ├── admin_login.html
│   │   └── admin_vinculos.html
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
```

---

## Requisitos

Recomendado:

- Python 3.11
- Git
- Arduino IDE para testar os ESP32
- ESP32
- Leitor RFID RC522
- Tags RFID compatíveis

---

## Executando localmente

Crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente virtual no Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Crie um arquivo `.env` baseado no `.env.example`.

Exemplo para execução local:

```env
APP_ENV=local

DATABASE_URL=sqlite:///./data/freeflow.db

VALOR_PASSAGEM=5.0
TEMPO_DUPLICIDADE=60
TEMPO_SEM_DADOS_ALERTA=120
REFRESH_SEGUNDOS=5

ADMIN_USER=admin
ADMIN_PASSWORD=admin
SESSION_SECRET=troque-por-uma-chave-secreta
```

O arquivo `.env` real não é enviado ao GitHub.

---

## Iniciando a API

Na raiz do projeto:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

Com o servidor iniciado, as principais páginas ficam disponíveis em:

```text
Dashboard:
http://localhost:8002/dashboard

Portal do cliente:
http://localhost:8002/portal

Admin:
http://localhost:8002/admin/login
```

---

## Dashboard

O dashboard apresenta informações como:

- passagens recebidas;
- placa/UID do veículo;
- faixa utilizada;
- data e horário;
- valor da passagem;
- anomalias detectadas;
- duplicidades;
- status de comunicação;
- total gerado.

---

## Portal do cliente

O portal permite consultar as cobranças utilizando:

```text
CPF + Placa
```

O sistema verifica se a placa informada pertence ao CPF antes de liberar as cobranças.

Fluxo:

```text
/portal
   ↓
CPF + placa
   ↓
/cobrancas
   ↓
Pix ou boleto
```

---

## Área administrativa

Existe uma área administrativa destinada à consulta dos vínculos entre veículos e proprietários.

Acesso:

```text
http://localhost:8002/admin/login
```

Credenciais locais padrão:

```text
Usuário: admin
Senha: admin
```

Após o login, o sistema direciona para:

```text
/admin/vinculos
```

A página apresenta:

- placa;
- UID RFID;
- nome do proprietário;
- CPF.

Isso permite identificar a quem pertence uma placa/UID observada no monitoramento.

As credenciais administrativas podem ser alteradas através das variáveis:

```env
ADMIN_USER=
ADMIN_PASSWORD=
SESSION_SECRET=
```

Para produção, não utilizar `admin/admin`.

---

## Clientes demonstrativos

O protótipo possui uma lista de clientes demonstrativos.

Quando uma nova placa/UID é recebida em uma passagem válida, o sistema pode associá-la automaticamente ao próximo cliente demonstrativo disponível.

Exemplo:

```text
1ª placa → Cliente Demo 01 → CPF 10000000001
2ª placa → Cliente Demo 02 → CPF 10000000002
3ª placa → Cliente Demo 03 → CPF 10000000003
...
10ª placa → Cliente Demo 10 → CPF 10000000010
```

Depois que uma placa é vinculada, ela continua associada ao mesmo proprietário.

Os vínculos podem ser consultados pela área administrativa.

---

## Inteligência Artificial

O projeto utiliza **Isolation Forest** para auxiliar na identificação de comportamentos anômalos nos eventos de passagem.

O modelo treinado utilizado pela aplicação está em:

```text
app/modelo_anomalia.joblib
```

Os scripts relacionados à IA ficam em:

```text
scripts/ia/
```

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

```text
scripts/banco/
```

Exemplos:

```bash
python -m scripts.banco.cadastro_veic_teste

python -m scripts.banco.gerar_dados_portal

python -m scripts.banco.sincronizar_cobrancas
```

Esses scripts alteram dados do banco, portanto devem ser utilizados apenas quando necessário.

---

## ESP32 e RFID

O firmware disponível no repositório está em:

```text
scripts/esp32/esp32.ino
```

O sistema utiliza dois ESP32, um para cada faixa.

O mesmo firmware pode ser utilizado nos dois dispositivos, pois a faixa é identificada através do endereço MAC do ESP32.

Os leitores utilizados são RC522.

Pinagem utilizada:

```text
SDA / SS  → GPIO 5
SCK       → GPIO 18
MOSI      → GPIO 23
MISO      → GPIO 19
RST       → GPIO 2
3.3V      → 3.3V
GND       → GND
```

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

Para testes locais, o computador e os ESP32 devem estar na mesma rede Wi-Fi.

No Windows, descubra o IPv4 do computador:

```powershell
ipconfig
```

Exemplo:

```text
IPv4 do computador:
192.168.1.50
```

A URL configurada no ESP32 ficaria semelhante a:

```text
http://192.168.1.50:8002/evento
```

O FastAPI deve estar rodando com:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

Depois:

```text
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
Banco + IA + cobrança
   ↓
Dashboard
```

Ao aproximar uma tag do leitor, o Monitor Serial deve mostrar o UID detectado e o resultado da requisição HTTP.

O evento também deve aparecer no dashboard.

---

## Credenciais dos ESP32

O repositório contém:

```text
scripts/esp32/secrets.example.h
```

As credenciais reais podem ser colocadas em:

```text
scripts/esp32/secrets.h
```

O `secrets.h` está ignorado pelo Git e não deve ser enviado ao repositório público.

---

## Banco de dados

Durante o desenvolvimento local, o sistema pode utilizar SQLite:

```env
DATABASE_URL=sqlite:///./data/freeflow.db
```

O arquivo do banco local:

```text
data/freeflow.db
```

não é enviado ao GitHub.

A aplicação utiliza SQLAlchemy, permitindo configurar outro banco através da variável `DATABASE_URL`.

---

## AWS / Produção

Para implantação na AWS, o banco local pode ser substituído por PostgreSQL.

Exemplo:

```env
DATABASE_URL=postgresql://USUARIO:SENHA@HOST:5432/BANCO
```

As configurações de produção devem ser definidas por variáveis de ambiente, principalmente:

```env
APP_ENV=production
DATABASE_URL=
ADMIN_USER=
ADMIN_PASSWORD=
SESSION_SECRET=
```

A pessoa responsável pelo deploy pode utilizar a infraestrutura AWS mais adequada para executar a aplicação FastAPI e conectar o sistema ao PostgreSQL.

Após o sistema estar publicado, a URL configurada nos ESP32 deve ser alterada do IP local para o endpoint HTTPS disponibilizado na nuvem.

---

## Arquivos que não devem ser enviados ao Git

O `.gitignore` protege arquivos locais ou sensíveis, incluindo:

```text
.env
.venv/
data/freeflow.db
scripts/esp32/secrets.h
__pycache__/
.vscode/
```

---

## Resumo do fluxo

```text
RFID
 ↓
ESP32
 ↓
FastAPI
 ↓
Registro da passagem
 ↓
Análise de anomalia
 ↓
Identificação do veículo/proprietário
 ↓
Cobrança
 ↓
Dashboard / Portal / Admin
```

O projeto foi desenvolvido como protótipo acadêmico de uma arquitetura de cobrança automática Free Flow baseada em IoT, computação em nuvem e Inteligência Artificial.