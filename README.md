# HF WhatsApp Status Publisher

Automatiza a publicação diária de imagens no **Status do WhatsApp** usando o WhatsApp Web e o [Playwright](https://playwright.dev/python/).

Coloque as imagens na pasta "Status", defina o horário de publicação no arquivo "config.json que esta dentro da pasta Config" e o programa publica tudo sozinho, na ordem alfabética, movendo cada imagem publicada para pasta "Publicados".

## Funcionalidades

- Publicação agendada em um horário diário configurável
- Publica todas as imagens (`.jpg`, `.jpeg`, `.png`) da pasta `Status`, em ordem alfabética
- Sessão do WhatsApp salva: o QR Code só precisa ser escaneado uma vez
- Fecha automaticamente pop-ups e avisos do WhatsApp Web
- Janela do navegador minimizada durante a execução
- Duas tentativas por imagem, com captura de tela e HTML para depuração em caso de erro
- Move as imagens publicadas para `Publicados` e mantém em `Status` as que falharam
- Registro das execuções em arquivo de log

## Requisitos

- Windows (também deve funcionar em Linux/macOS, mas foi testado no Windows)
- Python 3.9 ou superior
- Uma conta de WhatsApp com acesso ao WhatsApp Web

## Instalação

```bash
git clone https://github.com/SEU_USUARIO/HF_WhatsApp_Status_Publish.git
cd HF_WhatsApp_Status_Publish

pip install playwright
playwright install chromium
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

1. Em `HF_WhatsApp_Status_Publisher.py`, coloque `START_MINIMIZED = False`.
2. Coloque ao menos uma imagem na pasta `Status`.
3. Defina `agendamento_ativo` como `true` e um horário próximo.
4. Execute o programa e escaneie o QR Code com o celular (**WhatsApp > Aparelhos conectados > Conectar um aparelho**).
5. Depois que a sessão estiver salva, volte `START_MINIMIZED` para `True`.

## Como usar

1. Coloque as imagens na pasta `Status`.
2. Execute o programa:

   ```bash
   python HF_WhatsApp_Status_Publisher.py
   ```

   ou dê dois cliques em `iniciar.bat`.
3. O programa aguarda o horário configurado, abre o WhatsApp Web, publica as imagens e encerra.

## Estrutura de pastas

As pastas abaixo são criadas automaticamente na primeira execução:

```
HF_WhatsApp_Status_Publish/
├── HF_WhatsApp_Status_Publisher.py
├── iniciar.bat
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
| QR Code não aparece ou não carrega | Defina `START_MINIMIZED = False` e verifique a conexão com a internet |
| "Não encontrei a área Atualizações/Status" | O WhatsApp Web pode ter mudado a interface. Veja os arquivos em `Erros/` e ajuste os seletores |
| "Não encontrei o botão Enviar/Publicar" | Mesmo caso acima: ajuste os seletores em `click_send` |
| A janela não minimiza | Confira o log em `Logs/`. A minimização é feita via Chrome DevTools Protocol |
| `python` abre a Microsoft Store | Use `py` no lugar de `python` no `.bat` |

## Aviso

Este projeto automatiza o WhatsApp Web e **não é afiliado, associado ou endossado pelo WhatsApp ou pela Meta**. Esse tipo de automação não é um uso oficialmente suportado e pode, em tese, levar a restrições na conta. Use por sua conta e risco e apenas com suas próprias contas e conteúdos.
