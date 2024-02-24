GHG_PARAMS = {
    "name_FR": "GES",
    "name_EN": "GHG",
    "unit": "kgCO2eq",
    "proxy": {
        "CO2": {
            "exiobase_keys": [
                "CO2 - combustion - air",
                "CO2 - non combustion - Cement production - air",
                "CO2 - non combustion - Lime production - air",
                "CO2 - agriculture - peat decay - air",
                "CO2 - waste - biogenic - air",
                "CO2 - waste - fossil - air",
            ],
            "weight": 1,
        },
        "CH4": {
            "exiobase_keys": [
                "CH4 - combustion - air",
                "CH4 - non combustion - Extraction/production of (natural) gas - air",
                "CH4 - non combustion - Extraction/production of crude oil - air",
                "CH4 - non combustion - Mining of antracite - air",
                "CH4 - non combustion - Mining of bituminous coal - air",
                "CH4 - non combustion - Mining of coking coal - air",
                "CH4 - non combustion - Mining of lignite (brown coal) - air",
                "CH4 - non combustion - Mining of sub-bituminous coal - air",
                "CH4 - non combustion - Oil refinery - air",
                "CH4 - agriculture - air",
                "CH4 - waste - air",
            ],
            "weight": 28,
        },
        "N2O": {
            "exiobase_keys": ["N2O - combustion - air", "N2O - agriculture - air"],
            "weight": 265,
        },
        "SF6": {
            "exiobase_keys": ["SF6 - air"],
            "weight": 23500,
        },
        "HFC": {
            "exiobase_keys": ["HFC - air"],
            "weight": 1,
        },
        "PFC": {
            "exiobase_keys": ["PFC - air"],
            "weight": 1,
        },
    },
}

MATERIAL_PARAMS = {
    "name_FR": "matières",
    "name_EN": "materials",
    "unit": "kt",
    "proxy": {
        "Bauxite et aluminium": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Bauxite and aluminium ores",
                "Unused Domestic Extraction - Metal Ores - Bauxite and aluminium ores",
            ],
            "weight": 1,
        },
        "Cuivre": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Copper ores",
                "Unused Domestic Extraction - Metal Ores - Copper ores",
            ],
            "weight": 1,
        },
        "Or": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Gold ores",
                "Unused Domestic Extraction - Metal Ores - Gold ores",
            ],
            "weight": 1,
        },
        "Fer": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Iron ores",
                "Unused Domestic Extraction - Metal Ores - Iron ores",
            ],
            "weight": 1,
        },
        "Plomb": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Lead ores",
                "Unused Domestic Extraction - Metal Ores - Lead ores",
            ],
            "weight": 1,
        },
        "Nickel": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Nickel ores",
                "Unused Domestic Extraction - Metal Ores - Nickel ores",
            ],
            "weight": 1,
        },
        "Autres métaux non-ferreux": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Other non-ferrous metal ores",
                "Unused Domestic Extraction - Metal Ores - Other non-ferrous metal ores",
            ],
            "weight": 1,
        },
        "Platine": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - PGM ores",
                "Unused Domestic Extraction - Metal Ores - PGM ores",
            ],
            "weight": 1,
        },
        "Argent": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Silver ores",
                "Unused Domestic Extraction - Metal Ores - Silver ores",
            ],
            "weight": 1,
        },
        "Cassitérite": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Tin ores",
                "Unused Domestic Extraction - Metal Ores - Tin ores",
            ],
            "weight": 1,
        },
        "Uranium et thorium": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Uranium and thorium ores",
                "Unused Domestic Extraction - Metal Ores - Uranium and thorium ores",
            ],
            "weight": 1,
        },
        "Zinc": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Zinc ores",
                "Unused Domestic Extraction - Metal Ores - Zinc ores",
            ],
            "weight": 1,
        },
        "Pierre de construction": {
            "exiobase_keys": [
                "Domestic Extraction Used - Non-Metallic Minerals - Building stones",
                "Unused Domestic Extraction - Non-Metallic Minerals - Building stones",
            ],
            "weight": 1,
        },
        "Minéraux chimiques et d'engrais": {
            "exiobase_keys": [
                "Domestic Extraction Used - Non-Metallic Minerals - Chemical and fertilizer minerals",
                "Unused Domestic Extraction - Non-Metallic Minerals - Chemical and fertilizer minerals",
            ],
            "weight": 1,
        },
        "Argiles et kaolin": {
            "exiobase_keys": [
                "Domestic Extraction Used - Non-Metallic Minerals - Clays and kaolin",
                "Unused Domestic Extraction - Non-Metallic Minerals - Clays and kaolin",
            ],
            "weight": 1,
        },
        "Gravier et sable": {
            "exiobase_keys": [
                "Domestic Extraction Used - Non-Metallic Minerals - Gravel and sand",
                "Unused Domestic Extraction - Non-Metallic Minerals - Gravel and sand",
            ],
            "weight": 1,
        },
        "Calcaire, gypse, craie, dolomite": {
            "exiobase_keys": [
                "Domestic Extraction Used - Non-Metallic Minerals - Limestone, gypsum, chalk, dolomite",
                "Unused Domestic Extraction - Non-Metallic Minerals - Limestone, gypsum, chalk, dolomite",
            ],
            "weight": 1,
        },
        "Autres minéraux": {
            "exiobase_keys": [
                "Domestic Extraction Used - Non-Metallic Minerals - Other minerals",
                "Unused Domestic Extraction - Non-Metallic Minerals - Other minerals",
            ],
            "weight": 1,
        },
        "Sel": {
            "exiobase_keys": [
                "Domestic Extraction Used - Non-Metallic Minerals - Salt",
                "Unused Domestic Extraction - Non-Metallic Minerals - Salt",
            ],
            "weight": 1,
        },
        "Ardoise": {
            "exiobase_keys": [
                "Domestic Extraction Used - Non-Metallic Minerals - Slate",
                "Unused Domestic Extraction - Non-Metallic Minerals - Slate",
            ],
            "weight": 1,
        },
    },
}

COPPER_PARAMS = {
    "name_FR": "cuivre",
    "name_EN": "copper",
    "unit": "kt",
    "proxy": {
        "Cuivre": {
            "exiobase_keys": [
                "Domestic Extraction Used - Metal Ores - Copper ores",
                "Unused Domestic Extraction - Metal Ores - Copper ores",
            ],
            "weight": 1,
        },
    },
}

LANDUSE_PARAMS = {
    "name_FR": "usage des sols",
    "name_EN": "land_use",
    "unit": "km2",
    "proxy": {
        "cultures": {
            "exiobase_keys": [
                "Cropland - Cereal grains nec",
                "Cropland - Crops nec",
                "Cropland - Fodder crops-Cattle",
                "Cropland - Fodder crops-Meat animals nec",
                "Cropland - Fodder crops-Pigs",
                "Cropland - Fodder crops-Poultry",
                "Cropland - Fodder crops-Raw milk",
                "Cropland - Oil seeds",
                "Cropland - Paddy rice",
                "Cropland - Plant-based fibers",
                '"Cropland - Sugar cane, sugar beet"',
                '"Cropland - Vegetables, fruit, nuts"',
                "Cropland - Wheat",
            ],
            "weight": 1,
        },
        "forêts": {
            "exiobase_keys": [
                "Forest area - Forestry",
                "Forest area - Marginal use",
            ],
            "weight": 1,
        },
        "pâturages": {
            "exiobase_keys": [
                "Permanent pastures - Grazing-Cattle",
                "Permanent pastures - Grazing-Meat animals nec",
                "Permanent pastures - Grazing-Raw milk",
            ],
            "weight": 1,
        },
        "infrastructures": {
            "exiobase_keys": ["Infrastructure land"],
            "weight": 1,
        },
        "autres usages": {"exiobase_keys": ["Other land Use: Total"], "weight": 1},
    },
}
