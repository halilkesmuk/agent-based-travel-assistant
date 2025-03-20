import requests
import os 
from datetime import datetime

api_key = os.getenv("RAPID_API_KEY")
url = "https://sky-scanner3.p.rapidapi.com/flights/search-one-way"


def search_flights(fromEntityId, toEntityId, departDate, max_results=5):
    querystring = {
        "fromEntityId": fromEntityId,
        "toEntityId": toEntityId,
        "departDate": departDate,
        "market": "TR",
        "locale": "tr-TR",
        "currency": "TRY"
    }

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "sky-scanner3.p.rapidapi.com"
    }

    flights = []
    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code == 200:
        results = response.json()

        itineraries = results.get("data", {}).get("itineraries", [])[:max_results]

        if itineraries:
            for itinerary in itineraries:
                new_flight = {}
                new_flight["flight_id"] = itinerary["id"]
                new_flight["from"] = fromEntityId
                new_flight["to"] = toEntityId
                new_flight["price"] = itinerary["price"]["formatted"]
                
                leg = itinerary["legs"][0]
                new_flight["airline"] = leg["segments"][0]["operatingCarrier"]["name"]

                departure_dt = datetime.fromisoformat(leg["departure"])
                arrival_dt = datetime.fromisoformat(leg["arrival"])

                new_flight["date"] = departure_dt.date().isoformat()
                new_flight["departure_time"] = departure_dt.time().strftime('%H:%M')
                new_flight["arrival_time"] = arrival_dt.time().strftime('%H:%M')
                new_flight["duration"] = leg["durationInMinutes"]
                new_flight["cabin_class"] = leg["segments"][0].get("cabinClass", "Economy")
                
                flights.append(new_flight)

    return flights



# if __name__ == "__main__":
#     flights = search_flights("IST", "ADB", "2025-03-25")
#     for flight in flights : 
#         print(flight["flight_id"],flight["from"] ,flight["to"], flight["price"], flight["airline"], flight["date"], flight["departure_time"], flight["arrival_time"], flight["duration"], flight["cabin_class"])
#         break
