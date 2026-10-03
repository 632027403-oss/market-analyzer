# AI 市场分析系统 (Evidence-Based Market Analyzer)

面向普通投资者的多源数据交叉验证、历史情景统计、正反证据融合、短中期分层判断的 AI 市场分析系统。

## 核心原则

- **证据先行，仓位第二**
- 不承诺“我一定知道明天涨还是跌”
- 真正承诺：尽可能把现在能验证的证据摆在你面前，让你知道当前哪一方向占优势、优势来自哪里、历史上类似情况发生过什么，以及什么情况出现后应该改变判断

## 覆盖范围

- 美股（Yahoo Finance）
- 加密货币（CoinGecko）

## 功能

1. **默认首页推荐**：自动扫描热门美股与加密货币，按技术+证据评分展示 Top 3
2. **单资产深度分析**：输入代码（如 AAPL、BTC、ETH、SOL）即可查看：
   - 短 / 中 / 长期趋势与当前阶段
   - 正证据 vs 反证据列表
   - 历史相似技术情景的前瞻收益统计（胜率、均值、分位数）
   - 宏观背景（SPY、QQQ、VIX、债券、美元）
   - 主要风险
   - 判断改变条件
3. **图表**：价格 + 均线 + RSI

## 快速启动（本地）

```bash
pip install -r requirements.txt
streamlit run app.py
```

浏览器会自动打开 http://localhost:8501

## 部署到 Render.com（推荐，手机可直接打开）

### 1. 把代码推到你的 GitHub 仓库

在本地（或 GitHub 网页端上传）确保仓库根目录包含以下文件：

```
├── app.py
├── analyzer.py
├── requirements.txt
├── .gitignore
└── README.md
```

### 2. 在 Render 创建 Web Service

1. 登录 [https://render.com](https://render.com)
2. 点击 **New +** → **Web Service**
3. 连接你的 GitHub 仓库并选择本项目
4. 填写配置：
   - **Name**：随便起，例如 `market-analyzer`
   - **Runtime**：Python 3
   - **Build Command**：`pip install -r requirements.txt`
   - **Start Command**：`streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
   - **Instance Type**：Free
5. 点击 **Create Web Service**

部署完成后，Render 会给你一个网址（类似 `https://market-analyzer-xxxx.onrender.com`），用手机浏览器打开即可使用。

> 注意：免费实例有休眠机制，第一次打开可能需要等待 30-60 秒唤醒。

## 目录结构

```
market_analyzer/
├── app.py              # Streamlit 前端界面
├── analyzer.py         # 核心分析引擎
├── requirements.txt    # 依赖列表
├── .gitignore
└── README.md
```

## 数据与方法说明

- **价格与基本面**：yfinance（美股）、CoinGecko（加密货币）
- **技术指标**：SMA20/50/200、RSI、MACD、布林带、ATR、成交量
- **证据生成**：规则驱动的多因子证据与反证（价格 vs 均线、RSI 区间、MACD 动能、动量、量价、估值/分析师目标等）
- **历史统计**：在历史数据中匹配「RSI 相近 + 相对 SMA20/50 位置相同」的相似日，统计其后 5 日 / 20 日收益分布
- **宏观**：SPY、QQQ、VIX、TLT、UUP 的近期表现

## 局限与扩展方向

当前为可运行原型，使用免费公开数据源：

- 数据有延迟与请求限制
- 链上数据、ETF 实时资金流、深度新闻情感、期权数据等需额外付费 API
- 历史匹配为简化规则，可升级为更精细的相似性搜索或机器学习模型
- 无实时推送、无用户账户与仓位管理（符合“证据先行，仓位第二”设计）

可扩展方向：接入 FRED 宏观、Glassnode/CryptoQuant 链上、Polygon/Alpaca 新闻、自建向量库做事件匹配等。

## 免责声明

本系统仅用于展示可验证证据与历史统计，**不构成任何投资建议**。市场有风险，投资需谨慎。决策责任由用户自行承担。
