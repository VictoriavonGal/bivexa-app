"""Testes da camada de IA: com resposta do modelo e com falha (plano de reserva)."""

import json

import pytest

from bivexa import ia


class RespostaFalsa:
    def __init__(self, conteudo):
        self.conteudo = conteudo

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self.conteudo}}]}


@pytest.fixture()
def com_chave(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "chave-de-teste")


def test_triagem_usa_a_resposta_do_modelo(com_chave, monkeypatch):
    resposta = {"area": "Trabalhista", "urgente": True, "motivo_urgencia": "assinatura amanhã",
                "resumo": "Cliente demitido; empresa propõe acordo para amanhã.", "documentos": ["CTPS", "termo"]}
    monkeypatch.setattr(ia.requests, "post", lambda *a, **k: RespostaFalsa(json.dumps(resposta)))
    t = ia.triagem("Fui demitido e querem que eu assine amanhã")
    assert t["fonte"] == "IA" and t["area"] == "Trabalhista" and t["urgente"]
    assert t["documentos"] == "CTPS, termo"


def test_triagem_cai_nas_regras_se_o_modelo_falhar(com_chave, monkeypatch):
    def quebra(*a, **k):
        raise ia.requests.ConnectionError("sem internet")
    monkeypatch.setattr(ia.requests, "post", quebra)
    t = ia.triagem("Quero pedir pensão alimentícia para minha filha")
    assert t["fonte"] == "regras" and t["area"] == "Família"


def test_resposta_do_modelo_com_opiniao_e_descartada(com_chave, monkeypatch):
    resposta = {"resumo": "Publicação de audiência.", "mensagem_cliente": "Você vai ganhar com certeza!"}
    monkeypatch.setattr(ia.requests, "post", lambda *a, **k: RespostaFalsa(json.dumps(resposta)))
    leitura = ia.ler_publicacao("Designada audiência para 20/12/2026, às 14h.", "Carlos Souza")
    assert leitura["fonte"] == "regras"          # o texto da IA foi descartado
    assert "ganhar" not in leitura["mensagem"]
    assert leitura["data"] == "2026-12-20 14:00:00"
