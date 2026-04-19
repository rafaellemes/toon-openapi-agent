---
name: exportgen-api
description: >
  Exporta um bloco TooN compacto pronto para colar em qualquer thread,
  system prompt ou contexto de outro agente. Ativar ao pedir "exportar
  contexto da API", "gerar bloco TooN", "injetar contexto em outra
  thread", "copiar spec para usar em outro agente".
---

# Exportação de Contexto TooN

## Propósito
Gerar um bloco auto-explicativo que qualquer LLM entende sem precisar
ingerir a spec OpenAPI. O receptor usa o bloco para raciocinar sobre
a API diretamente na sua thread.

## Fluxo

1. `cat .toon_apis/apis/<ns>/toon.txt` — verificar que a API foi ingerida.
2. Executar:
   ```bash
   # Compacto (padrão)
   python .claude/skills/toon-openapi/scripts/export/export_context.py <ns>

   # Com parâmetros inline
   python .claude/skills/toon-openapi/scripts/export/export_context.py <ns> --params

   # Por tag
   python .claude/skills/toon-openapi/scripts/export/export_context.py <ns> --tag pet

   # Por operação
   python .claude/skills/toon-openapi/scripts/export/export_context.py <ns> --operation addPet

   # Salvar arquivo além de imprimir
   python .claude/skills/toon-openapi/scripts/export/export_context.py <ns> --save
   ```
3. Apresentar o bloco na thread principal — o dev copia.

## Regras
- Output **sempre** no terminal — o dev decide o que fazer com ele.
- `--save` é opt-in — nunca salvar por padrão.
- Bloco deve ser compacto — sem JSON, sem mapping exposto.
- Incluir sempre a dica de uso no rodapé.
- Métricas: `python .claude/skills/toon-openapi/scripts/consult/log_metrics.py <ns> <tokens> export`


## Linguagem Cognitiva (Cognitive Language)
Você deve pensar e responder ao usuário exatamente no mesmo idioma em que ele fez o prompt. Exemplo: Se o prompt for em Inglês, pense e responda em Inglês. Se for em Português do Brasil, pense e responda em Português do Brasil (PT-BR). Se for em Espanhol, etc.
