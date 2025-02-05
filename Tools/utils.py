def calculate_interest_payement(
    principal: float, interest_rate: float, days: int, use_trading_days: bool = True
):
    if use_trading_days:
        total_days = 252
    else:
        total_days = 365

    annual_interest = interest_rate / 100
    daily_interest = annual_interest / total_days
    total_payout = principal * (1 + daily_interest) ** days
    interest_earned = total_payout - principal

    return {
        "principal": principal,
        "interest_earned": interest_earned,
        "total": total_payout,
    }


if __name__ == "__main__":

    data = calculate_interest_payement(1900, 4.5, 4)
    print(data)
