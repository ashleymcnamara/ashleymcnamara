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
    "dark": {"edge": "#3b2a5a", "title": YELLOW, "shadow": SHADOW, "outline": None,
             "text": "#c9d1d9", "muted": "#8b949e", "cab": "#1a0f2e", "head": YELLOW, "coin": PINK,
             "eggline": "#0b0614", "oneup": TEAL},
    "light": {"edge": "#f0cfe0", "title": YELLOW, "shadow": INK, "outline": INK,
              "text": "#4a3a5a", "muted": "#7a6a8a", "cab": "#fdebf3", "head": SHADOW, "coin": "#d1477a",
              "eggline": "#3b2a5c", "oneup": "#b8336a"},
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


def svg(w, h, css, body, title, x=0, y=0):
    reduce = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}" width="{w}" height="{h}" preserveAspectRatio="none" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
            f"<style>{css}{reduce}</style>{body}</svg>\n")


def title_text(x, y, size, text, th, anchor="start"):
    t = esc(text)
    common = f'font-family="{MONO}" font-weight="800" font-size="{size}" text-anchor="{anchor}"'
    off = max(2, size // 12)
    line = ""
    if th["outline"]:
        sw = max(2, size / 9)
        line = f' stroke="{th["outline"]}" stroke-width="{sw:.1f}" stroke-linejoin="round" paint-order="stroke"'
    return (f'<text x="{x + off}" y="{y + off}" {common} fill="{th["shadow"]}"{line}>{t}</text>'
            f'<text x="{x}" y="{y}" {common} fill="{th["title"]}"{line}>{t}</text>')


def frame(W, H, th, part):
    """One slice of the shared cabinet. Slices fill edge to edge so tiles meet with no visible seam."""
    box = {"top": (0, 0, W, H + 40), "bottom": (0, -40, W, H + 40),
           "left": (-40, -40, W + 80, H + 80), "right": (-40, -40, W + 80, H + 80),
           "mid": (-40, -40, W + 80, H + 80)}[part]
    x, y, w, h = box
    return (f'<rect x="{x}" y="{y}" width="{w:.2f}" height="{h}" rx="16" fill="{th["cab"]}"/>')


EGG = ["....XXXXX....", "..XXPPPPPXX..", ".XPHHPPPPPDX.", ".XPHPPPPPPDX.", "XPPPPPPPPPPDX",
       "XPPLLLLLLLPDX", "XPPLSSSSSLPDX", "XPPLSSBSSLPDX", "XPPLSSSSSLPDX", "XPPLLLLLLLPDX",
       "XPPPPPPPPPPDX", "XPPOPPOPPOPDX", ".XPPPPPPPPDX.", "..XXDDDDDXX..", "....XXXXX...."]
EGG_URL = "https://ashleymcnamara.github.io/devgotchi/"
EGG_CSS = (".e{transform-origin:50% 100%;transform-box:fill-box;animation:w 6s steps(1) infinite}"
           "@keyframes w{0%,84%{transform:rotate(0)}86%{transform:rotate(-8deg)}88%{transform:rotate(8deg)}"
           "90%{transform:rotate(-5deg)}92%{transform:rotate(4deg)}94%,100%{transform:rotate(0)}}"
           ".u,.b{animation:k 1.2s steps(1) infinite}.b{animation-duration:2.4s}@keyframes k{50%{opacity:0}}")


def egg(x, y, px, th):
    """the devgotchi easter egg: a tiny pixel egg that wiggles now and then."""
    c = {"X": th["eggline"], "P": PINK, "H": "#fff0f6", "D": "#e07aa4", "L": "#fbd3e2",
         "S": "#e6defa", "B": "#3b2a5c", "O": YELLOW}
    cells = []
    for j, row in enumerate(EGG):
        for i, ch in enumerate(row):
            if ch != ".":
                blink = ' class="b"' if ch == "B" else ""
                cells.append(f'<rect x="{x + i * px}" y="{y + j * px}" width="{px}" height="{px}" fill="{c[ch]}"{blink}/>')
    return f'<g class="e" shape-rendering="crispEdges">{"".join(cells)}</g>'


def header(cal, phone=False, theme="dark"):
    """three slices: title (links to the snake), egg tile (links to devgotchi), graph (links to the snake)."""
    th = THEMES[theme]
    weeks = cal["weeks"]
    total = cal["totalContributions"]
    best = max(d["contributionCount"] for wk in weeks for d in wk["contributionDays"])
    hud_mid = f"{total:,} CONTRIBUTIONS"
    hud_right = f"BEST DAY {best}"
    one_up = lambda x, y, fs: (f'<text class="u" x="{x}" y="{y}" text-anchor="middle" font-family="{MONO}" '
                               f'font-weight="700" font-size="{fs}" fill="{th["oneup"]}">1UP</text>')
    if phone:
        weeks = weeks[-26:]
        W, H, pitch, cell, CX, CY = 400, 330, 13, 10.5, 320, 62
        gx, gy = 31, 200
        css, board = snake_board(weeks, gx, gy, pitch, cell, 0.16)
        title = (frame(W, H, th, "top")
                 + title_text(22, 52, 26, "ASHLEY WILLIS", th))
        tile = egg(352, 12, 3, th) + one_up(337, 39, 10)
        graph = (frame(W, H, th, "top")
                 + title_text(22, 86, 24, "LEADS DEVREL AT GITHUB.", th)
                 + f'<text font-family="{SANS}" font-size="13.5" fill="{th['text']}">'
                   f'<tspan x="22" y="124">After hours, I build tiny,</tspan>'
                   f'<tspan x="22" y="144">delightful toys for the web.</tspan></text>'
                 + f'<rect x="18" y="168" width="{W - 36}" height="134" rx="8" fill="#05070b" stroke="#3b2a5a" stroke-width="2"/>'
                 + f'<text x="31" y="189" font-family="{MONO}" font-size="10" fill="{TEAL}">{hud_mid}</text>'
                 + f'<text x="{W - 31}" y="189" text-anchor="end" font-family="{MONO}" font-size="10" fill="{TEAL}">{hud_right}</text>'
                 + board
                 + f'<text x="22" y="320" font-family="{SANS}" font-size="11" fill="{th['muted']}">↑ my real contribution graph, redrawn daily as a game of snake</text>')
    else:
        W, H, pitch, cell, CX, CY = 900, 410, 14.6, 11.5, 720, 200
        gx, gy = 66, 262
        css, board = snake_board(weeks, gx, gy, pitch, cell, 0.11)
        title = (frame(W, H, th, "top")
                 + title_text(44, 82, 46, "ASHLEY WILLIS", th) + title_text(44, 136, 46, "LEADS DEVREL AT GITHUB.", th)
                 + f'<text font-family="{SANS}" font-size="17" fill="{th['text']}">'
                   f'<tspan x="44" y="186">After hours, I build tiny, delightful toys for the web.</tspan></text>')
        tile = egg(783, 62, 5, th) + one_up(815, 50, 15)
        graph = (frame(W, H, th, "top")
                 + f'<rect x="44" y="220" width="{W - 88}" height="152" rx="10" fill="#05070b" stroke="#3b2a5a" stroke-width="2"/>'
                 + f'<text x="66" y="246" font-family="{MONO}" font-size="12" fill="{TEAL}">P1 · {USER.upper()}</text>'
                 + f'<text x="{W / 2}" y="246" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{TEAL}">{hud_mid}</text>'
                 + f'<text x="{W - 66}" y="246" text-anchor="end" font-family="{MONO}" font-size="12" fill="{TEAL}">{hud_right}</text>'
                 + board
                 + f'<text x="44" y="394" font-family="{SANS}" font-size="13" fill="{th['muted']}">↑ my real contribution graph, redrawn every day as a game of snake</text>')
    alt = f"Ashley Willis leads DevRel at GitHub. A snake eats {USER}'s contribution graph: {total:,} contributions in the last year."
    return {"header": svg(CX, CY, "", title, "Ashley Willis leads DevRel at GitHub. After hours, I build tiny, delightful toys for the web."),
            "egg": svg(W - CX, CY, EGG_CSS, frame(W, H, th, "top") + tile, "A tiny wiggling egg. Press start to raise Byte.", x=CX),
            "graph": svg(W, H - CY, css, graph, alt, y=CY)}


STATS = [("PARTY", "10+", "people on my team"),
         ("XP", "15 YRS", "in community & DevRel"),
         ("CLASS", "LEADER", "builder · speaker · artist")]
WINS = ["Spoken at GopherCon, OSCON, Google Cloud Next, All Things Open & RenderATL"]
WINS_PHONE = [["Spoken at GopherCon, OSCON, Google Cloud", "Next, All Things Open & RenderATL"]]
SCREEN = 'fill="#05070b" stroke="#3b2a5a" stroke-width="2"'


def mainquest(phone=False, theme="dark"):
    th = THEMES[theme]
    alt = ("Main quest: Sr. Director of DevRel at GitHub. "
           + ". ".join(f"{k}: {v}, {sub}" for k, v, sub in STATS) + ". " + " ".join(WINS))
    if phone:
        W, H = 400, 260
        body = (frame(W, H, th, "mid")
                + f'<text x="22" y="30" font-family="{MONO}" font-weight="800" font-size="13" fill="{th["head"]}" letter-spacing="2">★ MAIN QUEST</text>'
                + f'<text x="{W - 22}" y="30" text-anchor="end" font-family="{MONO}" font-size="9.5" fill="{th["muted"]}" letter-spacing=".5">LVL: SR. DIRECTOR · DEVREL</text>'
                + f'<rect x="18" y="42" width="{W - 36}" height="150" rx="8" {SCREEN}/>')
        for i, (k, v, sub) in enumerate(STATS):
            y = 82 + i * 44
            if i:
                body += f'<line x1="34" y1="{y - 27}" x2="{W - 34}" y2="{y - 27}" stroke="#3b2a5a" stroke-width="1.5" stroke-dasharray="4 4"/>'
            body += (f'<text x="34" y="{y - 6}" font-family="{MONO}" font-size="10" fill="{TEAL}" letter-spacing="1.5">{k}</text>'
                     f'<text x="98" y="{y}" font-family="{MONO}" font-weight="800" font-size="21" fill="{YELLOW}">{esc(v)}</text>'
                     f'<text x="{W - 34}" y="{y - 5}" text-anchor="end" font-family="{SANS}" font-size="11" fill="#c9d1d9">{esc(sub)}</text>')
        y = 216
        for lines in WINS_PHONE:
            body += f'<text x="22" y="{y}" font-family="{MONO}" font-weight="800" font-size="12" fill="{th["coin"]}">✓</text>'
            body += f'<text font-family="{SANS}" font-size="13" fill="{th["text"]}">' + "".join(
                f'<tspan x="40" y="{y + j * 18}">{esc(t)}</tspan>' for j, t in enumerate(lines)) + "</text>"
            y += 18 * len(lines) + 6
        return svg(W, H, "", body, alt)
    W, H = 900, 250
    body = (frame(W, H, th, "mid")
            + f'<text x="44" y="34" font-family="{MONO}" font-weight="800" font-size="15" fill="{th["head"]}" letter-spacing="2">★ MAIN QUEST</text>'
            + f'<text x="{W - 44}" y="34" text-anchor="end" font-family="{MONO}" font-size="12" fill="{th["muted"]}" letter-spacing="1">CURRENT LEVEL: SR. DIRECTOR · DEVREL @ GITHUB</text>'
            + f'<rect x="44" y="48" width="{W - 88}" height="150" rx="10" {SCREEN}/>')
    cw = (W - 88) / len(STATS)
    for i, (k, v, sub) in enumerate(STATS):
        cx = 44 + cw * i + cw / 2
        if i:
            body += f'<line x1="{44 + cw * i:.1f}" y1="70" x2="{44 + cw * i:.1f}" y2="176" stroke="#3b2a5a" stroke-width="2" stroke-dasharray="4 4"/>'
        body += (f'<text x="{cx:.1f}" y="82" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{TEAL}" letter-spacing="2">{k}</text>'
                 f'<text x="{cx:.1f}" y="134" text-anchor="middle" font-family="{MONO}" font-weight="800" font-size="40" fill="{YELLOW}">{esc(v)}</text>'
                 f'<text x="{cx:.1f}" y="164" text-anchor="middle" font-family="{SANS}" font-size="12.5" fill="#c9d1d9">{esc(sub)}</text>')
    for i, q in enumerate(WINS):
        y = 226 + i * 22
        body += (f'<text x="44" y="{y}" font-family="{MONO}" font-weight="800" font-size="13" fill="{th["coin"]}">✓</text>'
                 f'<text x="66" y="{y}" font-family="{SANS}" font-size="14.5" fill="{th["text"]}">{esc(q)}</text>')
    return svg(W, H, "", body, alt)


def sidequests(phone=False, theme="dark"):
    th = THEMES[theme]
    W, H, m, fs, sub = (400, 40, 22, 13, 9.5) if phone else (900, 44, 44, 15, 12)
    body = (frame(W, H, th, "mid")
            + f'<line x1="{m}" y1="8" x2="{W - m}" y2="8" stroke="{th["edge"]}" stroke-width="2" stroke-dasharray="6 6"/>'
            + f'<text x="{m}" y="{H - 8}" font-family="{MONO}" font-weight="800" font-size="{fs}" fill="{th["head"]}" letter-spacing="2">◆ SIDE QUESTS</text>'
            + f'<text x="{W - m}" y="{H - 8}" text-anchor="end" font-family="{MONO}" font-size="{sub}" fill="{th["muted"]}" letter-spacing="1">TINY TOYS I BUILD AFTER HOURS</text>')
    return svg(W, H, "", body, "Side quests: tiny toys I build after hours.")


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


def slot(w, h, body, i, theme, SW, dx, dy, k, title):
    SH = round(h * k + dy + 14)
    part = ["left", "mid", "right"][i]
    return svg(f"{SW:.2f}", SH, CART_CSS, frame(SW, SH, THEMES[theme], part)
               + f'<g transform="translate({dx} {dy}) scale({k})">{body}</g>', title)


def cart(c, i, theme="dark"):
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
    return slot(W, H, body, i, theme, 300, 18, 4, .88, f'{c["title"]}: {" ".join(c["desc"])} {c["start"]}.')


def cart_phone(c, i, theme="dark"):
    W, H = 150, 230
    body = (cart_shell(W, H, c["body"])
            + f'<rect x="10" y="16" width="130" height="164" rx="6" fill="#fffaf0" stroke="{INK}" stroke-width="2.5"/>'
            + f'<rect x="19" y="25" width="112" height="96" rx="3" fill="{c["sky"]}"/>'
            + sprite(c["id"], 45, 43, 5)
            + f'<text x="75" y="146" text-anchor="middle" font-family="{MONO}" font-weight="800" font-size="16" fill="{INK}">{esc(c["short"])}</text>'
            + f'<text x="75" y="166" text-anchor="middle" font-family="{MONO}" font-weight="800" font-size="10" fill="#4a3a5a" letter-spacing=".5">{esc(c["tag"][0])}</text>'
            + f'<text class="start" style="animation-delay:{i * .45:.2f}s" x="75" y="206" text-anchor="middle" font-family="{MONO}" '
              f'font-weight="800" font-size="11" fill="{INK}" letter-spacing="1">▶ {esc(c["start"])}</text>')
    return slot(W, H, body, i, theme, 400 / 3, 6.67, 2, .8, f'{c["title"]}: {" ".join(c["desc"])}')


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
    body = (frame(W, H, th, "bottom")
            + f'<line x1="{W * .08:.0f}" y1="8" x2="{W * .92:.0f}" y2="8" stroke="{th['edge']}" stroke-width="2" stroke-dasharray="6 6"/>'
            + f'<text x="{W / 2}" y="38" text-anchor="middle" font-family="{MONO}" font-weight="800" font-size="15" fill="{th['head']}" letter-spacing="2">CREDITS</text>'
            + "".join(f'<text x="{W / 2}" y="{y0 + i * lh}" text-anchor="middle" font-family="{MONO}" font-size="{fs}" fill="{th['text']}">{esc(t)}</text>'
                      for i, t in enumerate(lines))
            + f'<text class="ins" x="{W / 2}" y="{H - 20}" text-anchor="middle" font-family="{MONO}" font-weight="700" font-size="13" fill="{th['coin']}" letter-spacing="2">INSERT COIN TO CONTINUE</text>')
    return svg(W, H, css, body, "Credits: Yes, I drew the Go gophers. They're retired, free to use, and not open for commissions.")


def main():
    cal = fetch_calendar()
    files = {
        "credits.svg": credits(),
        "phone/credits.svg": credits(phone=True),
        "credits-light.svg": credits(theme="light"),
        "phone/credits-light.svg": credits(phone=True, theme="light"),
    }
    for t, sfx in (("dark", ""), ("light", "-light")):
        for d, ph in (("", False), ("phone/", True)):
            for part, content in header(cal, phone=ph, theme=t).items():
                files[f"{d}{part}{sfx}.svg"] = content
        files[f"mainquest{sfx}.svg"] = mainquest(theme=t)
        files[f"phone/mainquest{sfx}.svg"] = mainquest(phone=True, theme=t)
        files[f"sidequests{sfx}.svg"] = sidequests(theme=t)
        files[f"phone/sidequests{sfx}.svg"] = sidequests(phone=True, theme=t)
    for i, c in enumerate(CARTS):
        files[f"cart-{i + 1}.svg"] = cart(c, i)
        files[f"phone/cart-{i + 1}.svg"] = cart_phone(c, i)
        files[f"cart-{i + 1}-light.svg"] = cart(c, i, "light")
        files[f"phone/cart-{i + 1}-light.svg"] = cart_phone(c, i, "light")
    for name, content in files.items():
        path = OUT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
