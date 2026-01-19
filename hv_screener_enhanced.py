"""
Historical Volatility Screener - Market Maker Edition
=====================================================

Professional volatility analysis tool designed for market makers to:
- Screen realized volatility across multiple tenors
- Analyze volatility term structure and regime shifts  
- Export historical data for offline modeling and risk analysis
- Price theoretical options using Black-Scholes with realized vol inputs

Features
--------
* Market Type Toggle: Switch between Binance Spot and USDT-M Perpetual Futures
* Multi-Asset Analysis: Compare up to 5 assets simultaneously
* Customizable HV Windows: Define your own volatility calculation periods
* RMS Metrics: Normalized volatility measures for inventory risk pricing
* Data Export: Download complete historical volatility data for selected date ranges
* Options Pricer: Theoretical pricing with Greeks using realized volatility

Usage
-----
Run with: streamlit run hv_screener_enhanced.py
Ensure asset_list.csv is in the same directory
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.stats import norm
from datetime import datetime, timedelta
import time
import os
from io import BytesIO
import pytz

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    layout="wide",
    page_title="HV Screener - Market Maker Edition",
    page_icon="📊",
)

# =============================================================================
# STYLING
# =============================================================================

st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #888;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #1e1e1e;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #333;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📊 Historical Volatility Screener</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Market Maker Volatility Engine - Powered by CoinGecko API | HV at 08:00 UTC</div>', unsafe_allow_html=True)

# =============================================================================
# DATA LOADING & UTILITIES
# =============================================================================

@st.cache_data(show_spinner=False)
def load_asset_list(csv_path: str = None) -> pd.DataFrame:
    """Load the curated asset list from CSV file."""
    try:
        # Try multiple possible locations
        possible_paths = [
            csv_path,
            "asset_list.csv",
            "./asset_list.csv",
            os.path.join(os.getcwd(), "asset_list.csv"),
            os.path.join(os.path.dirname(__file__), "asset_list.csv")
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                df = pd.read_csv(path)
                return df.fillna("")
        
        return pd.DataFrame()
    except Exception as exc:
        st.error(f"Failed to load asset list: {exc}")
        return pd.DataFrame()

def build_token_options(df: pd.DataFrame, filter_coingecko: bool = False, 
                       filter_binance_options: bool = False) -> dict:
    """Build token selection options from asset list with filtering."""
    options = {}
    seen = set()
    
    for _, row in df.iterrows():
        coin = str(row.get("Coin symbol", "")).strip().upper()
        if not coin or coin in seen:
            continue
        
        common = str(row.get("Common Name", "")).strip()
        cg_id = str(row.get("CG API ID", "")).strip()
        
        # Skip if no CoinGecko ID (required for API calls)
        if not cg_id:
            continue
        
        # Apply filters
        if filter_coingecko and not cg_id:
            continue
        
        # Check if it's an options-eligible asset
        is_options_eligible = coin in ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'DOGE', 'ADA', 'LINK', 'DOT', 'MATIC']
        
        if filter_binance_options and not is_options_eligible:
            continue
        
        seen.add(coin)
        
        # Build display name with availability indicators
        indicators = []
        if cg_id:
            indicators.append("CG")  # CoinGecko
        if is_options_eligible:
            indicators.append("OPT")  # Options
        
        indicator_str = f" [{'/'.join(indicators)}]" if indicators else ""
        display = f"{coin}{f' - {common}' if common else ''}{indicator_str}"
        
        # Store CoinGecko ID for API calls
        options[display] = (coin, cg_id)
    
    return options

# =============================================================================
# API DATA FETCHING
# =============================================================================

@st.cache_data(ttl=600, show_spinner=False)
def get_crypto_data_coingecko(
    coin_id: str,
    start_date: datetime,
    end_date: datetime
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data from CoinGecko with 08:00 UTC timestamps.
    
    Args:
        coin_id: CoinGecko API ID (e.g., 'bitcoin')
        start_date: Start date
        end_date: End date
    
    Returns:
        DataFrame with OHLCV data indexed by timestamp (08:00 UTC)
    """
    try:
        # CoinGecko uses Unix timestamps in seconds
        from_timestamp = int(start_date.timestamp())
        to_timestamp = int(end_date.timestamp())
        
        # CoinGecko market_chart/range endpoint
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
        params = {
            'vs_currency': 'usd',
            'from': from_timestamp,
            'to': to_timestamp
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            st.warning(f"CoinGecko API returned status {response.status_code} for {coin_id}")
            return pd.DataFrame()
        
        data = response.json()
        
        if 'prices' not in data or not data['prices']:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(data['prices'], columns=['timestamp', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        
        # Get volumes if available
        if 'total_volumes' in data and data['total_volumes']:
            volumes = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'volume'])
            volumes['timestamp'] = pd.to_datetime(volumes['timestamp'], unit='ms', utc=True)
            df = df.merge(volumes, on='timestamp', how='left')
        else:
            df['volume'] = 0
        
        # Resample to daily and align to 08:00 UTC
        df = df.set_index('timestamp')
        df = df.resample('1D').agg({
            'close': 'last',
            'volume': 'sum'
        })
        
        # Shift to 08:00 UTC
        df.index = df.index + pd.Timedelta(hours=8)
        
        # Add OHLC (CoinGecko only provides close prices in market_chart)
        df['open'] = df['close']
        df['high'] = df['close']
        df['low'] = df['close']
        
        df = df[['open', 'high', 'low', 'close', 'volume']].dropna()
        
        return df
    
    except Exception as e:
        st.warning(f"Error fetching data from CoinGecko for {coin_id}: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def get_current_price_coingecko(coin_id: str) -> float:
    """Get the latest price from CoinGecko."""
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd'
        }
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if coin_id in data and 'usd' in data[coin_id]:
                return float(data[coin_id]['usd'])
        return None
    except Exception:
        return None

# =============================================================================
# VOLATILITY CALCULATIONS
# =============================================================================

def calculate_hv_metrics(df: pd.DataFrame, vol_windows: list) -> pd.DataFrame:
    """
    Calculate historical volatility metrics across multiple windows at 08:00 UTC.
    
    All volatility calculations are performed using close prices at 08:00 UTC daily snapshots.
    This ensures consistency across different assets and markets.
    
    Args:
        df: DataFrame with OHLCV data (indexed at 08:00 UTC)
        vol_windows: List of window sizes in days
    
    Returns:
        DataFrame with HV calculations and RMS metrics (indexed at 08:00 UTC)
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    if len(df) < max(vol_windows) + 1:
        return pd.DataFrame()
    
    df = df.copy()
    
    # Calculate log returns using 08:00 UTC close prices
    df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
    
    # Annualization factor for daily data
    annual_factor = np.sqrt(365)
    
    # Calculate HV for each window
    for w in vol_windows:
        df[f'hv_{w}'] = df['log_ret'].rolling(window=w).std() * annual_factor
    
    # Normalized RMS calculations for inventory risk
    if 2 in vol_windows and 3 in vol_windows:
        df['rms_2_3'] = np.sqrt((df['hv_2']**2 + df['hv_3']**2) / 2)
    
    if 7 in vol_windows and 14 in vol_windows:
        df['rms_7_14'] = np.sqrt((df['hv_7']**2 + df['hv_14']**2) / 2)
    
    # Representative RMS for UI (prefer 7-14 mix)
    if 'rms_7_14' in df.columns:
        df['rms_vol'] = df['rms_7_14']
    elif 'rms_2_3' in df.columns:
        df['rms_vol'] = df['rms_2_3']
    else:
        df['rms_vol'] = np.nan
    
    return df.dropna()

# =============================================================================
# BLACK-SCHOLES OPTION PRICING
# =============================================================================

def black_scholes(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call'):
    """
    Black-Scholes option pricing with Greeks.
    
    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry (years)
        r: Risk-free rate
        sigma: Volatility (annualized)
        option_type: 'call' or 'put'
    
    Returns:
        Tuple of (price, delta, gamma, theta, vega)
    """
    if T <= 0 or sigma <= 0:
        return 0, 0, 0, 0, 0
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
    else:  # put
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = -norm.cdf(-d1)
    
    # Greeks (same for calls and puts)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # Per 1% vol change
    theta = -(S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))) / 365  # Per day
    
    if option_type == 'put':
        theta -= r * K * np.exp(-r * T) * norm.cdf(-d2) / 365
    else:
        theta -= r * K * np.exp(-r * T) * norm.cdf(d2) / 365
    
    return price, delta, gamma, theta, vega

# =============================================================================
# SIDEBAR CONTROLS
# =============================================================================

with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Load asset list (no upload option)
    asset_df = load_asset_list(csv_path="asset_list.csv")
    
    if asset_df.empty:
        st.error("⚠️ Asset list not found. Please ensure asset_list.csv is in the same directory as the script.")
        st.stop()
    
    st.success(f"✓ Loaded {len(asset_df)} assets")
    
    st.divider()
    
    # Data Source Selection
    st.subheader("📊 Data Source")
    
    data_source = st.radio(
        "Select Asset Filter",
        options=["CoinGecko", "Binance Options"],
        index=0,
        help="Choose which assets to display based on market availability"
    )
    
    # Explain the data source
    if data_source == "CoinGecko":
        st.info("📈 All CoinGecko-listed assets (comprehensive coverage)")
        filter_cg = True
        filter_options = False
    else:
        st.info("⚡ Options-tradeable assets only (BTC, ETH, SOL, etc.)")
        filter_cg = False
        filter_options = True
    
    st.divider()
    
    # Asset Selection
    st.subheader("Asset Selection")
    
    # Build token options with filters
    with st.spinner("Loading available assets..."):
        token_options = build_token_options(
            asset_df,
            filter_coingecko=filter_cg,
            filter_binance_options=filter_options
        )
    
    if not token_options:
        st.warning("No assets match your selection. Try switching data source.")
        st.stop()
    
    # Default selections (BTC, ETH, SOL)
    default_tokens = []
    for name in ['BTC', 'ETH', 'SOL']:
        for k in token_options.keys():
            if k.startswith(name):
                default_tokens.append(k)
                break
    
    selected_display = st.multiselect(
        "Select Assets (max 5)",
        options=list(token_options.keys()),
        default=default_tokens[:3] if default_tokens else [],
        max_selections=5,
        help="Choose up to 5 assets for volatility analysis. Legend: CG=CoinGecko, OPT=Options Available"
    )
    
    st.caption(f"Showing {len(token_options)} assets | Source: {data_source}")
    
    st.divider()
    
    # Date Range
    st.subheader("Date Range")
    today = datetime.now().date()
    default_start = today - timedelta(days=180)
    
    start_date = st.date_input(
        "Start Date",
        value=default_start,
        max_value=today,
        help="Beginning of historical data range"
    )
    
    end_date = st.date_input(
        "End Date",
        value=today,
        min_value=start_date,
        max_value=today,
        help="End of historical data range"
    )
    
    st.divider()
    
    # Volatility Windows
    st.subheader("HV Windows")
    windows_input = st.text_input(
        "Window Sizes (days)",
        value="2,3,7,14,30,60,90",
        help="Comma-separated list of volatility calculation windows"
    )
    
    try:
        vol_windows = sorted(list(set([
            int(x.strip()) for x in windows_input.split(',') 
            if x.strip().isdigit() and int(x.strip()) > 0
        ])))
    except:
        vol_windows = [7, 14, 30]
        st.warning("Invalid window input. Using default: 7, 14, 30")
    
    if not vol_windows:
        vol_windows = [7, 14, 30]
    
    st.divider()
    
    # Term Structure Comparison
    st.subheader("Term Structure")
    
    if len(vol_windows) >= 2:
        tenor1 = st.selectbox(
            "Short Tenor",
            vol_windows,
            index=0,
            help="Shorter maturity for term structure analysis"
        )
        
        tenor2 = st.selectbox(
            "Long Tenor",
            vol_windows,
            index=min(1, len(vol_windows)-1),
            help="Longer maturity for term structure analysis"
        )
    else:
        tenor1 = tenor2 = vol_windows[0] if vol_windows else 7
    
    st.divider()
    
    # Options Pricer Settings
    st.subheader("Options Pricer")
    
    days_expiry = st.number_input(
        "Days to Expiry",
        min_value=1,
        max_value=365,
        value=30,
        help="Time to expiration for theoretical option pricing"
    )
    
    strike_range = st.slider(
        "Strike Range (%)",
        min_value=0.5,
        max_value=1.5,
        value=(0.8, 1.2),
        step=0.05,
        help="Strike price range as percentage of spot"
    )
    
    risk_free_rate = st.number_input(
        "Risk-Free Rate",
        min_value=0.0,
        max_value=0.20,
        value=0.05,
        step=0.01,
        format="%.4f",
        help="Annual risk-free interest rate"
    )

# =============================================================================
# MAIN ANALYSIS LOOP
# =============================================================================

if not selected_display:
    st.info("👈 Select one or more assets from the sidebar to begin analysis")
    st.stop()

if not vol_windows:
    st.error("Please specify at least one valid HV window")
    st.stop()

# Convert dates to datetime for CoinGecko
utc = pytz.UTC
start_dt = datetime.combine(start_date, datetime.min.time()).replace(hour=8, minute=0, second=0, microsecond=0)
start_dt = utc.localize(start_dt)
end_dt = datetime.combine(end_date, datetime.min.time()).replace(hour=8, minute=0, second=0, microsecond=0)
end_dt = utc.localize(end_dt)

# Process each selected asset
for idx, display_name in enumerate(selected_display):
    asset_data = token_options.get(display_name)
    if not asset_data:
        continue
    
    coin_symbol, coin_id = asset_data
    
    # Section divider
    st.markdown("---")
    st.markdown(f"## {display_name}")
    
    # Fetch data from CoinGecko
    with st.spinner(f"Fetching {coin_symbol} data from CoinGecko..."):
        raw_df = get_crypto_data_coingecko(
            coin_id=coin_id,
            start_date=start_dt,
            end_date=end_dt
        )
    
    if raw_df.empty:
        st.warning(f"⚠️ No data available for {coin_symbol} from CoinGecko. The asset may not have sufficient price history.")
        continue
    
    # Calculate volatility metrics
    processed_df = calculate_hv_metrics(raw_df, vol_windows)
    
    if processed_df.empty:
        st.warning(f"⚠️ Insufficient data to calculate volatility for {symbol}. Try a shorter HV window or longer date range.")
        continue
    
    # Get latest metrics
    latest = processed_df.iloc[-1]
    current_price = get_current_price_coingecko(coin_id) or latest['close']
    
    # =============================================================================
    # METRICS ROW
    # =============================================================================
    
    m1, m2, m3, m4, m5 = st.columns(5)
    
    with m1:
        st.metric(
            "Current Price",
            f"${current_price:,.4f}" if current_price < 100 else f"${current_price:,.2f}"
        )
    
    with m2:
        rms_714 = latest.get('rms_7_14', 0)
        st.metric(
            "RMS (7,14)",
            f"{rms_714:.2%}",
            help="Root Mean Square volatility of 7d and 14d windows"
        )
    
    with m3:
        rms_23 = latest.get('rms_2_3', 0)
        st.metric(
            "RMS (2,3)",
            f"{rms_23:.2%}",
            help="Root Mean Square volatility of 2d and 3d windows"
        )
    
    with m4:
        hv_short = latest.get(f'hv_{tenor1}', 0)
        st.metric(
            f"{tenor1}d HV",
            f"{hv_short:.2%}"
        )
    
    with m5:
        hv_long = latest.get(f'hv_{tenor2}', 0)
        st.metric(
            f"{tenor2}d HV",
            f"{hv_long:.2%}"
        )
    
    # =============================================================================
    # CHARTS & DATA TABLE
    # =============================================================================
    
    col_chart, col_table = st.columns([2, 3])
    
    with col_chart:
        # ----- Main Volatility Chart -----
        fig = go.Figure()
        
        colors = ['#00d4ff', '#ff6b6b', '#4ecdc4', '#ffe66d', '#a8dadc']
        
        # Plot HV windows
        for i, w in enumerate(vol_windows[:5]):  # Limit to 5 for readability
            color = colors[i % len(colors)]
            fig.add_trace(go.Scatter(
                x=processed_df.index,
                y=processed_df[f'hv_{w}'],
                name=f'{w}d HV',
                line=dict(width=1.5, color=color),
                mode='lines'
            ))
        
        # Highlight RMS volatility
        if 'rms_7_14' in processed_df.columns:
            fig.add_trace(go.Scatter(
                x=processed_df.index,
                y=processed_df['rms_7_14'],
                name='RMS (7,14)',
                line=dict(color='white', width=2.5, dash='dot'),
                mode='lines'
            ))
        
        fig.update_layout(
            title=f"Volatility Term Structure",
            yaxis=dict(
                tickformat='.0%',
                title="Annualized Volatility"
            ),
            xaxis=dict(title="Date"),
            height=450,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode='x unified',
            template='plotly_dark'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # ----- Term Structure Spread Chart -----
        if tenor1 != tenor2:
            fig_spread = go.Figure()
            
            fig_spread.add_trace(go.Scatter(
                x=processed_df.index,
                y=processed_df[f'hv_{tenor1}'],
                name=f'{tenor1}d HV',
                line=dict(color='cyan', width=2),
                mode='lines'
            ))
            
            fig_spread.add_trace(go.Scatter(
                x=processed_df.index,
                y=processed_df[f'hv_{tenor2}'],
                name=f'{tenor2}d HV',
                line=dict(color='magenta', width=2),
                mode='lines'
            ))
            
            # Calculate and plot spread
            spread = processed_df[f'hv_{tenor1}'] - processed_df[f'hv_{tenor2}']
            
            fig_spread.add_trace(go.Scatter(
                x=processed_df.index,
                y=spread,
                name='Spread (Short - Long)',
                line=dict(color='yellow', width=1.5),
                mode='lines',
                yaxis='y2'
            ))
            
            fig_spread.update_layout(
                title=f"Term Structure Spread: {tenor1}d vs {tenor2}d",
                height=300,
                yaxis=dict(
                    tickformat='.0%',
                    title="Volatility"
                ),
                yaxis2=dict(
                    title="Spread",
                    overlaying='y',
                    side='right',
                    tickformat='.2%',
                    showgrid=False
                ),
                xaxis=dict(title="Date"),
                hovermode='x unified',
                legend=dict(orientation="h", y=1.02),
                template='plotly_dark'
            )
            
            st.plotly_chart(fig_spread, use_container_width=True)
    
    with col_table:
        st.subheader("Historical Data")
        
        # Prepare display columns
        display_cols = ['close']
        
        if 'rms_7_14' in processed_df.columns:
            display_cols.append('rms_7_14')
        if 'rms_2_3' in processed_df.columns:
            display_cols.append('rms_2_3')
        
        # Add HV columns (show first 4 windows to save space)
        for w in vol_windows[:4]:
            display_cols.append(f'hv_{w}')
        
        # Create table with most recent data first
        table_df = processed_df[display_cols].copy().sort_index(ascending=False)
        
        # Format for display with UTC timezone indicator
        fmt_df = table_df.copy()
        fmt_df.index = fmt_df.index.strftime('%Y-%m-%d %H:%M UTC')
        
        for col in fmt_df.columns:
            if col == 'close':
                if current_price < 100:
                    fmt_df[col] = fmt_df[col].apply(lambda x: f"${x:.4f}")
                else:
                    fmt_df[col] = fmt_df[col].apply(lambda x: f"${x:.2f}")
            else:
                fmt_df[col] = fmt_df[col].apply(lambda x: f"{x:.2%}")
        
        # Rename columns for clarity
        rename_map = {
            'close': 'Price',
            'rms_7_14': 'RMS(7,14)',
            'rms_2_3': 'RMS(2,3)'
        }
        for w in vol_windows[:4]:
            rename_map[f'hv_{w}'] = f'{w}d HV'
        
        fmt_df = fmt_df.rename(columns=rename_map)
        
        st.dataframe(
            fmt_df,
            height=600,
            use_container_width=True
        )
        
        # =============================================================================
        # DOWNLOAD BUTTON - Export complete dataset
        # =============================================================================
        
        st.markdown("### 📥 Export Data")
        
        # Prepare export dataframe with all calculated metrics
        export_df = processed_df.copy()
        export_df.index.name = 'Date'
        
        # Create CSV
        csv_buffer = BytesIO()
        export_df.to_csv(csv_buffer)
        csv_data = csv_buffer.getvalue()
        
        filename = f"{coin_symbol}_Volatility_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        
        st.download_button(
            label=f"📥 Download {coin_symbol} Volatility Data",
            data=csv_data,
            file_name=filename,
            mime='text/csv',
            key=f"download_{coin_symbol}_{idx}",
            help=f"Export complete volatility dataset for {coin_symbol} from {start_date} to {end_date}"
        )
    
    # =============================================================================
    # OPTIONS PRICER
    # =============================================================================
    
    with st.expander("🛠️ Theoretical Options Pricer", expanded=False):
        st.markdown(f"""
        **Black-Scholes pricing using realized volatility as input**
        
        - Spot: ${current_price:,.2f}
        - Volatility Input: {latest.get('rms_7_14', latest.get('rms_vol', 0)):.2%} (RMS 7,14)
        - Days to Expiry: {days_expiry}
        - Risk-Free Rate: {risk_free_rate:.2%}
        """)
        
        # Use RMS volatility as input
        vol_input = latest.get('rms_7_14', latest.get('rms_vol', 0.5))
        t_years = days_expiry / 365.0
        
        # Generate strikes across the selected range
        strikes = np.linspace(
            current_price * strike_range[0],
            current_price * strike_range[1],
            5
        )
        
        pricer_data = []
        
        for K in strikes:
            k_pct = K / current_price
            
            # Calculate Call
            c_price, c_delta, c_gamma, c_theta, c_vega = black_scholes(
                current_price, K, t_years, risk_free_rate, vol_input, 'call'
            )
            
            # Calculate Put
            p_price, p_delta, p_gamma, p_theta, p_vega = black_scholes(
                current_price, K, t_years, risk_free_rate, vol_input, 'put'
            )
            
            pricer_data.append({
                "Strike": f"${K:,.2f}",
                "K/S": f"{k_pct:.1%}",
                "Call Price": f"${c_price:.2f}",
                "Call Δ": f"{c_delta:.3f}",
                "Put Price": f"${p_price:.2f}",
                "Put Δ": f"{p_delta:.3f}",
                "Γ": f"{c_gamma:.4f}",
                "Vega": f"{c_vega:.2f}",
                "Θ/day": f"{c_theta:.2f}"
            })
        
        pricer_df = pd.DataFrame(pricer_data)
        st.table(pricer_df)
        
        st.caption("Δ = Delta | Γ = Gamma | Θ = Theta (per day) | Vega = per 1% vol change")

# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.caption("Market Maker HV Screener | Data: CoinGecko API | HV calculated at 08:00 UTC using 365-day annualization")
