# FillPass 🔐

Robô que preenche automaticamente as credenciais do certificado digital nas plataformas de assinatura, após confirmação do usuário.

## Plataformas suportadas

- DocuSign
- FepWeb
- CertiSign
- Gov.Br

---

## Pré-requisitos

- Mac com macOS 12 ou superior
- Python 3 instalado
- Terminal

---

## Instalação (primeira vez)

### 1. Baixe o repositório

Acesse [github.com/ianapioner-arch/FillPass](https://github.com/ianapioner-arch/FillPass), clique em **Code → Download ZIP** e extraia na pasta Downloads.

### 2. Instale as dependências

Abra o Terminal (**Command ⌘ + Espaço → Terminal**) e rode:

```bash
cd ~/Downloads/FillPass
pip3 install pynput pyautogui
```

### 3. Permissão de teclado

Na primeira execução, o Mac vai pedir permissão para monitorar o teclado:

1. **Apple () → Ajustes do Sistema → Privacidade e Segurança**
2. Clique em **Acessibilidade** e ative o **Terminal**
3. Clique em **Monitoramento de Entrada** e ative o **Terminal**

---

## Como usar

### 1. Inicie o robô

```bash
python3 ~/Downloads/FillPass/FillPass.py
```

### 2. Digite suas credenciais

Na inicialização, o robô pede o usuário e senha do certificado **uma única vez**:

```
Digite as credenciais do certificado digital:
Usuário: seu_usuario
Senha: (nada aparece enquanto digita — é normal)
```

### 3. Assine seus contratos

1. Selecione os contratos e clique em assinar
2. Quando a primeira janelinha aparecer, **clique no campo de usuário**
3. Pressione **Ctrl + Shift + F**
4. ✅ O robô preenche usuário, senha e clica em **Permitir** automaticamente em todas as janelinhas!

---

## Atalho

| Atalho | Ação |
|--------|------|
| `Ctrl + Shift + F` | Preenche as credenciais do certificado |

---

## Segurança

- As credenciais ficam **apenas na memória** durante a sessão
- Nada é salvo em arquivo ou banco de dados
- A cada nova sessão, as credenciais são solicitadas novamente

---

## Encerrar o robô

No Terminal, pressione **Ctrl + C**.
