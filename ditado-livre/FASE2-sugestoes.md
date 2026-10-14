# Fase 2: sugestões de uso (ainda não implementadas)

Você pediu exemplos antes de implementar as duas últimas funções. Os exemplos abaixo partem do seu dia a dia (auditoria de enfermagem / home care); troque pelo que fizer sentido. Diga quais quer e eu implemento.

## 1. Dicionário e atalhos de texto (snippets)

### Dicionário: palavras que o Whisper costuma errar
Você cadastra uma vez e elas passam a vir escritas certo. Tecnicamente, entram como "dica" para o Whisper e para a IA, mais uma troca automática depois.

| Você fala | Sem dicionário pode sair | Com dicionário |
|---|---|---|
| "planserv" | "plano serve", "planserve" | **Planserv** |
| "SAD" | "sade", "saad" | **SAD** |
| nome de paciente / empresa de home care | grafia errada | grafia certa |
| termos técnicos (ex.: "gastrostomia", "traqueostomia", "oxigenoterapia") e nomes de medicamentos | trocados por palavras parecidas | escritos certo |

Como seria: uma lista no `config.json` (ex.: `"dictionary": ["Planserv", "SAD", "gastrostomia"]`) e trocas fixas (`"replacements": {"planserve": "Planserv"}`).

### Snippets: uma frase curta vira um texto longo

| Você diz | Cola |
|---|---|
| "minha assinatura" | sua assinatura completa de e-mail (nome, cargo, registro, telefone) |
| "meu e-mail" | seu endereço de e-mail |
| "parecer padrão" | o parágrafo-modelo que você repete nos pareceres |
| "pedido de documentos" | o texto que pede ao SAD a documentação pendente |

## 2. Tom por aplicativo e comandos

### Estilo conforme o programa aberto
O app vê qual janela está ativa e ajusta a revisão da IA.

| Programa ativo | Estilo |
|---|---|
| Outlook / Gmail | formal, com saudação e parágrafos ("Prezados, …") |
| WhatsApp Web / Teams chat | curto e informal, sem ponto final no fim |
| Word / sistema de evolução | texto corrido, técnico, sem emojis nem gírias |

Exemplo: você dita *"oi pessoal preciso da evolução do paciente até sexta"*.
- No Outlook vira: "Prezados, boa tarde. Solicito o envio da evolução do paciente até sexta-feira."
- No WhatsApp vira: "Oi, pessoal! Preciso da evolução do paciente até sexta"

### Modo comando (selecionar texto e mandar a IA mexer)
Você seleciona um texto, segura outro atalho (ex.: `Ctrl+Win+Alt`) e fala uma instrução. O texto selecionado é substituído pelo resultado.

- "deixe mais formal"
- "resuma em três tópicos"
- "corrija a gramática"
- "traduza para o inglês"
- "transforme em lista de pendências"

Atenção: no modo comando, o texto selecionado vai para a IA. Com o Ollama ele não sai do PC; com a Groq, sai.
