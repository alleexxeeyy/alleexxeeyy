import argparse
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.sax.saxutils import escape, quoteattr


SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
ASSETS = ROOT / "assets"
FONTS = SCRIPTS / "fonts"
STATS = SCRIPTS / "stats.json"

BG = "#0a0a0a"
BAR = "#0f0f0f"
BAND = "#0d0d0d"
LINE = "#222222"
TEXT = "#e6e6e6"
SOFT = "#9a9a9a"
DIM = "#5c5c5c"
RED = "#e3262f"
CYAN = "#5ee7ff"

ADVANCE = 0.6
HOLD = 0.5
FONT_STACK = "jbm,Consolas,Menlo,'DejaVu Sans Mono',monospace"
BOLD = ' class="xb"'
END = ' text-anchor="end"'
MIDDLE = ' text-anchor="middle" class="xb"'

REPOS = ["alleexxeeyy/playerok-universal", "alleexxeeyy/PlayerokAPI", "alleexxeeyy/funpay-universal"]

TICKER = ["python", "c#", "aiogram", "fastapi", "telegram bots", "funpay", "playerok",
          "ggsel", "digiseller", "wpf", "avalonia", "automation"]

CLIENTS = [
    ("ok", "approute-shop", "telegram store for digital codes · platega · auto-purchase",
     "telegram store · platega · auto-purchase"),
    ("ok", "ggsel-autopricer", "ggsel & digiseller prices synced with ps store, xbox, epic",
     "prices synced with ps store, xbox, epic"),
    ("ok", "kwork-responder", "kwork project scanner · ai scoring · auto-replies",
     "kwork scanner · ai scoring · replies"),
    ("ok", "digiseller-steam", "steam offline activations · steam guard codes on demand",
     "steam offline · guard codes on demand"),
    ("wip", "dota2-farm", "dota 2 account farm · win32 window control, no injection",
     "account farm · win32, no injection"),
]

PORTS = [
    ("22/tcp", "deploy", "linux · systemd · docker"),
    ("443/tcp", "telegram", "aiogram 3 · bots · stores · mini apps"),
    ("3306/tcp", "storage", "sqlite · mysql"),
    ("5000/tcp", "csharp", ".net · wpf · avalonia"),
    ("8000/tcp", "python", "fastapi · asyncio · httpx · aiohttp · pydantic"),
    ("8008/tcp", "ai", "deepseek · openai · gemini · openrouter"),
    ("8080/tcp", "scraping", "curl-cffi · beautifulsoup · lxml · websocket"),
]


class Sheet:
    def __init__(self, freeze=None):
        self.freeze = freeze
        self.rules = ["@keyframes show{0%{opacity:0}50%{opacity:1}100%{opacity:1}}",
                      "@keyframes blinkonce{0%{opacity:1}50%{opacity:0}99%{opacity:1}100%{opacity:1}}",
                      "@keyframes blink{0%{opacity:1}50%{opacity:0}100%{opacity:0}}",
                      "@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}"]

    def add(self, rule):
        self.rules.append(rule)

    def keyframes(self, name, frames):
        body = "".join(f"{pos}{{{props}}}" for pos, props in frames)
        self.rules.append(f"@keyframes {name}{{{body}}}")

    def animate(self, selector, name, duration, delay=0.0, timing="linear", count="1", fill="both"):
        paused = ""
        if self.freeze is not None:
            delay -= self.freeze
            paused = ";animation-play-state:paused"
        self.rules.append(f"{selector}{{animation:{name} {duration}s {timing} {delay:.3f}s {count} {fill}{paused}}}")

    def css(self):
        return "".join(self.rules)


def pct(t, total):
    return f"{min(max(t / total, 0), 1) * 100:.3f}%"


def font_face(weights):
    faces = []
    for weight in weights:
        data = base64.b64encode((FONTS / f"jbmono-{weight}.woff2").read_bytes()).decode()
        faces.append(f"@font-face{{font-family:jbm;font-weight:{weight};"
                     f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")
    return "".join(faces)


def base_css(weights):
    return (font_face(weights) +
            f"text{{font-family:{FONT_STACK};white-space:pre}}"
            ".xb{font-weight:800}")


def svg(w, h, label, defs, css, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'xml:space="preserve" role="img" aria-label={quoteattr(label)}><title>{escape(label)}</title>'
            f"<defs>{defs}</defs><style>{css}</style>{body}</svg>")


def window_defs(w, h):
    return (f'<clipPath id="win"><rect width="{w}" height="{h}" rx="12"/></clipPath>'
            f'<pattern id="sl" width="4" height="3" patternUnits="userSpaceOnUse">'
            f'<rect width="4" height="1" fill="#000" opacity=".3"/></pattern>'
            f'<linearGradient id="rf" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset=".5" stop-color="#fff" stop-opacity=".045"/>'
            f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            f'<radialGradient id="vg" cx=".5" cy=".5" r=".75">'
            f'<stop offset=".55" stop-color="#000" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="#000" stop-opacity=".6"/></radialGradient>')


def title_bar(w, bar, left, right):
    size = 13 if w < 800 else 14
    y = bar / 2 + size * 0.36
    return (f'<rect width="{w}" height="{bar}" fill="{BAR}"/>'
            f'<line x1="0" y1="{bar - 0.5}" x2="{w}" y2="{bar - 0.5}" stroke="{LINE}"/>'
            f'<circle cx="22" cy="{bar / 2}" r="4" fill="{RED}"/>'
            f'<text x="36" y="{y:.1f}" font-size="{size}" fill="{DIM}">{escape(left)}</text>'
            f'<text x="{w - 20}" y="{y:.1f}" font-size="{size}" fill="{DIM}" text-anchor="end">{escape(right)}</text>')


def crt(sheet, w, h):
    sheet.keyframes("refresh", [("from", "transform:translateY(-160px)"), ("to", f"transform:translateY({h}px)")])
    sheet.animate(".rf", "refresh", 7, count="infinite")
    return (f'<rect width="{w}" height="{h}" fill="url(#sl)"/>'
            f'<rect class="rf" width="{w}" height="160" fill="url(#rf)"/>'
            f'<rect width="{w}" height="{h}" fill="url(#vg)"/>')


def window(sheet, w, h, label, body, title=None, bar=0, defs="", weights=(400,)):
    parts = [f'<rect width="{w}" height="{h}" fill="{BG}"/>']
    if title:
        parts.append(title_bar(w, bar, *title))
    parts.extend(body)
    parts.append(crt(sheet, w, h))
    sheet.add("@media (prefers-reduced-motion:reduce){*{animation:none!important}.cover,.glitch,.rf{display:none}}")
    content = (f'<g clip-path="url(#win)">{"".join(parts)}</g>'
               f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="none" stroke="{LINE}"/>')
    return svg(w, h, label, window_defs(w, h) + defs, base_css(weights) + sheet.css(), content)


def spans(parts):
    return "".join(f'<tspan fill="{color}">{escape(text)}</tspan>' for text, color in parts)


def line(x, y, size, parts, extra=""):
    return f'<text x="{x:.2f}" y="{y:.1f}" font-size="{size}"{extra}>{spans(parts)}</text>'


def show(sheet, cls, at):
    sheet.animate(f".{cls}", "show", 0.4, at - 0.2, "step-end")


def typed(sheet, cls, x, y, size, parts, start, step, bg=BG):
    cw = size * ADVANCE
    n = sum(len(text) for text, _ in parts)
    duration = n * step
    shift = f"transform:translateX({n * cw:.2f}px)"
    sheet.keyframes(f"{cls}k", [("0%", "transform:translateX(0)"), (pct(duration, duration + HOLD), shift), ("100%", shift)])
    sheet.animate(f".{cls}", f"{cls}k", round(duration + HOLD, 3), start, f"steps({n},start)")
    cover = (f'<rect class="{cls} cover" x="{x - 1:.2f}" y="{y - size:.2f}" '
             f'width="{n * cw + 2:.2f}" height="{size * 1.35:.2f}" fill="{bg}"/>')
    return line(x, y, size, parts) + cover, start + duration


def prompt(sheet, cls, x, y, size, command, start=0.4, step=0.045):
    head = line(x, y, size, [("fried@fdev", RED), (":~$ ", SOFT)])
    if not command:
        return head, start
    text, end = typed(sheet, cls, x + 14 * size * ADVANCE, y, size, [(command, TEXT)], start, step)
    return head + text, end


def cursor(sheet, cls, x, y, size, at, color=SOFT):
    show(sheet, cls, at)
    sheet.animate(f".{cls}b", "blink", 1.06, at, "step-end", "infinite", "none")
    return (f'<g class="{cls}"><rect class="{cls}b" x="{x:.2f}" y="{y - size * 0.8:.2f}" '
            f'width="{size * ADVANCE * 0.55:.2f}" height="{size:.2f}" fill="{color}"/></g>')


def idle_prompt(sheet, cls, x, y, size, at):
    show(sheet, f"{cls}p", at)
    head = f'<g class="{cls}p">{line(x, y, size, [("fried@fdev", RED), (":~$ ", SOFT)])}</g>'
    return head + cursor(sheet, f"{cls}c", x + 14 * size * ADVANCE, y, size, at)


def ticker(sheet, w, y, height, size):
    cw = size * ADVANCE
    spacing = 3
    seq = []
    for item in TICKER:
        seq.append((item, SOFT))
        seq.append(("  //  ", RED))
    length = sum(len(text) for text, _ in seq)
    seq_w = length * (cw + spacing)
    copies = int(w // seq_w) + 2
    base = y + height / 2 + size * 0.36
    texts = "".join(line(24 + k * seq_w, base, size, seq, f' letter-spacing="{spacing}"') for k in range(copies))
    sheet.keyframes("tick", [("from", "transform:translateX(0)"), ("to", f"transform:translateX(-{seq_w:.2f}px)")])
    sheet.animate(".tick", "tick", round(seq_w / 38, 2), count="infinite")
    return (f'<rect y="{y}" width="{w}" height="{height}" fill="{BAND}"/>'
            f'<line x1="0" y1="{y + 0.5}" x2="{w}" y2="{y + 0.5}" stroke="{LINE}"/>'
            f'<g class="tick">{texts}</g>')


HERO = {
    False: {
        "w": 1280, "h": 500, "pad": 56, "bar": 44,
        "prompt_y": 106, "prompt_size": 22,
        "big_y": 268, "big_size": 112,
        "sub": [
            [("> ", RED), ("python & c# developer · 5+ years · bots, marketplaces, automation", SOFT)],
            [("● ", RED), ("open for orders · ", SOFT), ("tg @friedfluoride", TEXT)],
        ],
        "sub_y": 340, "sub_size": 24, "sub_gap": 38,
        "ticker_y": 436, "ticker_h": 64, "ticker_size": 18,
        "title": ("fried@fdev: ~", "bash — 120×32"),
    },
    True: {
        "w": 640, "h": 430, "pad": 32, "bar": 40,
        "prompt_y": 94, "prompt_size": 18,
        "big_y": 214, "big_size": 64,
        "sub": [
            [("> ", RED), ("python & c# developer · 5+ years", SOFT)],
            [("  ", RED), ("bots · marketplaces · automation", SOFT)],
            [("● ", RED), ("open for orders · ", SOFT), ("@friedfluoride", TEXT)],
        ],
        "sub_y": 270, "sub_size": 18, "sub_gap": 30,
        "ticker_y": 370, "ticker_h": 60, "ticker_size": 15,
        "title": ("fried@fdev: ~", "bash"),
    },
}


def hero(mobile=False, freeze=None):
    L = HERO[mobile]
    w, h, pad = L["w"], L["h"], L["pad"]
    sheet = Sheet(freeze)
    body = []

    size = L["prompt_size"]
    cw = size * ADVANCE
    cmd_x = pad + 14 * cw
    text, cmd_end = prompt(sheet, "hcmd", pad, L["prompt_y"], size, "./hello.sh", 0.5, 0.07)
    body.append(text)
    sheet.keyframes("hscur", [("0%", "opacity:1"), (pct(cmd_end + 0.25, cmd_end + 0.8), "opacity:0"), ("100%", "opacity:0")])
    sheet.animate(".hscur", "hscur", round(cmd_end + 0.8, 3), timing="step-end")
    shift = f"transform:translateX({10 * cw:.2f}px)"
    sheet.keyframes("hscurx", [("0%", "transform:translateX(0)"), (pct(cmd_end - 0.5, cmd_end - 0.5 + HOLD), shift), ("100%", shift)])
    sheet.animate(".hscurx", "hscurx", round(cmd_end - 0.5 + HOLD, 3), 0.5, "steps(10,start)")
    body.append(f'<g class="hscur" opacity="0"><rect class="hscurx" x="{cmd_x:.2f}" y="{L["prompt_y"] - size * 0.8:.2f}" '
                f'width="{cw * 0.55:.2f}" height="{size:.2f}" fill="{SOFT}"/></g>')

    size = L["big_size"]
    cw = size * ADVANCE
    x0, y0 = pad - size * 0.04, L["big_y"]
    start, step = cmd_end + 0.35, 0.085
    word = "hello, friend"
    chars = []
    marks = [(cmd_end + 0.25, 0)]
    for i, ch in enumerate(word):
        t = start + i * step
        chars.append([i, ch, TEXT, t, None])
        marks.append((t, i + 1))
    n = len(word)
    t_back = start + n * step + 1.05
    chars[n - 1][4] = t_back
    marks.append((t_back, n - 1))
    chars[n - 2][4] = t_back + 0.15
    marks.append((t_back + 0.15, n - 2))
    t_d = t_back + 0.55
    chars.append([n - 2, "d", TEXT, t_d, None])
    marks.append((t_d, n - 1))
    chars.append([n - 1, ".", RED, t_d + 0.17, None])
    marks.append((t_d + 0.17, n))
    total = t_d + 0.17 + HOLD

    for k, (i, ch, color, on, off) in enumerate(chars):
        if ch == " ":
            continue
        frames = [("0%", "opacity:0"), (pct(on, total), "opacity:1")]
        if off is not None:
            frames.append((pct(off, total), "opacity:0"))
        frames.append(("100%", f"opacity:{0 if off is not None else 1}"))
        sheet.keyframes(f"hb{k}", frames)
        sheet.animate(f".hb{k}", f"hb{k}", round(total, 3), timing="step-end")
        body.append(f'<text class="hb{k} xb" x="{x0 + i * cw:.2f}" y="{y0}" font-size="{size}" fill="{color}" '
                    f'opacity="{0 if off is not None else 1}">{escape(ch)}</text>')

    frames = [(pct(t, total), f"transform:translateX({(idx - n) * cw:.2f}px)") for t, idx in marks]
    frames.insert(0, ("0%", f"transform:translateX({-n * cw:.2f}px)"))
    frames.append(("100%", "transform:translateX(0)"))
    sheet.keyframes("hbcx", frames)
    sheet.animate(".hbcx", "hbcx", round(total, 3), timing="step-end")
    sheet.keyframes("hbcon", [("0%", "opacity:0"), (pct(marks[0][0], total), "opacity:1"), ("100%", "opacity:1")])
    sheet.animate(".hbcon", "hbcon", round(total, 3), timing="step-end")
    sheet.animate(".hblink", "blink", 1.06, t_d + 0.3, "step-end", "infinite", "none")
    sheet.animate(".hidle", "blinkonce", 1.06, start + n * step, "step-end", "1", "none")
    body.append(f'<g class="hbcon"><g class="hblink"><g class="hidle"><rect class="hbcx" x="{x0 + n * cw + size * 0.03:.2f}" '
                f'y="{y0 - size * 0.8:.2f}" width="{cw * 0.5:.2f}" height="{size * 0.9:.2f}" fill="{RED}"/></g></g></g>')

    final = escape("hello, fried")
    g_start, g_period = t_d + 0.45, 7.0
    bands = [(0.80, 0.62, -16), (0.48, 0.3, 11), (0.2, 0.14, -7)]
    defs = ""
    glitch = [f'<text x="{x0 - 6:.2f}" y="{y0}" font-size="{size}" fill="{RED}" opacity=".85" class="xb">{final}.</text>',
              f'<text x="{x0 + 5:.2f}" y="{y0 + 2}" font-size="{size}" fill="{CYAN}" opacity=".45" class="xb">{final}.</text>']
    for k, (top, height, shift) in enumerate(bands):
        by = y0 - size * top
        defs += f'<clipPath id="hband{k}"><rect x="0" y="{by:.2f}" width="{w}" height="{size * height * 0.6:.2f}"/></clipPath>'
        sheet.keyframes(f"hsh{k}", [("0%", f"transform:translateX({shift}px)"), ("1.6%", f"transform:translateX({-shift * 0.6:.1f}px)"),
                                    ("3.2%", f"transform:translateX({shift * 0.4:.1f}px)"), ("4.8%", "transform:translateX(0)"),
                                    ("100%", "transform:translateX(0)")])
        sheet.animate(f".hsh{k}", f"hsh{k}", g_period, g_start, "step-end", "infinite", "none")
        glitch.append(f'<g clip-path="url(#hband{k})"><g class="hsh{k}"><rect x="0" y="{by:.2f}" width="{w}" '
                      f'height="{size * height * 0.6:.2f}" fill="{BG}"/><text x="{x0:.2f}" y="{y0}" font-size="{size}" '
                      f'fill="{TEXT}" class="xb">{final}<tspan fill="{RED}">.</tspan></text></g></g>')
    sheet.keyframes("hgl", [("0%", "opacity:1"), ("5%", "opacity:0"), ("100%", "opacity:0")])
    sheet.animate(".hgl", "hgl", g_period, g_start, "step-end", "infinite", "none")
    body.append(f'<g class="hgl glitch" opacity="0">{"".join(glitch)}</g>')

    size = L["sub_size"]
    t = g_start + 0.4
    for k, parts in enumerate(L["sub"]):
        text, t = typed(sheet, f"hsub{k}", pad, L["sub_y"] + k * L["sub_gap"], size, parts, t + 0.15 * (k > 0), 0.026)
        body.append(text)

    body.append(ticker(sheet, w, L["ticker_y"], L["ticker_h"], L["ticker_size"]))
    label = "hello, fried. — python & c# developer, 5+ years: bots, marketplaces, automation"
    return window(sheet, w, h, label, body, L["title"], L["bar"], defs, (400, 800))


def uptime(created, synced):
    a = datetime.fromisoformat(created.replace("Z", "+00:00"))
    b = datetime.fromisoformat(synced.replace("Z", "+00:00"))
    months = (b.year - a.year) * 12 + b.month - a.month - (b.day < a.day)
    return f"{months // 12}y {months % 12}m" if months >= 12 else f"{months}m"


def projects(stats, mobile=False, freeze=None):
    w, pad, bar, size, lh = (640, 32, 40, 19, 36) if mobile else (1280, 56, 44, 22, 42)
    cw = size * ADVANCE
    sheet = Sheet(freeze)
    repos, synced = stats["repos"], stats["synced"]
    if mobile:
        cols = [("NAME", 20, "<"), ("STARS", 6, ">"), ("VER", 8, ">"), ("REL", 6, ">")]
    else:
        cols = [("PID", 6, "<"), ("NAME", 21, "<"), ("STARS", 7, ">"), ("FORKS", 7, ">"),
                ("VERSION", 10, ">"), ("RELEASES", 10, ">"), ("UPTIME", 9, ">")]
    status_at = sum(width for _, width, _ in cols) + 2

    y = bar + 44 + size * 0.2
    body = []
    text, t = prompt(sheet, "cmd", pad, y, size, "ps aux --sort=-stars")
    body.append(text)

    y += lh * 1.25
    head = "".join(title.ljust(width) if align == "<" else title.rjust(width) for title, width, align in cols)
    head += "  " + ("" if mobile else "STATUS")
    show(sheet, "head", t + 0.25)
    body.append(f'<g class="head"><rect x="{pad - 10}" y="{y - size * 0.95:.1f}" width="{w - 2 * pad + 20}" '
                f'height="{size * 1.35:.1f}" fill="{RED}"/>{line(pad, y, size, [(head, BG)], BOLD)}</g>')

    for k, repo in enumerate(repos):
        y += lh
        values = {
            "PID": f"0x{k + 1:02d}", "NAME": repo["name"], "STARS": repo["stars"], "FORKS": repo["forks"],
            "VERSION": repo["version"], "VER": repo["version"], "RELEASES": repo["releases"] or "—",
            "REL": repo["releases"] or "—", "UPTIME": uptime(repo["created"], synced),
        }
        parts = []
        for title, width, align in cols:
            value = str(values[title])[:width - 1]
            color = DIM if title == "PID" else TEXT if title in ("NAME", "STARS") else SOFT
            parts.append((value.ljust(width) if align == "<" else value.rjust(width), color))
        show(sheet, f"r{k}", t + 0.45 + 0.2 * k)
        status = "" if mobile else line(pad + (status_at + 2) * cw, y, size, [("running", SOFT)])
        body.append(f'<g class="r{k}">{line(pad, y, size, parts)}<circle class="pulse" cx="{pad + (status_at + 0.5) * cw:.2f}" '
                    f'cy="{y - size * 0.32:.2f}" r="{size * 0.2:.2f}" fill="{RED}"/>{status}</g>')
    sheet.animate(".pulse", "pulse", 2, 0, "ease-in-out", "infinite", "none")

    at = t + 0.45 + 0.2 * len(repos) + 0.2
    stars = sum(repo["stars"] for repo in repos)
    forks = sum(repo["forks"] for repo in repos)
    releases = sum(repo["releases"] for repo in repos)
    sync = f"updated {synced[:10]} utc"
    y += lh * 0.6
    summary = [f'<line x1="{pad}" y1="{y:.1f}" x2="{w - pad}" y2="{y:.1f}" stroke="{LINE}"/>']
    y += lh * 0.85
    if mobile:
        summary.append(line(pad, y, size, [(str(releases), TEXT), (" releases · ", SOFT), (str(stars), TEXT), (" stars", SOFT)]))
        y += lh * 0.8
        summary.append(line(pad, y, size, [(sync, DIM)]))
    else:
        summary.append(line(pad, y, size, [(f"{len(repos)} processes · ", SOFT), (str(stars), TEXT), (" stars · ", SOFT),
                                           (str(forks), TEXT), (" forks · ", SOFT), (str(releases), TEXT), (" releases", SOFT)]))
        summary.append(line(w - pad, y, size, [(sync, DIM)], END))
    show(sheet, "sum", at)
    body.append(f'<g class="sum">{"".join(summary)}</g>')

    y += lh * 1.15
    body.append(idle_prompt(sheet, "end", pad, y, size, at + 0.3))
    h = round(y + lh * 0.9)
    names = ", ".join(f"{repo['name']} {repo['stars']} stars" for repo in repos)
    label = f"ps aux: {names}; {releases} releases"
    title = ("fried@fdev: ~/projects", "bash — ps") if not mobile else ("~/projects", "ps")
    return window(sheet, w, h, label, body, title, bar, weights=(400, 800))


def clients(mobile=False, freeze=None):
    w, pad, bar, size = (640, 28, 40, 17) if mobile else (1280, 56, 44, 20)
    cw = size * ADVANCE
    sheet = Sheet(freeze)
    y = bar + 44 + size * 0.2
    body = []
    text, t = prompt(sheet, "cmd", pad, y, size, "tail -f clients.log")
    body.append(text)
    y += 12

    for k, (state, name, desc, short) in enumerate(CLIENTS):
        tag = [("[ ", DIM), ("ok", TEXT), ("  ]", DIM)] if state == "ok" else [("[ ", DIM), ("wip", RED), (" ]", DIM)]
        pulse = ' class="pulse"' if state == "wip" else ""
        show(sheet, f"l{k}", t + 0.4 + 0.45 * k)
        if mobile:
            y += 38
            row = (line(pad, y, size, tag, pulse) + line(pad + 9 * cw, y, size, [(name, TEXT)]) +
                   line(pad + 9 * cw, y + 26, size, [(short, SOFT)]))
            y += 26
        else:
            y += 40
            row = line(pad, y, size, tag, pulse) + line(pad + 9 * cw, y, size, [(name.ljust(19), TEXT), (desc, SOFT)])
        body.append(f'<g class="l{k}">{row}</g>')
    sheet.animate(".pulse", "pulse", 2, 0, "ease-in-out", "infinite", "none")

    y += 40 if not mobile else 42
    body.append(cursor(sheet, "end", pad, y, size, t + 0.4 + 0.45 * len(CLIENTS)))
    h = round(y + (36 if not mobile else 30))
    label = "clients.log: " + "; ".join(f"{name} — {desc}" for _, name, desc, _ in CLIENTS)
    title = ("fried@fdev: /var/log/fdev", "tail") if not mobile else ("/var/log/fdev", "tail")
    return window(sheet, w, h, label, body, title, bar)


def stack(mobile=False, freeze=None):
    w, pad, bar, size = (640, 28, 40, 17) if mobile else (1280, 56, 44, 20)
    cw = size * ADVANCE
    sheet = Sheet(freeze)
    y = bar + 44 + size * 0.2
    body = []
    text, t = prompt(sheet, "cmd", pad, y, size, "nmap -sV fried")
    body.append(text)

    at = t + 0.5
    intro = [] if mobile else ["Nmap scan report for fried (fdev.local)"]
    intro.append("Host is up (0.00042s latency).")
    for k, msg in enumerate(intro):
        y += 34 if k else 44
        show(sheet, f"i{k}", at + 0.3 * k)
        body.append(f'<g class="i{k}">{line(pad, y, size, [(msg, DIM)])}</g>')
    at += 0.3 * len(intro) + 0.2

    y += 48
    head = "PORT      SERVICE" if mobile else "PORT      STATE  SERVICE   VERSION"
    show(sheet, "head", at)
    body.append(f'<g class="head">{line(pad, y, size, [(head, SOFT)], BOLD)}</g>')

    for k, (port, service, version) in enumerate(PORTS):
        show(sheet, f"p{k}", at + 0.25 + 0.18 * k)
        if mobile:
            y += 36
            row = (line(pad, y, size, [(port.ljust(10), TEXT), (service, RED)]) +
                   line(pad + 10 * cw, y + 24, size, [(version, SOFT)]))
            y += 24
        else:
            y += 38
            row = line(pad, y, size, [(port.ljust(10), TEXT), ("open".ljust(7), RED), (service.ljust(10), TEXT), (version, SOFT)])
        body.append(f'<g class="p{k}">{row}</g>')
    at += 0.25 + 0.18 * len(PORTS) + 0.3

    y += 50
    done = f"Nmap done: 1 host up, {len(PORTS)} services" if mobile else "Nmap done: 1 IP address (1 host up) scanned in 1.42 seconds"
    show(sheet, "done", at)
    body.append(f'<g class="done">{line(pad, y, size, [(done, DIM)])}</g>')
    y += 44
    body.append(idle_prompt(sheet, "end", pad, y, size, at + 0.3))
    h = round(y + 34)
    label = "nmap -sV fried: " + "; ".join(f"{service}: {version}" for _, service, version in PORTS)
    title = ("fried@fdev: ~", "bash — nmap") if not mobile else ("~", "nmap")
    return window(sheet, w, h, label, body, title, bar, weights=(400, 800))


def connect(mobile=False, freeze=None):
    w, h, pad, size = (640, 176, 28, 18) if mobile else (1280, 150, 56, 24)
    cw = size * ADVANCE
    sheet = Sheet(freeze)
    body = []
    y = 64 if not mobile else 58
    command = "./connect --tg @friedfluoride" if mobile else "./connect --telegram @friedfluoride"
    text, t = prompt(sheet, "cmd", pad, y, size, command, 0.5, 0.05)
    body.append(text)
    body.append(cursor(sheet, "cur", pad + (14 + len(command) + 1) * cw, y, size, t, RED))

    note = "# what to automate? we'll figure out time & price" if not mobile else "# what to automate?"
    y2 = y + (44 if not mobile else 40)
    show(sheet, "note", t + 0.3)
    body.append(f'<g class="note">{line(pad, y2, size * 0.8 if not mobile else size * 0.85, [(note, DIM)])}</g>')

    ex, ey = (w - pad, y) if not mobile else (pad, y2 + 46)
    show(sheet, "enter", t + 0.3)
    bw = 11 * cw
    bx = ex - bw if not mobile else ex
    sheet.animate(".enter rect", "pulse", 1.6, t + 0.3, "ease-in-out", "infinite", "none")
    body.append(f'<g class="enter"><rect x="{bx:.1f}" y="{ey - size * 1.05:.1f}" width="{bw:.1f}" height="{size * 1.5:.1f}" '
                f'rx="4" fill="none" stroke="{RED}"/>'
                f'{line(bx + bw / 2, ey, size, [("[ enter ]", RED)], MIDDLE)}</g>')
    label = "write me on telegram: @friedfluoride"
    return window(sheet, w, h, label, body, weights=(400, 800))


def request(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "fried-profile"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
                return response.read().decode(), response.headers.get("Link", "")
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 2:
                raise
        except urllib.error.URLError:
            if attempt == 2:
                raise
        time.sleep(5)


def setup_version(repo):
    try:
        setup = request(f"https://raw.githubusercontent.com/{repo}/HEAD/setup.py")[0]
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        return "—"
    match = re.search(r"setup\(.*?\bversion\s*=\s*[\"']([^\"']+)[\"']", setup, re.S)
    return match.group(1) if match else "—"


def fetch_repo(repo):
    data = json.loads(request(f"https://api.github.com/repos/{repo}")[0])
    body, link = request(f"https://api.github.com/repos/{repo}/releases?per_page=1")
    last = re.search(r'<([^>]+)>;\s*rel="last"', link)
    releases = int(parse_qs(urlparse(last.group(1)).query)["page"][0]) if last else len(json.loads(body))
    if releases:
        try:
            version = json.loads(request(f"https://api.github.com/repos/{repo}/releases/latest")[0])["tag_name"]
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            version = json.loads(body)[0]["tag_name"]
    else:
        version = setup_version(repo)
    return {"name": data["name"], "stars": data["stargazers_count"], "forks": data["forks_count"],
            "version": version, "releases": releases, "created": data["created_at"]}


def update_stats():
    repos = sorted((fetch_repo(repo) for repo in REPOS), key=lambda repo: -repo["stars"])
    if STATS.exists():
        old = json.loads(STATS.read_text(encoding="utf-8"))
        if old["repos"] == repos:
            return old
    stats = {"synced": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "repos": repos}
    STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="подтянуть свежие цифры из GitHub API")
    args = parser.parse_args()
    stats = update_stats() if args.live else json.loads(STATS.read_text(encoding="utf-8"))

    ASSETS.mkdir(exist_ok=True)
    files = {}
    for mobile in (False, True):
        suffix = "-mobile" if mobile else ""
        files[f"hero{suffix}.svg"] = hero(mobile)
        files[f"projects{suffix}.svg"] = projects(stats, mobile)
        files[f"clients{suffix}.svg"] = clients(mobile)
        files[f"stack{suffix}.svg"] = stack(mobile)
        files[f"connect{suffix}.svg"] = connect(mobile)
    for name, content in files.items():
        (ASSETS / name).write_text(content, encoding="utf-8")
        print(f"{name}: {len(content.encode()) // 1024} КБ")


if __name__ == "__main__":
    main()
