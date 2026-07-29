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
import threading
from pynput import keyboard
from pynput.keyboard import HotKey, Controller, Key

kb_controller = Controller()
_lock = threading.Lock()

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
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except Exception:
        return ""


def _click_buttons_by_text(text: str) -> int:
    """Clica em todos os elementos visíveis que contenham o texto. Procura no documento e iframes."""
    text_lower = text.lower()
    js = (
        "(function(){"
        "var n=0;"
        "function vis(e){var s=window.getComputedStyle(e);if(s.display==='none'||s.visibility==='hidden')return false;var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}"
        "function clickIn(doc){"
        "var els=doc.querySelectorAll('button,a,[role=button],input[type=submit],input[type=button],span,div');"
        "els.forEach(function(e){"
        "var own=(e.childElementCount===0?e.textContent:Array.from(e.childNodes).filter(function(c){return c.nodeType===3;}).map(function(c){return c.textContent;}).join('')).trim().toLowerCase();"
        f"if(own.includes('{text_lower}')&&vis(e)){{e.click();n++;}}"
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
        else:
            # Sem nome informado: fallback para segundo radio (pula certificado de máquina)
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
        "function vis(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}"
        "var tabs=document.querySelectorAll('.signature-tab-content,.tab-content-wrapper');"
        "tabs.forEach(function(e){"
        "if(vis(e)){e.click();n++;}"
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
    """Preenche usuário/senha via pynput — para DocuSign (janelinha já focada)."""
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


def _as_literal(s: str) -> str:
    """Converte string Python para literal AppleScript seguro (trata aspas)."""
    parts = s.split('"')
    return ' & quote & '.join(f'"{p}"' for p in parts)


def _fill_next_dialog() -> bool:
    """Localiza janelinha SecurityAgent/Java e preenche usuário+senha via AppleScript (sem pynput)."""
    user_as = _as_literal(_username)
    pass_as = _as_literal(_password)
    script = (
        'tell application "System Events"\n'
        '  set nomes to {"SecurityAgent", "java", "Java"}\n'
        '  repeat with pname in nomes\n'
        '    try\n'
        '      tell process pname\n'
        '        repeat with w in windows\n'
        '          try\n'
        '            if exists (text field 1 of w) then\n'
        '              set frontmost to true\n'
        '              delay 0.2\n'
        '              click text field 1 of w\n'
        '              delay 0.2\n'
        f'              keystroke {user_as}\n'
        '              key code 48\n'
        '              delay 0.5\n'
        f'              keystroke {pass_as}\n'
        '              key code 36\n'
        '              return "ok"\n'
        '            end if\n'
        '          end try\n'
        '        end repeat\n'
        '      end tell\n'
        '    end try\n'
        '  end repeat\n'
        '  return "nf"\n'
        'end tell'
    )
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=20)
        return "ok" in result.stdout
    except Exception:
        return False


def _focus_next_dialog() -> bool:
    """Aguarda a janelinha de credenciais aparecer apenas em processos confiáveis (não no Chrome)."""
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
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=6,
            )
            if "true" in result.stdout:
                return True
        except Exception:
            pass
        time.sleep(0.5)
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
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=6)
        return "true" in result.stdout
    except Exception:
        return False


def sign_all_contracts() -> None:
    """Fluxo completo: Assinar → (Continuar → Certificado se DocuSign) → preenche credenciais."""
    if not _lock.acquire(blocking=False):
        print("[FillPass] Já em execução — ignorando acionamento duplo.")
        return
    try:
        _sign_all_contracts_impl()
    except Exception as exc:
        import traceback
        print(f"[FillPass] ERRO: {exc}")
        traceback.print_exc()
    finally:
        _lock.release()


def _sign_all_contracts_impl() -> None:
    if not _username or not _password:
        print("[FillPass] Credenciais não disponíveis.")
        return

    # 1. Clica em "Assinar" / "Sign"
    print("[FillPass] Clicando em 'Assinar' / 'Sign'...")
    time.sleep(0.3)
    n = _click_docusign_signature_tabs()
    if n == 0:
        n = _click_buttons_by_text("assinar") + _click_buttons_by_text("sign")
    if n > 0:
        print(f"[FillPass] {n} botão(ões) clicado(s).")
    else:
        print("[FillPass] Nenhum botão 'Assinar'/'Sign' encontrado.")
    time.sleep(1.5)

    # 2. Declaração FepWeb (checkbox + OK)
    print("[FillPass] Verificando declaração...")
    if _handle_declaration_modal():
        print("[FillPass] Declaração confirmada, OK clicado.")
        time.sleep(1.5)

    # 3. Detecta plataforma pelo botão "Continuar":
    #    - DocuSign: aparece "Continuar" → faz fluxo certificado, preenche via pynput
    #    - FepWeb:   sem "Continuar" → janelinha direta, preenche via AppleScript
    print("[FillPass] Procurando 'Continuar' (pré-assinatura)...")
    is_docusign = _wait_for_button("continuar", "continue", wait_seconds=6)

    if is_docusign:
        print("[FillPass] 'Continuar' clicado — fluxo DocuSign.")
        time.sleep(1.5)

        print("[FillPass] Selecionando certificado...")
        if _select_certificate():
            print("[FillPass] Certificado selecionado.")
        else:
            print("[FillPass] Certificado não encontrado — selecione manualmente.")
        time.sleep(0.5)

        for step in range(2):
            print(f"[FillPass] Clicando em 'Avançar' (etapa {step+1})...")
            if _wait_for_button("avan", "next", wait_seconds=8):
                print("[FillPass] 'Avançar' clicado.")
            else:
                print("[FillPass] 'Avançar' não encontrado — pulando.")
                break
            time.sleep(1.5)
    else:
        print("[FillPass] Sem 'Continuar' — fluxo FepWeb.")

    # 4. Preenche credenciais:
    #    DocuSign → pynput (janelinha SecurityAgent/Java já focada pelo _focus_next_dialog)
    #    FepWeb   → AppleScript direto (evita problema de foco)
    count = 0
    while count < 20:
        print("[FillPass] Aguardando janelinha de credenciais...")
        if is_docusign:
            if not _focus_next_dialog():
                if count == 0:
                    print("[FillPass] Nenhuma janelinha encontrada.")
                break
            _fill_one()
            count += 1
            print(f"[FillPass] Janelinha {count} preenchida.")
        else:
            # FepWeb: AppleScript faz tudo (find + fill)
            if not _focus_next_dialog():
                if count == 0:
                    print("[FillPass] Nenhuma janelinha encontrada.")
                break
            if _fill_next_dialog():
                count += 1
                print(f"[FillPass] Janelinha {count} preenchida.")
            else:
                print("[FillPass] Não foi possível preencher a janelinha.")
                break
        time.sleep(0.5)

    print(f"[FillPass] Concluído — {count} janelinha(s) assinada(s).")

    # 5. Pós-assinatura: Continuar → Concluir
    if count > 0:
        print("[FillPass] Aguardando processamento...")
        time.sleep(2.0)
        if _wait_for_button("continuar", "continue", wait_seconds=10):
            print("[FillPass] 'Continuar' pós-assinatura clicado.")
            time.sleep(1.5)

        print("[FillPass] Procurando 'Concluir'...")
        js_concluir = (
            "(function(){"
            "var n=0;"
            "function vis(e){var s=window.getComputedStyle(e);if(s.display==='none'||s.visibility==='hidden')return false;var r=e.getBoundingClientRect();return r.width>0&&r.height>0;}"
            "document.querySelectorAll('*').forEach(function(e){"
            "if(vis(e)){"
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
