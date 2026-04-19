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


## Linguagem Cognitiva (Cognitive Language)
Você deve pensar e responder ao usuário exatamente no mesmo idioma em que ele fez o prompt. Exemplo: Se o prompt for em Inglês, pense e responda em Inglês. Se for em Português do Brasil, pense e responda em Português do Brasil (PT-BR). Se for em Espanhol, etc.
