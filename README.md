# Accumulator Bot - Mean Reversion Strategy

![Accumulator Bot](https://via.placeholder.com/150)

Automated trading bot for Deriv's accumulator contracts using mean reversion strategy.

## Key Features

- **Rolling Window Analysis**: 55-tick window for market condition assessment
- **Percentage Threshold**: Triggers trades when market meets quiet conditions
- **Auto Take-Profit**: 19% profit target per contract
- **Data Logging**: Saves all tick data for analysis

## Installation

```bash
pip install websocket-client pandas