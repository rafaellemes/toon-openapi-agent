---
name: validate-api
description: >
  Valida payload JSON contra contrato de endpoint ingerido. Validação
  recursiva até 3 níveis (configurável). Ativar ao pedir "validar",
  "checar", "verificar" payload. Também usada internamente pelo
  consult-api após gerar código.
---

# Validação de Payload

## Modos
- **Manual**: `python .claude/skills/toon-openapi/scripts/validate/validate_payload.py <ns> <opId> '<json>'`
- **Manual arquivo**: adicionar `--file <path>`
- **Profundidade**: adicionar `--depth N` (padrão: 3)
- **Automático**: chamado pelo consult-api pós-geração

## Classificação
🔴 ERRO = inválido | 🟡 AVISO = campo extra | ⚪ INFO = além da profundidade

## Fluxo automático (consult-api)
1. Extrair payload do snippet gerado.
2. Validar. Se inválido → corrigir e revalidar (máx. 2x).
3. Nunca entregar código com payload inválido.

## Output
- Terminal + .toon_apis/validations/
- Exit: 0=válido, 1=inválido, 2=erro


## Linguagem Cognitiva (Cognitive Language)
Você deve pensar e responder ao usuário exatamente no mesmo idioma em que ele fez o prompt. Exemplo: Se o prompt for em Inglês, pense e responda em Inglês. Se for em Português do Brasil, pense e responda em Português do Brasil (PT-BR). Se for em Espanhol, etc.
