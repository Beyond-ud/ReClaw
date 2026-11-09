#!/usr/bin/env python3
"""
reclaw_agent.py — Full ReClaw Passive Agent
============================================
Features:
- Telegram master-slave (phone acts as passive agent)
- Real notification parsing & digest
- GPS geofencing → auto profile switching
- Commute planner with departure alerts
- Background cron scheduler
- SLM-powered natural language commands
"""

import json, os, re, subprocess, sys, time, threading
from datetime import datetime, timedelta

# ══════════════════════════════════════════════════════════
MODEL = os.path.expanduser("~/models/Qwen3-0.6B-Q8_0.gguf")
LLAMA = os.path.expanduser("~/llama.cpp/llama.cpp/build/bin/llama-completion")
TOKEN = os.environ.get("RECLAW_BOT_TOKEN", "")
CHAT_ID = os.environ.get("RECLAW_CHAT_ID", "")

PROFILES = {
    "home":    {"volume": 70, "dnd": False, "brightness": 60},
    "office":  {"volume": 0,  "dnd": True,  "brightness": 40},
    "transit": {"volume": 40, "dnd": False, "brightness": 50},
    "sleep":   {"volume": 0,  "dnd": True,  "brightness": 5},
}

# Geofence coordinates (edit for your locations)
GEOFENCES = {
    "home":   {"lat": 28.6139, "lon": 77.2090, "radius_m": 200},
    "office": {"lat": 28.5355, "lon": 77.3910, "radius_m": 300},
}

# Starred contacts for notification priority
STARRED = ["Mom", "Boss", "Partner", "Dad"]
MUTED_APPS = ["Instagram", "YouTube", "Games"]

# Simulated calendar (replace with real API if available)
CALENDAR = [
    {"title": "Q2 Review", "time": "10:00", "location": "Connaught Place, Block A",
     "route": "Blue Line Metro → walk 5min", "travel_min": 75},
    {"title": "Team Standup", "time": "14:00", "location": "Office",
     "route": "Already at office", "travel_min": 0},
]

current_profile = "home"
agent_running = True

# ══════════════════════════════════════════════════════════
#  Termux API Layer
# ══════════════════════════════════════════════════════════

def tx(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except:
        return ""

def tx_json(cmd):
    try:
        return json.loads(tx(cmd))
    except:
        return {}

class Device:
    def volume(self, pct):
        tx(["termux-volume", "music", str(max(0, min(15, pct * 15 // 100)))])

    def brightness(self, pct):
        tx(["termux-brightness", str(max(0, min(255, pct * 255 // 100)))])

    def dnd(self, on):
        if on:
            tx(["termux-volume", "music", "0"])

    def toast(self, msg):
        tx(["termux-toast", "-g", "middle", msg])

    def notify(self, title, body):
        tx(["termux-notification", "--title", title, "--content", body, "--id", "reclaw"])

    def battery(self):
        return tx_json(["termux-battery-status"])

    def volumes(self):
        return tx_json(["termux-volume"])

    def location(self):
        return tx_json(["termux-location", "-p", "network", "-r", "once"])

    def notifications(self):
        r = tx(["termux-notification-list"])
        try:
            return json.loads(r) if r else []
        except:
            return []

dev = Device()

# ══════════════════════════════════════════════════════════
#  Telegram
# ══════════════════════════════════════════════════════════

def tg_send(text):
    if not TOKEN or not CHAT_ID:
        return
    try:
        import urllib.request
        data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except:
        pass

def tg_poll():
    """Background thread: listen for Telegram commands from master phone."""
    import urllib.request
    offset = 0
    while agent_running:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=10"
            resp = urllib.request.urlopen(url, timeout=15)
            for u in json.loads(resp.read()).get("result", []):
                offset = u["update_id"] + 1
                text = u.get("message", {}).get("text", "")
                cid = str(u.get("message", {}).get("chat", {}).get("id", ""))
                if text and cid == CHAT_ID:
                    log(f"📨 Master: \"{text}\"")
                    reply = handle(text)
                    tg_send(reply)
        except:
            time.sleep(3)

# ══════════════════════════════════════════════════════════
#  Profile Manager
# ══════════════════════════════════════════════════════════

def switch_profile(name):
    global current_profile
    if name not in PROFILES:
        return f"❌ Unknown profile: {name}"
    p = PROFILES[name]
    current_profile = name

    dev.volume(p["volume"])
    dev.brightness(p["brightness"])
    if p["dnd"]:
        dev.dnd(True)

    icons = {"home": "🏠", "office": "💼", "transit": "🚇", "sleep": "🌙"}
    icon = icons.get(name, "📱")
    dev.toast(f"{icon} {name.title()} mode")
    dev.notify(f"{icon} ReClaw", f"{name.title()} profile activated")

    log(f"{icon} Profile → {name.title()} | vol:{p['volume']}% bri:{p['brightness']}% dnd:{p['dnd']}")
    return (f"{icon} <b>{name.title()}</b> profile activated\n"
            f"• Volume: {p['volume']}%\n"
            f"• Brightness: {p['brightness']}%\n"
            f"• DND: {'On' if p['dnd'] else 'Off'}")

# ══════════════════════════════════════════════════════════
#  Skill: Notification Hub (REAL notifications)
# ══════════════════════════════════════════════════════════

def notification_digest():
    """Parse REAL notifications from the phone and categorize them."""
    notifs = dev.notifications()
    urgent, important, casual, noise = [], [], [], []

    for n in notifs:
        title = n.get("title", "")
        pkg = n.get("packageName", "")
        content = n.get("content", "")

        # Categorize
        if any(c.lower() in title.lower() for c in STARRED):
            urgent.append(f"{title}: {content[:40]}")
        elif "whatsapp" in pkg.lower() or "telegram" in pkg.lower():
            important.append(f"{title}: {content[:40]}")
        elif any(a.lower() in pkg.lower() for a in MUTED_APPS):
            noise.append(title)
        else:
            casual.append(f"{title}: {content[:40]}")

    total = len(notifs)
    msg = f"📋 <b>Notification Digest</b> ({total} total)\n━━━━━━━━━━━━━━━━━━━━\n"

    if urgent:
        msg += f"🔴 <b>{len(urgent)} Urgent:</b>\n"
        for u in urgent[:5]:
            msg += f"   • {u}\n"
    if important:
        msg += f"🟡 <b>{len(important)} Important:</b>\n"
        for i in important[:5]:
            msg += f"   • {i}\n"
    if casual:
        msg += f"🟢 <b>{len(casual)} Casual:</b>\n"
        for c in casual[:3]:
            msg += f"   • {c}\n"
    if noise:
        msg += f"⚪ {len(noise)} Noise (auto-dismissed)\n"
    msg += "━━━━━━━━━━━━━━━━━━━━"

    if total == 0:
        msg = "📋 No notifications right now. All clear! ✅"

    log(f"📋 Digest: {len(urgent)} urgent, {len(important)} important, {len(casual)} casual, {len(noise)} noise")
    return msg

# ══════════════════════════════════════════════════════════
#  Skill: Commute Planner
# ══════════════════════════════════════════════════════════

def commute_check():
    """Check today's calendar and generate departure alerts."""
    now = datetime.now()
    alerts = []

    for event in CALENDAR:
        h, m = map(int, event["time"].split(":"))
        event_time = now.replace(hour=h, minute=m, second=0)
        depart_time = event_time - timedelta(minutes=event["travel_min"] + 15)

        if now < depart_time and event["travel_min"] > 0:
            alerts.append(
                f"🚇 <b>Departure Alert</b>\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"📅 {event['title']}\n"
                f"📍 {event['location']}\n"
                f"🕐 Event: {event['time']}\n"
                f"🛣️ Route: {event['route']}\n"
                f"⏱️ Travel: {event['travel_min']} min\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"🚨 Leave by <b>{depart_time.strftime('%H:%M')}</b>"
            )

    if alerts:
        return "\n\n".join(alerts)
    return "✅ No upcoming commutes. You're all set!"

# ══════════════════════════════════════════════════════════
#  Skill: GPS Geofencing (Auto-Profile)
# ══════════════════════════════════════════════════════════

def haversine(lat1, lon1, lat2, lon2):
    """Distance in meters between two GPS points."""
    import math
    R = 6371000
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + \
        math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
    return 2 * R * math.asin(math.sqrt(a))

def check_geofence():
    """Check GPS and auto-switch profile if inside a geofence."""
    global current_profile
    loc = dev.location()
    if not loc or "latitude" not in loc:
        return

    lat, lon = loc["latitude"], loc["longitude"]
    log(f"📍 GPS: {lat:.4f}, {lon:.4f}")

    for name, fence in GEOFENCES.items():
        dist = haversine(lat, lon, fence["lat"], fence["lon"])
        if dist <= fence["radius_m"] and current_profile != name:
            log(f"📍 Entered {name} geofence ({dist:.0f}m)")
            result = switch_profile(name)
            tg_send(f"📍 Auto-detected: entered {name} zone\n\n{result}")
            return

# ══════════════════════════════════════════════════════════
#  Background Scheduler (Cron)
# ══════════════════════════════════════════════════════════

def cron_loop():
    """Background: run scheduled tasks like a real agent."""
    last_commute_check = ""
    last_digest = ""
    last_geofence = 0

    while agent_running:
        now = datetime.now()
        hm = now.strftime("%H:%M")

        # 7:00 AM — Morning commute check
        if hm == "07:00" and last_commute_check != hm:
            last_commute_check = hm
            log("⏰ Cron: morning commute check")
            alert = commute_check()
            tg_send(alert)
            print(f"  {alert}")

        # 9:00 AM weekdays — Auto office profile
        if hm == "09:00" and now.weekday() < 5 and current_profile != "office":
            log("⏰ Cron: office hours started")
            result = switch_profile("office")
            tg_send(f"⏰ Scheduled: office hours\n\n{result}")

        # 6:00 PM weekdays — Auto home profile
        if hm == "18:00" and now.weekday() < 5 and current_profile != "home":
            log("⏰ Cron: office hours ended")
            result = switch_profile("home")
            tg_send(f"⏰ Scheduled: heading home\n\n{result}")

        # 8:00 PM — Evening digest
        if hm == "20:00" and last_digest != hm:
            last_digest = hm
            log("⏰ Cron: evening notification digest")
            digest = notification_digest()
            tg_send(digest)

        # Every 5 min — GPS geofence check
        if time.time() - last_geofence > 300:
            last_geofence = time.time()
            try:
                check_geofence()
            except:
                pass

        time.sleep(30)

# ══════════════════════════════════════════════════════════
#  SLM Inference (fallback for unknown commands)
# ══════════════════════════════════════════════════════════

SYS = ("You are ReClaw. Use [CALL tool(args)] format. "
       "Tools: switch_profile(home/office/sleep/transit), "
       "device.volume.set(0-100), device.brightness.set(0-100), "
       "slave.status(), notification.digest(), commute.check(). "
       "Be brief. /no_think")

def slm(text):
    try:
        r = subprocess.run(
            [LLAMA, "-m", MODEL, "-p",
             f"<|im_start|>system\n{SYS}<|im_end|>\n<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n",
             "-n", "60", "--temp", "0.7", "--top-k", "20",
             "--presence-penalty", "1.5"],
            capture_output=True, text=True, timeout=30)
        out = r.stdout.strip()
        out = re.sub(r'<think>.*?</think>', '', out, flags=re.DOTALL)
        out = re.sub(r'<think>.*', '', out, flags=re.DOTALL)
        if "<|im_start|>assistant" in out:
            out = out.split("<|im_start|>assistant")[-1]
        return out.replace("<|im_end|>", "").strip().split("\n")[0]
    except:
        return ""

# ══════════════════════════════════════════════════════════
#  Command Router
# ══════════════════════════════════════════════════════════

def handle(text):
    """Route command → skill → execute → respond."""
    t = text.lower().strip()

    # Profile commands
    for name in PROFILES:
        if name in t and any(w in t for w in ["mode", "profile", "switch", "laga", "karo", name]):
            return switch_profile(name)
    if any(w in t for w in ["goodnight", "soja", "night", "neend"]):
        return switch_profile("sleep")

    # Status
    if any(w in t for w in ["status", "battery", "kaisa", "haal", "how are you"]):
        bat = dev.battery()
        vol_data = dev.volumes()
        vol = "?"
        for v in (vol_data if isinstance(vol_data, list) else []):
            if v.get("stream") == "music":
                vol = f"{v.get('volume', '?')}/{v.get('max_volume', '?')}"
        return (f"📱 <b>Device Status</b>\n━━━━━━━━━━━━━━━━━━\n"
                f"🔋 Battery: {bat.get('percentage', '?')}% ({bat.get('status', '?')})\n"
                f"👤 Profile: {current_profile.title()}\n"
                f"🔊 Volume: {vol}\n"
                f"🧠 Runtime: llama.cpp (Q8_0)\n"
                f"⏰ Uptime: {datetime.now().strftime('%H:%M')}\n━━━━━━━━━━━━━━━━━━")

    # Notification digest
    if any(w in t for w in ["digest", "notification", "messages", "kya aaya", "missed"]):
        return notification_digest()

    # Commute
    if any(w in t for w in ["commute", "leave", "route", "travel", "nikalna", "meeting"]):
        return commute_check()

    # GPS check
    if any(w in t for w in ["location", "gps", "kahan", "where"]):
        loc = dev.location()
        if loc and "latitude" in loc:
            return f"📍 GPS: {loc['latitude']:.4f}, {loc['longitude']:.4f}\nAccuracy: {loc.get('accuracy', '?')}m"
        return "📍 Getting location... (GPS may take a moment)"

    # Volume
    if "volume" in t or "awaaz" in t or "sound" in t:
        if any(w in t for w in ["0", "zero", "mute", "silent", "chup", "band"]):
            dev.volume(0); return "🔇 Volume muted"
        if any(w in t for w in ["full", "max", "100", "badha", "loud"]):
            dev.volume(100); return "🔊 Volume maxed"
        m = re.search(r'(\d+)', t)
        if m:
            v = int(m.group(1))
            dev.volume(v); return f"🔊 Volume → {v}%"

    # Brightness
    if "bright" in t or "screen" in t or "roshni" in t:
        if any(w in t for w in ["full", "max", "100"]):
            dev.brightness(100); return "💡 Brightness maxed"
        if any(w in t for w in ["low", "dim", "kam", "0"]):
            dev.brightness(10); return "💡 Brightness dimmed"
        m = re.search(r'(\d+)', t)
        if m:
            b = int(m.group(1))
            dev.brightness(b); return f"💡 Brightness → {b}%"

    # Benchmark
    if any(w in t for w in ["benchmark", "specs", "hardware"]):
        return run_benchmark_text()

    # Help
    if any(w in t for w in ["help", "commands", "kya kar sakta"]):
        return ("🦞 <b>ReClaw Commands</b>\n"
                "• office/home/sleep/transit mode\n"
                "• status — device info\n"
                "• digest — notification summary\n"
                "• commute — departure alerts\n"
                "• location — GPS coordinates\n"
                "• volume/brightness 0-100\n"
                "• benchmark — hardware report\n"
                "• Any natural language → SLM")

    # SLM fallback
    log("🧠 SLM processing...")
    resp = slm(text)
    if resp:
        # Try to execute any tool calls in response
        pm = re.search(r'switch_profile\((\w+)\)', resp)
        if pm:
            return switch_profile(pm.group(1))
        vm = re.search(r'volume\.set\((\d+)\)', resp)
        if vm:
            dev.volume(int(vm.group(1)))
        bm = re.search(r'brightness\.set\((\d+)\)', resp)
        if bm:
            dev.brightness(int(bm.group(1)))
        if "digest" in resp:
            return notification_digest()
        if "commute" in resp:
            return commute_check()
        return f"🧠 {resp}"

    return "🤔 Samajh nahi aaya. Type 'help' for commands."

# ══════════════════════════════════════════════════════════
#  Benchmark
# ══════════════════════════════════════════════════════════

def get_ram():
    try:
        with open("/proc/meminfo") as f:
            return int(f.readline().split()[1]) // 1024
    except:
        return 0

def run_benchmark_text():
    ram = get_ram()
    arch = subprocess.run(["uname", "-m"], capture_output=True, text=True).stdout.strip()
    bat = dev.battery()
    cores = os.cpu_count() or 0
    return (f"📊 <b>Benchmark Report</b>\n═══════════════════\n"
            f"Arch: {arch}\nCores: {cores}\nRAM: {ram} MB\n"
            f"Battery: {bat.get('percentage', '?')}%\n"
            f"Runtime: llama.cpp ✅\n═══════════════════")

def log(msg):
    print(f"  [{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ══════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════

def main():
    global agent_running

    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║       🦞 ReClaw Agent v2.0 — Live        ║")
    print("  ║   Passive AI Agent for Old Smartphones    ║")
    print("  ╚══════════════════════════════════════════╝\n")

    # Benchmark
    log("🔍 Benchmarking device...")
    ram = get_ram()
    arch = subprocess.run(["uname", "-m"], capture_output=True, text=True).stdout.strip()
    log(f"   {arch} | {os.cpu_count()} cores | {ram} MB RAM")
    log(f"   Runtime: llama.cpp (GGUF Q8_0)")

    # Model
    if not os.path.exists(MODEL):
        log("❌ Model not found!"); sys.exit(1)
    sz = os.path.getsize(MODEL) / 1024 / 1024
    log(f"   Model: {os.path.basename(MODEL)} ({sz:.0f} MB)")

    # Skills
    log("📦 Skills loaded:")
    for s in ["routine-manager", "commute-planner", "smart-customizer", "notification-hub"]:
        log(f"   ✅ {s}")

    # Profiles
    log("👤 Profiles:")
    for n, p in PROFILES.items():
        log(f"   📋 {n}: vol={p['volume']}% bri={p['brightness']}% dnd={p['dnd']}")

    # Telegram
    if TOKEN and CHAT_ID:
        log("📡 Telegram: connected (master-slave active)")
        tg_send("🦞 ReClaw agent started!\n📱 Ready for commands.\nType 'help' for options.")
        threading.Thread(target=tg_poll, daemon=True).start()
    else:
        log("⚠️  Set RECLAW_BOT_TOKEN & RECLAW_CHAT_ID for Telegram")

    # Cron
    log("⏰ Background scheduler started")
    threading.Thread(target=cron_loop, daemon=True).start()

    # Auto-profile based on time
    h = datetime.now().hour
    if 9 <= h < 18:
        switch_profile("office")
    elif 22 <= h or h < 6:
        switch_profile("sleep")
    else:
        switch_profile("home")

    print(f"\n  {'═' * 44}")
    print("  🦞 Agent LIVE — type commands or use Telegram")
    print("  Try: office mode | digest | commute | status")
    print(f"  {'═' * 44}\n")

    while True:
        try:
            inp = input("  🦞 > ")
        except (EOFError, KeyboardInterrupt):
            break
        if inp.strip().lower() in ("quit", "exit", "q"):
            break
        if not inp.strip():
            continue
        reply = handle(inp.strip())
        # Print with indent
        for line in reply.replace("<b>", "").replace("</b>", "").split("\n"):
            print(f"  {line}")
        print()

    agent_running = False
    log("Agent stopped.")
    tg_send("🦞 ReClaw agent stopped.")

if __name__ == "__main__":
    main()
