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
from analyzer import analyze_asset, fetch_stock_data, fetch_crypto_data, resolve_crypto_id, is_crypto
from datetime import datetime

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
        font-size: 2.0rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1e3a5f, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 1.2rem;
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


@st.cache_data(ttl=300, show_spinner=False)
def cached_analyze(symbol: str):
    """缓存分析结果，5分钟内相同资产不重复请求"""
    return analyze_asset(symbol)


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
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI", line=dict(color="#8b5cf6")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="gray", row=2, col=1)

    fig.update_layout(
        height=500,
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
    return fig


def render_analysis(result: dict):
    """渲染单个资产完整分析"""
    if "error" in result:
        st.error(result["error"])
        return

    st.markdown(f"## {result.get('name', result['symbol'])} ({result['symbol']})")
    st.caption(f"类型: {'加密货币' if result['type']=='crypto' else '美股'} | 分析时间: {result['timestamp'][:19]}")

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
    try:
        if is_c:
            df, _ = fetch_crypto_data(result.get("coin_id", resolve_crypto_id(symbol)), days=180)
        else:
            df, _ = fetch_stock_data(symbol, period="6mo")
        if df is not None:
            fig = plot_price_chart(df, symbol, tech)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("图表加载失败，不影响文字分析")

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
        st.warning(hist.get("note", "历史数据不足"))
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

    st.markdown("### 🔄 判断改变条件")
    for cond in result.get("change_conditions", []):
        st.info(cond)

    st.markdown("---")
    st.markdown(f'<div class="disclaimer"><strong>免责声明</strong><br>{result.get("disclaimer", "")}</div>', unsafe_allow_html=True)


def main():
    st.markdown('<p class="main-header">📊 AI 市场分析系统</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">多源数据交叉验证 · 历史情景统计 · 正反证据融合 · 短中期分层判断<br>覆盖美股 + 加密货币 | 证据先行，仓位第二 | 不预测必然，只呈现可验证证据</p>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("🔍 查询资产")
        query = st.text_input("输入代码或名称", placeholder="例如: AAPL, NVDA, BTC, ETH, SOL", key="query_input")
        analyze_btn = st.button("分析", type="primary")

        if analyze_btn and query.strip():
            st.session_state["selected_asset"] = query.strip().upper()
            st.session_state["page"] = "detail"
            st.rerun()

        st.markdown("---")
        st.markdown("**快速选择**")
        quick_stocks = ["AAPL", "NVDA", "TSLA", "MSFT", "META"]
        quick_cryptos = ["BTC", "ETH", "SOL", "BNB", "XRP"]

        st.caption("美股")
        cols = st.columns(2)
        for i, s in enumerate(quick_stocks):
            if cols[i % 2].button(s, key=f"qs_{s}"):
                st.session_state["selected_asset"] = s
                st.session_state["page"] = "detail"
                st.rerun()

        st.caption("加密货币")
        cols = st.columns(2)
        for i, c in enumerate(quick_cryptos):
            if cols[i % 2].button(c, key=f"qc_{c}"):
                st.session_state["selected_asset"] = c
                st.session_state["page"] = "detail"
                st.rerun()

        st.markdown("---")
        if st.button("🏠 返回首页"):
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
        symbol = st.session_state["selected_asset"]
        with st.spinner(f"正在分析 {symbol}，请稍候（首次约10-30秒）..."):
            try:
                result = cached_analyze(symbol)
                render_analysis(result)
            except Exception as e:
                st.error(f"分析失败: {str(e)}")
                st.info("可能是数据源暂时限流，请稍后再试，或换一个资产。")
    else:
        # Lightweight homepage
        st.markdown("### 👋 欢迎使用")
        st.markdown("""
        在左侧输入资产代码（如 **BTC**、**AAPL**、**ETH**、**NVDA**），或点击快速选择按钮，即可查看完整证据链分析。

        **支持：**
        - 美股代码（AAPL、TSLA、NVDA…）
        - 加密货币（BTC、ETH、SOL、BNB、XRP…）
        """)

        st.markdown("---")
        st.markdown("#### 使用提示")
        st.markdown("""
        1. 输入代码后点击「分析」，等待 10-30 秒即可看到结果。
        2. 结果包含：短中长期趋势、正反证据、历史概率统计、宏观背景、风险与改变条件。
        3. 免费服务器有休眠机制，如果很久没人用，第一次打开可能稍慢。
        4. 本系统只呈现可验证证据，不构成投资建议。
        """)

        st.markdown("---")
        st.info("💡 提示：直接在左侧输入 BTC 或 AAPL 开始分析。")


if __name__ == "__main__":
    main()
