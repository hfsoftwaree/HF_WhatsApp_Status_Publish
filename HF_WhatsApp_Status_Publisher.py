from __future__ import annotations

import json
import logging
import re
import shutil
import sys
import time
import unicodedata

from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


# ---------------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------------

# Diretório onde este arquivo Python está localizado.
BASE_DIR = Path(__file__).resolve().parent

CONFIG_DIR = BASE_DIR / "Config"
CONFIG_FILE = CONFIG_DIR / "config.json"

PENDING_DIR = BASE_DIR / "Status"
PUBLISHED_DIR = BASE_DIR / "Publicados"
ERROR_DIR = BASE_DIR / "Erros"
PROFILE_DIR = BASE_DIR / "Perfil_WhatsApp"
LOG_DIR = BASE_DIR / "Logs"

INTERVAL_SECONDS = 10

PAGE_LOAD_TIMEOUT_MS = 60_000
ELEMENT_TIMEOUT_MS = 15_000

# Esperas de inicialização
INITIAL_CONNECTION_WAIT_SECONDS = 10
STATUS_SYNC_WAIT_SECONDS = 10

# Tempo após fechar cada pop-up
POPUP_WAIT_MS = 700

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# False = navegador visível (mas pode ficar minimizado).
HEADLESS = False

# Minimiza a janela do navegador após abrir.
# Na primeira execução (QR Code), deixe False para poder escanear.
START_MINIMIZED = False

# Inicia automaticamente após conectar ao WhatsApp Web.
CONFIRM_BEFORE_PUBLISHING = False

# Verifica o horário a cada 30 segundos enquanto aguarda.
SCHEDULE_CHECK_SECONDS = 30


# ---------------------------------------------------------------------------
# CONFIGURAÇÃO JSON
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "agendamento_ativo": False,
    "horario_envio": "08:00",
}


def create_config_file() -> None:
    """Cria a pasta Config e o arquivo JSON caso não existam."""

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():

        CONFIG_FILE.write_text(
            json.dumps(
                DEFAULT_CONFIG,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print("Arquivo de configuração criado:")
        print(CONFIG_FILE)


def load_config() -> dict:
    """Carrega e valida as configurações do usuário."""

    create_config_file()

    try:

        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            config = json.load(file)

    except json.JSONDecodeError as error:

        raise RuntimeError(
            f"Arquivo config.json inválido: {error}"
        )

    except OSError as error:

        raise RuntimeError(
            f"Não foi possível ler config.json: {error}"
        )

    if not isinstance(config, dict):
        raise RuntimeError(
            "O conteúdo de config.json deve ser um objeto JSON."
        )

    ativo = config.get("agendamento_ativo")

    if not isinstance(ativo, bool):

        raise RuntimeError(
            "A opção 'agendamento_ativo' deve ser true ou false."
        )

    horario = config.get("horario_envio")

    if not isinstance(horario, str) or not re.fullmatch(
        r"(?:[01]\d|2[0-3]):[0-5]\d",
        horario,
    ):

        raise RuntimeError(
            "Horário inválido em config.json. "
            "Utilize o formato HH:MM, por exemplo 08:00."
        )

    return config


# ---------------------------------------------------------------------------
# AGENDAMENTO
# ---------------------------------------------------------------------------

def wait_for_schedule(config: dict) -> None:
    """
    Aguarda o horário diário configurado.

    Se o programa for iniciado antes do horário,
    aguarda até o horário do mesmo dia.

    Se for iniciado depois do horário, aguarda
    até o próximo dia.

    Não abre o navegador durante a espera.
    """

    horario = datetime.strptime(
        config["horario_envio"],
        "%H:%M",
    ).time()

    now = datetime.now()

    scheduled_datetime = datetime.combine(
        now.date(),
        horario,
    )

    # Se já passou mais de um minuto do horário,
    # considera o próximo dia.
    if now > scheduled_datetime + timedelta(minutes=1):

        scheduled_datetime += timedelta(days=1)

    print("\n==============================================")
    print("       HF WHATSAPP - AGENDAMENTO")
    print("==============================================")
    print("Agendamento      : ATIVADO")
    print(f"Horário definido : {config['horario_envio']}")
    print(
        f"Próxima execução : "
        f"{scheduled_datetime.strftime('%d/%m/%Y %H:%M')}"
    )
    print("==============================================")

    logging.info(
        "Agendamento ativo. Próxima execução: %s",
        scheduled_datetime.strftime("%d/%m/%Y %H:%M"),
    )

    if now < scheduled_datetime:

        print("\nAguardando horário programado...")
        print("O WhatsApp Web ainda não será aberto.")

        while True:

            now = datetime.now()

            remaining = (
                scheduled_datetime - now
            ).total_seconds()

            if remaining <= 0:
                break

            time.sleep(
                min(
                    SCHEDULE_CHECK_SECONDS,
                    remaining,
                )
            )

    print("\nHorário de publicação atingido!")

    logging.info(
        "Horário de publicação atingido. Iniciando processo."
    )


# ---------------------------------------------------------------------------
# LOG
# ---------------------------------------------------------------------------

def configure_logging() -> None:

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOG_DIR / "publicador_status.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


# ---------------------------------------------------------------------------
# PASTAS E ARQUIVOS
# ---------------------------------------------------------------------------

def create_folders() -> None:

    for folder in (
        PENDING_DIR,
        PUBLISHED_DIR,
        ERROR_DIR,
        PROFILE_DIR,
        LOG_DIR,
    ):
        folder.mkdir(parents=True, exist_ok=True)


def get_images() -> list[Path]:
    """Retorna as imagens pendentes em ordem alfabética."""

    return sorted(
        (
            path
            for path in PENDING_DIR.iterdir()
            if path.is_file()
            and path.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda path: path.name.lower(),
    )


def move_file(source: Path, destination_folder: Path) -> Path:
    """Move um arquivo sem sobrescrever outro com o mesmo nome."""

    destination_folder.mkdir(parents=True, exist_ok=True)

    destination = destination_folder / source.name

    if destination.exists():

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        destination = destination_folder / (
            f"{source.stem}_{timestamp}{source.suffix}"
        )

    shutil.move(str(source), str(destination))

    return destination


# ---------------------------------------------------------------------------
# NORMALIZAÇÃO DE TEXTOS
# ---------------------------------------------------------------------------

def normalize_text(value: str) -> str:

    value = unicodedata.normalize("NFKD", value)

    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )

    return value.lower().strip()


# ---------------------------------------------------------------------------
# AUXILIARES PLAYWRIGHT
# ---------------------------------------------------------------------------

def click_first_visible(
    page,
    selectors: Iterable[str],
    description: str,
) -> bool:
    """Tenta clicar no primeiro elemento visível encontrado."""

    for selector in selectors:

        try:

            locator = page.locator(selector).first

            if locator.is_visible(timeout=1_500):

                locator.click(timeout=ELEMENT_TIMEOUT_MS)

                logging.info("Ação: %s", description)

                return True

        except Exception:
            continue

    return False


def save_debug(page, label: str) -> None:
    """Salva screenshot e HTML para ajustar seletores."""

    try:

        ts = time.strftime("%Y%m%d_%H%M%S")

        ERROR_DIR.mkdir(parents=True, exist_ok=True)

        page.screenshot(
            path=str(ERROR_DIR / f"debug_{label}_{ts}.png")
        )

        (ERROR_DIR / f"debug_{label}_{ts}.html").write_text(
            page.content(),
            encoding="utf-8",
        )

        logging.info("Debug salvo em %s (%s)", ERROR_DIR, label)

    except Exception:
        pass


def minimize_window(page) -> None:
    """Minimiza a janela do navegador via Chrome DevTools Protocol."""

    cdp = None

    try:

        cdp = page.context.new_cdp_session(page)

        window = cdp.send("Browser.getWindowForTarget")

        cdp.send(
            "Browser.setWindowBounds",
            {
                "windowId": window["windowId"],
                "bounds": {"windowState": "minimized"},
            },
        )

        logging.info("Janela do navegador minimizada.")

    except Exception as error:

        logging.warning(
            "Não foi possível minimizar a janela: %s",
            error,
        )

    finally:

        if cdp is not None:

            try:
                cdp.detach()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# FECHAR POP-UPS E AVISOS DO WHATSAPP
# ---------------------------------------------------------------------------

def dismiss_popups(page) -> int:
    """
    Procura janelas de propaganda, avisos e apresentações
    do WhatsApp Web e tenta fechá-las.
    """

    dismissed_count = 0

    dismiss_words = [
        "agora nao",
        "not now",
        "fechar",
        "close",
        "entendi",
        "got it",
        "dispensar",
        "dismiss",
        "pular",
        "skip",
        "talvez mais tarde",
        "maybe later",
        "nao obrigado",
        "no thanks",
    ]

    logging.info("Verificando pop-ups do WhatsApp...")

    for attempt in range(8):

        closed_this_round = False

        dialogs = page.locator(
            '[role="dialog"], [aria-modal="true"]'
        )

        try:
            dialog_count = dialogs.count()
        except Exception:
            break

        for dialog_index in range(dialog_count):

            try:

                dialog = dialogs.nth(dialog_index)

                if not dialog.is_visible():
                    continue

                buttons = dialog.locator(
                    'button, [role="button"]'
                )

                button_count = buttons.count()

                for button_index in range(button_count):

                    try:

                        button = buttons.nth(button_index)

                        if not button.is_visible():
                            continue

                        aria_label = (
                            button.get_attribute("aria-label") or ""
                        )

                        title = (
                            button.get_attribute("title") or ""
                        )

                        text = (
                            button.inner_text(timeout=1_000) or ""
                        )

                        description = normalize_text(
                            f"{aria_label} {title} {text}"
                        )

                        should_close = any(
                            word in description
                            for word in dismiss_words
                        )

                        if should_close:

                            button.click(
                                timeout=ELEMENT_TIMEOUT_MS
                            )

                            logging.info(
                                "Pop-up fechado: %s",
                                description[:100],
                            )

                            dismissed_count += 1
                            closed_this_round = True

                            page.wait_for_timeout(POPUP_WAIT_MS)

                            break

                    except Exception:
                        continue

                if not closed_this_round:

                    close_selectors = [
                        'button[aria-label*="fechar" i]',
                        'button[aria-label*="close" i]',
                        '[role="button"][aria-label*="fechar" i]',
                        '[role="button"][aria-label*="close" i]',
                        'button[title*="fechar" i]',
                        'button[title*="close" i]',
                    ]

                    for selector in close_selectors:

                        try:

                            close_button = dialog.locator(
                                selector
                            ).first

                            if close_button.is_visible(
                                timeout=1_000
                            ):

                                close_button.click(
                                    timeout=ELEMENT_TIMEOUT_MS
                                )

                                logging.info(
                                    "Pop-up fechado pelo botão X."
                                )

                                dismissed_count += 1
                                closed_this_round = True

                                page.wait_for_timeout(
                                    POPUP_WAIT_MS
                                )

                                break

                        except Exception:
                            continue

            except Exception:
                continue

        if not closed_this_round:
            break

    logging.info(
        "Verificação de pop-ups concluída. Fechados: %s",
        dismissed_count,
    )

    return dismissed_count


# ---------------------------------------------------------------------------
# RESETAR A INTERFACE
# ---------------------------------------------------------------------------

def reset_ui(page) -> None:
    """Fecha visualizador/editor/menus que ficaram abertos."""

    for _ in range(3):

        page.keyboard.press("Escape")

        page.wait_for_timeout(500)

        click_first_visible(
            page,
            [
                'button:has-text("Descartar")',
                'button:has-text("Discard")',
            ],
            "descartar rascunho",
        )

    dismiss_popups(page)


# ---------------------------------------------------------------------------
# AGUARDAR CONEXÃO DO WHATSAPP
# ---------------------------------------------------------------------------

def wait_for_whatsapp(page) -> None:
    """Aguarda o carregamento da lista de conversas."""

    try:

        page.locator("#side").wait_for(
            state="visible",
            timeout=PAGE_LOAD_TIMEOUT_MS,
        )

    except PlaywrightTimeoutError:

        raise RuntimeError(
            "O WhatsApp Web não confirmou o carregamento "
            "da lista de conversas. Verifique a conexão e o QR Code."
        )

    logging.info("WhatsApp Web conectado.")


# ---------------------------------------------------------------------------
# RECARGA FORÇADA DO WHATSAPP WEB
# ---------------------------------------------------------------------------

def hard_reload_page(page) -> None:
    """
    Recarrega o WhatsApp Web desabilitando temporariamente
    o cache HTTP do navegador.

    Preserva cookies e sessão de autenticação.
    Não apaga os dados do perfil.
    """

    logging.info(
        "Iniciando recarga forçada do WhatsApp Web..."
    )

    print("\nAtualizando completamente o WhatsApp Web...")

    cdp = None

    try:

        cdp = page.context.new_cdp_session(page)

        cdp.send("Network.enable")

        cdp.send(
            "Network.setCacheDisabled",
            {"cacheDisabled": True},
        )

        page.reload(
            wait_until="domcontentloaded",
            timeout=PAGE_LOAD_TIMEOUT_MS,
        )

        wait_for_whatsapp(page)

        logging.info(
            "Recarga forçada concluída."
        )

    except Exception as error:

        logging.warning(
            "Recarga via CDP não concluída: %s. "
            "Tentando recarga convencional.",
            error,
        )

        page.reload(
            wait_until="domcontentloaded",
            timeout=PAGE_LOAD_TIMEOUT_MS,
        )

        wait_for_whatsapp(page)

    finally:

        if cdp is not None:

            try:

                cdp.send(
                    "Network.setCacheDisabled",
                    {"cacheDisabled": False},
                )

                cdp.detach()

            except Exception:
                pass


# ---------------------------------------------------------------------------
# ABRIR ATUALIZAÇÕES / STATUS
# ---------------------------------------------------------------------------

def open_updates(page) -> None:
    """Abre a área Atualizações/Status."""

    selectors = [
        'a[aria-label*="Atualizações" i]',
        'button[aria-label*="Atualizações" i]',
        '[title*="Atualizações" i]',
        'a[aria-label*="Updates" i]',
        'button[aria-label*="Updates" i]',
        '[title*="Updates" i]',
        'a[aria-label*="Status" i]',
        'button[aria-label*="Status" i]',
        '[title*="Status" i]',
        'span[title="Atualizações"]',
        'span[title="Updates"]',
    ]

    if click_first_visible(
        page,
        selectors,
        "abrir Atualizações/Status",
    ):

        page.wait_for_timeout(2_000)

        return

    raise RuntimeError(
        "Não encontrei a área Atualizações/Status. "
        "Verifique se o WhatsApp Web carregou e ajuste os seletores."
    )


# ---------------------------------------------------------------------------
# SINCRONIZAÇÃO INICIAL
# ---------------------------------------------------------------------------

def synchronize_status(page) -> None:
    """
    Executa a sequência de inicialização:

    1. Aguarda conexão.
    2. Fecha pop-ups.
    3. Aguarda estabilização.
    4. Recarrega a página sem cache HTTP.
    5. Fecha novamente eventuais pop-ups.
    6. Abre Atualizações.
    7. Aguarda a sincronização.
    """

    print("\n----------------------------------------------")
    print("SINCRONIZAÇÃO DO WHATSAPP")
    print("----------------------------------------------")

    print("Verificando avisos e propagandas...")

    dismiss_popups(page)

    print(
        f"Aguardando {INITIAL_CONNECTION_WAIT_SECONDS} "
        "segundos..."
    )

    page.wait_for_timeout(
        INITIAL_CONNECTION_WAIT_SECONDS * 1000
    )

    hard_reload_page(page)

    print("Verificando novamente os pop-ups...")

    dismiss_popups(page)

    page.wait_for_timeout(5_000)

    print("Abrindo Atualizações/Status...")

    open_updates(page)

    dismiss_popups(page)

    print(
        f"Aguardando {STATUS_SYNC_WAIT_SECONDS} "
        "segundos para sincronização dos Status..."
    )

    page.wait_for_timeout(
        STATUS_SYNC_WAIT_SECONDS * 1000
    )

    dismiss_popups(page)

    logging.info(
        "Sequência de sincronização inicial concluída."
    )

    print("----------------------------------------------")
    print("SINCRONIZAÇÃO CONCLUÍDA")
    print("----------------------------------------------\n")


# ---------------------------------------------------------------------------
# NOVO STATUS
# ---------------------------------------------------------------------------

def select_add_status_button(page) -> None:
    """
    Abre o fluxo de criação de um novo Status.

    Prioriza o botão "+" / "Adicionar status". Só usa "Meu status"
    como último recurso.
    """

    plus_selectors = [
        'button[aria-label*="Adicionar status" i]',
        '[role="button"][aria-label*="Adicionar status" i]',
        'button[aria-label*="Add status" i]',
        '[role="button"][aria-label*="Add status" i]',
        'button[title*="Adicionar status" i]',
        '[title*="Add status" i]',
        'button:has([data-icon="plus"])',
        'button:has([data-icon="plus-rounded"])',
        '[role="button"]:has([data-icon="plus"])',
        '[role="button"]:has([data-icon="plus-rounded"])',
    ]

    if click_first_visible(
        page,
        plus_selectors,
        "iniciar novo Status (+)",
    ):

        page.wait_for_timeout(1_000)

        return

    logging.warning(
        "Botão '+' não encontrado; tentando 'Meu status'."
    )

    if click_first_visible(
        page,
        [
            'button:has-text("Meu status")',
            'button:has-text("My status")',
            'div[role="button"]:has-text("Meu status")',
            'div[role="button"]:has-text("My status")',
        ],
        "iniciar novo Status (Meu status)",
    ):

        page.wait_for_timeout(1_000)

        return

    raise RuntimeError(
        "Não encontrei o botão para adicionar Status. "
        "A interface do WhatsApp Web pode ter mudado."
    )


# ---------------------------------------------------------------------------
# ANEXAR IMAGEM
# ---------------------------------------------------------------------------

def attach_image(page, image_path: Path) -> None:
    """Anexa a imagem ao editor de Status."""

    file_inputs = page.locator('input[type="file"]')

    try:

        count = file_inputs.count()

        for index in range(count):

            candidate = file_inputs.nth(index)

            accept = (
                candidate.get_attribute("accept") or ""
            ).lower()

            if not accept or "image" in accept or "*" in accept:

                candidate.set_input_files(
                    str(image_path),
                    timeout=ELEMENT_TIMEOUT_MS,
                )

                logging.info(
                    "Imagem selecionada: %s",
                    image_path.name,
                )

                return

    except Exception:
        pass

    buttons = [
        'button[aria-label*="Fotos" i]',
        'button[aria-label*="Photos" i]',
        'button[aria-label*="Galeria" i]',
        'button[aria-label*="Gallery" i]',
        'button[aria-label*="Adicionar" i]',
        'button[aria-label*="Add" i]',
    ]

    for selector in buttons:

        try:

            locator = page.locator(selector).first

            if locator.is_visible(timeout=1_000):

                with page.expect_file_chooser(
                    timeout=5_000
                ) as chooser_info:

                    locator.click()

                chooser_info.value.set_files(
                    str(image_path)
                )

                logging.info(
                    "Imagem selecionada pelo seletor: %s",
                    image_path.name,
                )

                return

        except Exception:
            continue

    menu_items = [
        '[role="menuitem"]:has-text("Fotos e vídeos")',
        '[role="menuitem"]:has-text("Photos & videos")',
        'li:has-text("Fotos e vídeos")',
        'li:has-text("Photos & videos")',
        'div[role="button"]:has-text("Fotos e vídeos")',
        'div[role="button"]:has-text("Photos & videos")',
    ]

    for selector in menu_items:

        try:

            locator = page.locator(selector).first

            if locator.is_visible(timeout=1_500):

                with page.expect_file_chooser(
                    timeout=5_000
                ) as chooser_info:

                    locator.click()

                chooser_info.value.set_files(
                    str(image_path)
                )

                logging.info(
                    "Imagem selecionada pelo menu: %s",
                    image_path.name,
                )

                return

        except Exception:
            continue

    raise RuntimeError(
        "Não consegui anexar a imagem. "
        "O WhatsApp Web pode ter alterado o fluxo de publicação."
    )


# ---------------------------------------------------------------------------
# ENVIAR STATUS
# ---------------------------------------------------------------------------

def click_send(page) -> None:
    """Clica em Enviar/Publicar no editor de Status."""

    selectors = [
        'button[aria-label="Enviar"]',
        'button[aria-label*="Enviar" i]',
        '[role="button"][aria-label*="Enviar" i]',
        'button[aria-label="Send"]',
        'button[aria-label*="Send" i]',
        '[role="button"][aria-label*="Send" i]',
        'button[title="Enviar"]',
        'button[title="Send"]',
        'span[data-icon="send"]',
        'button:has-text("Publicar")',
        'button:has-text("Post")',
    ]

    if click_first_visible(
        page,
        selectors,
        "enviar Status",
    ):
        return

    try:

        icon = page.locator('[data-icon="send"]').last

        if icon.is_visible(timeout=2_000):

            icon.click(timeout=ELEMENT_TIMEOUT_MS)

            logging.info(
                "Ação: clicar no ícone de envio"
            )

            return

    except Exception:
        pass

    raise RuntimeError(
        "Não encontrei o botão Enviar/Publicar. "
        "A imagem pode estar no editor, mas não foi enviada."
    )


# ---------------------------------------------------------------------------
# AGUARDAR PROCESSAMENTO DO ENVIO
# ---------------------------------------------------------------------------

def wait_after_send(page) -> None:
    """
    Espera o envio e devolve a interface a um estado limpo.

    O fechamento do editor não representa confirmação oficial
    da publicação pelo WhatsApp.
    """

    page.wait_for_timeout(3_000)

    try:

        page.locator('[data-icon="send"]').last.wait_for(
            state="hidden",
            timeout=15_000,
        )

    except Exception:

        logging.warning(
            "O editor pode não ter fechado após o envio."
        )

    page.wait_for_timeout(2_000)

    reset_ui(page)


# ---------------------------------------------------------------------------
# PUBLICAR UMA IMAGEM
# ---------------------------------------------------------------------------

def publish_one(page, image_path: Path) -> bool:
    """Executa o fluxo de publicação de uma imagem (com 2 tentativas)."""

    logging.info(
        "Iniciando publicação: %s",
        image_path.name,
    )

    last_error: Exception | None = None

    for attempt in (1, 2):

        try:

            reset_ui(page)

            open_updates(page)

            page.wait_for_timeout(1_500)

            dismiss_popups(page)

            select_add_status_button(page)

            attach_image(page, image_path)

            page.wait_for_timeout(2_000)

            click_send(page)

            wait_after_send(page)

            logging.info(
                "Etapa de envio concluída: %s",
                image_path.name,
            )

            return True

        except Exception as error:

            last_error = error

            logging.warning(
                "Tentativa %s falhou para %s: %s",
                attempt,
                image_path.name,
                error,
            )

            save_debug(
                page,
                f"tentativa{attempt}_{image_path.stem}",
            )

            reset_ui(page)

    raise last_error


# ---------------------------------------------------------------------------
# EXECUÇÃO PRINCIPAL
# ---------------------------------------------------------------------------

def main() -> None:

    # -------------------------------------------------------
    # 1. PRIMEIRO: VERIFICAR A CONFIGURAÇÃO
    # -------------------------------------------------------

    try:

        config = load_config()

    except Exception as error:

        print(f"\nERRO NA CONFIGURAÇÃO: {error}")

        input("\nPressione ENTER para sair...")

        return

    # Cria todas as pastas já na primeira execução,
    # mesmo com o agendamento desativado.
    create_folders()

    # Se desativado, encerra antes de iniciar qualquer
    # navegador ou processo do WhatsApp.

    if not config["agendamento_ativo"]:

        print("\n==============================================")
        print("       HF WHATSAPP STATUS PUBLISHER")
        print("==============================================")
        print("Agendamento desativado.")
        print("O processo não será iniciado.")
        print()
        print("Pastas criadas. Para começar:")
        print(f"1. Coloque as imagens em: {PENDING_DIR}")
        print(f"2. Abra: {CONFIG_FILE}")
        print("   e altere 'agendamento_ativo' para true.")
        print("==============================================\n")

        input("Pressione ENTER para sair...")

        return

    # -------------------------------------------------------
    # 2. CONFIGURAR LOG E AGUARDAR O HORÁRIO
    # -------------------------------------------------------

    configure_logging()

    try:

        wait_for_schedule(config)

    except KeyboardInterrupt:

        logging.warning(
            "Aguardamento interrompido pelo usuário."
        )

        print("\nAguardamento interrompido pelo usuário.")

        return

    # -------------------------------------------------------
    # 3. SOMENTE AGORA PREPARAR O PROCESSO
    # -------------------------------------------------------

    images = get_images()

    print("\n==============================================")
    print("       HF WHATSAPP STATUS PUBLISHER")
    print("==============================================")
    print(f"Pasta de imagens   : {PENDING_DIR}")
    print(f"Imagens encontradas: {len(images)}")
    print(f"Intervalo          : {INTERVAL_SECONDS} segundos")
    print(f"Horário agendado   : {config['horario_envio']}")
    print(f"Navegador          : {'MINIMIZADO' if START_MINIMIZED else 'VISÍVEL'}")
    print("==============================================\n")

    logging.info(
        "Iniciando publicador. Imagens encontradas: %s",
        len(images),
    )

    if not images:

        logging.info(
            "Nenhuma imagem encontrada na pasta Status."
        )

        input("Pressione ENTER para sair...")

        return

    for image_path in images:
        print(f" - {image_path.name}")

    if CONFIRM_BEFORE_PUBLISHING:

        answer = input(
            "\nDigite PUBLICAR para iniciar: "
        ).strip()

        if answer.upper() != "PUBLICAR":

            logging.info(
                "Execução cancelada pelo usuário."
            )

            return

    published_count = 0
    error_count = 0

    try:

        # ---------------------------------------------------
        # 4. INICIAR PLAYWRIGHT E ABRIR WHATSAPP
        # ---------------------------------------------------

        with sync_playwright() as playwright:

            browser_args = []

            launch_options = {}

            if START_MINIMIZED and not HEADLESS:

                # Evita que o Playwright force o tamanho da janela.
                launch_options["no_viewport"] = True

                browser_args += [
                    "--start-minimized",
                    # Impede o Chromium de "dormir" a aba minimizada.
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-background-timer-throttling",
                ]

            else:

                launch_options["viewport"] = {
                    "width": 1365,
                    "height": 900,
                }

            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=HEADLESS,
                args=browser_args,
                **launch_options,
            )

            page = (
                context.pages[0]
                if context.pages
                else context.new_page()
            )

            page.set_default_timeout(
                ELEMENT_TIMEOUT_MS
            )

            page.goto(
                "https://web.whatsapp.com",
                wait_until="domcontentloaded",
            )

            # Minimiza a janela via CDP (a flag --start-minimized
            # sozinha costuma ser ignorada).
            if START_MINIMIZED and not HEADLESS:
                minimize_window(page)

            logging.info(
                "WhatsApp Web iniciado em segundo plano."
                if HEADLESS
                else "WhatsApp Web aberto."
            )

            if HEADLESS:

                print(
                    "\nWhatsApp Web iniciado em segundo plano. "
                    "Aguardando conexão..."
                )

            else:

                print(
                    "\nWhatsApp Web aberto. "
                    "Na primeira execução, escaneie o QR Code com o celular. "
                    "A sessão ficará salva para as próximas execuções."
                )

            # Aguarda a conexão.
            wait_for_whatsapp(page)

            logging.info(
                "WhatsApp Web conectado."
            )

            print("\nWhatsApp conectado com sucesso.")

            # Executa toda a sequência de inicialização.
            synchronize_status(page)

            # Garante que a janela continue minimizada após o reload.
            if START_MINIMIZED and not HEADLESS:
                minimize_window(page)

            # ------------------------------------------------
            # 5. PUBLICAR AS IMAGENS
            # ------------------------------------------------

            for index, image_path in enumerate(images, start=1):

                print(
                    f"\n[{index}/{len(images)}] "
                    f"Publicando: {image_path.name}"
                )

                try:

                    publish_one(
                        page,
                        image_path,
                    )

                    destination = move_file(
                        image_path,
                        PUBLISHED_DIR,
                    )

                    published_count += 1

                    logging.info(
                        "Movida para Publicados: %s",
                        destination.name,
                    )

                except KeyboardInterrupt:

                    logging.warning(
                        "Interrupção solicitada pelo usuário."
                    )

                    raise

                except Exception as error:

                    error_count += 1

                    logging.exception(
                        "Falha ao publicar %s: %s",
                        image_path.name,
                        error,
                    )

                    print(f"ERRO: {error}")

                    print(
                        "A imagem permanecerá na pasta Status "
                        "para conferência. O programa continuará "
                        "com a próxima."
                    )

                # Intervalo entre as imagens.
                if index < len(images):

                    print(
                        f"Aguardando {INTERVAL_SECONDS} segundos "
                        "antes da próxima imagem..."
                    )

                    time.sleep(INTERVAL_SECONDS)

            logging.info(
                "Processamento das imagens concluído."
            )

            context.close()

    except KeyboardInterrupt:

        logging.warning(
            "Programa interrompido."
        )

        print(
            "\nExecução interrompida. "
            "Confira o WhatsApp antes de reiniciar."
        )

    except Exception as error:

        logging.exception(
            "Erro geral: %s",
            error,
        )

        print(
            f"\nERRO GERAL: {error}"
        )

    finally:

        try:
            pending_count = len(get_images())
        except Exception:
            pending_count = -1

        print("\n==============================================")
        print("RESUMO")
        print(f"Publicações concluídas: {published_count}")
        print(f"Falhas: {error_count}")

        if pending_count >= 0:
            print(f"Pendentes: {pending_count}")

        print("==============================================")

        logging.info(
            "Resumo: publicações concluídas=%s | falhas=%s | pendentes=%s",
            published_count,
            error_count,
            pending_count,
        )

        input("\nPressione ENTER para fechar...")


if __name__ == "__main__":
    main()
