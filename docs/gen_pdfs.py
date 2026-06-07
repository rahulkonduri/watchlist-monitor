"""Generate both watchlist-monitor PDFs."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, PageBreak, KeepTogether)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

W, H = A4

# ── Shared helpers ────────────────────────────────────────────────────────────
def base_styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle('Title2', parent=s['Title'], fontSize=22, spaceAfter=6, textColor=colors.HexColor('#1a237e')))
    s.add(ParagraphStyle('Sub',    parent=s['Normal'], fontSize=11, textColor=colors.HexColor('#455a64'), spaceAfter=18, alignment=TA_CENTER))
    s.add(ParagraphStyle('H1',     parent=s['Heading1'], fontSize=14, textColor=colors.HexColor('#1565c0'), spaceBefore=18, spaceAfter=6, borderPad=2))
    s.add(ParagraphStyle('H2',     parent=s['Heading2'], fontSize=12, textColor=colors.HexColor('#0277bd'), spaceBefore=12, spaceAfter=4))
    s.add(ParagraphStyle('H3',     parent=s['Heading3'], fontSize=10, textColor=colors.HexColor('#00838f'), spaceBefore=8, spaceAfter=3))
    s.add(ParagraphStyle('Body',   parent=s['Normal'],  fontSize=9.5, leading=14, spaceAfter=6, alignment=TA_JUSTIFY))
    s.add(ParagraphStyle('Li', parent=s['Normal'],  fontSize=9.5, leading=13, leftIndent=16, spaceAfter=2))
    s.add(ParagraphStyle('Mono',   parent=s['Code'],    fontSize=8.5, backColor=colors.HexColor('#f5f5f5'), leftIndent=12, rightIndent=12, spaceBefore=4, spaceAfter=4))
    s.add(ParagraphStyle('Callout',parent=s['Normal'],  fontSize=9.5, leading=13, backColor=colors.HexColor('#e3f2fd'), leftIndent=12, rightIndent=12, borderPad=6, spaceBefore=6, spaceAfter=6, borderColor=colors.HexColor('#1565c0'), borderWidth=1))
    s.add(ParagraphStyle('Warn',   parent=s['Normal'],  fontSize=9.5, leading=13, backColor=colors.HexColor('#fff8e1'), leftIndent=12, rightIndent=12, borderPad=6, spaceBefore=6, spaceAfter=6))
    s.add(ParagraphStyle('Footer', parent=s['Normal'],  fontSize=7.5, textColor=colors.grey, alignment=TA_CENTER))
    return s

def tbl(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1565c0')),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f0f4ff')]),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#cfd8dc')),
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING',(0,0),(-1,-1), 6),
    ]
    if not header:
        style[0] = ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e3f2fd'))
        style[1] = ('TEXTCOLOR',  (0,0), (-1,0), colors.HexColor('#1565c0'))
    t.setStyle(TableStyle(style))
    return t

def hr(): return HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bbdefb'), spaceAfter=8, spaceBefore=4)

def footer_cb(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(W/2, 1.8*cm, f"watchlist-monitor  |  Page {doc.page}  |  Informational only — not financial advice")
    canvas.restoreState()

# ═══════════════════════════════════════════════════════════════════════════════
# PDF 1 — Indicators & Signal Assessment Guide
# ═══════════════════════════════════════════════════════════════════════════════
def build_pdf1(path):
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2.5*cm)
    s = base_styles()
    P = lambda txt, style='Body': Paragraph(txt, s[style])
    B = lambda txt: Paragraph(f"• {txt}", s['Li'])
    story = []

    # Cover
    story += [Spacer(1, 1.5*cm),
              P("Understanding Technical Indicators<br/>&amp; Signal Assessments", 'Title2'),
              P("A complete guide to watchlist-monitor's indicators, assessment labels, and their relationships", 'Sub'),
              hr(), Spacer(1, 0.3*cm),
              P("<b>Who this is for:</b> Anyone using watchlist-monitor who wants to understand "
                "what RSI, SMA, golden/death cross and the assessment labels actually mean — "
                "and crucially, what they do <i>not</i> mean.", 'Body'),
              Paragraph("<b>⚠ Important:</b> All indicators are descriptions of current or past conditions. "
                        "None of them predict future prices. This tool is decision-support, not financial advice.",
                        s['Warn']),
              PageBreak()]

    # Chapter 1
    story += [P("Chapter 1: The Four Indicators", 'H1'), hr()]

    story += [P("1.1  RSI — Relative Strength Index (Wilder's, 14-period)", 'H2'),
              P("RSI measures the <b>speed and size of recent price changes</b> on a 0–100 scale. "
                "Invented by J. Welles Wilder Jr. in 1978, it is one of the most widely-used "
                "momentum indicators in the world.", 'Body'),
              P("How it is calculated:", 'H3'),
              P("Step 1 — Compute daily changes: today's close minus yesterday's close.", 'Li'),
              P("Step 2 — Separate gains (positive changes) from losses (absolute negative changes).", 'Li'),
              P("Step 3 — Seed with the simple average of the first 14 gains and 14 losses.", 'Li'),
              P("Step 4 — Wilder's smoothing for every day after:", 'Li'),
              Paragraph("avg_gain = (prev_avg_gain × 13 + today_gain) / 14<br/>"
                        "avg_loss = (prev_avg_loss × 13 + today_loss) / 14", s['Code']),
              P("Step 5 — RS = avg_gain / avg_loss", 'Li'),
              P("Step 6 — RSI = 100 − (100 / (1 + RS))", 'Li'),
              Spacer(1,0.2*cm),
              tbl([["RSI Range","Zone","What it generally signals"],
                   ["0 – 30","Oversold","Price fell fast; some mean-reversion traders watch closely"],
                   ["30 – 50","Weakly bearish","Momentum tilted downward but not extreme"],
                   ["~50","Neutral midpoint","Roughly equal gains and losses"],
                   ["50 – 70","Weakly bullish","Momentum tilted upward but not extreme"],
                   ["70 – 100","Overbought","Price rose fast; some traders watch for pullbacks"]],
                  [2.5*cm, 3.5*cm, 9.5*cm]),
              Spacer(1,0.3*cm),
              Paragraph("<b>Key nuances:</b> RSI can stay above 70 for months (NVIDIA 2023) or below 30 "
                        "through an entire bear market. It is a <b>momentum measure, not a forecaster.</b>",
                        s['Callout'])]

    story += [Spacer(1,0.4*cm), P("1.2  SMA — Simple Moving Average", 'H2'),
              P("An SMA averages closing prices over N trading days, smoothing out noise to "
                "reveal the underlying trend direction. Formula: SMA(n) = sum of last n closes ÷ n", 'Body'),
              tbl([["SMA","Period","What it tracks","Why it matters"],
                   ["Short SMA","50 days","Medium-term trend (~10 weeks)","Watched by most active traders"],
                   ["Long SMA","200 days","Long-term trend (~10 months)","The most-watched trend divider in finance"]],
                  [2.5*cm, 2.5*cm, 5*cm, 5.5*cm]),
              Spacer(1,0.2*cm),
              Paragraph("<b>Price above 200-day SMA</b> = long-term bull context. "
                        "<b>Price below 200-day SMA</b> = long-term bear context. "
                        "Both SMAs lag — they reflect where price <i>has been</i>, not where it is going.",
                        s['Callout'])]

    story += [Spacer(1,0.4*cm), P("1.3  MA Crossover — Golden Cross &amp; Death Cross", 'H2'),
              P("A crossover fires when the short SMA and long SMA change relative positions "
                "between the previous bar and the current bar.", 'Body'),
              tbl([["Event","Condition","Common interpretation"],
                   ["Golden Cross","Short SMA crosses ABOVE long SMA","Medium-term trend overtook long-term — potential uptrend start"],
                   ["Death Cross","Short SMA crosses BELOW long SMA","Medium-term trend fell below long-term — potential downtrend start"],
                   ["None","No change in relative position","No crossover event today"]],
                  [3*cm, 6*cm, 6.5*cm]),
              Spacer(1,0.2*cm),
              Paragraph("<b>Critical:</b> Crossovers are heavily <b>lagging</b>. The S&P 500's 2020 golden "
                        "cross appeared <i>after</i> the index had already rallied 40% from its COVID lows. "
                        "They confirm trends that have already begun — they do not predict them. "
                        "In choppy sideways markets they generate frequent false signals.",
                        s['Warn'])]

    story += [Spacer(1,0.4*cm), P("1.4  Daily % Change", 'H2'),
              P("Formula: ((today_close − yesterday_close) / yesterday_close) × 100", 'Body'),
              P("A large single-day move (above your configured threshold, default 3%) is a flag "
                "that <b>something happened</b> — earnings, news, analyst action, sector rotation, "
                "or unusual volume. It is a <b>prompt to investigate</b>, not a trading signal by itself. "
                "The other indicators tell you the context of that move.", 'Body'),
              PageBreak()]

    # Chapter 2
    story += [P("Chapter 2: The Four Assessment Labels", 'H1'), hr(),
              P("The assessment system is <b>fully deterministic</b> — no ML, no randomness, "
                "no AI. Each indicator casts a vote; the label comes from the vote tally.", 'Body'),
              tbl([["Signal fired","Vote cast"],
                   ["RSI >= overbought threshold (default 70)","+ 1 bull"],
                   ["RSI <= oversold threshold (default 30)","+ 1 bear"],
                   ["Golden cross today","+ 1 bull"],
                   ["Death cross today","+ 1 bear"],
                   ["Large daily move","Noted in rationale — no vote"]],
                  [9*cm, 6.5*cm]),
              Spacer(1,0.3*cm),
              tbl([["Label","Bull votes","Bear votes","Meaning"],
                   ["Technically strong","> 0","0","All signals bullish"],
                   ["Technically weak","0","> 0","All signals bearish"],
                   ["Looks stretched","> 0","> 0","Conflicting signals"],
                   ["Mixed / neutral","0","0","No signals fired today"]],
                  [4.5*cm, 2.5*cm, 2.5*cm, 6*cm]),
              Spacer(1,0.4*cm)]

    labels = [
        ("Technically Strong", "#1b5e20", "#e8f5e9",
         "RSI overbought and/or golden cross fired; no bearish signals.",
         "Momentum indicators align bullishly. The stock has risen fast recently or "
         "its medium-term trend just overtook the long-term average.",
         "Does NOT mean 'will keep rising.' Overbought can persist in strong uptrends or "
         "reverse sharply. Always check fundamentals and news."),
        ("Technically Weak", "#b71c1c", "#ffebee",
         "RSI oversold and/or death cross fired; no bullish signals.",
         "Momentum indicators align bearishly. Heavy recent selling or medium-term trend "
         "has fallen below the long-term average.",
         "Does NOT mean 'will keep falling.' Oversold can mean mean-reversion opportunity "
         "OR continued decline. Context matters enormously."),
        ("Looks Stretched", "#e65100", "#fff3e0",
         "Both bullish AND bearish signals fire simultaneously.",
         "Example: RSI overbought (bull) + death cross (bear). Or RSI oversold (bear) + "
         "golden cross (bull). The technical picture is genuinely contradictory.",
         "Often an inflection point. Shorter and longer-term timeframes disagree. "
         "Warrants the most careful investigation of all four labels."),
        ("Mixed / Neutral", "#37474f", "#eceff1",
         "No RSI thresholds breached and no crossover today.",
         "No notable technical condition by your configured thresholds. "
         "The most common label — most stocks on most days.",
         "Does NOT mean safe, good, or boring — just that the screener's specific "
         "conditions weren't met. Adjust thresholds in Settings if too many are neutral."),
    ]
    for name, hdr_col, bg_col, when, means, important in labels:
        head_style = ParagraphStyle('lh', parent=s['Body'], textColor=colors.HexColor(hdr_col), fontSize=11)
        t = Table([[Paragraph(f"<b>{name}</b>", head_style)]], [15.5*cm])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor(bg_col)),
                                ('LEFTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),5),
                                ('BOTTOMPADDING',(0,0),(-1,-1),5),
                                ('BOX',(0,0),(-1,-1),0.5,colors.HexColor(hdr_col))]))
        body_t = Table([
            [Paragraph("<b>When it fires:</b> " + when, s['Body'])],
            [Paragraph("<b>What it means:</b> " + means, s['Body'])],
            [Paragraph("<b>Important:</b> " + important, s['Body'])],
        ], [15.5*cm])
        body_t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor(bg_col)),
                                     ('LEFTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),3),
                                     ('BOTTOMPADDING',(0,0),(-1,-1),3),
                                     ('BOX',(0,0),(-1,-1),0.5,colors.HexColor(hdr_col))]))
        story += [KeepTogether([t, body_t, Spacer(1,0.3*cm)])]

    story.append(PageBreak())

    # Chapter 3
    story += [P("Chapter 3: How the Indicators Relate", 'H1'), hr(),
              P("3.1  RSI and Price Trend (SMA Relationship)", 'H2'),
              tbl([["Price vs 200-day SMA","RSI","Combined picture","Assessment likely"],
                   ["Above (long-term uptrend)",">=70 (overbought)","Strong momentum in uptrend","Technically strong"],
                   ["Above (long-term uptrend)","<=30 (oversold)","Dip in uptrend — short-term weakness","Technically weak (but may reverse)"],
                   ["Below (long-term downtrend)",">=70 (overbought)","Sharp bounce in downtrend — dead cat?","Technically strong (high risk)"],
                   ["Below (long-term downtrend)","<=30 (oversold)","Downtrend with heavy selling","Technically weak — strongest bear"]],
                  [4*cm, 3.5*cm, 5*cm, 3.5*cm]),
              Spacer(1,0.4*cm),
              P("3.2  RSI and MA Crossovers: Timeframe Mismatch", 'H2'),
              P("RSI responds to the <b>last ~14 days</b>. MA crossovers reflect <b>weeks-to-months</b> "
                "of price history. They naturally disagree at market turning points — that is exactly "
                "when you get a <b>'Looks stretched'</b> label.", 'Body'),
              tbl([["Scenario","RSI","MA Cross","Label","What it suggests"],
                   ["Bounce in downtrend","Overbought","Death cross","Looks stretched","Short-term rally within longer downtrend"],
                   ["Trend turning up","Overbought","Golden cross","Technically strong","Momentum confirms new uptrend"],
                   ["Dip in uptrend","Oversold","Golden cross","Looks stretched","Short-term weakness in new uptrend"],
                   ["Trend turning down","Oversold","Death cross","Technically weak","Momentum confirms new downtrend"]],
                  [4.5*cm, 2.5*cm, 2.5*cm, 3.5*cm, 3*cm]),
              Spacer(1,0.4*cm),
              P("3.3  Large Daily Move in Context", 'H2'),
              tbl([["Large move","RSI after","vs 200-day SMA","Context"],
                   ["Down","Oversold (<30)","Below","Selling into downtrend — multiple bear signals"],
                   ["Down","Neutral (30-70)","Above","Dip in uptrend — may be noise"],
                   ["Up","Overbought (>70)","Above + golden cross","Breakout with multiple confirming signals"],
                   ["Up","Neutral (30-70)","Below","Bounce in downtrend — investigate carefully"]],
                  [2.5*cm, 3.5*cm, 3.5*cm, 6*cm]),
              PageBreak()]

    # Chapter 4
    story += [P("Chapter 4: Common Misreadings", 'H1'), hr()]
    misreadings = [
        ("RSI < 30, so the stock will bounce",
         "RSI can stay below 30 for months in a severe downtrend (many stocks in 2022). "
         "Oversold means selling pressure is high — not that a reversal is imminent."),
        ("Golden cross appeared — time to buy",
         "Crossovers are backward-looking. By the time a golden cross prints, "
         "the rally may be 20-40% old. It confirms a trend already in progress."),
        ("'Technically strong' means it's a good investment",
         "A label reflects today's technical conditions only. It says nothing about "
         "valuation, earnings quality, debt, competitive position, or macro risk."),
        ("'Technically weak' means I should sell",
         "'Technically weak' in a long-term uptrend is often a buying opportunity "
         "for mean-reversion strategies. The same signal means different things "
         "depending on your timeframe and strategy."),
        ("More signals = more certain",
         "Multiple confirming signals increase the probability of a condition, "
         "not its certainty. All technical signals have significant failure rates."),
    ]
    for wrong, right in misreadings:
        story.append(KeepTogether([
            tbl([[Paragraph(f"<b>Misreading:</b> \"{wrong}\"", s['Body']),
                  Paragraph(f"<b>Reality:</b> {right}", s['Body'])]], [6*cm, 9.5*cm], header=False),
            Spacer(1,0.15*cm)]))

    story += [Spacer(1,0.4*cm), P("Chapter 5: Threshold Configuration", 'H1'), hr(),
              tbl([["Setting","Default","What it controls"],
                   ["daily_move_pct","3.0%","Flags tickers where |daily change| >= this"],
                   ["rsi_oversold","30","Bear vote + alert when RSI at or below this"],
                   ["rsi_overbought","70","Bull vote + alert when RSI at or above this"],
                   ["ma_short","50 days","Short SMA window"],
                   ["ma_long","200 days","Long SMA window (needs 200+ bars of data)"]],
                  [4*cm, 2.5*cm, 9*cm]),
              Spacer(1,0.3*cm),
              Paragraph("<b>Reset your thresholds.</b> The test values in the DB "
                        "(rsi_oversold: 99, daily_move_pct: 0.1) flag nearly everything. "
                        "Open the Settings tab and set: daily_move_pct=3.0, rsi_oversold=30, rsi_overbought=70.",
                        s['Warn']),
              Spacer(1,0.5*cm),
              P("Appendix: Glossary", 'H1'), hr()]
    glossary = [
        ("Momentum","The speed of recent price movement. High RSI = high upward momentum."),
        ("Mean reversion","The tendency of extreme moves to return toward average. Basis for oversold strategies."),
        ("Lagging indicator","Reflects past price history. RSI and SMA are both lagging — they do not predict."),
        ("Oversold","RSI in the 0-30 zone. Selling pressure is high. Not a guaranteed reversal."),
        ("Overbought","RSI in the 70-100 zone. Buying pressure is high. Not a guaranteed pullback."),
        ("Support","A price level where demand has historically emerged — often near the 200-day SMA."),
        ("Resistance","A price level where supply has historically appeared and slowed rallies."),
    ]
    story.append(tbl([["Term","Definition"]] + glossary, [3.5*cm, 12*cm]))
    story += [Spacer(1,0.5*cm),
              Paragraph("DISCLAIMER: This document is for educational purposes only. It does not constitute "
                        "financial advice or a recommendation to buy or sell any security. Past technical "
                        "patterns do not guarantee future results. Always consult a qualified financial "
                        "advisor before making investment decisions.", s['Footer'])]

    doc.build(story, onFirstPage=footer_cb, onLaterPages=footer_cb)
    print(f"PDF 1 written: {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# PDF 2 — Architecture & Code Guide
# ═══════════════════════════════════════════════════════════════════════════════
def build_pdf2(path):
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2.5*cm)
    s = base_styles()
    P = lambda txt, style='Body': Paragraph(txt, s[style])
    story = []

    # Cover
    story += [Spacer(1,1.5*cm),
              P("watchlist-monitor<br/>Architecture &amp; Code Guide", 'Title2'),
              P("A complete walkthrough of every module, data flow, API, frontend and deployment", 'Sub'),
              hr(), Spacer(1,0.3*cm),
              P("This document explains how watchlist-monitor is built — what each file does, "
                "how data flows from a market close to your email/screen, and how all the pieces "
                "fit together. Aimed at developers and power users who want to understand, extend "
                "or debug the system.", 'Body'),
              PageBreak()]

    # Chapter 1 — Overview
    story += [P("Chapter 1: Project Overview", 'H1'), hr(),
              P("watchlist-monitor is a <b>personal stock alert and screener tool</b> built on "
                "Python. It fetches real market data, computes technical indicators, evaluates "
                "configurable trigger conditions, surfaces research candidates, and delivers an "
                "HTML report by email — all running free on GitHub Actions or locally via a "
                "FastAPI web UI.", 'Body'),
              P("Core design principles:", 'H2'),
              P("1. <b>Alert tool, not prediction tool.</b> Every output describes current technical "
                "conditions. Nothing forecasts prices.", 'Li'),
              P("2. <b>No code changes needed for normal use.</b> All user configuration lives in "
                "config.yaml or the Settings tab.", 'Li'),
              P("3. <b>One bad ticker never aborts the run.</b> Every fetch and evaluate call is "
                "wrapped; errors are surfaced per-ticker, not globally.", 'Li'),
              P("4. <b>Pure functions at the core.</b> indicators.py, portfolio.py, assessment.py, "
                "screener.py, themes.py — all side-effect-free and fully unit-tested.", 'Li'),
              Spacer(1,0.3*cm),
              P("Technology Stack", 'H2'),
              tbl([["Layer","Technology","Purpose"],
                   ["Data fetch","yfinance (0.2.x)","Daily OHLC price history from Yahoo Finance"],
                   ["Indicators","numpy + pandas","RSI, SMA, daily %, MA crossover"],
                   ["Persistence","SQLite (stdlib)","Watchlist, portfolio, settings for the UI"],
                   ["Backend API","FastAPI + uvicorn","REST JSON API serving the web frontend"],
                   ["Frontend","Vanilla JS + Chart.js","SPA — no build step, no npm"],
                   ["Scheduler","APScheduler","In-app daily email job"],
                   ["Email","smtplib (stdlib)","SMTP send or stdout dry-run"],
                   ["AI notes","InvestorMate + OpenAI","Optional context notes via Investor.ask()"],
                   ["CI/CD","GitHub Actions","Free weekday cron, no server needed"],
                   ["Config","PyYAML","Human-editable config.yaml"],
                   ["Tests","pytest","85 tests covering all pure modules + API"]],
                  [3*cm, 4.5*cm, 8*cm]),
              PageBreak()]

    # Chapter 2 — File map
    story += [P("Chapter 2: File Map", 'H1'), hr(),
              tbl([["File / Directory","Role"],
                   ["config.yaml","User-editable watchlist, thresholds, AI settings. Seeded into SQLite on first UI launch."],
                   ["monitor/__init__.py","Empty — marks monitor/ as a Python package."],
                   ["monitor/indicators.py","Pure functions: wilder_rsi(), sma(), daily_pct_change(), ma_crossover(). Zero I/O."],
                   ["monitor/triggers.py","evaluate(ticker, hist, cfg) — runs all indicators, returns snapshot + alert strings."],
                   ["monitor/assessment.py","assess(result, position, cfg) — deterministic label from indicator votes. Zero I/O."],
                   ["monitor/core.py","fetch_history(), fetch_many() (bulk), scan() — the shared pipeline. 15-min cache."],
                   ["monitor/portfolio.py","compute_position(), summarize() — pure P&L math. Zero I/O."],
                   ["monitor/screener.py","build_ideas() — ranks tickers by signal count. Used by Daily Ideas + Market Scan."],
                   ["monitor/themes.py","THEME_TICKERS map + expand_interests() — theme name -> ticker list."],
                   ["monitor/universe.py","Index constituent lists: Dow30, Nasdaq100, NIFTY50, SENSEX30."],
                   ["monitor/store.py","SQLite CRUD for holdings, interests, settings. build_cfg() reconstructs config dict."],
                   ["monitor/ai_notes.py","get_ai_notes() — calls InvestorMate Investor.ask(). Skips gracefully if not configured."],
                   ["monitor/emailer.py","build_html() + send_or_print() — HTML report, SMTP send or stdout dry-run."],
                   ["monitor/run.py","CLI entry point: python -m monitor.run. Thin wrapper around core.scan + emailer."],
                   ["webapp/__init__.py","Empty — marks webapp/ as a package."],
                   ["webapp/main.py","FastAPI app: all /api/* routes, APScheduler setup, static file mount."],
                   ["webapp/static/index.html","Single-page app shell. Six tabs. Chart.js via CDN."],
                   ["webapp/static/app.js","All frontend logic: tab routing, API calls, Chart.js rendering."],
                   ["webapp/static/styles.css","Dark-theme CSS. No framework."],
                   [".github/workflows/daily.yml","Weekday 21:30 UTC cron + manual dispatch. Runs monitor/run.py."],
                   ["tests/","85 pytest tests: indicators, triggers, portfolio, assessment, screener, themes, store, API."],
                   ["watchlist.db","SQLite database (git-ignored). Created on first uvicorn startup."]],
                  [5.5*cm, 10*cm]),
              PageBreak()]

    # Chapter 3 — Data flow
    story += [P("Chapter 3: Data Flow — From Market Close to Screen/Email", 'H1'), hr(),
              P("The pipeline is identical whether triggered by the CLI, GitHub Actions, "
                "the web UI dashboard, or the APScheduler daily job:", 'Body'),
              tbl([["Step","Where","What happens"],
                   ["1. Load config","store.build_cfg() or config.yaml","Tickers, thresholds, AI flag assembled into a cfg dict"],
                   ["2. Fetch history","core.fetch_history() / fetch_many()","~13 months of daily OHLC via yfinance. 15-min cache."],
                   ["3. Compute indicators","indicators.py (called by triggers.py)","RSI, SMA50, SMA200, daily %, MA crossover"],
                   ["4. Evaluate triggers","triggers.evaluate()","Compare indicators to thresholds; build alert strings"],
                   ["5. Assess","assessment.py assess()","Vote-based label: strong / weak / stretched / neutral"],
                   ["6. Portfolio P&L","portfolio.py (UI/API only)","Market value and unrealized P&L per holding"],
                   ["7. AI notes (optional)","ai_notes.get_ai_notes()","Investor.ask() per ticker if enabled + key present"],
                   ["8. Build report","emailer.build_html()","HTML table with all ticker rows, alerts, AI notes"],
                   ["9. Deliver","emailer.send_or_print()","SMTP if all env vars set; stdout dry-run otherwise"]],
                  [1.5*cm, 4.5*cm, 9.5*cm]),
              Spacer(1,0.4*cm),
              P("The Screener path (Daily Ideas / Market Scan) inserts between steps 5 and 8:", 'H3'),
              P("screener.build_ideas(results, cfg) groups tickers by which signals fired "
                "(oversold, overbought, golden cross, death cross, big movers) and ranks them "
                "by signal count + daily move magnitude. group_limit caps per-group items "
                "for the large index scans.", 'Body'),
              PageBreak()]

    # Chapter 4 — Module deep-dives
    story += [P("Chapter 4: Module Deep-Dives", 'H1'), hr()]

    modules = [
        ("monitor/indicators.py — Pure Indicator Math",
         [("wilder_rsi(prices, period=14)",
           "Returns a pd.Series of RSI values. First 'period' values are NaN (insufficient data). "
           "Uses explicit Wilder smoothing loop (not ewm) for correctness. Handles flat prices "
           "(both avg_g=0 and avg_l=0) by returning NaN rather than 100."),
          ("sma(prices, period)",
           "Rolling mean. Returns NaN for the first period-1 values. One line: prices.rolling(period).mean()."),
          ("daily_pct_change(prices)",
           "pct_change() × 100. First value is always NaN."),
          ("ma_crossover(prices, short_period, long_period)",
           "Drops NaN from both SMA series, aligns them, checks the last two bars for a "
           "position change. Returns 'golden', 'death', or None.")]),
        ("monitor/triggers.py — Trigger Evaluation",
         [("evaluate(ticker, hist, cfg)",
           "Entry point for a single ticker. Calls all four indicator functions, compares to "
           "thresholds from cfg['triggers'], builds a list of human-readable alert strings, "
           "and returns a result dict: {ticker, price, change_pct, rsi, ma_cross, alerts, error}. "
           "Any exception sets error= and returns gracefully.")]),
        ("monitor/assessment.py — Signal Assessment",
         [("assess(result, position=None, cfg=None)",
           "Pure function. Reads rsi, ma_cross, change_pct from result. Assigns bull/bear votes. "
           "Label = strong (bull only), weak (bear only), stretched (both), neutral (neither). "
           "If a portfolio position is passed, adds P&L context. Never emits buy/sell/hold verbs — "
           "tested explicitly in test_assessment.py.")]),
        ("monitor/core.py — Shared Scan Pipeline",
         [("fetch_history(ticker, use_cache=True)",
           "Single-ticker fetch via yf.Ticker.history(). Stores result in _HIST_CACHE with a "
           "15-minute TTL. Prevents re-fetching the same ticker within a session."),
          ("fetch_many(tickers, refresh=False)",
           "Bulk fetch via yf.download(group_by='ticker', threads=True). Returns a dict of "
           "DataFrames. Used by market_scan for 30–100 ticker batches. Honours the same cache."),
          ("scan(cfg, tickers=None, histories=None, refresh=False, progress=None)",
           "Loops tickers, fetches (or uses pre-fetched histories dict), calls evaluate(). "
           "Never raises — errors are captured per-ticker. Optional progress callback for CLI logging.")]),
        ("monitor/store.py — SQLite Persistence",
         [("init_db()",
           "Creates tables (holdings, interests, settings) if absent. Calls _seed_if_empty() "
           "which imports config.yaml on first run."),
          ("build_cfg()",
           "Reconstructs the cfg dict that core.scan + ai_notes expect: tickers from "
           "watchlist_tickers() (interests expanded via themes + holdings), triggers and "
           "ai_analysis from settings table."),
          ("update_settings(patch)",
           "Shallow-merges top-level keys; nested dicts (triggers, ai_analysis) merge one level. "
           "Stored as JSON per key in the settings table.")]),
        ("monitor/screener.py — Screener",
         [("build_ideas(results, cfg, ai_notes={}, top_n=5, group_limit=None)",
           "Iterates results, assigns each ticker to one or more signal groups (oversold, overbought, "
           "golden, death, movers). Ranks all flagged tickers by (signal_count DESC, |change_pct| DESC). "
           "Returns {top: [...], groups: [...], counts: {...}}. group_limit caps per-group items "
           "for large scans (15 per group for index scans).")]),
    ]
    for title, funcs in modules:
        story.append(P(title, 'H2'))
        rows = [["Function / method", "What it does"]]
        for fn, desc in funcs:
            rows.append([Paragraph(f"<b>{fn}</b>", s['Code']), Paragraph(desc, s['Body'])])
        story.append(tbl(rows, [5.5*cm, 10*cm]))
        story.append(Spacer(1, 0.3*cm))

    story.append(PageBreak())

    # Chapter 5 — Web app
    story += [P("Chapter 5: The Web Application", 'H1'), hr(),
              P("Start with: <b>uvicorn webapp.main:app --host 127.0.0.1 --port 8000</b>", 'Code'),
              Spacer(1,0.2*cm),
              P("5.1  FastAPI Routes", 'H2'),
              tbl([["Method + Path","Purpose"],
                   ["GET /api/dashboard","Scan all interests+holdings, enrich with assessment+AI notes. ?refresh=1 bypasses cache."],
                   ["GET /api/ideas","Daily Ideas screener for user's own universe."],
                   ["GET /api/universe","Returns index metadata (name, currency symbol, ticker count)."],
                   ["GET /api/market-scan?index=X","Bulk-fetch index constituents, run screener, return flagged names (top 8, groups capped at 15)."],
                   ["GET /api/ticker/{symbol}","Deep-dive: snapshot, assessment, 90-day price/SMA/RSI chart series, AI note, SMA relationship label."],
                   ["GET+POST /api/holdings","List or create holdings."],
                   ["PUT+DELETE /api/holdings/{id}","Update or remove a holding."],
                   ["GET+POST /api/interests","List (with available themes) or add an interest."],
                   ["DELETE /api/interests/{id}","Remove an interest."],
                   ["GET+PUT /api/settings","Read or update settings (triggers, ai_analysis, schedule, always_send_summary)."],
                   ["POST /api/email/preview","Returns HTML string for preview in an iframe."],
                   ["POST /api/email/send","Runs the daily report job (SMTP or stdout dry-run)."],
                   ["POST /api/export-config","Writes current store state back to config.yaml for the Actions cron."],
                   ["GET /","Serves webapp/static/index.html."],
                   ["/* (static)","Serves CSS, JS, any other static assets."]],
                  [5.5*cm, 10*cm]),
              Spacer(1,0.4*cm),
              P("5.2  In-App Scheduler (APScheduler)", 'H2'),
              P("A BackgroundScheduler starts on app startup. The Settings tab lets you toggle "
                "it on/off and set hour/minute. When enabled, a cron job runs weekdays at the "
                "configured time, calling the same pipeline as the CLI: scan → assess → build_html "
                "→ send_or_print. Reschedules itself on every PUT /api/settings.", 'Body'),
              Spacer(1,0.3*cm),
              P("5.3  Frontend — Six Tabs", 'H2'),
              tbl([["Tab","What it shows / does"],
                   ["Dashboard","Sortable table of all interests+holdings. Price, daily%, RSI, MA cross, alerts, assessment, AI note. Refresh button."],
                   ["Daily Ideas","Research candidates from your own universe. Top-ranked + by-signal groups. Refreshes on demand."],
                   ["Market Scan","Pick an index (Dow30/Nasdaq100/NIFTY50/SENSEX30) and scan. Currency-aware ($/Rs). Top 8 + groups."],
                   ["Ticker Inspector","Type any ticker (US or Indian). Shows metric cards, 90-day price+SMA chart, RSI chart, alerts, assessment, AI note."],
                   ["Portfolio","Add/edit/delete holdings. Live market value + unrealized P&L per holding and in total."],
                   ["Interests","Manage individual tickers and themes. Available themes dropdown. Chips list with delete."],
                   ["Settings","Trigger thresholds, AI toggle, scheduler config, email preview/send, Export to config.yaml."]],
                  [3.5*cm, 12*cm]),
              Spacer(1,0.3*cm),
              P("5.4  Chart.js Integration (Ticker Inspector)", 'H2'),
              P("Two Chart.js line charts are rendered per ticker inspection:", 'Body'),
              P("<b>Price chart:</b> 90 sessions of closing price (blue) + SMA50 (gold dashed) + SMA200 (red dashed). "
                "The SMA series have NaN values for the first period-1 bars, passed as null to Chart.js.", 'Li'),
              P("<b>RSI chart:</b> 90 sessions of RSI(14) (green) + static 70-line (red dashed) + static 30-line "
                "(amber dashed). Y-axis clamped 0–100.", 'Li'),
              P("Both charts are destroyed and recreated on each new inspection to prevent canvas reuse errors.", 'Li'),
              PageBreak()]

    # Chapter 6 — GitHub Actions
    story += [P("Chapter 6: GitHub Actions Deployment", 'H1'), hr(),
              P("File: <b>.github/workflows/daily.yml</b>", 'Code'),
              tbl([["Property","Value"],
                   ["Trigger","Weekday cron at 21:30 UTC (~4:30 PM ET) + manual workflow_dispatch"],
                   ["Runner","ubuntu-latest (free GitHub Actions)"],
                   ["Python","3.11 with pip cache"],
                   ["Secrets needed","SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_TO (all required for email); OPENAI_API_KEY (optional)"],
                   ["Dry-run","If any SMTP secret is missing, the report prints to the Actions log instead of emailing"],
                   ["Config source","Reads config.yaml from the repo. Use 'Export to config.yaml' in Settings then commit to sync."]],
                  [3.5*cm, 12*cm], header=False),
              Spacer(1,0.4*cm),
              P("Setting up GitHub Secrets:", 'H2'),
              P("Repository → Settings → Secrets and variables → Actions → New repository secret", 'Li'),
              P("Add each of: SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASS (Gmail app password), MAIL_TO", 'Li'),
              P("For Gmail: enable 2FA → myaccount.google.com/apppasswords → generate a 16-char app password", 'Li'),
              PageBreak()]

    # Chapter 7 — Testing
    story += [P("Chapter 7: Test Suite (85 tests)", 'H1'), hr(),
              P("Run with: <b>python -m pytest tests/ -v</b>", 'Code'),
              tbl([["Test file","What it covers"],
                   ["test_indicators.py","19 tests: SMA (4), Wilder RSI (6), daily% (4), MA crossover (5). Pure math, deterministic data."],
                   ["test_triggers.py","17 tests: snapshot correctness, error cases, all four alert types (move, RSI, crossover)."],
                   ["test_portfolio.py","7 tests: P&L gain/loss/zero-cost, summarize() with missing prices."],
                   ["test_assessment.py","8 tests: each label, position context, and a directive-language assertion (no buy/sell/hold)."],
                   ["test_screener.py","7 tests: grouping, sorting, ranking, error exclusion, directive-language assertion."],
                   ["test_themes.py","4 tests: theme expansion, de-duplication, unknown theme, suffix correctness."],
                   ["test_store.py","12 tests: holdings CRUD, interests deduplication, settings deep merge, build_cfg() assembly."],
                   ["test_api.py","11 tests: full FastAPI TestClient tests for interests, holdings, portfolio P&L, dashboard assessment, market scan (offline with monkeypatched fetch_many)."],
                   ["test_universe.py","6 tests: index presence, India .NS/.BO suffixes, US no-suffix, currency symbols, count consistency."]],
                  [4.5*cm, 11*cm]),
              Spacer(1,0.4*cm),
              Paragraph("<b>Key testing patterns:</b><br/>"
                        "• Pure modules tested with synthetic pandas Series — no network calls.<br/>"
                        "• FastAPI tests use TestClient with monkeypatched fetch_history / fetch_many — fully offline.<br/>"
                        "• Each test DB uses tmp_path (pytest fixture) — no shared state between tests.<br/>"
                        "• Directive-language tests: assert 'buy'/'sell'/'hold'/'price target'/'will rise'/'will fall' "
                        "never appear in any assessment or screener output.",
                        s['Callout']),
              PageBreak()]

    # Chapter 8 — Extension guide
    story += [P("Chapter 8: How to Extend the Project", 'H1'), hr(),
              P("8.1  Adding a new indicator", 'H2'),
              P("1. Add a pure function to <b>monitor/indicators.py</b> following the pd.Series → pd.Series pattern.", 'Li'),
              P("2. Add unit tests to <b>tests/test_indicators.py</b> using synthetic data.", 'Li'),
              P("3. Call it inside <b>monitor/triggers.py evaluate()</b> and add a threshold check.", 'Li'),
              P("4. Optionally add a bull/bear vote in <b>monitor/assessment.py assess()</b>.", 'Li'),
              P("5. Expose the new value in the result dict — the UI and screener pick it up automatically.", 'Li'),
              Spacer(1,0.3*cm),
              P("8.2  Adding a new index to the Market Scan", 'H2'),
              P("1. Add the ticker list and metadata to the INDEXES dict in <b>monitor/universe.py</b>.", 'Li'),
              P("2. Indian NSE tickers use a <b>.NS</b> suffix; BSE use <b>.BO</b>. "
                "Other markets use Yahoo Finance's suffix convention.", 'Li'),
              P("3. No other changes needed — the frontend reads index_meta() dynamically.", 'Li'),
              Spacer(1,0.3*cm),
              P("8.3  Adding a new theme", 'H2'),
              P("Add a key→list[str] entry to THEME_TICKERS in <b>monitor/themes.py</b>. "
                "The Interests tab picks it up automatically via GET /api/interests.", 'Li'),
              Spacer(1,0.3*cm),
              P("8.4  Adding a new API endpoint", 'H2'),
              P("Add a route function in <b>webapp/main.py</b> following the existing pattern. "
                "FastAPI validates types automatically via Pydantic models.", 'Li'),
              P("Add corresponding TestClient tests to <b>tests/test_api.py</b> using the "
                "monkeypatched client fixture.", 'Li'),
              Spacer(1,0.5*cm),
              P("Out of Scope (by design)", 'H2'),
              tbl([["Feature","Why excluded"],
                   ["Trade execution / brokerage API","Explicitly never — this tool never places trades"],
                   ["Price forecasting / ML predictions","Tool is alert-based; predictions would contradict all disclaimers"],
                   ["Multi-user / authentication","Personal tool; adding auth is straightforward with FastAPI middleware if needed"],
                   ["Real-time intraday data","yfinance provides daily; intraday requires a paid data feed"],
                   ["Hosted cloud deployment","Docker + cloud deployment can be added; current scope is local/Actions"]],
                  [4.5*cm, 11*cm]),
              Spacer(1,0.5*cm),
              Paragraph("DISCLAIMER: This document is for technical reference only. watchlist-monitor "
                        "is an informational tool — it does not provide financial advice, does not "
                        "forecast prices, and never places trades. Always consult a qualified financial "
                        "advisor before making investment decisions.", s['Footer'])]

    doc.build(story, onFirstPage=footer_cb, onLaterPages=footer_cb)
    print(f"PDF 2 written: {path}")


if __name__ == "__main__":
    build_pdf1(r"G:\Claude\watchlist-monitor\docs\indicators-guide.pdf")
    build_pdf2(r"G:\Claude\watchlist-monitor\docs\architecture-guide.pdf")
    print("Both PDFs complete.")
