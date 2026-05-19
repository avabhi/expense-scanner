from langchain_core.tools import tool

@tool
def convert_currency(amount: float, from_currency: str, to_currency: str = "USD") -> float:
    """
    Converts an amount from one currency to another using a mock conversion rate.
    In a real app, this would hit an external API like Fixer or ExchangeRate-API.
    """
    # Mock conversion rates
    rates = {
        "INR": 0.012,
        "EUR": 1.08,
        "GBP": 1.26,
        "USD": 1.0
    }
    
    from_rate = rates.get(from_currency.upper(), 1.0)
    to_rate = rates.get(to_currency.upper(), 1.0)
    
    # Convert to USD first (base), then to target
    amount_in_usd = amount * from_rate
    final_amount = amount_in_usd / to_rate
    
    return round(final_amount, 2)
