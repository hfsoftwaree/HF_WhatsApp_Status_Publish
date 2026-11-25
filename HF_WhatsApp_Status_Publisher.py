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

INITIAL_CONNECTION_WAIT_SECONDS = 10
STATUS_SYNC_WAIT_SECONDS = 10

POPUP_WAIT_MS = 700

# --- Tipos de arquivo aceitos ---------------------------------------------
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".3gp"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# --- Ajustes específicos para vídeo ---------------------------------------
# Tempo máximo esperando o botão Enviar ficar disponível (vídeo).
VIDEO_SEND_READY_TIMEOUT_MS = 120_000
# Tempo máximo esperando o editor fechar após enviar (vídeo).
VIDEO_AFTER_SEND_TIMEOUT_MS = 90_000
# Espera extra de estabilização após o editor carregar o vídeo.
VIDEO_SETTLE_MS = 3_000
# Avisa no log se o vídeo passar deste tamanho (o WhatsApp pode recusar).
VIDEO_MAX_RECOMMENDED_MB = 16

HEADLESS = False
START_MINIMIZED = True
CONFIRM_BEFORE_PUBLISHING = False
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
    """Aguarda o horário diário configurado (sem abrir o navegador)."""

    horario = datetime.strptime(
        config["horario_envio"],
        "%H:%M",
    ).time()

    now = datetime.now()

    scheduled_datetime = datetime.combine(
        now.date(),
        horario,
    )

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


def is_video(path: Path) -> bool:
    """Indica se o arquivo é um vídeo."""

    return path.suffix.lower() in VIDEO_EXTENSIONS


def get_media_files() -> list[Path]:
    """Retorna imagens e vídeos pendentes em ordem alfabética."""

    return sorted(
        (
            path
            for path in PENDING_DIR.iterdir()
            if path.is_file()
            and path.suffix.lower() in MEDIA_EXTENSIONS
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
    """Procura avisos/propagandas do WhatsApp Web e tenta fechá-los."""

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
    """Recarrega o WhatsApp Web sem cache HTTP (preserva a sessão)."""

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
    """Sequência de inicialização antes de publicar."""

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
    """Abre o fluxo de criação de um novo Status."""

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
# ANEXAR MÍDIA (IMAGEM OU VÍDEO)
# ---------------------------------------------------------------------------

def attach_media(page, media_path: Path) -> None:
    """Anexa a imagem ou o vídeo ao editor de Status."""

    video = is_video(media_path)
    kind = "vídeo" if video else "imagem"

    if video:

        size_mb = media_path.stat().st_size / (1024 * 1024)

        if size_mb > VIDEO_MAX_RECOMMENDED_MB:

            logging.warning(
                "O vídeo %s tem %.1f MB (recomendado até %s MB). "
                "O WhatsApp pode recusar ou demorar mais.",
                media_path.name,
                size_mb,
                VIDEO_MAX_RECOMMENDED_MB,
            )

    # --- 1ª tentativa: input[type=file] direto ---------------------------
    file_inputs = page.locator('input[type="file"]')

    try:

        count = file_inputs.count()

        # Para vídeo, prioriza inputs que declaram aceitar vídeo.
        ordered_indexes = list(range(count))

        if video:

            def accepts_video(index: int) -> bool:

                try:

                    accept = (
                        file_inputs.nth(index).get_attribute("accept")
                        or ""
                    ).lower()

                except Exception:
                    return False

                return "video" in accept

            ordered_indexes.sort(
                key=lambda index: 0 if accepts_video(index) else 1
            )

        for index in ordered_indexes:

            candidate = file_inputs.nth(index)

            accept = (
                candidate.get_attribute("accept") or ""
            ).lower()

            if video:
                compatible = (
                    not accept or "video" in accept or "*" in accept
                )
            else:
                compatible = (
                    not accept or "image" in accept or "*" in accept
                )

            if compatible:

                candidate.set_input_files(
                    str(media_path),
                    timeout=ELEMENT_TIMEOUT_MS,
                )

                logging.info(
                    "Arquivo (%s) selecionado: %s",
                    kind,
                    media_path.name,
                )

                return

    except Exception:
        pass

    # --- 2ª tentativa: botões que abrem o seletor de arquivos ------------
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
                    str(media_path)
                )

                logging.info(
                    "Arquivo (%s) selecionado pelo botão: %s",
                    kind,
                    media_path.name,
                )

                return

        except Exception:
            continue

    # --- 3ª tentativa: itens de menu -------------------------------------
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
                    str(media_path)
                )

                logging.info(
                    "Arquivo (%s) selecionado pelo menu: %s",
                    kind,
                    media_path.name,
                )

                return

        except Exception:
            continue

    raise RuntimeError(
        f"Não consegui anexar o {kind}. "
        "O WhatsApp Web pode ter alterado o fluxo de publicação."
    )


# ---------------------------------------------------------------------------
# AGUARDAR O EDITOR FICAR PRONTO PARA ENVIAR
# ---------------------------------------------------------------------------

SEND_SELECTORS = [
    'button[aria-label="Enviar"]',
    'button[aria-label*="Enviar" i]',
    '[role="button"][aria-label*="Enviar" i]',
    'button[aria-label="Send"]',
    'button[aria-label*="Send" i]',
    '[role="button"][aria-label*="Send" i]',
    'button[title="Enviar"]',
    'button[title="Send"]',
    'span[data-icon="send"]',
]


def wait_for_send_ready(page, media_path: Path) -> None:
    """
    Aguarda o editor carregar a mídia e o botão de envio aparecer.

    Imagens: espera curta.
    Vídeos: espera até o botão Enviar ficar visível e habilitado
    (o WhatsApp processa o vídeo antes de liberar o envio).
    """

    if not is_video(media_path):

        page.wait_for_timeout(2_000)

        return

    logging.info(
        "Aguardando o vídeo carregar no editor: %s",
        media_path.name,
    )

    deadline = time.monotonic() + (
        VIDEO_SEND_READY_TIMEOUT_MS / 1000
    )

    while time.monotonic() < deadline:

        for selector in SEND_SELECTORS:

            try:

                locator = page.locator(selector).last

                if not locator.is_visible(timeout=500):
                    continue

                # Se o botão estiver desabilitado, continua esperando.
                disabled = page.evaluate(
                    """
                    (el) => {
                        const btn = el.closest('button, [role="button"]') || el;
                        return btn.disabled === true
                            || btn.getAttribute('aria-disabled') === 'true';
                    }
                    """,
                    locator.element_handle(),
                )

                if not disabled:

                    page.wait_for_timeout(VIDEO_SETTLE_MS)

                    logging.info(
                        "Vídeo pronto para envio."
                    )

                    return

            except Exception:
                continue

        page.wait_for_timeout(1_000)

    raise RuntimeError(
        "O vídeo não ficou pronto para envio dentro do tempo limite. "
        "Verifique formato (MP4 H.264/AAC), duração e tamanho."
    )


# ---------------------------------------------------------------------------
# ENVIAR STATUS
# ---------------------------------------------------------------------------

def click_send(page) -> None:
    """Clica em Enviar/Publicar no editor de Status."""

    selectors = SEND_SELECTORS + [
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
        "A mídia pode estar no editor, mas não foi enviada."
    )


# ---------------------------------------------------------------------------
# AGUARDAR PROCESSAMENTO DO ENVIO
# ---------------------------------------------------------------------------

def wait_after_send(page, media_path: Path) -> None:
    """
    Espera o envio e devolve a interface a um estado limpo.

    O fechamento do editor não representa confirmação oficial
    da publicação pelo WhatsApp.
    """

    page.wait_for_timeout(3_000)

    timeout = (
        VIDEO_AFTER_SEND_TIMEOUT_MS
        if is_video(media_path)
        else 15_000
    )

    try:

        page.locator('[data-icon="send"]').last.wait_for(
            state="hidden",
            timeout=timeout,
        )

    except Exception:

        logging.warning(
            "O editor pode não ter fechado após o envio."
        )

    page.wait_for_timeout(
        4_000 if is_video(media_path) else 2_000
    )

    reset_ui(page)


# ---------------------------------------------------------------------------
# PUBLICAR UM ARQUIVO
# ---------------------------------------------------------------------------

def publish_one(page, media_path: Path) -> bool:
    """Executa o fluxo de publicação de uma imagem ou vídeo (2 tentativas)."""

    logging.info(
        "Iniciando publicação (%s): %s",
        "vídeo" if is_video(media_path) else "imagem",
        media_path.name,
    )

    last_error: Exception | None = None

    for attempt in (1, 2):

        try:

            reset_ui(page)

            open_updates(page)

            page.wait_for_timeout(1_500)

            dismiss_popups(page)

            select_add_status_button(page)

            attach_media(page, media_path)

            wait_for_send_ready(page, media_path)

            click_send(page)

            wait_after_send(page, media_path)

            logging.info(
                "Etapa de envio concluída: %s",
                media_path.name,
            )

            return True

        except Exception as error:

            last_error = error

            logging.warning(
                "Tentativa %s falhou para %s: %s",
                attempt,
                media_path.name,
                error,
            )

            save_debug(
                page,
                f"tentativa{attempt}_{media_path.stem}",
            )

            reset_ui(page)

    raise last_error


# ---------------------------------------------------------------------------
# EXECUÇÃO PRINCIPAL
# ---------------------------------------------------------------------------

def main() -> None:

    # 1. Verificar a configuração
    try:

        config = load_config()

    except Exception as error:

        print(f"\nERRO NA CONFIGURAÇÃO: {error}")

        input("\nPressione ENTER para sair...")

        return

    create_folders()

    if not config["agendamento_ativo"]:

        print("\n==============================================")
        print("       HF WHATSAPP STATUS PUBLISHER")
        print("==============================================")
        print("Agendamento desativado.")
        print("O processo não será iniciado.")
        print()
        print("Pastas criadas. Para começar:")
        print(f"1. Coloque imagens/vídeos em: {PENDING_DIR}")
        print(f"2. Abra: {CONFIG_FILE}")
        print("   e altere 'agendamento_ativo' para true.")
        print("==============================================\n")

        input("Pressione ENTER para sair...")

        return

    # 2. Log e espera do horário
    configure_logging()

    try:

        wait_for_schedule(config)

    except KeyboardInterrupt:

        logging.warning(
            "Aguardamento interrompido pelo usuário."
        )

        print("\nAguardamento interrompido pelo usuário.")

        return

    # 3. Preparar o processo
    media_files = get_media_files()

    video_count = sum(1 for path in media_files if is_video(path))
    image_count = len(media_files) - video_count

    print("\n==============================================")
    print("       HF WHATSAPP STATUS PUBLISHER")
    print("==============================================")
    print(f"Pasta de mídias    : {PENDING_DIR}")
    print(f"Arquivos           : {len(media_files)} "
          f"({image_count} imagem(ns), {video_count} vídeo(s))")
    print(f"Intervalo          : {INTERVAL_SECONDS} segundos")
    print(f"Horário agendado   : {config['horario_envio']}")
    print(f"Navegador          : {'MINIMIZADO' if START_MINIMIZED else 'VISÍVEL'}")
    print("==============================================\n")

    logging.info(
        "Iniciando publicador. Arquivos encontrados: %s "
        "(imagens=%s, vídeos=%s)",
        len(media_files),
        image_count,
        video_count,
    )

    if not media_files:

        logging.info(
            "Nenhum arquivo encontrado na pasta Status."
        )

        input("Pressione ENTER para sair...")

        return

    for media_path in media_files:

        tag = "VÍDEO " if is_video(media_path) else "IMAGEM"

        print(f" - [{tag}] {media_path.name}")

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

        # 4. Iniciar Playwright e abrir WhatsApp
        with sync_playwright() as playwright:

            browser_args = []

            launch_options = {}

            if START_MINIMIZED and not HEADLESS:

                launch_options["no_viewport"] = True

                browser_args += [
                    "--start-minimized",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-background-timer-throttling",
                ]

            else:

                launch_options["viewport"] = {
                    "width": 1365,
                    "height": 900,
                }

            # Observação: o Chromium do Playwright não inclui alguns
            # codecs proprietários (H.264/AAC), mas isso afeta apenas
            # a PRÉ-VISUALIZAÇÃO do vídeo no editor. O arquivo é enviado
            # normalmente. Se a prévia não carregar e o envio falhar,
            # troque para o Chrome instalado adicionando channel="chrome"
            # abaixo.
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=HEADLESS,
                args=browser_args,
                # channel="chrome",
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

            wait_for_whatsapp(page)

            logging.info(
                "WhatsApp Web conectado."
            )

            print("\nWhatsApp conectado com sucesso.")

            synchronize_status(page)

            if START_MINIMIZED and not HEADLESS:
                minimize_window(page)

            # 5. Publicar os arquivos
            for index, media_path in enumerate(media_files, start=1):

                tag = "vídeo" if is_video(media_path) else "imagem"

                print(
                    f"\n[{index}/{len(media_files)}] "
                    f"Publicando ({tag}): {media_path.name}"
                )

                try:

                    publish_one(
                        page,
                        media_path,
                    )

                    destination = move_file(
                        media_path,
                        PUBLISHED_DIR,
                    )

                    published_count += 1

                    logging.info(
                        "Movido para Publicados: %s",
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
                        media_path.name,
                        error,
                    )

                    print(f"ERRO: {error}")

                    print(
                        "O arquivo permanecerá na pasta Status "
                        "para conferência. O programa continuará "
                        "com o próximo."
                    )

                if index < len(media_files):

                    print(
                        f"Aguardando {INTERVAL_SECONDS} segundos "
                        "antes do próximo arquivo..."
                    )

                    time.sleep(INTERVAL_SECONDS)

            logging.info(
                "Processamento dos arquivos concluído."
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
            pending_count = len(get_media_files())
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
