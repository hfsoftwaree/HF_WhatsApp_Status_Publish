# HF WhatsApp Status Publisher

Automatiza a publicação diária de imagens e vídeos no **Status do WhatsApp** usando o WhatsApp Web e o [Playwright](https://playwright.dev/python/).

Coloque as imagens e os vídeos na pasta `Status`, defina o horário de publicação no arquivo `config.json` (dentro da pasta `Config`) e o programa publica tudo sozinho, em ordem alfabética, movendo cada arquivo publicado para a pasta `Publicados`.

## Funcionalidades

- Instalador automático: instala o Python, o Playwright e o Chromium com um duplo clique
- Publicação agendada em um horário diário configurável
- Publica todas as imagens (`.jpg`, `.jpeg`, `.png`) e vídeos (`.mp4`, `.mov`, `.3gp`) da pasta `Status`, em ordem alfabética
- Espera inteligente para vídeos: aguarda o carregamento no editor antes de enviar
- Sessão do WhatsApp salva: o QR Code só precisa ser escaneado uma vez
- Fecha automaticamente pop-ups e avisos do WhatsApp Web
- Opção de rodar o navegador minimizado durante a execução
- Duas tentativas por arquivo, com captura de tela e HTML para depuração em caso de erro
- Move os arquivos publicados para `Publicados` e mantém em `Status` os que falharam
- Registro das execuções em arquivo de log

## Requisitos

- **Windows 10 ou 11** com o **WinGet** (Windows Package Manager) disponível. Ele vem com o *App Installer* da Microsoft Store; se estiver faltando, atualize o *App Installer* pela loja.
- Conexão com a internet durante a instalação
- Uma conta de WhatsApp com acesso ao WhatsApp Web

**Você não precisa instalar o Python manualmente.** O `Installer.bat` cuida disso.

> Linux e macOS: o script Python deve funcionar, mas o instalador automático é exclusivo do Windows. Veja [Instalação manual](#instalação-manual-linuxmacos-ou-quem-preferir).

## Instalação

1. Baixe ou clone o repositório:

   ```bash
   git clone https://github.com/SEU_USUARIO/HF_WhatsApp_Status_Publish.git
   cd HF_WhatsApp_Status_Publish
   ```

2. Dê dois cliques em **`Installer.bat`**. Isso só precisa ser feito uma vez em cada computador.

### O que o instalador faz

O `Installer.bat` executa seis etapas, mostrando o progresso na tela:

| Etapa | Ação |
|---|---|
| 1/6 | Verifica se o WinGet está disponível |
| 2/6 | Instala o **Python Install Manager** oficial (via WinGet), caso ainda não exista |
| 3/6 | Configura o Python Install Manager |
| 4/6 | Instala o Python estável mais recente |
| 5/6 | Atualiza o `pip` e instala o **Playwright** |
| 6/6 | Instala o navegador **Chromium** usado pelo Playwright |

Ao final, ele exibe as versões instaladas do Python e do Playwright. Se alguma etapa falhar, uma mensagem de erro é exibida e a janela aguarda uma tecla antes de fechar.

### Instalação manual (Linux/macOS ou quem preferir)

Com o Python 3.9 ou superior já instalado:

```bash
pip install playwright
python -m playwright install chromium
```

## Configuração

Na primeira execução (`Start.bat`), o programa cria o arquivo `Config/config.json`:

```json
{
    "agendamento_ativo": false,
    "horario_envio": "08:00"
}
```

| Campo | Descrição |
|---|---|
| `agendamento_ativo` | `true` para o programa funcionar, `false` para encerrar sem abrir o navegador |
| `horario_envio` | Horário diário da publicação, no formato `HH:MM` (ex.: `08:00`) |

Para usar, altere `agendamento_ativo` para `true`.

Se o programa for iniciado depois do horário definido (mais de 1 minuto), ele aguarda até o mesmo horário do dia seguinte. Se for iniciado antes, aguarda até o horário do mesmo dia. O navegador só é aberto quando o horário chega.

Outras opções ficam no topo do script (`HF_WhatsApp_Status_Publisher.py`):

| Variável | Descrição |
|---|---|
| `START_MINIMIZED` | Minimiza a janela do navegador após abrir (padrão: `False`). Pode ser alternado com o `Alternar_Minimizado.bat` |
| `HEADLESS` | Executa sem janela visível (não recomendado, o WhatsApp Web pode se comportar diferente) |
| `INTERVAL_SECONDS` | Intervalo entre um arquivo e outro |
| `CONFIRM_BEFORE_PUBLISHING` | Pede confirmação digitada antes de publicar |
| `VIDEO_SEND_READY_TIMEOUT_MS` | Tempo máximo (ms) esperando o vídeo ficar pronto para envio (padrão: 120000) |
| `VIDEO_AFTER_SEND_TIMEOUT_MS` | Tempo máximo (ms) esperando o envio do vídeo concluir (padrão: 90000) |

## Vídeos

- Formatos aceitos: `.mp4`, `.mov` e `.3gp`. O mais seguro é **MP4 (H.264 + AAC)**.
- Recomendado: até 16 MB e cerca de 1 minuto de duração. O programa registra um aviso no log se o vídeo passar de 16 MB.
- Vídeos demoram mais para carregar e enviar, então a publicação de cada um leva mais tempo que a de uma imagem.
- Se a prévia do vídeo não carregar no navegador do Playwright, abra o script e ative a linha `channel="chrome"` em `launch_persistent_context` para usar o Google Chrome instalado. Nesse caso, será preciso escanear o QR Code novamente.

## Primeira execução (QR Code)

1. Rode o `Installer.bat`, se ainda não o fez.
2. Coloque ao menos uma imagem ou vídeo na pasta `Status`.
3. Execute `Start.bat` uma vez para o programa criar o `Config/config.json`, depois defina `agendamento_ativo` como `true` e um horário próximo.
4. Execute o programa novamente e escaneie o QR Code com o celular (**WhatsApp > Aparelhos conectados > Conectar um aparelho**).
5. Depois que a sessão estiver salva, você pode mudar `START_MINIMIZED` para `True` se preferir que o WhatsApp Web rode minimizado, sem ocupar a tela durante a publicação. Se preferir acompanhar o processo na tela, deixe `False`.

   Para alternar sem editar o código, dê dois cliques em **`Alternar_Minimizado.bat`**: cada execução inverte a opção entre `True` e `False` e informa o novo estado.

A sessão fica salva na pasta `Perfil_WhatsApp`, que é local de cada computador. Em cada máquina nova, é preciso escanear o QR Code novamente.

## Como usar

1. Coloque as imagens e os vídeos na pasta `Status`.
2. Execute o programa com dois cliques em **`Start.bat`** ou pelo terminal:

   ```bash
   py HF_WhatsApp_Status_Publisher.py
   ```

3. O programa aguarda o horário configurado, abre o WhatsApp Web, publica os arquivos e encerra.

## Estrutura de pastas

As pastas abaixo, exceto as que já vêm no repositório, são criadas automaticamente na primeira execução:

```
HF_WhatsApp_Status_Publish/
├── HF_WhatsApp_Status_Publisher.py
├── Installer.bat
├── Start.bat
├── Alternar_Minimizado.bat
├── Config/            # config.json
├── Status/            # imagens e vídeos a publicar
├── Publicados/        # arquivos já publicados
├── Erros/             # capturas de tela e HTML de falhas
├── Logs/              # publicador_status.log
└── Perfil_WhatsApp/   # sessão do navegador (dados de login)
```

## Segurança e privacidade

- A pasta `Perfil_WhatsApp/` contém a **sessão logada da sua conta**. Nunca a envie ao Git nem a compartilhe.
- A pasta `Erros/` pode conter capturas de tela com suas conversas e contatos.
- Todas essas pastas estão listadas no `.gitignore` deste projeto.
- Para encerrar a sessão do programa, remova o aparelho em **WhatsApp > Aparelhos conectados** no celular.

## Solução de problemas

| Problema | O que fazer |
|---|---|
| `Installer.bat` diz "WinGet não encontrado" | Atualize o **App Installer** pela Microsoft Store e execute o instalador novamente |
| "Python Install Manager não foi localizado" | Reinicie o Windows e execute o `Installer.bat` de novo |
| Erro ao instalar o Python Install Manager | Verifique a conexão com a internet e se a Microsoft Store está funcionando; tente novamente |
| Erro ao instalar o Chromium | Verifique a conexão e se antivírus ou firewall não estão bloqueando o download; execute o instalador de novo |
| `python` não é reconhecido ou abre a Microsoft Store | Use `py` no lugar de `python` (inclusive nos arquivos `.bat`) ou reinicie o terminal depois da instalação |
| QR Code não aparece ou não carrega | Confira se `START_MINIMIZED` está em `False` (padrão) e verifique a conexão com a internet |
| "Não encontrei a área Atualizações/Status" | O WhatsApp Web pode ter mudado a interface. Veja os arquivos em `Erros/` e ajuste os seletores |
| "Não encontrei o botão Enviar/Publicar" | Mesmo caso acima: ajuste os seletores em `click_send` |
| A janela não minimiza | Confira o log em `Logs/`. A minimização é feita via Chrome DevTools Protocol |
| "O vídeo não ficou pronto para envio dentro do tempo limite" | Confira se o vídeo é MP4 (H.264 + AAC), com tamanho e duração moderados. Se a prévia não carrega, ative `channel="chrome"` no script. Aumente `VIDEO_SEND_READY_TIMEOUT_MS` se o vídeo for grande |
| Vídeo não é publicado e fica em `Status` | Veja os arquivos em `Erros/` e o log em `Logs/` para identificar a etapa que falhou |

## Aviso

Este projeto automatiza o WhatsApp Web e **não é afiliado, associado ou endossado pelo WhatsApp ou pela Meta**. Esse tipo de automação não é um uso oficialmente suportado e pode, em tese, levar a restrições na conta. Use por sua conta e risco e apenas com suas próprias contas e conteúdos.
