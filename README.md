# HF WhatsApp Status Publisher

Automatiza a publicação diária de imagens e vídeos no **Status do WhatsApp** usando o WhatsApp Web e o [Playwright](https://playwright.dev/python/).

Coloque as imagens e os vídeos na pasta `Status`, defina o horário de publicação no arquivo `config.json` (dentro da pasta `Config`) e o programa publica tudo sozinho, em ordem alfabética, movendo cada arquivo publicado para a pasta `Publicados`.

## Funcionalidades

- Instalação com um único arquivo (`InstallerProject.bat`): baixa o programa, cria as pastas e instala o Python, o Playwright e o Chromium
- Atualizações automáticas pelo GitHub, com conferência de integridade (SHA256) e backup dos arquivos substituídos
- Publicação agendada em um horário diário configurável
- Tecla **ESC** para publicar imediatamente, sem esperar o horário
- Publica todas as imagens (`.jpg`, `.jpeg`, `.png`) e vídeos (`.mp4`, `.mov`, `.3gp`) da pasta `Status`, em ordem alfabética
- Espera inteligente para vídeos: aguarda o carregamento no editor antes de enviar
- Sessão do WhatsApp salva: o QR Code só precisa ser escaneado uma vez
- Fecha automaticamente pop-ups e avisos do WhatsApp Web
- Opção de rodar o navegador minimizado durante a execução
- Duas tentativas por arquivo, com captura de tela e HTML para depuração em caso de erro
- Move os arquivos publicados para `Publicados` e mantém em `Status` os que falharam
- Registro das execuções em arquivo de log

## Requisitos

- **Windows 10 ou 11** (o programa usa recursos exclusivos do Windows)
- Conexão com a internet durante a instalação e para as atualizações
- Uma conta de WhatsApp com acesso ao WhatsApp Web

**Você não precisa instalar o Python manualmente.** O `InstallerProject.bat` cuida disso, instalando o Python apenas para o usuário atual do Windows.

## Instalação

1. Baixe o instalador:

   [**InstallerProject.bat**](https://github.com/hfsoftwaree/HF_WhatsApp_Status_Publish/releases/download/installer/InstallerProject.bat)

2. Dê dois cliques no arquivo baixado.

   Se o Windows exibir o aviso *"O Windows protegeu seu computador"* (SmartScreen), clique em **Mais informações** e depois em **Executar assim mesmo**.

3. Aguarde o término. Ao final, o instalador pergunta se você quer criar um atalho na área de trabalho.

O programa é instalado em **`C:\HF_WhatsApp`**. Se precisar reinstalar, basta executar o `InstallerProject.bat` de novo: as pastas `Config`, `Status` e `Perfil_WhatsApp` são preservadas.

### O que o instalador faz

O `InstallerProject.bat` executa dez etapas, mostrando o progresso na tela:

| Etapa | Ação |
|---|---|
| 1/10 | Prepara a pasta `C:\HF_WhatsApp` |
| 2/10 | Baixa o atualizador |
| 3/10 | Baixa os arquivos do programa, conferindo o SHA256 de cada um |
| 4/10 | Cria a estrutura de pastas e o `Config/config.json` (somente se ainda não existir) |
| 5/10 | Baixa e instala a versão estável mais recente do **Python** (instalador oficial do python.org) |
| 6/10 | Atualiza o `pip` |
| 7/10 | Instala o **Playwright** |
| 8/10 | Instala o navegador **Chromium** usado pelo Playwright |
| 9/10 | Verifica as versões instaladas |
| 10/10 | Cria o atalho na área de trabalho (opcional) |

Se alguma etapa falhar, uma mensagem de erro é exibida e a janela aguarda uma tecla antes de fechar.

### Instalação manual (para desenvolvedores)

Com o Python 3.9 ou superior já instalado no Windows:

```bash
git clone https://github.com/hfsoftwaree/HF_WhatsApp_Status_Publish.git
cd HF_WhatsApp_Status_Publish
pip install playwright
python -m playwright install chromium
python HF_WhatsApp_Status_Publisher.py
```

## Atualizações

A cada abertura, o `Start.bat` verifica se existe uma versão nova, de forma silenciosa:

- Os arquivos locais são comparados (SHA256) com o `manifest.json` publicado no [Release `installer`](https://github.com/hfsoftwaree/HF_WhatsApp_Status_Publish/releases/tag/installer) do GitHub.
- Somente os arquivos alterados são baixados, e cada um tem o hash conferido antes de substituir o original. Se algum não bater, a atualização é cancelada e nada é alterado.
- Os arquivos antigos ficam guardados em `Backup_Atualizacao`.
- Sem internet, o programa segue normalmente com a versão instalada.
- Uma nova versão do próprio `Start.bat` é aplicada na abertura seguinte.
- A opção `START_MINIMIZED` escolhida por você é mantida após as atualizações.
- Suas pastas `Config`, `Status`, `Publicados` e `Perfil_WhatsApp` nunca são alteradas.

Para verificar manualmente, dê dois cliques em **`VerificarAtualizacao.bat`**.

## Configuração

O instalador cria o arquivo `Config/config.json` (se ele não existir, o programa também o cria na primeira execução):

```json
{
    "agendamento_ativo": true,
    "horario_envio": "08:00"
}
```

| Campo | Descrição |
|---|---|
| `agendamento_ativo` | `true` para o programa funcionar, `false` para encerrar sem abrir o navegador |
| `horario_envio` | Horário diário da publicação, no formato `HH:MM` (ex.: `08:00`) |

Se o programa for iniciado depois do horário definido (mais de 1 minuto), ele aguarda até o mesmo horário do dia seguinte. Se for iniciado antes, aguarda até o horário do mesmo dia. O navegador só é aberto quando o horário chega.

Durante a espera, pressione **ESC** para publicar imediatamente.

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

1. Execute o `InstallerProject.bat`, se ainda não o fez.
2. Coloque ao menos uma imagem ou vídeo na pasta `Status`.
3. Confira o horário em `Config/config.json` (o padrão é `08:00`).
4. Execute o `Start.bat` (ou o atalho da área de trabalho). Para não esperar o horário agora, pressione **ESC**.
5. Escaneie o QR Code com o celular (**WhatsApp > Aparelhos conectados > Conectar um aparelho**).
6. Depois que a sessão estiver salva, você pode mudar `START_MINIMIZED` para `True` se preferir que o WhatsApp Web rode minimizado, sem ocupar a tela durante a publicação. Se preferir acompanhar o processo na tela, deixe `False`.

   Para alternar sem editar o código, dê dois cliques em **`Alternar_Minimizado.bat`**: cada execução inverte a opção entre `True` e `False` e informa o novo estado.

A sessão fica salva na pasta `Perfil_WhatsApp`, que é local de cada computador. Em cada máquina nova, é preciso escanear o QR Code novamente.

## Como usar

1. Coloque as imagens e os vídeos na pasta `Status`.
2. Execute o programa com dois cliques em **`Start.bat`** (ou no atalho da área de trabalho).
3. O programa aguarda o horário configurado (ou o **ESC**), abre o WhatsApp Web, publica os arquivos e encerra.

> O computador precisa estar ligado e a janela do programa aberta até o horário de publicação.

## Estrutura de pastas

Pasta de instalação (`C:\HF_WhatsApp`). As pastas de dados são criadas automaticamente pelo instalador:

```
C:\HF_WhatsApp\
├── HF_WhatsApp_Status_Publisher.py
├── Start.bat
├── Alternar_Minimizado.bat
├── VerificarAtualizacao.bat
├── VerificarAtualizacao.ps1
├── Config/               # config.json
├── Status/               # imagens e vídeos a publicar
├── Publicados/           # arquivos já publicados
├── Erros/                # capturas de tela e HTML de falhas
├── Logs/                 # publicador_status.log
├── Perfil_WhatsApp/      # sessão do navegador (dados de login)
└── Backup_Atualizacao/   # cópias dos arquivos substituídos nas atualizações
```

## Segurança e privacidade

- A pasta `Perfil_WhatsApp/` contém a **sessão logada da sua conta**. Nunca a envie ao Git nem a compartilhe.
- A pasta `Erros/` pode conter capturas de tela com suas conversas e contatos.
- Todas essas pastas estão listadas no `.gitignore` deste projeto.
- Para encerrar a sessão do programa, remova o aparelho em **WhatsApp > Aparelhos conectados** no celular.
- As atualizações são baixadas apenas do Release deste repositório e conferidas por SHA256, o que detecta arquivos corrompidos ou incompletos.

## Solução de problemas

| Problema | O que fazer |
|---|---|
| O Windows bloqueia o `InstallerProject.bat` (SmartScreen) | Clique em **Mais informações** e depois em **Executar assim mesmo** |
| "Não foi possível baixar os arquivos" | Verifique a conexão com a internet e se antivírus ou firewall não estão bloqueando o download; execute o instalador de novo |
| "ERRO ao instalar Python" | Verifique a conexão (o instalador baixa o Python do python.org) e se o antivírus não está bloqueando; execute o instalador de novo |
| Erro ao instalar o Chromium | Verifique a conexão e se antivírus ou firewall não estão bloqueando o download; execute o instalador de novo |
| `python` não é reconhecido ao abrir o `Start.bat` | Feche e abra o programa novamente ou reinicie o Windows, para o sistema reconhecer o Python recém-instalado. Se persistir, execute o `InstallerProject.bat` de novo |
| "Atualização cancelada" ou "Hash inválido" | O Release pode estar sendo atualizado ou o download foi corrompido. Nada foi alterado; tente novamente mais tarde com o `VerificarAtualizacao.bat` |
| QR Code não aparece ou não carrega | Confira se `START_MINIMIZED` está em `False` (padrão) e verifique a conexão com a internet |
| "Não encontrei a área Atualizações/Status" | O WhatsApp Web pode ter mudado a interface. Veja os arquivos em `Erros/` e ajuste os seletores |
| "Não encontrei o botão Enviar/Publicar" | Mesmo caso acima: ajuste os seletores em `click_send` |
| A janela não minimiza | Confira o log em `Logs/`. A minimização é feita via Chrome DevTools Protocol |
| "O vídeo não ficou pronto para envio dentro do tempo limite" | Confira se o vídeo é MP4 (H.264 + AAC), com tamanho e duração moderados. Se a prévia não carrega, ative `channel="chrome"` no script. Aumente `VIDEO_SEND_READY_TIMEOUT_MS` se o vídeo for grande |
| Vídeo não é publicado e fica em `Status` | Veja os arquivos em `Erros/` e o log em `Logs/` para identificar a etapa que falhou |

## Aviso

Este projeto automatiza o WhatsApp Web e **não é afiliado, associado ou endossado pelo WhatsApp ou pela Meta**. Esse tipo de automação não é um uso oficialmente suportado e pode, em tese, levar a restrições na conta. Use por sua conta e risco e apenas com suas próprias contas e conteúdos.
