"""
AI 市场分析系统 - Evidence-Based Market Analyzer
面向普通投资者的多源数据交叉验证、历史情景统计、正反证据融合、短中期分层判断系统
覆盖：加密货币 + 美股
原则：证据先行，仓位第二。不承诺预测，只呈现可验证证据。
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from analyzer import analyze_asset, get_recommendations, fetch_stock_data, fetch_crypto_data, resolve_crypto_id, is_crypto
from datetime import datetime
import time

st.set_page_config(
    page_title="AI 市场分析系统 | Evidence-Based Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1e3a5f, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .evidence-box {
        background-color: #f0fdf4;
        border-left: 4px solid #22c55e;
        padding: 0.8rem 1rem;
        margin: 0.3rem 0;
        border-radius: 0 6px 6px 0;
    }
    .counter-box {
        background-color: #fef2f2;
        border-left: 4px solid #ef4444;
        padding: 0.8rem 1rem;
        margin: 0.3rem 0;
        border-radius: 0 6px 6px 0;
    }
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .disclaimer {
        background: #fffbeb;
        border: 1px solid #fbbf24;
        border-radius: 8px;
        padding: 1rem;
        font-size: 0.9rem;
        color: #92400e;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

def plot_price_chart(df, symbol, tech):
    """绘制价格与均线、RSI图"""
    if df is None or df.empty:
        return None

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{symbol} 价格与均线", "RSI (14)")
    )

    # Candlestick or line
    if "Open" in df.columns and df["Open"].nunique() > 1:
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="OHLC"
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"], name="Close",
            line=dict(color="#3b82f6", width=2)
        ), row=1, col=1)

    # MAs
    if tech.get("sma20"):
        sma20 = df["Close"].rolling(20).mean()
        fig.add_trace(go.Scatter(x=df.index, y=sma20, name="SMA20", line=dict(color="orange", width=1)), row=1, col=1)
    if tech.get("sma50"):
        sma50 = df["Close"].rolling(50).mean()
        fig.add_trace(go.Scatter(x=df.index, y=sma50, name="SMA50", line=dict(color="purple", width=1)), row=1, col=1)
    if len(df) >= 200:
        sma200 = df["Close"].rolling(200).mean()
        fig.add_trace(go.Scatter(x=df.index, y=sma200, name="SMA200", line=dict(color="gray", width=1, dash="dash")), row=1, col=1)

    # RSI
    rsi = ta_rsi(df["Close"])
    fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI", line=dict(color="#8b5cf6")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="gray", row=2, col=1)

    fig.update_layout(
        height=550,
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
    return fig

def ta_rsi(close, window=14):
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def render_analysis(result: dict):
    """渲染单个资产完整分析"""
    if "error" in result:
        st.error(result["error"])
        return

    st.markdown(f"## {result.get('name', result['symbol'])} ({result['symbol']})")
    st.caption(f"类型: {'加密货币' if result['type']=='crypto' else '美股'} | 分析时间: {result['timestamp'][:19]}")

    # Key metrics
    tech = result.get("technicals", {})
    trend = result.get("trend", {})
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("当前价格", f"${tech.get('price', 0):,.2f}", f"{tech.get('pct_change_1d', 0):.2f}%")
    with col2:
        st.metric("短期趋势", trend.get("short", "-"))
    with col3:
        st.metric("中期趋势", trend.get("mid", "-"))
    with col4:
        st.metric("长期结构", trend.get("long", "-"))
    with col5:
        st.metric("证据优势", result.get("advantage", "-"))

    st.markdown(f"**当前阶段**: {trend.get('stage', '-')}")

    # Chart
    symbol = result["symbol"]
    is_c = result["type"] == "crypto"
    if is_c:
        df, _ = fetch_crypto_data(result.get("coin_id", resolve_crypto_id(symbol)), days=180)
    else:
        df, _ = fetch_stock_data(symbol, period="6mo")
    if df is not None:
        fig = plot_price_chart(df, symbol, tech)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    # Evidence & Counter
    st.markdown("### 📋 证据链（正证据 vs 反证据）")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### ✅ 支持当前优势方向的证据")
        for e in result.get("evidence", []):
            st.markdown(f'<div class="evidence-box">{e}</div>', unsafe_allow_html=True)
        if not result.get("evidence"):
            st.info("暂无明显正证据")
    with c2:
        st.markdown("#### ⚠️ 反证 / 风险信号")
        for c in result.get("counter_evidence", []):
            st.markdown(f'<div class="counter-box">{c}</div>', unsafe_allow_html=True)
        if not result.get("counter_evidence"):
            st.info("暂无明显反证")

    # Historical probability
    st.markdown("### 📊 历史情景统计（相似技术状态前瞻）")
    hist = result.get("historical", {})
    if "note" in hist and hist.get("sample_size", 0) == 0:
        st.warning(hist["note"])
    else:
        st.markdown(f"**匹配条件**: {hist.get('condition', '-')}")
        st.markdown(f"**样本数量**: {hist.get('sample_size', 0)} 个历史相似日")
        h1, h2 = st.columns(2)
        with h1:
            f5 = hist.get("forward_5d", {})
            if f5:
                st.markdown("**未来5日收益分布**")
                st.write(f"- 平均: {f5.get('mean', 0):.2f}% | 中位数: {f5.get('median', 0):.2f}%")
                st.write(f"- 胜率(>0): {f5.get('win_rate', 0):.1f}%")
                st.write(f"- 25%-75%分位: {f5.get('pct25', 0):.2f}% ~ {f5.get('pct75', 0):.2f}%")
        with h2:
            f20 = hist.get("forward_20d", {})
            if f20:
                st.markdown("**未来20日收益分布**")
                st.write(f"- 平均: {f20.get('mean', 0):.2f}% | 中位数: {f20.get('median', 0):.2f}%")
                st.write(f"- 胜率(>0): {f20.get('win_rate', 0):.1f}%")
                st.write(f"- 25%-75%分位: {f20.get('pct25', 0):.2f}% ~ {f20.get('pct75', 0):.2f}%")
        st.caption(hist.get("note", ""))

    # Macro
    st.markdown("### 🌍 宏观背景简要")
    macro = result.get("macro", {})
    if "error" not in macro:
        mcols = st.columns(5)
        mcols[0].metric("SPY 20日", f"{macro.get('spy_20d') or 0:.1f}%")
        mcols[1].metric("QQQ 20日", f"{macro.get('qqq_20d') or 0:.1f}%")
        mcols[2].metric("VIX", f"{macro.get('vix_last') or 0:.1f}")
        mcols[3].metric("TLT 20日", f"{macro.get('tlt_20d') or 0:.1f}%")
        mcols[4].metric("美元 20日", f"{macro.get('dollar_20d') or 0:.1f}%")
        st.caption(macro.get("note", ""))
    else:
        st.warning("宏观数据获取失败")

    # Risks & Change conditions
    st.markdown("### ⚡ 主要风险")
    for r in result.get("risks", []):
        st.warning(r)

    st.markdown("### 🔄 判断改变条件（什么情况下应降低当前优势权重）")
    for cond in result.get("change_conditions", []):
        st.info(cond)

    # Disclaimer
    st.markdown("---")
    st.markdown(f'<div class="disclaimer"><strong>免责声明</strong><br>{result.get("disclaimer", "")}</div>', unsafe_allow_html=True)

def render_recommendation_card(r: dict, key_prefix: str):
    """推荐卡片"""
    tech = r.get("technicals", {})
    trend = r.get("trend", {})
    with st.container():
        st.markdown(f"**{r.get('name', r['symbol'])} ({r['symbol']})**")
        c1, c2, c3 = st.columns(3)
        c1.metric("价格", f"${tech.get('price', 0):,.2f}", f"{tech.get('pct_change_1d', 0):.2f}%")
        c2.metric("短期", trend.get("short", "-"))
        c3.metric("优势", r.get("advantage", "-")[:6])
        st.caption(f"阶段: {trend.get('stage', '-')} | 中期: {trend.get('mid', '-')}")
        if st.button(f"查看完整证据链 →", key=f"{key_prefix}_{r['symbol']}"):
            st.session_state["selected_asset"] = r["symbol"]
            st.session_state["page"] = "detail"
            st.rerun()

# ========== Main App ==========
def main():
    st.markdown('<p class="main-header">📊 AI 市场分析系统</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">多源数据交叉验证 · 历史情景统计 · 正反证据融合 · 短中期分层判断<br>覆盖美股 + 加密货币 | 证据先行，仓位第二 | 不预测必然，只呈现可验证证据</p>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("🔍 查询资产")
        query = st.text_input("输入代码或名称", placeholder="例如: AAPL, NVDA, BTC, ETH, SOL", key="query_input")
        if st.button("分析", type="primary"):
            if query.strip():
                st.session_state["selected_asset"] = query.strip()
                st.session_state["page"] = "detail"
                st.rerun()

        st.markdown("---")
        st.markdown("**快速选择**")
        quick_stocks = ["AAPL", "NVDA", "TSLA", "MSFT", "META"]
        quick_cryptos = ["BTC", "ETH", "SOL", "BNB", "XRP"]
        scols = st.columns(2)
        with scols[0]:
            st.caption("美股")
            for s in quick_stocks:
                if st.button(s, key=f"qs_{s}"):
                    st.session_state["selected_asset"] = s
                    st.session_state["page"] = "detail"
                    st.rerun()
        with scols[1]:
            st.caption("加密货币")
            for c in quick_cryptos:
                if st.button(c, key=f"qc_{c}"):
                    st.session_state["selected_asset"] = c
                    st.session_state["page"] = "detail"
                    st.rerun()

        st.markdown("---")
        if st.button("🏠 返回推荐首页"):
            st.session_state["page"] = "home"
            st.session_state.pop("selected_asset", None)
            st.rerun()

        st.markdown("---")
        st.markdown("""
        **系统原则**
        - 证据先行，仓位第二
        - 不承诺“明天一定涨/跌”
        - 呈现：趋势 + 阶段 + 证据 + 反证 + 历史概率 + 风险 + 改变条件
        """)

    # Page routing
    page = st.session_state.get("page", "home")

    if page == "detail" and "selected_asset" in st.session_state:
        with st.spinner(f"正在多源交叉验证 {st.session_state['selected_asset']} 的证据链..."):
            result = analyze_asset(st.session_state["selected_asset"])
        render_analysis(result)
    else:
        # Home: Recommendations
        st.markdown("### 🏆 今日推荐观察（基于技术+证据评分）")
        st.caption("系统自动对热门美股与加密货币进行快速扫描，按证据优势与动量排序。点击可查看完整证据链。")

        with st.spinner("正在扫描热门资产并生成证据排名（约需15-40秒）..."):
            recs = get_recommendations(n=3)

        tab1, tab2 = st.tabs(["📈 美股 Top 3", "🪙 加密货币 Top 3"])

        with tab1:
            if recs["stocks"]:
                cols = st.columns(3)
                for i, r in enumerate(recs["stocks"]):
                    with cols[i]:
                        render_recommendation_card(r, f"stock_{i}")
            else:
                st.warning("暂无获取股票推荐数据")

        with tab2:
            if recs["cryptos"]:
                cols = st.columns(3)
                for i, r in enumerate(recs["cryptos"]):
                    with cols[i]:
                        render_recommendation_card(r, f"crypto_{i}")
            else:
                st.warning("暂未获取加密货币推荐数据")

        st.markdown("---")
        st.markdown("#### 使用说明")
        st.markdown("""
        1. **首页**：自动展示评分靠前的3只美股与3个加密货币，包含价格、趋势、证据优势摘要。
        2. **点击「查看完整证据链」** 或侧边栏输入代码：进入单资产深度分析。
        3. **深度分析包含**：
           - 短/中/长期趋势与当前阶段
           - 正证据 vs 反证据列表（技术、量价、估值/市值等）
           - 历史相似情景下的前瞻收益统计（胜率、分位数）
           - 宏观背景（SPY/QQQ/VIX/债券/美元）
           - 主要风险与「判断改变条件」
        4. **数据来源**：Yahoo Finance（美股）、CoinGecko（加密货币）、自计算技术指标与历史统计。
        5. **局限**：免费数据源有延迟与限制；链上数据、ETF实时资金流、深度新闻情感等高级源需付费API扩展；历史统计为简化匹配，非完整机器学习模型。
        """)

if __name__ == "__main__":
    main()
