"""Inteligência artificial da Bivexa.

Usa um modelo de linguagem pelo Groq (plano gratuito, citado na aula 19).
Para ligar, defina a variável de ambiente GROQ_API_KEY.

Plano de reserva: se não houver chave, se a internet falhar ou se a resposta
vier num formato inesperado, cada função usa as regras fixas de regras.py.
O app nunca para por causa da IA.
"""

import json
import os

import requests

from . import regras

URL_GROQ = "https://api.groq.com/openai/v1/chat/completions"
MODELO_PADRAO = "llama-3.3-70b-versatile"

INSTRUCOES_GERAIS = (
    "Você é a Bivexa, assistente administrativa de um escritório de advocacia "
    "brasileiro. Você NUNCA dá opinião jurídica, nunca promete resultado e nunca "
    "diz se a pessoa tem direito ou deve assinar algo: isso é atividade privativa "
    "do advogado (Lei 8.906/1994, art. 1º). Escreva em português do Brasil, em tom "
    "formal e claro."
)


def ligada():
    return bool(os.environ.get("GROQ_API_KEY"))


def descricao_status():
    if ligada():
        return f"IA ligada (Groq, {os.environ.get('GROQ_MODEL', MODELO_PADRAO)})"
    return "IA em modo de reserva (regras fixas)"


def _perguntar(instrucao, conteudo, quer_json=True):
    """Faz uma pergunta ao modelo. Devolve dict/texto, ou None se falhar."""
    chave = os.environ.get("GROQ_API_KEY")
    if not chave:
        return None
    corpo = {
        "model": os.environ.get("GROQ_MODEL", MODELO_PADRAO),
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": INSTRUCOES_GERAIS + "\n\n" + instrucao},
            {"role": "user", "content": conteudo},
        ],
    }
    if quer_json:
        corpo["response_format"] = {"type": "json_object"}
    try:
        resposta = requests.post(
            URL_GROQ,
            headers={"Authorization": f"Bearer {chave}"},
            json=corpo,
            timeout=20,
        )
        resposta.raise_for_status()
        texto = resposta.json()["choices"][0]["message"]["content"]
        return json.loads(texto) if quer_json else texto.strip()
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None


# ---------------------------------------------------------------- triagem

def triagem(relato):
    """Lê o relato do cliente e devolve área, urgência, resumo e documentos."""
    urgente_regra, motivo_regra = regras.detectar_urgencia(relato)
    area_regra = regras.classificar_area(relato)

    dados = _perguntar(
        "Leia o relato de uma pessoa que procurou o escritório e responda SÓ com um "
        "JSON com as chaves: area (uma de: Família, Trabalhista, Consumidor, "
        "Previdenciário, Imobiliário, Criminal, Empresarial, A definir), urgente "
        "(true/false: há audiência, prazo, assinatura ou risco à integridade em até "
        "2 dias?), motivo_urgencia (texto curto ou vazio), resumo (até 3 frases, "
        "neutras, sem opinião jurídica, para o advogado ler antes da consulta) e "
        "documentos (lista curta de documentos que o cliente deve trazer).",
        relato,
    )
    if isinstance(dados, dict) and dados.get("resumo"):
        urgente = bool(dados.get("urgente")) or urgente_regra
        motivo = dados.get("motivo_urgencia") or motivo_regra
        documentos = dados.get("documentos") or regras.documentos_sugeridos(area_regra)
        if isinstance(documentos, list):
            documentos = ", ".join(str(d) for d in documentos)
        return {
            "area": dados.get("area") or area_regra,
            "urgente": urgente,
            "motivo": motivo if urgente else "",
            "resumo": str(dados["resumo"]),
            "documentos": documentos,
            "fonte": "IA",
        }

    return {
        "area": area_regra,
        "urgente": urgente_regra,
        "motivo": motivo_regra,
        "resumo": regras.resumo_simples(relato, area_regra, urgente_regra, motivo_regra),
        "documentos": regras.documentos_sugeridos(area_regra),
        "fonte": "regras",
    }


# ---------------------------------------------------------------- proposta

def descrever_servico(frase_advogado, servico_nome, area):
    """Transforma a frase curta do advogado no parágrafo de objeto da proposta."""
    texto = _perguntar(
        "O advogado escreveu uma frase curta sobre o serviço que vai prestar. "
        "Reescreva como o parágrafo de OBJETO de uma proposta de honorários: 2 a 3 "
        "frases, formais, descrevendo só o que será feito. Não fale de valores, não "
        "prometa resultado. Responda só com o parágrafo.",
        f"Serviço da tabela: {servico_nome} ({area}). Frase do advogado: {frase_advogado}",
        quer_json=False,
    )
    if texto:
        aprovado, _, _ = regras.verificar_mensagem(texto)
        if aprovado:
            return texto, "IA"
    base = f"Prestação de serviços advocatícios de {servico_nome.lower()}"
    if frase_advogado.strip():
        base += f": {frase_advogado.strip().rstrip('.')}"
    return base + ".", "regras"


# ---------------------------------------------------------------- publicações

def ler_publicacao(texto_publicacao, nome_cliente):
    """Resume uma publicação para o advogado e rascunha o aviso ao cliente."""
    tipo, data_iso, explicacao = regras.ler_publicacao(texto_publicacao)

    dados = _perguntar(
        "Leia a publicação de um processo e responda SÓ com um JSON com as chaves: "
        "resumo (até 2 frases, para o advogado) e mensagem_cliente (mensagem curta, "
        "em linguagem simples, avisando o cliente do que aconteceu no processo, sem "
        "opinião jurídica e sem promessa de resultado, assinada pelo advogado).",
        f"Cliente: {nome_cliente}\nPublicação: {texto_publicacao}",
    )
    if isinstance(dados, dict) and dados.get("resumo") and dados.get("mensagem_cliente"):
        aprovado, _, _ = regras.verificar_mensagem(dados["mensagem_cliente"])
        if aprovado:
            return {
                "resumo": str(dados["resumo"]),
                "mensagem": str(dados["mensagem_cliente"]),
                "tipo": tipo, "data": data_iso, "explicacao": explicacao, "fonte": "IA",
            }

    trecho = texto_publicacao.strip()
    resumo = trecho if len(trecho) <= 220 else trecho[:217] + "..."
    primeiro_nome = (nome_cliente or "").split(" ")[0] or "cliente"
    if tipo and data_iso:
        quando = regras.data_extenso(data_iso)
        mensagem = (f"Olá, {primeiro_nome}. Houve uma movimentação no seu processo: "
                    f"{tipo} em {quando}. Vamos conversar antes para nos prepararmos.")
    else:
        mensagem = (f"Olá, {primeiro_nome}. Houve uma movimentação no seu processo. "
                    "Já estou acompanhando e falo com você sobre os próximos passos.")
    return {"resumo": resumo, "mensagem": mensagem, "tipo": tipo, "data": data_iso,
            "explicacao": explicacao, "fonte": "regras"}
