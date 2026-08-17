async def get_weather(origin: str, destination: str):

    # TODO:
    # Replace with real weather API.

    return {
        "origin": origin,
        "destination": destination,
        "severity_score": 0.50,
        "status": "MODERATE"
    }


async def get_congestion(origin: str, destination: str):

    # TODO:
    # Replace with real aviation/airport
    # congestion API.

    return {
        "origin": origin,
        "destination": destination,
        "airport_congestion_score": 0.40,
        "route_congestion_score": 0.35,
        "status": "MODERATE"
    }