import os

from typing import Callable, Dict, List, Tuple

import pickle as pkl
import pandas as pd
import pymrio
import copy
import multiprocessing


import src.figures as figures

from src.settings import (
    CAPITAL_CONS_DIR,
    EXIOBASE_DIR,
    FIGURES_DIR,
    MODELS_DIR,
)
# from src.stressors import STRESSOR_DICT_GHG_MAT, GHG_AND_MATERIALS_PARAM
from src.stressors import STRESSORS_DICT_DEF

from src.utils import build_reference_data, build_counterfactual_data, reverse_mapper, subsetting, save_CoefRoW 


class Model:
    def __init__(
        self,
        base_year: int = 2015,
        system: str = "pxp",
        aggregation_name: str = "opti_S",
        calib: bool = False,
        regions_mapper: Dict = None,
        sectors_mapper: Dict = None,
        capital: bool = False,
        stressor_subset: str = "full",
        recalib_capital=False
    ):
        """Inits Model class

        Args:
            base_year (int): year in 4 digits. Defaults to 2015.
            system (str): product ('pxp') or industry ('ixi'). Defaults to 'pxp'.
            aggregation_name (str): name of the aggregation matrix used. Defaults to 'opti_S'.
            calib (bool, optional): True to recalibrate the model from downloaded data. Defaults to False.
            regions_mapper (Dict, optional): regions aggregation for figures editing, no aggregation if is None. Defaults to None.
            sectors_mapper (Dict, optional): sectors aggregation for figures editing, no aggregation if is None. Defaults to None.
            capital (bool, optional): True to endogenize investments and capital. Defaults to False.
#####            stressor_params (Dict, optional): dictionnary with the stressors' french name, english name, unit and a proxy as a dictionnary of comparable stressors (name as key, dictionnary as value with the list of corresponding Exiobase stressors and their weight). Defaults to a dictionnary with the GHGs.
            stressor_subset (str, optional): stressor(s) to calibrate a Model on. Extracted from a dictionnary (see STRESSORS_DICT_DEF variable in stressors.py) with the stressors' french name, english name, unit and a proxy as a dictionnary of comparable stressors (name as key, dictionnary as value with the list of corresponding Exiobase stressors and their weight). Defaults to a dictionnary with the GHGs.
            recalib_capital (Bool): allows to recalibrated iot system to take into account the discrepency between additionnal capital matrix data and Exiobase data.
        """

        self.base_year = base_year
        self.system = system
        self.aggregation_name = aggregation_name
        self.calib = calib
        self.capital = capital
        self.recalib_capital = recalib_capital
        self.stressor_name = stressor_subset
        # self.stressor_shortname = "".join(
        #     filter(str.isalnum, stressor_params["name_EN"].lower())
        # )  # format as file path # if stressor_subset==None else shortnaming(stressor_subset)
        self.stressor_shortname = STRESSORS_DICT_DEF[stressor_subset]['name_EN']
        self.stressor_dict = subsetting(stressor_subset)
        self.stressor_unit = STRESSORS_DICT_DEF[stressor_subset]['unit']

        self.summary_shortest = str(base_year) + "__" + system
        self.summary_short = self.summary_shortest + "__" + aggregation_name
        self.summary_long = (
            self.summary_short
            + "__"
            + self.stressor_shortname
            + capital * "__with_capital"
        )
        self.exiobase_dir = EXIOBASE_DIR / self.summary_shortest
        self.model_dir = MODELS_DIR / self.summary_long
        self.raw_file_name = f"IOT_{base_year}_{system}.zip"
        self.exiobase_pickle_file_name = self.summary_shortest + ".pickle"
        self.figures_dir = FIGURES_DIR / self.summary_long
        # if self.capital:
        self.capital_consumption_path = (
            CAPITAL_CONS_DIR / f"Kbar_exio_v3_6_{self.base_year}{self.system}.mat"
        )

        self.iot = build_reference_data(model=self)
        self.regions = list(self.iot.get_regions())
        self.sectors = list(self.iot.get_sectors())
        self.y_categories = list(self.iot.get_Y_categories())

        self._regions_mapper = regions_mapper
        self._sectors_mapper = sectors_mapper
        self.rev_regions_mapper = reverse_mapper(mapper=regions_mapper)
        self.rev_sectors_mapper = reverse_mapper(mapper=sectors_mapper)
        if regions_mapper is None:
            self.new_regions_index = None
            self.agg_regions = self.regions
        else:
            self.agg_regions = list(regions_mapper.keys())
            self.new_regions_index = pd.Index(self.agg_regions)
        if sectors_mapper is None:
            self.new_sectors_index = None
            self.agg_sectors = self.sectors
        else:
            self.agg_sectors = list(sectors_mapper.keys())
            self.new_sectors_index = pd.Index(self.agg_sectors)

        self.counterfactuals = {}

        self.reloc = None
        self.save_figures = False
        self.scenar_stressors = 'aucun'

        self.save()

    ## save model

    def save(self) -> None:
        """Saves the model as a pickle file"""
        with open(self.model_dir / "backup.pickle", "wb") as f:
            pkl.dump(self, f)

    ## counterfactuals

    def new_counterfactual(
        self,
        name: str,
        scenar_function: Callable[["Model", ], pymrio.IOSystem],
        **kwargs
        ) -> None:
        """Creates a new counterfactual from scenario_parameters in self.counterfactuals

        Args:
            name (str): counterfactual name
            scenar_function (Callable[[Model, bool], Tuple[pd.DataFrame]]): functions that builds the new Z and Y matrices
            reloc (bool, optional): True if relocation is allowed. Defaults to False.
        """

        self.counterfactuals[name] = Counterfactual(name, self, scenar_function, **kwargs)

    def create_counterfactuals_from_dict(
        self,
        parameters_dict: Dict = {},
        reloc: bool = False,
        verbose: bool = True,
        **kwargs
    ) -> None:
        """Creates all new counterfactuals from scenario_parameters in self.counterfactuals

        Args:
            parameters_dict (Dict, optional): dictionnary with counterfactuals' names as keys and scenario parametersas values, set as DICT_SCENARIOS from scenarios.py if None. Defaults to None.
            reloc (bool, optional): True if relocation is allowed. Defaults to False.
            verbose (bool, optional): True to print infos. Defaults to True.
        """

        if parameters_dict=={}:
            from scenarios import DICT_SCENARIOS

            parameters_dict = DICT_SCENARIOS
        for name, scenar_function in parameters_dict.items():
            self.new_counterfactual(
                name=name, scenar_function=scenar_function, reloc=reloc, **kwargs
            )
            if verbose:
                print(f"New counterfactual created : {name}")

        print(f"Available counterfactuals : {self.get_counterfactuals_list()}")

    def get_counterfactuals_list(self) -> List[str]:
        """Returns the list of the names of the available counterfactuals

        Returns:
            List[str]: names of the available counterfactuals
        """
        return list(self.counterfactuals.keys())
    
    def modify_counterfactual(
        self,
        name:str,
        scenar_function: Callable[["Model", ], pymrio.IOSystem],
        new_name=None,
        **kwargs
        ) -> None:
        """Creates a new counterfactual from scenario_parameters in self.counterfactuals

        Args:
            name (str): counterfactual to modify
            scenar_function (Callable[[Model, bool], Tuple[pd.DataFrame]]): functions that builds the new Z and Y matrices
            reloc (bool, optional): True if relocation is allowed. Defaults to False.
            new_name (str,optional): If not None, the modified counterfactuals is created and given the new_name, the original one remane unchanged
        """
        #creating a temporary model with counterfactuals info to work on
        if new_name is None:
            new_name=name
        temp_model=copy.copy(self)
        temp_model.iot=self.counterfactuals[name].iot
        self.counterfactuals[new_name]=Counterfactual(new_name, temp_model, scenar_function, **kwargs)
        del(temp_model)
        
        
    def delete_counterfactual(
            self,
            name:str
        )->None:
        """ Delete selected counterfactual.
        
        Args:
            name (str): name of the counterfactual to delete.
        """
        del self.counterfactuals[name]
        
        return None
    
    
    ## aggregation mapping for figure editing

    @property
    def regions_mapper(self):
        return self._regions_mapper

    @regions_mapper.setter
    def regions_mapper(self, mapper):
        self._regions_mapper = mapper
        self.rev_regions_mapper = reverse_mapper(mapper=mapper)
        if mapper is None:
            self.new_regions_index = None
            self.agg_regions = self.regions
        else:
            self.agg_regions = list(mapper.keys())
            self.new_regions_index = pd.Index(self.agg_regions)

    @property
    def sectors_mapper(self):
        return self._sectors_mapper

    @sectors_mapper.setter
    def sectors_mapper(self, mapper):
        self._sectors_mapper = mapper
        self.rev_sectors_mapper = reverse_mapper(mapper=mapper)
        if mapper is None:
            self.agg_sectors = self.sectors
            self.new_sectors_index = None
        else:
            self.agg_sectors = list(mapper.keys())
            self.new_sectors_index = pd.Index(self.agg_sectors)

    ## description plots

    def plot_footprint(
        self,
        counterfactual_name: str = None,
        region: str = "FR",
        stressors_to_display: str = None,
        title: str = None,
    ) -> None:
        """Plots region's footprint (D_pba-D_exp+D_imp+F_Y)

        Args:
            counterfactual_name (str, optional): name of the counterfactual to plot, or None to plot the reference (self). Defaults to None.
            region (str, optional): region name. Defaults to "FR".
            stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
            title (str, optional): title of the figure. Defaults to None.
        """
        figures.plot_footprint(
            model=self,
            region=region,
            counterfactual_name=counterfactual_name,
            stressors_to_display=stressors_to_display,
            title=title,
        )

    def plot_footprint_FR(self, counterfactual_name: str = None, stressors_to_display:str = None) -> None:
        """Plots french footprint (D_pba-D_exp+D_imp+F_Y)

        Args:
            counterfactual_name (str, optional): name of the counterfactual to plot, or None to plot the reference (self). Defaults to None.
            stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
        """
        figures.plot_footprint_FR(
            model=self,
            counterfactual_name=counterfactual_name,
            stressors_to_display=stressors_to_display
        )

    def plot_stressor_content_heatmap(
        self,
        counterfactual_name: str = None,
        stressors_to_display: str = None,
        prod: bool = False,
    ) -> None:
        """Plots the content in stressors of each sector for each region in a heatmap

        Args:
            counterfactual_name (str, optional): name of the counterfactual to plot, or None to plot the reference (self). Defaults to None.
            stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
            prod (bool, optional): True to focus on production values, otherwise focus on consumption values. Defaults to False.
        """
        figures.plot_stressor_content_heatmap(
            model=self, counterfactual_name=counterfactual_name, stressors_to_display=stressors_to_display, prod=prod
        )

    def plot_stressor_content_production(
        self,
        counterfactual_name: str = None,
        stressors_to_display: str = None
    ) -> None:
        """Plots the content in stressors of each region for each sector

        Args:
            counterfactual_name (str, optional): name of the counterfactual to plot, or None to plot the reference (self). Defaults to None.
            stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
        """
        figures.plot_stressor_content_production(
            model=self, counterfactual_name=counterfactual_name, stressors_to_display=stressors_to_display
        )

    ## comparison plots

    def plot_trade_synthesis(self, counterfactual_name: str) -> None:
        """Plots the french importations for a given counterfactual

        Args:
            counterfactual_name (str): name of the counterfactual in model.counterfactuals
        """
        figures.plot_trade_synthesis(
            model=self, counterfactual_name=counterfactual_name
        )

    def plot_stressor_synthesis(self, counterfactual_name: str, stressors_to_display: str) -> None:
        """Plots the french emissions per sector for a given counterfactual and chosen stressor(s)

        Args:
            counterfactual_name (str): name of the counterfactual in model.counterfactuals
            stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
        """
        figures.plot_stressor_synthesis(
            model=self, counterfactual_name=counterfactual_name, stressors_to_display=stressors_to_display
        )

    def plot_substressor_synthesis(self, counterfactual_name: str, stressors_to_display: str) -> None:
        """Plots the french emissions per substressor for a given counterfactual and chosen stressor(s)

        Args:
            counterfactual_name (str): name of the counterfactual in model.counterfactuals
            stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.

        """
        figures.plot_substressor_synthesis(
            model=self, counterfactual_name=counterfactual_name, stressors_to_display=stressors_to_display
        )

    ## plots for all scenarios

    def compare_scenarios(self, verbose: bool = False) -> None:
        """Plots the footprints and the imports associated with the different counterfactuals

        Args:
            verbose (bool, optional): True to print infos. Defaults to False.
        """
        figures.compare_scenarios(model=self, verbose=verbose)

    def plot_stressor_content_heatmap_all(self, stressors_to_display: str, prod: bool = False) -> None:
        """Plots the contents in stressors each sector for each region in a heatmap for each counterfactual

        Args:
            stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
            prod (bool, optional): True to focus on production values, otherwise focus on consumption values. Defaults to False.
        """
        for counterfactual_name in self.get_counterfactuals_list():
            self.plot_stressor_content_heatmap(
                counterfactual_name=counterfactual_name, stressors_to_display=stressors_to_display, prod=prod
            )

    def plot_trade_synthesis_all(self) -> None:
        """Plots the french importations for each counterfactual"""
        for counterfactual_name in self.get_counterfactuals_list():
            self.plot_trade_synthesis(counterfactual_name=counterfactual_name)

    def plot_stressor_synthesis_all(self, stressors_to_display: str) -> None:
        """Plots the french emissions of stressors by sector for each counterfactual

        Args:
            stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
        """
        for counterfactual_name in self.get_counterfactuals_list():
            self.plot_stressor_synthesis(counterfactual_name=counterfactual_name, stressors_to_display=stressors_to_display)

    def plot_substressor_synthesis_all(self, stressors_to_display: str) -> None:
        """Plots the french emissions per substressor for a given counterfactual
        
        Args:
            stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
        """
        for counterfactual_name in self.get_counterfactuals_list():
            self.plot_substressor_synthesis(counterfactual_name=counterfactual_name, stressors_to_display=stressors_to_display)

    ## plot all

    def plot_all(self, stressors_to_display:str) -> None:
        """Plots all possible plots
        
        Args:
            stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
        """
        #self.compare_scenarios()
        self.plot_trade_synthesis_all()
        self.plot_stressor_synthesis_all(stressors_to_display)
        self.plot_substressor_synthesis_all(stressors_to_display)
        self.plot_footprint_FR(stressors_to_display)
        self.plot_stressor_content_heatmap_all(stressors_to_display)
        self.plot_stressor_content_production(stressors_to_display)


    def plot_impacts_by_exporting_country_for_one_product(
            self,
            sector: str,
            country_importing: str,
            scenarios: List[str],
            stressors_to_display: str,
            scope: int
            ) -> None:
        """" Plots imported impacts by origin(s) of the imported good.
            Impacts occuring along the entire value chain (in case of scope=3) or direct impacts (scope = 1) of the selected product are attributed to last exporter of the product.
        
        Args:
            sector (str): imported product whose impacts will be displayed 
            country_importing (str): importing country of the above product
            scenarios (list of str): scenarios to display. Default to all existing counterfactuals (cf. model.get_counterfactuals_list()).
            stressors_to_display (str): impacts to display (to be defined in variable STRESSORS_DICT_DEF in stresors.py).
            scope (int): 1 (direct impacts of production only) or 3 (impacts of the entire value chain).
        """
        figures.plot_impacts_by_exporting_country_for_one_product_2(
            model=self,
            sector= sector,
            country_importing=country_importing,
            scenarios=scenarios,
            stressors_to_display=stressors_to_display,
            scope=scope
            )

    def plot_impacts_by_location_for_one_product(
            self,
            sector: str,
            country_importing: str,
            scenarios: List[str],
            stressors_to_display: str,
            option: str = 'MRIO'
            ) -> None:
        """" Plots imported impacts by location of impacts. 
            Impacts occuring along the entire value chain are attributed to the region(s) where there actually happened.
        
        Args:
            sector (str): imported product whose impacts will be displayed 
            country_importing (str): importing country of the above product
            scenarios (list of str): scenarios to display. Default to all existing counterfactuals (cf. model.get_counterfactuals_list()).
            stressors_to_display (str): impacts to display (to be defined in variable STRESSORS_DICT_DEF in stresors.py).
        """
        if option=='final demand':
            figures.plot_impacts_by_location_for_one_product_FD(
                model=self,
                sector= sector,
                country_importing=country_importing,
                scenarios=scenarios,
                stressors_to_display=stressors_to_display,
                )
        elif option=='total imports':
            figures.plot_impacts_by_location_for_one_product(
                model=self,
                sector= sector,
                country_importing=country_importing,
                scenarios=scenarios,
                stressors_to_display=stressors_to_display,
                )
        else:
            print('WARNING: "option" argument must be "final demand" or "total imports".')


    def save_CoefRoW(
            self,
            region : str = "FR",
            stressors_list : list= ['GES', 'Matières premières'],
            SRIO_filename : str = "SRIO_FR_2015_Transitions"
            )->None:
        """" Compute and save CoefRoW for MatMat in outputs/CoefRoW folder.
        
        Args:
            region (str): region to compute the CoefRoW's
            stressor_lists (list of str): list of the calibrated stressors to save (see STRESSORS_DICT_DEF variable in src/stressors)
            SRIO_filename (str): name of the file in folder data/MatMat/ where SRIO from MatMat are stored (without ".xlsx" at the end !!).
        """
        save_CoefRoW(model=self,region=region, stressors_list=stressors_list, SRIO_filename=SRIO_filename)



class Counterfactual:
    def __init__(
        self,
        name: str,
        model: Model,
        scenar_function: Callable[[Model, bool, List[str], float], Tuple[pd.DataFrame]],
        **kwargs
    ):
        """Inits Counterfactual class

        Args:
            name (str): name of the counterfactual
            model (Model): object Model defined in model.py
            scenar_function (Callable[[Model, bool], Tuple[pd.DataFrame]]): builds the iot system
            reloc (bool, optional): True if relocation is allowed. Defaults to False.
        """

        self.name = name
        self.reloc=kwargs.get("reloc",False)
        self.sectors_list=kwargs.get("sectors_list",None)
        self.percentage_change=kwargs.get("percentage_change",None)

        self.scenar_stressors = kwargs.get("scenar_stressors", None)

        self.iot = build_counterfactual_data(
            model=model, scenar_function=scenar_function, **kwargs
        )
        # self.figures_dir = model.figures_dir / name / ("scenar_on_"+STRESSORS_DICT_DEF[self.scenar_stressors]["name_EN"])
        self.figures_dir = model.figures_dir / name
        # self.figures_dir.mkdir(exist_ok = True)#, parents=True)

        self.regions = model.regions
        self.sectors = model.sectors
        self.y_categories = model.y_categories
        
