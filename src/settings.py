import matplotlib.pyplot as plt
import numpy as np
import os
import pathlib
import sys

import plotly.express as px

###################
### LOCAL PATHS ###
###################

sys.path.append(os.sep.join(sys.path[0].split(os.sep)[:-1]))

BASE_DIR = pathlib.Path(__file__).parents[1]
DATA_DIR = BASE_DIR / "data"
AGGREGATION_DIR = DATA_DIR / "aggregation"
CAPITAL_CONS_DIR = DATA_DIR / "capital_consumption"
EXIOBASE_DIR = DATA_DIR / "exiobase"
MODELS_DIR = DATA_DIR / "models"
FIGURES_DIR = BASE_DIR / "figures"
FIGURES_MULTIMODEL_DIR = FIGURES_DIR / "multimodel"

for path in [
    DATA_DIR,
    CAPITAL_CONS_DIR,
    EXIOBASE_DIR,
    MODELS_DIR,
    FIGURES_DIR,
    FIGURES_MULTIMODEL_DIR,
]:
    if not os.path.isdir(path):
        os.mkdir(path)


##############
### COLORS ###
##############

COLORS=px.colors.qualitative.D3+px.colors.qualitative.Alphabet+px.colors.qualitative.Dark24
# COLORS = list(plt.cm.tab10(np.arange(10))) + ["gold"]
COLORS_NO_FR = COLORS[1:]


######################
### OTHER SETTINGS ###
######################

## max increase of french imports param
CAP_IMPORTS_INCREASE_PARAM= 30/100

## pref_region and tradewar_region default regions
ALLIES="EU"
OPPONENTS="China"

## scenar_stressors by default
DEFAULT_SCENAR_STRESSORS = 'GES'


####################################
### AGGREGATIONS FOR THE FIGURES ###
####################################
# These aggregations are only dedicated to make the figures more legible. They have no influence on the models nor on their results.
# The aggregation used in the models is set through the matrices from data/aggregation as an argument of Model objects in model.py, but it's not the purpose of this section.
# The default REGIONS_AGG and SECTORS_AGG fit the model aggregation "opti_S".

## ofce
REGIONS_AGG = {
    "FR": ["FR"],
    "China+": ["China", "Asia"],
    "Europe+": ["EU", "Row Europe"],
    "North_Amer": ["United States", "North America"],
    "RoW": [
        "Middle East",
        "Africa",
        "Oceania",
        "Russia",
        "South America"
    ],
}

## opti_S
# REGIONS_AGG = {
#     "FR": ["FR"],
#     "UK, Norway, Switzerland": ["UK, Norway, Switzerland"],
#     "China+": ["China, RoW Asia and Pacific"],
#     "EU": ["EU"],
#     "RoW": [
#         "United States",
#         "Asia, Row Europe",
#         "RoW America,Turkey, Taïwan",
#         "RoW Middle East, Australia",
#         "Brazil, Mexico",
#         "South Africa",
#         "Japan, Indonesia, RoW Africa",
#     ],
# }

## ofce
SECTORS_AGG = {
    "Agriculture": ["Agriculture"],
    "Energy": [
        "Crude coal",
        "Crude oil",
        "Natural gas",
        "Fossil fuels",
        "Electricity and heat",
    ],
    "Industry": [
        "Extractive industry",
        "Biomass_industry",
        "Clothing",
        "Heavy_industry",
        "Machinery",
        "Electronics",
    ],
    "Construction":[
        "Construction"
    ],
    "Transports": [
        "Transport services",
        "Automobile",
        "Oth transport equipment",
    ],
    "Composite": ["Composite"],
}

## opti_S
# SECTORS_AGG = {
#     "Agriculture": ["Agriculture"],
#     "Energy": [
#         "Crude coal",
#         "Crude oil",
#         "Natural gas",
#         "Fossil fuels",
#         "Electricity and heat",
#     ],
#     "Industry": [
#         "Extractive industry",
#         "Biomass_industry",
#         "Clothing",
#         "Heavy_industry",
#         "Automobile",
#         "Oth transport equipment",
#         "Machinery",
#         "Electronics",
#         "Construction",
#         "Transport services",
#     ],
#     "Composite": ["Composite"],
# }
