import requests
import json
import copy

from thy_api_config import *


class ThyAPI: 
    def __init__(self) -> None:
        pass

    def get_domestic_ports(self): 
        payload = copy.deepcopy(get_ports_payload)
        response = requests.request("POST", get_ports_url, headers=headers, data=json.dumps(payload))
        response_json = response.json()
        ports = response_json["data"]["Port"]
        domestic_ports = []
        for port in ports: 
            if port["IsDomestic"] == True:
                coordinate = port["Coordinate"]
                code = port["Code"]
                # name = port["LanguageInfo"]["Language"][0]["Name"]
                domestic_port = [code, coordinate]
                domestic_ports.append(domestic_port)
        return domestic_ports 
    
    def get_distance_between_ports(self, departure_code, arrival_code): 
        payload = copy.deepcopy(get_sector_payload)
        payload["departureAirport"] = departure_code
        payload["arrivalAirport"] = arrival_code
        response = requests.request("POST", get_sector_url, headers=headers, data=json.dumps(payload))
        return response.json()

    def get_availability(self, origin_code, destination_code, date): 
        payload = copy.deepcopy(availability_payload)
        payload["OriginDestinationInformation"][0]["DepartureDateTime"]["Date"] = date
        payload["OriginDestinationInformation"][0]["DepartureDateTime"]["Date"] = date
        payload["OriginDestinationInformation"][0]["DepartureDateTime"]["Date"] = date
        response = requests.request("POST", availability_url, headers=headers, data=json.dumps(payload))
        return response.json()


if __name__ == "__main__": 
    api = ThyAPI()
    domestic_ports = api.get_domestic_ports()
    # ports = {}
    # for port in domestic_ports: 
    #     ports[port[0]] = port[1]
    # with open('ports.json', 'w') as fp:
    #     json.dump(ports, fp)

    port_distances = {}
    for port in domestic_ports: 
        port_distances[port[0]] = {}
        for other_port in domestic_ports: 
            if port[0] != other_port[0]: 
                try: 
                    distance = api.get_distance_between_ports(port[0], other_port[0])["data"]["distance"]
                    port_distances[port[0]][other_port[0]] = distance
                except: 
                    print("Distance not found")
    with open('port_distances.json', 'w') as fp:
        json.dump(port_distances, fp)
    # api.get_distance_between_ports("IST", "BAL")