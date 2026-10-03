"""
Evidence-Based Market Analyzer Core Engine
原则：证据先行，仓位第二。不预测必然，只呈现可验证证据与历史统计。
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pycoingecko import CoinGeckoAPI
import ta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings("ignore")

cg = CoinGeckoAPI()

# 热门资产列表（默认推荐用）
POPULAR_STOCKS = ["AAPL", "NVDA", "MSFT", "TSLA", "AMZN", "META", "GOOGL", "AMD", "AVGO", "JPM"]
POPULAR_CRYPTOS = ["bitcoin", "ethereum", "solana", "binancecoin", "ripple", "cardano", "dogecoin", "avalanche-2"]

CRYPTO_ID_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin", "AVAX": "avalanche-2",
    "bitcoin": "bitcoin", "ethereum": "ethereum", "solana": "solana"
}

def resolve_crypto_id(symbol: str) -> str:
    s = symbol.upper().strip()
    if s in CRYPTO_ID_MAP:
        return CRYPTO_ID_MAP[s]
    # try lower
    return symbol.lower().replace(" ", "-")

def is_crypto(symbol: str) -> bool:
    s = symbol.upper().strip()
    if s in ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX"] or s.lower() in CRYPTO_ID_MAP.values():
        return True
    # heuristic: if not found in yfinance as stock-like
    return False

def fetch_stock_data(ticker: str, period: str = "1y") -> Tuple[Optional[pd.DataFrame], Optional[Dict]]:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period)
        if hist.empty:
            return None, None
        info = t.info
        return hist, info
    except Exception as e:
        print(f"Stock fetch error {ticker}: {e}")
        return None, None

def fetch_crypto_data(coin_id: str, days: int = 365) -> Tuple[Optional[pd.DataFrame], Optional[Dict]]:
    try:
        # market chart
        chart = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency="usd", days=days)
        prices = chart["prices"]
        volumes = chart["total_volumes"]
        df = pd.DataFrame(prices, columns=["timestamp", "Close"])
        df["Date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("Date")
        vol_df = pd.DataFrame(volumes, columns=["timestamp", "Volume"])
        vol_df["Date"] = pd.to_datetime(vol_df["timestamp"], unit="ms")
        vol_df = vol_df.set_index("Date")
        df["Volume"] = vol_df["Volume"]
        df = df[["Close", "Volume"]].dropna()
        # add OHLC approx (use Close for all for simplicity)
        df["Open"] = df["Close"]
        df["High"] = df["Close"]
        df["Low"] = df["Close"]
        # coin info
        info = cg.get_coin_by_id(id=coin_id, localization=False, tickers=False, market_data=True, community_data=False, developer_data=False)
        return df, info
    except Exception as e:
        print(f"Crypto fetch error {coin_id}: {e}")
        return None, None

def compute_technicals(df: pd.DataFrame) -> Dict[str, Any]:
    if len(df) < 50:
        return {}
    close = df["Close"]
    high = df["High"] if "High" in df else close
    low = df["Low"] if "Low" in df else close
    volume = df["Volume"] if "Volume" in df else pd.Series(0, index=df.index)

    # Moving averages
    sma20 = ta.trend.sma_indicator(close, window=20)
    sma50 = ta.trend.sma_indicator(close, window=50)
    sma200 = ta.trend.sma_indicator(close, window=200) if len(df) >= 200 else None
    ema12 = ta.trend.ema_indicator(close, window=12)
    ema26 = ta.trend.ema_indicator(close, window=26)

    # RSI
    rsi = ta.momentum.rsi(close, window=14)

    # MACD
    macd = ta.trend.macd(close)
    macd_signal = ta.trend.macd_signal(close)
    macd_diff = ta.trend.macd_diff(close)

    # Bollinger
    bb_high = ta.volatility.bollinger_hband(close)
    bb_low = ta.volatility.bollinger_lband(close)
    bb_mid = ta.volatility.bollinger_mavg(close)

    # ATR for volatility
    atr = ta.volatility.average_true_range(high, low, close, window=14)

    # Volume SMA
    vol_sma = volume.rolling(20).mean()

    latest = {
        "price": float(close.iloc[-1]),
        "sma20": float(sma20.iloc[-1]) if not pd.isna(sma20.iloc[-1]) else None,
        "sma50": float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else None,
        "sma200": float(sma200.iloc[-1]) if sma200 is not None and not pd.isna(sma200.iloc[-1]) else None,
        "rsi": float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None,
        "macd": float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else None,
        "macd_signal": float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else None,
        "macd_hist": float(macd_diff.iloc[-1]) if not pd.isna(macd_diff.iloc[-1]) else None,
        "bb_high": float(bb_high.iloc[-1]) if not pd.isna(bb_high.iloc[-1]) else None,
        "bb_low": float(bb_low.iloc[-1]) if not pd.isna(bb_low.iloc[-1]) else None,
        "atr": float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None,
        "volume": float(volume.iloc[-1]),
        "vol_sma20": float(vol_sma.iloc[-1]) if not pd.isna(vol_sma.iloc[-1]) else None,
        "pct_change_1d": float(close.pct_change().iloc[-1] * 100) if len(close) > 1 else 0,
        "pct_change_5d": float((close.iloc[-1] / close.iloc[-5] - 1) * 100) if len(close) >= 5 else None,
        "pct_change_20d": float((close.iloc[-1] / close.iloc[-20] - 1) * 100) if len(close) >= 20 else None,
        "pct_change_60d": float((close.iloc[-1] / close.iloc[-60] - 1) * 100) if len(close) >= 60 else None,
        "pct_change_ytd": None,  # compute later if possible
    }
    return latest

def determine_trend_and_stage(tech: Dict) -> Dict[str, str]:
    """分层判断：短中长期趋势与阶段"""
    price = tech.get("price")
    sma20 = tech.get("sma20")
    sma50 = tech.get("sma50")
    sma200 = tech.get("sma200")
    rsi = tech.get("rsi")
    macd_hist = tech.get("macd_hist")

    # Short-term (days-weeks)
    short = "中性"
    if price and sma20:
        if price > sma20 and (macd_hist or 0) > 0:
            short = "偏多"
        elif price < sma20 and (macd_hist or 0) < 0:
            short = "偏空"
        elif price > sma20:
            short = "弱多"
        else:
            short = "弱空"

    # Mid-term (weeks-months)
    mid = "中性"
    if price and sma50:
        if price > sma50 and sma20 and sma20 > sma50:
            mid = "上升趋势"
        elif price < sma50 and sma20 and sma20 < sma50:
            mid = "下降趋势"
        elif price > sma50:
            mid = "偏多整理"
        else:
            mid = "偏空整理"

    # Long-term
    long = "中性"
    if price and sma200:
        if price > sma200:
            long = "牛市结构"
        else:
            long = "熊市结构"
    elif price and sma50:
        long = "数据不足（用中期代替）"

    # Stage
    stage = "震荡"
    if rsi:
        if rsi > 70:
            stage = "超买/可能回调阶段"
        elif rsi < 30:
            stage = "超卖/可能反弹阶段"
        elif mid == "上升趋势" and short == "偏多":
            stage = "趋势加速阶段"
        elif mid == "下降趋势" and short == "偏空":
            stage = "下跌加速阶段"
        elif mid.startswith("上升") and short in ["弱空", "偏空"]:
            stage = "上升趋势中的回调"
        elif mid.startswith("下降") and short in ["弱多", "偏多"]:
            stage = "下降趋势中的反弹"

    return {"short": short, "mid": mid, "long": long, "stage": stage}

def generate_evidence(tech: Dict, info: Optional[Dict], is_crypto_flag: bool, symbol: str) -> Tuple[List[str], List[str]]:
    """生成正证据与反证据"""
    evidence = []
    counter = []

    price = tech.get("price")
    sma20 = tech.get("sma20")
    sma50 = tech.get("sma50")
    sma200 = tech.get("sma200")
    rsi = tech.get("rsi")
    macd_hist = tech.get("macd_hist")
    pct5 = tech.get("pct_change_5d")
    pct20 = tech.get("pct_change_20d")
    vol = tech.get("volume")
    vol_sma = tech.get("vol_sma20")

    # Price vs MA
    if price and sma20:
        if price > sma20:
            evidence.append(f"价格 ({price:.2f}) 站上20日均线 ({sma20:.2f})，短期动能偏多")
        else:
            counter.append(f"价格 ({price:.2f}) 跌破20日均线 ({sma20:.2f})，短期承压")

    if price and sma50:
        if price > sma50:
            evidence.append(f"价格站上50日均线，中期结构偏多")
        else:
            counter.append(f"价格低于50日均线，中期结构偏空")

    if price and sma200:
        if price > sma200:
            evidence.append(f"价格位于200日均线上方，长期牛市结构 intact")
        else:
            counter.append(f"价格位于200日均线下方，长期熊市结构")

    # RSI
    if rsi:
        if 40 < rsi < 60:
            evidence.append(f"RSI ({rsi:.1f}) 处于中性区间，无明显超买超卖")
        elif rsi >= 70:
            counter.append(f"RSI ({rsi:.1f}) 超买区域，短期回调风险上升")
        elif rsi <= 30:
            evidence.append(f"RSI ({rsi:.1f}) 超卖区域，存在技术反弹可能")
        elif rsi > 60:
            evidence.append(f"RSI ({rsi:.1f}) 偏强，多头占优")
        else:
            counter.append(f"RSI ({rsi:.1f}) 偏弱，空头占优")

    # MACD
    if macd_hist is not None:
        if macd_hist > 0:
            evidence.append(f"MACD 柱状图为正 ({macd_hist:.4f})，动能向上")
        else:
            counter.append(f"MACD 柱状图为负 ({macd_hist:.4f})，动能向下")

    # Momentum
    if pct5 is not None:
        if pct5 > 3:
            evidence.append(f"近5日涨幅 {pct5:.1f}%，短期动量强劲")
        elif pct5 < -3:
            counter.append(f"近5日跌幅 {pct5:.1f}%，短期抛压明显")

    if pct20 is not None:
        if pct20 > 10:
            evidence.append(f"近20日涨幅 {pct20:.1f}%，中期趋势强")
        elif pct20 < -10:
            counter.append(f"近20日跌幅 {pct20:.1f}%，中期趋势弱")

    # Volume
    if vol and vol_sma and vol_sma > 0:
        if vol > vol_sma * 1.5:
            if (pct5 or 0) > 0:
                evidence.append(f"成交量放大 (当前/均量 {vol/vol_sma:.1f}x)，配合上涨，量价齐升")
            else:
                counter.append(f"成交量放大但价格下跌，可能有恐慌抛售")
        elif vol < vol_sma * 0.5:
            counter.append("成交量萎缩，市场参与度低，趋势可信度下降")

    # Fundamentals / Crypto specific
    if is_crypto_flag and info:
        md = info.get("market_data", {})
        mc = md.get("market_cap", {}).get("usd")
        if mc:
            evidence.append(f"市值约 ${mc/1e9:.1f}B")
        change_24h = md.get("price_change_percentage_24h")
        if change_24h:
            if change_24h > 0:
                evidence.append(f"24h 涨幅 {change_24h:.2f}%")
            else:
                counter.append(f"24h 跌幅 {abs(change_24h):.2f}%")
        # ATH distance
        ath = md.get("ath", {}).get("usd")
        if ath and price:
            dist = (price / ath - 1) * 100
            if dist > -20:
                evidence.append(f"距离历史高点仅 {abs(dist):.1f}%，处于相对高位区域")
            else:
                counter.append(f"距离历史高点 {abs(dist):.1f}%，仍有较大回升空间或风险")

    elif not is_crypto_flag and info:
        # Stock fundamentals
        pe = info.get("trailingPE") or info.get("forwardPE")
        if pe:
            if pe < 25:
                evidence.append(f"PE 约 {pe:.1f}，估值相对合理/偏低")
            elif pe > 40:
                counter.append(f"PE 约 {pe:.1f}，估值偏高，需增长支撑")
        rec = info.get("recommendationKey")
        if rec:
            if rec in ["buy", "strong_buy"]:
                evidence.append(f"分析师共识：{rec}")
            elif rec in ["sell", "strong_sell"]:
                counter.append(f"分析师共识：{rec}")
        target = info.get("targetMeanPrice")
        if target and price:
            upside = (target / price - 1) * 100
            if upside > 10:
                evidence.append(f"分析师目标价暗示上涨空间 {upside:.1f}%")
            elif upside < -5:
                counter.append(f"分析师目标价暗示下行空间 {abs(upside):.1f}%")

    return evidence, counter

def historical_probability(df: pd.DataFrame, tech: Dict) -> Dict[str, Any]:
    """简化历史情景统计：基于当前类似技术状态的前瞻收益分布"""
    if len(df) < 100:
        return {"note": "历史数据不足，无法进行可靠统计"}

    close = df["Close"]
    rsi = ta.momentum.rsi(close, window=14)
    sma20 = ta.trend.sma_indicator(close, window=20)
    sma50 = ta.trend.sma_indicator(close, window=50)

    current_rsi = tech.get("rsi")
    current_above_sma20 = tech.get("price", 0) > (tech.get("sma20") or 0)
    current_above_sma50 = tech.get("price", 0) > (tech.get("sma50") or 0)

    # Define similar conditions in past
    # Look for days where RSI within 10 of current, and same MA position
    results = []
    for i in range(50, len(df) - 20):  # leave room for forward
        past_rsi = rsi.iloc[i]
        if pd.isna(past_rsi) or current_rsi is None:
            continue
        if abs(past_rsi - current_rsi) > 12:
            continue
        past_above20 = close.iloc[i] > sma20.iloc[i] if not pd.isna(sma20.iloc[i]) else False
        past_above50 = close.iloc[i] > sma50.iloc[i] if not pd.isna(sma50.iloc[i]) else False
        if past_above20 != current_above_sma20 or past_above50 != current_above_sma50:
            continue

        # Forward returns
        ret_5 = (close.iloc[i+5] / close.iloc[i] - 1) * 100 if i+5 < len(df) else None
        ret_20 = (close.iloc[i+20] / close.iloc[i] - 1) * 100 if i+20 < len(df) else None
        if ret_5 is not None:
            results.append({"ret5": ret_5, "ret20": ret_20})

    if not results:
        return {"note": "未找到足够相似的历史情景", "sample_size": 0}

    rets5 = [r["ret5"] for r in results if r["ret5"] is not None]
    rets20 = [r["ret20"] for r in results if r["ret20"] is not None]

    def stats(arr):
        if not arr:
            return {}
        arr = np.array(arr)
        return {
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "win_rate": float(np.mean(arr > 0) * 100),
            "pct25": float(np.percentile(arr, 25)),
            "pct75": float(np.percentile(arr, 75)),
            "sample": len(arr)
        }

    return {
        "condition": f"RSI≈{current_rsi:.0f}, 价格相对SMA20/50位置相同",
        "forward_5d": stats(rets5),
        "forward_20d": stats(rets20),
        "sample_size": len(results),
        "note": "基于历史相似技术状态的统计，非预测。过去表现不代表未来。"
    }

def get_macro_context() -> Dict[str, Any]:
    """获取宏观背景简要"""
    try:
        spy = yf.Ticker("SPY").history(period="3mo")
        qqq = yf.Ticker("QQQ").history(period="3mo")
        vix = yf.Ticker("^VIX").history(period="1mo")
        tlt = yf.Ticker("TLT").history(period="3mo")  # bonds
        uup = yf.Ticker("UUP").history(period="3mo")  # dollar

        def last_pct(df, days=20):
            if len(df) < days:
                return None
            return float((df["Close"].iloc[-1] / df["Close"].iloc[-days] - 1) * 100)

        return {
            "spy_20d": last_pct(spy),
            "qqq_20d": last_pct(qqq),
            "vix_last": float(vix["Close"].iloc[-1]) if not vix.empty else None,
            "tlt_20d": last_pct(tlt),
            "dollar_20d": last_pct(uup),
            "note": "宏观仅作背景参考，非直接驱动。"
        }
    except Exception as e:
        return {"error": str(e)}

def analyze_asset(symbol: str) -> Dict[str, Any]:
    """主分析入口"""
    symbol = symbol.strip().upper()
    is_c = is_crypto(symbol) or symbol.lower() in CRYPTO_ID_MAP.values()

    result = {
        "symbol": symbol,
        "type": "crypto" if is_c else "stock",
        "timestamp": datetime.now().isoformat(),
        "disclaimer": "本分析仅呈现当前可验证证据与历史统计，不构成投资建议。市场有风险，决策需自负。证据先行，仓位第二。"
    }

    if is_c:
        coin_id = resolve_crypto_id(symbol)
        df, info = fetch_crypto_data(coin_id)
        result["name"] = info.get("name", symbol) if info else symbol
        result["coin_id"] = coin_id
    else:
        df, info = fetch_stock_data(symbol)
        result["name"] = info.get("shortName") or info.get("longName") or symbol if info else symbol

    if df is None or df.empty:
        result["error"] = f"无法获取 {symbol} 的数据，请检查代码是否正确（美股用代码如AAPL，加密货币用BTC/ETH或全名）"
        return result

    tech = compute_technicals(df)
    result["technicals"] = tech
    result["trend"] = determine_trend_and_stage(tech)
    evidence, counter = generate_evidence(tech, info, is_c, symbol)
    result["evidence"] = evidence
    result["counter_evidence"] = counter
    result["historical"] = historical_probability(df, tech)
    result["macro"] = get_macro_context()

    # Advantage summary
    e_count = len(evidence)
    c_count = len(counter)
    if e_count > c_count + 1:
        advantage = "多头证据占优"
    elif c_count > e_count + 1:
        advantage = "空头证据占优"
    else:
        advantage = "多空证据相对均衡"
    result["advantage"] = advantage

    # Risks
    risks = []
    if tech.get("rsi") and tech["rsi"] > 75:
        risks.append("严重超买，短期回调风险高")
    if tech.get("rsi") and tech["rsi"] < 25:
        risks.append("严重超卖，可能继续惯性下跌或剧烈反弹")
    if result["trend"]["long"] == "熊市结构":
        risks.append("长期结构偏空，反弹可能受阻")
    if result["macro"].get("vix_last") and result["macro"]["vix_last"] > 25:
        risks.append(f"VIX 处于 {result['macro']['vix_last']:.1f} 高位，市场波动与风险偏好下降")
    result["risks"] = risks if risks else ["无明显极端风险信号，但市场永远存在不确定性"]

    # Change conditions
    change_conds = []
    if result["trend"]["short"] in ["偏多", "弱多"]:
        change_conds.append("若价格跌破20日均线并伴随成交量放大，短期偏多判断应降低权重")
    if result["trend"]["mid"] == "上升趋势":
        change_conds.append("若价格有效跌破50日均线，中期上升趋势判断需重新评估")
    if tech.get("rsi") and tech["rsi"] > 60:
        change_conds.append("若RSI跌破50并伴随MACD死叉，动能优势可能转向")
    change_conds.append("重大宏观事件（如非农、FOMC、监管政策）或公司/项目特定事件可能瞬间改变证据权重")
    result["change_conditions"] = change_conds

    # Simple score for ranking (for recommendations)
    score = 0
    if "偏多" in result["trend"]["short"] or "弱多" in result["trend"]["short"]:
        score += 1
    if "上升" in result["trend"]["mid"]:
        score += 2
    if "牛市" in result["trend"]["long"]:
        score += 1
    if e_count > c_count:
        score += 1
    hist = result["historical"]
    if "forward_20d" in hist and hist["forward_20d"].get("win_rate", 0) > 55:
        score += 1
    result["score"] = score

    return result

def get_recommendations(n: int = 3) -> Dict[str, List[Dict]]:
    """获取默认推荐：热门股票与加密货币的快速分析排名"""
    stock_results = []
    for s in POPULAR_STOCKS[:8]:  # limit to avoid rate limit
        try:
            r = analyze_asset(s)
            if "error" not in r:
                stock_results.append(r)
        except:
            continue

    crypto_results = []
    for c in POPULAR_CRYPTOS[:6]:
        try:
            r = analyze_asset(c)
            if "error" not in r:
                crypto_results.append(r)
        except:
            continue

    # Sort by score descending, then by short-term momentum
    def sort_key(r):
        return (r.get("score", 0), r.get("technicals", {}).get("pct_change_5d") or 0)

    stock_results.sort(key=sort_key, reverse=True)
    crypto_results.sort(key=sort_key, reverse=True)

    return {
        "stocks": stock_results[:n],
        "cryptos": crypto_results[:n]
    }

if __name__ == "__main__":
    # Quick test
    print("Testing AAPL...")
    r = analyze_asset("AAPL")
    print(r.get("name"), r.get("advantage"), r.get("trend"))
    print("Evidence:", r.get("evidence")[:2])
    print("Testing BTC...")
    r2 = analyze_asset("BTC")
    print(r2.get("name"), r2.get("advantage"), r2.get("trend"))
