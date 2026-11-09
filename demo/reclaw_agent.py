#!/usr/bin/env python3
"""ReClaw Agent v2.1 — Full featured passive AI phone agent."""
import json,os,re,subprocess,sys,time,threading,pty,string,math
from datetime import datetime,timedelta

MODEL=os.path.expanduser("~/models/qwen3-0.6b-q4_0.gguf")
CHAT_BIN=os.path.expanduser("~/llama.cpp/llama.cpp/build/bin/llama-simple-chat")
TOKEN=os.environ.get("RECLAW_BOT_TOKEN","")
CHATID=os.environ.get("RECLAW_CHAT_ID","")
PROFILES={"home":{"vol":70,"dnd":False,"bri":60},"office":{"vol":0,"dnd":True,"bri":40},"transit":{"vol":40,"dnd":False,"bri":50},"sleep":{"vol":0,"dnd":True,"bri":5}}
STARRED=["Mom","Boss","Partner","Dad"]
CALENDAR=[{"title":"Q2 Review","time":"10:00","loc":"Connaught Place","route":"Blue Line Metro","mins":75},{"title":"Team Standup","time":"14:00","loc":"Office","route":"Already there","mins":0}]
GEOFENCES={"home":{"lat":28.6139,"lon":77.2090,"r":200},"office":{"lat":28.5355,"lon":77.3910,"r":300}}
cur_profile="home"
running=True
slm_fd=None
slm_pid=None

# ═══ Termux API ═══
def tx(cmd):
    try: return subprocess.run(cmd,capture_output=True,text=True,timeout=10).stdout.strip()
    except: return ""
def txj(cmd):
    try: return json.loads(tx(cmd))
    except: return {}
def vol(p):tx(["termux-volume","music",str(max(0,min(15,p*15//100)))])
def bri(p):tx(["termux-brightness",str(max(0,min(255,p*255//100)))])
def toast(m):tx(["termux-toast","-g","middle",m])
def bat():return txj(["termux-battery-status"])
def vols():return txj(["termux-volume"])
def loc():return txj(["termux-location","-p","network","-r","once"])
def notifs():
    r=tx(["termux-notification-list"])
    try: return json.loads(r) if r else []
    except: return []

# ═══ Telegram ═══
def tg(text):
    if not TOKEN or not CHATID: return
    try:
        import urllib.request
        d=json.dumps({"chat_id":CHATID,"text":text}).encode()
        r=urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data=d,headers={"Content-Type":"application/json"})
        urllib.request.urlopen(r,timeout=5)
    except: pass
def tg_poll():
    import urllib.request
    off=0
    while running:
        try:
            resp=urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={off}&timeout=10",timeout=15)
            for u in json.loads(resp.read()).get("result",[]):
                off=u["update_id"]+1
                txt=u.get("message",{}).get("text","")
                cid=str(u.get("message",{}).get("chat",{}).get("id",""))
                if txt and cid==CHATID:
                    log(f"Master: {txt}")
                    tg(handle(txt))
        except: time.sleep(3)

# ═══ Profile Manager ═══
def switch(name):
    global cur_profile
    if name not in PROFILES: return f"Unknown: {name}"
    p=PROFILES[name]; cur_profile=name
    vol(p["vol"]); bri(p["bri"])
    if p["dnd"]: tx(["termux-volume","music","0"])
    icons={"home":"🏠","office":"💼","transit":"🚇","sleep":"🌙"}
    ic=icons.get(name,"📱")
    toast(f"{ic} {name.title()} mode")
    log(f"{ic} Profile -> {name.title()}")
    return f"{ic} {name.title()} profile activated\n Volume: {p['vol']}%\n Brightness: {p['bri']}%\n DND: {'On' if p['dnd'] else 'Off'}"

# ═══ Notification Digest ═══
def digest():
    ns=notifs(); urg,imp,cas,noi=[],[],[],[]
    for n in ns:
        t=n.get("title","");pk=n.get("packageName","");c=n.get("content","")
        if any(s.lower() in t.lower() for s in STARRED): urg.append(f"{t}: {c[:40]}")
        elif "whatsapp" in pk.lower() or "telegram" in pk.lower(): imp.append(f"{t}: {c[:40]}")
        elif any(a in pk.lower() for a in ["instagram","youtube","game"]): noi.append(t)
        else: cas.append(f"{t}: {c[:40]}")
    m=f"📋 Notification Digest ({len(ns)} total)\n"
    if urg: m+=f"🔴 {len(urg)} Urgent:\n"+"".join(f"  {u}\n" for u in urg[:5])
    if imp: m+=f"🟡 {len(imp)} Important:\n"+"".join(f"  {i}\n" for i in imp[:5])
    if cas: m+=f"🟢 {len(cas)} Casual:\n"+"".join(f"  {c}\n" for c in cas[:3])
    if noi: m+=f"⚪ {len(noi)} Noise\n"
    if not ns: m="📋 No notifications. All clear!"
    return m

# ═══ Commute Planner ═══
def commute():
    now=datetime.now(); alerts=[]
    for e in CALENDAR:
        h,mi=map(int,e["time"].split(":"))
        et=now.replace(hour=h,minute=mi,second=0)
        dt=et-timedelta(minutes=e["mins"]+15)
        if now<et and e["mins"]>0:
            alerts.append(f"🚇 Departure Alert\n📅 {e['title']}\n📍 {e['loc']}\n🕐 At: {e['time']}\n🛣️ {e['route']}\n⏱️ {e['mins']} min travel\n🚨 Leave by {dt.strftime('%H:%M')}")
    return "\n\n".join(alerts) if alerts else "✅ No upcoming commutes!"

def add_event(text):
    """Add event: title, HH:MM, location, travel_mins"""
    try:
        clean = text.lower().replace("add meeting","").replace("add event","").replace("add commute","").strip()
        parts = [p.strip() for p in clean.split(",")]
        if len(parts) >= 3:
            title = parts[0].title()
            time_str = parts[1]
            loc_str = parts[2]
            mins = int(parts[3]) if len(parts) > 3 else 30
            CALENDAR.append({"title":title,"time":time_str,"loc":loc_str,"route":"TBD","mins":mins})
            return f"📅 Added: {title} at {time_str}\n📍 {loc_str} ({mins} min travel)"
        else:
            return "📅 Format: add meeting Title, HH:MM, Location, mins\nExample: add meeting Gym, 18:00, Gold Gym, 20"
    except:
        return "📅 Format: add meeting Title, HH:MM, Location, mins"

def list_events():
    if not CALENDAR: return "📅 No events scheduled"
    m = "📅 Today's Events:\n"
    for e in CALENDAR:
        m += f"  🕐 {e['time']} — {e['title']} @ {e['loc']} ({e['mins']}min travel)\n"
    return m

# ═══ GPS Geofencing ═══
def haversine(a1,o1,a2,o2):
    R=6371000;p=math.pi/180
    a=0.5-math.cos((a2-a1)*p)/2+math.cos(a1*p)*math.cos(a2*p)*(1-math.cos((o2-o1)*p))/2
    return 2*R*math.asin(math.sqrt(a))

def check_geo():
    l=loc()
    if not l or "latitude" not in l: return
    lat,lon=l["latitude"],l["longitude"]
    log(f"📍 GPS: {lat:.4f}, {lon:.4f}")
    for n,f in GEOFENCES.items():
        d=haversine(lat,lon,f["lat"],f["lon"])
        if d<=f["r"] and cur_profile!=n:
            log(f"📍 Entered {n} zone ({d:.0f}m)")
            r=switch(n)
            tg(f"📍 Auto: entered {n} zone\n{r}")
            return

# ═══ Device Status ═══
def status():
    b=bat();v=vols();vl="?"
    for x in (v if isinstance(v,list) else []):
        if x.get("stream")=="music": vl=f"{x.get('volume','?')}/{x.get('max_volume','?')}"
    return f"📱 Device Status\n🔋 Battery: {b.get('percentage','?')}% ({b.get('status','?')})\n👤 Profile: {cur_profile.title()}\n🔊 Volume: {vl}\n🧠 Runtime: llama.cpp (Q4_0)\n⏰ Time: {datetime.now().strftime('%H:%M')}"

# ═══ SLM (persistent via pty) ═══
def slm_start():
    global slm_fd, slm_pid
    try:
        pid,fd=pty.fork()
        if pid==0:
            os.execvp(CHAT_BIN,[CHAT_BIN,"-m",MODEL])
        else:
            slm_pid=pid; slm_fd=fd
            time.sleep(4)
            try: os.read(fd,8192)
            except: pass
            log("🧠 SLM ready")
    except Exception as e:
        log(f"🧠 SLM failed: {e}")
        slm_fd=None

def slm(text):
    global slm_fd,slm_pid
    if slm_fd is None: return ""
    try:
        os.write(slm_fd,(text+"\n").encode())
        time.sleep(5)
        chunks=[]
        import select as sel
        while True:
            if sel.select([slm_fd],[],[],0.5)[0]:
                data=os.read(slm_fd,4096).decode(errors='ignore')
                chunks.append(data)
            else: break
        out="".join(chunks)
        out=re.sub(r'\x1b\[[0-9;]*m','',out)
        out=''.join(c for c in out if c in string.printable)
        out=re.sub(r'<think>.*?</think>','',out,flags=re.DOTALL)
        out=re.sub(r'<think>.*','',out,flags=re.DOTALL)
        out=out.replace("> ","").replace(text,"").strip()
        lines=[l.strip() for l in out.split("\n") if l.strip()]
        return " ".join(lines[:3]) if lines else ""
    except: return ""

# ═══ Command Router ═══
def handle(text):
    t=text.lower().strip()
    # Profiles
    for n in PROFILES:
        if n in t and any(w in t for w in ["mode","profile","switch","laga","karo",n]): return switch(n)
    if any(w in t for w in ["goodnight","soja","night","neend"]): return switch("sleep")
    # Status
    if any(w in t for w in ["status","battery","kaisa","haal"]): return status()
    # Notifications
    if any(w in t for w in ["digest","notification","messages","kya aaya","missed"]): return digest()
    # Commute
    if any(w in t for w in ["commute","leave","route","nikalna"]): return commute()
    # Add event
    if "add" in t and any(w in t for w in ["meeting","event","commute","calendar"]): return add_event(text)
    # List events
    if any(w in t for w in ["events","schedule","aaj kya","calendar"]): return list_events()
    # Location
    if any(w in t for w in ["location","gps","kahan","where"]):
        l=loc()
        return f"📍 GPS: {l.get('latitude','?')}, {l.get('longitude','?')}" if l and "latitude" in l else "📍 Getting GPS..."
    # Volume
    if "volume" in t or "awaaz" in t:
        if any(w in t for w in ["0","mute","silent","chup"]): vol(0); return "🔇 Muted"
        if any(w in t for w in ["full","max","badha","loud"]): vol(100); return "🔊 Max volume"
        m=re.search(r'(\d+)',t)
        if m: vol(int(m.group(1))); return f"🔊 Volume -> {m.group(1)}%"
    # Brightness
    if "bright" in t or "roshni" in t:
        if any(w in t for w in ["full","max"]): bri(100); return "💡 Max brightness"
        if any(w in t for w in ["low","dim","kam"]): bri(10); return "💡 Dimmed"
        m=re.search(r'(\d+)',t)
        if m: bri(int(m.group(1))); return f"💡 Brightness -> {m.group(1)}%"
    # Help
    if any(w in t for w in ["help","commands","kya kar"]):
        return "🦞 ReClaw Commands:\n office/home/sleep/transit mode\n status | digest | commute\n location | volume | brightness\n events — list today's events\n add meeting Title, HH:MM, Loc, mins\n Any free text -> SLM processes it"
    # SLM fallback
    log("🧠 SLM processing...")
    r=slm(text)
    if r:
        pm=re.search(r'switch_profile\((\w+)\)',r)
        if pm: return switch(pm.group(1))
        return f"🧠 {r}"
    return "🤔 Try 'help' for commands"

# ═══ Background Cron ═══
def cron():
    lc=ld=""
    while running:
        hm=datetime.now().strftime("%H:%M")
        # Morning commute check
        if hm=="07:00" and lc!=hm:
            lc=hm; log("⏰ Morning commute check")
            a=commute(); tg(a)
        # Auto office 9 AM weekdays
        if hm=="09:00" and cur_profile!="office" and datetime.now().weekday()<5:
            log("⏰ Auto office"); switch("office"); tg("⏰ Auto: Office mode")
        # Auto home 6 PM weekdays
        if hm=="18:00" and cur_profile!="home" and datetime.now().weekday()<5:
            log("⏰ Auto home"); switch("home"); tg("⏰ Auto: Home mode")
        # Evening digest
        if hm=="20:00" and ld!=hm:
            ld=hm; log("⏰ Evening digest"); tg(digest())
        # GPS geofence check every 5 min
        try: check_geo()
        except: pass
        time.sleep(30)

def log(m): print(f"  [{datetime.now().strftime('%H:%M:%S')}] {m}")

# ═══ Main ═══
def main():
    global running
    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║       🦞 ReClaw Agent v2.1 — Live        ║")
    print("  ║   Passive AI Agent for Old Smartphones    ║")
    print("  ╚══════════════════════════════════════════╝\n")
    # Benchmark
    log(f"🔍 Device: {os.cpu_count()} cores | {subprocess.run(['uname','-m'],capture_output=True,text=True).stdout.strip()}")
    if not os.path.exists(MODEL): log("❌ Model not found!"); sys.exit(1)
    log(f"✅ Model: {os.path.getsize(MODEL)//1024//1024} MB")
    # Skills
    log("📦 Skills:")
    for s in ["routine-manager","commute-planner","smart-customizer","notification-hub"]: log(f"  ✅ {s}")
    # Profiles
    log("👤 Profiles:")
    for n,p in PROFILES.items(): log(f"  📋 {n}: vol={p['vol']}% bri={p['bri']}% dnd={p['dnd']}")
    # Events
    log(f"📅 Events: {len(CALENDAR)} scheduled")
    # Geofences
    log(f"📍 Geofences: {', '.join(GEOFENCES.keys())}")
    # Telegram
    if TOKEN and CHATID:
        log("📡 Telegram: connected (master-slave active)")
        tg("🦞 ReClaw v2.1 started!\nType 'help' for commands.")
        threading.Thread(target=tg_poll,daemon=True).start()
    else: log("⚠️ Set RECLAW_BOT_TOKEN & RECLAW_CHAT_ID for Telegram")
    # Cron
    threading.Thread(target=cron,daemon=True).start()
    log("⏰ Background scheduler active")
    # Auto-profile by time
    h=datetime.now().hour
    if 9<=h<18: switch("office")
    elif 22<=h or h<6: switch("sleep")
    else: switch("home")
    # SLM
    slm_start()
    # Ready
    print(f"\n  {'═'*44}")
    print("  🦞 Agent LIVE — type commands or use Telegram")
    print("  Try: office mode | digest | commute | status")
    print("  Add: add meeting Title, HH:MM, Location, mins")
    print(f"  {'═'*44}\n")
    while True:
        try: inp=input("  🦞 > ")
        except: break
        if inp.strip().lower() in ("quit","exit","q"): break
        if not inp.strip(): continue
        r=handle(inp.strip())
        for l in r.split("\n"): print(f"  {l}")
        print()
    running=False; log("Stopped."); tg("🦞 Agent stopped.")

if __name__=="__main__": main()
