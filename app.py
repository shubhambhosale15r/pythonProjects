from flask import Flask, render_template, request, jsonify
import mysql.connector
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import requests
import os

app = Flask(__name__)

# Database connection details
db_config = {
    'user': 'root',
    'password': 'PassworD@1',
    'host': 'localhost',
    'database': 'stock_data'
}

yahoo_finance_base_url = "https://query1.finance.yahoo.com/v8/finance/chart/"

def fetch_data(symbol):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    response = requests.get(f"{yahoo_finance_base_url}{symbol}", headers=headers)
    if response.status_code == 200:
        try:
            data = response.json()
            if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                result = data['chart']['result'][0]['meta']
                stock_data = {
                    "symbol": symbol,
                    "regularMarketPrice": result.get("regularMarketPrice", "N/A"),
                    "fiftyTwoWeekHigh": result.get("fiftyTwoWeekHigh", "N/A"),
                    "fiftyTwoWeekLow": result.get("fiftyTwoWeekLow", "N/A"),
                    "regularMarketDayHigh": result.get("regularMarketDayHigh", "N/A"),
                    "regularMarketDayLow": result.get("regularMarketDayLow", "N/A"),
                    "regularMarketVolume": result.get("regularMarketVolume", "N/A"),
                    "previousClose": result.get("previousClose", "N/A"),
                    "currency": result.get("currency", "N/A"),
                    "regularMarketTime": datetime.fromtimestamp(result.get("regularMarketTime", 0)).strftime('%Y-%m-%d %H:%M:%S') if result.get("regularMarketTime") else "N/A"
                }
                return stock_data
        except ValueError as e:
            print("Error decoding JSON:", e)
            return None
    return None

def plot_stock_chart(symbol):
    stock = yf.Ticker(symbol)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    data = stock.history(start=start_date, end=end_date)
    static_dir = 'D:/pyProject/flaskProject/static'
    
    if data.empty:
        print(f"No historical data available for {symbol}.")
        return None
    
    plt.figure(figsize=(10, 5))
    plt.plot(data.index, data['Close'], label='Closing Price', color='blue')
    plt.title(f'{symbol} Stock Price - Last Month')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    
    chart_filename = f'{symbol}_chart.png'
    chart_path = os.path.join(static_dir, chart_filename)
    plt.savefig(chart_path)
    plt.close()
    
    return f'static/{chart_filename}'

def update_mysql(stock_data):
    if not stock_data:
        print("No data to update in MySQL.")
        return

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    sql = """
    INSERT INTO stock_price (symbol, regular_market_price, fifty_two_week_high, fifty_two_week_low, regular_market_day_high, regular_market_day_low, regular_market_volume, previous_close, currency, market_time)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    regular_market_price = VALUES(regular_market_price),
    fifty_two_week_high = VALUES(fifty_two_week_high),
    fifty_two_week_low = VALUES(fifty_two_week_low),
    regular_market_day_high = VALUES(regular_market_day_high),
    regular_market_day_low = VALUES(regular_market_day_low),
    regular_market_volume = VALUES(regular_market_volume),
    previous_close = VALUES(previous_close),
    currency = VALUES(currency),
    market_time = VALUES(market_time);
    """
    values = (
        stock_data["symbol"],
        stock_data["regularMarketPrice"],
        stock_data["fiftyTwoWeekHigh"],
        stock_data["fiftyTwoWeekLow"],
        stock_data["regularMarketDayHigh"],
        stock_data["regularMarketDayLow"],
        stock_data["regularMarketVolume"],
        stock_data["previousClose"],
        stock_data["currency"],
        stock_data["regularMarketTime"]
    )

    cursor.execute(sql, values)
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    stock_data = None
    chart_path = None
    if request.method == 'POST':
        symbol = request.form['symbol']
        stock_data = fetch_data(symbol)
        if stock_data:
            update_mysql(stock_data)
            chart_path = plot_stock_chart(symbol)
        
        return render_template('index.html', stock_data=stock_data, symbol=symbol, chart_path=chart_path, datetime=datetime)
    return render_template('index.html', stock_data=stock_data, datetime=datetime)

@app.route('/get_stock_data', methods=['GET'])
def get_stock_data():
    symbol = request.args.get('symbol')
    if symbol:
        stock_data = fetch_data(symbol)
        if stock_data:
            update_mysql(stock_data)  # Update database each time this endpoint is called
            return jsonify(stock_data)
    return jsonify({'error': 'No data found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
