---
name: progresso
description: Relatório de progresso no japonês e correção de rota — compara ritmo real contra o plano, projeta o nível provável no exame e propõe ajustes. Aciona em - /progresso, como estou indo, meu progresso, vou conseguir, relatório, estou no ritmo
---

# /progresso — Relatório e correção de rota

Esta skill responde a uma pergunta só, com honestidade: **no ritmo atual, ele chega no N3 em dezembro de 2027?**

Leia `progresso/estado.json`, `progresso/diario.md` e `plano/roadmap.md`.

---

## Passo 1 — Medir o ritmo real

Calcule, a partir do estado e do diário:

| Métrica | Como |
|---|---|
| Dias corridos desde o início | data de hoje − `inicio_plano` |
| Taxa de adesão | (`sessoes_completas` + `sessoes_parciais` × 0,4) ÷ dias corridos |
| Minutos por dia efetivos | `minutos_acumulados` ÷ dias corridos |
| Horas projetadas até 05/12/2027 | `minutos_acumulados`/60 + (dias restantes × min/dia efetivos ÷ 60) |

Use `date` para a data real. Não estime de cabeça.

## Passo 2 — Projetar o nível

Compare as horas projetadas com as faixas de `plano/roadmap.md`:

| Horas projetadas | Nível provável em dez/2027 |
|---|---|
| < 300h | N5 |
| 300–450h | N4 |
| 450–700h | N4 sólido, N3 arriscado |
| 700–1.000h | N3 provável |
| > 1.000h | N3 confortável |

Some a isso o sinal qualitativo do diário: se `pontos_fracos` cresce sem nunca esvaziar, o problema não é volume de horas, é retenção — e mais horas do mesmo método não resolvem.

## Passo 3 — Apresentar

Formato curto, sem enfeite:

```
## Progresso — [data]

**Ritmo:** X min/dia efetivos · adesão Y% · streak Z (recorde: W)
**Acumulado:** Nh de ~420h planejadas até dez/2027
**Projeção:** Kh até o exame → nível provável [N]

### O que está funcionando
- [1-3 pontos concretos, tirados do diário]

### O que não está
- [1-3 pontos concretos; se não houver, dizer que não há]

### Veredito
[Uma frase direta: está no ritmo do N3, ou não está.]
```

## Passo 4 — Corrigir a rota

Quando a projeção ficar **15% ou mais abaixo** do necessário para a meta declarada, apresente as três saídas reais, com o custo de cada uma. Não escolha por ele:

1. **Aumentar tempo** — de 1h para 1h30/dia. Recupera a meta N3 sem mexer na data. Custo: 30 min/dia a mais, todo dia, pelo resto do plano.
2. **Reduzir escopo** — assumir N4 em dez/2027 e mirar N3 em jul/2028. Custo: mais 7 meses até o objetivo original.
3. **Melhorar eficiência** — se o gargalo for retenção e não horas: mais revisão, menos conteúdo novo, mais produção ativa. Custo: a sensação de "avançar" diminui, ainda que o aprendizado real aumente.

Atualize `pontos_de_decisao` no estado com a escolha e a data.

## Passo 5 — Checar o calendário do exame

Verifique se algum `ponto_de_decisao` vence nos próximos 30 dias e avise. Especialmente:

- **30/08/2026** — fim da inscrição para o exame de dez/2026
- **fev/2027** — a decisão estruturante do plano (subir para 1h30 ou remarcar)
- **mar/2027** e **ago/2027** — janelas de inscrição

Para qualquer data de 2027, lembre que ainda **não** há confirmação oficial: consulte jlpt.org.br antes de tratar como certa.

---

## Regra

Nunca suavize o número. Um relatório que diz "está indo bem" quando a projeção aponta N4 numa meta N3 destrói justamente a função desta skill: dar tempo de reagir enquanto ainda dá.
