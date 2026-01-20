# Historical Volatility Dashboard - Data Collector

## Overview
This Python script collects historical volatility (HV) data for cryptocurrency assets from multiple sources for market making purposes.

**Date Range:** January 1, 2025 to January 17, 2026

**Data Sources:**
- CoinGecko API (primary source - most comprehensive coverage)
- Binance Perpetual Futures API (OHLCV, funding rates, open interest)
- Kraken API (backup for major pairs)

## Features

### Data Collection
- Fetches daily historical price data for 100+ crypto assets
- **Enhanced Binance Perpetuals support**:
  - OHLCV data (Open, High, Low, Close, Volume)
  - Funding rate history (3x daily funding)
  - Open interest and open interest value
  - Trade count and taker volume
- Handles API rate limiting automatically
- Falls back to alternative sources if primary source fails
- Tracks which data source was used for each asset

### Historical Volatility Calculation
Calculates annualized historical volatility for multiple time windows:
- **7-day HV**: Short-term volatility
- **14-day HV**: Two-week volatility
- **30-day HV**: Monthly volatility (standard for options pricing)
- **60-day HV**: Quarter volatility
- **90-day HV**: Long-term volatility

**Additional volatility estimators:**
- **Parkinson Volatility**: Uses high-low range for more efficient estimation
- **Close-to-Close**: Traditional log return based HV

### Perpetual Futures Specific Metrics
- **Funding Rate**: Average daily funding rate
- **Annualized Funding Rate**: Funding rate × 3 × 365 (for comparison)
- **Open Interest**: Number of open contracts
- **Open Interest Value**: Total value of open positions in USD
- **Volume Metrics**: Base volume, quote volume, trade counts

### Formula
```
HV = σ(log returns) × √365
```
where σ is the standard deviation of log returns over the window period.

## Installation

### Requirements
- Python 3.8+
- pip

### Setup
```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

**Option 1: Place asset_list.csv in the same folder**
```bash
# Navigate to your project folder
cd C:\Users\Federico\Desktop\Python\HV

# Run the script
python hv_collector.py
```

**Option 2: Specify the path to asset_list.csv**
```bash
python hv_collector.py path/to/asset_list.csv
```

The script will:
1. Load the asset list from `asset_list.csv`
2. Fetch price data for each asset from available APIs
3. Calculate historical volatility metrics
4. Export results to CSV files in the current directory

### Output Files

**1. hv_data_full.csv**
- Complete dataset with daily HV calculations and perpetual futures data
- Columns:
  - `symbol`: Asset symbol (e.g., BTC, ETH)
  - `date`: Date of the data point
  - `close_price`: Closing price in USD
  - `volume`: Trading volume (Binance perpetuals)
  - `quote_volume`: Quote asset volume (Binance perpetuals)
  - `trades`: Number of trades (Binance perpetuals)
  - `funding_rate`: Daily average funding rate (Binance perpetuals)
  - `annualized_funding_rate`: Annualized funding rate (Binance perpetuals)
  - `open_interest`: Number of open contracts (Binance perpetuals)
  - `open_interest_value`: USD value of open interest (Binance perpetuals)
  - `hv_7d`: 7-day historical volatility (annualized)
  - `hv_14d`: 14-day historical volatility
  - `hv_30d`: 30-day historical volatility
  - `hv_60d`: 60-day historical volatility
  - `hv_90d`: 90-day historical volatility
  - `parkinson_vol_7d`: 7-day Parkinson volatility (if available)
  - `parkinson_vol_14d`: 14-day Parkinson volatility (if available)
  - `parkinson_vol_30d`: 30-day Parkinson volatility (if available)
  - `parkinson_vol_60d`: 60-day Parkinson volatility (if available)
  - `parkinson_vol_90d`: 90-day Parkinson volatility (if available)
  - `data_sources`: Source(s) of the data (coingecko/binance/kraken)

**2. hv_summary_stats.csv**
- Summary statistics for each asset
- Columns:
  - Asset identification
  - Data coverage (number of points, date range)
  - Price statistics (avg, min, max)
  - Volume statistics (avg volume, quote volume, trades)
  - Funding rate statistics (avg and current)
  - Open interest statistics (avg and current)
  - Average HV for each window
  - Current (most recent) HV for each window
  - Average Parkinson volatility for each window
  - Data sources used

## API Rate Limits

### CoinGecko (Free Tier)
- 50 calls per minute
- Script includes 1.2s delays between calls
- Automatically retries on rate limit (429 error)

### Binance Futures
- Weight-based limits
- Script includes 0.5s delays between requests
- 1500 candles per request limit

### Kraken
- 15-20 calls per minute (Tier 0)
- Script includes 1s delays between calls

## Understanding Historical Volatility

### What is HV?
Historical Volatility (HV) measures the actual price movement of an asset over a specific period. It's annualized and expressed as a percentage.

### Interpretation
- **Low HV (<30%)**: Stable, low-risk asset
- **Medium HV (30-70%)**: Moderate volatility
- **High HV (>70%)**: Volatile asset with large price swings
- **Very High HV (>100%)**: Extremely volatile

### Market Making Applications
1. **Options Pricing**: HV is a key input for pricing models
2. **Risk Management**: Helps size positions appropriately
3. **Spread Setting**: Higher HV → wider spreads needed
4. **Inventory Management**: High HV requires tighter risk controls
5. **Strategy Selection**: Different strategies for different volatility regimes
6. **Perpetual Futures Trading**:
   - **Funding Rate Analysis**: Positive funding = longs pay shorts (bullish sentiment)
   - **Open Interest Trends**: Rising OI with price = strong trend, falling OI = weakening trend
   - **Volume Analysis**: Compare volume to OI for market activity insights
   - **Funding + Volatility**: High funding + high vol = potential reversal opportunities

## Understanding Perpetual Futures Metrics

### Funding Rate
- Payment between longs and shorts every 8 hours
- Positive rate: Longs pay shorts (market is bullish)
- Negative rate: Shorts pay longs (market is bearish)
- Typical range: -0.1% to +0.1% per 8h period
- Annualized: Rate × 3 × 365

### Open Interest (OI)
- Total number of outstanding perpetual contracts
- Rising OI + Rising Price = Strong bullish trend
- Rising OI + Falling Price = Strong bearish trend  
- Falling OI = Positions being closed, trend weakening
- OI Value = OI × Mark Price (total notional value)

### Trading Applications
**1. Mean Reversion on Funding**
- Extreme positive funding (>0.1%) + high vol = potential short opportunity
- Extreme negative funding (<-0.1%) + high vol = potential long opportunity

**2. Trend Confirmation**
- Price up + OI up + Moderate funding = Healthy uptrend
- Price up + OI down = Weak rally, shorts covering

**3. Risk Management**
- High HV + High OI = Market is crowded, use tighter stops
- High HV + Low volume = Low liquidity, reduce position size

## Script Architecture

### Classes

**HistoricalVolatilityCollector**
- Main class handling data collection and processing
- Methods:
  - `fetch_coingecko_data()`: Fetches from CoinGecko API
  - `fetch_binance_futures_data()`: Fetches from Binance Futures
  - `fetch_kraken_options_iv()`: Fetches from Kraken
  - `calculate_historical_volatility()`: Calculates HV from price series
  - `calculate_hv_metrics()`: Calculates multi-window HV for dataset
  - `collect_all_data()`: Orchestrates collection for all assets
  - `export_to_csv()`: Exports data to CSV
  - `generate_summary_stats()`: Creates summary statistics

### Data Flow
1. Load asset list from CSV
2. For each asset:
   - Try CoinGecko (primary)
   - Fall back to Binance if needed
   - Fall back to Kraken if needed
3. Calculate log returns from prices
4. Calculate rolling HV for multiple windows
5. Aggregate all data
6. Export to CSV files

## Troubleshooting

### No Data for Specific Asset
- Check if the CoinGecko ID is correct in asset_list.csv
- Verify the asset is listed on Binance Futures (requires USDT pair)
- Check logs for specific API errors

### Rate Limiting Issues
- Increase sleep times in the code
- Consider using CoinGecko Pro API for higher limits
- Process assets in smaller batches

### Missing Historical Data
- Some assets may not have data going back to Jan 1, 2025
- Newer tokens will have shorter histories
- Check the summary stats file to see actual date ranges

## Customization

### Modify Date Range
```python
self.start_date = datetime(2025, 1, 1)  # Change start date
self.end_date = datetime(2026, 1, 17)   # Change end date
```

### Change Volatility Windows
```python
windows = [7, 14, 30, 60, 90]  # Add or remove windows
```

### Add New Data Sources
Implement a new fetch method following the pattern:
```python
def fetch_new_source_data(self, symbol: str) -> Optional[pd.DataFrame]:
    # Return DataFrame with 'date' and 'price' columns
    pass
```

## Performance Notes

- Expected runtime: 2-4 hours for 100+ assets (due to rate limits)
- Memory usage: ~500MB for full dataset
- Output file sizes:
  - hv_data_full.csv: ~50-100MB
  - hv_summary_stats.csv: ~50KB

## Next Steps

After collecting the data, you can:
1. Build visualization dashboards (Plotly, Dash, Streamlit)
2. Implement real-time updates
3. Add implied volatility from options markets
4. Calculate volatility surfaces
5. Build trading signals based on HV patterns
6. Compare realized vs implied volatility

## License
This code is provided as-is for market making and trading analysis purposes.

## Disclaimer
This tool is for informational purposes only. Historical volatility does not predict future volatility. Always conduct your own analysis before making trading decisions.
