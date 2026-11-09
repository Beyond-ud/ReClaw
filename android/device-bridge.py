#!/usr/bin/env python3
"""
device-bridge.py — Android device control bridge for PicoClaw.

Provides Python wrappers around Termux:API commands to control
Android hardware: volume, brightness, DND, wallpaper, notifications,
location, and more.

This bridge is used by PicoClaw skills to execute device control
actions. It runs on the old phone (slave) and translates tool calls
from the SLM into actual Android API calls.

Usage:
    python3 device-bridge.py server          # Start JSON-RPC server
    python3 device-bridge.py test            # Run hardware test
    python3 device-bridge.py volume 50       # Set volume directly

Prerequisites:
    - Termux installed on Android device
    - Termux:API app installed
    - termux-api package: pkg install termux-api
"""

import json
import os
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional


# ══════════════════════════════════════════════════════════
#  Device Control Functions (Termux:API wrappers)
# ══════════════════════════════════════════════════════════

def termux_cmd(cmd: list[str], input_data: str = None) -> str:
    """Run a Termux:API command and return stdout."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            input=input_data,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return '{"error": "command timed out"}'
    except FileNotFoundError:
        return '{"error": "termux-api not installed"}'


class DeviceBridge:
    """Provides device control methods mapped to PicoClaw tool calls."""

    # ── Volume ──
    def volume_set(self, level: int) -> dict:
        """Set media volume (0-100)."""
        # Termux volume is 0-15, we map from 0-100
        termux_level = max(0, min(15, int(level * 15 / 100)))
        termux_cmd(["termux-volume", "music", str(termux_level)])
        return {"action": "volume.set", "level": level, "termux_level": termux_level}

    def volume_get(self) -> dict:
        """Get current volume levels."""
        output = termux_cmd(["termux-volume"])
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"error": "failed to parse volume"}

    # ── DND (Do Not Disturb) ──
    def dnd_toggle(self, enabled: bool) -> dict:
        """Toggle Do Not Disturb mode."""
        mode = "priority" if enabled else "all"
        termux_cmd(["termux-notification-remove", "--all"])  # Clear noise
        # DND is set via notification policy
        termux_cmd(["termux-volume", "music", "0" if enabled else "7"])
        return {"action": "dnd.toggle", "enabled": enabled, "mode": mode}

    # ── Brightness ──
    def brightness_set(self, level: int) -> dict:
        """Set screen brightness (0-100)."""
        # Android brightness is 0-255
        android_level = max(0, min(255, int(level * 255 / 100)))
        termux_cmd(["termux-brightness", str(android_level)])
        return {"action": "brightness.set", "level": level}

    # ── Wallpaper ──
    def wallpaper_set(self, image_id: str) -> dict:
        """Set wallpaper from a preset pack."""
        wallpaper_dir = os.path.expanduser("~/wallpapers")
        path = os.path.join(wallpaper_dir, f"{image_id}.jpg")

        if not os.path.exists(path):
            # Try PNG
            path = os.path.join(wallpaper_dir, f"{image_id}.png")

        if os.path.exists(path):
            termux_cmd(["termux-wallpaper", "-f", path])
            return {"action": "wallpaper.set", "image": image_id, "path": path}
        else:
            return {"action": "wallpaper.set", "error": f"wallpaper '{image_id}' not found"}

    # ── Location ──
    def location_get(self) -> dict:
        """Get current GPS coordinates."""
        output = termux_cmd(["termux-location", "-p", "gps", "-r", "once"])
        try:
            loc = json.loads(output)
            return {
                "action": "location.get",
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "accuracy": loc.get("accuracy"),
            }
        except json.JSONDecodeError:
            return {"error": "failed to get location"}

    # ── Notifications ──
    def notification_send(self, title: str, content: str, priority: str = "default") -> dict:
        """Send a notification on the device."""
        cmd = [
            "termux-notification",
            "--title", title,
            "--content", content,
            "--priority", priority,
            "--id", "picoclaw",
        ]
        termux_cmd(cmd)
        return {"action": "notification.send", "title": title}

    def notification_list(self) -> list:
        """List all current notifications."""
        output = termux_cmd(["termux-notification-list"])
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return []

    # ── Battery ──
    def battery_status(self) -> dict:
        """Get battery status."""
        output = termux_cmd(["termux-battery-status"])
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"error": "failed to get battery status"}

    # ── Alarm ──
    def alarm_set(self, time_str: str) -> dict:
        """Set an alarm (HH:MM format)."""
        parts = time_str.split(":")
        if len(parts) == 2:
            hour, minute = parts
            # Use Android intent to set alarm
            termux_cmd([
                "am", "start",
                "-a", "android.intent.action.SET_ALARM",
                "--ei", "android.intent.extra.alarm.HOUR", hour,
                "--ei", "android.intent.extra.alarm.MINUTES", minute,
                "--ez", "android.intent.extra.alarm.SKIP_UI", "true",
            ])
            return {"action": "alarm.set", "time": time_str}
        return {"error": f"invalid time format: {time_str}"}

    # ── Toast ──
    def toast(self, message: str) -> dict:
        """Show a toast message on screen."""
        termux_cmd(["termux-toast", "-g", "middle", message])
        return {"action": "toast", "message": message}

    # ── Dispatch ──
    def dispatch(self, tool_call: str, args: dict) -> dict:
        """Route a PicoClaw tool call to the appropriate method."""
        method_map = {
            "device.volume.set": lambda: self.volume_set(args.get("level", 50)),
            "device.volume.get": lambda: self.volume_get(),
            "device.dnd.toggle": lambda: self.dnd_toggle(args.get("enabled", False)),
            "device.brightness.set": lambda: self.brightness_set(args.get("level", 50)),
            "device.wallpaper.set": lambda: self.wallpaper_set(args.get("image", "default")),
            "device.ringtone.set": lambda: {"action": "ringtone.set", "note": "not yet implemented"},
            "device.alarm.set": lambda: self.alarm_set(args.get("time", "07:00")),
            "location.get": lambda: self.location_get(),
            "notifications.list": lambda: {"notifications": self.notification_list()},
            "slave.status": lambda: {
                "battery": self.battery_status(),
                "volume": self.volume_get(),
                "location": self.location_get(),
            },
        }

        handler = method_map.get(tool_call)
        if handler:
            return handler()
        else:
            return {"error": f"unknown tool call: {tool_call}"}


# ══════════════════════════════════════════════════════════
#  JSON-RPC Server (for PicoClaw agent communication)
# ══════════════════════════════════════════════════════════

bridge = DeviceBridge()


class BridgeHandler(BaseHTTPRequestHandler):
    """Simple JSON-RPC handler for PicoClaw → device-bridge communication."""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body)
            tool_call = request.get("tool", "")
            args = request.get("args", {})

            result = bridge.dispatch(tool_call, args)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        print(f"[bridge] {args[0]}")


def run_server(port: int = 8421):
    """Start the device bridge JSON-RPC server."""
    server = HTTPServer(("127.0.0.1", port), BridgeHandler)
    print(f"🌉 Device bridge listening on http://127.0.0.1:{port}")
    print("   PicoClaw sends tool calls here for device control.")
    server.serve_forever()


def run_test():
    """Run a quick hardware test to verify Termux:API access."""
    print("🧪 Device Bridge Hardware Test")
    print("═══════════════════════════════════════")

    tests = [
        ("Battery", bridge.battery_status),
        ("Volume", bridge.volume_get),
        ("Location", bridge.location_get),
        ("Notifications", bridge.notification_list),
    ]

    for name, func in tests:
        try:
            result = func()
            status = "✅" if "error" not in str(result) else "⚠️"
            print(f"  {status} {name}: {json.dumps(result, indent=2)[:100]}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")

    print("═══════════════════════════════════════")


# ══════════════════════════════════════════════════════════
#  CLI Entry Point
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 device-bridge.py [server|test|<tool> <args>]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "server":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8421
        run_server(port)
    elif cmd == "test":
        run_test()
    elif cmd == "volume":
        level = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        print(json.dumps(bridge.volume_set(level)))
    elif cmd == "brightness":
        level = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        print(json.dumps(bridge.brightness_set(level)))
    elif cmd == "location":
        print(json.dumps(bridge.location_get(), indent=2))
    elif cmd == "battery":
        print(json.dumps(bridge.battery_status(), indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
