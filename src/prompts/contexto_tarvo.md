# Contexto da Tarvo (para a IA de investigação)

## A empresa
- A Tarvo é uma subadquirente para escolas de idiomas e agências de intercâmbio (os "lojistas").
- Duas linhas de negócio, cada uma com um parceiro:
  - CHECKOUT: pagamentos processados pela **Orbe** (adquirente). Cada lojista tem um código EC na Orbe.
  - REMESSA: câmbio operado pela **Ponte Câmbio**. A Tarvo fica com 50% do spread realizado.
- A taxa contratada de cada lojista está na planilha de taxas (aba vigente). A planilha é a única
  fonte de contrato e é mantida por quem não decide taxa (S38).

## Como o dinheiro chega ao lojista (S34, S16)
- A Orbe liquida o **valor líquido**: a taxa já sai descontada no pagamento ao lojista.
- Se o parceiro cobrou taxa maior que a contratada, o lojista **já recebeu a menos**.
  Toda divergência é, portanto, dinheiro a devolver ao lojista.

## Divergência de taxa (R13, R22, S19, S24)
- Divergência = o lojista pagou taxa/spread diferente do contratado (a mais ou a menos).
- Checkout: valor = valor bruto × (taxa aplicada − contratada), linha a linha.
- Remessa: valor cheio que o lojista pagou a mais = (spread % aplicado − contratado) × PTAX × valor em moeda.
- Truncamento de centavos da Orbe não é divergência (R02).
- Spread contratado em branco ou "padrão" na remessa = 1,5% (R21).

## Duas naturezas, dois destinos
- **CONTRATO**: o parceiro aplicou algo diferente do que lhe foi informado.
  Destino: devolver ao lojista **e** recuperar do parceiro (cobrar a Orbe ou contestar com a Ponte).
- **ISENCAO_NAO_INFORMADA**: a Tarvo concedeu uma condição (ex.: isenção) e não avisou o parceiro;
  o parceiro cobrou certo pelo que sabia. Destino: **só devolver ao lojista**; não há o que cobrar
  do parceiro (S18, S37).
- Mundo Aberto é caso de fronteira: também não foi avisada à Ponte (S30), mas a Helena decidiu
  tratar como divergência e contestar (S05).

## Causa raiz frequente (S30)
- Ninguém tem a função de avisar a Orbe e a Ponte de condições novas. O Comercial fecha e, quando
  lembra, manda e-mail. A Bridge foi avisada alguns dias depois de 15/09; Casa do Estudante e
  Mundo Aberto não foram avisadas.

## Papéis (S32, S33, S38)
- **Helena** (financeiro): confere, decide exceções e fala com Comercial, Orbe e Ponte.
  Devolver ao lojista e cobrar/contestar o parceiro é decisão dela, caso a caso.
- **Comercial**: fecha e aprova taxa e condição comercial; decide cadastro e contrato.
- **Bia**: mantém a planilha de taxas e o checkout, mas não decide taxa.
- **Caio**: bancos e remessas.

## Contatos possíveis para "falar com"
- Orbe: taxa cadastrada/aplicada no checkout.
- Ponte: spread aplicado na remessa.
- Comercial: o que foi negociado, quando e se o parceiro foi avisado.
- Lojista: confirmar o que ele recebeu ou o que combinou.
