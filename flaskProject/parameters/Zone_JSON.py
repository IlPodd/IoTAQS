cell_side = 0.0006

"""DEFINING ZONES
zones = [{ name:Name, center:latitude, longitude, half_width: cell_side }]"""

geo_zones_json= [
    {"p": [39.228272, 9.109862, cell_side], "n": "Parchetto"},
    {"p": [39.229247, 9.109036, cell_side], "n": "Segreteria"},
    {"p": [39.230172, 9.108120, cell_side], "n": "Biblioteca"},
    {"p": [39.230572, 9.106862, cell_side], "n": "Sterrato"}
]

geo_zones  = "[[39.228272, 9.109862,0.0006,\"Parchetto\"],[39.229247, 9.109036, 0.0006,\"Segreteria\"],[39.230172, 9.108120, 0.0006, \"Biblioteca\"],[39.230572, 9.106862, 0.0006,\"Sterrato\"]]"