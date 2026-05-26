#!/usr/bin/env python3
"""Configuração inicial — salva credenciais do certificado no Keychain do macOS."""

import getpass
import keyring

SERVICE_NAME = "FillPass"
CREDENTIAL_USER_KEY = "certificate_username"
CREDENTIAL_PASS_KEY = "certificate_password"


def main() -> None:
    print("=" * 50)
    print("FillPass — Configuração de Credenciais")
    print("=" * 50)
    print("As credenciais serão salvas no Keychain do macOS.")
    print("Nunca gravadas em arquivo ou código.\n")

    username = input("Usuário do certificado digital (CPF, email ou login): ").strip()
    if not username:
        print("Erro: usuário não pode ser vazio.")
        return

    password = getpass.getpass("Senha do certificado digital: ")
    if not password:
        print("Erro: senha não pode ser vazia.")
        return

    keyring.set_password(SERVICE_NAME, CREDENTIAL_USER_KEY, username)
    keyring.set_password(SERVICE_NAME, CREDENTIAL_PASS_KEY, password)

    # Limpa da memória local imediatamente
    password = None

    print("\nCredenciais salvas com segurança no Keychain do macOS.")
    print("Para iniciar o robô: python FillPass.py")
    print("\nPara atualizar a senha no futuro, execute este script novamente.")


if __name__ == "__main__":
    main()
