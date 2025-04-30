#wwww.BinaryAcademy.uk
#Binary Options Trading Bot with EMA Strategy
#EDITED BY BINARY ACADEMY
#This bot uses EMA strategy to trade binary options on Deriv platform.
#It uses the Deriv API to place trades based on EMA signals.
#The bot is designed to be run in a simulated environment for testing purposes.
#It is not intended for live trading without proper testing and validation.
#Please use at your own risk.
#This bot is for educational purposes only and should not be considered as financial advice.
#Join our community at www.binaryacademy.uk for more resources and support.

#For customized trading strategies and advanced features, please visit our website or contact us directly.
#We offer personalized trading solutions and support for traders of all levels.



import pandas as pd
import json
import time
import websocket
import logging

# Constants for Trading
API_TOKEN = "replace_with_your_api_token"  # Replace with your Deriv API token
APP_ID = "replace_with_your_app_id"  # Replace with your Deriv app ID
# Replace with your trading symbol (e.g., "R_10", "R_100", etc.)
SYMBOL = "replace_with_your_symbol"
CURRENCY = "USD"
STAKE = 1
GROWTH_RATE = 0.02
PERCENTAGE_THRESHOLD = +0.0005  # Threshold for average percentage change
ROLLING_WINDOW_SIZE = 55  # Number of ticks to consider for the moving average
TAKE_PROFIT_MULTIPLIER = 0.19  # 50% take profit

# Initialize empty DataFrame for market data
df = pd.DataFrame(columns=['Timestamp', 'Price'])

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def save_to_csv(timestamp, quote, symbol):
    global df
    new_data = pd.DataFrame({'Timestamp': [pd.to_datetime(timestamp, unit='s')], 'Price': [quote]})
    df = pd.concat([df, new_data], ignore_index=True)

def on_message(ws, message):
    try:
        data = json.loads(message)
        logging.info(f"Received data: {data}")

        if 'tick' in data:
            quote = data['tick']['quote']
            timestamp = data['tick']['epoch']
            symbol = data['tick']['symbol']
            logging.info(f"Saving tick data: {quote} at {timestamp} for {symbol}")
            save_to_csv(timestamp, quote, symbol)
            
            # Check if we have enough data points to start analysis
            if len(df) > ROLLING_WINDOW_SIZE:
                # Calculate percentage change
                calculate_percentage_change(df)
                
                # Calculate the rolling average of the percentage change
                rolling_avg_pct_change = df['Pct_Change'].rolling(window=ROLLING_WINDOW_SIZE).mean().iloc[-1]
                logging.info(f"Rolling average percentage change: {rolling_avg_pct_change}%")

                # Trigger a trade if the average percentage change is below the threshold
                if rolling_avg_pct_change < PERCENTAGE_THRESHOLD:
                    logging.info(f"Average percentage change {rolling_avg_pct_change}% is below threshold. Placing accumulator trade.")
                    trade_outcome = place_trade("ACCU")
                    logging.info(f"Final trade outcome: {trade_outcome}")
                    # Reset DataFrame for the next cycle
                    df.drop(df.index, inplace=True)
                else:
                    logging.info(f"Average percentage change {rolling_avg_pct_change}% exceeds threshold. Holding.")
        else:
            logging.error("Error: 'tick' not found in response.")
    except (KeyError, ValueError) as e:
        logging.error(f"Error processing response: {e}")

def on_error(ws, error):
    logging.error(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    logging.info("WebSocket closed")

def on_open(ws):
    subscribe_request = json.dumps({
        "ticks": SYMBOL,
        "subscribe": 1
    })
    ws.send(subscribe_request)

# Function to calculate percentage change
def calculate_percentage_change(df):
    df['Pct_Change'] = df['Price'].pct_change() * 100
    logging.info(f"Percentage changes calculated: {df['Pct_Change'].tail()}")

# Function to place a trade using WebSocket API
def place_trade(contract_type):
    ws = websocket.create_connection(f'wss://ws.derivws.com/websockets/v3?app_id={APP_ID}')
    
    auth_request = json.dumps({"authorize": API_TOKEN})
    ws.send(auth_request)
    auth_response = ws.recv()
    auth_data = json.loads(auth_response)
    
    if 'error' in auth_data:
        logging.error(f"Authorization error: {auth_data['error']['message']}")
        ws.close()
        return None

    # Trade request for accumulator
    trade_request = json.dumps({
        "buy": "1",
        "price": STAKE,
        "parameters": {
            "amount": STAKE,
            "basis": "stake",
            "contract_type": contract_type,
            "currency": CURRENCY,
            "symbol": SYMBOL,
            "growth_rate": GROWTH_RATE
        }
    })
    ws.send(trade_request)
    trade_response = ws.recv()
    
    logging.info(f"Trade Response: {trade_response}")
    
    trade_data = json.loads(trade_response)
    
    if 'error' in trade_data:
        logging.error(f"Trade error: {trade_data['error']['message']}")
        ws.close()
        return 'loss'

    contract_id = trade_data.get('buy', {}).get('contract_id')
    if not contract_id:
        logging.error("Error: 'contract_id' not found in the trade response.")
        ws.close()
        return 'loss'

    logging.info(f"Trade placed successfully: {contract_type}")
    
    # Monitor the trade for take profit
    sell_contract_if_profitable(ws, contract_id)
    ws.close()
    return 'sold'

# Function to monitor and sell the contract if profitable
def sell_contract_if_profitable(ws, contract_id):
    """ Monitor the contract and sell when the profit reaches or exceeds 25%. """
    while True:
        result_request = json.dumps({"proposal_open_contract": 1, "contract_id": contract_id})
        ws.send(result_request)
        result_response = ws.recv()
        result_data = json.loads(result_response)

        if 'proposal_open_contract' in result_data:
            contract = result_data['proposal_open_contract']
            if contract.get('is_sold'):
                logging.info("Contract already sold.")
                break
            
            profit = contract.get('profit', 0)
            logging.info(f"Current profit: {profit}")
            if profit >= TAKE_PROFIT_MULTIPLIER * STAKE:
                logging.info(f"Profit {profit} meets or exceeds 25% threshold. Selling contract.")
                sell_request = json.dumps({
                    "sell": contract_id,
                    "price": profit  # Price at which to sell the contract
                })
                ws.send(sell_request)
                sell_response = ws.recv()
                logging.info(f"Sell response: {sell_response}")
                break

        time.sleep(1)  # Adjust the frequency of checks as needed

# Establish WebSocket connection and start the process
if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()
