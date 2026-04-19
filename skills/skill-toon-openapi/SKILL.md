---
name: toon-openapi
description: >
  Toolkit para ingestão e consulta de APIs OpenAPI/Swagger em notação TooN compacta.
  Reduz consumo de tokens em até 90%. Ativar ao receber URL ou arquivo de API,
  perguntas sobre endpoints, pedidos de código de integração, diff entre versões,
  validação de payload, geração de testes ou exportação de contexto.
version: 1.0.0
---

# TooN_OpenApi — Contexto Global do Agente

## ⚠️ Regra de Ativação

Para QUALQUER tarefa relacionada a APIs — perguntas sobre endpoints, geração de
código, testes, validação de payload, diff, exportação ou consulta — a
**sessão/agente principal DEVE ativar esta skill** antes de responder.
**PROIBIDO responder diretamente sem passar pela skill.**

| Pedido do usuário | Sub-skill a usar |
|---|---|
| "como chamo esse endpoint?" / "gera código" | consult-api |
| "gera um cliente HTTP / SDK" | clientgen-api |
| "quais endpoints existem?" | consult-api |
| "gera testes para X" | testgen-api |
| "o que mudou nessa API?" / "compara versões" | diff-api |
| "valida esse payload" | validate-api |
| "exporta o contexto" | exportgen-api |

---

## Sub-Skills Disponíveis

Antes de executar qualquer sub-skill, leia o arquivo `.md` correspondente em `scripts/`:

| Sub-skill | Arquivo de instruções | Ativar quando |
|-----------|----------------------|---------------|
| **ingest-api** | `.claude/skills/toon-openapi/scripts/ingest/ingest-api.md` | URL ou arquivo OpenAPI/Swagger fornecido |
| **consult-api** | `.claude/skills/toon-openapi/scripts/consult/consult-api.md` | Perguntas sobre API ingerida, geração de código |
| **diff-api** | `.claude/skills/toon-openapi/scripts/diff/diff-api.md` | "diff", "comparar versões", "o que mudou" |
| **validate-api** | `.claude/skills/toon-openapi/scripts/validate/validate-api.md` | "validar payload", "checar JSON" |
| **testgen-api** | `.claude/skills/toon-openapi/scripts/testgen/testgen-api.md` | "gerar testes", "criar testes de integração" |
| **exportgen-api** | `.claude/skills/toon-openapi/scripts/export/exportgen-api.md` | "exportar", "gerar bloco TooN", "injetar contexto" |
| **clientgen-api** | `.claude/skills/toon-openapi/scripts/clientgen/clientgen-api.md` | "cliente HTTP", "SDK", "wrapper da API" |

---

## Arquitetura de Storage

- A pipeline isola os dados processados das rotinas operacionais no diretório raiz do
  projeto consumidor, sob namespace específico.
- `.toon_apis/apis/<namespace>/toon.txt`: descoberta rápida — lido pelo LLM no início
  para entender o que a API faz (rico com nós de Requisições, Respostas e varredura de
  Arrays em payloads `body:a!`).
- `.toon_apis/apis/<namespace>/mapping.json`: dados técnicos exatos — usado de forma
  granular, lido via `jq`.

### Como Gerar e Ler o Toon

1. **Para Criar (Ingerir API):**
   Rode os scripts em cascata (substituindo pela URL/Arquivo da API):
   ```bash
   python .claude/skills/toon-openapi/scripts/ingest/parse_spec.py <API_URL> > /tmp/spec.json
   python .claude/skills/toon-openapi/scripts/ingest/transform_toon.py /tmp/spec.json
   ```
   *(Isso criará a estrutura isolada sob `.toon_apis/apis/<namespace>/`)*

2. **Para Ler/Consultar:**
   Leia primeiramente o arquivo semântico:
   ```bash
   cat .toon_apis/apis/<namespace>/toon.txt
   ```
   Em seguida pesquise a operação final usando `jq` no `mapping.json`:
   ```bash
   jq '.<operationId>' .toon_apis/apis/<namespace>/mapping.json
   ```

### Referência Rápida: Gramática TooN

Ao analisar o arquivo `toon.txt`, utilize este glossário de decodificação:

- **Métodos**: `GET`, `POST`, `PUT`, `DEL`, `PATCH`, `HEAD`, `OPT`
- **Tipos de Dado**: `s`=string, `i`=integer, `b`=boolean, `a`=array, `o`=object
- **Marcadores**: `!`=obrigatório, `?`=opcional
- **Prefixos de Parâmetro de Requisição**:
  `q:`=query param · `h:`=header · `c:`=cookie · `f:`=form field (urlencoded/multipart)
  `body.`=campo de body JSON/XML · `body:s`=body texto primitivo · `binary`=upload binário · `stream`=SSE
- **Prefixo de Response Header**: `rh:`=header da resposta

---

## Estratégia de Contexto para Geração de Código

### 1º — Pedido actual (prioridade máxima)
"gera em Go" → usa Go, ignora histórico.

### 2º — Histórico da thread (fallback passivo)
Linguagem, cliente HTTP, padrão, nomenclatura, auth mencionados
anteriormente → aplicar sem precisar repetir.

### 3º — Sem contexto
Perguntar: "Em qual linguagem e com quais convenções?"

### Regra de ouro
Contexto afeta APENAS a forma do código.
Dados técnicos (url, método, params) vêm SEMPRE do `mapping.json`.

---

## Validação Automática Pós-Geração de Código

Após gerar código de integração, SEMPRE:
1. Extrair payload do snippet
2. Chamar `validate_payload.py` contra o mapping
3. Válido → entregar | Inválido → corrigir silenciosamente (máx. 2x)

---

## Regras Globais

1. NUNCA inventar campos, params ou endpoints não presentes no mapping.
2. NUNCA `cat` do `mapping.json` completo — sempre `jq` cirúrgico.
3. SEMPRE resolver contexto antes de gerar código.
4. SEMPRE validar payload gerado antes de entregar.
5. SEMPRE informar custo estimado em tokens.
6. Se endpoint não existir no `toon.txt` — declarar e listar disponíveis.
7. Se um namespace faltar em `.toon_apis/apis/` — instruir a usar ingest-api.
8. Em multi-namespace — NUNCA misturar params ou endpoints de APIs distintas.
9. NUNCA usar dados de toon ou mapping que estejam apenas na memória da conversa —
   SEMPRE ler do disco via cat/jq/scripts antes de responder. O contexto de
   conversa pode estar desatualizado. A Sessão/Agente principal que precisar
   desses dados deve invocar a skill — NUNCA executar cat/jq diretamente.

---

## Auth da Spec

O campo `AUTH:` no `toon.txt` e o campo `security` no `mapping.json` são populados
automaticamente pelo `transform_toon.py` a partir dos `securitySchemes` da spec.
O agente deve usar esses dados para gerar código com autenticação correta sem que
o dev precise declarar na thread.

Prioridade: auth declarada na thread > auth da spec > placeholder comentado.

---

## Geração de Cliente HTTP (clientgen-api)

### Lógica de estrutura
1. Pedido explícito ("standalone", "nova classe") → seguir
2. Arquivo/classe aberta na thread → standalone
3. Sem contexto, rota única → classe com um método
4. Sem contexto, API completa/tag → classe completa

### Responsabilidade
O script extrai o contrato. O LLM gera o código.
Sem restrição de linguagem ou framework.

---

## Caminhos de Storage

```
toon.txt:    .toon_apis/apis/<namespace>/toon.txt
mapping:     .toon_apis/apis/<namespace>/mapping.json
metrics:     .toon_apis/apis/<namespace>/metrics.json
diffs:       .toon_apis/diffs/diff_<base>_vs_<target>_<ts>.txt
validations: .toon_apis/validations/validation_<op>_<ts>.txt
tests:       .toon_apis/tests/<ns>_<op>_<lang>_<ts>.<ext>
clients:     .toon_apis/clients/<ns>_<scope>_<lang>_<ts>.<ext>
exports:     .toon_apis/exports/<ns>_<scope>_<ts>.txt  (apenas com --save)
```

---

## Linguagem Cognitiva (Cognitive Language)

Você deve pensar e responder ao usuário exatamente no mesmo idioma em que ele fez o
prompt. Exemplo: Se o prompt for em Inglês, pense e responda em Inglês. Se for em
Português do Brasil, pense e responda em Português do Brasil (PT-BR). Se for em
Espanhol, etc.
