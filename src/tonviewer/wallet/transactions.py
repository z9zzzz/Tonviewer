"""
Rich transaction / action parsing from TONAPI account events.
Produces the human-friendly format used by Wallet.transactions() and CLI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

TON_DECIMALS = 1_000_000_000

# Heuristic spam / scam comment markers (TONAPI is_scam is not always set)
_SCAM_KEYWORDS = (
    "首存", "包赔", "充值", "亏损送", "娱乐", "担保", "公群", "飞投",
    "福利群", "真人视讯", "电子游戏", "返水", "提佣",
    "casino", "gambling", "betting", "airdrop claim", "free ton",
    "double your", "100% bonus", "first deposit",
    "必安", "世博", "人人娱乐", "btc.cc", "pc28",
    "buying all anon numbers", "buying all anonymous numbers", "anon numbers",
    "промокод", "promo code", "крипто-фиатный кошелек",
)


def _fmt_time(ts: Optional[int]) -> str:
    if not ts:
        return ""
    try:
        # Use local time to match typical wallet UIs
        dt = datetime.fromtimestamp(int(ts))
        return dt.strftime("%d %b %I:%M:%S %p")
    except Exception:
        return str(ts)


def _try_friendly(addr: Any) -> str:
    """Best-effort convert raw/user-friendly address to bounceable UQ form."""
    if not addr:
        return ""
    s = addr if isinstance(addr, str) else str(addr)
    s = s.strip()
    if not s:
        return ""
    try:
        from tonsdk.utils import Address as TonAddress
        a = TonAddress(s)
        return a.to_string(is_user_friendly=True, is_url_safe=True, is_bounceable=False)
    except Exception:
        return s


def _addr_key(addr: Any) -> str:
    """Comparable key: 64-char hex of the address hash."""
    if not addr:
        return ""
    s = addr if isinstance(addr, str) else str(addr)
    s = s.strip()
    if not s:
        return ""
    try:
        from tonsdk.utils import Address as TonAddress
        a = TonAddress(s)
        # hash_part is bytes
        return a.hash_part.hex().lower()
    except Exception:
        # fallback: raw 0:hex
        if ":" in s:
            part = s.split(":", 1)[-1].lower()
            part = "".join(c for c in part if c in "0123456789abcdef")
            return part[-64:] if len(part) >= 64 else part
        return ""


def _same_addr(a: Any, b: Any) -> bool:
    ka, kb = _addr_key(a), _addr_key(b)
    return bool(ka and kb and ka == kb)


def _addr_label(obj: Any) -> str:
    """Show the friendly address followed by the public name when available."""
    if not obj:
        return ""
    if isinstance(obj, str):
        return _try_friendly(obj) or obj
    if isinstance(obj, dict):
        name = obj.get("name")
        addr = obj.get("address") or ""
        friendly = _try_friendly(addr) or str(addr)
        if name and friendly and str(name).strip() not in {friendly, str(addr).strip()}:
            return f"{friendly} ({str(name).strip()})"
        return str(name).strip() if name else friendly
    return str(obj)


def _ton_amount(nano: Any) -> Decimal:
    try:
        return Decimal(int(nano)) / Decimal(TON_DECIMALS)
    except (TypeError, ValueError, InvalidOperation):
        return Decimal(0)


def _price_str(amount_ton: Decimal, rate: Optional[float], incoming: Optional[bool]) -> str:
    sign = "+" if incoming is True else "-" if incoming is False else ""
    amount = format(abs(amount_ton).normalize(), "f")
    if "." in amount:
        amount = amount.rstrip("0").rstrip(".")
    if rate is not None:
        usd = abs(amount_ton) * Decimal(str(rate))
        return f"{sign}{amount} TON ≈ {usd:.5f} $"
    return f"{sign}{amount} TON"


def _status_label(status: Optional[str]) -> str:
    s = (status or "").lower()
    if s in ("ok", "completed", "success"):
        return "Success"
    if s in ("failed", "fail", "error"):
        return "Failed"
    return status or "Unknown"



def _looks_like_scam(
    *,
    event_scam: bool,
    sender: Any = None,
    recipient: Any = None,
    comment: str = "",
    preview: Optional[Dict[str, Any]] = None,
) -> bool:
    """Combine TONAPI flag + account flags + comment heuristics."""
    if event_scam:
        return True
    for obj in (sender, recipient):
        if isinstance(obj, dict) and obj.get("is_scam"):
            return True
    text = (comment or "").lower()
    if preview:
        text += " " + str(preview.get("description") or "").lower()
        text += " " + str(preview.get("name") or "").lower()
    # original case for CJK
    raw = (comment or "") + " " + str((preview or {}).get("description") or "")
    for kw in _SCAM_KEYWORDS:
        if kw.lower() in text or kw in raw:
            return True
    # very long promotional comments are often spam
    if len(comment or "") > 180 and any(ch in (comment or "") for ch in ("http", "t.me", "@", "www")):
        return True
    return False


def parse_event_actions(
    event: Dict[str, Any],
    *,
    wallet_address: str,
    dollar_rate: Optional[float] = None,
    index_start: int = 1,
) -> List[Dict[str, Any]]:
    """Flatten one TONAPI event into one or more display rows."""
    rows: List[Dict[str, Any]] = []
    ts = event.get("timestamp")
    event_scam = bool(event.get("is_scam"))
    event_id = event.get("event_id") or ""
    actions = event.get("actions") or []

    # Event subject account (the wallet we queried)
    event_account = (event.get("account") or {})
    event_account_addr = event_account.get("address") if isinstance(event_account, dict) else None

    for action in actions:
        atype = action.get("type") or ""
        status = _status_label(action.get("status"))
        preview = action.get("simple_preview") or {}

        row: Dict[str, Any] = {
            "Action": preview.get("name") or atype or "Unknown",
            "Time": _fmt_time(ts),
            "From": "",
            "To": "",
            "Price": "",
            "State": status,
            "Comment": "",
            "Hash": event_id,
            "Scam": event_scam,
            "#": index_start + len(rows),
            "_amount_ton": 0.0,
            "_incoming": None,
            "_type": atype,
        }

        # --- TonTransfer ---
        if atype == "TonTransfer" or action.get("TonTransfer"):
            tt = action.get("TonTransfer") or {}
            sender = tt.get("sender") or {}
            recipient = tt.get("recipient") or {}
            amount = _ton_amount(tt.get("amount"))
            comment = tt.get("comment") or ""

            from_s = _addr_label(sender)
            to_s = _addr_label(recipient)

            sender_addr = sender.get("address") if isinstance(sender, dict) else sender
            recip_addr = recipient.get("address") if isinstance(recipient, dict) else recipient

            is_sender = _same_addr(wallet_address, sender_addr) or _same_addr(event_account_addr, sender_addr)
            is_recipient = _same_addr(wallet_address, recip_addr) or _same_addr(event_account_addr, recip_addr)
            if is_sender and is_recipient:
                is_incoming = None
                row["Action"] = "Self-transfer TON"
            elif is_recipient:
                is_incoming = True
                row["Action"] = "Received TON"
            elif is_sender:
                is_incoming = False
                row["Action"] = "Sent TON"
            else:
                is_incoming = None
                row["Action"] = "TON transfer (direction unknown)"
            row["From"] = from_s
            row["To"] = to_s
            row["Price"] = _price_str(amount, dollar_rate, is_incoming)
            row["Comment"] = comment
            row["Scam"] = _looks_like_scam(
                event_scam=event_scam,
                sender=sender,
                recipient=recipient,
                comment=comment,
                preview=preview,
            )
            row["_amount_ton"] = amount
            row["_incoming"] = is_incoming

        # --- JettonTransfer ---
        elif atype == "JettonTransfer" or action.get("JettonTransfer"):
            jt = action.get("JettonTransfer") or {}
            sender = jt.get("sender") or {}
            recipient = jt.get("recipient") or {}
            jetton = jt.get("jetton") or {}
            symbol = jetton.get("symbol") or "JETTON"
            try:
                raw_decimals = jetton.get("decimals")
                decimals = 9 if raw_decimals is None else int(raw_decimals)
                raw_amt = int(jt.get("amount") or 0)
                amount = Decimal(raw_amt) / (Decimal(10) ** decimals)
            except Exception:
                amount = Decimal(0)
            comment = jt.get("comment") or ""

            from_s = _addr_label(sender)
            to_s = _addr_label(recipient)
            sender_addr = sender.get("address") if isinstance(sender, dict) else sender
            recip_addr = recipient.get("address") if isinstance(recipient, dict) else recipient
            is_sender = _same_addr(wallet_address, sender_addr) or _same_addr(event_account_addr, sender_addr)
            is_recipient = _same_addr(wallet_address, recip_addr) or _same_addr(event_account_addr, recip_addr)
            is_incoming = True if is_recipient and not is_sender else False if is_sender and not is_recipient else None
            if is_incoming is True:
                row["Action"] = f"Received {symbol}"
            elif is_incoming is False:
                row["Action"] = f"Sent {symbol}"
            else:
                row["Action"] = f"{symbol} transfer (direction unknown)"
            row["From"] = from_s
            row["To"] = to_s
            amount_text = format(amount.normalize(), "f")
            if "." in amount_text:
                amount_text = amount_text.rstrip("0").rstrip(".")
            sign = "+" if is_incoming is True else "-" if is_incoming is False else ""
            row["Price"] = f"{sign}{amount_text} {symbol}"
            row["Comment"] = comment
            row["Scam"] = _looks_like_scam(
                event_scam=event_scam,
                sender=sender,
                recipient=recipient,
                comment=comment,
                preview=preview,
            )
            row["_amount_ton"] = 0.0
            row["_incoming"] = is_incoming

        # --- NftItemTransfer / NftPurchase ---
        elif atype in ("NftItemTransfer", "NftPurchase") or action.get("NftItemTransfer") or action.get("NftPurchase"):
            key = "NftPurchase" if action.get("NftPurchase") else "NftItemTransfer"
            nt = action.get(key) or {}
            if key == "NftPurchase":
                sender = nt.get("seller") or nt.get("sender") or {}
                recipient = nt.get("buyer") or nt.get("recipient") or {}
            else:
                sender = nt.get("sender") or {}
                recipient = nt.get("recipient") or {}
            row["Action"] = preview.get("name") or ("NFT Purchase" if key == "NftPurchase" else "NFT Transfer")
            row["From"] = _addr_label(sender)
            row["To"] = _addr_label(recipient)
            row["Price"] = preview.get("value") or ""
            row["Comment"] = preview.get("description") or ""
            nft_name = nt.get("nft_name") or nt.get("name")
            nft_obj = nt.get("nft") or nt.get("item") or nt.get("nft_item")
            if isinstance(nft_obj, dict):
                nft_name = nft_name or nft_obj.get("name") or (nft_obj.get("metadata") or {}).get("name")
            if nft_name:
                row["NFT"] = str(nft_name).strip()
            row["_incoming"] = None

        # --- Generic ---
        else:
            accounts = preview.get("accounts") or []
            if len(accounts) >= 2:
                row["From"] = _addr_label(accounts[0])
                row["To"] = _addr_label(accounts[1])
            elif len(accounts) == 1:
                row["From"] = _addr_label(accounts[0])
            row["Price"] = preview.get("value") or preview.get("fiat_value") or ""
            row["Comment"] = preview.get("description") or ""
            row["Action"] = preview.get("name") or atype or "Action"

        rows.append(row)

    if not rows:
        rows.append({
            "Action": "Event",
            "Time": _fmt_time(ts),
            "From": "",
            "To": "",
            "Price": "",
            "State": "Unknown",
            "Comment": "",
            "Hash": event_id,
            "Scam": event_scam,
            "#": index_start,
            "_amount_ton": 0.0,
            "_incoming": None,
            "_type": "",
        })

    return rows


def filter_rows(
    rows: List[Dict[str, Any]],
    *,
    action: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not action:
        return rows
    key = action.strip().lower()
    out = []
    for r in rows:
        a = (r.get("Action") or "").lower()
        t = (r.get("_type") or "").lower()
        incoming = r.get("_incoming")

        if key in ("sent ton", "sent", "outgoing", "out"):
            if "sent ton" in a or (t == "tontransfer" and incoming is False):
                out.append(r)
        elif key in ("received ton", "received", "incoming", "in"):
            if "received ton" in a or (t == "tontransfer" and incoming is True):
                out.append(r)
        elif key in ("ton", "ton transfer"):
            if "ton" in a or t == "tontransfer":
                out.append(r)
        elif key in ("jetton", "token"):
            if "jetton" in t or ("jetton" in a):
                out.append(r)
        elif key in ("nft",):
            if "nft" in t or "nft" in a:
                out.append(r)
        elif key in ("scam",):
            if r.get("Scam"):
                out.append(r)
        else:
            if key in a or key in t:
                out.append(r)
    return out


def build_transactions_payload(
    events: List[Dict[str, Any]],
    *,
    wallet_address: str,
    dollar_rate: Optional[float] = None,
    action: Optional[str] = None,
    limit: Optional[int] = None,
    number: Optional[int] = None,
) -> Dict[str, Any]:
    all_rows: List[Dict[str, Any]] = []
    idx = 1
    for ev in events:
        parsed = parse_event_actions(
            ev,
            wallet_address=wallet_address,
            dollar_rate=dollar_rate,
            index_start=idx,
        )
        all_rows.extend(parsed)
        idx += len(parsed)

    filtered = filter_rows(all_rows, action=action)

    if number is not None:
        # number refers to position in the filtered list (1-based), not original #
        if 1 <= number <= len(filtered):
            filtered = [filtered[number - 1]]
        else:
            filtered = []

    total_before_limit = len(filtered)
    if limit is not None and limit >= 0:
        filtered = filtered[:limit]

    for i, r in enumerate(filtered, start=1):
        r["#"] = i

    spend_ton = Decimal(0)
    received_ton = Decimal(0)
    for r in filtered:
        if r.get("State") == "Failed":
            continue
        amt = Decimal(str(r.get("_amount_ton") or 0))
        if r.get("_incoming") is False:
            spend_ton += amt
        elif r.get("_incoming") is True:
            received_ton += amt

    spend_usd = (spend_ton * Decimal(str(dollar_rate))) if dollar_rate is not None else None
    received_usd = (received_ton * Decimal(str(dollar_rate))) if dollar_rate is not None else None

    clean = []
    for r in filtered:
        clean.append({k: v for k, v in r.items() if not k.startswith("_")})

    return {
        "transactions": clean,
        "total": len(clean),
        "skipped": max(0, total_before_limit - len(clean)),
        "dollar_rate": dollar_rate,
        "total_spend_ton": float(spend_ton),
        "total_spend_usd": float(spend_usd.quantize(Decimal("0.00001"))) if spend_usd is not None else None,
        "total_received_ton": float(received_ton),
        "total_received_usd": float(received_usd.quantize(Decimal("0.00001"))) if received_usd is not None else None,
    }
