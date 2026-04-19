---
name: diff-api
description: >
  Compara duas versões de uma API com classificação de breaking changes.
  Ativar com palavras como "diff", "comparar", "o que mudou", "migrar
  de v1 para v2". Fontes: namespace, arquivo local ou URL.
---

# Diff de Especificações

## Fontes suportadas (qualquer combinação)
namespace ↔ namespace | namespace ↔ URL | arquivo ↔ arquivo

## Fluxo
1. Resolver fontes (ingerir se necessário).
2. `python .claude/skills/toon-openapi/scripts/diff/diff_specs.py <base> <target>`
3. Relatório exibido no terminal + gravado em .toon_apis/diffs/.

## Classificação
🔴 BREAKING | 🟢 NON-BREAKING | 🟡 ATENÇÃO | ⚪ INFO

## Regras
- Fontes idênticas → "Nenhuma diferença encontrada."
- Fonte inválida → informar qual falhou.


## Linguagem Cognitiva (Cognitive Language)
Você deve pensar e responder ao usuário exatamente no mesmo idioma em que ele fez o prompt. Exemplo: Se o prompt for em Inglês, pense e responda em Inglês. Se for em Português do Brasil, pense e responda em Português do Brasil (PT-BR). Se for em Espanhol, etc.
