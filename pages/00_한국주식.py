import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------------------------------------------------------
# 페이지 설정
# ----------------------------------------------------------------
st.set_page_config(page_title="🇰🇷 AI·반도체 대표주 분석", page_icon="📈", layout="wide")

st.title("🇰🇷 한국 AI·반도체 대표주 인터랙티브 분석 대시보드")
st.caption("Yahoo Finance 데이터 · Plotly 기반 인터랙티브 차트")

# ----------------------------------------------------------------
# 한국 AI / 반도체 대표주 목록 (티커: 회사명, 카테고리)
# ----------------------------------------------------------------
KR_STOCKS = {
    "005930.KS": {"name": "삼성전자", "category": "반도체"},
    "000660.KS": {"name": "SK하이닉스", "category": "반도체"},
    "042700.KS": {"name": "한미반도체", "category": "반도체"},
    "000990.KS": {"name": "DB하이텍", "category": "반도체"},
    "058470.KQ": {"name": "리노공업", "category": "반도체"},
    "222800.KQ": {"name": "심텍", "category": "반도체"},
    "007660.KQ": {"name": "이수페타시스", "category": "반도체"},
    "036930.KQ": {"name": "주성엔지니어링", "category": "반도체"},
    "240810.KQ": {"name": "원익IPS", "category": "반도체"},
    "035420.KS": {"name": "NAVER", "category": "AI"},
    "035720.KS": {"name": "카카오", "category": "AI"},
    "066570.KS": {"name": "LG전자", "category": "AI"},
    "251270.KS": {"name": "넷마블", "category": "AI"},
    "304100.KQ": {"name": "솔트룩스", "category": "AI"},
    "347860.KQ": {"name": "알체라", "category": "AI"},
    "289220.KQ": {"name": "코난테크놀로지", "category": "AI"},
    "041020.KQ": {"name": "폴라리스오피스", "category": "AI"},
}

# ----------------------------------------------------------------
# 사이드바 - 사용자 입력
# ----------------------------------------------------------------
st.sidebar.header("⚙️ 설정")

category_filter = st.sidebar.radio("카테고리 필터", ["전체", "반도체", "AI"], index=0)

if category_filter == "전체":
    available = KR_STOCKS
else:
    available = {k: v for k, v in KR_STOCKS.items() if v["category"] == category_filter}

label_to_ticker = {f"{v['name']} ({k})": k for k, v in available.items()}

default_labels = [lbl for lbl, tkr in label_to_ticker.items() if tkr in ("005930.KS", "000660.KS")]
if not default_labels:
    default_labels = list(label_to_ticker.keys())[:2]

selected_labels = st.sidebar.multiselect(
    "종목 선택 (복수 선택 가능)",
    options=list(label_to_ticker.keys()),
    default=default_labels,
)

tickers = [label_to_ticker[lbl] for lbl in selected_labels]

period_options = {
    "1개월": "1mo", "3개월": "3mo", "6개월": "6mo",
    "1년": "1y", "2년": "2y", "5년": "5y", "최대": "max",
}
period_label = st.sidebar.selectbox("조회 기간", list(period_options.keys()), index=3)
period = period_options[period_label]

interval_options = {"1일": "1d", "1주": "1wk", "1개월": "1mo"}
interval_label = st.sidebar.selectbox("데이터 간격", list(interval_options.keys()), index=0)
interval = interval_options[interval_label]

show_ma = st.sidebar.checkbox("이동평균선 표시", value=True)
ma_short = st.sidebar.number_input("단기 이동평균(일)", min_value=2, max_value=100, value=20)
ma_long = st.sidebar.number_input("장기 이동평균(일)", min_value=5, max_value=300, value=60)

chart_type = st.sidebar.radio("차트 유형", ["캔들스틱", "라인"], index=0)

st.sidebar.markdown("---")
st.sidebar.caption("데이터 출처: Yahoo Finance (yfinance) · .KS=코스피, .KQ=코스닥")


# ----------------------------------------------------------------
# 데이터 로딩 (캐시로 속도 개선)
# ----------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()


if not tickers:
    st.warning("사이드바에서 최소 하나의 종목을 선택해주세요.")
    st.stop()

# ----------------------------------------------------------------
# 메인 종목 (첫 번째 선택) - 상세 분석
# ----------------------------------------------------------------
main_ticker = tickers[0]
main_name = KR_STOCKS[main_ticker]["name"]
df = load_data(main_ticker, period, interval)

if df.empty:
    st.error(f"'{main_name} ({main_ticker})'에 대한 데이터를 불러올 수 없습니다.")
    st.stop()

st.subheader(f"🏢 {main_name} ({main_ticker})")

last_close = float(df["Close"].iloc[-1])
prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else last_close
change = last_close - prev_close
change_pct = (change / prev_close * 100) if prev_close else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("현재가 (원)", f"{last_close:,.0f}", f"{change:,.0f} ({change_pct:.2f}%)")
col2.metric("최고가 (원)", f"{float(df['High'].max()):,.0f}")
col3.metric("최저가 (원)", f"{float(df['Low'].min()):,.0f}")
col4.metric("평균 거래량", f"{int(df['Volume'].mean()):,}")

# ----------------------------------------------------------------
# 이동평균 계산
# ----------------------------------------------------------------
if show_ma:
    df[f"MA{ma_short}"] = df["Close"].rolling(window=ma_short).mean()
    df[f"MA{ma_long}"] = df["Close"].rolling(window=ma_long).mean()

# ----------------------------------------------------------------
# 캔들스틱 / 라인 + 거래량 차트 (Plotly)
# ----------------------------------------------------------------
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.75, 0.25], vertical_spacing=0.03,
    subplot_titles=(f"{main_name} 가격", "거래량")
)

if chart_type == "캔들스틱":
    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="가격",
            increasing_line_color="#26a69a", decreasing_line_color="#ef5350"
        ),
        row=1, col=1
    )
else:
    fig.add_trace(
        go.Scatter(x=df.index, y=df["Close"], mode="lines", name="종가",
                    line=dict(color="#1f77b4", width=2)),
        row=1, col=1
    )

if show_ma:
    fig.add_trace(
        go.Scatter(x=df.index, y=df[f"MA{ma_short}"], mode="lines",
                    name=f"MA{ma_short}", line=dict(color="orange", width=1.5)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df[f"MA{ma_long}"], mode="lines",
                    name=f"MA{ma_long}", line=dict(color="purple", width=1.5)),
        row=1, col=1
    )

colors = ["#ef5350" if row["Close"] < row["Open"] else "#26a69a" for _, row in df.iterrows()]
fig.add_trace(
    go.Bar(x=df.index, y=df["Volume"], name="거래량", marker_color=colors),
    row=2, col=1
)

fig.update_layout(
    height=700,
    xaxis_rangeslider_visible=False,
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=40, b=10),
)

st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------
# 여러 종목 비교 (정규화 수익률)
# ----------------------------------------------------------------
if len(tickers) > 1:
    st.subheader("🔀 선택 종목 비교 (수익률 %)")
    comp_fig = go.Figure()
    for t in tickers:
        t_name = KR_STOCKS[t]["name"]
        t_df = load_data(t, period, interval)
        if t_df.empty:
            st.warning(f"'{t_name} ({t})' 데이터를 불러오지 못했습니다.")
            continue
        normalized = (t_df["Close"] / t_df["Close"].iloc[0] - 1) * 100
        comp_fig.add_trace(go.Scatter(x=t_df.index, y=normalized, mode="lines", name=t_name))

    comp_fig.update_layout(
        height=450,
        template="plotly_white",
        yaxis_title="수익률 (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(comp_fig, use_container_width=True)

# ----------------------------------------------------------------
# 원본 데이터 테이블
# ----------------------------------------------------------------
with st.expander("📋 원본 데이터 보기"):
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    csv = df.to_csv().encode("utf-8")
    st.download_button("CSV로 다운로드", data=csv, file_name=f"{main_ticker}_data.csv", mime="text/csv")

st.caption("⚠️ 본 데이터와 차트는 투자 참고용이며, 투자 판단의 근거가 될 수 없습니다.")
