def analyze_prediction(predicted_density: float, env_data: dict) -> dict:
    """Return conservation decision support from prediction and environment."""
    density = float(predicted_density)

    vegetation = float(env_data.get("vegetation_index", 0.0))
    water = float(env_data.get("water_availability", 0.0))
    disturbance = float(env_data.get("human_disturbance", 0.0))

    if density < 5.0 and disturbance >= 0.65:
        return {
            "risk_level": "High",
            "status": "Critical",
            "recommendation": (
                "Urgent intervention required: restrict human activity, strengthen habitat protection, "
                "and deploy rapid biodiversity recovery measures in this zone."
            ),
        }

    if vegetation >= 0.65 and water >= 0.55:
        return {
            "risk_level": "Low",
            "status": "Stable",
            "recommendation": (
                "Habitat conditions are favorable. Continue routine monitoring, preserve water sources, "
                "and maintain existing conservation corridors."
            ),
        }

    return {
        "risk_level": "Medium",
        "status": "Declining",
        "recommendation": (
            "Apply targeted habitat restoration, improve water retention, and reduce local disturbances "
            "through community-led conservation actions."
        ),
    }
