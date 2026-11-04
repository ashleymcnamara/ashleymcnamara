#!/usr/bin/env python3
"""Renders the arcade-style profile SVGs in assets/.

Run: GITHUB_TOKEN=... python3 tools/render.py
The header pulls the live contribution calendar; cartridges and credits are static.
"""
import json
from datetime import date
import os
import urllib.request
from pathlib import Path

USER = "ashleymcnamara"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
INK = "#1a0f2e"
YELLOW = "#ffd479"
PINK = "#f7a8c4"
SHADOW = "#b8336a"
TEAL = "#7ee0d4"
THEMES = {
    "dark": {"top": "#1a0f2e", "bot": "#0d1117", "edge": "#3b2a5a", "title": YELLOW, "shadow": SHADOW,
             "text": "#c9d1d9", "muted": "#8b949e", "card": "#0d1117", "head": YELLOW, "coin": PINK},
    "light": {"top": "#fff0f6", "bot": "#fffaf0", "edge": "#f0cfe0", "title": INK, "shadow": PINK,
              "text": "#4a3a5a", "muted": "#7a6a8a", "card": "#fffaf0", "head": SHADOW, "coin": "#d1477a"},
}
LEVELS = {"NONE": "#161b22", "FIRST_QUARTILE": "#0e4429", "SECOND_QUARTILE": "#006d32",
          "THIRD_QUARTILE": "#26a641", "FOURTH_QUARTILE": "#39d353"}

PALETTE = {"k": INK, "p": PINK, "y": YELLOW, "w": "#fffaf0", "t": TEAL, "b": "#bfe3ff",
           "s": "#ffffff", "r": "#ff6b8b"}
SPRITES = {
    "snake": ["............", "......kkkk..", ".....kppppk.", "....kpwkppkr", "....kppppkr.",
              "..kkkpppk...", ".kpppppk....", "kppkkkk.....", "kpk.........", "kppkkkkkk...",
              ".kppppppppk.", "..kkkkkkkk.."],
    "tear": ["............", "...kkkkkk...", "..kyyyyyyk..", ".kyyyyyyyyk.", ".kykkyykkyk.",
             ".kybyyyybyk.", ".kbyyyyyybk.", ".kyyykkyyyk.", ".kyykyykyyk.", "..kyyyyyyk..",
             "...kkkkkk...", "............"],
    "cloud": ["............", "....kkkk....", "...kssssk...", ".kkssssssk..", "kssssssssskk",
              "kssssssssssk", "kssksssskssk", "kssssssssssk", "ksrsskkssrsk", ".kssssssssk.",
              "..kkkkkkkk..", "............"],
}

CARTS = [
    {"id": "snake", "title": "CONTRIBUTION SNAKE", "short": "SNAKE", "body": "#f7a8c4", "sky": "#1d1030",
     "desc": ["Snake, but the board is", "your GitHub graph."], "tag": ("1 PLAYER", "BROWSER"),
     "start": "PRESS START"},
    {"id": "tear", "title": "CRYING.DEV", "short": "CRYING", "body": "#b8d8ff", "sky": "#1b2440",
     "desc": ["A terminal where developers", "log their tears."], "tag": ("TERMINAL", "ALL TEARS"),
     "start": "LOG A TEAR"},
    {"id": "cloud", "title": "SOFT SKIES", "short": "SKIES", "body": "#ffd479", "sky": "url(#skygrad)",
     "desc": ["A squishy WebGPU sky.", "Stretch it, let it drift back."], "tag": ("WEBGPU", "SQUISHY"),
     "start": "SQUISH"},
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sprite(name, x, y, px):
    rows = SPRITES[name]
    rects = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch in PALETTE:
                rects.append(f'<rect x="{c}" y="{r}" width="1.02" height="1.02" fill="{PALETTE[ch]}"/>')
    return (f'<g transform="translate({x} {y}) scale({px})"><g class="hop" shape-rendering="crispEdges">'
            + "".join(rects) + "</g></g>")


def fetch_calendar():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    query = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
      totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def snake_board(weeks, x0, y0, pitch, cell, step):
    """Boustrophedon snake that eats lit cells; they regrow behind it so the loop is seamless."""
    path = []
    for w in range(len(weeks)):
        days = range(7) if w % 2 == 0 else range(6, -1, -1)
        path.extend((w, d) for d in days)
    n = len(path)
    total = n * step
    lookup = {}
    for w, week in enumerate(weeks):
        for day in week["contributionDays"]:
            d = date.fromisoformat(day["date"]).isoweekday() % 7
            lookup[(w, d)] = day["contributionLevel"]
    order = {pos: i for i, pos in enumerate(path)}

    out = []
    for (w, d), level in lookup.items():
        x, y = x0 + w * pitch, y0 + d * pitch
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="2" fill="{LEVELS["NONE"]}"/>')
        if level != "NONE":
            delay = order[(w, d)] * step - total
            out.append(f'<rect class="lit" style="animation-delay:{delay:.2f}s" x="{x:.1f}" y="{y:.1f}" '
                       f'width="{cell}" height="{cell}" rx="2" fill="{LEVELS[level]}"/>')

    frames = [f"{i / n * 100:.3f}%{{transform:translate({w * pitch:.1f}px,{d * pitch:.1f}px)}}"
              for i, (w, d) in enumerate(path)]
    lw, ld = path[-1]
    frames.append(f"100%{{transform:translate({lw * pitch:.1f}px,{ld * pitch:.1f}px)}}")
    css = (f"@keyframes mv{{{''.join(frames)}}}"
           f".seg{{animation:mv {total:.2f}s linear infinite}}"
           f"@keyframes eat{{0%{{opacity:0}}10%{{opacity:0}}14%{{opacity:1}}100%{{opacity:1}}}}"
           f".lit{{animation:eat {total:.2f}s linear infinite}}")
    segs = []
    for k in range(5, -1, -1):
        color = YELLOW if k == 0 else PINK
        delay = k * step - total
        segs.append(f'<rect class="seg" style="animation-delay:{delay:.2f}s" x="{x0}" y="{y0}" '
                    f'width="{cell}" height="{cell}" rx="2" fill="{color}"/>')
    return css, "".join(out) + "".join(segs)


def svg(w, h, css, body, title):
    reduce = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
            f"<style>{css}{reduce}</style>{body}</svg>\n")


def title_text(x, y, size, text, th, anchor="start"):
    t = esc(text)
    common = f'font-family="{MONO}" font-weight="800" font-size="{size}" text-anchor="{anchor}"'
    off = max(2, size // 12)
    return (f'<text x="{x + off}" y="{y + off}" {common} fill="{th["shadow"]}">{t}</text>'
            f'<text x="{x}" y="{y}" {common} fill="{th["title"]}">{t}</text>')


def header(cal, phone=False, theme="dark"):
    th = THEMES[theme]
    weeks = cal["weeks"]
    total = cal["totalContributions"]
    best = max(d["contributionCount"] for wk in weeks for d in wk["contributionDays"])
    hud_mid = f"{total:,} CONTRIBUTIONS"
    hud_right = f"BEST DAY {best}"
    bg = ('<defs><linearGradient id="cab" x1="0" y1="0" x2="0" y2="1">'
          f'<stop offset="0" stop-color="{th['top']}"/><stop offset="1" stop-color="{th['bot']}"/></linearGradient></defs>')
    if phone:
        weeks = weeks[-26:]
        W, H, pitch, cell = 400, 330, 13, 10.5
        gx, gy = 31, 200
        css, board = snake_board(weeks, gx, gy, pitch, cell, 0.16)
        body = (bg + f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="url(#cab)" stroke="{th['edge']}" stroke-width="2"/>'
                + title_text(22, 52, 26, "ASHLEY WILLIS", th) + title_text(22, 86, 26, "MAKES TINY TOYS.", th)
                + f'<text font-family="{SANS}" font-size="13.5" fill="{th['text']}">'
                  f'<tspan x="22" y="118">Sr. Director of DevRel at GitHub. In my</tspan>'
                  f'<tspan x="22" y="137">spare time I build small, delightful</tspan>'
                  f'<tspan x="22" y="156">things for the web.</tspan></text>'
                + f'<rect x="18" y="168" width="{W - 36}" height="134" rx="8" fill="#05070b" stroke="#3b2a5a" stroke-width="2"/>'
                + f'<text x="31" y="189" font-family="{MONO}" font-size="10" fill="{TEAL}">{hud_mid}</text>'
                + f'<text x="{W - 31}" y="189" text-anchor="end" font-family="{MONO}" font-size="10" fill="{TEAL}">{hud_right}</text>'
                + board
                + f'<text x="22" y="320" font-family="{SANS}" font-size="11" fill="{th['muted']}">↑ my real contribution graph, redrawn daily as a game of snake</text>')
    else:
        W, H, pitch, cell = 900, 410, 14.6, 11.5
        gx, gy = 66, 262
        css, board = snake_board(weeks, gx, gy, pitch, cell, 0.11)
        body = (bg + f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="url(#cab)" stroke="{th['edge']}" stroke-width="2"/>'
                + title_text(44, 82, 46, "ASHLEY WILLIS", th) + title_text(44, 136, 46, "MAKES TINY TOYS.", th)
                + f'<text font-family="{SANS}" font-size="17" fill="{th['text']}">'
                  f'<tspan x="44" y="178">Sr. Director of DevRel at GitHub. In my spare time I build small,</tspan>'
                  f'<tspan x="44" y="201">delightful things for the web.</tspan></text>'
                + f'<rect x="44" y="220" width="{W - 88}" height="152" rx="10" fill="#05070b" stroke="#3b2a5a" stroke-width="2"/>'
                + f'<text x="66" y="246" font-family="{MONO}" font-size="12" fill="{TEAL}">P1 · {USER.upper()}</text>'
                + f'<text x="{W / 2}" y="246" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{TEAL}">{hud_mid}</text>'
                + f'<text x="{W - 66}" y="246" text-anchor="end" font-family="{MONO}" font-size="12" fill="{TEAL}">{hud_right}</text>'
                + board
                + f'<text x="44" y="394" font-family="{SANS}" font-size="13" fill="{th['muted']}">↑ my real contribution graph, redrawn every day as a game of snake</text>')
    return svg(W, H, css, body, f"Ashley Willis makes tiny toys. A snake eats {USER}'s contribution graph: {total:,} contributions in the last year.")


CART_CSS = (f"@keyframes hop{{0%,49%{{transform:translateY(0)}}50%,100%{{transform:translateY(-.6px)}}}}"
            f".hop{{animation:hop 1.6s infinite}}"
            f"@keyframes blink{{0%,59%{{opacity:1}}60%,100%{{opacity:.25}}}}.start{{animation:blink 1.4s infinite}}")
SKYGRAD = ('<defs><linearGradient id="skygrad" x1="0" y1="0" x2="0" y2="1">'
           '<stop offset="0" stop-color="#8cc8f2"/><stop offset="1" stop-color="#f7c6d9"/></linearGradient></defs>')


def cart_shell(W, H, color):
    return (SKYGRAD
            + f'<rect x="0" y="6" width="{W}" height="{H - 6}" rx="10" fill="{INK}" fill-opacity=".22"/>'
            + f'<rect x="0" y="0" width="{W}" height="{H - 6}" rx="12" fill="{color}"/>'
            + f'<rect x="0" y="{H - 18}" width="{W}" height="12" fill="#0002"/>'
            + f'<rect x="{W * .22:.0f}" y="0" width="{W * .56:.0f}" height="8" rx="3" fill="#0003"/>')


def cart(c, i):
    W, H = 300, 350
    body = (cart_shell(W, H, c["body"])
            + f'<rect x="18" y="24" width="264" height="262" rx="8" fill="#fffaf0" stroke="{INK}" stroke-width="3"/>'
            + f'<rect x="32" y="38" width="236" height="118" rx="4" fill="{c["sky"]}"/>'
            + sprite(c["id"], 114, 61, 6)
            + f'<text x="32" y="184" font-family="{MONO}" font-weight="800" font-size="17" fill="{INK}">{esc(c["title"])}</text>'
            + f'<text font-family="{SANS}" font-size="13.5" fill="#4a3a5a"><tspan x="32" y="206">{esc(c["desc"][0])}</tspan>'
              f'<tspan x="32" y="224">{esc(c["desc"][1])}</tspan></text>'
            + f'<rect x="32" y="240" width="236" height="30" rx="4" fill="{INK}"/>'
            + f'<text x="44" y="260" font-family="{MONO}" font-weight="800" font-size="12" fill="{YELLOW}" letter-spacing="1">{c["tag"][0]}</text>'
            + f'<text x="256" y="260" text-anchor="end" font-family="{MONO}" font-weight="800" font-size="12" fill="#fffaf0" letter-spacing="1">{c["tag"][1]}</text>'
            + f'<text class="start" style="animation-delay:{i * .45:.2f}s" x="{W / 2}" y="318" text-anchor="middle" font-family="{MONO}" '
              f'font-weight="800" font-size="14" fill="{INK}" letter-spacing="2">▶ {esc(c["start"])}</text>')
    return svg(W, H, CART_CSS, body, f'{c["title"]}: {" ".join(c["desc"])} {c["start"]}.')


def cart_phone(c, i):
    W, H = 150, 230
    body = (cart_shell(W, H, c["body"])
            + f'<rect x="10" y="16" width="130" height="164" rx="6" fill="#fffaf0" stroke="{INK}" stroke-width="2.5"/>'
            + f'<rect x="19" y="25" width="112" height="96" rx="3" fill="{c["sky"]}"/>'
            + sprite(c["id"], 45, 43, 5)
            + f'<text x="75" y="146" text-anchor="middle" font-family="{MONO}" font-weight="800" font-size="16" fill="{INK}">{esc(c["short"])}</text>'
            + f'<text x="75" y="166" text-anchor="middle" font-family="{MONO}" font-weight="800" font-size="10" fill="#4a3a5a" letter-spacing=".5">{esc(c["tag"][0])}</text>'
            + f'<text class="start" style="animation-delay:{i * .45:.2f}s" x="75" y="206" text-anchor="middle" font-family="{MONO}" '
              f'font-weight="800" font-size="11" fill="{INK}" letter-spacing="1">▶ {esc(c["start"])}</text>')
    return svg(W, H, CART_CSS, body, f'{c["title"]}: {" ".join(c["desc"])}')


def credits(phone=False, theme="dark"):
    th = THEMES[theme]
    css = "@keyframes blink{0%,59%{opacity:1}60%,100%{opacity:0}}.ins{animation:blink 1.2s infinite}"
    if phone:
        W, H = 400, 150
        lines = ['Yes, I drew the Go gophers 🐹', "They're retired, free to use,", "and not open for commissions."]
        fs, y0, lh = 13, 64, 20
    else:
        W, H = 900, 130
        lines = ["Yes, I drew the Go gophers 🐹 They're retired, free to use, and not open for commissions."]
        fs, y0, lh = 14, 70, 22
    body = (f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="{th['card']}" stroke="{th['edge']}" stroke-width="2"/>'
            + f'<text x="{W / 2}" y="38" text-anchor="middle" font-family="{MONO}" font-weight="800" font-size="15" fill="{th['head']}" letter-spacing="2">CREDITS</text>'
            + "".join(f'<text x="{W / 2}" y="{y0 + i * lh}" text-anchor="middle" font-family="{MONO}" font-size="{fs}" fill="{th['text']}">{esc(t)}</text>'
                      for i, t in enumerate(lines))
            + f'<text class="ins" x="{W / 2}" y="{H - 20}" text-anchor="middle" font-family="{MONO}" font-weight="700" font-size="13" fill="{th['coin']}" letter-spacing="2">INSERT COIN TO CONTINUE</text>')
    return svg(W, H, css, body, "Credits: Yes, I drew the Go gophers. They're retired, free to use, and not open for commissions.")


def main():
    cal = fetch_calendar()
    files = {
        "header.svg": header(cal),
        "phone/header.svg": header(cal, phone=True),
        "credits.svg": credits(),
        "phone/credits.svg": credits(phone=True),
        "header-light.svg": header(cal, theme="light"),
        "phone/header-light.svg": header(cal, phone=True, theme="light"),
        "credits-light.svg": credits(theme="light"),
        "phone/credits-light.svg": credits(phone=True, theme="light"),
    }
    for i, c in enumerate(CARTS):
        files[f"cart-{i + 1}.svg"] = cart(c, i)
        files[f"phone/cart-{i + 1}.svg"] = cart_phone(c, i)
    for name, content in files.items():
        path = OUT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
