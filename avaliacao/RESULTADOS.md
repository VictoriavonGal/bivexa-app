# Quanto a Bivexa acerta

Gerado por `uv run python -m avaliacao.avaliar` em 12/11/2026. Não edite à mão: rode o comando de novo.

## Resumo

Medimos as **regras fixas** da Bivexa, que funcionam com ou sem IA, em dois conjuntos de casos com a resposta certa marcada antes de rodar (`avaliacao/casos.py`):

- **Primeira rodada:** 48 primeiros contatos e 28 mensagens ao cliente. Depois de ver os erros, ajustamos as regras.
- **Casos novos:** 20 primeiros contatos e 13 mensagens, escritos depois do ajuste. **É o número que vale**, porque mostra o que as regras fazem com frases que nunca viram.

| O que medimos | 1ª rodada, antes do ajuste | 1ª rodada, depois do ajuste | **Casos novos** |
|---|---|---|---|
| Bloquear mensagem com opinião jurídica | 79% | 100% | **46%** |
| Reconhecer urgência no primeiro contato | 83% | 98% | **70%** |
| Reconhecer pedido de opinião do cliente | 88% | 96% | **80%** |
| Classificar a área do Direito | 83% | 83% | **60%** |

Nas medidas de sim ou não, o acerto geral esconde um detalhe importante: quantos casos "sim" a regra encontrou. Nos casos novos:

- mensagens com opinião jurídica bloqueadas: **0 de 7**;
- casos urgentes reconhecidos: **3 de 9**;
- pedidos de opinião reconhecidos: **0 de 4**.

## O que concluímos

**Listas de palavras não reconhecem opinião jurídica escrita de outro jeito.** O ajuste fez a primeira rodada chegar perto de 100%, mas os casos novos mostram que ele decorou as frases em vez de aprender a ideia: "você será indenizado" e "a lei está do seu lado" passam pelo filtro. Por isso não ajustamos as regras de novo olhando para os casos novos.

**Por que isso não põe o cliente em risco:** o filtro é a segunda camada, e não a primeira.

1. As respostas automáticas do atendimento (boas-vindas, pedido de nome, horários, confirmação) são **textos fixos**, escritos no código, e não texto livre da IA.
2. Tudo o que tem texto novo (proposta, contrato, aviso de publicação, primeira cobrança) **espera o "sim" do advogado**, que vê o texto exato antes de enviar.
3. O filtro confere tudo de novo antes do envio e bloqueia o que reconhece.

**O erro que mais pesa é a urgência perdida.** Quando a regra não reconhece a urgência, o caso entra na fila sem o alerta vermelho. Com a IA ligada, o modelo faz uma segunda leitura do relato, e o alerta acende se *qualquer um* dos dois apontar urgência. Medir a IA nestes mesmos casos é o próximo passo.

## Erros nos casos novos

**Mensagens com opinião que o filtro deixou passar (o advogado as veria antes do envio):**

- "Seu caso é bem simples, deve se resolver rápido a seu favor."
- "A outra parte não tem razão nenhuma."
- "Pelo valor envolvido, acho melhor fazer um acordo."
- "O seu empregador não podia ter feito isso."
- "Você será indenizado."
- "Nesse tipo de situação, a lei está do seu lado."
- "Sugiro aguardar a decisão antes de pagar qualquer valor."

**Urgências não reconhecidas (o caso entra sem alerta):**

- "Me chamaram para depor na semana que vem e não sei se preciso de advogado."
- "Meu companheiro quebrou meu celular e disse que vai me matar."
- "O despejo está marcado para a próxima terça."
- "O leilão do meu carro é na quarta."
- "Fui agredido pelo segurança do mercado."
- "Minha mãe está internada e o plano de saúde quer suspender o tratamento amanhã."

**Pedidos de opinião não reconhecidos (a Bivexa também não opina; segue para o agendamento):**

- "Me chamaram para depor na semana que vem e não sei se preciso de advogado."
- "Quero saber se dá para pedir revisão da minha aposentadoria."
- "Será que eu consigo a guarda dos meus netos?"
- "A empresa pode me obrigar a voltar ao presencial?"

**Área classificada errado** (só organiza a ficha; o advogado corrige):

| Mensagem | Certo | Bivexa |
|---|---|---|
| Me chamaram para depor na semana que vem e não sei se preciso de advogado. | Criminal | A definir |
| Estou sendo cobrado por um empréstimo que nunca fiz. | Consumidor | A definir |
| A firma me mandou embora e não pagou as férias. | Trabalhista | A definir |
| A construtora atrasou a entrega do apartamento em dois anos. | Imobiliário | A definir |
| Sou MEI e um cliente não me paga há seis meses. | Empresarial | A definir |
| Fui agredido pelo segurança do mercado. | Criminal | A definir |
| Preciso de um contrato de prestação de serviços para minha loja. | Empresarial | Consumidor |
| A empresa pode me obrigar a voltar ao presencial? | Trabalhista | Empresarial |

## Primeira rodada, depois do ajuste

Erros que continuam: 11. Os ajustes estão marcados em `bivexa/regras.py` com o comentário "Incluídas depois da avaliação de 12/11".

**Alarmes falsos de urgência:**

- "Meu tio foi preso há dez anos e agora quer limpar o nome."

**Pedidos de opinião não reconhecidos:**

- "O RH me deu até sexta para assinar o termo de rescisão."
- "Quero processar a operadora porque a internet cai todo dia, não é urgente."

## O que esta avaliação não mede

- **A IA ligada.** Pede uma chave do Groq e o resultado varia de um dia para outro. Para medir, rode a triagem de `bivexa/ia.py` com `GROQ_API_KEY` nestes mesmos casos.
- **Mensagens reais.** Os casos foram escritos pelo grupo. O passo seguinte é testar com mensagens reais de um advogado autônomo, com autorização e sem dados pessoais.
- **Contagem de prazo.** A Bivexa só sugere a data, sem feriados; o advogado sempre confirma.
