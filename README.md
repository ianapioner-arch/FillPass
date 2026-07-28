# FillPass

Robô que automatiza o fluxo completo de assinatura de contratos com certificado digital.

## Plataformas suportadas

- DocuSign
- FepWeb

---

## O que o robô faz

Ao pressionar **Ctrl + Shift + F**, o robô executa tudo automaticamente:

1. Clica em **Assinar** nos contratos da página
2. Confirma declarações (quando necessário)
3. Seleciona o certificado *(apenas DocuSign)*
4. Preenche **usuário e senha** em todas as janelinhas de autenticação
5. Clica em **Continuar** e **Concluir** para finalizar

---

## 🍎 Instalação no Mac

### 1. Baixe o repositório

Acesse o repositório, clique em **Code → Download ZIP** e extraia na pasta Downloads.

### 2. Instale as dependências

Abra o **Terminal** — Finder → Aplicativos → Utilitários → Terminal — e rode:

```bash
/usr/bin/pip3 install pynput
```

### 3. Permissões de acessibilidade

Na primeira execução, o Mac vai pedir permissão para controlar o teclado:

1. **Apple → Ajustes do Sistema → Privacidade e Segurança**
2. Clique em **Acessibilidade** e ative o **Terminal**
3. Clique em **Monitoramento de Entrada** e ative o **Terminal**

### 4. Inicie o robô

**Opção A — pelo Finder:** clique duas vezes no arquivo **`Iniciar FillPass.command`** dentro da pasta FillPass.

**Opção B — pelo Terminal:**

```bash
/usr/bin/python3 ~/Downloads/FillPass/FillPass.py
```

> **Atenção Mac com ambiente corporativo:** sempre use `/usr/bin/python3` (não `python3`), pois ambientes como Fury podem redirecionar `python3` para um ambiente virtual sem as dependências necessárias.

---

## 🪟 Instalação no Windows

### 1. Baixe o repositório

Acesse o repositório, clique em **Code → Download ZIP** e extraia na pasta Downloads.

### 2. Instale o Python

Baixe em [python.org/downloads](https://python.org/downloads) e instale. Durante a instalação, marque **"Add Python to PATH"**.

### 3. Instale as dependências

Abra o **Prompt de Comando** (tecla Windows → digite `cmd` → Enter) e rode:

```cmd
pip install pynput pywin32
```

### 4. Inicie o robô

Dê dois cliques no arquivo **`Iniciar FillPass.bat`** dentro da pasta FillPass.

---

## Como usar

### 1. Digite suas credenciais

Na inicialização, o robô pede usuário e senha do certificado **uma única vez**:

```
Digite as credenciais do certificado digital:
Usuário: seu_usuario
Senha: (nada aparece enquanto digita — é normal)
Parte do seu nome no certificado (ex: IANA):
```

### 2. Assine seus contratos

1. Abra a plataforma de assinatura no Chrome e selecione os contratos
2. Pressione **Ctrl + Shift + F**
3. ✅ O robô faz todo o resto automaticamente!

---

## Atalho

| Atalho | Ação |
|--------|------|
| `Ctrl + Shift + F` | Inicia o fluxo completo de assinatura |

---

## Segurança

- As credenciais ficam **apenas na memória** durante a sessão
- Nada é salvo em arquivo ou banco de dados
- A cada nova sessão, as credenciais são solicitadas novamente
- O robô só preenche campos em janelinhas de autenticação do sistema operacional — nunca em campos de páginas web

---

## Encerrar o robô

Pressione **Ctrl + C** no Terminal ou Prompt de Comando.
