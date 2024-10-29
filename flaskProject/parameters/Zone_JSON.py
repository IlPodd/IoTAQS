cell_side = 0.000116

"""DEFINING ZONES
zones = [{ name:Name, center:latitude, longitude, half_width: cell_side }]"""
zoneSE = [{"Name": "South East", "Center": "39.228376, 9.109906", "Width": cell_side}]
zoneNE = [{"Name": "North East", "Center": "39.228534, 9.109764", "Width": cell_side}]
zoneSO = [{"Name": "South West", "Center": "39.228494, 9.109559", "Width": cell_side}]
zoneNO = [{"Name": "North West", "Center": "39.228293, 9.109721", "Width": cell_side}]

geo_zones_json= [
    {"p": [39.228376, 9.109906, 0.000116], "n": "ParchettoSE"},
    {"p": [39.228534, 9.109764, 0.000116], "n": "ParchettoNE"},
    {"p": [39.228494, 9.109559, 0.000116], "n": "ParchettoNO"},
    {"p": [39.228293, 9.109721, 0.000116], "n": "ParchettoSO"}
]

geo_zones  = "[{\"p\":[39.228376, 9.109906,0.000116 ] , \"n\":\"ParchettoSE\"},{\"p\":[39.228534, 9.109764,0.000116 ] , \"n\":\"ParchettoNO\"},{\"p\":[39.228494, 9.109559,0.000116 ] , \"n\":\"ParchettoNE\"},{\"p\":[39.228293, 9.109721,0.000116 ] , \"n\":\"ParchettoSO\"}]"