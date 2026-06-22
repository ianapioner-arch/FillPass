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
    """Aguarda a janelinha de credenciais aparecer apenas em processos confiáveis (não no Chrome)."""
    # Procura apenas em processos que mostram diálogos de certificado: SecurityAgent e java
    script = (
        'tell application "System Events"\n'
        '  set trusted to {"SecurityAgent", "java", "Java"}\n'
        '  repeat with pname in trusted\n'
        '    try\n'
        '      tell process pname\n'
        '        repeat with w in windows\n'
        '          try\n'
        '            if exists (text field 1 of w) then\n'
        '              set frontmost to true\n'
        '              click text field 1 of w\n'
        '              return "true"\n'
        '            end if\n'
        '          end try\n'
        '        end repeat\n'
        '      end tell\n'
        '    end try\n'
        '  end repeat\n'
        '  return "false"\n'
        'end tell'
    )
    for _ in range(10):
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


def _handle_declaration_modal() -> bool:
    """Marca o checkbox de declaração e clica em OK — apenas se o modal do FepWeb estiver visível."""
    # Só age se houver um checkbox E um botão OK visíveis ao mesmo tempo (modal FepWeb)
    js = (
        "(function(){"
        "var cbs=document.querySelectorAll('input[type=checkbox]');"
        "var visibleCb=Array.from(cbs).filter(function(c){return c.offsetParent!==null;});"
        "if(visibleCb.length===0) return 'no_modal';"
        "var btns=document.querySelectorAll('button,a,[role=button]');"
        "var hasOk=Array.from(btns).some(function(b){"
        "return (b.textContent||'').trim().toLowerCase()==='ok'&&b.offsetParent!==null;"
        "});"
        "if(!hasOk) return 'no_modal';"
        "visibleCb.forEach(function(c){if(!c.checked)c.click();});"
        "return 'ok';"
        "})();"
    )
    result = _run_js(js)
    if result != "ok":
        return False
    time.sleep(0.5)
    # Clica apenas em botão cujo texto seja exatamente "OK"
    js_ok = (
        "(function(){"
        "var btns=document.querySelectorAll('button,a,[role=button]');"
        "for(var i=0;i<btns.length;i++){"
        "var t=(btns[i].textContent||'').trim();"
        "if(t==='OK'&&btns[i].offsetParent!==null){btns[i].click();return 'clicked';}"
        "}"
        "return 'nf';"
        "})();"
    )
    return _run_js(js_ok) == "clicked"


def _check_dialog_now() -> bool:
    """Verifica se já há uma janelinha de credenciais aberta em processos confiáveis."""
    script = (
        'tell application "System Events"\n'
        '  set trusted to {"SecurityAgent", "java", "Java"}\n'
        '  repeat with pname in trusted\n'
        '    try\n'
        '      tell process pname\n'
        '        repeat with w in windows\n'
        '          try\n'
        '            if exists (text field 1 of w) then return "true"\n'
        '          end try\n'
        '        end repeat\n'
        '      end tell\n'
        '    end try\n'
        '  end repeat\n'
        '  return "false"\n'
        'end tell'
    )
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
    return "true" in result.stdout


def sign_all_contracts() -> None:
    """Fluxo completo: Assinar → (Continuar → Certificado se DocuSign) → preenche credenciais."""
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

    # Trata declaração de confirmação se aparecer (FepWeb)
    print("[FillPass] Verificando declaração...")
    if _handle_declaration_modal():
        print("[FillPass] Declaração confirmada, OK clicado.")
        time.sleep(2.0)

    # Aguarda até 6s para ver se a janelinha já apareceu (FepWeb — aparece direto)
    dialog_appeared = False
    for _ in range(6):
        if _check_dialog_now():
            dialog_appeared = True
            break
        time.sleep(1)

    if dialog_appeared:
        print("[FillPass] Janelinha detectada — pulando etapas de certificado.")
    if not dialog_appeared:
        # 2. Aguarda e clica em "Continuar" / "Continue" (DocuSign)
        print("[FillPass] Procurando 'Continuar' / 'Continue'...")
        if _wait_for_button("continuar", "continue", wait_seconds=8):
            print("[FillPass] 'Continuar' clicado.")
            time.sleep(2.0)
        else:
            print("[FillPass] 'Continuar' não encontrado — pulando etapa.")

        # 3. Seleciona o certificado pelo nome (DocuSign)
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

    # Após assinar: clica "Continuar" (se aparecer) e depois "Concluir"
    if count > 0:
        print("[FillPass] Aguardando processamento...")
        time.sleep(3.0)
        if _wait_for_button("continuar", "continue", wait_seconds=10):
            print("[FillPass] 'Continuar' pós-assinatura clicado.")
            time.sleep(2.0)

        # Clica "Concluir"/"Finish" — clica em todos os elementos com esse texto exato
        print("[FillPass] Procurando 'Concluir'...")
        js_concluir = (
            "(function(){"
            "var n=0;"
            "document.querySelectorAll('*').forEach(function(e){"
            "if(e.offsetParent!==null){"
            "var t=e.textContent.trim().toLowerCase();"
            "if(t==='concluir'||t==='finish'){"
            "['mousedown','mouseup','click'].forEach(function(ev){"
            "e.dispatchEvent(new MouseEvent(ev,{bubbles:true,cancelable:true,view:window}));"
            "});"
            "n++;"
            "}"
            "}"
            "});"
            "return n>0?'ok':'nf';"
            "})();"
        )
        found = False
        for _ in range(15):
            if _run_js(js_concluir) == "ok":
                found = True
                break
            time.sleep(1)
        if found:
            print("[FillPass] 'Concluir' clicado. Assinatura finalizada!")


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
