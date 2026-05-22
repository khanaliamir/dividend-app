import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. App Styling & Layout
st.set_page_config(page_title="Dividend Backtester", layout="wide")
st.title("📈 Custom Tactical Stock & Dividend Yield Backtester")
st.markdown("### Optimized for Salaried Investors: Monthly regular SIP + Max 1 Dip-Buy per month.")

# 2. Sidebar Control Panel for User Input
st.sidebar.header("⚙️ Strategy Parameters")

# NEW: Pre-mapped dictionary of popular high-yield dividend stocks
ticker_dict = {
    "Coal India Ltd. (NSE)": "COALINDIA.NS",
    "Hindustan Zinc Ltd. (NSE)": "HINDZINC.NS",
    "ITC Ltd. (NSE)": "ITC.NS",
    "TCS Ltd. (NSE)": "TCS.NS",
    "Infosys Ltd. (NSE)": "INFY.NS",
    "REC Ltd. (NSE)": "REC.NS",
    "PFC Ltd. (NSE)": "PFC.NS",
    "Realty Income - Monthly Dividend (US)": "O",
    "Apple Inc. (US)": "AAPL",
    "Microsoft Corp. (US)": "MSFT",
    "🔍 Enter a Custom Ticker...": "CUSTOM"
}

# User selects a friendly name instead of typing codes
selected_display = st.sidebar.selectbox("Choose a Stock / Company", options=list(ticker_dict.keys()))

# If the user selects the custom option, show a hidden text box to let them type manually
if selected_display == "🔍 Enter a Custom Ticker...":
    ticker = st.sidebar.text_input("Type Global Ticker Symbol (e.g., Reliance is RELIANCE.NS)", value="RELIANCE.NS").strip()
else:
    ticker = ticker_dict[selected_display]

start_year = st.sidebar.slider("Start Year", 2000, 2026, 2011)
end_year = st.sidebar.slider("End Year", 2001, 2026, 2026)

# Dynamically detect currency symbol based on asset selection rules
currency = "₹"
if ".NS" not in ticker.upper() and ".BO" not in ticker.upper():
    if ".L" in ticker.upper():
        currency = "£"
    else:
        currency = "\$"

monthly_sip = st.sidebar.number_input(f"Regular Monthly SIP Amount ({currency})", value=10000, step=1000)
dip_trigger = st.sidebar.slider("Dip Target (% below 52W High)", 1, 20, 5) / 100
dip_buy_amt = st.sidebar.number_input(f"Extra Monthly Cash Input on Dip ({currency})", value=5000, step=500)

# Strategy Choice Toggles
st.sidebar.markdown("---")
st.sidebar.header("🔄 Strategy Configuration")
drip_enabled = st.sidebar.toggle("Reinvest Dividends (DRIP Mode)", value=False)

price_mode = st.sidebar.selectbox(
    "Price Data Display Mode",
    options=["Raw Market Prices", "Corporate Adjusted Prices"],
    help="Raw Market Prices shows the exact historical price traded on that day. Corporate Adjusted subtracts payouts/dividends retroactively."
)

# 3. Execution Core
if st.sidebar.button("🚀 Run Backtest Engine"):
    with st.spinner("Fetching historical market databases..."):
        stock = yf.Ticker(ticker)
        
        auto_adjust_setting = True if price_mode == "Corporate Adjusted Prices" else False
        df = stock.history(start=f"{start_year}-01-01", end=f"{end_year}-05-22", actions=True, auto_adjust=auto_adjust_setting)
        
        if df.empty:
            st.error("Error fetching data. Please ensure the ticker format is correct.")
        else:
            total_invested = 0
            shares_held = 0
            total_dividends_collected = 0
            dip_buy_count = 0  
            
            dip_log_dates = []
            dip_log_prices = []
            
            history_dates = []
            history_wealth = []
            history_investment = []
            
            # Dictionary structures to accumulate dividends and share counts by calendar year
            annual_dividend_tracker = {}
            annual_shares_tracker = {}
            
            df['52W_High'] = df['Close'].rolling(window=252, min_periods=1).max()
            monthly_markers = df.resample('MS').first().index

            for date, row in df.iterrows():
                current_price = row['Close']
                current_year = date.year
                
                # Initialize tracking containers for new years seamlessly
                if current_year not in annual_dividend_tracker:
                    annual_dividend_tracker[current_year] = 0.0
                
                # EXECUTION DAY: Only evaluate actions on the 1st trading day of the month
                if date in monthly_markers:
                    shares_held += (monthly_sip / current_price)
                    total_invested += monthly_sip
                    
                    if current_price <= (row['52W_High'] * (1 - dip_trigger)):
                        shares_held += (dip_buy_amt / current_price)
                        total_invested += dip_buy_amt
                        dip_buy_count += 1  
                        
                        dip_log_dates.append(date.strftime('%Y-%m-%d'))
                        dip_log_prices.append(current_price)
                
                # Dividend payout distribution tracking
                if 'Dividends' in row and row['Dividends'] > 0:
                    cash_received = shares_held * row['Dividends']
                    total_dividends_collected += cash_received
                    annual_dividend_tracker[current_year] += cash_received 
                    
                    if drip_enabled:
                        shares_held += (cash_received / current_price)
                    
                # Store structural closing share value counts for each year
                annual_shares_tracker[current_year] = shares_held
                
                history_dates.append(date)
                history_investment.append(total_invested)
                
                if drip_enabled:
                    history_wealth.append(shares_held * current_price)
                else:
                    history_wealth.append((shares_held * current_price) + total_dividends_collected)
            
            final_share_price = df['Close'].iloc[-1]
            equity_market_value = shares_held * final_share_price
            net_portfolio_worth = equity_market_value if drip_enabled else (equity_market_value + total_dividends_collected)
            
            avg_purchase_price = total_invested / shares_held if shares_held > 0 else 0
            
            last_year_dividends = df['Dividends'].resample('YE').sum().iloc[-1] if ('Dividends' in df and not df['Dividends'].empty) else 0
            personal_yield_on_cost = (last_year_dividends / avg_purchase_price) * 100 if avg_purchase_price > 0 else 0
            market_dividend_yield = (last_year_dividends / final_share_price) * 100 if final_share_price > 0 else 0

            # 4. Display Metrics
            st.markdown("### 📊 Portfolio Valuation Dashboard")
            st.info(f"🎯 **Tactical Execution Summary**: Your buy-the-dip rule triggered exactly **{dip_buy_count} times** during this backtest period, deploying an extra {currency}{dip_buy_count * dip_buy_amt:,.2f} in disciplined capital additions.")
            
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total Invested Principal", f"{currency}{total_invested:,.2f}")
            with m2:
                st.metric("Total Shares Accumulated", f"{shares_held:,.2f}")
            with m3:
                st.metric("Cumulative Dividends Generated", f"{currency}{total_dividends_collected:,.2f}")
            with m4:
                st.metric("Final Portfolio Value", f"{currency}{net_portfolio_worth:,.2f}")
                
            # 5. Cost Baseline Metrics
            st.markdown("### 💸 Cost Analysis & Personal Yield Metrics")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Your Average Purchase Price", f"{currency}{avg_purchase_price:,.2f}")
            with c2:
                st.metric("Current Stock Market Price", f"{currency}{final_share_price:,.2f}")
            with c3:
                st.metric("Your Personal Yield-on-Cost (YoC)", f"{personal_yield_on_cost:.2f}%")
            with c4:
                st.metric("Standard Market Dividend Yield", f"{market_dividend_yield:.2f}%")
            
            # 6. Interactive Line Graph Construction
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=history_dates, y=history_investment, name="Total Capital Invested", line=dict(color='orange', width=2)))
            fig.add_trace(go.Scatter(x=history_dates, y=history_wealth, name="Total Portfolio Value", line=dict(color='green', width=3)))
            fig.update_layout(title=f"Salaried Growth Timeline ({price_mode})", xaxis_title="Timeline", yaxis_title=f"Value ({currency})", legend=dict(x=0.01, y=0.99))
            st.plotly_chart(fig, use_container_width=True)
            
            # 7. Annual Dividend Breakdown Ledger
            st.markdown("### 📅 Annual Income Progression Ledger")
            years_list = sorted(list(annual_dividend_tracker.keys()))
            
            annual_df = pd.DataFrame({
                "Calendar Year": years_list,
                "Shares Held at Year End": [f"{annual_shares_tracker[y]:,.2f}" for y in years_list],
                f"Total Cash Dividends Received ({currency})": [f"{annual_dividend_tracker[y]:.2f}" for y in years_list],
                "Estimated Monthly Avg Income": [f"{(annual_dividend_tracker[y]/12):.2f}" for y in years_list]
            })
            st.dataframe(annual_df, use_container_width=True, hide_index=True)
            
            annual_csv = annual_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Annual Data as CSV",
                data=annual_csv,
                file_name=f"{ticker}_annual_progression.csv",
                mime="text/csv"
            )
            
            # 8. Historical Purchase Ledger Dropdown Table
            st.markdown("### 📜 Tactical Action Logs")
            with st.expander(f"View exact historical dates when Buy-the-Dip triggered ({price_mode})"):
                if len(dip_log_dates) > 0:
                    log_df = pd.DataFrame({
"Execution Date (Monthly Payday)": dip_log_dates,f"Stock Entry Price ({currency})": [f"{p:,.2f}" for p in dip_log_prices],"Action Status": ["Extra Cash Deployed Successfully"] * len(dip_log_dates)})st.dataframe(log_df, use_container_width=True)log_csv = log_df.to_csv(index=False).encode('utf-8')st.download_button(label="📥 Download Tactical Dip Logs as CSV",data=log_csv,file_name=f"{ticker}_tactical_dips.csv",mime="text/csv")else:st.write("No dips matched your exact criteria during this timeline window.")
