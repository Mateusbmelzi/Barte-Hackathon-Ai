"""Parâmetros de negócio do fechamento. Cada um cita a regra (R##, REGRAS_DE_NEGOCIO.md)
ou a hipótese (H##, HIPOTESES.md) que o justifica. Mudou a regra? Mude AQUI, não no código."""
from datetime import date
from decimal import Decimal

# ---------------------------------------------------------------- descoberta de arquivos
# Padrões (glob, sem diferenciar maiúsculas) para achar cada fonte na pasta de entrada.
# Em outubro basta colocar os arquivos novos na pasta: o nome só precisa conter o padrão.
PADROES_ARQUIVOS = {
    "orbe": "*orbe*.csv",
    "taxas": "*taxas*.xlsx",
    "ponte": "*.eml",
    "plano": "*plano_de_contas*.csv",
    "aurora": "*aurora*.csv",
    "meridiano": "*.ofx",
}

# Fontes que podem vir em 1 ou mais arquivos no mesmo mês (a Orbe manda ajustes tardios à parte).
# Os arquivos são lidos todos, em ordem de nome, e concatenados; cada linha guarda o arquivo de origem.
FONTES_MULTIPLAS = {"orbe"}

# ---------------------------------------------------------------- geral
DIVISAO_PCT = Decimal("100")          # taxas vêm em % (2,69 = 2,69%)
QUEM_HELENA = "Helena (Financeiro)"
QUEM_COMERCIAL = "Comercial"
QUEM_RISCO = "Helena (Financeiro) / Comercial"   # B3: cliente não citou área de Risco; S23: alerta p/ Helena e Comercial
QUEM_HELENA_COMERCIAL = "Helena (Financeiro) / Comercial"   # S18: devolução por isenção não informada

# ---------------------------------------------------------------- checkout (Orbe)
# CC04/S03: ECs Orbe sem código na planilha -> CNPJ da linha da aba vigente.
DEPARA_EC_CNPJ = {
    "1043300981": "66564512000199",  # HORIZONTE INTERCAMBIO = Novo Horizonte Intercambio
    "1043396662": "78576234000179",  # HORIZONTE VIAGENS TURISMO = Horizonte Viagens (outra empresa)
    "1038867654": "07752116000126",  # KIWI EXPERIENCE TURISMO = Kiwi Experience
}

# R15/CC05/S03: ECs que NÃO podem ser faturados (sem contrato vigente). Ficam fora de
# comissões e notas e viram pendência para o Comercial. H15: checar risco de antecipação.
ECS_BLOQUEADOS = {
    "1076801732": "Atlas Idiomas: sem contrato na aba vigente; taxa desconhecida (R15/CC05)",
}

# CC01/S07 (tratamento R52): taxa contratada ZERO no checkout (MDR e antecipação) por período.
# Chave = EC Orbe; (início, fim) inclusivos, aplicados à data de referência da taxa
# (venda: data_movimento; estorno: data da venda original - R11/H01).
TAXA_ZERO_CHECKOUT = {
    "1018325654": (date(2026, 9, 1), date(2026, 12, 31)),  # Casa do Estudante
}
# ID da condição contratual (REGRAS_DE_NEGOCIO.md, seção "Condições contratuais vigentes") de cada isenção.
ISENCAO_CONDICAO = {"1018325654": "CC01"}

# R57/S38: a Tarvo não vende acima de 12x; se aparecer, a linha fica fora de comissões/notas e vira pendência.
MAX_PARCELAS = 12

# Dupla reversão: estorno/reversão cujo id_referencia já foi estornado/revertido por outra linha.
# False (padrão) = a 2ª NÃO é aplicada (fica fora de comissões) e vira pendência ORBE_ESTORNO_DUPLICADO
# para o gestor decidir. True = a 2ª é aplicada normalmente (a pendência continua sendo aberta).
APLICAR_ESTORNO_DUPLICADO = False

# H04: Orbe cobrar menos que o contrato também é divergência (valor negativo).
# Comparação exata: as taxas são percentuais com 2 casas; truncamento da Orbe
# no valor_taxa NÃO é divergência (R02), por isso comparamos a TAXA, não o valor.

# ---------------------------------------------------------------- remessa (Ponte Câmbio)
CNPJ_PONTE = "75374179000146"            # R32/S04: tomadora da nota de remessa
NOME_PONTE = "Ponte Câmbio S.A."
PARTICIPACAO_REMESSA = Decimal("0.5")    # R20/S05: 50% do Spread R$ realizado, por operação
SPREAD_PADRAO = Decimal("0.015")         # CC03/S05: célula em branco ou "padrão" = 1,5%
TOLERANCIA_SPREAD = Decimal("0.0001")    # H06/S10: divergência só se |aplicado-contratado| >= 0,01 p.p.
                                         # (fração: 0,01 p.p. = 0,0001)

# ---------------------------------------------------------------- extratos / plano de contas
# R40/S12: conta_codigo = contrapartida do movimento bancário.
# Cada regra: (banco, regex na descrição, conta, referência, confiança, pendência?)
# A primeira que casar vence (ordem importa). pendência = None ou (tipo, motivo, quem_decide).
CONTA_NAO_IDENTIFICADO = "1.1.09.002"    # H12: crédito/lançamento sem regra -> créditos não identificados
REGRAS_EXTRATO = [
    # ---- Aurora
    ("AURORA", r"^TED RECEBIDA .*ORBE", "1.1.03.001", "R43/H18 crédito Orbe = recebível de adquirente", Decimal("1.00"), None),
    ("AURORA", r"^PIX ENVIADO CONTABILIDADE", "4.2.06", "R42 serviço contábil, despesa do mês", Decimal("1.00"), None),
    ("AURORA", r"^PIX ENVIADO ", "2.1.01.001", "H18 repasse a lojista (baixa de repasses a pagar)", Decimal("0.95"), None),
    ("AURORA", r"^TRANSF ENTRE CONTAS", "1.1.09.001", "H13 transferência entre contas próprias", Decimal("1.00"), None),
    ("AURORA", r"^PAGTO SALARIOS", "2.1.04.001", "R41/H14 folha do mês anterior provisionada (baixa do passivo)", Decimal("1.00"), None),
    ("AURORA", r"^PAGTO ISS", "2.1.03.003", "R41/H14 ISS do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"^GPS INSS", "2.1.04.002", "R41/H14 INSS do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"^GRF FGTS", "2.1.04.003", "R41/H14 FGTS do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"DARF 0561", "2.1.03.004", "R41/H14 IRRF (DARF 0561) do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"DARF 8109", "2.1.03.001", "R41/H14 PIS (DARF 8109) do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"DARF 2172", "2.1.03.002", "R41/H14 COFINS (DARF 2172) do mês anterior provisionado", Decimal("1.00"), None),
    ("AURORA", r"CONDOMINIO|ALUGUEL", "4.2.02", "R42 aluguel/condomínio, despesa do mês", Decimal("1.00"), None),
    ("AURORA", r"AMAZON WEB SERVICES", "4.2.03", "R42 cloud, despesa do mês", Decimal("1.00"), None),
    ("AURORA", r"GOOGLE WORKSPACE", "4.2.04", "R42 software/assinatura, despesa do mês", Decimal("1.00"), None),
    ("AURORA", r"^TAR ", "4.2.01", "R42 tarifa bancária, despesa do mês", Decimal("1.00"), None),
    ("AURORA", r"^PIX RECEBIDO .*SEM IDENTIFICACAO", "1.1.09.002", "R44/H12 crédito sem identificação não é receita", Decimal("0.70"),
     ("CREDITO_NAO_IDENTIFICADO",
      "PIX recebido sem identificação do pagador. Não é receita até identificar (R44/S09). Classificado em 1.1.09.002 (H12). Identificar o pagador e reclassificar.",
      QUEM_HELENA)),
    ("AURORA", r"^DEVOLUCAO PIX", "2.1.01.001", "H11 repasse a lojista devolvido; obrigação com o lojista continua", Decimal("0.70"),
     ("DEVOLUCAO_REPASSE",
      "PIX de repasse ao lojista voltou (devolução) por motivo desconhecido (S09). Classificado em 2.1.01.001 (H11): o repasse continua a pagar. Confirmar o motivo e se deve repagar em outubro.",
      QUEM_HELENA)),
    # ---- Meridiano
    ("MERIDIANO", r"^PIX RECEB ", "2.1.02.001", "H18 recurso de lojista para remessa", Decimal("1.00"), None),
    ("MERIDIANO", r"^TED ENVIADA PONTE CAMBIO", "2.1.02.001", "H18 liquidação de remessas na Ponte (Valor R$ + IOF)", Decimal("1.00"), None),
    ("MERIDIANO", r"REPASSE COMISSAO", "1.1.03.002", "R41/S08 repasse de comissão de câmbio já registrado (baixa do a receber)", Decimal("1.00"), None),
    ("MERIDIANO", r"MESMA TITULARIDADE", "1.1.09.001", "H13 transferência entre contas próprias", Decimal("1.00"), None),
    ("MERIDIANO", r"^RENDIMENTO", "3.2.01", "rendimento de aplicação automática", Decimal("1.00"), None),
    ("MERIDIANO", r"APLICACAO AUTOMATICA|RESGATE AUTOMATICO", "1.1.02.001", "aplicação/resgate automático (contrapartida na aplicação)", Decimal("1.00"), None),
    ("MERIDIANO", r"^TARIFA", "4.2.01", "R42 tarifa bancária, despesa do mês", Decimal("1.00"), None),
    ("MERIDIANO", r"SEGURO", "4.2.05", "R42 seguro, despesa do mês (sem provisão)", Decimal("1.00"), None),
    ("MERIDIANO", r"^IOF", "4.3.01", "IOF debitado pelo banco", Decimal("1.00"), None),
]

# Conciliações de apoio (só por VALOR e DATA, nunca por nome):
JANELA_PIX_REMESSA_DIAS = 7   # PIX de lojista no dia d cobre ops do mesmo CNPJ contratadas em [d, d+7) (doc §6.3)
CONF_NAO_CONCILIADO = Decimal("0.60")   # confiança quando a regra casa mas a conciliação não fecha
CONF_PIX_REMESSA_FUTURA = Decimal("1.00")  # S22: PIX de lojista sem operação Ponte no mês = recurso para
                                           # remessa futura (regra confirmada pelo financeiro) -> HUMANO 1,00 + acompanhamento
CONF_SEM_REGRA = Decimal("0.30")        # nenhuma regra casou -> HUMANO

# ---------------------------------------------------------------- natureza das divergências (R52, R60; S18, S34, S37)
# CONTRATO: o parceiro aplicou taxa diferente da informada a ele -> devolver ao lojista E cobrar o parceiro.
# ISENCAO_NAO_INFORMADA: isenção (TAXA_ZERO_CHECKOUT) que o parceiro não conhecia -> só devolver ao lojista.
NATUREZA_CONTRATO = "CONTRATO"
NATUREZA_ISENCAO = "ISENCAO_NAO_INFORMADA"
COBRAR_PARCEIRO = {NATUREZA_CONTRATO: "S", NATUREZA_ISENCAO: "N"}

# ---------------------------------------------------------------- dossiê de investigação (src/investigacao.py)
# Respostas do financeiro (docs/00_slack_respostas_financeiro.md) que tocam cada lojista.
# Chave = (linha_negocio, CNPJ). O dossiê só copia estes textos: nunca gera texto livre sobre S##.
TEXTOS_FINANCEIRO = {
    "S05": "Mundo Aberto negociou spread de 1,20% em julho; aplicar mais é divergência, Helena contesta com a Ponte.",
    "S06": "Rota Global: o contrato não mudou este ano; a cobrança de +0,50 p.p. desde 12/09 é divergência.",
    "S07": "Casa do Estudante: tarifa zerada no checkout de setembro a dezembro (MDR e antecipação), acordo comercial; a Orbe cobrou e a Helena devolve ao lojista.",
    "S10": "Divergência de remessa vale pelo valor cheio que o lojista pagou a mais, não só os 50% da Tarvo.",
    "S13": "O excesso da Mundo Aberto entra na nota de setembro pelo realizado; se a Ponte devolver, a metade da Tarvo sai no mês do ajuste.",
    "S18": "Casa do Estudante: a Orbe cobrou certo pela planilha porque ninguém avisou a isenção; não há o que cobrar da Orbe, é devolução ao lojista (Helena com o Comercial).",
    "S30": "Ninguém tem a função de avisar Orbe/Ponte das condições novas; a Bridge foi avisada alguns dias depois de 15/09; Casa do Estudante e Mundo Aberto não foram avisadas.",
    "S37": "Casa do Estudante: uma pendência com o total e o detalhe por transação; não pode entrar na cobrança da Orbe.",
}
# Contexto de fronteira escrito no motivo da pendência de divergência (o que a Helena precisa saber ao decidir).
CONTEXTO_PENDENCIA = {
    ("REMESSA", "17217888000111"): ("Caso de fronteira: a Ponte não foi avisada do spread de 1,20% (S30), mas a "
                                    "Helena decidiu tratar como divergência e contestar com a Ponte (S05)."),
}
RESPOSTAS_FINANCEIRO = {
    ("CHECKOUT", "95927868000148"): ["S06"],                      # Rota Global (EC 1074504011)
    ("CHECKOUT", "00520815000100"): ["S07", "S18", "S37", "S30"],  # Casa do Estudante (EC 1018325654)
    ("CHECKOUT", "22224579000109"): ["S30"],                      # Escola Bridge (EC 1075624862)
    ("REMESSA", "17217888000111"): ["S05", "S10", "S13", "S30"],  # Mundo Aberto
}
