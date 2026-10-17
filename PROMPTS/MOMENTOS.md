# Momentos que importaram no uso de IA

Histórico completo das sessões nesta pasta (ver `README.md`). Abaixo estão 4 momentos, e em todos a IA errou ou poderia ter errado. Para cada um: o que pedimos, o que a IA devolveu e o que fizemos.

## 1. A IA errou: spread negativo tratado como divergência de taxa
**Pedido:** decidir como tratar as 4 operações da Ponte com spread negativo. **O que a IA devolveu:** o gestor (IA) decidiu listá-las em `divergencias_taxa.csv` ("taxa aplicada ≠ contratada"), e o dev implementou. **O que fizemos:** o auditor recalculou a partir do arquivo bruto e mostrou que isso gerava 4 alarmes falsos, porque o lojista não pagou a mais (S10). Corrigimos a H08 e o código (`docs/02_validacao.md`, M1). Depois a Helena confirmou: spread negativo é contestação, de outra natureza (S25, regra R53).

## 2. O prompt de investigação entregava a resposta
**Pedido:** escrever o prompt da IA de investigação de divergências. **O que a IA devolveu:** a v1 usava como exemplo de tom o caso real da Rota (+0,50 p.p. desde 12/09), e com isso vazaria a resposta para o modelo. **O que fizemos:** o gestor pegou na revisão. Trocamos por um exemplo fictício (Escola Farol, IDs FX#) e criamos o teste `test_prompt_nao_contem_casos_de_setembro`, que falha se algum caso de setembro voltar ao prompt.

## 3. O gestor (IA) afirmou um fato errado; o dado corrigiu
**Pedido:** o gestor (IA) pediu ao dev um dossiê em que a Rota aparecia divergente também no débito. **O que a IA devolveu:** o dev calculou a partir do relatório da Orbe e viu que o débito da Rota seguiu a taxa contratada. Só as 3 faixas de crédito divergem. **O que fizemos:** o dossiê saiu com o fato calculado, e não com o que estava no pedido. Os fatos vêm do dado, nunca do pedido.

## 4. A IA escolheu como principal uma hipótese que um fato citado por ela contradizia
**Pedido:** levantar hipóteses de causa para a Rota (primeira execução real, antes do prompt v3). **O que a IA devolveu:** como principal, "a Orbe voltou à tabela de 2025". Mas o fato que ela mesma citou mostrava que a aba 2025 não explica o 7–12x (4,09%), nem o débito, nem o Pix. **O que fizemos:** o auditor apontou o problema (`docs/04_validacao_ia.md`, M1/M2). Completamos o fato no dossiê, criamos o prompt v3 com teste de contradição e `fatos_contrarios`, e um guarda-corpo que rebaixa "alta" com fato contrário. Na execução 3, a principal virou "alteração de cadastro do EC na Orbe" e a tabela 2025 caiu para baixa, com os fatos contrários citados (`docs/exemplo_investigacao_ia.md`).

## Outros registros
- **Arredondamento:** a IA alertou que o `round()` do Python arredonda para o par. Com 114 operações em meio centavo, a nota da Ponte sairia R$ 0,60 menor (R$ 39.542,85 em vez de R$ 39.543,45). Exigimos `Decimal` com `ROUND_HALF_UP` (`src/dinheiro.py`) e um teste que trava o valor.
- **Casamento por nome proibido:** "HORIZONTE INTERCAMBIO" (Orbe) parece mais com "Horizonte Viagens" do que com a Novo Horizonte, que é a empresa certa. O vínculo é só por EC → CNPJ (S03, `config.DEPARA_EC_CNPJ`).
- **Número conferido por fora:** a comissão de remessa calculada pelo agente analista (R$ 39.543,45) só foi aceita depois de bater com o cálculo independente de um colega no Slack.
- **Ajuste tardio da Orbe (17/10):** o arquivo de 14 ajustes (`06_orbe_ajustes_tardios_set2026.csv`) foi analisado por um agente e implementado por outro, de forma independente; os totais bateram ao centavo (checkout R$ 203.735,34, notas R$ 203.740,84) antes de qualquer número ir para `saida/`.
