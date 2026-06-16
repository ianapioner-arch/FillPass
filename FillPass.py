#!/usr/bin/env python3
"""FillPass — Autofill completo do fluxo de assinatura de certificado digital.

Uso:
  1. Selecione os contratos na plataforma
  2. Pressione Ctrl+Shift+F
  3. O robô faz tudo: Assinar → Continuar → seleciona certificado
     → preenche usuário/senha → clica Permitir em todas as janelinhas!
"""

import subprocess
import sys
import time
import getpass
from pynput import keyboard
from pynput.keyboard import HotKey, Controller, Key

kb_controller = Controller()

_username: str = ""
_password: str = ""
_cert_name: str = ""


def preload_credentials() -> None:
    global _username, _password, _cert_name
    print("Digite as credenciais do certificado digital:")
    _username = input("Usuário: ").strip()
    _password = getpass.getpass("Senha: ")
    _cert_name = input("Parte do seu nome no certificado (ex: IANA): ").strip().upper()
    if not _username or not _password:
        print("[FillPass] Usuário ou senha em branco. Encerrando.")
        sys.exit(1)
    print("[FillPass] Pronto! Credenciais carregadas.\n")


def _run_js(js: str) -> str:
    """Executa JavaScript na aba ativa do Chrome via AppleScript."""
    js_oneline = js.replace("\n", " ")
    script = (
        'tell application "Google Chrome"\n'
        f'    execute active tab of front window javascript "{js_oneline}"\n'
        'end tell'
    )
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
    return result.stdout.strip()


def _click_buttons_by_text(text: str) -> int:
    """Clica em todos os elementos visíveis que contenham o texto. Procura no documento e iframes."""
    text_lower = text.lower()
    js = (
        "(function(){"
        "var n=0;"
        "function clickIn(doc){"
        "var els=doc.querySelectorAll('button,a,[role=button],input[type=submit],input[type=button],span,div');"
        "els.forEach(function(e){"
        "var own=(e.childElementCount===0?e.textContent:Array.from(e.childNodes).filter(function(c){return c.nodeType===3;}).map(function(c){return c.textContent;}).join('')).trim().toLowerCase();"
        f"if(own.includes('{text_lower}')&&e.offsetParent!==null){{e.click();n++;}}"
        "});}"
        "clickIn(document);"
        "var frames=document.querySelectorAll('iframe');"
        "for(var i=0;i<frames.length;i++){"
        "try{clickIn(frames[i].contentDocument||frames[i].contentWindow.document);}catch(e){}}"
        "return n;"
        "})();"
    )
    result = _run_js(js)
    try:
        return int(result)
    except Exception:
        return 0


def _select_certificate() -> bool:
    """Aguarda o modal de certificado carregar e seleciona pelo nome do usuário."""
    name_part = _cert_name.replace("'", "") if _cert_name else ""

    for _ in range(10):
        if name_part:
            js = (
                "(function(){"
                "var radios=document.querySelectorAll('input[type=radio]');"
                "for(var i=0;i<radios.length;i++){"
                "var r=radios[i];"
                "var lbl=r.closest('label')||r.parentElement||document.querySelector('label[for='+JSON.stringify(r.id)+']');"
                "var txt=lbl?lbl.textContent.toUpperCase():'';"
                f"if(txt.includes('{name_part}')){{r.click();return 'ok';}}"
                "}"
                "return 'nf';"
                "})();"
            )
            if _run_js(js) == "ok":
                return True

        # Fallback: segundo radio button (índice 1) — pula o certificado de máquina
        js = (
            "(function(){"
            "var radios=document.querySelectorAll('input[type=radio]');"
            "if(radios.length>1){radios[1].click();return 'ok';}"
            "if(radios.length>0){radios[0].click();return 'ok';}"
            "return 'nf';"
            "})();"
        )
        if _run_js(js) == "ok":
            return True

        time.sleep(1)
    return False


def _click_docusign_signature_tabs() -> int:
    """Clica nos campos de assinatura do DocuSign (botões roxos 'Assinar' no documento)."""
    js = (
        "(function(){"
        "var n=0;"
        "var tabs=document.querySelectorAll('.signature-tab-content,.tab-content-wrapper');"
        "tabs.forEach(function(e){"
        "if(e.offsetParent!==null){e.click();n++;}"
        "});"
        "return n;"
        "})();"
    )
    result = _run_js(js)
    try:
        return int(result)
    except Exception:
        return 0


def _wait_for_button(*texts: str, wait_seconds: int = 10) -> bool:
    """Aguarda até wait_seconds por um botão com qualquer um dos textos e clica."""
    for _ in range(wait_seconds):
        for text in texts:
            if _click_buttons_by_text(text) > 0:
                return True
        time.sleep(1)
    return False


def _type_string(text: str) -> None:
    for char in text:
        kb_controller.type(char)
        time.sleep(0.03)


def _fill_one() -> None:
    """Preenche usuário, senha e clica em Permitir em uma janelinha."""
    time.sleep(0.3)
    _type_string(_username)
    time.sleep(0.5)
    kb_controller.press(Key.tab)
    kb_controller.release(Key.tab)
    time.sleep(0.8)
    _type_string(_password)
    time.sleep(0.3)
    kb_controller.press(Key.enter)
    kb_controller.release(Key.enter)


def _focus_next_dialog() -> bool:
    """Aguarda a janelinha de credenciais aparecer (Chrome ou sistema macOS) e foca no campo."""
    # Primeiro tenta no Chrome (sheets e janelas separadas)
    chrome_script = (
        'tell application "System Events" to tell process "Google Chrome"\n'
        '  try\n'
        '    set s to sheets of front window\n'
        '    if (count s) > 0 then\n'
        '      click text field 1 of item 1 of s\n'
        '      return "true"\n'
        '    end if\n'
        '  end try\n'
        '  repeat with w in windows\n'
        '    try\n'
        '      if exists (text field 1 of w) then\n'
        '        click text field 1 of w\n'
        '        return "true"\n'
        '      end if\n'
        '    end try\n'
        '  end repeat\n'
        '  return "false"\n'
        'end tell'
    )
    # Depois tenta em qualquer processo do sistema (SecurityAgent, etc.)
    system_script = (
        'tell application "System Events"\n'
        '  repeat with p in processes\n'
        '    try\n'
        '      repeat with w in windows of p\n'
        '        try\n'
        '          if exists (text field 1 of w) then\n'
        '            set frontmost of p to true\n'
        '            click text field 1 of w\n'
        '            return "true"\n'
        '          end if\n'
        '        end try\n'
        '      end repeat\n'
        '    end try\n'
        '  end repeat\n'
        '  return "false"\n'
        'end tell'
    )
    for _ in range(10):
        for script in [chrome_script, system_script]:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "true" in result.stdout:
                return True
        time.sleep(1)
    return False


def sign_all_contracts() -> None:
    """Fluxo completo: Assinar → Continuar → seleciona certificado → preenche credenciais."""
    if not _username or not _password:
        print("[FillPass] Credenciais não disponíveis.")
        return

    # 1. Clica em "Assinar" / "Sign" — tenta campos DocuSign primeiro, depois botões genéricos
    print("[FillPass] Clicando em 'Assinar' / 'Sign'...")
    time.sleep(0.5)
    n = _click_docusign_signature_tabs()
    if n == 0:
        n = _click_buttons_by_text("assinar") + _click_buttons_by_text("sign")
    if n > 0:
        print(f"[FillPass] {n} botão(ões) clicado(s).")
    else:
        print("[FillPass] Nenhum botão 'Assinar'/'Sign' encontrado.")
    time.sleep(2.0)

    # 2. Aguarda e clica em "Continuar" / "Continue"
    print("[FillPass] Procurando 'Continuar' / 'Continue'...")
    if _wait_for_button("continuar", "continue", wait_seconds=10):
        print("[FillPass] 'Continuar' clicado.")
        time.sleep(2.0)
    else:
        print("[FillPass] 'Continuar' não encontrado — pulando etapa.")

    # 3. Seleciona o certificado pelo nome
    print("[FillPass] Selecionando certificado...")
    if _select_certificate():
        print("[FillPass] Certificado selecionado.")
    else:
        print("[FillPass] Certificado não encontrado — selecione manualmente.")
    time.sleep(1.0)

    # 3b. Clica em "Avançar" duas vezes (seleção + confirmação do certificado)
    for step in range(2):
        print(f"[FillPass] Clicando em 'Avançar' (etapa {step+1})...")
        if _wait_for_button("avan", "next", wait_seconds=8):
            print("[FillPass] 'Avançar' clicado.")
        else:
            print("[FillPass] 'Avançar' não encontrado — pulando.")
            break
        time.sleep(2.0)

    # 4. Preenche usuário/senha em todas as janelinhas que aparecerem
    count = 0
    while count < 20:
        print("[FillPass] Aguardando janelinha de credenciais...")
        if not _focus_next_dialog():
            if count == 0:
                print("[FillPass] Nenhuma janelinha encontrada.")
            break
        _fill_one()
        count += 1
        print(f"[FillPass] Janelinha {count} preenchida.")
        time.sleep(0.5)

    print(f"[FillPass] Concluído — {count} janelinha(s) assinada(s).")


def run() -> None:
    print("=" * 50)
    print("FillPass — Autofill de Certificado Digital")
    print("=" * 50)
    print()
    print("Atalho: Ctrl + Shift + F")
    print()
    print("Como usar:")
    print("  1. Selecione os contratos na plataforma")
    print("  2. Pressione Ctrl+Shift+F")
    print("  3. O robô faz tudo: Assinar → Continuar → Certificado → Credenciais!")
    print()
    print("Pressione Ctrl+C para encerrar.")
    print()

    preload_credentials()

    hotkey = HotKey(
        HotKey.parse("<ctrl>+<shift>+f"),
        on_activate=sign_all_contracts,
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
