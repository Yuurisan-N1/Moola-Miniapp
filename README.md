<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=Moola%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Daily%20Check-in%20%7C%20Mining%20%7C%20Social%20Tasks%20%7C%20Ads%20%7C%20NFT%20Upgrade&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Auto+Daily+Check-in+%7C+Claim+MOOLA+Reward;Auto+Mining+%7C+Claim+%26+Restart+Session;Auto+Social+Tasks+%7C+Claim+Pending+Ones;Auto+Watch+%26+Verify+Ads+Until+Daily+Cap;Auto+NFT+Upgrade+%7C+Best+Affordable+Pick"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-Moola%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>Moola Bot</b> is a full automation bot for the Moola Telegram Miniapp.<br/>
  It handles the complete daily cycle: claiming the daily check-in, managing mining sessions by claiming and restarting, completing all pending social tasks, claiming all remaining watch and verify ad slots, and optionally upgrading the NFT to the best affordable option, all running automatically across multiple accounts with proxy support and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Credits](#credits)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.10+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Moola-Miniapp.git
cd Moola-Miniapp
```

**Install dependencies:**

```bash
pip install requests
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456
```

Lines starting with `#` are ignored. Lines prefixed with `init_data=` or `init-data=` are automatically stripped to extract the value.

> `initData` can be obtained from the browser DevTools when opening Moola on Telegram Web.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. `nft.enabled` toggles automatic NFT upgrading. Set it to `true` to enable the bot to purchase the best affordable NFT after each cycle. If `config.json` is missing, the bot exits with an error.

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Daily Check-in
The bot checks whether the daily check-in is available for each account. If so, it claims the reward and logs the streak day and MOOLA earned. If already claimed today, the current day is logged and it is skipped.

### Auto Mining
If a mining session is active, the bot claims the pending MOOLA and immediately restarts a new session. If no session is running, it starts one. If the first claim attempt fails, it retries after ad completion. A second claim and restart attempt is made at the end of the cycle for accounts that had no active session initially.

### Auto Social Tasks
The bot compares the full social task list against the account's already-completed tasks. Each pending task is claimed individually. Failed claims are skipped and the next task is attempted. All 11 task types are supported including follow, subscribe, retweet, react, like, comment, vote, boost, and join actions.

### Auto Ads
The bot reads the current watch and verify ad counters and daily caps from the server. It then claims all remaining watch ad slots and all remaining verify ad slots in sequence. Progress is logged per slot. Slots already at the cap are skipped.

### Auto NFT Upgrade
If `nft.enabled` is set to `true`, the bot fetches the latest balance and collection after the main cycle, finds all unlockable NFTs the account can afford that are a higher tier than the current active NFT, picks the most expensive one, and purchases it. The upgrade is logged with old NFT name, new NFT name, cost, and remaining balance. If no upgrade is available or affordable, it is skipped.

### Session Expiry Handling
If a session expires mid-cycle, the bot catches the error, logs it, and skips the account for that cycle without crashing.

### Multi Account
All accounts in `data.txt` are processed sequentially within every cycle. Balance, mining status, check-in availability, ad progress, active NFT, and owned NFTs are all logged at the start of each account.

### Proxy Support
Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown
After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
Moola-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration and NFT toggle
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
└── utils/
    └── banner.py   # Banner display on startup
```

---

## Credits

This project is a fork of the original work by **konter0nline**. Big thanks for the base implementation.

<p>
  <a href="https://github.com/konter0nline">
    <img src="https://github.com/konter0nline.png" width="60" style="border-radius:50%"/>
  </a>
  <br/>
  <a href="https://github.com/konter0nline"><b>konter0nline</b></a>
  <br/>
  <a href="https://github.com/konter0nline/moola">github.com/konter0nline/moola</a>
</p>

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>