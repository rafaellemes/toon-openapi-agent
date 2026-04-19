---
name: ingest-api
description: >
  Converte especificações OpenAPI (Swagger) para notação TooN compacta.
  Ativar quando o usuário fornecer URL de API, arquivo .json/.yaml,
  ou usar palavras como "ingerir", "carregar", "mapear", "converter" API.
---

# Ingestão de API

## Fluxo

1. Parse: `python .claude/skills/toon-openapi/scripts/ingest/parse_spec.py <fonte> > /tmp/spec.json`
   - Se contiver `"error"` → parar e informar o usuário.
2. Transform: `python .claude/skills/toon-openapi/scripts/ingest/transform_toon.py /tmp/spec.json`
3. Apresentar APENAS: bloco TooN, namespace, nº operações, confirmação.

## Regras
- Nunca expor mapping.json ou JSON bruto na conversa.
- Em erro de rede → sugerir arquivo local.
- Sem operationId → informar que IDs foram gerados automaticamente.
- Sem servers → informar que BASE não foi definida.


## Linguagem Cognitiva (Cognitive Language)
Você deve pensar e responder ao usuário exatamente no mesmo idioma em que ele fez o prompt. Exemplo: Se o prompt for em Inglês, pense e responda em Inglês. Se for em Português do Brasil, pense e responda em Português do Brasil (PT-BR). Se for em Espanhol, etc.
