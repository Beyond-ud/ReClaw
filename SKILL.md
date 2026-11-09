---
name: reclaw
description: Develop, run, and extend ReClaw, a framework that turns old Android phones into offline AI assistants controlled over Telegram. Use when working on the PicoClaw agent, Termux setup, device profiles, GPS geofencing, commute and notification logic, agent skills in skills/, on-device SLM fine-tuning, GGUF/ExecuTorch/TFLite export, or Android NDK builds.
license: Apache-2.0
compatibility: Android 7.0+ (ARM64), Termux, Python 3.10+, llama.cpp / ExecuTorch
metadata:
  author: ReClaw Core Team
  version: "2.1.0"
  repository: https://github.com/Beyond-ud/ReClaw
---

# ReClaw

ReClaw repurposes an unused Android phone (the **slave**) as an always-on personal assistant. A primary phone or desktop (the **master**) controls it through Telegram, so no companion app is required. A small on-device language model (SLM) interprets commands offline, and the agent changes real device state through Termux:API. The default model is Qwen3-0.6B (QAT INT4), but any compatible SLM can be swapped in via config.

## When to use this skill

- Setting up or debugging the agent on a phone running Termux.
- Adding or modifying agent skills, profiles, geofences, schedules, or commands.
- Fine-tuning, quantizing, exporting, or swapping the on-device SLM (any compatible model).
- Building or extending the PicoClaw runtime (Go, Android NDK) and its inference backends.
- Keeping documentation consistent with behavior changes.

## Architecture

| Layer | Component | Notes |
|---|---|---|
| Control | Telegram bot (master) | Polls via `getUpdates`, same commands as the terminal |
| Agent | `demo/reclaw_agent.py` (v2.1) | Primary entry point; also has PicoClaw (Go NDK binary, under 15 MB) |
| Model | Default: Qwen3-0.6B, QAT fine-tuned, Q4_0 | Any GGUF/PTE/TFLite SLM supported; about 447 MB for default model, invoked via `llama-simple-chat` over a `pty` |
| Skills | Routine Manager, Commute Planner, Notification Hub, Smart Customizer | Behavior rules in `skills/`, but logic is inline in `reclaw_agent.py` |
| Device I/O | Termux:API | `termux-volume`, `termux-brightness`, `termux-battery-status`, `termux-location`, `termux-notification-list`, `termux-toast` |

> [!IMPORTANT]
> The agent currently runs its core logic (profiles, commute, digest, geofencing) as deterministic Python code in `reclaw_agent.py`. The SLM is only a **fallback** for free-text commands that do not match any rule. Do not route deterministic logic through the 0.6B model.

## Repository layout

| Path | Purpose |
|---|---|
| `demo/reclaw_agent.py` | Main agent script (v2.1), primary entry point |
| `demo/reclaw_demo.py` | Standalone demo script |
| `demo/VIDEO_SCRIPT.md` | Demo recording guide |
| `config/picoclaw.json` | Runtime selection, cron schedule, enabled skills, model paths |
| `config/memory.json` | Profiles, geofences, contacts, commute preferences |
| `skills/<name>/SKILL.md` | Behavior rules for the agent's own runtime skills |
| `model/ReClaw_QAT_Finetune.py` | QAT fine-tuning script (PyTorch + TorchAO), works with any HuggingFace model |
| `model/export_gguf.py` | GGUF exporter for llama.cpp |
| `model/export_pte.py` | ExecuTorch `.pte` exporter |
| `model/export_tflite.py` | LiteRT `.tflite` exporter |
| `model/dataset/` | Training data: 6 JSONL files, about 1,700 examples, 30% Hinglish |
| `picoclaw/` | Go runtime, NDK Makefile, multi-backend inference |
| `android/` | `device-bridge.py` (Termux:API bridge), `ndk-build.sh`, `proot-setup.sh` |
| `ReClaw_Architecture.png` | System architecture diagram |
| `ReClaw_Skills_Reference.pdf`, `skills_reference.html` | Skills documentation |

> [!NOTE]
> The `skills/` folder holds **runtime behavior rules for the ReClaw agent itself**, not developer agent skills. Do not confuse them with this `SKILL.md`.

## Quick start (Termux)

Requirements: Android 7.0+ (ARM64), 1 GB RAM minimum (2 GB+ recommended), about 500 MB free storage, Termux and Termux:API from F-Droid, a Telegram bot token from @BotFather, and a compatible GGUF model (default: Qwen3-0.6B Q4_0).

```bash
pkg install python llama.cpp termux-api
git clone https://github.com/Beyond-ud/ReClaw.git && cd ReClaw
mkdir -p ~/models   # place your GGUF model here (default: qwen3-0.6b-q4_0.gguf)
export RECLAW_BOT_TOKEN="your_bot_token"
export RECLAW_CHAT_ID="your_chat_id"
python3 demo/reclaw_agent.py
```

The agent auto-selects a profile based on the current hour at startup (office 09:00-18:00, sleep 22:00-06:00, home otherwise), starts background cron and GPS threads, launches the SLM via `pty.fork()`, and begins polling Telegram.

## Working rules

1. **Never commit secrets.** The bot token and chat ID belong in environment variables (`RECLAW_BOT_TOKEN`, `RECLAW_CHAT_ID`) only.
2. **Prefer rules over the model for deterministic logic.** Profile switching, commute math, and notification tiers must not depend on a 0.6B model's output. The SLM is only the fallback.
3. **Test on a real device or Termux.** Device effects (`termux-volume`, `termux-brightness`, DND, GPS) cannot be validated on a desktop.
4. **Keep sources of truth in sync.** A behavior change usually touches several files at once (see the sync table below).
5. **Match terminal and Telegram behavior.** Every command must produce identical output in both interfaces.
6. **Verify before assuming.** Cross-check the items below against actual code before relying on them.

### Sync table

| If you change | Also update |
|---|---|
| Profile values or triggers | `PROFILES` dict in `reclaw_agent.py`, `config/memory.json`, `skills/routine-manager/SKILL.md`, README profile table |
| Schedule (7 AM, 9 AM, 6 PM, 8 PM cron jobs) | `cron()` function in `reclaw_agent.py`, `config/picoclaw.json`, README schedule table |
| Commute formula or buffer | `commute()` function in `reclaw_agent.py`, `skills/commute-planner/SKILL.md`, `config/memory.json` `buffer_minutes`, README |
| Notification tiers or starred contacts | `digest()` function and `STARRED` list in `reclaw_agent.py`, `config/memory.json` `starred_contacts`, `skills/notification-hub/SKILL.md`, README tier table |
| Commands or Hinglish keywords | `handle()` router in `reclaw_agent.py`, help text in the same function, README command table |
| Model or runtime support | `MODEL` and `CHAT_BIN` paths in `reclaw_agent.py`, `config/picoclaw.json`, README tech stack and runtime tables |

### Cross-check in code before relying on docs

- `PROFILES` dict (line 10 of `reclaw_agent.py`) — the hardcoded profile values may differ from `config/memory.json`
- `commute()` uses a hardcoded 15-min buffer (`e["mins"]+15`), while `memory.json` says `buffer_minutes: 30`
- Home trigger is `18:00` in the `cron()` function but `18:30` in `config/memory.json`
- SLM prompt format — search for `<think>` tag stripping (default model uses Qwen3 thinking mode; other models may differ)
- `CHAT_BIN` path defaults to `~/llama.cpp/llama.cpp/build/bin/llama-simple-chat`

## Workflows

### Add or change an agent skill

- [ ] Create or edit `skills/<skill-name>/SKILL.md`, following the format of existing skills in that folder
- [ ] Add the skill name to `config/picoclaw.json` under `skills.enabled`
- [ ] Add command or trigger handling in the `handle()` function of `demo/reclaw_agent.py`
- [ ] Add training examples to `model/dataset/` if the model must recognize new phrasing (include Hinglish variants)
- [ ] Update the README, help text, and sync table items above
- [ ] Verify via `help`, then run the new command in both terminal and Telegram

### Change profiles, geofences, or contacts

Edit `config/memory.json` for persistent config and `PROFILES`/`GEOFENCES`/`STARRED` in `reclaw_agent.py` for runtime defaults. Current defaults:

| Profile | Volume | Brightness | DND | Trigger |
|---|---|---|---|---|
| Home | 70% | 60% | Off | GPS geofence (200 m), 18:00 cron, command |
| Office | 0% | 40% | On | GPS geofence (300 m), 09:00 cron (weekdays), command |
| Transit | 40% | 50% | Off | Command only |
| Sleep | 0% | 5% | On | Keywords `goodnight`/`soja`/`night`/`neend`, command |

GPS geofences are checked every 30 seconds in the background `cron()` thread. Distance is calculated using the Haversine formula.

### Fine-tune and export the model

A free Colab T4 is sufficient. This is full QAT fine-tuning (INT8 dynamic activations, INT4 weights), not LoRA. The `--model` flag accepts any HuggingFace model (default: Qwen/Qwen3-0.6B).

```bash
pip install torch torchao transformers datasets accelerate
python model/ReClaw_QAT_Finetune.py --model Qwen/Qwen3-0.6B \
    --dataset model/dataset/ --output model/output/ --epochs 3

python model/export_gguf.py   --model model/output/final --output model.gguf     # recommended
python model/export_pte.py    --model model/output/final --output model.pte      # ExecuTorch
python model/export_tflite.py --model model/output/final --output model.tflite   # LiteRT
```

Dataset categories (6 JSONL files): `profile_switching` (~400), `commute_queries` (~300), `device_commands` (~350), `context_sensing` (~250), `notification_mgmt` (~200), `master_slave` (~200). About 30% include Hinglish phrasing.

### Swap the base model

The training script accepts `--model`, and llama.cpp loads any supported GGUF, so the model is fully replaceable. The framework is model-agnostic by design. Before swapping:

- [ ] Check `slm()` and `slm_start()` in `reclaw_agent.py` — the SLM is launched via `pty.fork()` calling `llama-simple-chat`
- [ ] Verify the `<think>...</think>` tag stripping still works for the new model family (line 185-186) — may need adjustment for non-Qwen models
- [ ] Confirm the quantized size still fits the target RAM (see the runtime table)
- [ ] Retrain on `model/dataset/` so command recognition and Hinglish support carry over
- [ ] Re-export, then compare latency and accuracy against the previous model on a real phone
- [ ] Update the README, tech stack table, and AI disclosure section

### Build the PicoClaw runtime

Cross-compile with the Android NDK using `picoclaw/Makefile.ndk` or `android/ndk-build.sh`. Use `android/proot-setup.sh` if a proot distro is required. Inference backends live in `picoclaw/runtime/` (executorch, llamacpp, litert, mnn, picolm) with a `router.go` that auto-selects based on device benchmarks.

## Reference

### Agent commands

The `handle()` function in `reclaw_agent.py` routes commands. Both English and Hinglish triggers are supported:

| Command | Hinglish aliases | Action |
|---|---|---|
| `home mode`, `office mode`, `transit mode` | `laga`, `karo` | Switch profile |
| `goodnight`, `sleep` | `soja`, `neend` | Sleep profile |
| `status` | `kaisa`, `haal` | Battery, profile, volume, runtime |
| `events`, `schedule` | `aaj kya` | List today's calendar events |
| `add meeting Title, HH:MM, Location, mins` | | Add a calendar event |
| `commute`, `leave`, `route` | `nikalna` | Departure alerts |
| `digest`, `notifications` | `kya aaya`, `missed` | Notification summary |
| `volume N`, `mute`, `max` | `awaaz`, `chup`, `badha` | Set volume (0-100) |
| `brightness N`, `dim`, `max` | `roshni`, `kam` | Set brightness (0-100) |
| `location`, `gps` | `kahan` | Current GPS coordinates |
| `help` | `kya kar` | Show commands |
| `quit`, `exit` | | Stop the agent |
| Any other text | | Forwarded to SLM as fallback |

### Commute formula

```
departure_time = event_time - travel_minutes - 15 min buffer
```

Alert is pushed via Telegram with route, travel time, and leave-by time. Only events with `mins > 0` trigger alerts.

### Notification tiers

Categorized by `digest()` in `reclaw_agent.py`:

| Tier | Logic | Action |
|---|---|---|
| Urgent (red) | Notification title matches any name in `STARRED` list | Always shown (up to 5) |
| Important (yellow) | Package name contains `whatsapp` or `telegram` | Shown (up to 5) |
| Casual (green) | Everything else not matching noise | Summarized (up to 3) |
| Noise (grey) | Package contains `instagram`, `youtube`, or `game` | Count only |

### Scheduled jobs

Hardcoded in the `cron()` function of `reclaw_agent.py` (also mirrored in `config/picoclaw.json`):

| Time | Action | Scope |
|---|---|---|
| 7:00 AM | Commute alert via Telegram | Daily |
| 9:00 AM | Switch to Office profile | Weekdays only |
| 6:00 PM | Switch to Home profile | Weekdays only |
| 8:00 PM | Notification digest via Telegram | Daily |

### Inference runtimes

PicoClaw selects a backend by device hardware (`picoclaw/runtime/router.go`):

| Runtime | Format | Best for | Min RAM |
|---|---|---|---|
| ExecuTorch | `.pte` | Snapdragon 6xx+ | 2 GB |
| llama.cpp | `.gguf` | Broad ARM64 | 1.5 GB |
| PicoLM (fork) | custom | Ultra-constrained | 512 MB |
| LiteRT | `.tflite` | GPU delegate | 1.5 GB |
| MNN | `.mnn` | MediaTek, Kirin | 1 GB |

Model paths are configured in `config/picoclaw.json` under `agent.model_paths`.

## Verification checklist

The project has no automated test suite. Verify manually before declaring a change done:

- [ ] Agent starts with `python3 demo/reclaw_agent.py` without errors
- [ ] `help` and `status` respond correctly in both terminal and Telegram
- [ ] Changed commands produce identical output in terminal and Telegram
- [ ] Device effects visibly apply on a phone (`termux-volume`, `termux-brightness`, DND)
- [ ] GPS geofencing triggers profile switch when entering a geofence zone
- [ ] Model changes: exported file loads and responds within 5-9 seconds on target hardware
- [ ] Docs, config, and the sync table are updated

## Known limits

- SLM responses take roughly 5 to 9 seconds on old hardware — avoid chains of sequential model calls
- The default model has 0.6B parameters: keep prompts short and outputs constrained. Larger models can be used if the device supports them.
- Termux:API is a separate F-Droid app; location, notification, and DND permissions must be granted manually on the device
- Target platform is Android 7.0+ on ARM64 only
- The `pty.fork()` approach for SLM invocation may not work on all Termux versions

## Project facts

- License: Apache-2.0
- Keep the AI disclosure section of the README accurate whenever AI-assisted code or data is added
- Consult `ReClaw_Architecture.png` before making architectural changes
