#!/usr/bin/env python3
"""FillPass — Autofill de certificado digital via atalho de teclado.

Uso:
  1. Abra o contrato e clique em assinar
  2. Quando a janelinha do certificado aparecer, pressione Ctrl+Shift+F
  3. Confirme no popup e as credenciais são preenchidas automaticamente
"""

import subprocess
import sys
import time
import keyring
from pynput import keyboard
from pynput.keyboard import HotKey, Controller, Key

SERVICE_NAME = "FillPass"
CREDENTIAL_USER_KEY = "certificate_username"
CREDENTIAL_PASS_KEY = "certificate_password"

kb_controller = Controller()


def get_frontmost_app() -> str:
    """Retorna o nome do app em primeiro plano."""
    result = subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to get name of first application process whose frontmost is true'],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def activate_app(app_name: str) -> None:
    """Traz o app de volta ao primeiro plano."""
    subprocess.run(
        ["osascript", "-e", f'tell application "{app_name}" to activate'],
        capture_output=True,
    )


def request_approval() -> bool:
    """Exibe diálogo nativo do macOS — retorna True somente se o usuário clicar OK."""
    script = (
        'display dialog "FillPass vai preencher as credenciais do certificado.\\n\\n'
        'Confirmar?" '
        'buttons {"Cancelar", "OK"} default button "OK" '
        'with title "FillPass" with icon caution'
    )
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    return "OK" in result.stdout


def get_credentials() -> tuple:
    """Busca credenciais do Keychain do macOS. Nunca logadas ou impressas."""
    username = keyring.get_password(SERVICE_NAME, CREDENTIAL_USER_KEY)
    password = keyring.get_password(SERVICE_NAME, CREDENTIAL_PASS_KEY)
    if not username or not password:
        print("[FillPass] Credenciais não configuradas.")
        print("[FillPass] Execute: python3 setup_credentials.py")
        return None, None
    return username, password


def _type_string(text: str) -> None:
    """Digita texto caractere a caractere via teclado virtual."""
    for char in text:
        kb_controller.type(char)
        time.sleep(0.03)


def fill_credentials() -> None:
    """Orquestra: salva foco → pede aprovação → restaura foco → preenche campos."""
    # Salva o app em foco ANTES do popup de aprovação aparecer
    active_app = get_frontmost_app()

    if not request_approval():
        print("[FillPass] Cancelado pelo usuário.")
        return

    username, password = get_credentials()
    if not username:
        return

    try:
        # Volta o foco para a janela do certificado
        activate_app(active_app)
        time.sleep(1.2)

        # Preenche usuário
        _type_string(username)
        time.sleep(0.3)

        # Avança para o campo de senha
        kb_controller.press(Key.tab)
        kb_controller.release(Key.tab)
        time.sleep(0.4)

        # Preenche senha
        _type_string(password)

        print("[FillPass] Credenciais preenchidas.")
    finally:
        # Limpa da memória local imediatamente após uso
        username = None
        password = None


def run() -> None:
    print("=" * 50)
    print("FillPass — Autofill de Certificado Digital")
    print("=" * 50)
    print()
    print("Atalho: Ctrl + Shift + F")
    print()
    print("Como usar:")
    print("  1. Abra o contrato e clique em assinar")
    print("  2. Quando a janelinha do certificado aparecer")
    print("  3. Pressione Ctrl+Shift+F")
    print("  4. Confirme no popup")
    print()
    print("Pressione Ctrl+C para encerrar.")
    print()

    hotkey = HotKey(
        HotKey.parse("<ctrl>+<shift>+f"),
        on_activate=fill_credentials,
    )

    def on_press(key):
        try:
            hotkey.press(kb_listener.canonical(key))
        except Exception:
            pass

    def on_release(key):
        try:
            hotkey.release(kb_listener.canonical(key))
        except Exception:
            pass

    with keyboard.Listener(on_press=on_press, on_release=on_release) as kb_listener:
        try:
            kb_listener.join()
        except KeyboardInterrupt:
            print("\n[FillPass] Encerrando...")


if __name__ == "__main__":
    run()
