# Relatório de uso de IA e de outras ferramentas · Fase 2

## 1. O que queríamos fazer

Na fase 1, a Bivexa era uma proposta: um site que prometia cuidar da parte não jurídica do escritório do advogado autônomo. Na fase 2, precisávamos de um produto funcionando, em Python, em que alguém de fora conseguisse se cadastrar e usar como se fosse de verdade. Decidimos que o app teria de ir além do site justamente na parte administrativa, porque é ela que pesa para o escritório pequeno ou boutique: agenda, honorários, cobrança e acompanhamento de processo.

## 2. Ferramentas: o que testamos e o que ficou

**Assistente de código.** O código foi escrito pelo Claude, a partir dos nossos pedidos e do site da fase 1. Antes de começar, ele perguntou três coisas, e as decisões foram nossas:

- **Onde rodar:** escolhemos um link público no Render (plano gratuito), e não só o computador do grupo, para a banca testar sozinha.
- **IA de verdade ou simulada:** escolhemos IA de verdade pelo Groq (citado na aula 19), com um plano de reserva em regras fixas. Assim o app não para se a chave faltar ou a internet cair no dia da apresentação.
- **Repositório:** ainda não tínhamos; o assistente entregou a pasta pronta para subir.

**Linguagem e bibliotecas.** Python com Flask (telas), SQLite (banco de dados, um arquivo só, já vem com o Python) e Requests (chamada à IA). Não testamos outras ferramentas nesta fase: usamos só o Claude, para montar o código, e o Render, para publicar o site.

**Onde a IA entra no produto, e onde não entra.** A IA faz a triagem do primeiro contato, o parágrafo de objeto da proposta e o resumo das publicações. As regras que protegem o advogado (bloqueio de opinião jurídica, conflito de interesses, nada sai sem aprovação) **não** dependem da IA: são regras fixas, testadas. Decidimos assim porque uma regra ética não pode falhar quando o modelo erra.

## 3. O que deu errado e o que fizemos

- **A urgência do nosso próprio exemplo não era detectada.** O teste automático mostrou que a frase do site, "a empresa quer que eu assine um acordo amanhã", passava sem alerta: a regra só reconhecia "assine amanhã" com as palavras lado a lado. Trocamos a regra para combinar uma palavra de tempo curto (amanhã, hoje) com uma palavra de ato (assinar, acordo, audiência, prazo). Lição: o teste com o exemplo do pitch pegou o erro antes da banca.
- **"Do escritório de Dra. Helena Silva".** As mensagens ao cliente usavam o nome do advogado e ficavam erradas em português, porque o app não sabe se é "o Dr." ou "a Dra.". Reescrevemos para usar o nome do escritório.
- **Texto da IA com opinião jurídica.** Previmos o caso: se o modelo escrever algo como "você vai ganhar", o texto é descartado e o app usa o modelo fixo. Há um teste automático para isso.
- **Consulta marcada num sábado.** Ao refazer a demonstração com datas relativas a hoje (feedback do professor), a conversa dizia "quinta às 14h" e a agenda mostrava a consulta num sábado. Corrigimos fazendo os exemplos caírem sempre em dia útil e gerando o dia da semana da conversa a partir da data real. Um teste roda a demonstração em sete "hojes" diferentes.
- **As regras acertavam os nossos exemplos, mas não frases novas.** Por causa do feedback da fase 1 ("mostrar que o produto foi testado e quanto ele acerta"), pedimos ao Claude uma avaliação com a resposta certa marcada antes de rodar (`avaliacao/`). Na primeira rodada, o filtro de opinião jurídica deixou passar "suas chances são muito boas", e a urgência não reconhecia "me bateu ontem" nem "até sexta". As regras foram ajustadas e a primeira rodada passou a acertar quase tudo. Mas um segundo conjunto, escrito depois do ajuste, mostrou que o ajuste tinha decorado as frases: "você será indenizado" continuou passando. Decidimos não ajustar de novo e deixar o número honesto no README. Lição: um teste em que o produto acerta 100% pode estar medindo o teste, e não o produto. O que protege o cliente é a aprovação do advogado, e não a lista de palavras.

## 4. Custo e limite

- **Render gratuito:** o serviço "dorme" depois de 15 minutos sem uso e apaga o banco ao reiniciar. Decidimos que a conta de demonstração se recria sozinha e que abriremos o link alguns minutos antes da apresentação.
- **Groq gratuito:** limite diário de pedidos. Com o plano de reserva, o app continua funcionando se o limite acabar.
- **Claude:** usamos um plano pago do Claude para escrever o código. Foi o único gasto do projeto; o Render e o Groq ficaram no plano gratuito.

## 5. O que faríamos diferente

1. **Organizar melhor os prazos.** Nossa maior dificuldade foi a organização em relação aos prazos. Com um calendário interno, com datas para o código, o teste, o README e o ensaio, teríamos tempo de testar com um advogado de verdade e ajustar o produto com calma.
2. Testar o produto com um advogado autônomo de verdade antes de fechar as telas, e não só com os nossos exemplos.
3. Escrever os testes com os exemplos do pitch logo no começo, porque foram eles que pegaram o erro da urgência.
4. Separar desde o início os casos usados para ajustar as regras dos casos usados para medir, para não descobrir no fim que o acerto estava inflado.
