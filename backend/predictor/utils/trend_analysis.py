import random


def analyze_trend(current_prediction: float) -> dict:
    """Simulate short historical baseline and compare with current prediction."""
    current = float(current_prediction)

    # Keep deterministic-enough variations around the current value.
    baseline_noise = random.uniform(-0.18, 0.18)
    past_value = max(0.01, current * (1.0 - baseline_noise))

    percentage_change = ((current - past_value) / past_value) * 100.0

    if percentage_change > 5.0:
        trend = "Increasing"
    elif percentage_change < -5.0:
        trend = "Decreasing"
    else:
        trend = "Stable"

    return {
        "trend": trend,
        "percentage_change": round(float(percentage_change), 2),
    }
