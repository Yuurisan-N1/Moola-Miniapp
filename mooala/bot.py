#!/usr/bin/env python3
"""Moala/Moola single-file multi-account bot.

Supported scope: daily check-in, Watch Ads, and Verify Ads only.
Social tasks, wallet operations, mining, and withdrawals are intentionally excluded.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.txt"
BASE_URL = os.getenv("MOOLA_BASE_URL", "https://moola-peach.vercel.app").rstrip("/")
START_PARAM = os.getenv("MOOLA_START_PARAM", "1231751391")
REQUEST_TIMEOUT = int(os.getenv("MOOLA_TIMEOUT", "60"))
VERIFY_WAIT_DEFAULT = 5
WATCH_TOTAL_DEFAULT = 10
VERIFY_TOTAL_DEFAULT = 5

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"


def log(account: int, message: str, color: str = GREEN) -> None:
    print(f"{color}{BOLD}[Akun #{account}] {message}{RESET}")


def sleep_jitter(seconds: float) -> None:
    time.sleep(max(0, seconds + random.uniform(0.3, 1.0)))


def load_accounts() -> list[str]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {DATA_FILE}")
    rows = []
    for raw in DATA_FILE.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        if value.lower().startswith(("init_data=", "init-data=")):
            value = value.split("=", 1)[1].strip()
        rows.append(value)
    if not rows:
        raise ValueError("data.txt kosong. Isi satu Telegram init_data per baris.")
    return rows


class MoolaAPI:
    def __init__(self, init_data: str, account: int):
        self.init_data = init_data
        self.account = account
        self.session = requests.Session()
        self.guest_id = self._load_guest_id()
        self.session.headers.update({
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/?start={START_PARAM}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151.0.0.0 Safari/537.36",
        })

    def _load_guest_id(self) -> str:
        # Keep a stable ID per process/account. The real app uses localStorage key yoda_gid;
        # Moala's server accepts this auxiliary header alongside Telegram init_data.
        return os.getenv("MOOLA_GUEST_ID", f"gmo{self.account}{int(time.time())}{random.randrange(100000, 999999)}")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "x-init-data": self.init_data,
            "x-start-param": START_PARAM,
            "x-guest-id": self.guest_id,
        }
        response = self.session.request(
            method,
            BASE_URL + path,
            headers=headers,
            json=body,
            timeout=REQUEST_TIMEOUT,
        )
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}
        if response.status_code >= 400 or data.get("ok") is False:
            raise RuntimeError(f"HTTP {response.status_code}: {json.dumps(data, ensure_ascii=False)}")
        return data

    def state(self) -> dict[str, Any]:
        # The live Moola deployment exposes the authenticated user snapshot at POST /api/me.
        return self.request("POST", "/api/me", {})

    def checkin(self) -> dict[str, Any]:
        return self.request("POST", "/api/tasks/checkin", {})

    def ad(self, ad_type: str) -> dict[str, Any]:
        return self.request("POST", "/api/tasks/ad", {"type": ad_type})


def extract_state(data: dict[str, Any]) -> dict[str, Any]:
    # The live frontend receives {user: {...ads, checkin, balance...}} from POST /api/me.
    user = data.get("user")
    if isinstance(user, dict) and ("ads" in user or "checkin" in user):
        return user
    # Keep compatibility with wrappers used by earlier deployments.
    for key in ("result", "data", "stats"):
        wrapped = data.get(key)
        if isinstance(wrapped, dict):
            if isinstance(wrapped.get("user"), dict) and ("ads" in wrapped["user"] or "checkin" in wrapped["user"]):
                return wrapped["user"]
            if "ads" in wrapped or "checkin" in wrapped:
                return wrapped
    return data


def show_status(api: MoolaAPI, account: int) -> bool:
    state = extract_state(api.state())
    ads = state.get("ads", {}) or {}
    checkin = state.get("checkin", {}) or {}
    user = state.get("user", {}) or {}
    balance = user.get("balance", state.get("balance", "?"))
    log(account, f"Balance: {balance} MOOLA | check-in canClaim={checkin.get('canClaim')}")
    log(account, f"Watch Ads: {ads.get('watched', ads.get('watchToday', 0))}/{ads.get('watchTotal', WATCH_TOTAL_DEFAULT)}")
    log(account, f"Verify Ads: {ads.get('verified', 0)}/{ads.get('verifyTotal', VERIFY_TOTAL_DEFAULT)}")
    return True


def do_checkin(api: MoolaAPI, account: int) -> bool:
    state = extract_state(api.state())
    checkin = state.get("checkin", {}) or {}
    if not checkin.get("canClaim", False):
        log(account, "Daily check-in belum tersedia atau sudah di-claim hari ini.", YELLOW)
        return True
    result = api.checkin()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    log(account, "Daily check-in berhasil dikirim ke /api/tasks/checkin.", GREEN)
    return True


def do_ads(api: MoolaAPI, account: int, ad_type: str, count: int | None = None) -> bool:
    state = extract_state(api.state())
    ads = state.get("ads", {}) or {}
    if ad_type == "watch":
        done = int(ads.get("watched", ads.get("watchToday", 0)) or 0)
        total = int(ads.get("watchTotal", WATCH_TOTAL_DEFAULT) or WATCH_TOTAL_DEFAULT)
        reward = float(ads.get("watchReward", 1.25) or 1.25)
        # Live frontend waits 1600 ms before Watch claim.
        wait_seconds = 1.6
    else:
        done = int(ads.get("verified", 0) or 0)
        total = int(ads.get("verifyTotal", VERIFY_TOTAL_DEFAULT) or VERIFY_TOTAL_DEFAULT)
        reward = float(ads.get("verifyReward", 2.5) or 2.5)
        wait_seconds = int(ads.get("verifyWaitSeconds", VERIFY_WAIT_DEFAULT) or VERIFY_WAIT_DEFAULT)
    remaining = max(0, total - done)
    requested = remaining if count is None else min(max(0, count), remaining)
    if requested == 0:
        log(account, f"{ad_type} sudah selesai: {done}/{total}.", CYAN)
        return True
    log(account, f"{ad_type}: {done}/{total}; akan proses {requested} task, reward {reward:.2f} MOOLA.")
    completed = 0
    for index in range(requested):
        if ad_type == "verify":
            print(f"{YELLOW}Buka dan selesaikan Verify Ads secara manual, lalu tunggu {wait_seconds} detik.{RESET}")
        else:
            print(f"{YELLOW}Selesaikan Watch Ads secara manual di aplikasi.{RESET}")
        if wait_seconds:
            if ad_type == "verify":
                log(account, f"Menunggu tepat {wait_seconds:g} detik sesuai verifyWaitSeconds server...")
            else:
                log(account, "Menunggu tepat 1.6 detik sesuai handler Watch Ads aplikasi...")
            time.sleep(wait_seconds)
        result = api.ad(ad_type)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        completed += 1
        log(account, f"Claim {ad_type} #{done + completed} berhasil dikirim.", GREEN)
        sleep_jitter(1)
    # Re-read server state so the counter, not the local loop, is authoritative.
    final_state = extract_state(api.state())
    final_ads = final_state.get("ads", {}) or {}
    log(account, f"Konfirmasi server: watched={final_ads.get('watched', final_ads.get('watchToday', 0))}, verified={final_ads.get('verified', 0)}", CYAN)
    return True


def run_account(init_data: str, account: int, mode: str, ad_type: str, count: int | None) -> bool:
    api = MoolaAPI(init_data, account)
    if mode == "status":
        return show_status(api, account)
    if mode == "checkin":
        return do_checkin(api, account)
    if mode == "ads":
        return do_ads(api, account, ad_type, count)
    if mode == "all":
        # Per-account order is intentional: check-in -> all Watch Ads -> all Verify Ads.
        show_status(api, account)
        do_checkin(api, account)
        watch_ok = do_ads(api, account, "watch", None)
        verify_ok = do_ads(api, account, "verify", None)
        return watch_ok and verify_ok
    raise ValueError(f"Mode tidak dikenal: {mode}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Moala/Moola single-file bot")
    parser.add_argument("--mode", choices=["status", "checkin", "ads", "all"], default="status")
    parser.add_argument("--ad-type", choices=["watch", "verify"], default="verify")
    parser.add_argument("--count", type=int, default=None, help="jumlah ads; default: semua sisa dari state server")
    parser.add_argument("--once", action="store_true", help="jalankan satu siklus lalu berhenti")
    parser.add_argument("--interval", type=int, default=86400, help="interval antar siklus dalam detik")
    args = parser.parse_args()
    print(f"{CYAN}{BOLD}\n========== MOOLA TASK BOT =========={RESET}")
    print(f"{WHITE}Base URL: {BASE_URL} | Mode: {args.mode} | Data: {DATA_FILE}{RESET}\n")
    try:
        accounts = load_accounts()
    except (FileNotFoundError, ValueError) as exc:
        print(f"{RED}Error: {exc}{RESET}")
        return 1
    cycle = 1
    while True:
        print(f"{MAGENTA}{BOLD}=== SIKLUS {cycle} ==={RESET}")
        success = 0
        for account, init_data in enumerate(accounts, 1):
            try:
                if run_account(init_data, account, args.mode, args.ad_type, args.count):
                    success += 1
            except Exception as exc:
                log(account, str(exc), RED)
            if account < len(accounts):
                time.sleep(1)
        log(0, f"Selesai: {success}/{len(accounts)} akun.", GREEN if success == len(accounts) else YELLOW)
        if args.once:
            return 0 if success == len(accounts) else 1
        next_run = max(60, args.interval)
        log(0, f"Siklus berikutnya sekitar {datetime.now().timestamp() + next_run:.0f} epoch.", CYAN)
        time.sleep(next_run)
        cycle += 1


if __name__ == "__main__":
    raise SystemExit(main())
