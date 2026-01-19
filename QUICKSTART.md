# Quick Start Guide - HV Screener

Get up and running in 5 minutes! ⚡

## 🚀 Fastest Start (3 steps)

### 1. Install Dependencies
```bash
pip install streamlit pandas numpy requests plotly scipy pytz
```

### 2. Run the App
```bash
streamlit run hv_screener_enhanced.py
```

### 3. Upload Asset List
- App opens at http://localhost:8501
- Click "Browse files" in the sidebar
- Upload `asset_list.csv`
- Start analyzing! 📊

## 💡 First Time Using the App?

### Recommended Workflow:

**Step 1: Load Your Assets**
- Upload `asset_list.csv` via sidebar (or place it in same directory)
- You should see "✓ Loaded X assets" message

**Step 2: Apply Filters** (Optional)
- Check "Binance Futures" to see only futures-traded assets
- Check "CoinGecko Listed" to see only CG-tracked assets
- Leave unchecked to see all assets

**Step 3: Select Market Type**
- Choose "Perps" for perpetual futures (recommended for market makers)
- Choose "Spot" for spot market analysis

**Step 4: Pick Your Assets**
- Select 1-5 assets from the dropdown
- Default selections: BTC, ETH, SOL
- Look for `[S/F/CG]` indicators showing availability

**Step 5: Configure Analysis**
- **Date Range**: Last 180 days (default) or custom range
- **HV Windows**: Keep default (2,3,7,14,30,60,90) or customize
- **Term Structure**: Select short (7d) vs long (30d) for comparison

**Step 6: Analyze Results**
- View volatility charts and metrics
- Check RMS (7,14) for inventory risk
- Compare term structure spreads
- Export data via download button

## 📋 Common Use Cases

### 1. Daily Vol Check (30 seconds)
```
1. Select your core assets (BTC, ETH, SOL)
2. Check RMS (7,14) metrics at top
3. Compare current levels to charts
4. Done!
```

### 2. Find Futures-Only Assets (1 minute)
```
1. Check "Binance Futures" filter
2. Uncheck "Binance Spot" filter  
3. Browse filtered asset list
4. Select interesting assets
5. Analyze volatility
```

### 3. Export Data for Analysis (2 minutes)
```
1. Select asset (e.g., BTC)
2. Set desired date range
3. Click "📥 Download" button below data table
4. CSV downloads with complete HV data
5. Import into Excel/Python/R for modeling
```

### 4. Compare Spot vs Futures Vol (3 minutes)
```
1. Select asset (e.g., ETH)
2. Set market to "Spot"
3. Note the RMS (7,14) value
4. Switch market to "Perps"
5. Compare RMS values and charts
6. Identify basis trading opportunities
```

### 5. Options Pricing (2 minutes)
```
1. Select asset
2. Expand "🛠️ Theoretical Options Pricer"
3. Set days to expiry and strike range
4. View theoretical prices with Greeks
5. Use RMS (7,14) as vol input for hedging
```

## 🎯 Key Metrics Explained

### RMS (7,14) - PRIMARY METRIC
- **What**: Normalized volatility across 7d and 14d windows
- **Use**: Main input for inventory risk pricing
- **Typical Range**: 30-150% for crypto
- **Red Flag**: Spikes above 200% = extreme volatility regime

### RMS (2,3) - SHORT-TERM METRIC  
- **What**: Ultra-short volatility (2d and 3d windows)
- **Use**: Scalping and intraday risk management
- **Typical Range**: 40-200% for crypto
- **Red Flag**: Divergence from RMS (7,14) = vol regime shift

### HV Windows (7d, 14d, 30d, etc.)
- **What**: Rolling historical volatility
- **Use**: Identify vol trends and regimes
- **Typical Pattern**: Short > Long = backwardation (risk-off)
- **Red Flag**: Rapid convergence = uncertainty spike

### Term Structure Spread
- **What**: Difference between short and long HV
- **Use**: Detect vol regime changes
- **Positive**: Short vol > Long vol (backwardation)
- **Negative**: Long vol > Short vol (contango)

## ⚙️ Pro Tips

### Filtering Mastery
```
✓ Use filters to focus on tradeable assets
✓ "Binance Futures" = assets you can actually hedge
✓ "CoinGecko Listed" = assets with market data
✓ Combine filters: Futures + CoinGecko = best combo
```

### Date Range Selection
```
✓ Last 180 days = good balance of history vs relevance
✓ Last 30 days = recent regime only
✓ Last 365 days = full year for seasonal patterns
✓ Custom range = specific event analysis
```

### HV Window Customization
```
✓ 2,3 = micro scalping
✓ 7,14 = standard market making (RECOMMENDED)
✓ 30,60,90 = position trading
✓ Mix tenors to see full term structure
```

### Export Strategy
```
✓ Export daily for record-keeping
✓ Save before major events (FOMC, NFP, etc.)
✓ Build historical database for backtesting
✓ Track your own vol predictions vs realized
```

## 🔥 Power User Shortcuts

### Keyboard Navigation
- `Tab` - Navigate between controls
- `Enter` - Confirm selections
- `Esc` - Close expanded sections
- Browser refresh (`Cmd+R` / `Ctrl+R`) - Reload app

### URL Parameters (Streamlit Cloud only)
Share links with pre-selected settings:
```
https://your-app.streamlit.app/?asset=BTC&market=perps
```

### Quick Filters
Save time by creating filtered views:
1. Set your preferred filters
2. Select your core assets
3. Bookmark the page
4. Return to same configuration instantly

## 🆘 Quick Troubleshooting

**Asset list won't load?**
→ Use the file uploader in sidebar

**No data for my asset?**
→ Check if it's available on Binance (use filters)

**Charts not showing?**
→ Reduce date range or HV windows

**Slow loading?**
→ Select fewer assets (max 3 recommended)

**Download not working?**
→ Try different browser or check download folder permissions

## 📚 Next Steps

Once you're comfortable with basics:

1. **Read TECHNICAL_NOTE_UTC.md** - Understand 08:00 UTC calculations
2. **Read DEPLOYMENT_GUIDE.md** - Deploy your own instance
3. **Customize HV windows** - Tailor to your trading style
4. **Build historical database** - Export data regularly
5. **Integrate with your tools** - Feed data into risk models

## 🎓 Learning Resources

- **Term Structure**: Watch how short/long vol relationships change
- **Vol Regimes**: Track when RMS spikes and compare to market events
- **Cross-Asset**: Compare BTC, ETH, SOL to see correlation patterns
- **Spot vs Futures**: Identify basis trading opportunities

## 💬 Remember

- **Start simple**: BTC + Perps + default settings
- **Add complexity**: More assets, custom windows, filters
- **Export often**: Build your historical database
- **Compare markets**: Spot vs Futures for arbitrage
- **Trust the data**: 08:00 UTC snapshots are standardized

---

Ready to dive deeper? Check out the full README.md for comprehensive documentation! 📖
