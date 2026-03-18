"""
Enjin Analisa Teknikal — SahamBot MY
Adaptive: 5–10 candle, multi-timeframe
"""

import math

# ─────────────────────────────────────────
# CANDLE COUNT INFO — Kesan setiap pilihan
# ─────────────────────────────────────────
CANDLE_INFO = {
    5: {
        "available": [
            "Candlestick Pattern (Marubozu, Hammer, Doji dll)",
            "Support & Resistance (Pivot asas)",
            "Moving Average MA5",
            "Trend Direction",
        ],
        "limited": [
            "RSI — estimated, kurang tepat",
            "MA berbilang period — terhad",
        ],
        "unavailable": [
            "MACD — perlukan lebih data",
            "Bollinger Bands — perlukan min 10 candle",
            "Fibonacci Retracement",
        ],
        "suitable": "Analisa pattern & arah trend ringkas. Sesuai untuk keputusan cepat.",
    },
    6: {
        "available": [
            "Candlestick Pattern",
            "Support & Resistance",
            "MA5, MA6",
            "Trend Direction",
            "RSI (lebih baik dari 5 candle)",
        ],
        "limited": [
            "RSI — masih estimated",
            "MACD — lemah",
        ],
        "unavailable": [
            "Bollinger Bands",
            "Fibonacci",
        ],
        "suitable": "Sedikit lebih baik dari 5 candle. Pattern detection lebih solid.",
    },
    7: {
        "available": [
            "Candlestick Pattern",
            "Support & Resistance",
            "MA5, MA7",
            "Trend Direction",
            "RSI (acceptable)",
            "Volume Analysis",
        ],
        "limited": [
            "MACD — weak signal",
            "Bollinger Bands — kurang tepat",
        ],
        "unavailable": [
            "Fibonacci Retracement",
        ],
        "suitable": "Balance antara mudah input dan ketepatan. Sweet spot untuk kebanyakan trader.",
    },
    8: {
        "available": [
            "Candlestick Pattern",
            "Support & Resistance",
            "MA5, MA8",
            "RSI (baik)",
            "Volume Analysis",
            "MACD (estimated)",
        ],
        "limited": [
            "Bollinger Bands — acceptable",
            "Fibonacci — terhad",
        ],
        "unavailable": [],
        "suitable": "Analisa teknikal yang lebih lengkap. RSI mula reliable.",
    },
    9: {
        "available": [
            "Candlestick Pattern",
            "Support & Resistance (advanced)",
            "MA5, MA9",
            "RSI (reliable)",
            "Volume Analysis",
            "MACD (lebih baik)",
            "Bollinger Bands (acceptable)",
        ],
        "limited": [
            "Fibonacci — boleh guna tapi terhad",
        ],
        "unavailable": [],
        "suitable": "Analisa hampir lengkap. Semua indicator utama tersedia.",
    },
    10: {
        "available": [
            "Candlestick Pattern (penuh)",
            "Support & Resistance (advanced)",
            "MA5, MA10",
            "RSI (paling tepat)",
            "Volume Analysis (penuh)",
            "MACD (reliable)",
            "Bollinger Bands (reliable)",
            "Fibonacci Retracement",
            "Overall Confluence Signal",
        ],
        "limited": [],
        "unavailable": [],
        "suitable": "Analisa teknikal paling lengkap dan paling tepat. Highly recommended.",
    },
}


# ─────────────────────────────────────────
# CALCULATION FUNCTIONS
# ─────────────────────────────────────────

def calc_rsi(closes: list) -> float:
    if len(closes) < 2:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains) / len(gains) if gains else 0.001
    avg_loss = sum(losses) / len(losses) if losses else 0.001
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def interpret_rsi(rsi: float) -> str:
    if rsi >= 70: return "⚠️ Overbought — pertimbangkan ambil untung"
    if rsi >= 60: return "🟢 Bullish"
    if rsi >= 40: return "🟡 Neutral"
    if rsi >= 30: return "🟠 Bearish"
    return "🔴 Oversold — potential reversal bullish"

def calc_ma(closes: list, period: int) -> float:
    if len(closes) < period:
        period = len(closes)
    return round(sum(closes[-period:]) / period, 3)

def calc_macd(closes: list):
    if len(closes) < 3:
        return 0, 0, 0
    # Simplified EMA
    def ema(data, period):
        if len(data) < period:
            period = len(data)
        k = 2 / (period + 1)
        ema_val = sum(data[:period]) / period
        for price in data[period:]:
            ema_val = price * k + ema_val * (1 - k)
        return round(ema_val, 4)

    fast = min(3, len(closes) - 1)
    slow = min(5, len(closes) - 1)
    signal_p = min(2, len(closes) - 1)

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = round(ema_fast - ema_slow, 4)
    signal_line = round(macd_line * 0.9, 4)
    histogram = round(macd_line - signal_line, 4)
    return macd_line, signal_line, histogram

def calc_bollinger(closes: list):
    if len(closes) < 5:
        return None, None, None
    period = min(10, len(closes))
    ma = sum(closes[-period:]) / period
    variance = sum((c - ma) ** 2 for c in closes[-period:]) / period
    std = math.sqrt(variance)
    upper = round(ma + 2 * std, 3)
    lower = round(ma - 2 * std, 3)
    return round(ma, 3), upper, lower

def calc_sr(highs: list, lows: list, closes: list):
    pivot = (max(highs) + min(lows) + closes[-1]) / 3
    r1 = round((2 * pivot) - min(lows), 3)
    s1 = round((2 * pivot) - max(highs), 3)
    r2 = round(pivot + (max(highs) - min(lows)), 3)
    s2 = round(pivot - (max(highs) - min(lows)), 3)
    return round(pivot, 3), r1, s1, r2, s2

def calc_fibonacci(highs: list, lows: list):
    high = max(highs)
    low = min(lows)
    diff = high - low
    levels = {
        "0%": round(high, 3),
        "23.6%": round(high - diff * 0.236, 3),
        "38.2%": round(high - diff * 0.382, 3),
        "50%": round(high - diff * 0.5, 3),
        "61.8%": round(high - diff * 0.618, 3),
        "100%": round(low, 3),
    }
    return levels

def detect_candlestick(open_p, high, low, close) -> str:
    body = abs(close - open_p)
    candle_range = high - low
    if candle_range == 0:
        return "Flat Candle"
    body_ratio = body / candle_range
    upper_wick = high - max(open_p, close)
    lower_wick = min(open_p, close) - low

    if body_ratio >= 0.92:
        return "🟢 Bullish Marubozu" if close > open_p else "🔴 Bearish Marubozu"
    if body_ratio <= 0.1:
        return "⚪ Doji — ketidaktentuan pasaran"
    if lower_wick > body * 2 and upper_wick < body * 0.5:
        return "🔨 Hammer — potential bullish reversal"
    if upper_wick > body * 2 and lower_wick < body * 0.5:
        return "💫 Shooting Star — potential bearish reversal"
    if body_ratio >= 0.6:
        return "🟢 Strong Bullish Candle" if close > open_p else "🔴 Strong Bearish Candle"
    return "🟢 Bullish Candle" if close > open_p else "🔴 Bearish Candle"

def detect_engulfing(candles: list) -> str:
    if len(candles) < 2:
        return ""
    prev = candles[-2]
    curr = candles[-1]
    prev_body = abs(curr[3] - curr[0])
    curr_body = abs(prev[3] - prev[0])
    if curr[3] > curr[0] and prev[3] < prev[0] and curr_body > prev_body:
        return "🟢 Bullish Engulfing — signal reversal kuat"
    if curr[3] < curr[0] and prev[3] > prev[0] and curr_body > prev_body:
        return "🔴 Bearish Engulfing — signal reversal kuat"
    return ""

def volume_analysis(volumes: list) -> str:
    avg_vol = sum(volumes[:-1]) / max(len(volumes) - 1, 1)
    last_vol = volumes[-1]
    ratio = last_vol / avg_vol if avg_vol > 0 else 1

    if ratio >= 2.0:
        return f"🔥 Ultra High Volume ({ratio:.1f}x avg) — pergerakan besar"
    if ratio >= 1.5:
        return f"📈 High Volume ({ratio:.1f}x avg) — konfirmasi kuat"
    if ratio >= 0.8:
        return f"📊 Normal Volume ({ratio:.1f}x avg)"
    return f"📉 Low Volume ({ratio:.1f}x avg) — kurang momentum"

def trend_analysis(closes: list) -> str:
    if len(closes) < 3:
        return "🟡 Tidak dapat tentukan trend"
    rising = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
    falling = len(closes) - 1 - rising
    if rising > falling * 1.5:
        return "🟢 Uptrend — harga secara konsisten naik"
    if falling > rising * 1.5:
        return "🔴 Downtrend — harga secara konsisten turun"
    return "🟡 Sideways — harga bergerak mendatar"

def overall_signal(rsi, trend, macd_hist, last_close, ma) -> str:
    bull, bear = 0, 0
    if rsi > 55: bull += 1
    elif rsi < 45: bear += 1
    if "Uptrend" in trend: bull += 2
    elif "Downtrend" in trend: bear += 2
    if macd_hist > 0: bull += 1
    elif macd_hist < 0: bear += 1
    if last_close > ma: bull += 1
    else: bear += 1
    if bull > bear + 1: return "🟢 BUY / BULLISH"
    if bear > bull + 1: return "🔴 SELL / BEARISH"
    return "🟡 NEUTRAL / HOLD"


# ─────────────────────────────────────────
# MAIN ENGINE
# ─────────────────────────────────────────
def analisa_engine(candles: list, ticker: str, timeframe: str, tier: int) -> str:
    opens  = [c[0] for c in candles]
    highs  = [c[1] for c in candles]
    lows   = [c[2] for c in candles]
    closes = [c[3] for c in candles]
    vols   = [c[4] for c in candles]
    n      = len(candles)

    tf_label = {"D": "Daily", "W": "Weekly", "M": "Monthly", "Y": "Yearly"}
    last_open  = opens[-1]
    last_close = closes[-1]
    last_high  = highs[-1]
    last_low   = lows[-1]
    change     = last_close - last_open
    change_pct = (change / last_open) * 100

    # Core indicators (semua tier)
    rsi     = calc_rsi(closes)
    rsi_lbl = interpret_rsi(rsi)
    ma      = calc_ma(closes, min(5, n))
    trend   = trend_analysis(closes)
    pattern = detect_candlestick(last_open, last_high, last_low, last_close)
    engulf  = detect_engulfing(candles)
    pivot, r1, s1, r2, s2 = calc_sr(highs, lows, closes)

    # Header
    tier_label = "💎 PREMIUM" if tier == 1 else ("👑 PRO" if tier == 2 else "⚡ FREE")
    msg = (
        f"{tier_label} *Analisa: {ticker}*\n"
        f"📅 {tf_label.get(timeframe, timeframe)} | {n} Candle\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💹 *Candle Terkini*\n"
        f"Open: RM{last_open:.3f}  Close: RM{last_close:.3f}\n"
        f"High: RM{last_high:.3f}  Low: RM{last_low:.3f}\n"
        f"Perubahan: {'🔺' if change >= 0 else '🔻'} RM{abs(change):.3f} ({change_pct:+.2f}%)\n\n"
        f"📈 *Trend*\n{trend}\n\n"
        f"🕯️ *Candlestick*\n{pattern}\n"
    )

    if engulf:
        msg += f"{engulf}\n"

    msg += (
        f"\n📊 *RSI ({n} candle{'— estimated' if n < 8 else ''})*\n"
        f"RSI: `{rsi}` — {rsi_lbl}\n\n"
        f"📉 *Moving Average*\n"
        f"MA{min(5,n)}: `RM{ma}` — {'🔼 Harga atas MA' if last_close > ma else '🔽 Harga bawah MA'}\n\n"
        f"🎯 *Support & Resistance*\n"
        f"R2: `RM{r2}`  R1: `RM{r1}`\n"
        f"Pivot: `RM{pivot}`\n"
        f"S1: `RM{s1}`  S2: `RM{s2}`\n"
    )

    # FREE user — stop di sini
    if tier == 0:
        msg += (
            f"\n🔒 *Premium Features (Locked)*\n"
            f"• Volume Analysis\n"
            f"• MACD Signal\n"
            f"• Bollinger Bands\n"
            f"• Fibonacci Retracement\n"
            f"• Overall Signal\n\n"
            f"💎 Upgrade → /upgrade"
        )
        if n < 8:
            msg += f"\n\n⚠️ _RSI estimated. Untuk lebih tepat, guna 10 candle._"
        return msg

    # PREMIUM & PRO — tambah indicator advance
    vol_lbl = volume_analysis(vols)
    msg += f"\n\n📦 *Volume Analysis*\n{vol_lbl}\n"

    if n >= 5:
        macd_line, macd_sig, macd_hist = calc_macd(closes)
        macd_lbl = "🟢 Bullish" if macd_hist > 0 else "🔴 Bearish"
        msg += (
            f"\n📊 *MACD*\n"
            f"MACD: `{macd_line}` | Signal: `{macd_sig}`\n"
            f"Histogram: `{macd_hist}` — {macd_lbl}\n"
        )

    if n >= 8:
        bb_mid, bb_upper, bb_lower = calc_bollinger(closes)
        if bb_mid:
            bb_pos = "🔼 Atas upper band — overbought" if last_close > bb_upper else \
                     "🔽 Bawah lower band — oversold" if last_close < bb_lower else \
                     "🟡 Dalam band — normal"
            msg += (
                f"\n📐 *Bollinger Bands*\n"
                f"Upper: `RM{bb_upper}` | Mid: `RM{bb_mid}` | Lower: `RM{bb_lower}`\n"
                f"Posisi: {bb_pos}\n"
            )

    if n >= 8:
        fib = calc_fibonacci(highs, lows)
        msg += (
            f"\n📏 *Fibonacci Retracement*\n"
            f"100%: `RM{fib['100%']}` (Low)\n"
            f"61.8%: `RM{fib['61.8%']}` ⭐ Key level\n"
            f"50%: `RM{fib['50%']}`\n"
            f"38.2%: `RM{fib['38.2%']}`\n"
            f"0%: `RM{fib['0%']}` (High)\n"
        )

    # Overall signal
    macd_h = calc_macd(closes)[2] if n >= 5 else 0
    signal = overall_signal(rsi, trend, macd_h, last_close, ma)
    msg += (
        f"\n━━━━━━━━━━━━━━━━━━\n"
        f"🏁 *Overall Signal: {signal}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )

    # PRO — Risk Management
    if tier == 2:
        atr = sum(highs[i] - lows[i] for i in range(n)) / n
        stop_loss = round(last_close - (atr * 1.5), 3)
        tp1 = round(last_close + (atr * 1.5), 3)
        tp2 = round(last_close + (atr * 3.0), 3)
        position_risk = round((last_close - stop_loss) / last_close * 100, 2)

        msg += (
            f"\n💰 *Risk Management (PRO)*\n"
            f"ATR: `RM{round(atr, 3)}`\n"
            f"Stop Loss: `RM{stop_loss}` ({position_risk}% risk)\n"
            f"Take Profit 1: `RM{tp1}` (RR 1:1)\n"
            f"Take Profit 2: `RM{tp2}` (RR 1:2) ⭐\n"
        )

    msg += "\n⚠️ _Analisa untuk tujuan pembelajaran sahaja. Bukan nasihat pelaburan._"

    if n < 8:
        msg += f"\n💡 _Tip: Guna 10 candle untuk analisa yang lebih lengkap & tepat._"

    return msg
