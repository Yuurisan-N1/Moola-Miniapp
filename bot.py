#!/usr/bin/env python3
from __future__ import annotations

import json
import signal
import sys
import time
from pathlib import Path
from typing import Any

import requests

from utils.banner import show_banner

MY_PROJECT = "Moola Miniapp"

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.txt"
PROXY_FILE = BASE_DIR / "proxy.txt"
CONFIG_FILE = BASE_DIR / "config.json"
BASE_URL = "https://moola-peach.vercel.app"
START_PARAM = "7334566449"

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

SOCIAL_TASKS = [
    "follow_x",
    "subscribe_youtube",
    "retweet",
    "react_post",
    "x_like",
    "x_retweet2",
    "x_comment",
    "x_vote",
    "boost_channel",
    "join_channel",
    "join_partner",
]


def log_green(msg: str) -> None:
    print(f"{GREEN}{BOLD}{msg}{RESET}")


def log_yellow(msg: str) -> None:
    print(f"{YELLOW}{BOLD}{msg}{RESET}")


def log_red(msg: str) -> None:
    print(f"{RED}{BOLD}{msg}{RESET}")


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        log_red("config.json not found, please create it before running")
        sys.exit(1)
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        log_red("config.json is invalid, please check the file")
        sys.exit(1)


def load_accounts() -> list[str]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"data.txt not found at {DATA_FILE}")
    rows = []
    for raw in DATA_FILE.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        if value.lower().startswith(("init_data=", "init-data=")):
            value = value.split("=", 1)[1].strip()
        rows.append(value)
    if not rows:
        raise ValueError("data.txt is empty. Add one Telegram init_data per line.")
    return rows


def load_proxies() -> list[str]:
    if not PROXY_FILE.exists():
        return []
    lines = []
    for raw in PROXY_FILE.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if value:
            lines.append(value)
    return lines


def get_proxy_for_account(proxies: list[str], index: int) -> str | None:
    if not proxies:
        return None
    return proxies[index % len(proxies)]


def mask_proxy_ip(proxy: str) -> str:
    try:
        host_part = proxy.split("@")[-1].split(":")[0]
        segments = host_part.split(".")
        if len(segments) == 4:
            return f"{segments[0]}*****{segments[3]}"
    except Exception:
        pass
    return "unknown"


def get_proxy_port(proxy: str) -> str:
    try:
        after_at = proxy.split("@")[-1]
        parts = after_at.split(":")
        if len(parts) >= 2:
            return parts[-1]
    except Exception:
        pass
    return "0"


def build_proxy_dict(proxy: str) -> dict[str, str]:
    return {"http": proxy, "https": proxy}


def countdown(seconds: int) -> None:
    for remaining in range(seconds, 0, -1):
        h = remaining // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60
        print(f"\r{YELLOW}{BOLD}Next cycle in {h:02d}:{m:02d}:{s:02d}{RESET}", end="", flush=True)
        time.sleep(1)
    print()


class ExpiredSessionError(Exception):
    pass


class MoolaAPI:
    def __init__(self, init_data: str, proxy: str | None):
        self.init_data = init_data
        self.session = requests.Session()
        if proxy:
            self.session.proxies.update(build_proxy_dict(proxy))
        self.session.headers.update({
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/?start={START_PARAM}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151.0.0.0 Safari/537.36",
            "x-init-data": init_data,
            "x-start-param": START_PARAM,
        })

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.request(
            method,
            BASE_URL + path,
            json=body if body is not None else {},
            timeout=60,
        )
        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(f"Invalid JSON response with status {response.status_code}")
        if response.status_code == 401 or (isinstance(data, dict) and "expired" in str(data).lower()):
            raise ExpiredSessionError("Session expired or unauthorized")
        if response.status_code >= 400:
            raise RuntimeError(f"Request failed with status {response.status_code}")
        return data

    def onboard(self) -> dict[str, Any]:
        return self.request("POST", "/api/onboard", {})

    def checkin(self) -> dict[str, Any]:
        return self.request("POST", "/api/tasks/checkin", {})

    def claim_social(self, task_id: str) -> dict[str, Any]:
        return self.request("POST", "/api/tasks/social", {"taskId": task_id})

    def claim_ad(self, ad_type: str) -> dict[str, Any]:
        return self.request("POST", "/api/tasks/ad", {"type": ad_type})

    def mine_start(self) -> dict[str, Any]:
        return self.request("POST", "/api/mine/start", {})

    def mine_claim(self) -> dict[str, Any]:
        return self.request("POST", "/api/mine/claim", {})

    def mint_nft(self, nft_id: str) -> dict[str, Any]:
        return self.request("POST", "/api/nft/unlock", {"id": nft_id})


def extract_user(data: dict[str, Any]) -> dict[str, Any]:
    user = data.get("user")
    if isinstance(user, dict):
        return user
    return data


def handle_nft(api: MoolaAPI, account: int, nft_enabled: bool, collection: list[dict], balance: float) -> None:
    active_nft = next((c for c in collection if c.get("active")), None)
    active_nft_name = active_nft.get("name", "None") if active_nft else "None"
    active_nft_cost = float(active_nft.get("costMoola") or 0) if active_nft else 0.0

    if not nft_enabled:
        log_yellow(f"Account {account} NFT purchase is disabled {active_nft_name} as active NFT")
        return

    candidates = [
        c for c in collection
        if not c.get("owned")
        and c.get("unlockable")
        and c.get("costMoola") is not None
        and float(c.get("costMoola", 0)) <= balance
        and float(c.get("costMoola", 0)) > active_nft_cost
    ]

    if not candidates:
        log_yellow(f"Account {account} no NFT upgrade available {active_nft_name} as active NFT")
        return

    target = max(candidates, key=lambda c: float(c.get("costMoola", 0)))
    target_id = target.get("id", "")
    target_name = target.get("name", target_id)
    target_cost = float(target.get("costMoola", 0))

    log_yellow(f"Account {account} upgrading NFT from {active_nft_name} to {target_name} for {target_cost} MOOLA")

    try:
        mint_result = api.mint_nft(target_id)
        mint_user = extract_user(mint_result)
        new_balance = mint_user.get("balance", balance)
        log_green(f"Account {account} successfully minted {target_name} for {target_cost} MOOLA, remaining balance {new_balance} MOOLA")
    except Exception:
        log_red(f"Account {account} failed to mint {target_name}, skipping NFT purchase")


def run_account(init_data: str, account: int, proxy: str | None, nft_enabled: bool) -> None:
    api = MoolaAPI(init_data, proxy)

    if proxy:
        masked_ip = mask_proxy_ip(proxy)
        port = get_proxy_port(proxy)
        log_yellow(f"Account {account} using proxy http://user:pass@{masked_ip}:{port}")

    raw = api.onboard()
    user = extract_user(raw)

    username = user.get("username") or user.get("firstName", "Unknown")
    balance = float(user.get("balance") or 0)
    mining = user.get("mining") or {}
    checkin_info = user.get("checkin") or {}
    ads_info = user.get("ads") or {}
    collection = user.get("collection") or []
    social_done = user.get("socialDone") or []

    mining_active = mining.get("active", False)
    mining_pending = mining.get("pending", 0)
    can_checkin = checkin_info.get("canClaim", False)
    checkin_day = checkin_info.get("day", 0)

    watched = ads_info.get("watched")
    watch_total = ads_info.get("watchTotal")
    watch_reward = ads_info.get("watchReward")
    verified = ads_info.get("verified")
    verify_total = ads_info.get("verifyTotal")
    verify_reward = ads_info.get("verifyReward")

    owned_nfts = [c for c in collection if c.get("owned")]
    active_nft = next((c for c in collection if c.get("active")), None)
    active_nft_name = active_nft.get("name", "None") if active_nft else "None"

    log_green(f"Account {account} logged in as {username}")
    log_green(f"Account {account} balance is {balance} MOOLA")
    log_green(f"Account {account} mining status is {'active' if mining_active else 'inactive'}, pending {mining_pending} MOOLA")
    log_green(f"Account {account} check-in available is {can_checkin} on day {checkin_day}")
    log_green(f"Account {account} watch ads progress {watched} of {watch_total} at {watch_reward} MOOLA each")
    log_green(f"Account {account} verify ads progress {verified} of {verify_total} at {verify_reward} MOOLA each")
    log_green(f"Account {account} active NFT is {active_nft_name}")
    log_green(f"Account {account} owned NFTs are {', '.join(c.get('name', c.get('id', '')) for c in owned_nfts)}")

    if can_checkin:
        try:
            checkin_result = api.checkin()
            checkin_reward = checkin_result.get("reward", 0)
            checkin_day_result = checkin_result.get("day", checkin_day)
            log_green(f"Account {account} daily check-in claimed successfully on day {checkin_day_result} for {checkin_reward} MOOLA")
        except Exception:
            log_yellow(f"Account {account} daily check-in failed, skipping")
    else:
        log_yellow(f"Account {account} daily check-in already claimed today on day {checkin_day}")

    if mining_active:
        try:
            claim_result = api.mine_claim()
            claimed_amount = claim_result.get("claimed", mining_pending)
            log_green(f"Account {account} mining session claimed successfully, received {claimed_amount} MOOLA")
        except Exception:
            log_yellow(f"Account {account} mining claim failed, skipping")
        try:
            api.mine_start()
            log_green(f"Account {account} mining session restarted successfully")
        except Exception:
            log_yellow(f"Account {account} mining start failed, skipping")
    else:
        try:
            api.mine_start()
            log_green(f"Account {account} mining session started successfully")
        except Exception:
            log_yellow(f"Account {account} mining start failed, skipping")

    pending_tasks = [t for t in SOCIAL_TASKS if t not in social_done]
    if pending_tasks:
        log_yellow(f"Account {account} has {len(pending_tasks)} pending social tasks to claim")
        for task_id in pending_tasks:
            try:
                api.claim_social(task_id)
                log_green(f"Account {account} social task {task_id} claimed successfully")
            except Exception:
                log_yellow(f"Account {account} social task {task_id} could not be claimed, skipping")
    else:
        log_green(f"Account {account} all social tasks already completed")

    watch_remaining = max(0, watch_total - watched)
    if watch_remaining > 0:
        log_yellow(f"Account {account} claiming {watch_remaining} watch ads")
        for i in range(watch_remaining):
            try:
                api.claim_ad("watch")
                log_green(f"Account {account} watch ad {watched + i + 1} of {watch_total} claimed successfully")
            except Exception:
                log_yellow(f"Account {account} watch ad claim failed, skipping")
    else:
        log_green(f"Account {account} all watch ads already completed")

    verify_remaining = max(0, verify_total - verified)
    if verify_remaining > 0:
        log_yellow(f"Account {account} claiming {verify_remaining} verify ads")
        for i in range(verify_remaining):
            try:
                api.claim_ad("verify")
                log_green(f"Account {account} verify ad {verified + i + 1} of {verify_total} claimed successfully")
            except Exception:
                log_yellow(f"Account {account} verify ad claim failed, skipping")
    else:
        log_green(f"Account {account} all verify ads already completed")

    if not mining_active:
        try:
            claim_result = api.mine_claim()
            claimed_amount = claim_result.get("claimed", 0)
            log_green(f"Account {account} mining session claimed successfully after ads, received {claimed_amount} MOOLA")
        except Exception:
            log_yellow(f"Account {account} mining claim after ads failed, skipping")
        try:
            api.mine_start()
            log_green(f"Account {account} mining session restarted successfully after ads")
        except Exception:
            log_yellow(f"Account {account} mining restart after ads failed, skipping")

    fresh_raw = api.onboard()
    fresh_user = extract_user(fresh_raw)
    fresh_balance = float(fresh_user.get("balance") or balance)
    fresh_collection = fresh_user.get("collection") or collection

    handle_nft(api, account, nft_enabled, fresh_collection, fresh_balance)


def main() -> None:
    def handle_sigint(sig: int, frame: Any) -> None:
        print()
        log_red("Script stopped by user")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    config = load_config()
    sleep_seconds = int(config.get("settings", {}).get("sleep_seconds", 86400))
    nft_enabled = bool(config.get("nft", {}).get("enabled", False))

    try:
        accounts = load_accounts()
    except (FileNotFoundError, ValueError) as exc:
        log_red(str(exc))
        sys.exit(1)

    proxies = load_proxies()
    cycle = 1

    while True:
        show_banner(MY_PROJECT)
        log_green(f"Starting cycle {cycle} with {len(accounts)} accounts")

        for idx, init_data in enumerate(accounts):
            if idx > 0:
                print()
            account = idx + 1
            proxy = get_proxy_for_account(proxies, idx)
            try:
                run_account(init_data, account, proxy, nft_enabled)
            except ExpiredSessionError:
                log_red(f"Account {account} session is expired, skipping")
            except Exception:
                log_red(f"Account {account} encountered an unexpected error, skipping")

        print()
        log_green("All accounts processed")
        countdown(sleep_seconds)
        cycle += 1


if __name__ == "__main__":
    main()