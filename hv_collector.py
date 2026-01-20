"""
Historical Volatility Data Collector for Market Making
Collects HV data from Kraken Options, Binance Futures, and CoinGecko API
Date Range: January 1, 2025 to January 17, 2026
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional, Tuple
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HistoricalVolatilityCollector:
    """Collects historical volatility data from multiple sources"""
    
    def __init__(self, asset_list_path: str):
        """
        Initialize the HV collector
        
        Args:
            asset_list_path: Path to the CSV file containing asset list
        """
        self.assets_df = pd.read_csv(asset_list_path)
        self.start_date = datetime(2025, 1, 1)
        self.end_date = datetime(2026, 1, 17)
        
        # Store all collected data
        self.all_hv_data = []
        
        # API endpoints
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.binance_base = "https://fapi.binance.com"
        self.kraken_base = "https://api.kraken.com/0"
        
    def calculate_historical_volatility(self, prices: pd.Series, window: int = 30) -> float:
        """
        Calculate historical volatility (annualized)
        
        Args:
            prices: Series of prices
            window: Rolling window for volatility calculation
            
        Returns:
            Annualized historical volatility as a decimal
        """
        if len(prices) < 2:
            return np.nan
            
        # Calculate log returns
        log_returns = np.log(prices / prices.shift(1))
        
        # Calculate standard deviation of returns
        volatility = log_returns.std()
        
        # Annualize (assuming daily data, 365 days per year)
        annualized_vol = volatility * np.sqrt(365)
        
        return annualized_vol
    
    def calculate_realized_volatility(self, prices: pd.Series, windows: List[int] = [7, 14, 30, 60, 90]) -> Dict[int, float]:
        """
        Calculate realized volatility for multiple windows
        
        Args:
            prices: Series of prices
            windows: List of window sizes in days
            
        Returns:
            Dictionary of window -> volatility
        """
        volatilities = {}
        
        for window in windows:
            if len(prices) >= window:
                recent_prices = prices.tail(window)
                vol = self.calculate_historical_volatility(recent_prices, window)
                volatilities[window] = vol
            else:
                volatilities[window] = np.nan
                
        return volatilities
    
    def fetch_coingecko_data(self, coin_id: str, symbol: str) -> Optional[pd.DataFrame]:
        """
        Fetch historical price data from CoinGecko
        
        Args:
            coin_id: CoinGecko API ID
            symbol: Coin symbol
            
        Returns:
            DataFrame with date and price columns
        """
        if pd.isna(coin_id) or coin_id == 'N/A' or coin_id == '':
            logger.warning(f"No CoinGecko ID for {symbol}")
            return None
            
        try:
            # Convert dates to timestamps
            from_timestamp = int(self.start_date.timestamp())
            to_timestamp = int(self.end_date.timestamp())
            
            url = f"{self.coingecko_base}/coins/{coin_id}/market_chart/range"
            params = {
                'vs_currency': 'usd',
                'from': from_timestamp,
                'to': to_timestamp
            }
            
            logger.info(f"Fetching CoinGecko data for {symbol} ({coin_id})")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'prices' in data and len(data['prices']) > 0:
                    df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
                    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df = df[['date', 'price']].sort_values('date')
                    
                    logger.info(f"Successfully fetched {len(df)} data points for {symbol}")
                    return df
                else:
                    logger.warning(f"No price data in response for {symbol}")
                    return None
            elif response.status_code == 429:
                logger.warning(f"Rate limited on CoinGecko for {symbol}. Waiting 60s...")
                time.sleep(60)
                return self.fetch_coingecko_data(coin_id, symbol)
            else:
                logger.error(f"CoinGecko API error for {symbol}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching CoinGecko data for {symbol}: {e}")
            return None
    
    def fetch_binance_futures_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Fetch comprehensive historical data from Binance Perpetual Futures
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            
        Returns:
            DataFrame with date, price, volume, and perpetual-specific data
        """
        try:
            # Binance uses USDT pairs
            binance_symbol = f"{symbol}USDT"
            
            # First, fetch OHLCV data
            klines_url = f"{self.binance_base}/fapi/v1/klines"
            
            # Binance has a limit of 1500 candles per request
            start_time = int(self.start_date.timestamp() * 1000)
            end_time = int(self.end_date.timestamp() * 1000)
            
            all_klines = []
            current_start = start_time
            
            logger.info(f"Fetching Binance Perpetual Futures data for {binance_symbol}")
            
            # Fetch OHLCV data
            while current_start < end_time:
                params = {
                    'symbol': binance_symbol,
                    'interval': '1d',
                    'startTime': current_start,
                    'endTime': end_time,
                    'limit': 1500
                }
                
                response = requests.get(klines_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if not data:
                        break
                    
                    all_klines.extend(data)
                    
                    # Update start time for next batch
                    current_start = data[-1][0] + 1
                    
                    if len(data) < 1500:
                        break
                        
                    time.sleep(0.5)  # Rate limiting
                    
                elif response.status_code == 429:
                    logger.warning(f"Rate limited on Binance for {binance_symbol}. Waiting...")
                    time.sleep(10)
                else:
                    logger.error(f"Binance API error for {binance_symbol}: {response.status_code}")
                    return None
            
            if not all_klines:
                logger.warning(f"No kline data returned for {binance_symbol}")
                return None
            
            # Create DataFrame from klines
            df = pd.DataFrame(all_klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['price'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            df['quote_volume'] = df['quote_volume'].astype(float)
            df['trades'] = df['trades'].astype(int)
            
            # Now fetch funding rate history
            logger.info(f"Fetching funding rate history for {binance_symbol}")
            funding_rates = self.fetch_binance_funding_rates(binance_symbol)
            
            # Fetch open interest history
            logger.info(f"Fetching open interest history for {binance_symbol}")
            open_interest = self.fetch_binance_open_interest(binance_symbol)
            
            # Merge all data
            result = df[['date', 'price', 'volume', 'quote_volume', 'trades']].copy()
            
            if funding_rates is not None:
                result = result.merge(funding_rates, on='date', how='left')
            
            if open_interest is not None:
                result = result.merge(open_interest, on='date', how='left')
            
            result = result.sort_values('date')
            
            logger.info(f"Successfully fetched {len(result)} data points for {binance_symbol} perpetuals")
            return result
                
        except Exception as e:
            logger.error(f"Error fetching Binance perpetual data for {symbol}: {e}")
            return None
    
    def fetch_binance_funding_rates(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Fetch historical funding rates for Binance perpetuals
        
        Args:
            symbol: Binance symbol (e.g., BTCUSDT)
            
        Returns:
            DataFrame with date and funding_rate columns
        """
        try:
            url = f"{self.binance_base}/fapi/v1/fundingRate"
            
            start_time = int(self.start_date.timestamp() * 1000)
            end_time = int(self.end_date.timestamp() * 1000)
            
            all_funding = []
            current_start = start_time
            
            while current_start < end_time:
                params = {
                    'symbol': symbol,
                    'startTime': current_start,
                    'endTime': end_time,
                    'limit': 1000
                }
                
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if not data:
                        break
                    
                    all_funding.extend(data)
                    
                    # Update start time for next batch
                    current_start = data[-1]['fundingTime'] + 1
                    
                    if len(data) < 1000:
                        break
                        
                    time.sleep(0.5)
                    
                elif response.status_code == 429:
                    logger.warning(f"Rate limited on funding rates. Waiting...")
                    time.sleep(10)
                else:
                    # Symbol might not have perpetual futures
                    logger.warning(f"Could not fetch funding rates for {symbol}: {response.status_code}")
                    return None
            
            if all_funding:
                df = pd.DataFrame(all_funding)
                df['date'] = pd.to_datetime(df['fundingTime'], unit='ms')
                df['funding_rate'] = df['fundingRate'].astype(float)
                
                # Aggregate to daily (funding happens every 8 hours, take average)
                daily_funding = df.groupby(df['date'].dt.date).agg({
                    'funding_rate': 'mean'
                }).reset_index()
                daily_funding['date'] = pd.to_datetime(daily_funding['date'])
                
                return daily_funding[['date', 'funding_rate']]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error fetching funding rates for {symbol}: {e}")
            return None
    
    def fetch_binance_open_interest(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Fetch historical open interest for Binance perpetuals
        
        Args:
            symbol: Binance symbol (e.g., BTCUSDT)
            
        Returns:
            DataFrame with date and open_interest columns
        """
        try:
            url = f"{self.binance_base}/futures/data/openInterestHist"
            
            start_time = int(self.start_date.timestamp() * 1000)
            end_time = int(self.end_date.timestamp() * 1000)
            
            params = {
                'symbol': symbol,
                'period': '1d',
                'startTime': start_time,
                'endTime': end_time,
                'limit': 500
            }
            
            all_oi = []
            current_start = start_time
            
            while current_start < end_time:
                params['startTime'] = current_start
                
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if not data:
                        break
                    
                    all_oi.extend(data)
                    
                    # Update start time for next batch
                    current_start = data[-1]['timestamp'] + 86400000  # +1 day in ms
                    
                    if len(data) < 500:
                        break
                        
                    time.sleep(0.5)
                    
                elif response.status_code == 429:
                    logger.warning(f"Rate limited on open interest. Waiting...")
                    time.sleep(10)
                else:
                    logger.warning(f"Could not fetch open interest for {symbol}: {response.status_code}")
                    return None
            
            if all_oi:
                df = pd.DataFrame(all_oi)
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                df['open_interest'] = df['sumOpenInterest'].astype(float)
                df['open_interest_value'] = df['sumOpenInterestValue'].astype(float)
                
                return df[['date', 'open_interest', 'open_interest_value']]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            return None
    
    def fetch_kraken_options_iv(self, symbol: str) -> Optional[Dict]:
        """
        Fetch implied volatility data from Kraken Options
        Note: Kraken Options API is limited. This is a placeholder for options-specific data.
        
        Args:
            symbol: Asset symbol
            
        Returns:
            Dictionary with IV data if available
        """
        try:
            # Kraken spot data (options data requires authenticated API)
            # For public demo, we'll use spot prices
            url = f"{self.kraken_base}/public/OHLC"
            
            # Kraken uses different pair names
            kraken_pairs = {
                'BTC': 'XXBTZUSD',
                'ETH': 'XETHZUSD',
                'XRP': 'XXRPZUSD',
                'SOL': 'SOLUSD',
                'DOGE': 'XDGUSD',
                'ADA': 'ADAUSD',
                'DOT': 'DOTUSD',
                'MATIC': 'MATICUSD',
                'LINK': 'LINKUSD',
                'AVAX': 'AVAXUSD',
                'LTC': 'LTCUSD',
            }
            
            if symbol not in kraken_pairs:
                return None
                
            pair = kraken_pairs[symbol]
            
            params = {
                'pair': pair,
                'interval': 1440,  # Daily
                'since': int(self.start_date.timestamp())
            }
            
            logger.info(f"Fetching Kraken data for {symbol} ({pair})")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'result' in data and pair in data['result']:
                    ohlc_data = data['result'][pair]
                    
                    df = pd.DataFrame(ohlc_data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'
                    ])
                    
                    df['date'] = pd.to_datetime(df['timestamp'], unit='s')
                    df['price'] = df['close'].astype(float)
                    df = df[['date', 'price']].sort_values('date')
                    
                    # Filter to our date range
                    df = df[(df['date'] >= self.start_date) & (df['date'] <= self.end_date)]
                    
                    logger.info(f"Successfully fetched {len(df)} data points for {symbol} from Kraken")
                    return df
                else:
                    logger.warning(f"No data in Kraken response for {symbol}")
                    return None
            else:
                logger.error(f"Kraken API error for {symbol}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching Kraken data for {symbol}: {e}")
            return None
    
    def collect_asset_data(self, row: pd.Series) -> Dict:
        """
        Collect data for a single asset from all available sources
        
        Args:
            row: Row from assets dataframe
            
        Returns:
            Dictionary with collected data
        """
        symbol = row['Coin symbol']
        cg_id = row['CG API ID']
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {symbol}")
        logger.info(f"{'='*60}")
        
        result = {
            'symbol': symbol,
            'coingecko_id': cg_id,
            'data_sources': [],
            'price_data': None
        }
        
        # Try CoinGecko first (most comprehensive)
        if not pd.isna(cg_id) and cg_id not in ['N/A', '']:
            cg_data = self.fetch_coingecko_data(cg_id, symbol)
            if cg_data is not None and len(cg_data) > 0:
                result['price_data'] = cg_data
                result['data_sources'].append('coingecko')
                time.sleep(1.2)  # Rate limiting for free tier (50 calls/min)
        
        # Try Binance if CoinGecko failed or for additional data
        if result['price_data'] is None:
            binance_data = self.fetch_binance_futures_data(symbol)
            if binance_data is not None and len(binance_data) > 0:
                result['price_data'] = binance_data
                result['data_sources'].append('binance')
                time.sleep(0.5)
        
        # Try Kraken as fallback
        if result['price_data'] is None:
            kraken_data = self.fetch_kraken_options_iv(symbol)
            if kraken_data is not None and len(kraken_data) > 0:
                result['price_data'] = kraken_data
                result['data_sources'].append('kraken')
                time.sleep(1)
        
        return result
    
    def calculate_hv_metrics(self, price_data: pd.DataFrame, symbol: str) -> List[Dict]:
        """
        Calculate HV metrics for the price data, including perpetual-specific metrics
        
        Args:
            price_data: DataFrame with date and price columns (may include funding_rate, open_interest)
            symbol: Asset symbol
            
        Returns:
            List of dictionaries with HV metrics by date
        """
        if price_data is None or len(price_data) < 2:
            return []
        
        # Ensure data is sorted by date
        price_data = price_data.sort_values('date').copy()
        price_data['price'] = pd.to_numeric(price_data['price'], errors='coerce')
        price_data = price_data.dropna(subset=['price'])
        
        # Calculate log returns
        price_data['log_return'] = np.log(price_data['price'] / price_data['price'].shift(1))
        
        # Check if we have perpetual-specific data
        has_funding = 'funding_rate' in price_data.columns
        has_oi = 'open_interest' in price_data.columns
        has_volume = 'volume' in price_data.columns
        
        # Calculate rolling volatilities for different windows
        windows = [7, 14, 30, 60, 90]
        
        results = []
        
        for idx, row in price_data.iterrows():
            date = row['date']
            price = row['price']
            
            record = {
                'symbol': symbol,
                'date': date,
                'close_price': price,
            }
            
            # Add volume data if available
            if has_volume:
                record['volume'] = row.get('volume', np.nan)
                record['quote_volume'] = row.get('quote_volume', np.nan)
                record['trades'] = row.get('trades', np.nan)
            
            # Add perpetual-specific metrics
            if has_funding:
                record['funding_rate'] = row.get('funding_rate', np.nan)
                # Annualized funding rate (funding happens 3x per day)
                if not pd.isna(row.get('funding_rate')):
                    record['annualized_funding_rate'] = row['funding_rate'] * 3 * 365
            
            if has_oi:
                record['open_interest'] = row.get('open_interest', np.nan)
                record['open_interest_value'] = row.get('open_interest_value', np.nan)
            
            # Calculate HV for each window
            for window in windows:
                # Get data up to current date
                historical_data = price_data[price_data['date'] <= date].tail(window)
                
                if len(historical_data) >= max(2, window // 2):  # At least half the window
                    vol = self.calculate_historical_volatility(historical_data['price'], window)
                    record[f'hv_{window}d'] = vol
                    
                    # Calculate realized volatility using high-low estimator (Parkinson)
                    if 'high' in historical_data.columns and 'low' in historical_data.columns:
                        parkinson_vol = self.calculate_parkinson_volatility(historical_data)
                        record[f'parkinson_vol_{window}d'] = parkinson_vol
                else:
                    record[f'hv_{window}d'] = np.nan
                    if has_volume:
                        record[f'parkinson_vol_{window}d'] = np.nan
            
            results.append(record)
        
        return results
    
    def calculate_parkinson_volatility(self, data: pd.DataFrame) -> float:
        """
        Calculate Parkinson volatility estimator using high-low prices
        More efficient than close-to-close for intraday ranges
        
        Args:
            data: DataFrame with 'high' and 'low' columns
            
        Returns:
            Annualized Parkinson volatility
        """
        try:
            if 'high' not in data.columns or 'low' not in data.columns:
                return np.nan
            
            high = data['high'].astype(float)
            low = data['low'].astype(float)
            
            # Parkinson formula: sqrt(1/(4*ln(2)) * mean((ln(H/L))^2))
            hl_ratio = np.log(high / low) ** 2
            variance = hl_ratio.mean() / (4 * np.log(2))
            
            # Annualize
            annualized_vol = np.sqrt(variance * 365)
            
            return annualized_vol
        except:
            return np.nan
    
    def collect_all_data(self) -> pd.DataFrame:
        """
        Collect data for all assets and calculate HV metrics
        
        Returns:
            DataFrame with all HV data
        """
        all_records = []
        
        total_assets = len(self.assets_df)
        
        for idx, row in self.assets_df.iterrows():
            logger.info(f"\nProcessing asset {idx + 1}/{total_assets}")
            
            try:
                # Collect price data
                asset_data = self.collect_asset_data(row)
                
                if asset_data['price_data'] is not None:
                    # Calculate HV metrics
                    hv_records = self.calculate_hv_metrics(
                        asset_data['price_data'],
                        asset_data['symbol']
                    )
                    
                    # Add data source info to each record
                    for record in hv_records:
                        record['data_sources'] = ','.join(asset_data['data_sources'])
                    
                    all_records.extend(hv_records)
                    
                    logger.info(f"✓ Collected {len(hv_records)} records for {asset_data['symbol']}")
                else:
                    logger.warning(f"✗ No data collected for {row['Coin symbol']}")
                    
            except Exception as e:
                logger.error(f"Error processing {row['Coin symbol']}: {e}")
                continue
        
        # Convert to DataFrame
        if all_records:
            df = pd.DataFrame(all_records)
            
            # Sort by symbol and date
            df = df.sort_values(['symbol', 'date'])
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Data collection complete!")
            logger.info(f"Total records: {len(df)}")
            logger.info(f"Unique assets: {df['symbol'].nunique()}")
            logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
            logger.info(f"{'='*60}\n")
            
            return df
        else:
            logger.error("No data collected!")
            return pd.DataFrame()
    
    def export_to_csv(self, df: pd.DataFrame, output_path: str = 'hv_data_export.csv'):
        """
        Export collected data to CSV
        
        Args:
            df: DataFrame with HV data
            output_path: Path for output CSV file
        """
        try:
            df.to_csv(output_path, index=False)
            logger.info(f"Data exported to {output_path}")
            logger.info(f"File size: {len(df)} rows x {len(df.columns)} columns")
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
    
    def generate_summary_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate summary statistics for each asset, including perpetual-specific metrics
        
        Args:
            df: DataFrame with HV data
            
        Returns:
            DataFrame with summary statistics
        """
        summary_records = []
        
        for symbol in df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol].copy()
            
            record = {
                'symbol': symbol,
                'data_points': len(symbol_data),
                'date_range_start': symbol_data['date'].min(),
                'date_range_end': symbol_data['date'].max(),
                'avg_price': symbol_data['close_price'].mean(),
                'min_price': symbol_data['close_price'].min(),
                'max_price': symbol_data['close_price'].max(),
            }
            
            # Add volume metrics if available
            if 'volume' in symbol_data.columns:
                record['avg_volume'] = symbol_data['volume'].mean()
                record['avg_quote_volume'] = symbol_data['quote_volume'].mean()
                record['avg_trades'] = symbol_data['trades'].mean()
            
            # Add perpetual-specific metrics if available
            if 'funding_rate' in symbol_data.columns:
                record['avg_funding_rate'] = symbol_data['funding_rate'].mean()
                record['current_funding_rate'] = symbol_data['funding_rate'].iloc[-1] if len(symbol_data) > 0 else np.nan
                if 'annualized_funding_rate' in symbol_data.columns:
                    record['avg_annualized_funding_rate'] = symbol_data['annualized_funding_rate'].mean()
            
            if 'open_interest' in symbol_data.columns:
                record['avg_open_interest'] = symbol_data['open_interest'].mean()
                record['current_open_interest'] = symbol_data['open_interest'].iloc[-1] if len(symbol_data) > 0 else np.nan
                record['avg_open_interest_value'] = symbol_data['open_interest_value'].mean()
            
            # Add average HV for each window
            for window in [7, 14, 30, 60, 90]:
                col = f'hv_{window}d'
                if col in symbol_data.columns:
                    record[f'avg_hv_{window}d'] = symbol_data[col].mean()
                    record[f'current_hv_{window}d'] = symbol_data[col].iloc[-1] if len(symbol_data) > 0 else np.nan
                
                # Add Parkinson volatility if available
                parkinson_col = f'parkinson_vol_{window}d'
                if parkinson_col in symbol_data.columns:
                    record[f'avg_parkinson_vol_{window}d'] = symbol_data[parkinson_col].mean()
            
            record['data_sources'] = symbol_data['data_sources'].iloc[0] if len(symbol_data) > 0 else ''
            
            summary_records.append(record)
        
        return pd.DataFrame(summary_records)


def main():
    """Main execution function"""
    
    print("="*80)
    print("Historical Volatility Data Collector for Market Making")
    print("="*80)
    print(f"Date Range: January 1, 2025 to January 17, 2026")
    print(f"Data Sources: CoinGecko, Binance Futures, Kraken")
    print("="*80)
    print()
    
    # Initialize collector - use relative path or command line argument
    import sys
    import os
    
    if len(sys.argv) > 1:
        asset_list_path = sys.argv[1]
    else:
        # Look for asset_list.csv in current directory
        asset_list_path = 'asset_list.csv'
    
    if not os.path.exists(asset_list_path):
        print(f"ERROR: Cannot find asset list file at: {asset_list_path}")
        print(f"Current directory: {os.getcwd()}")
        print(f"\nUsage: python hv_collector.py [path/to/asset_list.csv]")
        print(f"Or place asset_list.csv in the same directory as the script")
        return
    
    collector = HistoricalVolatilityCollector(asset_list_path)
    
    print(f"Loaded {len(collector.assets_df)} assets from asset list")
    print()
    
    # Collect all data
    print("Starting data collection...")
    print("This may take a while due to API rate limits...")
    print()
    
    hv_data = collector.collect_all_data()
    
    if not hv_data.empty:
        # Export main data to current directory
        output_path = 'hv_data_full.csv'
        collector.export_to_csv(hv_data, output_path)
        
        # Generate and export summary statistics
        summary_stats = collector.generate_summary_stats(hv_data)
        summary_path = 'hv_summary_stats.csv'
        collector.export_to_csv(summary_stats, summary_path)
        
        print("\n" + "="*80)
        print("EXPORT COMPLETE")
        print("="*80)
        print(f"Main data: {output_path}")
        print(f"Summary stats: {summary_path}")
        print()
        print("Summary Statistics:")
        print(summary_stats.to_string())
        print("="*80)
    else:
        print("\nNo data collected. Please check the logs for errors.")


if __name__ == "__main__":
    main()
