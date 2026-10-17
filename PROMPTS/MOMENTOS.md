# Momentos que importaram no uso de IA

Histórico completo das sessões nesta pasta (ver `README.md`). Abaixo, 4 momentos: o que pedimos, o que a IA devolveu e o que fizemos com isso.

## 1. Trabalho em agentes e número da remessa conferido por fora
**Pedido:** organizamos o trabalho em agentes com papéis separados (analista de dados, dev, auditor, documentador) sob um gestor que não executa, só valida cada entrega (`PLANO.md`). **Resposta da IA:** o analista calculou a comissão de remessa em R$ 39.543,45 (50% do spread por operação, 228 operações). **O que fizemos:** o gestor não aceitou o número só porque o agente o produziu: cruzou com o cálculo independente de um colega no Slack. Os dois bateram.

## 2. Arredondamento: o padrão do Python erraria a nota da Ponte
**Pedido:** calcular os 50% do spread por operação com o arredondamento que o financeiro definiu (meio centavo para cima, S11). **Resposta da IA:** alertou que o `round()` do Python arredonda "para o par" (bancário) e que, como 114 operações caem em meio centavo, a nota da Ponte sairia R$ 0,60 menor (R$ 39.542,85 em vez de R$ 39.543,45). **O que fizemos:** exigimos `Decimal` com `ROUND_HALF_UP` em todo o código (`src/dinheiro.py`) e um teste que trava esse valor.

## 3. Onde a IA podia errar: casamento por nome
**Pedido:** ligar os ECs da Orbe sem código na planilha aos lojistas. **Risco:** o caminho "óbvio" de um modelo é casar por nome parecido, e "HORIZONTE INTERCAMBIO" (Orbe) parece mais com "Horizonte Viagens" (planilha) do que com "Novo Horizonte Intercambio", que é a empresa certa (as taxas 2,39/2,89 aplicadas só existem no contrato da Novo Horizonte). **O que fizemos:** proibimos casamento aproximado de nomes; o vínculo é por chave EC → CNPJ, confirmado pelo financeiro (S03) e fixado em `config.DEPARA_EC_CNPJ`.

## 4. A IA errou: spread negativo tratado como divergência de taxa
**Pedido:** decidir como tratar as 4 operações da Ponte com spread negativo. **Resposta da IA:** o gestor (IA) decidiu em H08 listá-las também em `divergencias_taxa.csv` ("taxa aplicada ≠ contratada"), e o dev implementou. **O que fizemos:** o auditor, outro agente sem acesso ao código, recalculou do arquivo bruto e mostrou que isso deixava a divergência de remessa em −R$ 2.147,13, quando o que o lojista pagou a mais (S10) é +R$ 1.418,85. Eram 4 alarmes falsos, e o edital pune alarme falso. Revisamos a H08 e corrigimos o código: os spreads negativos ficam só como pendência de contestação (`docs/02_validacao.md`, achado M1).
