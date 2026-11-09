# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.1.x   | ✅ Yes    |
| < 2.0   | ❌ No     |

## Reporting a Vulnerability

If you discover a security vulnerability in ReClaw, please report it responsibly:

1. **Do NOT** open a public issue
2. Email the team at **beyond.ud.help@gmail.com** with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
3. We will acknowledge receipt within 48 hours
4. A fix will be prioritized based on severity

## Security Considerations

ReClaw is designed with privacy-first principles:

- **All AI inference runs on-device** — no data is sent to external servers
- **Telegram Bot API** — uses HTTPS encryption for master-slave communication
- **No data collection** — the agent does not store or transmit user data externally
- **Local storage only** — profiles, events, and preferences are stored on-device

## Best Practices for Users

- Keep your Telegram Bot Token private (never commit it to code)
- Use environment variables for sensitive credentials (`RECLAW_BOT_TOKEN`, `RECLAW_CHAT_ID`)
- Regularly update Termux and Termux:API packages
- Do not expose your bot token in public repositories
