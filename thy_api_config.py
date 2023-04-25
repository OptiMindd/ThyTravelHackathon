headers = {
  'apikey': 'l7xx19ed8298ff9b42f1a251ccb836fc142b',
  'apisecret': '4d8b020780ae4803a71114c77e68b9db',
  'Content-Type': 'application/json'
}

get_ports_url = "https://api.turkishairlines.com/test/getPortList"
get_ports_payload = {
  "requestHeader": {
    "clientUsername": "OPENAPI",
    "clientTransactionId": "CLIENT_TEST_1",
    "channel": "WEB",
    "languageCode": "TR",
    "airlineCode": "TK"
  }
}

get_sector_url = "https://api.turkishairlines.com/test/aodb-rest/mdm/getSector"
get_sector_payload = {
  "departureAirport": "IST",
  "arrivalAirport": "ESB"
}

availability_url = "https://api.turkishairlines.com/test/getAvailability"
availability_payload = {
  "requestHeader": {
    "clientUsername": "OPENAPI",
    "clientTransactionId": "CLIENT_TEST_1",
    "channel": "WEB"
  },
  "ReducedDataIndicator": False,
  "RoutingType": "R",
  "TargetSource": "BrandedFares",
  "PassengerTypeQuantity": [
    {
      "Code": "adult",
      "Quantity": 1
    },
    {
      "Code": "child",
      "Quantity": 0
    },
    {
      "Code": "infant",
      "Quantity": 0
    }
  ],
  "OriginDestinationInformation": [
    {
      "DepartureDateTime": {
        "WindowAfter": "P0D",
        "WindowBefore": "P0D",
        "Date": "30APR"
      },
      "OriginLocation": {
        "LocationCode": "IST",
        "MultiAirportCityInd": False
      },
      "DestinationLocation": {
        "LocationCode": "ESB",
        "MultiAirportCityInd": False
      },
      "CabinPreferences": [
        {
          "Cabin": "ECONOMY"
        },
        {
          "Cabin": "BUSINESS"
        }
      ]
    },
    {
      "DepartureDateTime": {
        "WindowAfter": "P0D",
        "WindowBefore": "P0D",
        "Date": "30APR"
      },
      "OriginLocation": {
        "LocationCode": "ESB",
        "MultiAirportCityInd": False
      },
      "DestinationLocation": {
        "LocationCode": "IST",
        "MultiAirportCityInd": False
      },
      "CabinPreferences": [
        {
          "Cabin": "ECONOMY"
        },
        {
          "Cabin": "BUSINESS"
        }
      ]
    }
  ]
}
