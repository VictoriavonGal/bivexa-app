"""Regras fixas da Bivexa: verificações de conduta, urgência, conflito,
datas e formatação.

Estas regras funcionam sempre, com ou sem inteligência artificial. Elas são
também o "plano de reserva" quando a IA não está disponível.
"""

import json
import re
import secrets
import unicodedata
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")

DIAS_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
DIAS_CURTOS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


# ---------------------------------------------------------------- datas

def agora():
    return datetime.now(FUSO).replace(microsecond=0)


def agora_iso():
    return agora().strftime("%Y-%m-%d %H:%M:%S")


def hoje():
    return agora().date()


def ler_data(texto):
    """'2026-11-17' ou '2026-11-17 14:00:00' -> date/datetime."""
    if not texto:
        return None
    if len(texto) <= 10:
        return date.fromisoformat(texto)
    return datetime.fromisoformat(texto)


def data_br(valor):
    if not valor:
        return ""
    if isinstance(valor, str):
        valor = ler_data(valor)
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    return valor.strftime("%d/%m/%Y")


def data_extenso(valor):
    """'quinta, 12/11, às 14h'"""
    if isinstance(valor, str):
        valor = ler_data(valor)
    dia = DIAS_SEMANA[valor.weekday()]
    texto = f"{dia}, {valor.strftime('%d/%m')}"
    if isinstance(valor, datetime):
        hora = f"{valor.hour}h" if valor.minute == 0 else f"{valor.hour}h{valor.minute:02d}"
        texto += f", às {hora}"
    return texto


def somar_dias_uteis(inicio, dias):
    """Conta dias úteis (segunda a sexta), começando no dia seguinte.

    Não considera feriados nem suspensões de prazo: por isso a data é sempre
    uma SUGESTÃO, que o advogado confere e confirma.
    """
    atual = inicio
    contados = 0
    while contados < dias:
        atual += timedelta(days=1)
        if atual.weekday() < 5:
            contados += 1
    return atual


# ---------------------------------------------------------------- dinheiro

def moeda(valor):
    """1234.5 -> 'R$ 1.234,50'"""
    if valor is None:
        valor = 0
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def ler_valor(texto):
    """'1.500,00' ou '1500' ou '1500.50' -> 1500.0"""
    texto = str(texto).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return round(float(texto), 2)


# ---------------------------------------------------------------- textos

def sem_acento(texto):
    texto = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower()


def novo_token():
    return secrets.token_urlsafe(16)


def criar_slug(nome):
    base = re.sub(r"[^a-z0-9]+", "-", sem_acento(nome)).strip("-")
    return base[:40] or "escritorio"


# ---------------------------------------------------------------- conduta

# Frases que a Bivexa nunca envia a um cliente: são opinião jurídica,
# promessa de resultado ou orientação sobre o caso (Estatuto da Advocacia,
# art. 1º, e Código de Ética e Disciplina da OAB).
FRASES_PROIBIDAS = [
    "voce tem direito", "tem direito a", "vai ganhar", "voce ganha", "ganharemos",
    "com certeza", "garanto", "garantimos", "certamente", "nao assine", "pode assinar",
    "deve assinar", "nao deve assinar", "e crime", "nao e crime", "o juiz vai",
    "a justica vai", "voce vai receber", "causa ganha", "sem risco",
    # Incluídas depois da avaliação de 12/11 (avaliacao/RESULTADOS.md):
    # avaliação do caso e conselho sobre o que fazer.
    "ilegal", "chances", "vitorios", "vale a pena", "nao compensa", "compensa entrar",
    "da para processar", "pode processar", "prescricao", "prescreveu",
]

# Conselho sobre o que o cliente deve fazer no caso: "recomendo aceitar",
# "sugiro recorrer". Recomendações administrativas ("recomendo chegar 10
# minutos antes") continuam permitidas.
CONSELHO = re.compile(r"\b(recomendo|sugiro|aconselho)\b.{0,15}\b(aceitar|recusar|assinar|recorrer|"
                      r"processar|desistir|fechar|nao)\b")

# Perguntas do cliente que pedem opinião sobre o caso.
PEDIDOS_DE_OPINIAO = [
    "tenho direito", "vou ganhar", "da para ganhar", "devo assinar", "posso assinar",
    "assino ou nao", "o que eu faco", "o que faco", "e crime", "quanto vou receber",
    "vale a pena", "tenho chance", "minhas chances", "e legal", "e ilegal",
    "eles podem", "ela pode", "ele pode", "posso processar",
    # Incluídas depois da avaliação de 12/11:
    "compensa", "e possivel fazer algo", "da para fazer algo", "tem como reverter",
]

# "O banco pode negativar...?", "Meu chefe pode descontar...?": perguntar se
# alguém pode fazer algo contra o cliente é pedir uma avaliação jurídica.
PODE_FAZER = re.compile(r"\bpodem? (me )?(descontar|negativar|cobrar|demitir|despejar|cortar|"
                        r"reter|bloquear|penhorar|tomar|proibir|exigir)")

RESPOSTA_SEM_OPINIAO = (
    "Entendo a sua dúvida. Eu sou a assistente virtual do escritório e não posso "
    "dar orientação sobre o caso: quem avalia é {advogado}, advogado(a) responsável, na consulta. "
    "Vou registrar a sua pergunta para que ela seja respondida nesse momento."
)


def verificar_mensagem(texto):
    """Confere uma mensagem antes de enviá-la ao cliente.

    Devolve (aprovada, lista_de_verificacoes, motivo_do_bloqueio).
    """
    normal = sem_acento(texto)
    achadas = [f for f in FRASES_PROIBIDAS if f in normal]
    conselho = CONSELHO.search(normal)
    if conselho:
        achadas.append(conselho.group(0))
    verificacoes = [
        "sem opinião jurídica" if not achadas else "OPINIÃO JURÍDICA DETECTADA",
        "sem promessa de resultado",
    ]
    if achadas:
        return False, verificacoes, "Trecho bloqueado: " + ", ".join(achadas)
    return True, verificacoes, ""


def pede_opiniao(texto):
    normal = sem_acento(texto)
    return any(p in normal for p in PEDIDOS_DE_OPINIAO) or bool(PODE_FAZER.search(normal))


# ---------------------------------------------------------------- urgência

SINAIS_URGENCIA = [
    ("audiencia amanha", "audiência marcada para amanhã"),
    ("audiencia hoje", "audiência marcada para hoje"),
    ("prazo vence", "prazo vencendo"),
    ("prazo acaba", "prazo vencendo"),
    ("ultimo dia", "prazo vencendo"),
    ("assinar amanha", "documento para assinar amanhã"),
    ("assine amanha", "documento para assinar amanhã"),
    ("assinar hoje", "documento para assinar hoje"),
    ("preso", "pessoa presa ou risco de prisão"),
    ("prisao", "pessoa presa ou risco de prisão"),
    ("delegacia", "situação policial em andamento"),
    ("agressao", "risco à integridade de alguém"),
    ("agrediu", "risco à integridade de alguém"),
    ("violencia", "risco à integridade de alguém"),
    ("ameaca", "risco à integridade de alguém"),
    ("ameacou", "risco à integridade de alguém"),
    ("medida protetiva", "pedido de medida protetiva"),
    ("despejo amanha", "despejo iminente"),
    ("oficial de justica", "cumprimento de ordem judicial"),
    ("liminar", "decisão liminar"),
    ("urgente", "o cliente informou urgência"),
    # Incluídas depois da avaliação de 12/11:
    ("me bateu", "risco à integridade de alguém"),
    ("bateu em mim", "risco à integridade de alguém"),
    ("me bate", "risco à integridade de alguém"),
    ("medo de voltar", "risco à integridade de alguém"),
    ("mandado", "cumprimento de ordem judicial"),
    ("trocar a fechadura", "despejo iminente"),
    ("trocam a fechadura", "despejo iminente"),
]


# Uma palavra de tempo curto + uma palavra de ato jurídico também é urgência,
# mesmo que não estejam lado a lado ("assine um acordo amanhã").
TEMPO_CURTO = ["amanha", "hoje", "agora", "esta noite", "hoje a noite", "em 24 horas", "em 48 horas",
               "depois de amanha", "esta semana", "fim da semana",
               "ate segunda", "ate terca", "ate quarta", "ate quinta", "ate sexta", "ate sabado"]

# "tenho 5 dias para", "prazo de 3 dias": prazo curto escrito em número.
PRAZO_CURTO = re.compile(r"\b([1-9]|1[0-5]) dias? (uteis )?(para|pra)\b")
ATOS = [("assin", "documento para assinar em breve"), ("acordo", "acordo a ser fechado em breve"),
        ("audiencia", "audiência próxima"), ("prazo", "prazo vencendo"), ("pericia", "perícia próxima"),
        ("despejo", "despejo iminente"), ("leilao", "leilão próximo"), ("intimad", "intimação com data próxima"),
        ("citad", "citação com data próxima"), ("defesa", "defesa com prazo próximo"),
        ("entregar", "entrega com prazo próximo"), ("sair d", "desocupação iminente")]


def detectar_urgencia(texto):
    normal = sem_acento(texto)
    # "não é urgente" não pode virar alerta só por conter a palavra "urgente".
    normal = re.sub(r"nao (e|eh|esta|parece) urgente", "", normal)
    for sinal, motivo in SINAIS_URGENCIA:
        if sinal in normal:
            return True, motivo
    if PRAZO_CURTO.search(normal):
        return True, "prazo de poucos dias"
    if any(re.search(rf"\b{t}\b", normal) for t in TEMPO_CURTO):
        for ato, motivo in ATOS:
            if ato in normal:
                return True, motivo
    return False, ""


# ---------------------------------------------------------------- área

AREAS = {
    "Família": ["pensao", "alimentos", "divorcio", "guarda", "separacao", "uniao estavel",
                "visita", "partilha", "inventario", "heranca", "filho", "filha", "marido", "esposa",
                "companheiro", "companheira", "ex-mulher", "ex-marido"],
    "Trabalhista": ["demitido", "demissao", "rescisao", "fgts", "horas extras", "carteira",
                    "patrao", "empregador", "salario", "justa causa", "acordo trabalhista"],
    "Consumidor": ["compra", "produto", "loja", "banco", "cobranca indevida", "voo",
                   "companhia aerea", "bagagem", "golpe", "pix", "cartao", "plano de saude"],
    "Previdenciário": ["inss", "aposentadoria", "beneficio", "auxilio", "bpc", "pericia"],
    "Imobiliário": ["aluguel", "despejo", "inquilino", "locador", "imovel", "condominio",
                    "escritura", "usucapiao"],
    "Criminal": ["preso", "delegacia", "boletim de ocorrencia", "inquerito", "crime", "policia"],
    "Empresarial": ["socio", "sociedade", "empresa", "contrato social", "cnpj", "fornecedor"],
}


def classificar_area(texto, areas_escritorio=None):
    normal = sem_acento(texto)
    pontos = {area: sum(1 for p in palavras if p in normal) for area, palavras in AREAS.items()}
    melhor = max(pontos, key=pontos.get)
    if pontos[melhor] == 0:
        return "A definir"
    return melhor


def resumo_simples(relato, area, urgente, motivo):
    """Resumo da triagem quando a IA não está disponível."""
    partes = [f"Área provável: {area}."]
    if urgente:
        partes.append(f"URGENTE: {motivo}.")
    trecho = relato.strip()
    if len(trecho) > 280:
        trecho = trecho[:277] + "..."
    partes.append(f"Relato do cliente: \"{trecho}\"")
    return " ".join(partes)


DOCUMENTOS_POR_AREA = {
    "Família": "documento de identidade, certidão de nascimento ou casamento, comprovante de renda",
    "Trabalhista": "carteira de trabalho, holerites, termo de rescisão, documento do acordo proposto",
    "Consumidor": "nota fiscal ou comprovante de compra, conversas com a empresa, protocolos",
    "Previdenciário": "documento de identidade, CNIS, carta de indeferimento do INSS",
    "Imobiliário": "contrato de locação ou escritura, comprovantes de pagamento, notificações",
    "Criminal": "boletim de ocorrência, documentos recebidos da delegacia ou do juízo",
    "Empresarial": "contrato social, contratos com a outra parte, notas fiscais",
}


def documentos_sugeridos(area):
    return DOCUMENTOS_POR_AREA.get(area, "documento de identidade e qualquer papel ligado ao caso")


# ---------------------------------------------------------------- conflito

def procurar_conflito(nome_cliente, parte_contraria, partes):
    """Compara os nomes informados com a lista de clientes e partes do escritório.

    Há conflito quando a parte contrária informada é (ou foi) cliente do
    escritório, ou quando a pessoa que procura o escritório já aparece como
    parte contrária em outro caso.
    """
    alvo_contraria = sem_acento(parte_contraria).strip()
    alvo_cliente = sem_acento(nome_cliente).strip()
    for p in partes:
        nome = sem_acento(p["nome"]).strip()
        if not nome:
            continue
        if alvo_contraria and p["papel"] == "cliente" and (nome in alvo_contraria or alvo_contraria in nome):
            return f"{parte_contraria} é cliente do escritório"
        if alvo_cliente and p["papel"] == "parte contrária" and (nome in alvo_cliente or alvo_cliente in nome):
            return f"{nome_cliente} aparece como parte contrária em outro caso"
    return ""


# ---------------------------------------------------------------- agenda

HORARIOS_PADRAO = {"dias": [0, 1, 2, 3, 4], "inicio": "09:00", "fim": "18:00",
                   "almoco_inicio": "12:00", "almoco_fim": "13:00"}


def ler_horarios(texto):
    try:
        dados = json.loads(texto) if texto else {}
    except ValueError:
        dados = {}
    return {**HORARIOS_PADRAO, **dados}


def horarios_livres(horarios_json, duracao_min, ocupados, quantidade=3, a_partir=None):
    """Devolve os próximos horários livres de consulta.

    ocupados: lista de datetimes já marcados.
    Começa no dia seguinte, para dar tempo de o advogado ler a ficha.
    """
    base = (a_partir or agora()).date()
    livres = []
    for d in range(1, 21):
        for vaga in vagas_do_dia(horarios_json, duracao_min, ocupados, base + timedelta(days=d)):
            livres.append(vaga)
            if len(livres) >= quantidade:
                return livres
    return livres


def vagas_do_dia(horarios_json, duracao_min, ocupados, dia):
    """Todos os horários de consulta livres de um dia, dentro do expediente.

    Um horário está ocupado se algum compromisso começa durante ele (e não
    só exatamente no início), para não marcar consulta em cima de audiência.
    """
    h = ler_horarios(horarios_json)
    if dia.weekday() not in h["dias"]:
        return []
    almoco_ini = time.fromisoformat(h["almoco_inicio"]) if h.get("almoco_inicio") else None
    almoco_fim = time.fromisoformat(h["almoco_fim"]) if h.get("almoco_fim") else None
    passo = timedelta(minutes=duracao_min or 60)
    ocupados = [o.replace(tzinfo=None) for o in ocupados]
    atual = datetime.combine(dia, time.fromisoformat(h["inicio"]))
    fim = datetime.combine(dia, time.fromisoformat(h["fim"]))
    vagas = []
    while atual + passo <= fim:
        no_almoco = almoco_ini and almoco_fim and almoco_ini <= atual.time() < almoco_fim
        tomado = any(atual <= o < atual + passo for o in ocupados)
        if not no_almoco and not tomado:
            vagas.append(atual)
        atual += passo
    return vagas


def descrever_horarios(horarios_json):
    h = ler_horarios(horarios_json)
    dias = ", ".join(DIAS_CURTOS[d] for d in sorted(h["dias"]))
    texto = f"{dias}, das {h['inicio']} às {h['fim']}"
    if h.get("almoco_inicio"):
        texto += f" (intervalo {h['almoco_inicio']}–{h['almoco_fim']})"
    return texto


# ---------------------------------------------------------------- publicações

PADRAO_DATA = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:[^\d]{1,12}(\d{1,2})[h:](\d{2})?)?")
PADRAO_PRAZO = re.compile(r"prazo de (\d{1,3}) \(?[a-z ]*\)?\s*dias", re.IGNORECASE)


def ler_publicacao(texto):
    """Lê uma publicação e sugere uma data para a agenda.

    Devolve (tipo, data_iso, explicacao). A data é sempre uma sugestão.
    """
    normal = sem_acento(texto)
    m = PADRAO_DATA.search(texto)
    if m and ("audiencia" in normal or "sessao" in normal or "pericia" in normal):
        dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hora = int(m.group(4)) if m.group(4) else 9
        minuto = int(m.group(5)) if m.group(5) else 0
        quando = datetime(ano, mes, dia, hora, minuto)
        tipo = "audiência" if "audiencia" in normal else ("perícia" if "pericia" in normal else "sessão")
        return tipo, quando.strftime("%Y-%m-%d %H:%M:%S"), f"{tipo.capitalize()} designada na publicação."
    p = PADRAO_PRAZO.search(normal)
    if p:
        dias = int(p.group(1))
        vence = somar_dias_uteis(hoje(), dias)
        explicacao = (f"Prazo de {dias} dias úteis contado a partir de hoje, sem feriados. "
                      "Confira o início da contagem e os feriados locais antes de confirmar.")
        return "prazo", vence.isoformat(), explicacao
    return "", "", "Nenhuma data identificada. Inclua manualmente, se houver."
