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

Na primeira vez que o app abre, ele baixa o modelo Whisper, que tem mais de 1 GB. A janelinha mostra "Carregando…" até terminar.

## Uso

| Ação | Como |
|---|---|
| Ditar | Segure **Ctrl + Win**, fale e solte |
| Cancelar | **Esc** enquanto grava |
| Menu | Ícone azul de microfone perto do relógio (pode estar na setinha ^) |

A janelinha embaixo da tela mostra o andamento: vermelho grava, azul processa, verde terminou e laranja avisa (por exemplo, "IA indisponível").

**Teste rápido**: abra o Bloco de Notas, segure Ctrl+Win e diga *"é… amanhã às duas, não, às três, eu passo aí"*. O esperado é algo como **"Amanhã às 3, eu passo aí."**

## Menu da bandeja

- **Transcrever no meu PC / na nuvem (Groq)**: escolhe o motor.
- **Limpeza com IA** e **Remover vícios**: ligam ou desligam cada etapa.
- **Ver últimos ditados**: abre os 30 últimos textos. Útil quando a colagem falha.
- **Abrir configurações**: abre o `config.json` no Bloco de Notas. Depois de salvar, use **Recarregar configurações**.

## Configurações (`%APPDATA%\DitadoLivre\config.json`)

| Chave | Padrão | O que faz |
|---|---|---|
| `hotkey` | `ctrl+win` | Atalho. Use `+` entre teclas: `ctrl`, `alt`, `shift`, `win`, `f9`, `space`, letras… |
| `hotkey_mode` | `hold` | `hold` = segurar para falar; `toggle` = aperta para começar e de novo para parar |
| `engine` | `local` | `local` (Whisper no PC) ou `groq` |
| `local_model` | `large-v3-turbo` | Modelos menores e mais rápidos: `small`, `medium` |
| `device` | `auto` | `auto` tenta a GPU e cai para o processador; ou `cuda` / `cpu` |
| `ai_cleanup` | `true` | Liga a revisão com IA |
| `llm_provider` | `ollama` | `ollama` (no PC) ou `groq` |
| `ollama_model` | `qwen2.5:3b` | Qualquer modelo baixado com `ollama pull` |
| `groq_api_key` | vazio | Chave da Groq (veja abaixo) |
| `extra_filler_words` | `[]` | Vícios extras a remover, ex.: `["tipo assim"]` |
| `append_space` | `true` | Põe um espaço depois do texto, para emendar o próximo ditado |
| `restore_clipboard` | `true` | Devolve o texto que estava copiado antes |

O log de erros fica em `%APPDATA%\DitadoLivre\ditado-livre.log`.

### Usar a Groq (nuvem, gratuita com limites)

1. Crie uma conta em https://console.groq.com e gere uma *API key*.
2. Cole a chave em `groq_api_key` no `config.json` e use **Recarregar configurações**.
3. No menu, escolha **Transcrever na nuvem (Groq)**. Para a limpeza também ir para a Groq, mude `llm_provider` para `groq`.

Os limites do plano gratuito mudam com o tempo; confira em https://console.groq.com/docs/rate-limits. Com a Groq, o áudio sai do seu PC.

## Problemas comuns

- **Aparece "processador (mais lento)" com placa NVIDIA**: atualize o driver da NVIDIA e rode `instalar.bat` de novo. O motivo exato fica no log.
- **Lento ou sem memória na placa**: troque `local_model` para `small` ou `medium`, ou use a Groq na limpeza.
- **Não colou**: alguns programas abertos como administrador não aceitam colagem de outro programa (regra do Windows). O texto fica em **Ver últimos ditados**.
- **Abre o menu Iniciar ao soltar o atalho**: troque `hotkey` para outra combinação, ex.: `ctrl+alt` ou `f9`.
- **Ver mensagens de erro**: abra `iniciar-com-terminal.bat`.
- **Abrir junto com o Windows**: aperte Win+R, digite `shell:startup` e copie o atalho "Ditado Livre" para essa pasta.

## Para desenvolvedores

```
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
pytest
python -m ditado_livre
```

Código em `src/ditado_livre/`: `pipeline.py` (fluxo), `transcribe/` (Whisper e Groq), `cleanup/` (regras, prompt e IA), `hotkey.py`, `audio.py`, `output.py`, `overlay.py`, `tray.py`. Ideias para a próxima versão estão em [`FASE2-sugestoes.md`](FASE2-sugestoes.md).

Inspirado nos projetos open-source [Handy](https://github.com/cjpais/Handy) e [OpenWhispr](https://github.com/OpenWhispr/openwhispr). Licença MIT.
