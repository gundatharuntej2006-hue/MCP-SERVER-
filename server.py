# server.py
import os
import logging
from fastmcp import FastMCP

# Try to import Aevo SDK client from the repo
try:
    from client import AevoClient
except Exception as e:
    AevoClient = None

# Read environment variables
SIGNING_KEY = os.getenv("AEVO_SIGNING_KEY")
WALLET_ADDRESS = os.getenv("AEVO_WALLET_ADDRESS")
API_KEY = os.getenv("AEVO_API_KEY")
API_SECRET = os.getenv("AEVO_API_SECRET")
ENV = os.getenv("AEVO_ENV", "testnet")

if not (API_KEY and API_SECRET and WALLET_ADDRESS):
    logging.warning("One or more AEVO env vars missing. Set AEVO_API_KEY, AEVO_API_SECRET, AEVO_WALLET_ADDRESS, AEVO_SIGNING_KEY if needed.")

# Initialize AevoClient if possible
aevo_client = None
if AevoClient is not None:
    try:
        aevo_client = AevoClient(
            signing_key=SIGNING_KEY or "",
            wallet_address=WALLET_ADDRESS or "",
            api_key=API_KEY or "",
            api_secret=API_SECRET or "",
            env=ENV,
        )
    except Exception as e:
        logging.warning(f"Could not initialize AevoClient: {e}")
        aevo_client = None

mcp = FastMCP("Aevo Testnet Tools")

@mcp.tool()
def transfer_coins(to_address: str, amount: float, asset: str = "USDC") -> dict:
    if not (API_KEY and API_SECRET and WALLET_ADDRESS):
        raise Exception("Server not configured: missing AEVO_API_KEY / AEVO_API_SECRET / AEVO_WALLET_ADDRESS")

    if aevo_client is not None:
        try:
            if hasattr(aevo_client, "transfer"):
                resp = aevo_client.transfer(to_address=to_address, amount=amount, asset=asset)
                return {"status": "ok", "via": "sdk.transfer", "response": resp}
            elif hasattr(aevo_client, "withdraw"):
                resp = aevo_client.withdraw(to_address=to_address, amount=amount, asset=asset)
                return {"status": "ok", "via": "sdk.withdraw", "response": resp}
            elif hasattr(aevo_client, "request"):
                resp = aevo_client.request("POST", "/transfer", json={"to": to_address, "amount": amount, "asset": asset})
                return {"status": "ok", "via": "sdk.request", "response": resp}
        except Exception as e:
            raise Exception(f"SDK transfer failed: {e}")

    # Fallback REST call
    import requests
    base = "https://api-testnet.aevo.xyz" if ENV == "testnet" else "https://api.aevo.xyz"
    url = f"{base}/transfer"
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY,
        "X-API-SECRET": API_SECRET,
    }
    try:
        r = requests.post(url, headers=headers, json={"to": to_address, "amount": f"{amount:.6f}", "asset": asset}, timeout=20)
        r.raise_for_status()
        return {"status": "ok", "via": "rest", "response": r.json()}
    except Exception as e:
        raise Exception(f"REST transfer failed: {e}")

@mcp.tool()
def cancel_order(order_id: str) -> dict:
    if not (API_KEY and API_SECRET):
        raise Exception("Server not configured: missing AEVO_API_KEY / AEVO_API_SECRET")

    if aevo_client is not None:
        try:
            if hasattr(aevo_client, "cancel_order"):
                resp = aevo_client.cancel_order(order_id)
                return {"status": "ok", "via": "sdk.cancel_order", "response": resp}
            elif hasattr(aevo_client, "request"):
                resp = aevo_client.request("DELETE", f"/orders/{order_id}")
                return {"status": "ok", "via": "sdk.request", "response": resp}
        except Exception as e:
            raise Exception(f"SDK cancel_order failed: {e}")

    # Fallback REST call
    import requests
    base = "https://api-testnet.aevo.xyz" if ENV == "testnet" else "https://api.aevo.xyz"
    url = f"{base}/orders/{order_id}"
    headers = {"X-API-KEY": API_KEY, "X-API-SECRET": API_SECRET}
    try:
        r = requests.delete(url, headers=headers, timeout=10)
        r.raise_for_status()
        return {"status": "ok", "via": "rest", "response": r.json()}
    except Exception as e:
        raise Exception(f"REST cancel failed: {e}")

if name == "main":
    # Start MCP server (STDIO transport by default)
    mcp.run()