---
name: clientgen-api
description: >
  Extrai contrato estruturado da API para o LLM gerar cliente HTTP em
  qualquer linguagem. Ativar ao pedir "cliente HTTP", "SDK", "wrapper
  da API", ou código para rota a encaixar em classe existente.
---

# Geração de Cliente HTTP

## Princípio
O script extrai o contrato. O LLM gera o código.
Sem restrição de linguagem ou framework.

## Lógica de estrutura
1. Pedido explícito ("standalone", "nova classe") → seguir
2. Arquivo/classe aberta na thread → standalone
3. Sem contexto, rota única → classe com um método
4. Sem contexto, API completa/tag → classe completa

## Fluxo
0. Resolver linguagem/padrão do contexto (ou perguntar).
1. `cat .toon_apis/apis/<ns>/toon.txt` — identificar escopo.
2. Extrair contrato:
   - Completo: `python .claude/skills/toon-openapi/scripts/clientgen/extract_contract.py <ns>`
   - Por tag:  `python .claude/skills/toon-openapi/scripts/clientgen/extract_contract.py <ns> --tag <tag>`
   - Por rota: `python .claude/skills/toon-openapi/scripts/clientgen/extract_contract.py <ns> --operation <opId>`
3. Gerar código idiomático com base no contrato.
4. Retornar para thread principal + salvar em .toon_apis/clients/.

## Regras
- NUNCA inventar campos não presentes no contrato.
- [obrigatório] → sem default | [opcional] → com default nulo.
- Código idiomático — sem restrição de linguagem.
- `python .claude/skills/toon-openapi/scripts/consult/log_metrics.py <ns> <tokens> clientgen`

## ⚠️ Constraints DEVEM ser IMPOSTAS no código (não apenas comentadas)

O contrato traz constraints (`enum`, `pattern`, `min`/`max`, `minLength`/`maxLength`,
`multipleOf`, `format`, obrigatoriedade). O código gerado **DEVE validar essas constraints
client-side ANTES de enviar a requisição** — falhar cedo, localmente. Comentário descrevendo
a constraint **não basta**.

**Motivo:** disparar uma chamada que já se sabe inválida gasta uma requisição do *bucket* de
rate-limit da API (crítico em APIs como o Pix) e desperdiça latência para receber um 400 certo.

Aplicação por stack:
- **Spring Boot / Java com Bean Validation:** anotar o modelo com Jakarta Validation —
  `@NotNull`/`@NotBlank` (obrigatório), `@Size(min,max)` (minLength/maxLength), `@Pattern(regexp=...)`
  (pattern), `@Min`/`@Max` ou `@DecimalMin`/`@DecimalMax` (min/max), `@Valid` em campos aninhados,
  e `enum` Java para `enum`. Validar (`@Valid` no controller ou `Validator.validate(...)`) ANTES
  de chamar a API.
- **Java puro / sem framework:** guardas explícitas que lançam `IllegalArgumentException` antes
  de montar/enviar (ex.: `Objects.requireNonNull`, checagem de tamanho, `Pattern.matches(regex, v)`,
  `enum` Java, verificação de faixa numérica).
- **Outras linguagens:** equivalente idiomático que imponha a constraint antes da chamada HTTP
  (ex.: Pydantic/dataclass validators em Python, Zod/class-validator em TS, `validator` em Go).
- **Enums:** modelar como tipo/enum de primeira classe sempre que a linguagem suportar.
- Após gerar, validar o payload de exemplo com `validate_payload.py` (ver SKILL.md).


## Linguagem Cognitiva (Cognitive Language)
Você deve pensar e responder ao usuário exatamente no mesmo idioma em que ele fez o prompt. Exemplo: Se o prompt for em Inglês, pense e responda em Inglês. Se for em Português do Brasil, pense e responda em Português do Brasil (PT-BR). Se for em Espanhol, etc.
