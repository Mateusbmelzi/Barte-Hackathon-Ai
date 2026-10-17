# Contexto da empresa: Tarvo Pagamentos

Camada 1 do conhecimento: o que a Tarvo é e como o fechamento funciona hoje. Só fatos, cada um com a fonte (S## = `docs/00_slack_respostas_financeiro.md`). As regras estão em `REGRAS_DE_NEGOCIO.md` e as premissas em `HIPOTESES.md`.

## Negócio e linhas
A Tarvo intermedeia pagamentos para lojistas (escolas de idiomas e agências de intercâmbio). Tem duas linhas de receita:
- **Checkout (cartão e Pix), com a adquirente Orbe.** A Tarvo ganha a taxa inteira contratada com o lojista (MDR e antecipação), sem descontar custo da Orbe (S01, S17).
- **Remessa internacional, com a Ponte Câmbio.** A Tarvo ganha 50% do spread realizado em cada operação (S05).

## Parceiros e sistemas
Orbe (adquirente, relatório mensal por transação), Ponte Câmbio (parceiro de câmbio, relatório mensal por e-mail), banco Aurora (conta principal, cc 4471), banco Meridiano (conta das remessas, cc 90233), ERP Fênix (plano de contas). A planilha de taxas contratadas é mantida à mão.

## Fluxo do dinheiro
- **Checkout:** a Orbe deposita tudo no Aurora, nunca paga o lojista direto. Débito e Pix em D+1; crédito e parcelado ao longo dos meses. Saldo negativo do Aurora usa a conta garantida (S16). A Orbe liquida o valor líquido: a taxa já sai descontada, e o lojista a vê no extrato de repasse. A nota fiscal só documenta essa taxa; não é cobrança nova. Se a Orbe cobra a mais, o lojista já recebeu a menos e a Tarvo precisa devolver (S34).
- **Repasse ao lojista:** duas vezes por mês, perto dos dias 10 e 24, sobre o que a Orbe já liquidou. A regra está no contrato de adesão (S35).
- **Remessa:** o lojista manda PIX ao Meridiano, a Tarvo paga a Ponte por TED, e a Ponte repassa a participação da Tarvo no mês seguinte (S08, S14).

## Pessoas e papéis
| Quem | Papel |
|---|---|
| Helena (financeiro) | Confere e aprova o fechamento, decide exceções, fala com Comercial, Orbe e Ponte. Aprova as regras de fechamento (S32, S33). |
| Bia (analista) | Checkout e manutenção da planilha de taxas; não decide taxa (S33, S38). |
| Caio (analista) | Bancos e remessas (S33). |
| Comercial | Fecha e aprova taxas e condições; decide cadastro e contrato (S32, S38). |

## Processo atual e onde vão os ~8 dias (S33)
Sequência: baixar Orbe, e-mail da Ponte e extratos → casar a Orbe com a planilha e calcular a comissão → remessa → classificar extratos no ERP → notas. O controle é uma aba da planilha com "ok" e data.
| Etapa | Tempo | Para onde vai o tempo |
|---|---|---|
| Comissão checkout | ~3 dias | metade casando nome com EC/CNPJ; metade retrabalho por planilha desatualizada |
| Remessa | ~2 dias | maior parte esperando Ponte ou Comercial |
| Extratos | ~2 dias | classificação manual, linha a linha |
| Notas e revisão | último dia | — |

## Dores e causa raiz
**Princípio: o contrato decide quem deve, não o aviso (S41).** Quando o parceiro cobra fora de aditivo ou condição registrada (Bridge, Mundo Aberto), é divergência de contrato e a Helena cobra o parceiro; quando o Comercial dá uma concessão fora do contrato (Casa do Estudante), o parceiro cobrou o contratado e a devolução ao lojista sai do bolso da Tarvo. O aviso atrasado é problema de processo.

1. **Ninguém avisa os parceiros das condições novas.** O Comercial fecha e, quando lembra, manda e-mail. A Bridge foi avisada dias depois de 15/09; Casa do Estudante e Mundo Aberto não foram avisadas (S30). Resultado: parceiro cobrando fora do contrato o mês inteiro.
2. **A planilha de taxas é a única fonte e está desatualizada**, mantida por quem não decide taxa (S33, S38).
3. **O conhecimento está em uma pessoa.** Quase tudo o que descobrimos no canal estava só na cabeça da Helena; nas férias dela ninguém fecha (S32, S33).

## Fora do escopo do fechamento
- **Provisão de setembro:** a contabilidade faz com a Helena; o fechamento só classifica o que passou nos extratos (S49).

## Riscos observados fora do escopo do fechamento
- **Repasse antecipado pela conta garantida sem regra nem limite:** na prática a Bia às vezes paga o lojista antes da liquidação da Orbe, usando a conta garantida (S35).
- **Antecipação sem trava:** a Atlas antecipou mais do que vendeu, sem contrato vigente (S23).
