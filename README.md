# Bivexa AI

**A secretária que o escritório do advogado autônomo ainda não pode contratar.** A Bivexa atende o cliente novo, marca a consulta, prepara proposta e contrato, cobra os honorários e acompanha as publicações do processo. O advogado só decide: nada sai em nome dele sem o seu "sim".

Projeto da APS de Ciência de Dados Aplicada ao Direito I, Insper, 2026/2.

## O problema, num caso

Sexta, 22h. Um trabalhador escreve para a Dra. Helena, advogada que trabalha sozinha: foi demitido, e a empresa quer que ele assine um acordo na segunda às 9h. Ela só vê a mensagem no sábado à tarde, entre um prazo e outro. Até lá, ele já procurou outro escritório.

Segundo a pesquisa Perfil ADV (OAB e FGV, 2024), 72% da advocacia brasileira atua de forma autônoma. Quem advoga sozinho também atende, agenda, faz proposta, cobra e acompanha processo, e esse trabalho administrativo ocupa as horas que deveriam ir para o caso.

Com a Bivexa, a mensagem de sexta é respondida na hora. O relato é organizado, a urgência acende um alerta e a empresa do outro lado é conferida contra a lista de clientes (conflito de interesses). A consulta fica marcada num horário livre, e a pergunta "devo assinar?" fica para a advogada responder.

## Experimente

- **Endereço:** <https://bivexa-ai.onrender.com>. No plano gratuito, o primeiro acesso depois de um tempo parado demora cerca de 1 minuto.
- **Conta de demonstração:** na página inicial, clique em **Ver a demonstração**. Abre um escritório fictício, já configurado, com clientes de exemplo.
- **Conta nova:** clique em **Criar a conta do escritório**. O cadastro é real: e-mail, senha cifrada e configuração em três passos.

**Roteiro de dois minutos para a banca:**

1. Entre na demonstração e, na tela **Hoje**, clique em **Abrir o atendimento ao cliente**. Abra o link numa janela anônima.
2. Escreva como cliente: *"Fui demitido e a empresa quer que eu assine um acordo amanhã às 9h. Devo assinar?"*. Depois informe um nome e, como empresa, **Transportes Ipê**.
3. Veja a resposta. A assistente não opina, reconhece a urgência e para antes de marcar a consulta, porque a Transportes Ipê já é cliente do escritório.
4. Volte ao painel. Em **Hoje** estão o alerta de urgência e o conflito de interesses, esperando a decisão da advogada.
5. Abra o **Registro de conduta**: tudo o que aconteceu está lá, com as verificações feitas.

## Por que a Bivexa, e não o que o escritório já tem

| Alternativa | O que falta para este problema |
|---|---|
| **Um assistente de uso geral** (ChatGPT, Gemini) com um bom comando | Responde a quem pergunta, mas não atende o cliente do escritório às 22h. Não tem a agenda do advogado, não confere conflito de interesses, não guarda o histórico do cliente e não impede que a resposta tenha opinião jurídica. |
| **Software de gestão jurídica** | Em geral organiza processos e financeiro depois que alguém cadastra tudo. Esse alguém é a secretária que o autônomo não tem. |
| **Agenda online e cobrança avulsas** | Cada ferramenta faz uma parte. Nenhuma delas cruza o cliente que marcou consulta com as partes contrárias dos outros casos, nem segura a proposta até o advogado aprovar. |

**O que a torna específica para advogados:**

- confere o conflito de interesses antes de marcar a consulta;
- bloqueia opinião jurídica nas mensagens (Estatuto da Advocacia, art. 1º);
- lê as publicações do processo;
- mantém um registro de conduta de tudo o que saiu em nome do advogado.

## Como a Bivexa chega ao resultado

O caminho completo de um cliente tem 12 etapas, e só 6 passam pelo advogado: ler a ficha, conduzir a consulta, aprovar a proposta, assinar o contrato, confirmar as datas do processo e aprovar os avisos ao cliente.

| Etapa | Quem faz | Como |
|---|---|---|
| Responder o primeiro contato | Regra fixa | Textos escritos no código, e não texto livre da IA |
| Organizar o relato para o advogado | IA, com regra de reserva | O modelo resume o relato em até 3 frases neutras; sem IA, a regra copia o relato e marca a área |
| Reconhecer urgência | Regra **e** IA | O alerta acende se qualquer um dos dois apontar urgência |
| Conferir conflito de interesses | Regra fixa | Compara os nomes com a lista de clientes e partes contrárias do escritório |
| Oferecer horários | Regra fixa | Horários de atendimento do escritório, menos o que já está na agenda |
| Redigir o objeto da proposta | IA, com regra de reserva | A partir de uma frase do advogado; vai para a fila de aprovação |
| Ler a publicação do processo | Regra **e** IA | A regra acha a data; a IA resume e rascunha o aviso ao cliente, que vai para aprovação |
| Conferir cada mensagem antes do envio | Regra fixa | Lista de frases de opinião jurídica e promessa de resultado (`regras.verificar_mensagem`) |

**O modelo:** Llama 3.3 70B, pelo [Groq](https://groq.com), no plano gratuito. Sem a chave `GROQ_API_KEY`, ou se a IA falhar, cada uma dessas funções usa as regras fixas de `bivexa/regras.py`, e o app continua funcionando. O canto inferior do painel mostra qual modo está ativo.

## Quanto ela acerta

Testamos as regras fixas com mensagens de cliente e rascunhos de resposta, marcando antes a resposta certa. O resultado completo, com cada erro, está em [`avaliacao/RESULTADOS.md`](avaliacao/RESULTADOS.md). Para refazer a conta: `uv run python -m avaliacao.avaliar`.

O que aprendemos com o teste:

- **As regras reconhecem bem as frases que conhecem e mal as que nunca viram.** Em casos escritos depois do último ajuste, o filtro de opinião jurídica deixou passar frases como "você será indenizado".
- **Por isso o filtro é a segunda camada, e não a primeira.** As respostas automáticas são textos fixos. Todo texto novo (proposta, contrato, aviso de publicação, cobrança) espera o advogado, que vê o texto exato antes de enviar.
- **O erro que mais pesa é a urgência perdida.** A IA faz uma segunda leitura do relato. Os próximos passos são medir a IA nos mesmos casos e testar com mensagens reais de um advogado.

## O que a Bivexa não faz

- **Não dá opinião jurídica nem avalia o caso.** Quando o cliente pergunta "tenho direito?", a resposta é que a advogada ou o advogado avalia na consulta.
- **Não decide o que depende de interpretação.** Entendimentos divergentes, decisão ainda sujeita a recurso e casos parecidos que pedem caminhos diferentes ficam com o advogado. A Bivexa só organiza o que chega e prepara o que ele pediu.
- **Não conta prazo sozinha.** Sugere a data em dias úteis, sem feriados nem suspensões, e explica a conta. O advogado confere e confirma.
- **Não define preço nem estratégia.** Usa a tabela de honorários do próprio escritório.

## Dados e sigilo

| Pergunta | Resposta |
|---|---|
| Que dados a Bivexa guarda? | Dados do escritório; nome, contato e relato dos clientes; mensagens; agenda; propostas, contratos e parcelas; publicações coladas pelo advogado. |
| O que fica de fora? | CPF e documentos não são pedidos no primeiro contato; só na hora do contrato. |
| Onde ficam? | Num banco SQLite, no servidor do Render. No plano gratuito, o banco é apagado quando o serviço reinicia. |
| Quem vê? | Cada escritório só vê os próprios dados: toda consulta ao banco filtra pelo escritório logado, e há teste automático para isso. A equipe Bivexa pode abrir o painel de um escritório para dar suporte, e **cada acesso fica gravado** no registro de conduta daquele escritório. |
| E as senhas? | Guardadas só como hash (Werkzeug), sem como ler de volta. |
| O que vai para a IA? | O relato do cliente, a frase do advogado sobre o serviço e o texto da publicação, só para gerar o resumo e os rascunhos. Sem a chave do Groq, nada sai do servidor. |
| O que ainda falta para dados reais? | Esta é uma versão de demonstração: não use dados reais de clientes. Para uso de verdade, faltam banco com cópia de segurança, criptografia dos dados guardados e contrato de tratamento de dados com o provedor de IA (LGPD, art. 39). |

## Regras do produto

- **Nada sai sem o "sim" do advogado**, exceto mensagens administrativas (confirmação de horário e lembretes), que são textos fixos.
- **Toda mensagem ao cliente é conferida antes do envio.** Se a conferência falhar, a mensagem é bloqueada e vira uma pendência.
- **O conflito de interesses é conferido antes de qualquer consulta.**
- **Tudo vai para o registro de conduta**, com data, hora e as verificações feitas.

Essas regras vêm do Estatuto da Advocacia (Lei 8.906/1994, arts. 1º, 7º e 34), do Provimento 205/2021 e das recomendações do Conselho Federal da OAB sobre IA generativa (nov. 2024).

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

**Administração da plataforma**, para a equipe Bivexa: no seu computador, o acesso já vem ligado em `http://127.0.0.1:5000/admin/entrar`. O e-mail e a senha de teste aparecem no terminal ao rodar o app. No Render, o acesso só liga depois de definir `ADMIN_EMAIL` e `ADMIN_SENHA`.

## Testes

```bash
uv run --group dev pytest              # testes automáticos
uv run python -m avaliacao.avaliar     # quanto as regras acertam
```

Os testes percorrem o caminho inteiro de um cliente, do primeiro contato ao pagamento. Também cobrem a urgência, o conflito de interesses, o bloqueio de opinião jurídica, o atraso de parcela, o isolamento entre escritórios e a camada de IA, com e sem resposta do modelo.

## Como publicar no Render

1. Crie uma conta em [render.com](https://render.com), entrando com o GitHub.
2. No painel, clique em **New → Blueprint** e escolha este repositório. O arquivo `render.yaml` já diz tudo o que o Render precisa.
3. Preencha os valores pedidos:
   - `GROQ_API_KEY`: a chave do Groq, ou em branco para usar só as regras fixas;
   - `ADMIN_EMAIL` e `ADMIN_SENHA`: o login da administração;
   - `CONTATO_EMAIL`: o e-mail de atendimento que aparece no rodapé do site.
4. Clique em **Apply**. Em alguns minutos, o endereço aparece no topo da página do serviço.

**Atenção:** no plano gratuito, o Render "dorme" depois de 15 minutos sem uso e apaga o banco quando reinicia. A conta de demonstração é recriada sozinha. Abram o link alguns minutos antes da apresentação.

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
bivexa/exemplos.py      o escritório fictício da demonstração
bivexa/templates/       HTML das telas
bivexa/static/          visual (CSS) e logo
tests/                  testes automáticos
avaliacao/              casos com a resposta certa e o cálculo de acerto
```

## Limitações conhecidas

- As regras de texto reconhecem as frases que conhecem; frases novas escapam (ver `avaliacao/RESULTADOS.md`).
- A contagem de prazo considera só dias úteis, sem feriados nem suspensões: por isso é sempre uma sugestão.
- O banco SQLite atende bem um escritório pequeno. Para muitos escritórios, o caminho é um banco como o PostgreSQL.

## Licença

Proprietária: o código é público para avaliação, mas não pode ser usado sem autorização (ver `LICENSE`). As bibliotecas usadas (Flask, Gunicorn, Requests) mantêm as próprias licenças abertas.

## Equipe

Bianca Quadros, Fabiana Blaauw, Sophia Mariotto, Stephanie Von Gal e Victoria Von Gal.
