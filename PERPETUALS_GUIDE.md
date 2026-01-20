# Perpetual Futures Data - Quick Reference Guide

## Data Fields Explained

### Price & Volume Data
- **close_price**: Daily closing price in USDT
- **volume**: Base asset volume (e.g., BTC traded)
- **quote_volume**: USDT volume
- **trades**: Number of trades executed

### Funding Rate
- **funding_rate**: Average funding rate for the day
- **annualized_funding_rate**: funding_rate × 3 × 365
- Funding happens every 8 hours (00:00, 08:00, 16:00 UTC)
- Formula: `Payment = Position Value × Funding Rate`

#### Funding Rate Interpretation
| Rate Range | Meaning | Trading Implication |
|------------|---------|-------------------|
| > +0.10% | Strong bullish sentiment | Consider shorts, longs overpaying |
| +0.05% to +0.10% | Moderate bullish | Normal bull market |
| +0.01% to +0.05% | Neutral to slightly bullish | Balanced market |
| -0.01% to +0.01% | Neutral | Balanced market |
| -0.05% to -0.01% | Neutral to slightly bearish | Balanced to bearish |
| -0.10% to -0.05% | Moderate bearish | Normal bear market |
| < -0.10% | Strong bearish sentiment | Consider longs, shorts overpaying |

### Open Interest
- **open_interest**: Total number of open contracts
- **open_interest_value**: Total USD value of all open positions

#### Open Interest Interpretation
| Scenario | Price | OI | Meaning |
|----------|-------|-----|---------|
| Strong Uptrend | ↑ | ↑ | New longs entering, healthy rally |
| Weak Rally | ↑ | ↓ | Shorts covering, not sustainable |
| Strong Downtrend | ↓ | ↑ | New shorts entering, healthy decline |
| Weak Decline | ↓ | ↓ | Longs exiting, potential bottom |

### Historical Volatility
Standard HV metrics for all windows (7d, 14d, 30d, 60d, 90d):
- Annualized volatility based on daily returns
- Expressed as decimal (0.50 = 50% annual volatility)

### Parkinson Volatility
Alternative volatility estimator using high-low range:
- Generally more efficient than close-to-close
- Better captures intraday volatility
- Useful for comparing against close-based HV

## Trading Strategies Using This Data

### 1. Funding Rate Arbitrage
**Setup**: Monitor funding rates across exchanges and assets
**Entry**: 
- Long when funding < -0.10% (collect funding from shorts)
- Short when funding > +0.10% (collect funding from longs)
**Exit**: When funding returns to -0.01% to +0.01% range
**Risk**: Use HV to size position (higher HV = smaller size)

### 2. Volatility Breakout
**Setup**: Look for low HV followed by OI increase
**Signal**: HV_30d < 50% + OI increasing > 20% in 7 days
**Entry**: Breakout direction with OI confirmation
**Stop**: 2 × HV_7d from entry
**Target**: 4 × HV_7d from entry

### 3. Mean Reversion on Extremes
**Setup**: Extreme funding + high volatility
**Entry Conditions**:
- Funding > +0.15% AND HV_7d > HV_30d × 1.5 → Short
- Funding < -0.15% AND HV_7d > HV_30d × 1.5 → Long
**Exit**: Funding returns to ±0.05% or 3-day time stop
**Position Size**: Inverse to HV (higher HV = smaller position)

### 4. Trend Following with OI Confirmation
**Setup**: Use OI to confirm trend strength
**Rules**:
- Uptrend: Price up + OI up + Funding < 0.15%
- Downtrend: Price down + OI up + Funding > -0.15%
**Entry**: Pullback to 7-day MA with OI support
**Stop**: Below/above 14-day MA
**Size**: Based on HV_14d relative to HV_60d

### 5. Market Making Spread Adjustment
**Formula**: `Spread = Base_Spread × (1 + HV_multiplier) × (1 + Funding_adjustment)`

**HV Multiplier**:
- HV < 30%: 1.0×
- HV 30-60%: 1.2×
- HV 60-100%: 1.5×
- HV > 100%: 2.0×

**Funding Adjustment**:
- Funding > +0.10%: Widen ask (1.1×)
- Funding < -0.10%: Widen bid (1.1×)
- |Funding| > 0.20%: Widen both (1.2×)

## Data Analysis Workflow

### Step 1: Load the Data
```python
import pandas as pd

# Load full dataset
df = pd.read_csv('hv_data_full.csv')
df['date'] = pd.to_datetime(df['date'])

# Load summary
summary = pd.read_csv('hv_summary_stats.csv')
```

### Step 2: Filter for Specific Analysis
```python
# Get data for specific asset
btc_data = df[df['symbol'] == 'BTC'].copy()

# Get recent data (last 30 days)
recent = btc_data.tail(30)

# Get assets with extreme funding
extreme_funding = summary[abs(summary['current_funding_rate']) > 0.10]

# Get high volatility assets
high_vol = summary[summary['current_hv_30d'] > 0.70]
```

### Step 3: Calculate Derived Metrics
```python
# Funding vs volatility ratio
df['funding_vol_ratio'] = df['annualized_funding_rate'] / df['hv_30d']

# OI change rate
df['oi_change_pct'] = df.groupby('symbol')['open_interest'].pct_change()

# Volume to OI ratio
df['volume_oi_ratio'] = df['volume'] / df['open_interest']

# Volatility term structure
df['vol_term_structure'] = df['hv_7d'] / df['hv_30d']
```

### Step 4: Identify Trading Opportunities
```python
# Extreme funding opportunities
opportunities = df[
    ((df['funding_rate'] > 0.10) & (df['hv_7d'] > df['hv_30d'] * 1.3)) |
    ((df['funding_rate'] < -0.10) & (df['hv_7d'] > df['hv_30d'] * 1.3))
].copy()

# Trend confirmation
strong_trends = df[
    ((df['close_price'] > df.groupby('symbol')['close_price'].shift(7).transform('mean')) & 
     (df['oi_change_pct'] > 0)) |
    ((df['close_price'] < df.groupby('symbol')['close_price'].shift(7).transform('mean')) & 
     (df['oi_change_pct'] > 0))
]
```

## Red Flags & Risk Signals

### High Risk Conditions
1. **HV > 150%**: Extreme volatility, reduce position sizes significantly
2. **Funding > ±0.30%**: Market extremely one-sided, reversal risk high
3. **OI spike > 50% in 24h**: Potential for violent liquidations
4. **Volume < 10% of OI**: Low liquidity, wide slippage expected
5. **Vol term structure inverted**: hv_7d > hv_30d × 2 = market stress

### Position Size Guidelines
Based on 30-day HV:
- HV < 30%: Up to 100% of base position size
- HV 30-60%: 50-75% of base position size
- HV 60-100%: 25-50% of base position size
- HV > 100%: 10-25% of base position size

### Stop Loss Guidelines
Based on 7-day HV:
- Normal: 1.5 × HV_7d
- Volatile (HV_7d > 100%): 1.0 × HV_7d
- Extreme (HV_7d > 150%): 0.75 × HV_7d

## Key Correlations to Monitor

1. **Funding vs Price**: Usually positively correlated
2. **OI vs Volume**: Rising OI with declining volume = potential reversal
3. **HV vs Funding**: Often inversely correlated (high vol = lower funding)
4. **Parkinson vs Close-based HV**: Should be similar; divergence = intraday vs overnight moves

## Next Steps

1. **Visualization**: Create time series charts of HV, funding, and OI
2. **Backtesting**: Test strategies on historical data
3. **Alerts**: Set up monitoring for extreme conditions
4. **Real-time**: Implement live data feeds for active trading
5. **Cross-asset**: Analyze correlations between assets

## Resources

- Binance Futures Documentation: https://binance-docs.github.io/apidocs/futures/en/
- Funding Rate Explained: https://www.binance.com/en/support/faq/funding-rate
- Historical Volatility Models: Hull, J. (2018). Options, Futures, and Other Derivatives
