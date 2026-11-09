# 🎬 ReClaw Demo — Final Director's Script (Telegram-First)

> **Duration:** 5-7 min | No voiceover, text captions only
> **Device:** Samsung S23 running Termux + Telegram
> **Recording:** Samsung Screen Recorder (Media sounds only, no mic)

---

## PREP CHECKLIST (do all of this before recording)

### 1. Edit Calendar Events

Open Termux. Edit the script to add events that are IN THE FUTURE:

```
nano ~/reclaw_agent.py
```

Ctrl+W → search `CALENDAR` → Replace the line with events AFTER current time.
Example (if recording around 5 AM):

```
CALENDAR=[{"title":"Q2 Review with Team","time":"10:00","loc":"Connaught Place, Block A","route":"Blue Line Metro + walk 5min","mins":75},{"title":"Client Call","time":"14:00","loc":"Office Conference Room","route":"Already at office","mins":0},{"title":"Gym Session","time":"18:00","loc":"Gold Gym Sector 50","route":"Auto 15min","mins":20}]
```

Ctrl+O → Enter → Ctrl+X

### 2. Export Telegram Credentials
```
export RECLAW_BOT_TOKEN="your_token"
export RECLAW_CHAT_ID="your_id"
```

### 3. Test Agent Works
```
python3 ~/reclaw_agent.py
```
Type `status` → verify it responds → type `quit`

### 4. Clear Telegram Chat
- Open Telegram → your bot
- Three dots → Clear History → confirm
- Now the chat is empty and clean

### 5. Create Caption Screenshots

Open **Samsung Notes**. Make 6 notes on BLACK background with WHITE text.
Screenshot each (Power + Vol Down).

---

**SCREENSHOT 1 — Title + Problem (combine into one):**
```
🦞 ReClaw
━━━━━━━━━━━━━━━━━━

Turning Old Phones into
AI-Powered Personal Assistants

5.3 Billion phones sit unused.
ReClaw gives them a new brain.

Fully Offline • Zero Cost • Privacy-First

ReClaw Open Source Project
```

---

**SCREENSHOT 2 — Telegram Intro:**
```
📡 MASTER-SLAVE ARCHITECTURE
━━━━━━━━━━━━━━━━━━━━━━━━━

Your Primary Phone (Master)
→ Send commands via Telegram

Old Phone (Slave)
→ AI Agent receives, processes,
  executes, and responds

No app installation needed.
Just a Telegram chat.
```

---

**SCREENSHOT 3 — Behind the Scenes:**
```
🔧 BEHIND THE SCENES
━━━━━━━━━━━━━━━━━━━━━━━

What just happened on the old phone:

• Telegram message received
• Routed to the right skill
• Termux:API called for hardware
• Response sent back via bot

All processing happens ON-DEVICE.
```

---

**SCREENSHOT 4 — Tech Stack:**
```
🧠 TECH STACK
━━━━━━━━━━━━━━━━━━━━━━━

Model: On-device SLM (default: Qwen3 0.6B, 447 MB)
Training: PyTorch QAT (INT4/INT8)
Runtime: llama.cpp (auto-selected)
Agent: PicoClaw (Android NDK)
API: Termux:API for hardware
Channel: Telegram Bot API
Language: English + Hinglish
```

---

**SCREENSHOT 5 — Automation:**
```
⏰ RUNS 24/7 AS PASSIVE AGENT
━━━━━━━━━━━━━━━━━━━━━━━

Background Scheduler:
  7:00 AM → Commute alert via Telegram
  9:00 AM → Auto Office profile
  6:00 PM → Auto Home profile
  8:00 PM → Notification digest

GPS Geofencing:
  📍 Enter office zone → Silent mode
  📍 Enter home zone → Normal mode
```

---

**SCREENSHOT 6 — Closing:**
```
🦞 ReClaw — Impact
━━━━━━━━━━━━━━━━━━━━━━━

♻️ Extends phone life 3-5 years
💰 Fully open-source, zero cost
🔒 All AI inference on-device
🌍 Works on $20 hardware
🗣️ Supports Hinglish

Every old phone deserves
a second life.

Thank you! 🙏
ReClaw Project Maintainers
ReClaw Open Source Project
```

---

### 6. Set Up Split Screen

Before recording, practice split screen:
1. Open Termux
2. Tap Recents (|||)
3. Tap Termux icon at top of its card → "Open in split screen"
4. Tap Telegram in the bottom list
5. Now: Termux on top, Telegram on bottom
6. In Telegram, open your bot chat

---

## ═══════════════════════════════════════
##   START RECORDING — CLIP BY CLIP
## ═══════════════════════════════════════

---

### 📸 CLIP 1: Title + Problem Card
**Duration: 8 seconds**

1. Open Gallery → find Screenshot 1 (Title + Problem)
2. START screen recording
3. Hold for 8 seconds
4. STOP recording

---

### 🎥 CLIP 2: Agent Startup
**Duration: 30 seconds**

This is a QUICK clip — don't linger. Just show it starts.

1. Open Termux (clean screen, nothing running)
2. START recording
3. TYPE:

```
python3 ~/reclaw_agent.py
```

4. Press Enter
5. Wait for FULL startup to complete
   - You'll see: skills loading, profiles, events, geofences
   - Final line: "🦞 Agent LIVE"
6. Wait 3 seconds after "Agent LIVE" appears
7. STOP recording

---

### 📸 CLIP 3: Master-Slave Caption
**Duration: 6 seconds**

1. Open Gallery → Screenshot 2 (Master-Slave Architecture)
2. START recording → hold 6 seconds → STOP

---

### 🎥 CLIP 4: TELEGRAM DEMO — THE MAIN EVENT ⭐
**Duration: 3-4 minutes**

This is the CORE of your demo. Everything happens in Telegram.

**SETUP:**
1. Enter split screen: Termux (top) + Telegram (bottom)
2. Termux shows the running agent with `🦞 >` prompt
3. Telegram shows your clean, empty bot chat
4. START recording
5. Wait 3 seconds (let viewer see the layout)

---

**PART A: Device Status (20 seconds)**

6. TAP on Telegram text input field
7. TYPE in Telegram: `status`
8. TAP send button
9. WAIT for bot reply (~4 seconds)
10. Bot replies:
    ```
    📱 Device Status
    🔋 Battery: 73% (discharging)
    👤 Profile: Home
    🔊 Volume: 10/15
    🧠 Runtime: llama.cpp (Q4_0)
    ⏰ Time: 05:15
    ```
11. LOOK at Termux (top): you'll see `Master: status` logged
12. WAIT 4 seconds — let viewer read the response

---

**PART B: Profile Switching (30 seconds)**

13. In Telegram, TYPE: `office mode`
14. TAP send
15. WAIT for reply (~3 seconds)
16. Bot replies:
    ```
    💼 Office profile activated
     Volume: 0%
     Brightness: 40%
     DND: On
    ```
17. **KEY MOMENT**: Notice your phone is now SILENT!
    The screen brightness also dropped.
    This happened FROM A TELEGRAM MESSAGE.
18. In Termux (top): logs show `💼 Profile -> Office`
19. WAIT 4 seconds

20. In Telegram, TYPE: `goodnight`
21. TAP send
22. Bot replies:
    ```
    🌙 Sleep profile activated
     Volume: 0%
     Brightness: 5%
     DND: On
    ```
23. **KEY MOMENT**: Screen gets VERY dim!
24. WAIT 3 seconds

25. In Telegram, TYPE: `home mode`
26. TAP send
27. Bot restores everything:
    ```
    🏠 Home profile activated
     Volume: 70%
     Brightness: 60%
     DND: Off
    ```
28. Screen brightens, volume returns
29. WAIT 3 seconds

---

**PART C: Calendar & Commute (40 seconds)**

30. In Telegram, TYPE: `events`
31. TAP send
32. Bot replies with today's events:
    ```
    📅 Today's Events:
      🕐 10:00 — Q2 Review With Team @ Connaught Place (75min)
      🕐 14:00 — Client Call @ Office Conference Room (0min)
      🕐 18:00 — Gym Session @ Gold Gym Sector 50 (20min)
    ```
33. WAIT 4 seconds

34. In Telegram, TYPE: `add meeting Dinner with Mom, 21:00, Home, 30`
35. TAP send
36. Bot replies:
    ```
    📅 Added: Dinner With Mom at 21:00
    📍 Home (30 min travel)
    ```
37. WAIT 3 seconds

38. In Telegram, TYPE: `commute`
39. TAP send
40. Bot replies with departure alerts:
    ```
    🚇 Departure Alert
    📅 Q2 Review With Team
    📍 Connaught Place, Block A
    🕐 At: 10:00
    🛣️ Blue Line Metro + walk 5min
    ⏱️ 75 min travel
    🚨 Leave by 08:30

    🚇 Departure Alert
    📅 Gym Session
    📍 Gold Gym Sector 50
    🕐 At: 18:00
    🛣️ Auto 15min
    ⏱️ 20 min travel
    🚨 Leave by 17:25
    ```
41. WAIT 5 seconds — let viewer read ALL the alerts

---

**PART D: Notification Digest (20 seconds)**

42. In Telegram, TYPE: `digest`
43. TAP send
44. Bot replies with real notification categories:
    ```
    📋 Notification Digest (X total)
    🔴 2 Urgent: Mom: Hey beta..., Boss: Call me
    🟡 3 Important: Work Group: Deadline tomorrow
    🟢 5 Casual: Instagram: user liked...
    ⚪ 8 Noise
    ```
    (Content depends on your actual notifications)
45. WAIT 4 seconds

---

**PART E: AI Free-Text & Hinglish (30 seconds)**

46. In Telegram, TYPE: `hi`
47. TAP send
48. WAIT ~10 seconds (SLM is processing on-device)
49. Bot replies with an AI-generated response:
    ```
    🧠 Hello! How can I help you today?
    ```
50. WAIT 3 seconds

51. In Telegram, TYPE: `volume badha do`
52. TAP send
53. Bot replies:
    ```
    🔊 Max volume
    ```
54. Phone volume ACTUALLY increases!
55. WAIT 3 seconds

56. In Telegram, TYPE: `help`
57. TAP send
58. Bot shows full command list
59. WAIT 4 seconds

60. STOP recording

---

### 📸 CLIP 5: Behind the Scenes Caption
**Duration: 5 seconds**

1. Exit split screen (swipe the divider to top)
2. Open Gallery → Screenshot 3 (Behind the Scenes)
3. START recording → hold 5 seconds → STOP

---

### 🎥 CLIP 6: Termux Logs
**Duration: 20 seconds**

1. Open Termux (agent still running)
2. START recording
3. SCROLL UP slowly in Termux to show all the logs:
   ```
   [05:15:23] Master: status
   [05:15:28] Master: office mode
   [05:15:28] 💼 Profile -> Office
   [05:15:35] Master: goodnight
   [05:15:35] 🌙 Profile -> Sleep
   [05:15:40] Master: home mode
   [05:15:40] 🏠 Profile -> Home
   [05:15:45] Master: events
   [05:15:50] Master: add meeting...
   [05:15:55] Master: commute
   [05:16:00] Master: digest
   [05:16:05] Master: hi
   [05:16:05] 🧠 SLM processing...
   [05:16:15] Master: volume badha do
   ```
4. Viewer sees: every Telegram command was logged on the device
5. WAIT 5 seconds at the bottom
6. STOP recording

---

### 📸 CLIP 7: Tech Stack Caption
**Duration: 5 seconds**

1. Open Gallery → Screenshot 4 (Tech Stack)
2. START recording → hold 5 seconds → STOP

---

### 📸 CLIP 8: Automation Caption
**Duration: 6 seconds**

1. Open Gallery → Screenshot 5 (Automation/Cron)
2. START recording → hold 6 seconds → STOP

---

### 📸 CLIP 9: Closing Card
**Duration: 6 seconds**

1. Open Gallery → Screenshot 6 (Impact/Closing)
2. START recording → hold 6 seconds → STOP

---

## ═══════════════════════════════════════
##   FINAL ASSEMBLY
## ═══════════════════════════════════════

### In Samsung Gallery:

1. Open Gallery → tap three dots → **Create** → **Movie** or **Video**
2. Select ALL 9 clips in order
3. Arrange them:

```
CLIP ORDER:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  📸 Title + Problem card      8s
2.  🎥 Agent startup            30s
3.  📸 Master-Slave caption      6s
4.  🎥 Telegram full demo    3-4 min  ⭐
5.  📸 Behind the Scenes         5s
6.  🎥 Termux logs              20s
7.  📸 Tech Stack                5s
8.  📸 Automation                6s
9.  📸 Closing card              6s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL:                      ~5-6 min
```

4. Trim dead time at start/end of each clip
5. Optional: add transitions (Samsung editor has fade/dissolve)
6. Optional: add background music (editor has free tracks)
7. Export → Save → Upload to YouTube/Google Drive

---

## WHAT THE FINAL VIDEO SHOWS

| Time | What viewer sees | Feature demonstrated |
|------|-----------------|---------------------|
| 0:00 | Title + problem statement | Why this matters |
| 0:08 | Agent starting in Termux | Benchmark, skills, profiles, SLM loading |
| 0:38 | Caption: Master-Slave | Architecture explanation |
| 0:44 | TG: `status` | Remote device monitoring |
| 1:04 | TG: `office mode` | Real profile switch from Telegram |
| 1:34 | TG: `goodnight` → `home mode` | Multiple profiles working |
| 2:04 | TG: `events` | Calendar management |
| 2:24 | TG: `add meeting` | Add events via chat |
| 2:44 | TG: `commute` | Departure alerts with routes |
| 3:24 | TG: `digest` | Real notification categorization |
| 3:44 | TG: `hi` | On-device SLM responding |
| 4:04 | TG: `volume badha do` | Hinglish support |
| 4:24 | TG: `help` | Full command reference |
| 4:38 | Caption: Behind the Scenes | How it works |
| 4:43 | Termux logs scrolling | Proof everything ran on-device |
| 5:03 | Caption: Tech Stack | On-device SLM, QAT, llama.cpp |
| 5:08 | Caption: Automation | Cron jobs, GPS geofencing |
| 5:14 | Caption: Closing + Impact | E-waste, privacy, cost |
| 5:20 | END | |

---

## EMERGENCY FIXES

| Problem | Quick Fix |
|---------|-----------|
| Telegram bot not replying | Check WiFi. Re-export TOKEN: `export RECLAW_BOT_TOKEN="..."` |
| Agent crashed | `python3 ~/reclaw_agent.py` to restart |
| "No upcoming commutes" | Your events are in the past. Edit CALENDAR times to the future |
| SLM says "try help" | It's fine — show 1 working SLM response, then use quick commands |
| Screen too dim after sleep | Send `home mode` in Telegram |
| Split screen won't open | Record Telegram separately (full screen). Show Termux logs after. |
| Bot sends empty reply | WiFi dropped. Wait and resend |
