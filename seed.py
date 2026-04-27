#!/usr/bin/env python3
"""
seed.py — Populate the Sakha backend with sample data.

Usage:
    # From the project root (backend must be running on :8080)
    python seed.py

    # Custom backend URL:
    BASE_URL=http://localhost:9000 python seed.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")
API      = f"{BASE_URL}/api/v1"

ADMIN_EMAIL    = "admin@sakha.dev"
ADMIN_PASSWORD = "sakha2026!"
ADMIN_NAME     = "Sakha Admin"

# ── Console colours ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
RESET  = "\033[0m";  BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✓{RESET}  {msg}")
def warn(msg): print(f"  {YELLOW}⚠{RESET}  {msg}")
def fail(msg): print(f"  {RED}✗{RESET}  {msg}")
def h1(msg):   print(f"\n{BOLD}{msg}{RESET}")


# ── HTTP ───────────────────────────────────────────────────────────────────────
def _req(method, path, body=None, token=None, is_api=True):
    url  = f"{API if is_api else BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:    detail = json.loads(raw)
        except: detail = raw.decode()
        return e.code, detail

def GET(path, token=None, is_api=True): return _req("GET",   path, token=token, is_api=is_api)
def POST(path, body, token=None):       return _req("POST",  path, body, token)
def PATCH(path, body, token=None):      return _req("PATCH", path, body, token)


def _multipart_post(path, fields, token):
    """Send a multipart/form-data POST (used for brand creation)."""
    boundary = "----SakhaSeedBoundary7MA4YW"
    parts = []
    for k, v in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}'
        )
    body = ("\r\n".join(parts) + f"\r\n--{boundary}--\r\n").encode()
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": f"Bearer {token}",
    }
    req = urllib.request.Request(f"{API}{path}", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:    detail = json.loads(raw)
        except: detail = raw.decode()
        return e.code, detail


# ── 0. Health ──────────────────────────────────────────────────────────────────
def check_health():
    h1("0 / Health check")
    code, resp = GET("/health", is_api=False)
    if code == 200:
        ok(f"Backend is up → {resp}")
    else:
        fail(f"Backend not reachable at {BASE_URL}  ({code})")
        sys.exit(1)


# ── 1. Auth ────────────────────────────────────────────────────────────────────
def get_token():
    h1("1 / Auth")

    code, resp = POST("/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if code == 200:
        ok(f"Logged in as {ADMIN_EMAIL}")
        return resp["access_token"]

    warn("No user found — registering…")
    code, resp = POST("/auth/register", {
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
        "name": ADMIN_NAME,   "role": "admin",
    })
    if code == 201:
        ok(f"Registered + logged in as {ADMIN_EMAIL}")
        return resp["access_token"]

    fail(f"Auth failed ({code}): {resp}")
    sys.exit(1)


# ── 2. Categories ──────────────────────────────────────────────────────────────
CATEGORIES = [
    {"name": "Electronics",    "slug": "electronics",   "description": "Gadgets, devices and tech accessories"},
    {"name": "Audio",          "slug": "audio",         "description": "Headphones, speakers and audio gear"},
    {"name": "Wearables",      "slug": "wearables",     "description": "Smartwatches, fitness bands and AR glasses"},
    {"name": "Home & Office",  "slug": "home-office",   "description": "Desks, chairs, lighting and smart home"},
    {"name": "Cameras",        "slug": "cameras",       "description": "Digital cameras, lenses and accessories"},
]

def seed_categories(token):
    h1("2 / Categories")
    ids = {}
    _, existing = GET("/categories", token)
    existing_slugs = {c["slug"]: c["id"] for c in (existing or [])}

    for c in CATEGORIES:
        if c["slug"] in existing_slugs:
            warn(f"Already exists: {c['name']} → {existing_slugs[c['slug']]}")
            ids[c["name"]] = existing_slugs[c["slug"]]
            continue
        code, resp = POST("/categories", c, token)
        if code == 201:
            ok(f"Created: {c['name']} → {resp['id']}")
            ids[c["name"]] = resp["id"]
        else:
            fail(f"{c['name']}: {code} {resp}")
    return ids


# ── 3. Brands ──────────────────────────────────────────────────────────────────
BRANDS_RAW = [
    {"name": "SoundCore",  "slug": "soundcore",  "description": "Premium audio brand",       "website": "https://soundcore.example.com"},
    {"name": "TechNova",   "slug": "technova",   "description": "Cutting-edge electronics",  "website": "https://technova.example.com"},
    {"name": "LumaLens",   "slug": "lumalens",   "description": "Optical excellence",        "website": "https://lumalens.example.com"},
    {"name": "OrbitWear",  "slug": "orbitwear",  "description": "Smart wearables",           "website": "https://orbitwear.example.com"},
    {"name": "DeskaForm",  "slug": "deskaform",  "description": "Ergonomic workspace",       "website": "https://deskaform.example.com"},
]

def seed_brands(token):
    h1("3 / Brands")
    ids = {}
    _, existing = GET("/brands/", token)
    existing_slugs = {b.get("slug"): b["id"] for b in (existing or [])}

    for b in BRANDS_RAW:
        if b["slug"] in existing_slugs:
            warn(f"Already exists: {b['name']} → {existing_slugs[b['slug']]}")
            ids[b["name"]] = existing_slugs[b["slug"]]
            continue
        code, resp = _multipart_post("/brands/", b, token)
        if code == 201:
            ok(f"Created: {b['name']} → {resp['id']}")
            ids[b["name"]] = resp["id"]
        else:
            fail(f"{b['name']}: {code} {resp}")
    return ids


# ── 4. Products ────────────────────────────────────────────────────────────────
def product_catalog(cat, brand):
    """Return list of product dicts using resolved category/brand IDs."""
    e = cat.get("Electronics");  a = cat.get("Audio")
    w = cat.get("Wearables");    h = cat.get("Home & Office")
    c = cat.get("Cameras")

    sc = brand.get("SoundCore"); tn = brand.get("TechNova")
    ll = brand.get("LumaLens");  ow = brand.get("OrbitWear")
    df = brand.get("DeskaForm")

    return [
        # ── Audio ──────────────────────────────────────────────────────────
        {"name": "SoundCore ANC Pro Headphones",
         "sku": "SC-ANC-001", "price": 349.99, "stock": 87,
         "description": "Industry-leading active noise cancellation, 30-hour battery, premium leather ear cushions and hi-res audio certification.",
         "category_id": a, "brand_id": sc, "status": "active",
         "tags": ["audio", "headphones", "anc", "wireless", "hi-res"]},

        {"name": "SoundCore Beam 360 Speaker",
         "sku": "SC-BM-002", "price": 129.00, "stock": 150,
         "description": "360° surround sound portable speaker with IPX7 waterproofing, 20-hour playback and USB-C fast charge.",
         "category_id": a, "brand_id": sc, "status": "active",
         "tags": ["audio", "speaker", "portable", "waterproof"]},

        {"name": "SoundCore Studio Monitor Pair",
         "sku": "SC-STD-003", "price": 599.00, "stock": 22,
         "description": "Professional studio monitor pair with flat-response drivers, balanced XLR/TRS inputs and room EQ presets.",
         "category_id": a, "brand_id": sc, "status": "active",
         "tags": ["audio", "studio", "monitors", "pro"]},

        {"name": "SoundCore Air Elite Earbuds",
         "sku": "SC-AP-004", "price": 199.99, "stock": 8,
         "description": "Ultra-lightweight true wireless earbuds with spatial audio, adaptive EQ and 30-hour total playtime.",
         "category_id": a, "brand_id": sc, "status": "active",
         "tags": ["audio", "earbuds", "tws", "wireless"]},

        # ── Electronics ────────────────────────────────────────────────────
        {"name": "TechNova UltraBook 14",
         "sku": "TN-UB-005", "price": 1499.00, "stock": 34,
         "description": "14-inch OLED laptop — Snapdragon X Elite, 32 GB LPDDR5, 1 TB NVMe, 18-hour battery and MIL-SPEC build.",
         "category_id": e, "brand_id": tn, "status": "active",
         "tags": ["laptop", "oled", "ultrabook", "windows", "portable"]},

        {"name": "TechNova Pad Pro 13",
         "sku": "TN-PAD-006", "price": 899.00, "stock": 56,
         "description": "13-inch AMOLED tablet, Wi-Fi 7, Bluetooth 5.4, optional folio keyboard, stylus support.",
         "category_id": e, "brand_id": tn, "status": "active",
         "tags": ["tablet", "amoled", "android", "portable"]},

        {"name": "TechNova Wireless Keyboard",
         "sku": "TN-KB-007", "price": 149.00, "stock": 0,
         "description": "Low-profile mechanical keyboard, PBT keycaps, Bluetooth 5.3, USB-C wired fallback, per-key RGB.",
         "category_id": h, "brand_id": tn, "status": "active",
         "tags": ["keyboard", "mechanical", "wireless", "office", "rgb"]},

        {"name": "TechNova 10-in-1 USB-C Hub",
         "sku": "TN-HUB-008", "price": 79.99, "stock": 210,
         "description": "Dual 4K HDMI, 10 Gbps USB-A ×3, SD/microSD, 100 W PD passthrough. Compact aluminium shell.",
         "category_id": e, "brand_id": tn, "status": "active",
         "tags": ["hub", "usb-c", "accessories", "dock"]},

        {"name": "TechNova ProMouse X",
         "sku": "TN-MX-009", "price": 89.99, "stock": 5,
         "description": "8000 DPI ergonomic wireless mouse, customisable weights, 90-day battery and silent switches.",
         "category_id": h, "brand_id": tn, "status": "active",
         "tags": ["mouse", "ergonomic", "wireless", "office"]},

        {"name": "TechNova Smart Webcam 4K",
         "sku": "TN-CAM-020", "price": 179.00, "stock": 73,
         "description": "4K 60fps webcam, AI auto-framing, dual noise-cancelling microphone array, privacy shutter.",
         "category_id": e, "brand_id": tn, "status": "active",
         "tags": ["webcam", "4k", "streaming", "wfh"]},

        # ── Wearables ──────────────────────────────────────────────────────
        {"name": "OrbitWear Pulse 3 Smartwatch",
         "sku": "OW-PL3-010", "price": 429.00, "stock": 63,
         "description": "Health-first smartwatch: ECG, SpO2, sleep coaching, 7-day battery, sapphire glass, LTE optional.",
         "category_id": w, "brand_id": ow, "status": "active",
         "tags": ["smartwatch", "health", "ecg", "wearable", "lte"]},

        {"name": "OrbitWear Band Lite",
         "sku": "OW-BD-011", "price": 79.00, "stock": 130,
         "description": "Slim fitness band, 24/7 heart rate, step & calorie tracking, stress monitor, 14-day battery.",
         "category_id": w, "brand_id": ow, "status": "active",
         "tags": ["fitness", "band", "wearable", "health"]},

        {"name": "OrbitWear AR Frames",
         "sku": "OW-AR-012", "price": 799.00, "stock": 12,
         "description": "Lightweight AR glasses with micro-OLED overlay display, 3-hour active use, IPX4, voice commands.",
         "category_id": w, "brand_id": ow, "status": "draft",
         "tags": ["ar", "glasses", "wearable", "tech"]},

        {"name": "OrbitWear Kids Tracker",
         "sku": "OW-KID-021", "price": 49.99, "stock": 95,
         "description": "GPS-enabled kids wristband, SOS button, geofencing, 5-day battery, colourful silicone band.",
         "category_id": w, "brand_id": ow, "status": "active",
         "tags": ["kids", "gps", "wearable", "safety"]},

        # ── Cameras ────────────────────────────────────────────────────────
        {"name": "LumaLens R7 Mirrorless Body",
         "sku": "LL-R7-013", "price": 2799.00, "stock": 18,
         "description": "45 MP full-frame mirrorless, 5-axis IBIS, dual card slots, 8K/30p video, weather-sealed magnesium alloy.",
         "category_id": c, "brand_id": ll, "status": "active",
         "tags": ["camera", "mirrorless", "fullframe", "8k", "pro"]},

        {"name": "LumaLens 24-70mm f/2.8 Pro Zoom",
         "sku": "LL-2470-014", "price": 1399.00, "stock": 29,
         "description": "Professional standard zoom, nano-coating, linear AF motor, constant f/2.8 aperture, weather sealed.",
         "category_id": c, "brand_id": ll, "status": "active",
         "tags": ["lens", "zoom", "f2.8", "pro", "fullframe"]},

        {"name": "LumaLens Compact A6",
         "sku": "LL-A6-015", "price": 849.00, "stock": 44,
         "description": "Pocketable APS-C compact, 24 MP, f/1.8 fixed lens, built-in ND filter, 4K video.",
         "category_id": c, "brand_id": ll, "status": "active",
         "tags": ["camera", "compact", "apsc", "travel"]},

        # ── Home & Office ──────────────────────────────────────────────────
        {"name": "DeskaForm Sit-Stand Desk Pro",
         "sku": "DF-DESK-016", "price": 899.00, "stock": 7,
         "description": "Electric height-adjustable desk, 180×80 cm solid oak top, dual motor, 4 memory presets, anti-collision.",
         "category_id": h, "brand_id": df, "status": "active",
         "tags": ["desk", "standing", "ergonomic", "office", "oak"]},

        {"name": "DeskaForm ErgoChair V2",
         "sku": "DF-CHR-017", "price": 649.00, "stock": 19,
         "description": "Fully adjustable ergonomic chair, adaptive lumbar support, 4D armrests, breathable all-day mesh back.",
         "category_id": h, "brand_id": df, "status": "active",
         "tags": ["chair", "ergonomic", "office", "mesh"]},

        {"name": "DeskaForm LED Architect Lamp",
         "sku": "DF-LED-019", "price": 119.00, "stock": 88,
         "description": "Architect-style LED desk lamp, CRI 95+, 2700–6500 K tunable white, with wireless Qi charging base.",
         "category_id": h, "brand_id": df, "status": "active",
         "tags": ["lighting", "led", "desk", "office", "qi"]},
    ]


def seed_products(token, cat_ids, brand_ids):
    h1("4 / Products + Pricing")
    catalog = product_catalog(cat_ids, brand_ids)
    created = []

    # Fetch existing products to skip duplicates
    _, existing = GET("/products/", token)
    existing_skus = set()
    if isinstance(existing, dict):
        existing_skus = {p.get("sku") for p in existing.get("items", [])}
    elif isinstance(existing, list):
        existing_skus = {p.get("sku") for p in existing}

    for p in catalog:
        price = p.pop("price")
        stock = p.pop("stock")

        if p["sku"] in existing_skus:
            warn(f"Already exists: {p['name']} [{p['sku']}]")
            continue

        code, resp = POST("/products/", p, token)
        if code not in (200, 201):
            fail(f"{p['name']}: {code} {resp}")
            continue

        pid_full = resp["id"]
        pid      = pid_full.split(":")[-1] if ":" in pid_full else pid_full

        # ── Set price via pricing router ─────────────────────
        pcode, _ = PATCH(f"/products/{pid}/price", {"price": price, "currency": "USD"}, token)
        price_ok = "✓" if pcode in (200, 201) else f"price {pcode}"

        # ── Set stock via inventory router ───────────────────
        scode, _ = POST(f"/products/{pid}/stock/set", {"quantity": stock}, token)
        stock_ok = "✓" if scode in (200, 201) else f"stock {scode}"

        # ── Publish active products ──────────────────────────
        if p.get("status") == "active":
            POST(f"/products/{pid}/publish", {}, token)

        ok(f"{p['name']} [{p['sku']}]  price={price_ok}  stock={stock_ok}")
        created.append({"id": pid, "full_id": pid_full, "name": p["name"], "price": price, "stock": stock})

    return created


# ── 5. Coupons ─────────────────────────────────────────────────────────────────
def seed_coupons(token):
    h1("5 / Coupons")
    coupons = [
        {"code": "WELCOME20", "type": "percentage",   "value": 20,   "min_order_value": 50,  "usage_limit": 500},
        {"code": "FLAT15",    "type": "fixed",         "value": 15,   "min_order_value": 100, "usage_limit": 200},
        {"code": "FREESHIP",  "type": "free_shipping", "value": 0,    "min_order_value": 30,  "usage_limit": 1000},
        {"code": "AUDIO30",   "type": "percentage",   "value": 30,   "min_order_value": 150, "usage_limit": 100},
    ]
    for c in coupons:
        code, resp = POST("/coupons/", c, token)
        if code == 201:
            ok(f"Created: {c['code']} ({c['type']}, value={c['value']})")
        elif code == 409:
            warn(f"Already exists: {c['code']}")
        else:
            fail(f"{c['code']}: {code} {resp}")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    check_health()
    token     = get_token()
    cat_ids   = seed_categories(token)
    brand_ids = seed_brands(token)
    created   = seed_products(token, cat_ids, brand_ids)
    seed_coupons(token)

    h1("Done! ✨")
    print(f"\n  {GREEN}{len(created)} products seeded{RESET}")
    print(f"  {GREEN}{len(cat_ids)} categories{RESET}  |  {GREEN}{len(brand_ids)} brands{RESET}")
    print(f"\n  Open: {BOLD}http://localhost:3000/dashboard.html{RESET}\n")
