# Ditado Livre

Ditado por voz **gratuito** para Windows, inspirado no [Wispr Flow](https://wisprflow.ai/):
segure um atalho, fale e solte. O texto aparece onde o cursor estiver (e-mail, WhatsApp Web, Word, sistema do trabalho…), já com pontuação e sem "hum", "ahn" etc.

- **Transcrição no seu PC** com o Whisper (`large-v3-turbo`) usando a placa NVIDIA. O áudio não sai do computador.
- **Nuvem opcional**: dá para usar a Groq, que tem plano gratuito com limite diário.
- **Limpeza com IA**: corrige pontuação, escreve números com dígitos e aplica autocorreções faladas ("às duas, não, às três" → "às 3"). Também formata listas. A IA pode rodar no seu PC (Ollama) ou na Groq.
- Se a IA falhar ou estiver desligada, o texto é colado assim mesmo, só sem essa limpeza. Você nunca perde o ditado.

## Como funciona

```
segura Ctrl+Win → grava o microfone → solta
  → Whisper transcreve (PC ou Groq)
  → regras tiram hesitações (hum, ahn, éé…)
  → IA revisa (Ollama ou Groq), opcional
  → cola no app ativo e devolve o que estava na área de transferência
  → guarda no histórico
```

## Instalação (uma vez)

1. Baixe esta pasta. No GitHub: botão **Code → Download ZIP**, depois extraia e entre em `ditado-livre`.
2. Clique duas vezes em **`instalar.bat`**.
   - Se o Python não estiver instalado, o instalador instala pelo `winget` e pede para rodar de novo.
   - Com placa NVIDIA, ele baixa as bibliotecas CUDA. O download é grande e só acontece na primeira vez.
   - No fim aparece o atalho **Ditado Livre** na Área de Trabalho.
3. Para a **limpeza com IA no seu PC**, instale o [Ollama](https://ollama.com/download). Depois abra o Prompt de Comando e rode:
   ```
   ollama pull qwen2.5:3b
   ```
   Se preferir não instalar o Ollama, use a Groq (veja abaixo) ou desligue "Limpeza com IA" no menu.

**Para atualizar** para uma versão nova: substitua os arquivos da pasta e rode `instalar.bat` de novo. Suas configurações e seu histórico são mantidos.

Na primeira vez que o app abre, ele baixa o modelo Whisper, que tem mais de 1 GB. A janelinha mostra "Carregando…" até terminar.

## Uso

| Ação | Como |
|---|---|
| Ditar | Segure **Ctrl + Win**, fale e solte |
| Cancelar | **Esc** enquanto grava |
| Menu | Ícone azul de microfone perto do relógio (pode estar na setinha ^) |
| Configurações | Clique duplo no ícone |

Uma pílula escura aparece embaixo da tela mostrando o andamento:

- **Gravando**: bolinha vermelha pulsando, ondas que seguem a sua voz e o tempo.
- **Processando**: pontinhos azuis, com "Transcrevendo…" e depois "Revisando com IA…".
- **Pronto**: sinal verde e quantas palavras foram coladas.
- **Avisos e erros**: ícone laranja ou vermelho com a explicação.

Ela não rouba o foco do programa onde você digita e deixa os cliques passarem.

**Teste rápido**: abra o Bloco de Notas, segure Ctrl+Win e diga *"é… amanhã às duas, não, às três, eu passo aí"*. O esperado é algo como **"Amanhã às 3, eu passo aí."**

## Menu da bandeja

Clique no ícone de microfone perto do relógio:

- **Configurações…**: abre a janela de configurações (também abre com clique duplo no ícone).
- **Histórico…**: os últimos ditados, com busca e botão **Copiar**. Útil quando a colagem falha.
- **Transcrição**, **Limpeza com IA** e **Remover vícios**: atalhos rápidos para as opções mais usadas.

A cor do ícone acompanha o estado: azul (pronto), vermelho (gravando), cinza (carregando).

## Configurações

A janela segue o tema claro ou escuro do Windows e tem quatro abas:

| Aba | O que dá para mudar |
|---|---|
| Geral | Atalho (Ctrl + Win, Ctrl + Alt, F9… ou outra combinação), segurar ou apertar para ligar e desligar, devolver o que estava copiado, espaço no final, **abrir junto com o Windows** |
| Transcrição | No computador ou na nuvem (Groq), modelo do Whisper, placa de vídeo ou processador, idioma, chave da Groq |
| Limpeza | Remover hesitações e palavras extras, revisão com IA (Ollama ou Groq) e o botão **Testar IA** |
| Sobre | Versão e botão para abrir a pasta de dados |

Mudanças no atalho e na limpeza valem na hora. Trocar o modelo ou o motor de transcrição recarrega o Whisper.

As opções ficam em `%APPDATA%\DitadoLivre\config.json`. Se você editar esse arquivo à mão, feche e abra o app de novo.

O log de erros fica em `%APPDATA%\DitadoLivre\ditado-livre.log`.

### Usar a Groq (nuvem, gratuita com limites)

1. Crie uma conta em https://console.groq.com e gere uma *API key*.
2. Abra **Configurações › Transcrição**, cole a chave e escolha **Na nuvem (Groq)**.
3. Para a revisão com IA também ir para a Groq, escolha **Groq — na nuvem** na aba **Limpeza** e clique em **Testar IA**.

Os limites do plano gratuito mudam com o tempo; confira em https://console.groq.com/docs/rate-limits. Com a Groq, o áudio sai do seu PC.

## Problemas comuns

- **Aparece "processador (mais lento)" com placa NVIDIA**: atualize o driver da NVIDIA e rode `instalar.bat` de novo. O motivo exato fica no log.
- **Lento ou sem memória na placa**: em **Configurações › Transcrição**, escolha o modelo Médio ou Pequeno, ou use a Groq na limpeza.
- **Não colou**: alguns programas abertos como administrador não aceitam colagem de outro programa (regra do Windows). O texto fica em **Ver últimos ditados**.
- **Abre o menu Iniciar ao soltar o atalho**: troque o atalho em **Configurações › Geral**, ex.: Ctrl + Alt ou F9.
- **Ver mensagens de erro**: abra `iniciar-com-terminal.bat`.
- **Abrir junto com o Windows**: marque a opção em **Configurações › Geral**.
- **A IA não revisa**: em **Configurações › Limpeza**, clique em **Testar IA**; a mensagem diz o que falta (por exemplo, o Ollama fechado).

## Para desenvolvedores

```
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
pytest
python -m ditado_livre
```

Código em `src/ditado_livre/`: `pipeline.py` (fluxo), `transcribe/` (Whisper e Groq), `cleanup/` (regras, prompt e IA), `hotkey.py`, `audio.py`, `output.py`; interface em `overlay.py` (pílula), `tray.py`, `settings_window.py`, `history_window.py` e `theme.py` (cores, tema [Sun Valley](https://github.com/rdbende/Sun-Valley-ttk-theme), modo escuro e nitidez em telas com zoom). Ideias para a próxima versão estão em [`FASE2-sugestoes.md`](FASE2-sugestoes.md).

Inspirado nos projetos open-source [Handy](https://github.com/cjpais/Handy) e [OpenWhispr](https://github.com/OpenWhispr/openwhispr). Licença MIT.
