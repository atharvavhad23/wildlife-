def analyze_prediction(predicted_density: float, env_data: dict, is_endangered: bool = False) -> dict:
    """Return conservation decision support from prediction, environment, and endangered risk status."""
    density = float(predicted_density)

    vegetation = float(env_data.get("vegetation_index", 0.0))
    water = float(env_data.get("water_availability", 0.0))
    disturbance = float(env_data.get("human_disturbance", 0.0))
    temp = float(env_data.get("temperature", 25.0))
    
    recs = []
    
    # High-Priority Assessment: Is the species Endangered based on the 10-year projection?
    if is_endangered:
        risk_level = "High"
        status = "Critical"
        recs.append("🚨 SPECIES IS ENDANGERED: Projections show a severe population decline over the next decade.")
        recs.append("Immediate Action: Establish ex-situ conservation programs (e.g., captive breeding or seed banks) immediately.")
        recs.append("Declare the surrounding habitat as an Eco-Sensitive Zone with zero human disturbance and strict legal protections against poaching or harvesting.")
    else:
        # Standard Base assessment
        if density < 5.0 and (disturbance >= 0.6 or vegetation < 0.3 or water < 0.3):
            risk_level = "High"
            status = "Critical"
            recs.append("Urgent intervention required due to critically low density and severe environmental stress.")
        elif vegetation >= 0.6 and water >= 0.5 and disturbance <= 0.4:
            risk_level = "Low"
            status = "Stable"
            recs.append("Habitat conditions are favorable, continue routine ecological monitoring.")
        else:
            risk_level = "Medium"
            status = "Vulnerable"
            recs.append("Habitat shows signs of stress, requiring proactive management.")

        # Environmental Breakdown
        if disturbance >= 0.6:
            recs.append("Restrict unauthorized human access and reduce local disturbances immediately.")
        elif disturbance >= 0.35:
            recs.append("Monitor edge habitats closely for human encroachment.")
            
        if vegetation < 0.4:
            recs.append("Initiate targeted flora restoration to improve natural cover.")
        elif vegetation > 0.7:
            recs.append("Maintain and protect existing green corridors.")
            
        if water < 0.35:
            recs.append("Create artificial water catchments to alleviate drought stress.")
        elif water < 0.6:
            recs.append("Implement measures to improve natural water retention in the area.")
            
        if temp > 35.0:
            recs.append("Provide shaded refuge zones to combat extreme thermal stress.")
            
        if len(recs) == 1:
            recs.append("Engage in community-led conservation actions to ensure long-term stability.")

    return {
        "risk_level": risk_level,
        "status": status,
        "recommendation": " ".join(recs),
    }
