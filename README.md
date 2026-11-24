# HF WhatsApp Status Publisher

Automatiza a publicação diária de imagens no **Status do WhatsApp** usando o WhatsApp Web e o [Playwright](https://playwright.dev/python/).

Coloque as imagens na pasta `Status`, defina o horário de publicação no arquivo `config.json` (dentro da pasta `Config`) e o programa publica tudo sozinho, em ordem alfabética, movendo cada imagem publicada para a pasta `Publicados`.

## Funcionalidades

- Instalador automático: instala o Python, o Playwright e o Chromium com um duplo clique
- Publicação agendada em um horário diário configurável
- Publica todas as imagens (`.jpg`, `.jpeg`, `.png`) da pasta `Status`, em ordem alfabética
- Sessão do WhatsApp salva: o QR Code só precisa ser escaneado uma vez
- Fecha automaticamente pop-ups e avisos do WhatsApp Web
- Janela do navegador minimizada durante a execução
- Duas tentativas por imagem, com captura de tela e HTML para depuração em caso de erro
- Move as imagens publicadas para `Publicados` e mantém em `Status` as que falharam
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

Na primeira execução, o programa cria o arquivo `Config/config.json`:

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
| `START_MINIMIZED` | Minimiza a janela do navegador após abrir |
| `HEADLESS` | Executa sem janela visível (não recomendado, o WhatsApp Web pode se comportar diferente) |
| `INTERVAL_SECONDS` | Intervalo entre uma imagem e outra |
| `CONFIRM_BEFORE_PUBLISHING` | Pede confirmação digitada antes de publicar |

## Primeira execução (QR Code)

1. Rode o `Installer.bat`, se ainda não o fez.
2. Em `HF_WhatsApp_Status_Publisher.py`, coloque `START_MINIMIZED = False`.
3. Coloque ao menos uma imagem na pasta `Status`.
4. Execute `Start.bat` uma vez para o programa criar o `Config/config.json`, depois defina `agendamento_ativo` como `true` e um horário próximo.
5. Execute o programa novamente e escaneie o QR Code com o celular (**WhatsApp > Aparelhos conectados > Conectar um aparelho**).
6. Depois que a sessão estiver salva, volte `START_MINIMIZED` para `True`.

A sessão fica salva na pasta `Perfil_WhatsApp`, que é local de cada computador. Em cada máquina nova, é preciso escanear o QR Code novamente.

## Como usar

1. Coloque as imagens na pasta `Status`.
2. Execute o programa com dois cliques em **`Start.bat`** ou pelo terminal:

   ```bash
   py HF_WhatsApp_Status_Publisher.py
   ```

3. O programa aguarda o horário configurado, abre o WhatsApp Web, publica as imagens e encerra.

## Estrutura de pastas

As pastas abaixo, exceto as que já vêm no repositório, são criadas automaticamente na primeira execução:

```
HF_WhatsApp_Status_Publish/
├── HF_WhatsApp_Status_Publisher.py
├── Installer.bat
├── Start.bat
├── Config/            # config.json
├── Status/            # imagens a publicar
├── Publicados/        # imagens já publicadas
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
| QR Code não aparece ou não carrega | Defina `START_MINIMIZED = False` e verifique a conexão com a internet |
| "Não encontrei a área Atualizações/Status" | O WhatsApp Web pode ter mudado a interface. Veja os arquivos em `Erros/` e ajuste os seletores |
| "Não encontrei o botão Enviar/Publicar" | Mesmo caso acima: ajuste os seletores em `click_send` |
| A janela não minimiza | Confira o log em `Logs/`. A minimização é feita via Chrome DevTools Protocol |

## Aviso

Este projeto automatiza o WhatsApp Web e **não é afiliado, associado ou endossado pelo WhatsApp ou pela Meta**. Esse tipo de automação não é um uso oficialmente suportado e pode, em tese, levar a restrições na conta. Use por sua conta e risco e apenas com suas próprias contas e conteúdos.
