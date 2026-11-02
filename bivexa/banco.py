"""Banco de dados da Bivexa.

Usamos o SQLite, que guarda tudo num único arquivo e já vem com o Python.
Cada escritório só enxerga os próprios dados: toda tabela tem a coluna
escritorio_id, e toda consulta filtra por ela.
"""

import sqlite3
from pathlib import Path

from flask import current_app, g

ESQUEMA = """
CREATE TABLE IF NOT EXISTS escritorio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    advogado_nome TEXT NOT NULL,
    oab TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    telefone TEXT DEFAULT '',
    cidade TEXT DEFAULT '',
    uf TEXT DEFAULT 'SP',
    areas TEXT DEFAULT '',
    horarios TEXT DEFAULT '',
    duracao_consulta INTEGER DEFAULT 60,
    consulta_por_video INTEGER DEFAULT 1,
    modelo_proposta TEXT DEFAULT '',
    modelo_contrato TEXT DEFAULT '',
    lembrete_dias INTEGER DEFAULT 3,
    configurado INTEGER DEFAULT 0,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS servico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escritorio_id INTEGER NOT NULL REFERENCES escritorio(id),
    nome TEXT NOT NULL,
    area TEXT NOT NULL,
    valor_total REAL NOT NULL,
    parcelas INTEGER NOT NULL DEFAULT 1,
    descricao TEXT DEFAULT '',
    ativo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS parte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escritorio_id INTEGER NOT NULL REFERENCES escritorio(id),
    nome TEXT NOT NULL,
    papel TEXT NOT NULL,
    observacao TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS cliente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escritorio_id INTEGER NOT NULL REFERENCES escritorio(id),
    nome TEXT DEFAULT '',
    contato TEXT DEFAULT '',
    parte_contraria TEXT DEFAULT '',
    area TEXT DEFAULT '',
    relato TEXT DEFAULT '',
    resumo TEXT DEFAULT '',
    documentos_pendentes TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'novo contato',
    urgente INTEGER DEFAULT 0,
    motivo_urgencia TEXT DEFAULT '',
    conflito TEXT DEFAULT '',
    etapa_conversa TEXT DEFAULT 'relato',
    opcoes_horario TEXT DEFAULT '',
    origem TEXT DEFAULT 'atendimento',
    token TEXT NOT NULL UNIQUE,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mensagem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    autor TEXT NOT NULL,
    texto TEXT NOT NULL,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS compromisso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escritorio_id INTEGER NOT NULL REFERENCES escritorio(id),
    cliente_id INTEGER REFERENCES cliente(id),
    tipo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    inicio TEXT NOT NULL,
    confirmado INTEGER DEFAULT 1,
    observacao TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS proposta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escritorio_id INTEGER NOT NULL REFERENCES escritorio(id),
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    servico_id INTEGER REFERENCES servico(id),
    descricao_servico TEXT NOT NULL,
    valor_total REAL NOT NULL,
    parcelas INTEGER NOT NULL,
    texto TEXT NOT NULL,
    status TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contrato (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escritorio_id INTEGER NOT NULL REFERENCES escritorio(id),
    proposta_id INTEGER NOT NULL REFERENCES proposta(id),
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    texto TEXT NOT NULL,
    status TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    assinado_por TEXT DEFAULT '',
    assinado_em TEXT DEFAULT '',
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parcela (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escritorio_id INTEGER NOT NULL REFERENCES escritorio(id),
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    contrato_id INTEGER REFERENCES contrato(id),
    numero INTEGER NOT NULL,
    total_parcelas INTEGER NOT NULL,
    valor REAL NOT NULL,
    vencimento TEXT NOT NULL,
    status TEXT NOT NULL,
    codigo_pagamento TEXT DEFAULT '',
    token TEXT NOT NULL UNIQUE,
    lembrete_enviado INTEGER DEFAULT 0,
    pago_em TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS processo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escritorio_id INTEGER NOT NULL REFERENCES escritorio(id),
    cliente_id INTEGER NOT NULL REFERENCES cliente(id),
    numero TEXT NOT NULL,
    tribunal TEXT NOT NULL,
    descricao TEXT DEFAULT '',
    acesso_autorizado INTEGER DEFAULT 1,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS andamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    processo_id INTEGER NOT NULL REFERENCES processo(id),
    texto TEXT NOT NULL,
    resumo TEXT DEFAULT '',
    data_sugerida TEXT DEFAULT '',
    tipo_data TEXT DEFAULT '',
    mensagem_cliente TEXT DEFAULT '',
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pendencia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escritorio_id INTEGER NOT NULL REFERENCES escritorio(id),
    cliente_id INTEGER REFERENCES cliente(id),
    tipo TEXT NOT NULL,
    ref_id INTEGER,
    titulo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    urgente INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pendente',
    criado_em TEXT NOT NULL,
    resolvido_em TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS registro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escritorio_id INTEGER NOT NULL REFERENCES escritorio(id),
    cliente_id INTEGER REFERENCES cliente(id),
    ator TEXT NOT NULL,
    acao TEXT NOT NULL,
    detalhe TEXT DEFAULT '',
    verificacoes TEXT DEFAULT '',
    criado_em TEXT NOT NULL
);
"""


def caminho_banco():
    return Path(current_app.config["BANCO"])


def conectar():
    """Abre (uma vez por requisição) a conexão com o banco."""
    if "db" not in g:
        caminho_banco().parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(caminho_banco())
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def fechar(_erro=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def criar_tabelas():
    db = conectar()
    db.executescript(ESQUEMA)
    db.commit()


def um(sql, *params):
    """Devolve uma linha (ou None)."""
    return conectar().execute(sql, params).fetchone()


def varios(sql, *params):
    """Devolve uma lista de linhas."""
    return conectar().execute(sql, params).fetchall()


def executar(sql, *params):
    """Roda um INSERT/UPDATE/DELETE, grava e devolve o id criado."""
    db = conectar()
    cursor = db.execute(sql, params)
    db.commit()
    return cursor.lastrowid
