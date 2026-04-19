[📖 Read in English](#english) | [📖 Ler em Português](#portugues)

---

<a name="english"></a>
# TooN OpenAPI Agent — Claude Code Agent

**TooN OpenAPI Agent** is a specialized Claude Code Agent designed to bridge the gap between large, complex REST APIs and Large Language Models (LLMs) with strict context windows.

It parses massive OpenAPI/Swagger `.json` or `.yaml` specs locally and compiles them into **TooN** (Token-Optimized Notation) — a custom, highly compressed syntactic grammar. By moving the heavy lifting of JSON parsing, circular `$ref` dereferencing, and nested schema flattening away from the AI agent and into local Python processes, **TooN OpenAPI Agent drastically reduces token consumption by up to ~90%**, all while keeping your AI perfectly aware of the entire API structure.

This agent is published on the **Anthropic Marketplace** and can be installed directly into any Claude Code project.

## How It Works

Once installed, the agent gains all capabilities below — activated by natural language, no need to know the internals:

| What you say | What the agent does |
|---|---|
| Provide an OpenAPI/Swagger URL or file | Ingests and compiles the API into TooN notation |
| "How do I call POST /users?" / "Generate a Go client" | Consults the contract and generates integration code |
| "Generate a complete TypeScript client" / "Generate only the POST /orders method" | Generates HTTP client for the full API or a single endpoint |
| "Generate Pytest tests for all endpoints" | Generates integration test suite |
| "Validate this JSON against the contract" | Validates the payload against the ingested schema |
| "Compare this API with the v2 I just ingested" | Diffs two versions and flags breaking changes |
| "Export the TooN context to use in another thread" | Generates a compact, self-contained context block |

---

## Installation

### From the Anthropic Marketplace

Search for **TooN OpenAPI Agent** in the Anthropic Marketplace and click **Install**. Claude Code will automatically configure the agent for your project.

### Manual Installation

**1. Clone this repository:**

```bash
git clone https://github.com/rafaellemes/toon-openapi-agent
```

**2. Copy the agent definition into your project:**

```bash
cp toon-openapi-agent/agents/toon-openapi-agent.md your-project/.claude/agents/
```

**3. Copy the skill into your project:**

```bash
cp -r toon-openapi-agent/skills/skill-toon-openapi your-project/.claude/skills/toon-openapi
```

**4. Install Python dependencies (from your project root or a shared venv):**

```bash
pip install -r your-project/.claude/skills/toon-openapi/requirements.txt
```

That's it. Claude Code will automatically load the agent and skill on the next session.

---

## Usage Examples

### 1. Ingesting an API (URL or Local File)

Instead of copying a 7,000-token JSON into the chat, just prompt the agent:

> *"Ingest the API at https://fakerestapi.azurewebsites.net/swagger/v1/swagger.json"*
> *(You can also pass a local file: `./downloads/api.yaml`)*

The agent processes everything locally and stores the compressed output under `.toon_apis/apis/fakerestapiweb-v1/`. It replies with the ultra-light TooN overview (~500 tokens):

```text
[API: fakerestapiweb-v1 | BASE: ]
---
GET   /api/v1/Authors -> getApiV1Authors |  [Authors]
POST  /api/v1/Authors -> postApiV1Authors |  [Authors]
  Req: body.id:i? body.idBook:i? body.firstName:s? body.lastName:s?
  Res: 200 (body.id:i? body.idBook:i? body.firstName:s? body.lastName:s?)
---
20 operations | Namespace: fakerestapiweb-v1

[toon-openapi] API mapped. You can ask for:
  → endpoint details or integration code    (e.g. "how do I call this endpoint?" / "generate a Go client")
  → HTTP client or SDK — full API or single endpoint  (e.g. "generate complete TypeScript class" / "generate only POST /orders method")
  → integration tests                       (e.g. "generate pytest tests for this endpoint")
  → payload validation                      (e.g. "validate this JSON against the contract")
  → diff with another version               (e.g. "compare with the v2 I just ingested")
  → export context to another thread        (e.g. "export the TooN block for this API")
```

### 2. Generating Code and Test Suites

Once ingested, ask in natural language — the agent handles the rest:

> *"Generate a complete Python client for this API."*
> *"Generate only the method for POST /authors."*
> *"Generate a full Pytest suite for all endpoints."*

The agent reads from `.toon_apis/apis/` automatically and outputs hallucination-free code — for the whole API or a single endpoint.

### 3. Comparing API Versions (Diff)

> *"Compare this API with the v2 I just ingested."*

The agent compares the two metadata folders and cleanly reports which endpoints were added, removed, or had breaking parameter changes — classified as 🔴 BREAKING, 🟢 NON-BREAKING, 🟡 ATTENTION, or ⚪ INFO.

### 4. Validating a Payload

> *"Validate this JSON against the contract for POST /users."*

The agent runs the payload through the ingested schema and reports errors, warnings, and info — without making network requests.

---

## Storage

All processed data is stored in `.toon_apis/` at your project root (created automatically on first ingest):

```
.toon_apis/
├── apis/
│   └── <namespace>/
│       ├── toon.txt       ← semantic overview (read by the agent)
│       ├── mapping.json   ← technical contract (queried via jq)
│       └── metrics.json   ← token usage history
├── diffs/
├── exports/
├── tests/
├── clients/
└── validations/
```

`.toon_apis/` is excluded from git by default via `.toon_apis/.gitignore`.

---

## Running Tests (for skill developers)

TooN OpenAPI has an aggressive TDD base covering edge cases (deep recursion limits, root primitives, priority form-data parsers):

```bash
cd skills/skill-toon-openapi/
pip install -r requirements.txt
pytest tests/test_unit.py tests/test_diff.py tests/test_validate.py tests/test_clientgen.py tests/test_testgen.py tests/test_exportgen.py tests/test_multi.py -v
```

---

## License

This project is licensed under the [MIT License](LICENSE).

<br><br>

---

<a name="portugues"></a>
# TooN OpenAPI Agent — Agente para Claude Code

O **TooN OpenAPI Agent** é um Agente Claude Code especializado, projetado para preencher a lacuna entre APIs REST complexas e Modelos de Linguagem (LLMs) com janelas de contexto estritas.

Ele analisa documentos `.json` ou `.yaml` massivos do OpenAPI/Swagger localmente e os compila para **TooN** (Token-Optimized Notation) — uma gramática tática e altamente comprimida. Ao transferir o peso do processamento de JSON, desserialização cíclica de `$ref` e resoluções encadeadas para scripts Python locais, o **TooN OpenAPI Agent reduz o consumo de tokens na IA em até ~90%**, mantendo o agente perfeitamente ciente de toda a estrutura da API.

Este agente está publicado no **Anthropic Marketplace** e pode ser instalado diretamente em qualquer projeto Claude Code.

## Como Funciona

Uma vez instalado, o agente ganha todas as capacidades abaixo — ativadas por linguagem natural, sem precisar conhecer os internos:

| O que você diz | O que o agente faz |
|---|---|
| Fornecer URL ou arquivo OpenAPI/Swagger | Ingere e compila a API em notação TooN |
| "Como chamo o POST /users?" / "Gera um cliente Go" | Consulta o contrato e gera código de integração |
| "Gera o cliente TypeScript completo" / "Gera só o método POST /orders" | Gera cliente HTTP para toda a API ou um único endpoint |
| "Gera testes pytest para todos os endpoints" | Gera suíte de testes de integração |
| "Valida esse JSON contra o contrato" | Valida o payload contra o schema ingerido |
| "Compara essa API com a v2 que acabei de ingerir" | Faz diff entre duas versões e aponta breaking changes |
| "Exporta o contexto TooN para usar em outra thread" | Gera bloco compacto e auto-explicativo |

---

## Instalação

### Pelo Anthropic Marketplace

Busque por **TooN OpenAPI Agent** no Anthropic Marketplace e clique em **Instalar**. O Claude Code configurará o agente automaticamente no seu projeto.

### Instalação Manual

**1. Clone este repositório:**

```bash
git clone https://github.com/rafaellemes/toon-openapi-agent
```

**2. Copie a definição do agente para o seu projeto:**

```bash
cp toon-openapi-agent/agents/toon-openapi-agent.md seu-projeto/.claude/agents/
```

**3. Copie a skill para o seu projeto:**

```bash
cp -r toon-openapi-agent/skills/skill-toon-openapi seu-projeto/.claude/skills/toon-openapi
```

**4. Instale as dependências Python (da raiz do seu projeto ou de um venv compartilhado):**

```bash
pip install -r seu-projeto/.claude/skills/toon-openapi/requirements.txt
```

Pronto. O Claude Code carregará o agente e a skill automaticamente na próxima sessão.

---

## Exemplos de Uso

### 1. Ingerindo uma API (Via URL ou Arquivo Local)

Em vez de colar o JSON gigante no chat, basta dizer para o agente:

> *"Faça o ingest da API disponível em https://fakerestapi.azurewebsites.net/swagger/v1/swagger.json"*
> *(Você também pode mapear um arquivo local: `./downloads/minha_api.yaml`)*

O agente processa tudo localmente e armazena o mapeamento em `.toon_apis/apis/fakerestapiweb-v1/`. Ele responde no chat apenas com o extrato ultraleve (~500 tokens):

```text
[API: fakerestapiweb-v1 | BASE: ]
---
GET   /api/v1/Authors -> getApiV1Authors |  [Authors]
POST  /api/v1/Authors -> postApiV1Authors |  [Authors]
  Req: body.id:i? body.idBook:i? body.firstName:s? body.lastName:s?
  Res: 200 (body.id:i? body.idBook:i? body.firstName:s? body.lastName:s?)
---
20 operações | Namespace: fakerestapiweb-v1

[toon-openapi] API mapeada. Você pode pedir:
  → detalhes de endpoint ou código de integração  (ex: "como chamo esse endpoint?" / "gera cliente Go")
  → cliente HTTP ou SDK — API inteira ou endpoint  (ex: "gera classe TypeScript completa" / "gera só o método POST /orders")
  → testes de integração                          (ex: "gera testes pytest para esse endpoint")
  → validação de payload                          (ex: "valida esse JSON contra o contrato")
  → diff com outra versão                         (ex: "compara com a v2 que acabei de ingerir")
  → exportar contexto para outra thread           (ex: "exporta o bloco TooN desta API")
```

### 2. Gerando Códigos e Testes

Com a API ingerida, basta pedir em linguagem natural — o agente cuida do resto:

> *"Gera o cliente Python completo para essa API."*
> *"Gera apenas o método para o POST /authors."*
> *"Gera a suíte de testes pytest para todos os endpoints."*

O agente lê de `.toon_apis/apis/` automaticamente e entrega código livre de alucinações — para toda a API ou um único endpoint.

### 3. Comparador de Versões (Diff)

> *"Compara essa API com a v2 que acabei de ingerir."*

O agente compara as duas versões e reporta quais rotas foram adicionadas, removidas ou tiveram breaking changes nos parâmetros — classificadas como 🔴 BREAKING, 🟢 NON-BREAKING, 🟡 ATENÇÃO ou ⚪ INFO.

### 4. Validando um Payload

> *"Valida esse JSON contra o contrato do POST /users."*

O agente executa o payload contra o schema ingerido e reporta erros, avisos e informações — sem fazer requisições de rede.

---

## Storage

Todos os dados processados ficam em `.toon_apis/` na raiz do seu projeto (criado automaticamente no primeiro ingest):

```
.toon_apis/
├── apis/
│   └── <namespace>/
│       ├── toon.txt       ← visão semântica (lida pelo agente)
│       ├── mapping.json   ← contrato técnico (consultado via jq)
│       └── metrics.json   ← histórico de uso de tokens
├── diffs/
├── exports/
├── tests/
├── clients/
└── validations/
```

`.toon_apis/` é excluído do git por padrão via `.toon_apis/.gitignore`.

---

## Rodando os Testes (para desenvolvedores da skill)

```bash
cd skills/skill-toon-openapi/
pip install -r requirements.txt
pytest tests/test_unit.py tests/test_diff.py tests/test_validate.py tests/test_clientgen.py tests/test_testgen.py tests/test_exportgen.py tests/test_multi.py -v
```

---

## Licença

Este projeto está sob a licença [MIT](LICENSE).
