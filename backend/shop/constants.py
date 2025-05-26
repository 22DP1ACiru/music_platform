from decimal import Decimal

# Target currency for all orders will be USD for this example
ORDER_SETTLEMENT_CURRENCY = 'USD'

# Hardcoded exchange rates TO USD
# 1 XXX = YYY USD
EXCHANGE_RATES_TO_USD = {
    'USD': Decimal('1.00'),
    'EUR': Decimal('1.14'), # 1 EUR = 1.08 USD (Example, update with your desired rate)
    'GBP': Decimal('1.36'), # 1 GBP = 1.27 USD (Example, update with your desired rate)
    # Add other currencies your artists might use
}

# Helper function
def convert_to_usd(amount: Decimal, currency: str) -> Decimal | None:
    rate = EXCHANGE_RATES_TO_USD.get(currency.upper())
    if rate is None:
        # Handle unknown currency - either raise error or return None/default
        # For now, let's assume all product currencies will be in this dict
        # Or you could have a platform default currency if conversion isn't possible
        raise ValueError(f"Exchange rate not available for currency: {currency}")
    return (amount * rate).quantize(Decimal('0.01'))