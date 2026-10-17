"""Investigação de divergências com IA (Fase 2 do PLANO_IA_01).

Lê o dossiê determinístico (fatos por grupo) e pede ao Claude Sonnet 5.5 hipóteses de
causa, uma chamada por grupo, com saída estruturada (JSON schema). Guarda-corpos em
código: hipótese sem ID citado ou com ID inexistente no grupo é descartada; no máximo 3.

Dois provedores, escolhidos pela chave:
- OpenRouter (OPENROUTER_API_KEY, ou ANTHROPIC_API_KEY começando com "sk-or-"):
  HTTP pela biblioteca padrão (urllib), sem dependência nova.
- Anthropic (ANTHROPIC_API_KEY normal): SDK `anthropic`, importado só dentro das funções.

O fechamento base nunca depende disto. Sem chave, sem biblioteca ou com erro da API,
`investigar` devolve cada grupo com `erro` legível, sem quebrar. O valor da chave nunca
é impresso, gravado ou incluído em mensagens de erro.

Uso: python -m src.ia <dossie.json> <saida.json>
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_PROMPTS = Path(__file__).resolve().parent / "prompts"

MODELO = "claude-sonnet-5-5"                      # id na API da Anthropic
MODELO_OPENROUTER = "anthropic/claude-sonnet-5.5"  # mesmo modelo no OpenRouter
URL_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
PREFIXO_OPENROUTER = "sk-or-"
ESFORCO = "medium"
MAX_TOKENS = 16000
TIMEOUT_S = 90.0
MAX_TENTATIVAS = 2          # novas tentativas em 429/5xx/conexão (além da primeira)
ESPERA_MAX_S = 20.0
MAX_HIPOTESES = 3
AVISO = "Sugestão da IA, não verificada. A decisão é da analista."
CONTATOS = ["Orbe", "Ponte", "Comercial", "Lojista"]
CONFIANCAS = ["alta", "media", "baixa"]

# Campos do grupo que vão para o modelo. Nada além disso sai do dossiê.
CAMPOS_GRUPO = [
    "id_grupo", "contraparte", "linha_negocio", "lojista", "cnpj", "ec_orbe", "natureza",
    "qtd", "valor_divergencia_brl", "valor_devolver_lojista_brl",
    "valor_recuperar_parceiro_brl", "condicao_contratual", "fatos",
    "respostas_financeiro", "exemplos", "resumo_fatos", "rota_valores", "condicoes_cliente",
    "regras_aplicaveis", "acao_regra",
]

CATEGORIAS = [
    "CONDICAO_NAO_INFORMADA_AO_PARCEIRO", "VIGENCIA_APLICADA_COM_ATRASO", "REAJUSTE_SEM_CONTRATO",
    "TABELA_DESATUALIZADA_NO_PARCEIRO", "ERRO_DE_CADASTRO_NO_PARCEIRO",
    "CONCESSAO_COMERCIAL_FORA_DO_CONTRATO", "OUTRA",
]
ROTULO_CATEGORIA = {
    "CONDICAO_NAO_INFORMADA_AO_PARCEIRO": "Condição não informada ao parceiro",
    "VIGENCIA_APLICADA_COM_ATRASO": "Vigência aplicada com atraso",
    "REAJUSTE_SEM_CONTRATO": "Reajuste sem contrato",
    "TABELA_DESATUALIZADA_NO_PARCEIRO": "Tabela desatualizada no parceiro",
    "ERRO_DE_CADASTRO_NO_PARCEIRO": "Erro de cadastro no parceiro",
    "CONCESSAO_COMERCIAL_FORA_DO_CONTRATO": "Concessão comercial fora do contrato",
    "OUTRA": "Outra causa",
}
CATEGORIAS_ISENCAO = ("CONCESSAO_COMERCIAL_FORA_DO_CONTRATO", "CONDICAO_NAO_INFORMADA_AO_PARCEIRO")

SCHEMA_SAIDA = {
    "type": "object",
    "properties": {
        "id_grupo": {"type": "string"},
        "resumo": {"type": "string"},
        "hipoteses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "causa_categoria": {"type": "string", "enum": CATEGORIAS},
                    "causa": {"type": "string"},
                    "explicacao": {"type": "string"},
                    "evidencias": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"texto": {"type": "string"}, "ref": {"type": "string"}},
                            "required": ["texto", "ref"],
                            "additionalProperties": False,
                        },
                    },
                    "fatos_citados": {"type": "array", "items": {"type": "string"}},
                    "fatos_contrarios": {"type": "array", "items": {"type": "string"}},
                    "confianca": {"type": "string", "enum": CONFIANCAS},
                },
                "required": ["causa_categoria", "causa", "explicacao", "evidencias", "fatos_citados",
                             "fatos_contrarios", "confianca"],
                "additionalProperties": False,
            },
        },
        "conferir": {"type": "array", "items": {"type": "string"}},
        "falar_com": {"type": "string", "enum": CONTATOS},
        "dado_faltante": {"type": "string"},
    },
    "required": ["id_grupo", "resumo", "hipoteses", "conferir", "falar_com", "dado_faltante"],
    "additionalProperties": False,
}


class ErroIA(Exception):
    """Falha com mensagem já legível para a analista (sem a chave)."""


# ---------------------------------------------------------------- chave e provedor
def _ler_env(caminho: Path) -> dict:
    """Parser simples de .env: KEY=VALUE, ignora comentários e linhas vazias."""
    valores = {}
    try:
        linhas = caminho.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return valores
    for linha in linhas:
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        if linha.startswith("export "):
            linha = linha[len("export "):]
        chave, valor = linha.split("=", 1)
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        valores[chave.strip()] = valor
    return valores


def _variavel(nome: str, raiz: Path | None) -> str | None:
    valor = os.environ.get(nome, "").strip()
    if not valor:
        valor = _ler_env((raiz or RAIZ) / ".env").get(nome, "").strip()
    return valor or None


def obter_chave(raiz: Path | None = None) -> str | None:
    """Chave em ANTHROPIC_API_KEY (variável de ambiente tem precedência sobre o .env)."""
    return _variavel("ANTHROPIC_API_KEY", raiz)


def selecionar_provedor(raiz: Path | None = None) -> tuple[str | None, str | None]:
    """('openrouter'|'anthropic'|None, chave). Nunca exponha o segundo valor."""
    chave = _variavel("OPENROUTER_API_KEY", raiz)
    if chave:
        return "openrouter", chave
    chave = obter_chave(raiz)
    if chave and chave.startswith(PREFIXO_OPENROUTER):
        return "openrouter", chave
    if chave:
        return "anthropic", chave
    return None, None


def _biblioteca_instalada() -> bool:
    return importlib.util.find_spec("anthropic") is not None


def disponivel(raiz: Path | None = None) -> tuple[bool, str]:
    """(pode usar a IA?, motivo legível) — para a tela habilitar ou não o botão."""
    provedor, _ = selecionar_provedor(raiz)
    if provedor is None:
        return False, ("Chave não configurada: defina OPENROUTER_API_KEY ou ANTHROPIC_API_KEY "
                       "(variável de ambiente ou arquivo .env na raiz).")
    if provedor == "openrouter":
        return True, f"IA disponível via OpenRouter ({MODELO_OPENROUTER})."
    if not _biblioteca_instalada():
        return False, "Biblioteca 'anthropic' não instalada (pip install -r requirements-ia.txt)."
    return True, f"IA disponível via Anthropic ({MODELO})."


# ---------------------------------------------------------------- prompt
def _ler_prompt(nome: str) -> str:
    return (PASTA_PROMPTS / nome).read_text(encoding="utf-8")


def versao_prompt() -> str:
    m = re.search(r"versao:\s*([\w.\-]+)", _ler_prompt("investigacao.md"))
    return m.group(1) if m else "desconhecida"


def montar_system() -> str:
    return _ler_prompt("contexto_tarvo.md").strip() + "\n\n---\n\n" + _ler_prompt("investigacao.md").strip()


def montar_mensagem(dossie: dict, grupo: dict) -> str:
    """JSON enviado ao modelo: só a competência e os campos do próprio grupo."""
    dados = {"competencia": dossie.get("competencia")}
    dados.update({c: copy.deepcopy(grupo.get(c)) for c in CAMPOS_GRUPO if c in grupo})
    return (
        "Grupo de divergência para investigar (JSON):\n\n"
        + json.dumps(dados, ensure_ascii=False, indent=2)
        + "\n\nResponda no formato pedido, citando apenas IDs deste grupo."
    )


# ---------------------------------------------------------------- guarda-corpos
def ids_do_grupo(grupo: dict) -> set[str]:
    ids = {str(f.get("id")) for f in grupo.get("fatos") or [] if f.get("id")}
    for campo in ("respostas_financeiro", "rota_valores", "condicoes_cliente", "regras_aplicaveis"):
        ids |= {str(x.get("id")) for x in grupo.get(campo) or [] if isinstance(x, dict) and x.get("id")}
    ids |= {str(r) for r in (grupo.get("acao_regra") or {}).get("regras") or []}
    return ids


def _ids(lista) -> list[str]:
    return [str(i).strip() for i in (lista or []) if str(i).strip()]


def validar(resposta: dict, grupo: dict) -> dict:
    """Aplica os guarda-corpos sobre a resposta do modelo para um grupo.

    - hipótese sem nenhuma evidência válida nem fato citado, ou com ID inexistente em
      `fatos_citados` → descartada;
    - evidência com `ref` inexistente → removida e registrada em `ajustes`;
    - categoria fora do enum → OUTRA (ajuste); ISENCAO_NAO_INFORMADA com categoria que não seja
      concessão comercial nem condição não informada → confiança rebaixada (ajuste);
    - ID inexistente em `fatos_contrarios` → removido (a hipótese fica) e registrado em `ajustes`;
    - hipótese com fato contrário e confiança alta → rebaixada para média, registrado em `ajustes`;
    - ordena por confiança (alta > media > baixa), estável no empate; mantém no máximo 3.
    """
    validos = ids_do_grupo(grupo)
    aceitas, motivos, ajustes = [], [], []
    for h in resposta.get("hipoteses") or []:
        citados = _ids(h.get("fatos_citados"))
        causa = str(h.get("causa") or "").strip()
        evidencias, ev_removidas = [], []
        for e in h.get("evidencias") or []:
            if not isinstance(e, dict):
                continue
            texto_ev, ref = str(e.get("texto") or "").strip(), str(e.get("ref") or "").strip()
            if texto_ev and ref in validos:
                evidencias.append({"texto": texto_ev, "ref": ref})
            else:
                ev_removidas.append(ref or "(vazia)")
        if ev_removidas:
            ajustes.append({"causa": causa, "ajuste": "evidência com referência inexistente removida: "
                            + ", ".join(ev_removidas)})
        if not citados and not evidencias:
            motivos.append({"causa": causa, "motivo": "não cita nenhum fato"})
            continue
        inexistentes = [i for i in citados if i not in validos]
        if inexistentes:
            motivos.append({"causa": causa, "motivo": "cita ID inexistente no grupo: " + ", ".join(inexistentes)})
            continue
        contrarios = _ids(h.get("fatos_contrarios"))
        removidos = [i for i in contrarios if i not in validos]
        if removidos:
            contrarios = [i for i in contrarios if i in validos]
            ajustes.append({"causa": causa, "ajuste": "ID inexistente removido de fatos_contrarios: " + ", ".join(removidos)})
        confianca = h.get("confianca") if h.get("confianca") in CONFIANCAS else "baixa"
        if contrarios and confianca == "alta":
            confianca = "media"
            ajustes.append({"causa": causa, "ajuste": "confiança rebaixada de alta para média: há fato contrário ("
                            + ", ".join(contrarios) + ")"})
        categoria = h.get("causa_categoria")
        if categoria not in CATEGORIAS:
            ajustes.append({"causa": causa, "ajuste": f"categoria inválida ({categoria or 'ausente'}); usada OUTRA"})
            categoria = "OUTRA"
        if grupo.get("natureza") == "ISENCAO_NAO_INFORMADA" and categoria not in CATEGORIAS_ISENCAO:
            novo = {"alta": "media", "media": "baixa"}.get(confianca, "baixa")
            ajustes.append({"causa": causa, "ajuste": f"categoria {categoria} incompatível com isenção não "
                            f"informada; confiança rebaixada de {confianca} para {novo}"})
            confianca = novo
        aceitas.append({"causa_categoria": categoria, "causa": causa,
                        "explicacao": str(h.get("explicacao") or "").strip(), "evidencias": evidencias,
                        "fatos_citados": citados, "fatos_contrarios": contrarios, "confianca": confianca})
    aceitas.sort(key=lambda h: CONFIANCAS.index(h["confianca"]))  # sort é estável
    for h in aceitas[MAX_HIPOTESES:]:
        motivos.append({"causa": h["causa"], "motivo": f"acima do limite de {MAX_HIPOTESES} hipóteses"})
    falar = resposta.get("falar_com")
    return {
        "resumo": str(resposta.get("resumo") or "").strip(),
        "hipoteses": aceitas[:MAX_HIPOTESES],
        "conferir": [str(c).strip() for c in (resposta.get("conferir") or []) if str(c).strip()],
        "falar_com": falar if falar in CONTATOS else None,
        "dado_faltante": str(resposta.get("dado_faltante") or "").strip(),
        "hipoteses_descartadas": len(motivos),
        "motivos_descarte": motivos,
        "ajustes": ajustes,
    }


# ---------------------------------------------------------------- provedor OpenRouter
MENSAGENS_HTTP = {
    400: "requisição recusada pelo OpenRouter (parâmetro inválido)",
    401: "chave inválida ou sem crédito",
    402: "sem crédito no OpenRouter",
    403: "pedido bloqueado pela moderação do OpenRouter",
    404: f"modelo {MODELO_OPENROUTER} não encontrado no OpenRouter",
    408: "tempo esgotado no OpenRouter",
    429: "limite de uso atingido; tente de novo em alguns minutos",
    502: "o modelo está fora do ar ou respondeu inválido",
    503: "nenhum provedor disponível para o modelo no momento",
}


class ClienteOpenRouter:
    provedor = "openrouter"
    modelo = MODELO_OPENROUTER

    def __init__(self, chave: str, *, urlopen=None, dormir=time.sleep):
        self._chave = chave
        self._urlopen = urlopen
        self._dormir = dormir

    def __repr__(self) -> str:  # nunca mostra a chave
        return "ClienteOpenRouter(chave=***)"

    def _limpo(self, texto: str) -> str:
        return texto.replace(self._chave, "***") if self._chave else texto

    def payload(self, system: str, mensagem: str) -> dict:
        return {
            "model": MODELO_OPENROUTER,
            "max_tokens": MAX_TOKENS,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": mensagem},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "investigacao_grupo", "strict": True, "schema": SCHEMA_SAIDA},
            },
            "reasoning": {"effort": ESFORCO},
            # Sem `models` (lista de modelos alternativos). Sem provedor reserva e só provedores
            # que aceitam todos os parâmetros (incl. response_format): quem responde é o Sonnet 5.5.
            "provider": {"allow_fallbacks": False, "require_parameters": True},
        }

    def _post(self, corpo: bytes) -> dict:
        req = urllib.request.Request(
            URL_OPENROUTER, data=corpo, method="POST",
            headers={
                "Authorization": f"Bearer {self._chave}",
                "Content-Type": "application/json",
                "X-Title": "Tarvo - fechamento mensal",
            },
        )
        abrir = self._urlopen or urllib.request.urlopen
        with abrir(req, timeout=TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def gerar(self, system: str, mensagem: str) -> tuple[dict, str | None]:
        corpo = json.dumps(self.payload(system, mensagem), ensure_ascii=False).encode("utf-8")
        for tentativa in range(MAX_TENTATIVAS + 1):
            try:
                dados = self._post(corpo)
                break
            except urllib.error.HTTPError as exc:
                if (exc.code == 429 or exc.code >= 500) and tentativa < MAX_TENTATIVAS:
                    self._dormir(self._espera(exc, tentativa))
                    continue
                raise ErroIA(self._mensagem_http(exc)) from None
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as exc:
                motivo = getattr(exc, "reason", exc)
                if tentativa < MAX_TENTATIVAS:
                    self._dormir(2.0 * (tentativa + 1))
                    continue
                if isinstance(motivo, (socket.timeout, TimeoutError)) or "timed out" in str(motivo):
                    raise ErroIA("tempo esgotado na chamada ao OpenRouter.") from None
                raise ErroIA("sem conexão com o OpenRouter.") from None
        return self._extrair(dados)

    @staticmethod
    def _espera(exc, tentativa: int) -> float:
        try:
            return min(float(exc.headers.get("Retry-After")), ESPERA_MAX_S)
        except (TypeError, ValueError, AttributeError):
            return min(2.0 * (tentativa + 1), ESPERA_MAX_S)

    def _mensagem_http(self, exc) -> str:
        detalhe = ""
        try:
            detalhe = json.loads(exc.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            pass
        base = MENSAGENS_HTTP.get(exc.code, "erro do OpenRouter")
        texto = f"{base} (HTTP {exc.code})"
        if detalhe:
            texto += f": {self._limpo(str(detalhe))[:200]}"
        return texto + "."

    def _extrair(self, dados: dict) -> tuple[dict, str | None]:
        modelo = dados.get("model")
        if dados.get("error"):
            msg = self._limpo(str(dados["error"].get("message", "")))[:200]
            raise ErroIA(f"erro do OpenRouter durante a geração: {msg}.")
        escolha = (dados.get("choices") or [{}])[0]
        mensagem = escolha.get("message") or {}
        motivo = escolha.get("finish_reason")
        if mensagem.get("refusal") or motivo in ("content_filter", "refusal"):
            raise ErroIA("o modelo recusou responder a este grupo.")
        if motivo == "length":
            raise ErroIA("resposta cortada por limite de tamanho.")
        texto = mensagem.get("content")
        if not texto:
            raise ErroIA("resposta sem texto.")
        try:
            return json.loads(texto), modelo
        except json.JSONDecodeError:
            raise ErroIA("resposta da IA não é um JSON válido.") from None


# ---------------------------------------------------------------- provedor Anthropic (SDK)
class AdaptadorAnthropic:
    """Envolve um cliente do SDK `anthropic` (ou um falso com a mesma interface)."""
    provedor = "anthropic"
    modelo = MODELO

    def __init__(self, sdk):
        self._sdk = sdk

    def gerar(self, system: str, mensagem: str) -> tuple[dict, str | None]:
        # Sonnet 5.5: sem temperature (valor não padrão = 400) e sem `thinking` (adaptativo por
        # padrão); profundidade por `effort`. Saída estruturada via output_config.format.
        # Sem fallback de modelo: recusa vira erro legível do grupo.
        resposta = self._sdk.messages.create(
            model=MODELO,
            max_tokens=MAX_TOKENS,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": mensagem}],
            output_config={
                "effort": ESFORCO,
                "format": {"type": "json_schema", "schema": SCHEMA_SAIDA},
            },
        )
        modelo = getattr(resposta, "model", None)
        motivo = getattr(resposta, "stop_reason", None)
        if motivo == "refusal":
            raise ErroIA("o modelo recusou responder a este grupo.", modelo)
        if motivo == "max_tokens":
            raise ErroIA("resposta cortada por limite de tamanho.", modelo)
        texto = next((b.text for b in resposta.content if getattr(b, "type", None) == "text"), None)
        if texto is None:
            raise ErroIA("resposta sem texto.", modelo)
        try:
            return json.loads(texto), modelo
        except json.JSONDecodeError:
            raise ErroIA("resposta da IA não é um JSON válido.", modelo) from None


def _criar_cliente(provedor: str, chave: str):
    if provedor == "openrouter":
        return ClienteOpenRouter(chave)
    import anthropic
    return AdaptadorAnthropic(anthropic.Anthropic(api_key=chave, timeout=TIMEOUT_S, max_retries=MAX_TENTATIVAS))


def _como_cliente(cliente):
    return cliente if hasattr(cliente, "gerar") else AdaptadorAnthropic(cliente)


# ---------------------------------------------------------------- execução
def _base_grupo(grupo: dict, cliente=None) -> dict:
    return {
        "id_grupo": grupo.get("id_grupo"),
        "contraparte": grupo.get("contraparte"),
        "lojista": grupo.get("lojista"),
        "aviso": AVISO,
        "provedor": getattr(cliente, "provedor", None),
        "modelo": getattr(cliente, "modelo", MODELO),
        "modelo_resposta": None,
        "versao_prompt": versao_prompt(),
    }


def _com_erro(grupo: dict, mensagem: str, cliente=None, modelo_resposta: str | None = None) -> dict:
    r = _base_grupo(grupo, cliente)
    r.update({
        "modelo_resposta": modelo_resposta,
        "erro": f"IA indisponível: {mensagem} O dossiê de fatos continua disponível.",
        "resumo": "", "hipoteses": [], "conferir": [], "falar_com": None,
        "dado_faltante": "", "hipoteses_descartadas": 0, "motivos_descarte": [], "ajustes": [],
    })
    return r


def _mensagem_erro(exc: Exception) -> str:
    if isinstance(exc, ErroIA):
        return str(exc.args[0])
    try:
        import anthropic
    except ImportError:
        anthropic = None
    if anthropic is not None:
        if isinstance(exc, anthropic.APITimeoutError):
            return "tempo esgotado na chamada à API."
        if isinstance(exc, anthropic.AuthenticationError):
            return "chave da API recusada (verifique ANTHROPIC_API_KEY)."
        if isinstance(exc, anthropic.PermissionDeniedError):
            return "a chave não tem permissão para este modelo."
        if isinstance(exc, anthropic.NotFoundError):
            return f"modelo {MODELO} não encontrado."
        if isinstance(exc, anthropic.RateLimitError):
            return "limite de uso da API atingido; tente de novo em alguns minutos."
        if isinstance(exc, anthropic.BadRequestError):
            return f"requisição recusada pela API ({exc.message})."
        if isinstance(exc, anthropic.APIStatusError):
            return f"erro da API (HTTP {exc.status_code})."
        if isinstance(exc, anthropic.APIConnectionError):
            return "sem conexão com a API."
    if isinstance(exc, TimeoutError):
        return "tempo esgotado na chamada à API."
    return f"erro inesperado ({type(exc).__name__})."


def investigar_grupo(dossie: dict, grupo: dict, cliente, system: str | None = None) -> dict:
    cliente = _como_cliente(cliente)
    try:
        bruto, modelo_resposta = cliente.gerar(system or montar_system(), montar_mensagem(dossie, grupo))
    except Exception as exc:  # noqa: BLE001 — qualquer falha vira erro legível do grupo
        modelo = exc.args[1] if isinstance(exc, ErroIA) and len(exc.args) > 1 else None
        return _com_erro(grupo, _mensagem_erro(exc), cliente, modelo)
    r = _base_grupo(grupo, cliente)
    r["modelo_resposta"] = modelo_resposta
    r.update(validar(bruto, grupo))
    r["erro"] = None
    return r


def investigar(dossie: dict, *, cliente=None, raiz: Path | None = None) -> dict:
    """Hipóteses por grupo. Nunca levanta exceção por falta de chave, biblioteca ou erro da API."""
    grupos = dossie.get("grupos") or []
    if cliente is None:
        ok, motivo = disponivel(raiz)
        if ok:
            try:
                cliente = _criar_cliente(*selecionar_provedor(raiz))
            except Exception as exc:  # noqa: BLE001
                ok, motivo = False, _mensagem_erro(exc)
    else:
        ok, motivo = True, ""
        cliente = _como_cliente(cliente)
    saida = {
        "competencia": dossie.get("competencia"),
        "provedor": getattr(cliente, "provedor", None),
        "modelo": getattr(cliente, "modelo", MODELO),
        "versao_prompt": versao_prompt(),
        "aviso": AVISO,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "grupos": [],
    }
    if not ok:
        saida["grupos"] = [_com_erro(g, motivo) for g in grupos]
        return saida
    system = montar_system()
    saida["grupos"] = [investigar_grupo(dossie, g, cliente, system) for g in grupos]
    return saida


# ---------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("Uso: python -m src.ia <dossie.json> <saida.json>")
        return 2
    origem, destino = Path(argv[0]), Path(argv[1])
    if not origem.exists():
        print(f"Dossiê não encontrado: {origem}")
        return 1
    _, motivo = disponivel()
    print(motivo)
    resultado = investigar(json.loads(origem.read_text(encoding="utf-8")))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    for g in resultado["grupos"]:
        if g.get("erro"):
            print(f"{g['id_grupo']} {g.get('lojista')}: {g['erro']}")
        else:
            print(f"{g['id_grupo']} {g.get('lojista')}: {len(g['hipoteses'])} hipótese(s), "
                  f"{g['hipoteses_descartadas']} descartada(s) [{g.get('modelo_resposta')}]")
    print(f"Gravado em {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
