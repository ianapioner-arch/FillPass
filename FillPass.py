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
import getpass
from pynput import keyboard
from pynput.keyboard import HotKey, Controller, Key

kb_controller = Controller()

# Credenciais carregadas na inicialização — ficam só na memória durante a sessão
_username: str = ""
_password: str = ""


def preload_credentials() -> None:
    """Pede credenciais uma vez ao iniciar. Ficam na memória — sem Keychain durante o uso."""
    global _username, _password
    print("Digite as credenciais do certificado digital:")
    _username = input("Usuário: ").strip()
    _password = getpass.getpass("Senha: ")
    if not _username or not _password:
        print("[FillPass] Usuário ou senha em branco. Encerrando.")
        sys.exit(1)
    print("[FillPass] Pronto! Credenciais carregadas.\n")


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


def _has_dialog() -> bool:
    """Verifica se ainda há uma janelinha de certificado aberta no Chrome."""
    result = subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to tell process "Google Chrome"\n'
         '  if exists (text field 2 of front window) then\n'
         '    return "true"\n'
         '  end if\n'
         '  return "false"\n'
         'end tell'],
        capture_output=True,
        text=True,
    )
    return "true" in result.stdout


def _fill_one() -> None:
    """Preenche usuário, senha e clica em Permitir em uma janelinha."""
    time.sleep(0.3)

    # Preenche usuário no campo atual
    _type_string(_username)
    time.sleep(0.5)

    # Avança para o campo de senha com Tab
    kb_controller.press(Key.tab)
    kb_controller.release(Key.tab)
    time.sleep(0.8)

    # Preenche senha
    _type_string(_password)
    time.sleep(0.3)

    # Clica em Permitir (Enter confirma o botão padrão)
    kb_controller.press(Key.enter)
    kb_controller.release(Key.enter)


def fill_credentials() -> None:
    """Preenche todas as janelinhas de certificado em loop até não restar nenhuma."""
    if not _username or not _password:
        print("[FillPass] Credenciais não disponíveis.")
        return

    count = 0
    max_iterations = 20  # segurança para não rodar infinitamente

    while count < max_iterations:
        _fill_one()
        count += 1
        print(f"[FillPass] Janelinha {count} preenchida.")

        # Aguarda a próxima janelinha aparecer
        time.sleep(1.5)

        if not _has_dialog():
            break

    print(f"[FillPass] Concluído — {count} janelinha(s) assinada(s).")


def run() -> None:
    print("=" * 50)
    print("FillPass — Autofill de Certificado Digital")
    print("=" * 50)
    print()
    print("Atalho: Ctrl + Shift + F")
    print()
    print("Como usar:")
    print("  1. Selecione os contratos e clique em assinar")
    print("  2. Quando a primeira janelinha aparecer, clique no campo de usuário")
    print("  3. Pressione Ctrl+Shift+F")
    print("  4. O robô preenche e clica em Permitir automaticamente em todas!")
    print()
    print("Pressione Ctrl+C para encerrar.")
    print()

    preload_credentials()

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
