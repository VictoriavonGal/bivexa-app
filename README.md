# Bivexa AI

**Mais horas para advogar.** A Bivexa é a assistente administrativa do advogado autônomo e do escritório boutique: atende o cliente novo, marca a consulta, prepara proposta e contrato, cobra os honorários e acompanha o processo. O advogado só aprova: nada sai em nome dele sem o seu "sim".

Projeto da APS de Ciência de Dados Aplicada ao Direito I, Insper, 2026/2.

## Experimente

- **Endereço público:** `https://bivexa-ai.onrender.com` *(confirme o endereço depois de publicar; ver "Como publicar")*
- **Conta de demonstração:** na página inicial, clique em **Entrar na demonstração**. Ela abre um escritório fictício, já configurado, com clientes de exemplo.
- **Conta nova:** clique em **Criar a conta do escritório**. O cadastro é real: e-mail, senha protegida e configuração em três passos.

Um roteiro de dois minutos para a banca:

1. Entre na demonstração e abra **Abrir o atendimento ao cliente** numa janela anônima.
2. Escreva como cliente: *"Fui demitido e a empresa quer que eu assine um acordo amanhã às 9h. Devo assinar?"*, depois um nome e, como empresa, **Transportes Ipê**.
3. Veja a resposta: a assistente não opina, identifica a urgência e para antes de marcar a consulta, porque a Transportes Ipê já é cliente do escritório.
4. Volte ao painel: em **Hoje** estão o alerta de urgência e o conflito de interesses, esperando a decisão do advogado.
5. Abra **Registro de conduta**: tudo o que aconteceu está lá, com as verificações feitas.

## Acesso da administração

Para quem mantém a plataforma (a equipe Bivexa), sem OAB. Mostra a visão geral (escritórios, clientes, consultas, contratos, honorários, mensagens bloqueadas) e permite abrir o painel de qualquer escritório. Cada acesso fica gravado no registro de conduta do escritório.

- **No seu computador:** já vem ligado. Endereço `http://127.0.0.1:5000/admin/entrar`, e-mail `admin@bivexa.app`, senha `admin-bivexa-2026` (aparecem no terminal ao rodar o app).
- **No Render:** o acesso só liga depois que vocês definem `ADMIN_EMAIL` e `ADMIN_SENHA` no painel do serviço (Environment). Usem uma senha forte: o site é público.

## Para quem é

Para o advogado que atende os próprios clientes, faz os próprios contratos e cobra os próprios honorários, sem secretária. Segundo a pesquisa Perfil ADV (OAB e FGV, 2024), 72% da advocacia brasileira atua de forma autônoma.

## O que o app faz

| Tela | O que resolve |
|---|---|
| **Atendimento** (`/atendimento/<escritório>`) | Primeiro contato a qualquer hora: triagem, alerta de urgência, conferência de conflito de interesses e agendamento da consulta nos horários livres. Nunca dá opinião jurídica. |
| **Hoje** | O que precisa do advogado agora: decisões pendentes, consultas dos próximos 7 dias com o resumo do caso, valores a receber e em atraso. |
| **Aprovações** | A fila do "sim": proposta, contrato, primeira cobrança, datas de processo e avisos ao cliente. Cada item pode ser aprovado ou revisado. |
| **Clientes** | O funil do escritório (novo contato → consulta → proposta → contrato) e a ficha de cada caso, com conversa, documentos a pedir e histórico. |
| **Agenda** | Consultas, audiências e prazos; os horários livres que a Bivexa oferece aos clientes. |
| **Financeiro** | Parcelas a aprovar, a vencer, em atraso e recebidas. Emissão e lembrete automáticos depois da primeira cobrança. |
| **Processos** | Publicação lida, resumida, com a data sugerida para a agenda e o aviso ao cliente rascunhado. |
| **Registro de conduta** | Tudo o que saiu em nome do advogado, com data, hora e as verificações feitas. |
| **Configurações** | Horários, tabela de honorários, modelos de proposta e contrato, lista de conflitos. |

O caminho completo de um cliente tem 12 etapas, e só 6 passam pelo advogado: ler a ficha, conduzir a consulta, aprovar a proposta, assinar o contrato, confirmar prazos e aprovar os avisos ao cliente.

## Regras que o app segue

- **Nada sai sem o "sim" do advogado**, exceto mensagens administrativas (confirmação de horário e lembretes).
- **Toda mensagem ao cliente é conferida** antes do envio contra frases de opinião jurídica ou promessa de resultado (`regras.verificar_mensagem`). Se a conferência falhar, a mensagem é bloqueada e vira uma pendência.
- **Conflito de interesses** é conferido antes de qualquer consulta, contra a lista de clientes e partes contrárias.
- **A Bivexa não conta prazo sozinha:** sugere a data e explica a conta; o advogado confere e confirma.
- **Cada escritório só vê os próprios dados.**

Essas regras vêm do Estatuto da Advocacia (Lei 8.906/1994, arts. 1º, 7º e 34), do Provimento 205/2021 e das recomendações do Conselho Federal da OAB sobre IA generativa (nov. 2024).

## Inteligência artificial

A IA (modelo de linguagem pelo [Groq](https://groq.com), plano gratuito) faz três coisas: a triagem do primeiro contato, o parágrafo de objeto da proposta e o resumo das publicações, com o aviso ao cliente.

**Plano de reserva:** sem a chave `GROQ_API_KEY`, ou se a IA falhar, cada uma dessas funções usa regras fixas (`bivexa/regras.py`) e o app continua funcionando. Texto da IA que contenha opinião jurídica é descartado. O canto inferior do painel mostra qual modo está ativo.

## O que é simulado nesta versão

| No produto completo | Nesta versão |
|---|---|
| Conversa pelo WhatsApp do escritório | Página de atendimento do escritório |
| Consulta automática aos tribunais | O advogado cola a publicação, e a Bivexa faz o resto |
| Pix e boleto reais | Código `DEMO-PIX` e botão "Simular pagamento" |
| Assinatura eletrônica certificada | Assinatura com nome digitado |

## Como rodar no seu computador

Precisa do [uv](https://docs.astral.sh/uv/), o mesmo da disciplina.

```bash
uv run python app.py
```

Abra `http://127.0.0.1:5000`. Para ligar a IA, crie uma chave gratuita em console.groq.com e rode:

```bash
GROQ_API_KEY=sua_chave uv run python app.py
```

No Windows (PowerShell): `$env:GROQ_API_KEY="sua_chave"; uv run python app.py`

## Testes

```bash
uv run --group dev pytest
```

Os testes percorrem o caminho inteiro de um cliente (do primeiro contato ao pagamento), a urgência, o conflito de interesses, o bloqueio de opinião jurídica, o atraso de parcela, o isolamento entre escritórios e a camada de IA com e sem resposta do modelo.

## Como publicar no Render

1. Crie uma conta em [render.com](https://render.com), entrando com o GitHub.
2. No painel, clique em **New → Blueprint** e escolha este repositório. O arquivo `render.yaml` já diz tudo o que o Render precisa.
3. O Render vai pedir três valores: `GROQ_API_KEY` (a chave do Groq, ou em branco para usar só as regras fixas), `ADMIN_EMAIL` e `ADMIN_SENHA` (o login da administração).
4. Clique em **Apply**. Em alguns minutos, o endereço aparece no topo da página do serviço.

**Atenção:** no plano gratuito, o Render "dorme" depois de 15 minutos sem uso (o primeiro acesso demora cerca de 1 minuto) e apaga o banco de dados quando reinicia. A conta de demonstração é recriada sozinha. Abram o link alguns minutos antes da apresentação.

## Estrutura do código

```
app.py                  ponto de entrada
bivexa/__init__.py      monta o app; cadastro, login e proteção dos formulários
bivexa/banco.py         tabelas do banco de dados (SQLite)
bivexa/regras.py        regras fixas: conduta, urgência, conflito, datas, dinheiro
bivexa/ia.py            chamadas ao modelo de linguagem, com plano de reserva
bivexa/servicos.py      o que o produto faz: atender, aprovar, propor, contratar, cobrar
bivexa/painel.py        telas do advogado
bivexa/admin.py         administração da plataforma (equipe Bivexa)
bivexa/publico.py       telas do cliente: atendimento, proposta, contrato, pagamento
bivexa/templates/       HTML das telas
bivexa/static/          visual (CSS) e logo
tests/                  testes automáticos
```

## Limitações conhecidas

- A contagem de prazo considera só dias úteis, sem feriados nem suspensões: por isso é sempre uma sugestão.
- A conferência de opinião jurídica usa uma lista de frases; não substitui a leitura do advogado.
- O banco SQLite atende bem um escritório pequeno; para muitos escritórios, o caminho é um banco como o PostgreSQL.

## Licença

Ver `LICENSE`. As bibliotecas usadas (Flask, Gunicorn, Requests) mantêm as próprias licenças abertas.

## Equipe

*(nomes do grupo)*
