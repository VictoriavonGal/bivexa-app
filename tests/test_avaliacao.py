"""A avaliação de acerto roda, e as regras nunca bloqueiam uma mensagem
administrativa (que, se bloqueada, deixaria o cliente sem a confirmação ou o
lembrete). Os números de acerto ficam em avaliacao/RESULTADOS.md, e não aqui:
um teste que exigisse 100% empurraria o grupo a decorar os casos."""

from avaliacao import casos
from avaliacao.avaliar import medir_tudo
from bivexa import regras


def test_avaliacao_roda_nos_dois_conjuntos():
    for contato, mensagens in [(casos.PRIMEIRO_CONTATO, casos.MENSAGENS_AO_CLIENTE),
                               (casos.PRIMEIRO_CONTATO_NOVOS, casos.MENSAGENS_AO_CLIENTE_NOVOS)]:
        r = medir_tudo(contato, mensagens)
        assert set(r) == {"bloqueio", "urgencia", "opiniao", "area"}


def test_mensagens_administrativas_nunca_sao_bloqueadas():
    administrativas = [t for t, opiniao in casos.MENSAGENS_AO_CLIENTE + casos.MENSAGENS_AO_CLIENTE_NOVOS
                       if not opiniao]
    for texto in administrativas:
        aprovada, _, motivo = regras.verificar_mensagem(texto)
        assert aprovada, f"{texto!r} foi bloqueada: {motivo}"


def test_nao_e_urgente_nao_dispara_alerta():
    assert not regras.detectar_urgencia("Quero rever o contrato do aluguel, não é urgente.")[0]
