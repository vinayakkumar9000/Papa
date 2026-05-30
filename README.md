<div align="center">

# 🚀 Papa

## Local AI-Powered Wallet Orchestration Platform

**Generate, manage, export, inspect, and orchestrate EVM wallets through a local-first Python CLI with Ollama-powered AI routing.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](#-installation)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-000000?style=for-the-badge&logo=ollama&logoColor=white)](#-how-ai-works)
[![Qwen](https://img.shields.io/badge/Qwen2.5-3B-6C5CE7?style=for-the-badge)](#-how-ai-works)
[![SQLite](https://img.shields.io/badge/SQLite-Local_Storage-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](#-database-layer)
[![Web3.py](https://img.shields.io/badge/Web3.py-EVM_Transactions-F16822?style=for-the-badge)](#-transaction-layer)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

> **Mission:** make wallet operations, transaction workflows, and AI-assisted blockchain automation usable from a private, local, inspectable developer workstation — without requiring a cloud AI dependency.

</div>

---

## 📚 Table of Contents

- [Why This Project Exists](#-why-this-project-exists)
- [Features](#-features)
- [Architecture Overview](#-architecture-overview)
- [Core Components](#-core-components)
- [How AI Works](#-how-ai-works)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage Examples](#-usage-examples)
- [Screenshots](#-screenshots)
- [Why You Might Find This Useful](#-why-you-might-find-this-useful)
- [AI Disclosure](#-ai-disclosure)
- [Open Source Contribution](#-open-source-contribution)
- [Issue Reporting](#-issue-reporting)
- [Pull Request Guide](#-pull-request-guide)
- [Community](#-community)
- [FAQ](#-faq)
- [Roadmap](#-roadmap)
- [Technical Highlights](#-technical-highlights)
- [Credits](#-credits)

---

## 🌍 Why This Project Exists

Wallet tooling has historically been split across isolated scripts, web dashboards, one-off CLIs, manual spreadsheets, and external automation glue. Developers often have to combine several unrelated tools just to answer basic operational questions:

- **Where are my generated wallets stored?**
- **Which wallet has funds on a network?**
- **How do I export wallet records safely?**
- **Can I execute a transaction without switching tools?**
- **Can an AI assistant help route commands without sending sensitive context to a cloud provider?**

Papa started as an **EVM wallet generator** with **SQLite wallet storage**, export utilities, and a transaction engine. It has since evolved into a **local AI-powered wallet orchestration platform**.

### ✨ The Vision

Papa is designed around a simple idea:

> **Wallet automation should be local, inspectable, scriptable, AI-assisted, and privacy-conscious by default.**

That means:

| Principle | What It Means |
|---|---|
| 🔐 **Local-first** | Wallet records, AI routing, prompts, and operational workflows are intended to run on your machine. |
| 🧠 **AI-assisted, not AI-trusted blindly** | Natural language can be interpreted into structured tool calls, while permission checks keep sensitive actions explicit. |
| 🧱 **Composable architecture** | Wallet generation, transaction sending, database access, exports, AI routing, and CLI interfaces are separated into modules. |
| 🧰 **Developer-oriented** | The project favors transparent Python code, SQLite storage, CLI commands, logs, migrations, and readable configuration files. |
| 🤖 **Automation-ready** | Papa can be used as a CLI utility, a wallet data layer, or a foundation for AI-powered wallet operations. |

---

## ✨ Features

### 🔎 Feature Matrix

| Category | Capability | Status | Notes |
|---|---:|---:|---|
| 👛 Wallet Management | Generate EVM-compatible wallets | ✅ Available | Uses Python wallet generation utilities and SQLite persistence. |
| 👛 Wallet Management | List wallets | ✅ Available | Rich-powered CLI tables hide private keys in normal wallet listings. |
| 👛 Wallet Management | Tag generated wallets | ✅ Available | AI tools can tag recently generated wallets when supported by the database layer. |
| 💸 Transactions | Send native token transactions | ✅ Available | Uses Web3.py with configurable chain settings. |
| 💸 Transactions | Batch native transfers | ✅ Available | Supports repeated transfers from available database wallets. |
| 💸 Transactions | Transaction history | ✅ Available | Stores and displays transaction records from SQLite. |
| 🧠 AI | Local Ollama inference | ✅ Available | Default model target is `qwen2.5:3b`. |
| 🧠 AI | Regex fallback parser | ✅ Available | Keeps supported prompt parsing available if Ollama is unavailable. |
| 🧠 AI | Structured tool calls | ✅ Available | AI output is constrained to allow-listed tools. |
| 🧠 AI | AI memory | ✅ Available | Intent/output memory can be stored through the database-backed memory layer. |
| 🗄️ Database | SQLite wallet storage | ✅ Available | Local `wallets.db` workflow by default. |
| 🗄️ Database | SQL migrations | ✅ Available | Versioned migrations live in `database/migrations/`. |
| ⚙️ Automation | Export wallets | ✅ Available | Existing export tooling supports multiple file-oriented workflows. |
| 🖥️ CLI | Typer command interface | ✅ Available | `papa.py` exposes wallet, transaction, AI, network, and diagnostic commands. |
| 📊 Monitoring | Logs | ✅ Available | Runtime logs are organized under `logs/`. |
| 🌐 Networks | Configurable EVM networks | ✅ Available | Network config is read from `config/networks.json` and CLI network commands. |

### 🧩 Capability Overview

| Area | What You Can Do |
|---|---|
| **Wallets** | Generate wallets, list stored wallets, reference wallets by ID/address/tag where supported. |
| **Balances** | Check native token balances for a wallet on a configured chain. |
| **Transactions** | Send native token transfers, batch sends, review local transaction history. |
| **AI Routing** | Convert supported natural-language prompts into structured tool calls through local Ollama inference or parser fallback. |
| **Exports** | Export wallet data through the converter/export utilities. |
| **Database** | Store wallet records, transactions, networks, balance cache, AI memory, and schema metadata locally. |
| **Networks** | List, add, or remove configured EVM networks from the CLI. |

---

## 🏗️ Architecture Overview

Papa is organized as a layered local orchestration system. The AI layer does not replace the wallet engine — it sits above it and translates supported natural language into explicit tool calls.

```text
┌───────────────────────────────────────────────────────────────────┐
│                               User                                │
│          CLI commands • natural language prompts • scripts         │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                            CLI Layer                              │
│       Typer commands • Rich tables • interactive terminal          │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│            AI Layer           │   │        Direct Commands         │
│ Ollama • Qwen2.5 • parser     │   │ wallets • send • balance      │
│ prompts • memory • router     │   │ networks • tx-history         │
└───────────────┬───────────────┘   └───────────────┬───────────────┘
                │                                   │
                ▼                                   ▼
┌───────────────────────────────────────────────────────────────────┐
│                         Tool Router                               │
│       typed tool calls • validation • permission policy            │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                         Wallet Engine                             │
│ generation • balances • gas • nonce • tx sender • RPC handling     │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│        SQLite Database        │   │           Blockchain           │
│ wallets • txs • memory        │   │ EVM RPC • explorer links       │
│ networks • migrations         │   │ configured networks            │
└───────────────────────────────┘   └───────────────────────────────┘
```

### 🔁 End-to-End Flow

```text
User
 ↓
Natural language or CLI command
 ↓
AI / CLI command parser
 ↓
Tool router
 ↓
Permission check
 ↓
Wallet / transaction / export / balance service
 ↓
SQLite + configured EVM RPC
 ↓
Rich terminal output + local logs
```

---

## 🧱 Core Components

### 🧠 AI Layer

The AI layer turns supported user prompts into structured wallet operations.

| Component | Responsibility |
|---|---|
| `ai/ollama_inference.py` | Calls Ollama and asks the local model to produce structured intent. |
| `ai/llm.py` | AI interpretation boundary with fallback behavior. |
| `ai/parser.py` | Parser utilities for supported prompts and intent conversion. |
| `ai/router.py` | Dispatches structured tool calls through permission enforcement. |
| `ai/tools.py` | Defines the tool registry, schemas, validation, and executor bindings. |
| `ai/permissions.py` | Defines safe, confirmation-required, and blocked tool behavior. |
| `ai/memory.py` | Stores interpreted intents and outputs in memory and optionally in SQLite. |
| `ai/prompts/` | System, tool, and safety prompt files for local AI interpretation. |

### 💸 Transaction Layer

The transaction layer is responsible for native token sending and reliability-oriented helpers.

| Component | Responsibility |
|---|---|
| `wallet/tx_sender.py` | Sends native token transactions with configured chain data. |
| `wallet/gas.py` | Resolves gas limits and gas prices with fallback behavior. |
| `wallet/nonce.py` | Handles nonce management for transaction execution. |
| `wallet/rpc_manager.py` | Provides RPC connection and failover infrastructure. |
| `wallet/error_classifier.py` | Classifies errors for retry and operational decisions. |
| `wallet/chains.py` | Reads and manages chain configuration. |

### 👛 Wallet Layer

The wallet layer handles wallet creation, access, listing, balance checks, and exports.

| Component | Responsibility |
|---|---|
| `wallet/generator.py` | Wallet generation service used by higher-level tools. |
| `wallet_gen.py` | Backward-compatible standalone wallet generator. |
| `wallet/balance.py` | Native token balance checks. |
| `wallet/exporter.py` | Export service wrapper for wallet records. |
| `converter.py` | Backward-compatible database export/conversion workflow. |
| `wallet/models.py` | Shared wallet-related data models. |

### 🗄️ Database Layer

Papa stores operational data locally in SQLite.

| Database Concern | Description |
|---|---|
| Wallet records | EVM addresses and private keys are stored in the local database. |
| Migrations | SQL migrations apply schema upgrades incrementally. |
| Transactions | Transaction metadata can be persisted and reviewed. |
| Networks | Chain/network records are configurable and queryable. |
| Balance cache | Balance-related schema exists for cached balance workflows. |
| AI memory | AI intents and outputs can be persisted through the memory layer. |

### 🖥️ CLI Layer

Papa uses Typer and Rich for a practical terminal experience.

| Command Area | Examples |
|---|---|
| Diagnostics | `python papa.py doctor` |
| Wallets | `python papa.py wallets` |
| Balances | `python papa.py balance --wallet 1` |
| Transactions | `python papa.py send ...`, `python papa.py tx-history` |
| Networks | `python papa.py networks list`, `add`, `remove` |
| AI | `python papa.py ai "generate 20 wallets"`, `python papa.py ai` |
| Legacy tools | `python wallet_gen.py --count 100`, `python converter.py --format json` |

---

## 🤖 How AI Works

Papa's AI layer is intentionally **tool-oriented**. It is not a general shell executor. The AI interpreter is expected to return a supported intent that can be validated, permission-checked, and routed to a known internal tool.

```text
┌────────────────────────────┐
│        User Prompt         │
│ "generate 20 wallets"     │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│  Local Ollama Inference    │
│  Model: qwen2.5:3b         │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│     Structured Intent      │
│ action + typed payload     │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│        Tool Call           │
│ allow-listed operation     │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│    Permission Check        │
│ safe / confirm / blocked   │
└─────────────┬──────────────┘
              │
              ▼
┌────────────────────────────┐
│        Execution           │
│ wallet, tx, balance, etc.  │
└────────────────────────────┘
```

### 🧭 AI Tooling Flow

| Stage | What Happens |
|---|---|
| 1. Prompt | You provide a supported natural-language request. |
| 2. Interpretation | Papa attempts local Ollama inference with `qwen2.5:3b`. |
| 3. Fallback | If Ollama is unavailable or output is invalid, supported regex parsing can be used. |
| 4. Intent | The prompt becomes a structured intent such as `generate_wallets` or `show_balances`. |
| 5. Tool Call | The intent is converted into a typed tool call with explicit arguments. |
| 6. Permission | The router checks whether the tool is safe, requires confirmation, or is blocked. |
| 7. Execution | Only known tools from the registry can execute. |

### 🧠 AI Memory

Papa includes an AI memory layer that can remember:

- interpreted intents,
- tool outputs,
- serialized execution context,
- database-backed memory records where configured.

This gives the platform a foundation for more capable local assistant workflows while keeping memory storage inspectable and local.

### 🛡️ AI Safety Model

Papa's AI safety approach is based on **containment and explicit routing**:

| Safety Boundary | Behavior |
|---|---|
| No raw shell execution | AI routing is designed around structured tools, not arbitrary terminal commands. |
| Allow-listed tools | Only tools registered in the AI tool registry are eligible for execution. |
| Permission policy | Balance and history checks are safer; generation, export, and sending require confirmation in the router policy. |
| Prompt separation | System, tool, and safety prompts live in dedicated prompt files. |
| Local inference | The default AI workflow targets local Ollama instead of cloud-hosted model APIs. |
| Private-key caution | Normal wallet listings avoid displaying private keys in CLI tables. |

> ⚠️ **Important:** This project can handle private keys and blockchain transactions. Treat local machines, databases, logs, exports, and backups as sensitive operational environments.

---

## 🗂️ Project Structure

```text
Papa/
├── ai/
│   ├── autonomous.py              # Autonomous controller foundation
│   ├── brain.py                   # Higher-level AI orchestration concepts
│   ├── llm.py                     # AI interpretation boundary
│   ├── memory.py                  # AI memory and optional persistence
│   ├── ollama_inference.py        # Ollama/Qwen inference integration
│   ├── parser.py                  # Prompt parsing and intent conversion
│   ├── permissions.py             # AI permission policy
│   ├── router.py                  # Structured dispatch layer
│   ├── tools.py                   # Tool registry and executors
│   └── prompts/
│       ├── safety.txt             # AI safety constraints
│       ├── system.txt             # AI system behavior
│       └── tools.txt              # Tool definitions for AI interpretation
│
├── cli/
│   ├── interactive.py             # Interactive AI terminal workflow
│   └── main.py                    # Package CLI entrypoint compatibility
│
├── config/
│   ├── networks.json              # EVM network configuration
│   └── settings.yaml              # Default chain, database path, retry/gas settings
│
├── database/
│   └── migrations/
│       ├── 001_initial_schema.sql
│       ├── 002_add_indexes.sql
│       ├── 003_add_transaction_queue.sql
│       └── 004_add_balance_cache.sql
│
├── exports/                       # Generated wallet export artifacts
├── logs/                          # Runtime logs
├── output/                        # Legacy/generated output artifacts
│
├── setup/
│   ├── bootstrap.py               # Ollama daemon/model bootstrap logic
│   └── install.sh                 # Setup wrapper
│
├── utils/
│   ├── dependency_checks.py       # Runtime dependency validation
│   ├── formatters.py              # Formatting helpers
│   ├── helpers.py                 # Shared config/helpers
│   ├── ollama.py                  # Ollama daemon/model checks
│   └── validators.py              # Validation helpers
│
├── wallet/
│   ├── balance.py                 # Balance service
│   ├── chains.py                  # Chain registry
│   ├── database.py                # SQLite database manager and migrations
│   ├── error_classifier.py        # Retry/permanent error classification
│   ├── exporter.py                # Wallet export service
│   ├── gas.py                     # Gas resolution
│   ├── generator.py               # Wallet generation service
│   ├── models.py                  # Shared data models
│   ├── nonce.py                   # Nonce management
│   ├── rpc_manager.py             # RPC failover/health infrastructure
│   └── tx_sender.py               # Native token transaction sender
│
├── converter.py                   # Backward-compatible export/converter CLI
├── install.sh                     # Top-level install helper
├── papa.py                        # Main Typer CLI
├── requirements.txt               # Python dependencies
├── wallet_gen.py                  # Backward-compatible wallet generator
└── README.md
```

---

## 🧰 Installation

### ✅ Prerequisites

| Requirement | Purpose |
|---|---|
| Python 3.10+ | Runtime for Papa and its CLI tools. |
| `pip` / virtual environment | Python dependency installation. |
| Ollama | Local AI inference runtime. |
| `qwen2.5:3b` | Default local model used by the AI workflow. |
| Network access | Required only for dependency/model installation and blockchain RPC calls. |

### 1️⃣ Clone the Repository

```bash
git clone <your-fork-or-repo-url>
cd Papa
```

### 2️⃣ Create and Activate a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3️⃣ Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Bootstrap Ollama and the Local Model

Papa includes setup helpers for Ollama availability and the default model:

```bash
./setup/install.sh
```

The bootstrap flow is designed to:

1. check that Python is available,
2. ensure Ollama is installed where supported,
3. start or reach the Ollama daemon,
4. pull `qwen2.5:3b`,
5. verify the model is available.

If you already manage Ollama yourself, the equivalent manual flow is:

```bash
ollama serve
ollama pull qwen2.5:3b
```

### 5️⃣ Validate the Environment

```bash
python papa.py doctor
```

---

## ⚡ Usage Examples

> The examples below show the intended CLI flow. Some commands require installed dependencies, a local database, funded wallets, a reachable EVM RPC endpoint, and chain configuration.

### 👛 Generate Wallets

Using the backward-compatible generator:

```bash
python wallet_gen.py --count 100
```

Using AI prompt interpretation:

```bash
python papa.py ai "generate 20 wallets"
```

### 📋 List Stored Wallets

```bash
python papa.py wallets
```

Limit output:

```bash
python papa.py wallets --limit 10
```

Filter by tag where tags are available:

```bash
python papa.py wallets --tag research
```

### 💰 Check Balance

```bash
python papa.py balance --wallet 1
```

Specify a chain key:

```bash
python papa.py balance --wallet 1 --chain skale_base_sepolia
```

### 💸 Send a Native Token Transaction

```bash
python papa.py send \
  --from 1 \
  --to 0x0000000000000000000000000000000000000000 \
  --amount 1wei \
  --chain skale_base_sepolia
```

### 🔁 Batch Send

```bash
python papa.py batch-send \
  --count 5 \
  --to 0x0000000000000000000000000000000000000000 \
  --amount 1wei \
  --chain skale_base_sepolia
```

### 🧾 View Transaction History

```bash
python papa.py tx-history
```

### 🌐 List Networks

```bash
python papa.py networks list
```

### ➕ Add a Network

```bash
python papa.py networks add \
  my_chain \
  "My Chain" \
  "https://rpc.example.invalid" \
  "https://explorer.example.invalid" \
  ETH \
  18 \
  12345
```

### 📦 Export Wallets

Using the backward-compatible converter:

```bash
python converter.py --format json
```

Other export formats may be available through the converter/export flow depending on the database and selected command options.

### 🤖 Start Interactive AI Mode

```bash
python papa.py ai
```

### 🧠 Ask Papa AI to Interpret a Prompt

```bash
python papa.py ai "show balances for wallet 1"
```

```bash
python papa.py ai "export wallets as json"
```

---

## 🖼️ Screenshots

Screenshots are intentionally not committed yet. Recommended screenshot locations:

```text
docs/screenshots/
├── papa-wallets-table.png
├── papa-balance-check.png
├── papa-ai-routing.png
├── papa-network-list.png
└── papa-transaction-history.png
```

| Screenshot | Description | Status |
|---|---|---:|
| Wallet table | Rich-rendered wallet listing without private keys. | 📌 Placeholder |
| Balance check | Native token balance table for a configured wallet. | 📌 Placeholder |
| AI routing | Natural language prompt converted into a structured tool call. | 📌 Placeholder |
| Network list | Configured EVM networks displayed in the terminal. | 📌 Placeholder |
| Transaction history | Stored transaction records rendered in the CLI. | 📌 Placeholder |

<details>
<summary>📸 Suggested screenshot capture workflow</summary>

1. Create a clean demo database.
2. Generate a small number of wallets.
3. Run `python papa.py wallets`.
4. Run `python papa.py networks list`.
5. Run `python papa.py ai "show balances for wallet 1"`.
6. Capture terminal output with your preferred screenshot utility.
7. Save images under `docs/screenshots/`.
8. Replace the placeholders above with image embeds.

</details>

---

## 🎯 Why You Might Find This Useful

### 🔐 For Local-First Users

If you prefer tools that keep operational data on your own machine, Papa gives you local SQLite storage, local AI inference, and local command execution patterns.

### 🧪 For Researchers

Papa is useful for experimenting with wallet generation, transaction flows, database-backed wallet metadata, network configuration, and AI routing behavior.

### 🧑‍💻 For Developers

The codebase is modular enough to inspect, replace, extend, or embed pieces of the stack:

- add networks,
- add wallet operations,
- improve transaction reliability,
- extend prompt parsing,
- add new AI tools,
- build higher-level automation.

### 🤖 For AI Experimentation

Papa demonstrates a practical local pattern for AI-powered tools:

```text
LLM interpretation → structured intent → typed tool call → permission policy → deterministic execution
```

That architecture is useful beyond wallets: it is a template for building local AI assistants that operate within explicit boundaries.

### ⚙️ For Automation Enthusiasts

Papa can serve as a foundation for repeatable wallet workflows, CLI scripts, testnet experiments, and AI-assisted operational tooling.

---

## 🧾 AI Disclosure

This project was heavily designed, implemented, reviewed, improved, and evolved with assistance from AI systems.

AI assistance was used across multiple parts of the project lifecycle, including:

| Area | AI-Assisted Work |
|---|---|
| 🧠 Architecture planning | Layering the AI, router, wallet, database, and CLI responsibilities. |
| 🧩 Code generation | Drafting and iterating on Python modules, command flows, and integration helpers. |
| 🔍 Reviews and audits | Identifying compatibility risks, duplicate modules, reliability gaps, and safety boundaries. |
| 🧪 Testing strategy | Designing compatibility, wrapper, and integration checks. |
| 📚 Documentation | Producing and refining project documentation, guides, and this README. |
| 🛡️ Safety framing | Making AI tool execution explicit, permissioned, and constrained. |

### 🤝 Human + AI Collaboration

Papa should be understood as a **human-directed, AI-assisted open-source project**. AI helped accelerate design and implementation, but users and contributors should still review behavior carefully, especially around private keys, exports, and transactions.

> Transparency matters. AI assistance is welcome in this project, but correctness, safety, testing, and maintainability still matter more than speed.

---

## 🌱 Open Source Contribution

Contributions are welcome — especially from people interested in local AI, wallet tooling, Python CLIs, SQLite systems, Web3.py, and developer experience.

### Ways to Help

| Action | How It Helps |
|---|---|
| ⭐ **Star the repository** | Helps other builders discover the project. |
| 🍴 **Fork it** | Experiment freely and propose improvements. |
| 🐛 **Submit issues** | Report bugs, confusing workflows, or missing docs. |
| 🔧 **Open pull requests** | Improve features, reliability, tests, docs, or architecture. |
| 🤖 **Use AI responsibly** | AI-assisted PRs are welcome when reviewed and explained clearly. |

### Good First Contribution Ideas

- Improve CLI help text.
- Add more README screenshots.
- Expand test coverage around AI parsing and routing.
- Add safer export workflows.
- Improve docs for adding networks.
- Add examples for testnet-only transaction workflows.
- Improve error messages for missing dependencies or unavailable Ollama.
- Document private-key handling best practices.

---

## 🐛 Issue Reporting

High-quality issues help maintainers move faster. Please include enough detail to reproduce the problem.

### 🐞 Bug Reports

Include:

| Field | What to Provide |
|---|---|
| Summary | What went wrong? |
| Environment | OS, Python version, dependency installation method. |
| Command | The exact command you ran. |
| Expected behavior | What you expected to happen. |
| Actual behavior | What happened instead. |
| Logs | Relevant output from `logs/` with secrets removed. |
| Database state | Whether this is a fresh or existing `wallets.db`. |
| Network | Chain key and RPC endpoint if relevant. |

<details>
<summary>Suggested bug report template</summary>

```markdown
## Bug Summary

## Environment
- OS:
- Python version:
- Papa commit:
- Ollama installed: yes/no
- Model available: qwen2.5:3b yes/no

## Command Run

## Expected Behavior

## Actual Behavior

## Relevant Logs

## Additional Context
```

</details>

### 💡 Feature Requests

Useful feature requests include:

- the problem you are trying to solve,
- why existing commands do not solve it,
- proposed CLI or AI prompt examples,
- safety or privacy considerations,
- whether it affects wallet generation, exports, transactions, AI, or database workflows.

### 🏛️ Architecture Discussions

Architecture discussions are welcome for larger changes such as:

- new AI tools,
- permission model changes,
- database schema changes,
- PostgreSQL compatibility,
- transaction queue behavior,
- multi-network strategy,
- key-management improvements.

### 🤖 AI Improvements

For AI-related issues, please include:

- prompt used,
- expected tool call,
- actual tool call or parser result,
- whether Ollama was running,
- model name,
- relevant prompt files changed, if any.

---

## 🔧 Pull Request Guide

### Recommended Workflow

```text
Fork → Branch → Change → Test → Document → Pull Request → Review
```

1. **Fork the repository.**
2. **Create a focused branch.**
   - Example: `docs/readme-screenshots`
   - Example: `fix/ollama-error-message`
   - Example: `feature/network-docs`
3. **Make a small, reviewable change.**
4. **Run relevant tests or checks.**
5. **Update documentation when behavior changes.**
6. **Open a pull request with a clear explanation.**

### PR Checklist

| Check | Description |
|---|---|
| ✅ Scope is clear | The PR solves one understandable problem. |
| ✅ Behavior is documented | CLI or AI behavior changes include docs/examples. |
| ✅ Safety is considered | Wallet, private-key, transaction, and export risks are addressed. |
| ✅ Tests are included where practical | Parser, router, database, or transaction changes should include checks. |
| ✅ AI usage is disclosed | If AI helped substantially, mention how in the PR body. |

### 🤖 AI-Assisted Pull Requests

AI-assisted PRs are welcome when they are:

- reviewed by the contributor,
- tested or manually verified,
- scoped clearly,
- transparent about AI involvement,
- careful with security-sensitive changes.

Please do **not** submit large AI-generated rewrites without explanation, tests, or rationale.

---

## 💬 Community

Papa is a space for builders interested in:

- local-first AI workflows,
- wallet orchestration,
- Web3 developer tooling,
- CLI-first automation,
- practical AI safety boundaries,
- SQLite-backed local applications,
- transparent open-source experimentation.

You are encouraged to:

- start discussions,
- share experiments,
- suggest improvements,
- ask architecture questions,
- propose new AI tools,
- help make the project safer and easier to use.

> Build openly, test carefully, and document what you learn.

---

## ❓ FAQ

<details open>
<summary><strong>Is everything local?</strong></summary>

Papa is designed around local-first workflows. The database is local SQLite, the AI workflow targets local Ollama, and the CLI runs on your machine. Blockchain interactions still require configured RPC endpoints, and dependency/model installation may require network access.

</details>

<details>
<summary><strong>Does this require cloud AI?</strong></summary>

No. The default AI workflow uses Ollama with `qwen2.5:3b`, which is intended to run locally. Papa also includes parser fallback behavior for supported prompts.

</details>

<details>
<summary><strong>Can I use Papa without AI?</strong></summary>

Yes. Core commands such as wallet listing, balance checks, transaction sending, transaction history, network listing, and legacy generation/export tools can be used directly from the CLI.

</details>

<details>
<summary><strong>Can I add networks?</strong></summary>

Yes. Networks are configured through `config/networks.json` and can also be managed through `python papa.py networks add`, `python papa.py networks list`, and `python papa.py networks remove`.

</details>

<details>
<summary><strong>Can I customize prompts?</strong></summary>

Yes. AI prompt files live under `ai/prompts/`. The current prompt structure separates system behavior, tool descriptions, and safety constraints.

</details>

<details>
<summary><strong>How does memory work?</strong></summary>

Papa includes an AI memory abstraction that can store interpreted intents and outputs in process memory and optionally persist serialized memory records through the database layer.

</details>

<details>
<summary><strong>Is this production-ready?</strong></summary>

Treat Papa as an evolving open-source wallet orchestration platform. It includes serious architecture work, but you should audit, test, and harden it before using it for high-value wallets or production transaction operations.

</details>

<details>
<summary><strong>Does Papa print private keys?</strong></summary>

Normal wallet listing through the main CLI displays wallet IDs and addresses, not private keys. Export workflows may include sensitive wallet material depending on format and usage, so handle exports carefully.

</details>

<details>
<summary><strong>What chains are supported?</strong></summary>

Papa is built around EVM-compatible wallet and transaction workflows. The included default configuration targets `skale_base_sepolia`, and additional EVM networks can be configured.

</details>

<details>
<summary><strong>Can I customize the Ollama model?</strong></summary>

The AI command exposes a model option, and the default is `qwen2.5:3b`. Other local Ollama models may work if they follow the expected structured output behavior.

</details>

<details>
<summary><strong>Does AI execute arbitrary commands?</strong></summary>

No. The AI router is designed around structured tool calls and an explicit registry. Unsupported or blocked actions should not be treated as executable shell commands.

</details>

<details>
<summary><strong>Where are logs stored?</strong></summary>

Runtime logs are stored under `logs/`, including wallet generation, transaction, converter, and error logs depending on which workflows are used.

</details>

---

## 🗺️ Roadmap

### ✅ Completed

- [x] EVM wallet generation utility.
- [x] SQLite wallet storage.
- [x] Backward-compatible wallet generator.
- [x] Wallet export/converter workflow.
- [x] Typer-based main CLI.
- [x] Rich terminal tables.
- [x] Transaction sender foundation.
- [x] Balance checking service.
- [x] Transaction history command.
- [x] Network configuration commands.
- [x] Ollama integration.
- [x] `qwen2.5:3b` default local model target.
- [x] AI parser fallback.
- [x] AI router and permission policy.
- [x] AI memory abstraction.
- [x] SQLite migrations.
- [x] Runtime dependency validation command.

### 🚧 In Progress / Near-Term

- [ ] More comprehensive test coverage for AI intent parsing.
- [ ] Additional documentation for transaction safety.
- [ ] More screenshots and demo workflows.
- [ ] Expanded examples for adding custom networks.
- [ ] Improved contributor documentation.
- [ ] Cleaner separation between AI interpretation and execution examples.
- [ ] Stronger export safety warnings and workflows.

### 🔮 Future Ideas

- [ ] Hardware-wallet or external signer integration.
- [ ] Encrypted-at-rest wallet storage options.
- [ ] More granular AI confirmation UX.
- [ ] Multi-network balance dashboards.
- [ ] Transaction queue UI and retry dashboards.
- [ ] PostgreSQL-compatible deployment mode.
- [ ] Plugin system for custom AI wallet tools.
- [ ] Local web dashboard.
- [ ] Policy profiles for research, testnet, and production modes.
- [ ] Prompt evaluation suite for AI routing reliability.

---

## 🧪 Technical Highlights

| Layer | Technology | Why It Matters |
|---|---|---|
| 🧠 AI | Ollama + Qwen2.5 3B | Enables local prompt interpretation without requiring a cloud AI API. |
| 🐍 Runtime | Python | Fast iteration, readable architecture, broad Web3 and CLI ecosystem. |
| 🖥️ CLI | Typer + Rich | Friendly command interface and polished terminal output. |
| 👛 Wallets | `eth-account` | EVM-compatible wallet generation and account primitives. |
| 🌐 Blockchain | Web3.py | EVM RPC communication and transaction sending. |
| 🗄️ Database | SQLite + migrations | Local durable storage with versioned schema evolution. |
| ⚙️ Config | YAML + JSON | Simple local configuration for settings and networks. |
| 📦 Exports | Converter/export services | Supports file-based wallet export workflows. |
| 🛡️ AI Safety | Tool registry + permission model | Keeps AI behavior constrained to explicit operations. |
| 📜 Observability | Logs | Operational logs for generation, transactions, conversion, and errors. |

---

## 🙏 Credits

Papa exists thanks to the broader open-source ecosystem and the maintainers of the tools that make local wallet orchestration possible.

Special thanks to:

- **Python** and its open-source community.
- **Ollama** for local model serving workflows.
- **Qwen** model contributors for capable local model options.
- **Web3.py** contributors for EVM integration tooling.
- **Typer** and **Rich** maintainers for excellent CLI developer experience.
- **SQLite** for simple, durable local storage.
- Everyone who files issues, opens PRs, improves docs, tests edge cases, and shares feedback.
- AI systems used during development for architecture planning, code assistance, reviews, audits, and documentation drafting.

---

## ⚠️ Security Notice

Papa can create and store private keys and can send blockchain transactions. Before using it with meaningful value:

- audit the code,
- use testnets first,
- protect local databases and exports,
- avoid committing wallet databases or private-key exports,
- review transaction parameters before sending,
- understand the configured RPC/network behavior,
- back up responsibly,
- assume exported wallet files are highly sensitive.

> This repository is provided for development, research, and experimentation. You are responsible for your own key management, operational security, and transaction decisions.

---

<div align="center">

## 🚀 Keep Building

⭐ **If this project helps you, consider starring it.**<br>
🍴 **Fork it and build something interesting.**<br>
🐛 **Open issues when you find problems.**<br>
🤖 **AI-assisted contributions are welcome.**<br>
🚀 **Keep building local-first tools.**

</div>
