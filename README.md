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
│   ├── security.py
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

* Python 3.12
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
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Crie um arquivo `.env.local` baseado no `.env.example`.

Exemplo para execução local:

APP_ENV=local

DATABASE_URL=postgresql://freeflow_app.PROJECT_REF:SENHA@HOST.pooler.supabase.com:6543/postgres?sslmode=require

VALOR_PASSAGEM=5.0
VALOR_PASSAGEM_A=5.0
VALOR_PASSAGEM_B=7.5
TEMPO_DUPLICIDADE=30
TEMPO_SEM_DADOS_ALERTA=120
REFRESH_SEGUNDOS=5

SESSION_SECRET=troque-por-uma-chave-secreta

ESP32_API_KEY=troque-por-uma-chave-longa-e-aleatoria

CONCESSIONARIA_A_USER=concessionaria_a
CONCESSIONARIA_A_PASSWORD=admin_a
CONCESSIONARIA_A_NOME=Concessionária A
CONCESSIONARIA_A_SIGLA=CA

CONCESSIONARIA_B_USER=concessionaria_b
CONCESSIONARIA_B_PASSWORD=admin_b
CONCESSIONARIA_B_NOME=Concessionária B
CONCESSIONARIA_B_SIGLA=CB

O arquivo `.env.local` real não é enviado ao GitHub. Para Vercel/serverless,
use sempre o Transaction pooler do Supabase na porta `6543`.

Antes de iniciar a aplicação, aplique as migrations e faça a carga dos dados:

```bash
supabase link --project-ref SEU_PROJECT_REF
supabase db push --linked
python -m scripts.banco.migrar_sqlite_supabase
python -m scripts.banco.seed_usuarios
```

A aplicação não cria tabelas automaticamente durante o boot. O esquema oficial
fica versionado em `supabase/migrations/`.

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

Na tela **Meus débitos**, somente concessionárias com valores pendentes são
exibidas. O pagamento demonstrativo gera um QR Code (PIX) ou código de barras
(boleto) que direciona para uma página separada de confirmação. Depois da
confirmação, os débitos são atualizados automaticamente.

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

Esses acessos são cadastrados pela carga inicial executada com
`python -m scripts.banco.seed_usuarios`. A senha é armazenada como hash PBKDF2
com salt e nunca é salva em texto puro.

As credenciais usadas nessa carga inicial podem ser configuradas por variáveis
de ambiente:

CONCESSIONARIA_A_USER=
CONCESSIONARIA_A_PASSWORD=

CONCESSIONARIA_B_USER=
CONCESSIONARIA_B_PASSWORD=

SESSION_SECRET=

As credenciais apresentadas são destinadas apenas ao protótipo acadêmico.

Depois que um usuário já foi criado, alterar a variável de ambiente não troca
automaticamente a senha existente no banco.

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

O menu fixo do Portal de Gestão reúne **Monitoria de passagens** e **Monitoria
de Recebíveis**. A identidade, a sigla e o valor por passagem podem ser
configurados separadamente para cada concessionária pelas variáveis de
ambiente.

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

## Análise de duplicidade

A partir da segunda passagem conhecida de um veículo, o evento é analisado por
dois modelos Isolation Forest. O modelo comportamental considera faixa,
intervalo e horário; o modelo temporal é especializado no intervalo entre as
passagens. Quando o modelo temporal detecta uma anomalia inferior a 30 segundos,
o evento recebe a categoria operacional de duplicidade.

No protótipo:

Mesmo veículo em intervalo inferior a 30 segundos
→ Duplicidade analisada pelo módulo de IA

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

O projeto utiliza dois modelos **Isolation Forest** como componentes ativos da
análise dos eventos de passagem e da decisão que antecede a cobrança.

O modelo busca identificar eventos que apresentam características fora do padrão observado nos dados utilizados durante o treinamento.

A primeira passagem conhecida de cada veículo é considerada normal porque ainda
não existe intervalo anterior. Todas as passagens seguintes são submetidas ao
modelo com as características `faixa`, `intervalo_segundos` e `hora_decimal`.

Quando o modelo temporal encontra uma repetição anômala inferior a 30 segundos,
o evento recebe a categoria `duplicidade`. Outras ocorrências rejeitadas pelo
modelo comportamental recebem a categoria `ia_anomalia`. Nenhuma dessas
categorias gera cobrança; somente eventos classificados como normais seguem
para o registro financeiro.

O limite temporal também permanece como salvaguarda operacional para que uma
leitura repetida nunca seja cobrada, mesmo diante de um falso negativo do modelo.

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
Análise por IA
   ↓
Classificação operacional
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

O banco oficial de desenvolvimento e produção é o PostgreSQL do Supabase:


DATABASE_URL=postgresql://freeflow_app.PROJECT_REF:SENHA@HOST.pooler.supabase.com:6543/postgres?sslmode=require

O SQLite abaixo permanece apenas como cópia/alternativa local e não deve ser
usado em produção:

```env
DATABASE_URL=sqlite:///./data/freeflow.db
```

O arquivo do banco local:

data/freeflow.db

não é enviado ao GitHub.

A aplicação utiliza SQLAlchemy, permitindo configurar outro banco através da variável:

DATABASE_URL=

O banco possui as tabelas:

* `proprietarios`;
* `veiculos`;
* `eventos_passagem`;
* `cobrancas`;
* `usuarios_concessionarias`.

A tabela `usuarios_concessionarias` guarda o login administrativo, o hash da
senha, a identificação e o nome da concessionária, as faixas permitidas, o
estado ativo do usuário e a data de criação.

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

## Supabase e Vercel

O PostgreSQL do Supabase é o banco oficial. O FastAPI é publicado como uma
Vercel Function a partir de `app/main.py`.

Fluxo recomendado:

```bash
vercel link
supabase link --project-ref SEU_PROJECT_REF
supabase db push --linked
vercel env ls preview
vercel env ls production
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002
vercel deploy
vercel deploy --prod
```

Só execute `vercel deploy --prod` depois de validar o Preview. Configure em
Preview e Production pelo menos `APP_ENV=production`, `DATABASE_URL`,
`SESSION_SECRET`, `ESP32_API_KEY`, os tempos operacionais e o valor da passagem.

A `DATABASE_URL` deve usar o Transaction pooler do Supabase (porta `6543`) e
SSL. O usuário do banco utilizado pela aplicação deve ter apenas os privilégios
necessários nas tabelas do Free Flow.

Depois da publicação, altere `URL_EVENTO` no `secrets.h` do ESP32 para o endpoint
HTTPS da Vercel e mantenha `FREEFLOW_API_KEY` igual a `ESP32_API_KEY`.

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
Análise pelo Isolation Forest
 ↓
Classificação normal, duplicidade ou anomalia
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

