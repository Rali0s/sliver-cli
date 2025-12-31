
```
cat <<'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║  ███████╗ ██╗     ██╗ ██╗   ██╗ ███████╗ ██████╗             ║
║  ██╔════╝ ██║     ██║ ██║   ██║ ██╔════╝ ██╔══██╗            ║
║  ███████╗ ██║     ██║ ██║   ██║ █████╗   ██████╔╝            ║
║  ╚════██║ ██║     ██║ ╚██╗ ██╔╝ ██╔══╝   ██╔══██╗            ║
║  ███████║ ███████╗██║  ╚████╔╝  ███████╗ ██║  ██║            ║
║  ╚══════╝ ╚══════╝╚═╝   ╚═══╝   ╚══════╝ ╚═╝  ╚═╝            ║
║                                                              ║
║        SLIVER-CLI — AES-256 Encrypted Notes & CLI Toolkit    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
```

**SLIVER‑AES256‑AutoHost Env for Encrypted Remote Note Sharing**

A lightweight command‑line environment built with Python and Shell tools to enable encrypted remote note sharing, monitoring backends, and CLI utilities in a modular setup. This toolset is built for persistant CLI ops similar to the VERCEL app written in NodeJS Typescript.

The Vercel app makes use of UPSTREAM-Redis Databases.

Our S.L.I.V.E.R App uses a redudant local DB structure between REDIS and Dragonly. Host user will run the autoscript and a persistance Docker-Redis & Docker-Dragonly Node is setup. Enviornment Vars are configured and localhost is utilied only for now. Next, run the notecli_v4.py script to target the local DB in Active State, if down, Dragonfly Takes over by default. Next, issue the unseal or open command via the 'Note' Python app and decrypt the message.

In order for full remote operations via encryption, one will need a DYN-NO-IP Static Nat Address route for the Both DB's to be accessed over remote commands.

---

## 📌 Overview

`sliver‑cli` is a CLI‑centric toolkit designed to help you **manage encrypted notes, automate hosting environments, and monitor backend processes** in an AES‑256 secured workflow. While it shares a name with the Sliver C2 framework, this repository is a **distinct project** focused on encrypted note storage and retrieval via CLI tools.

---

## 🚀 Features

- 🔐 **AES‑256 Encryption**  
  Secure note storage, sharing, and retrieval using AES‑256 encryption.

- 📝 **CLI‑First Tools**  
  Multiple Python scripts provide modular capabilities such as note creation, monitoring, and rendering.

- 🛠️ **Backend Monitors**  
  Scripts like `backend_monitors.py` are included to manage or observe backend processes.

- 🧰 **Shell Integration**  
  Shell utilities (`autogen.sh`) help bootstrap the environment and dependencies.

- 📡 **Portable & Scriptable**  
  Easily integrate with host environments or automate workflows via Bash or Python.

---

## 🧠 Getting Started

### Prerequisites

Make sure you have the following installed:

- Python 3.8+
- pip
- OpenSSL (for encryption support)
- Unix‑like shell (Linux, macOS, WSL recommended)

---

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/Rali0s/sliver‑cli.git
cd sliver‑cli

chmod +x autogen.sh
./autogen.sh

python3 notecli_v4.py create "Meeting notes" --ttl 600 --read 3
python3 notecli_v4.py open "note"
```

## 🧾 Acknowledgements

Inspired by the naming and modular CLI patterns of larger tools, from S.L.I.V.E.R NodeJS Framework by Vercel & Modified for AES256 from AES128

Sliver C2 is a separate open‑source adversary emulation framework. For more on that project (unrelated in codebase), see the BishopFox version.
