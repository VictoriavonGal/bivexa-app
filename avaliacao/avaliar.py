"""Mede quanto as regras fixas da Bivexa acertam nos casos de avaliacao/casos.py
e grava o resultado em avaliacao/RESULTADOS.md.

Para rodar:  uv run python -m avaliacao.avaliar

Mede só as regras fixas (o modo que funciona sem a IA), porque são elas que
continuam valendo em qualquer situação. A IA, quando ligada, trabalha por
cima delas: a urgência apontada pela regra nunca é desligada pela IA.
"""

from datetime import date
from pathlib import Path

from bivexa import regras

from .casos import (MENSAGENS_AO_CLIENTE, MENSAGENS_AO_CLIENTE_NOVOS, PRIMEIRO_CONTATO,
                    PRIMEIRO_CONTATO_NOVOS)

SAIDA = Path(__file__).with_name("RESULTADOS.md")

# Acerto da primeira rodada (12/11/2026), antes de ajustar as regras.
# Fica registrado aqui porque as regras de hoje já não reproduzem esse número.
PRIMEIRA_RODADA = {"bloqueio": 0.79, "urgencia": 0.83, "opiniao": 0.88, "area": 0.83}


def medir(casos, prever):
    """Compara a resposta certa com a da Bivexa.

    casos: lista de (texto, resposta_certa: bool)
    Devolve acerto geral, quantos positivos foram encontrados e os erros.
    """
    perdidos, alarmes, certos = [], [], 0
    for texto, certo in casos:
        previsto = bool(prever(texto))
        if previsto == certo:
            certos += 1
        elif certo:
            perdidos.append(texto)
        else:
            alarmes.append(texto)
    positivos = sum(1 for _, c in casos if c)
    return {"total": len(casos), "acerto": certos / len(casos), "positivos": positivos,
            "encontrados": positivos - len(perdidos), "perdidos": perdidos, "alarmes": alarmes}


def medir_area(casos):
    erros = [(t, a, regras.classificar_area(t)) for t, _, _, a in casos]
    erros = [e for e in erros if e[1] != e[2]]
    return {"total": len(casos), "acerto": 1 - len(erros) / len(casos), "erros": erros}


def medir_tudo(contato, mensagens):
    return {
        "bloqueio": medir(mensagens, lambda t: not regras.verificar_mensagem(t)[0]),
        "urgencia": medir([(t, u) for t, u, _, _ in contato], lambda t: regras.detectar_urgencia(t)[0]),
        "opiniao": medir([(t, o) for t, _, o, _ in contato], regras.pede_opiniao),
        "area": medir_area(contato),
    }


def pct(x):
    return f"{x * 100:.0f}%"


def achados(r):
    """'5 de 7' para as medidas sim/não."""
    return f"{r['encontrados']} de {r['positivos']}"


def lista(titulo, frases):
    if not frases:
        return []
    return [f"**{titulo}**", ""] + [f"- \"{f}\"" for f in frases] + [""]


def main():
    a = medir_tudo(PRIMEIRO_CONTATO, MENSAGENS_AO_CLIENTE)
    b = medir_tudo(PRIMEIRO_CONTATO_NOVOS, MENSAGENS_AO_CLIENTE_NOVOS)
    nomes = {
        "bloqueio": "Bloquear mensagem com opinião jurídica",
        "urgencia": "Reconhecer urgência no primeiro contato",
        "opiniao": "Reconhecer pedido de opinião do cliente",
        "area": "Classificar a área do Direito",
    }

    l = [
        "# Quanto a Bivexa acerta",
        "",
        f"Gerado por `uv run python -m avaliacao.avaliar` em {date.today().strftime('%d/%m/%Y')}. "
        "Não edite à mão: rode o comando de novo.",
        "",
        "## Resumo",
        "",
        "Medimos as **regras fixas** da Bivexa, que funcionam com ou sem IA, em dois conjuntos de casos "
        "com a resposta certa marcada antes de rodar (`avaliacao/casos.py`):",
        "",
        f"- **Primeira rodada:** {len(PRIMEIRO_CONTATO)} primeiros contatos e {len(MENSAGENS_AO_CLIENTE)} "
        "mensagens ao cliente. Depois de ver os erros, ajustamos as regras.",
        f"- **Casos novos:** {len(PRIMEIRO_CONTATO_NOVOS)} primeiros contatos e "
        f"{len(MENSAGENS_AO_CLIENTE_NOVOS)} mensagens, escritos depois do ajuste. **É o número que vale**, "
        "porque mostra o que as regras fazem com frases que nunca viram.",
        "",
        "| O que medimos | 1ª rodada, antes do ajuste | 1ª rodada, depois do ajuste | **Casos novos** |",
        "|---|---|---|---|",
    ]
    for k, nome in nomes.items():
        l.append(f"| {nome} | {pct(PRIMEIRA_RODADA[k])} | {pct(a[k]['acerto'])} | **{pct(b[k]['acerto'])}** |")
    l += [
        "",
        "Nas medidas de sim ou não, o acerto geral esconde um detalhe importante: quantos casos "
        "\"sim\" a regra encontrou. Nos casos novos:",
        "",
        f"- mensagens com opinião jurídica bloqueadas: **{achados(b['bloqueio'])}**;",
        f"- casos urgentes reconhecidos: **{achados(b['urgencia'])}**;",
        f"- pedidos de opinião reconhecidos: **{achados(b['opiniao'])}**.",
        "",
        "## O que concluímos",
        "",
        "**Listas de palavras não reconhecem opinião jurídica escrita de outro jeito.** O ajuste fez a "
        "primeira rodada chegar perto de 100%, mas os casos novos mostram que ele decorou as frases em vez "
        "de aprender a ideia: \"você será indenizado\" e \"a lei está do seu lado\" passam pelo filtro. "
        "Por isso não ajustamos as regras de novo olhando para os casos novos.",
        "",
        "**Por que isso não põe o cliente em risco:** o filtro é a segunda camada, e não a primeira.",
        "",
        "1. As respostas automáticas do atendimento (boas-vindas, pedido de nome, horários, confirmação) são "
        "**textos fixos**, escritos no código, e não texto livre da IA.",
        "2. Tudo o que tem texto novo (proposta, contrato, aviso de publicação, primeira cobrança) "
        "**espera o \"sim\" do advogado**, que vê o texto exato antes de enviar.",
        "3. O filtro confere tudo de novo antes do envio e bloqueia o que reconhece.",
        "",
        "**O erro que mais pesa é a urgência perdida.** Quando a regra não reconhece a urgência, o caso entra "
        "na fila sem o alerta vermelho. Com a IA ligada, o modelo faz uma segunda leitura do relato, e o "
        "alerta acende se *qualquer um* dos dois apontar urgência. Medir a IA nestes mesmos casos é o "
        "próximo passo.",
        "",
        "## Erros nos casos novos",
        "",
    ]
    l += lista("Mensagens com opinião que o filtro deixou passar (o advogado as veria antes do envio):",
               b["bloqueio"]["perdidos"])
    l += lista("Mensagens administrativas bloqueadas por engano (viram pendência, sem dano):",
               b["bloqueio"]["alarmes"])
    l += lista("Urgências não reconhecidas (o caso entra sem alerta):", b["urgencia"]["perdidos"])
    l += lista("Alarmes falsos de urgência (o advogado recebe um alerta desnecessário):",
               b["urgencia"]["alarmes"])
    l += lista("Pedidos de opinião não reconhecidos (a Bivexa também não opina; segue para o agendamento):",
               b["opiniao"]["perdidos"])
    l += lista("Respostas \"não posso orientar\" desnecessárias:", b["opiniao"]["alarmes"])
    if b["area"]["erros"]:
        l += ["**Área classificada errado** (só organiza a ficha; o advogado corrige):", "",
              "| Mensagem | Certo | Bivexa |", "|---|---|---|"]
        l += [f"| {t} | {c} | {p} |" for t, c, p in b["area"]["erros"]]
        l.append("")
    restantes = sum(len(a[k].get("perdidos", [])) + len(a[k].get("alarmes", [])) for k in
                    ("bloqueio", "urgencia", "opiniao")) + len(a["area"]["erros"])
    l += [
        "## Primeira rodada, depois do ajuste",
        "",
        f"Erros que continuam: {restantes}. Os ajustes estão marcados em `bivexa/regras.py` com o "
        "comentário \"Incluídas depois da avaliação de 12/11\".",
        "",
    ]
    l += lista("Alarmes falsos de urgência:", a["urgencia"]["alarmes"])
    l += lista("Urgências não reconhecidas:", a["urgencia"]["perdidos"])
    l += lista("Pedidos de opinião não reconhecidos:", a["opiniao"]["perdidos"])
    l += [
        "## O que esta avaliação não mede",
        "",
        "- **A IA ligada.** Pede uma chave do Groq e o resultado varia de um dia para outro. Para medir, "
        "rode a triagem de `bivexa/ia.py` com `GROQ_API_KEY` nestes mesmos casos.",
        "- **Mensagens reais.** Os casos foram escritos pelo grupo. O passo seguinte é testar com "
        "mensagens reais de um advogado autônomo, com autorização e sem dados pessoais.",
        "- **Contagem de prazo.** A Bivexa só sugere a data, sem feriados; o advogado sempre confirma.",
        "",
    ]
    SAIDA.write_text("\n".join(l), encoding="utf-8")
    for k, nome in nomes.items():
        print(f"{nome}: 1ª rodada {pct(a[k]['acerto'])} | casos novos {pct(b[k]['acerto'])}")
    print(f"Resultado gravado em {SAIDA}")


if __name__ == "__main__":
    main()
