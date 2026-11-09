# 🦞 ReClaw — Revive Your Old Smartphone with AI


---

## 📑 Table of Contents

- [Problem & Solution](#-problem--solution)
- [Architecture](#-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Setup & Installation](#-setup--installation)
- [Usage](#-usage)
- [AI Disclosure](#-ai-disclosure)
- [Repository Structure](#-repository-structure)

---

## 🎯 Problem & Solution

### The Problem

**5.3 Billion old smartphones sit unused worldwide.** They have working processors, cameras, sensors, and Wi-Fi — yet they become e-waste because their software is no longer supported.

### Our Solution

**ReClaw** transforms any old Android smartphone into an intelligent, always-on personal assistant:

- 🧠 **On-device SLM** — Runs fully offline; ships with Qwen3-0.6B (QAT INT4) by default, supports any compatible model
- 📡 **Master-Slave via Telegram** — Control the old phone from your primary device
- 📍 **GPS Geofencing** — Auto-switches profiles when entering home/office zones
- 📅 **Commute Planner** — Calculates departure times, sends alerts at 7 AM daily
- 📋 **Notification Hub** — Categorizes alerts by priority (urgent/important/casual/noise)
- 🏠 **4 Smart Profiles** — Home, Office, Transit, Sleep — real hardware control

---

## 🏗️ Architecture

### Master-Slave Model

```
┌─────────────────────┐          ┌──────────────────────────────────────┐
│  MASTER (Primary     │ Telegram │  SLAVE (Old Android Phone)           │
│  Phone / Desktop)    │◄────────►│                                      │
│                      │          │  ┌──────────────────────────────────┐│
│  • Sends commands    │          │  │  PicoClaw Agent (NDK binary)     ││
│  • Receives alerts   │          │  │  Native ARM · <15MB · <1s boot   ││
│  • Views dashboards  │          │  │                                  ││
│                      │          │  │  ┌────────────┐  ┌────────────┐ ││
│  No special app      │          │  │  │ On-device  │  │ Skills     │ ││
│  needed — just       │          │  │  │ SLM        │  │ Routine Mgr│ ││
│  Telegram            │          │  │  │ (any GGUF) │  │ Commute    │ ││
│                      │          │  │  │ Runtime:   │  │ Notif Hub  │ ││
└─────────────────────┘          │  │  │ auto-select│  │ Customizer │ ││
                                 │  │  └──────┬─────┘  └────────────┘ ││
                                 │  │         ▼                        ││
                                 │  │  ┌──────────────────────────┐   ││
                                 │  │  │ Tool Router + Memory     │   ││
                                 │  │  │ Shell·Sensors·GPS·Camera │   ││
                                 │  │  └──────────────────────────┘   ││
                                 │  └──────────────────────────────────┘│
                                 └──────────────────────────────────────┘
```

### Adaptive Runtime Selection

PicoClaw auto-selects the best inference backend based on device hardware:

| Runtime | Format | Best For | Min RAM |
|---------|--------|----------|---------|
| **ExecuTorch** | `.pte` | Snapdragon 6xx+ | 2GB |
| **llama.cpp** | `.gguf` | Broad ARM64 compat | 1.5GB |
| **PicoLM** (fork) | Custom | Ultra-constrained | 512MB |
| **LiteRT** | `.tflite` | GPU delegate | 1.5GB |
| **MNN** | `.mnn` | MediaTek/Kirin SoCs | 1GB |

---

## ✨ Features

### 1. 🏠 Routine Manager — Smart Profiles

| Profile | Volume | Brightness | DND | Trigger |
|---------|--------|------------|-----|---------|
| 🏠 Home | 70% | 60% | Off | GPS / 6 PM / command |
| 💼 Office | 0% | 40% | On | GPS / 9 AM / command |
| 🚇 Transit | 40% | 50% | Off | Command |
| 🌙 Sleep | 0% | 5% | On | "goodnight" / command |

All changes use **real Android APIs** via Termux:API (volume, brightness, DND).

### 2. 📅 Commute Planner

- View today's events: `events`
- Add events via chat: `add meeting Title, HH:MM, Location, Travel_mins`
- Check departure alerts: `commute`
- **Formula:** `Leave by = Event Time − Travel Time − 15 min buffer`
- Runs **automatically at 7 AM** and sends alerts via Telegram

### 3. 📋 Notification Hub

Reads real device notifications and categorizes them:

| Priority | Source | Action |
|----------|--------|--------|
| 🔴 Urgent | Starred contacts (Mom, Boss) | Always shown |
| 🟡 Important | WhatsApp, Telegram groups | Shown |
| 🟢 Casual | General apps | Summarized |
| ⚪ Noise | Games, ads, Instagram | Auto-dismissed |

Sent **automatically at 8 PM** via Telegram.

### 4. 📡 Master-Slave via Telegram

Control your old phone remotely from Telegram:

```
You: "status"
🦞: 📱 Battery: 73% | Profile: Home | Volume: 10/15 | Runtime: llama.cpp

You: "office mode"
🦞: 💼 Office profile activated — Volume: 0%, DND: On

You: "digest"
🦞: 📋 12 notifications — 2 Urgent, 3 Important, 7 Noise

You: "commute"
🦞: 🚇 Leave by 08:30 for Q2 Review (75 min travel)
```

### 5. 🧠 On-Device AI (SLM)

- **Model:** Default: Qwen3-0.6B (447 MB, Q4_0 quantized) — any GGUF/PTE/TFLite model supported
- **Training:** PyTorch QAT — INT8 activation, INT4 weights
- **Inference:** Fully offline, ~5-9 sec response time
- **Language:** English + Hinglish ("volume badha do" = increase volume)

### 6. 📍 GPS Geofencing

- Auto-switches to Office profile when entering office zone
- Auto-switches to Home profile when entering home zone
- Checks location every 5 minutes in background

### 7. ⏰ Background Automation

| Time | Action |
|------|--------|
| 7:00 AM | Morning commute alert via Telegram |
| 9:00 AM | Auto-switch to Office profile |
| 6:00 PM | Auto-switch to Home profile |
| 8:00 PM | Evening notification digest |

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Agent Runtime** | PicoClaw (compiled via Android NDK) |
| **Language Model** | Any compatible SLM (default: Qwen3-0.6B, QAT fine-tuned) |
| **Inference** | llama.cpp / ExecuTorch / LiteRT / MNN |
| **Fine-Tuning** | PyTorch + TorchAO QAT |
| **Messaging** | Telegram Bot API |
| **Device Control** | Termux:API (volume, brightness, DND, GPS) |
| **Platform** | Android 7.0+ (ARM64) |

---

## 🚀 Setup & Installation

### Prerequisites

**Target Phone (Slave):**
- Android 7.0+ (API 24+) with ARM64 processor
- Minimum 1GB RAM (2GB+ recommended)
- ~500MB free storage
- [Termux](https://f-droid.org/en/packages/com.termux/) + [Termux:API](https://f-droid.org/en/packages/com.termux.api/) installed
- Telegram bot token (via [@BotFather](https://t.me/BotFather))

### Quick Start (Termux)

```bash
# 1. Install dependencies
pkg install python llama.cpp termux-api

# 2. Clone the repo
git clone https://github.com/Beyond-ud/ReClaw.git
cd ReClaw

# 3. Download model
mkdir -p ~/models
# Download any compatible GGUF model to ~/models/
# Default: qwen3-0.6b-q4_0.gguf (~447MB)

# 4. Set Telegram credentials
export RECLAW_BOT_TOKEN="your_bot_token"
export RECLAW_CHAT_ID="your_chat_id"

# 5. Run the agent
python3 demo/reclaw_agent.py
```

### Advanced: QAT Fine-Tuning (Colab)

```bash
pip install torch torchao transformers datasets accelerate
python model/ReClaw_QAT_Finetune.py \
    --model Qwen/Qwen3-0.6B \   # or any HuggingFace model
    --dataset model/dataset/ \
    --output model/output/ \
    --epochs 3
```

### Export Model

```bash
# GGUF (recommended)
python model/export_gguf.py --model model/output/final --output model.gguf

# ExecuTorch
python model/export_pte.py --model model/output/final --output model.pte

# TFLite
python model/export_tflite.py --model model/output/final --output model.tflite
```

---

## 💬 Usage

### Terminal Commands

| Command | Action |
|---------|--------|
| `home mode` / `office mode` / `goodnight` | Switch profile |
| `status` | Device info (battery, profile, volume) |
| `events` | List today's events |
| `add meeting Title, HH:MM, Location, Mins` | Add calendar event |
| `commute` | Departure alerts |
| `digest` | Notification summary |
| `volume N` | Set volume (0-100) |
| `help` | Show all commands |
| `quit` | Stop agent |

All commands work in both **Terminal** and **Telegram**.

---

## 🤖 AI Disclosure

### AI Models in the Solution

| Component | Model / Tool | How It's Used |
|-----------|-------------|---------------|
| **On-device SLM** | Any compatible SLM (default: Qwen3-0.6B) | Core language model — interprets commands, generates responses. Runs fully offline. Swappable via config. |
| **QAT Fine-Tuning** | PyTorch + TorchAO | INT8 dynamic activation + INT4 weight quantization. Full fine-tuning (not LoRA). |
| **Inference Runtimes** | ExecuTorch / llama.cpp / LiteRT / MNN | Multiple backends — auto-selected per device capability. |

### AI Used During Development

| Tool | Purpose |
|------|---------|
| **Antigravity (Gemini)** | Documentation, code scaffolding, README generation. All outputs reviewed by team. |
| **Google Colab (T4 GPU)** | QAT fine-tuning (default: Qwen3-0.6B). Free tier sufficient. Any HuggingFace model supported. |
| **LLM-assisted augmentation** | Dataset paraphrasing and Hinglish variant generation (~30%). Human validated. |

### What AI Did NOT Do

- ❌ Architecture decisions — Master-slave design made by team
- ❌ Skill rule design — All behavior rules manually authored
- ❌ Hardware testing — On-device testing done manually
- ❌ Manual seed data — Initial 100 examples per category hand-written

---

## 📁 Repository Structure

```
ReClaw/
├── README.md                        # This file
├── SKILL.md                         # Agent Skills standard specification (Agensi / Claude / Cursor)
├── ReClaw_Architecture.png          # System architecture diagram
├── ReClaw_Skills_Reference.pdf      # Skills documentation
│
├── demo/                            # Working prototype
│   ├── reclaw_agent.py              # ⭐ Main agent script (runs on phone)
│   └── VIDEO_SCRIPT.md              # Demo recording guide
│
├── config/                          # Configuration
│   ├── picoclaw.json                # Agent config (runtime, cron, skills)
│   └── memory.json                  # Profiles, geofences, contacts
│
├── skills/                          # Skill definitions
│   ├── routine-manager/SKILL.md     # Auto-profile switching rules
│   ├── commute-planner/SKILL.md     # Departure alert rules
│   ├── smart-customizer/SKILL.md    # Personalization rules
│   └── notification-hub/SKILL.md    # Notification categorization
│
├── model/                           # SLM training & export
│   ├── ReClaw_QAT_Finetune.py       # QAT training script
│   ├── export_gguf.py               # GGUF export
│   ├── export_pte.py                # ExecuTorch export
│   ├── export_tflite.py             # TFLite export
│   └── dataset/                     # Training data (~1,700 examples)
│
├── picoclaw/                        # Agent runtime (Go + NDK)
│   ├── go.mod                       # Go module
│   ├── Makefile.ndk                 # Android NDK cross-compilation
│   ├── cmd/picoclaw/main.go         # Entry point
│   └── runtime/                     # Multi-runtime inference
│
├── android/                         # Android deployment
│   ├── device-bridge.py             # Termux:API bridge
│   ├── ndk-build.sh                 # NDK compilation
│   └── proot-setup.sh               # proot distro setup
│
```

---


<p align="center">
  Built with: PyTorch · TorchAO · ExecuTorch · llama.cpp · Qwen3 · Termux
</p>
