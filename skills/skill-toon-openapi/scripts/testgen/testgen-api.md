---
name: testgen-api
description: >
  Gera testes de integração automatizados para endpoints. Ativar ao
  pedir "gerar testes", "criar testes de integração". Respeita
  linguagem e framework declarados na thread.
---

# Geração de Testes

## Fluxo
0. Resolver linguagem/framework do contexto (ou perguntar).
1. `cat .toon_apis/apis/<ns>/toon.txt` — identificar operationId.
2. `python .claude/skills/toon-openapi/scripts/testgen/generate_tests.py <ns> <opId> <lang> [<framework>]`
3. Testes exibidos + gravados em .toon_apis/tests/.

## Cenários gerados
- Happy path — sempre
- Campo obrigatório ausente — se houver param com `!`
- Não encontrado — se endpoint tiver resposta `404`

## Linguagens e frameworks padrão
python/pytest | javascript/jest | typescript/jest |
kotlin/junit5 | go/testing | ruby/rspec

## Métricas
`python .claude/skills/toon-openapi/scripts/consult/log_metrics.py <ns> <tokens> testgen`


## Linguagem Cognitiva (Cognitive Language)
Você deve pensar e responder ao usuário exatamente no mesmo idioma em que ele fez o prompt. Exemplo: Se o prompt for em Inglês, pense e responda em Inglês. Se for em Português do Brasil, pense e responda em Português do Brasil (PT-BR). Se for em Espanhol, etc.
