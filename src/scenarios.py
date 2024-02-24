import numpy as np
import pandas as pd
import pymrio
import copy
from typing import Callable, Dict, List, Tuple

from src.utils import recal_stressor_per_region
from src.advance import extract_data
from src.model import Model
from src.stressors import STRESSORS_DICT_DEF
from src.settings import CAP_IMPORTS_INCREASE_PARAM, ALLIES, OPPONENTS, DEFAULT_SCENAR_STRESSORS

### AUXILIARY FUNCTIONS FOR SCENARIOS ###


def moves_final_demand_from_sorted_index_by_sector(
    model,
    sector: str,
    regions_index: List[int],
    reloc: bool = False
) -> Tuple[pd.DataFrame,pd.DataFrame]:
    """Allocates french final demand importations for a sector in the order given by region_index
        #firectly adapated from moves_from_sorted_index_by_sector hence the ressemblance and some weird approaches
 
    Args:
        model (Model): object Model defined in model.py
        sector (str): name of a product (or industry)
        regions_index (List[int]): list of ordered region indices
        reloc (bool): True if relocation is allowed. Defaults to None.

    Returns:
        Tuple[pd.DataFrame]: tuple with 2 elements :
            - DataFrame with the imports of 'sector' from regions (rows) for french final demands (columns)
    """

    if reloc:
        regions = model.regions
    else:
        regions = [ region for region in model.regions if region!="FR"] # remove FR
    Z = model.iot.Z   
    Y = model.iot.Y   


    # french total importations demand for each sector of final demand
    final_imports = Y["FR"].drop("FR", level=0).groupby(level=1).sum().loc[sector]
    total_imports = final_imports.sum()
    final_autoconso_FR = (
        Y.loc[("FR", sector), ("FR", slice(None))]
    )

    # export capacities of each regions the two parameters determine how much production each region/sector can do for France
    INCREASE_OVERALL=0
    INCREASE_FRENCH_EXPORT=1+CAP_IMPORTS_INCREASE_PARAM # if under 1 and INCREASE_OVERALL=0, reduces amounts available for france 
    export_capacities = {
        reg:  Y.drop(columns=reg, level=0).sum(axis=1).loc[(reg, sector)]*INCREASE_OVERALL
        + Y["FR"].sum(axis=1).loc[(reg, sector)]*INCREASE_FRENCH_EXPORT
        for reg in regions
    }

    # choice of the trade partners
    imports_from_regions = pd.Series(0, index=model.regions)
    remaining_imports = total_imports
    for i in regions_index:
        reg = regions[i]
        if export_capacities[reg] <= remaining_imports:
            imports_from_regions.loc[reg] = export_capacities[reg]
            remaining_imports -= export_capacities[reg]
        else:
            imports_from_regions.loc[reg] = remaining_imports
            break 
        
    
    # allocations for final imports
    new_final_imports = imports_from_regions.to_frame("").dot(
        (final_imports / total_imports).to_frame("").fillna(0).T
    )
    new_final_imports.loc["FR"] += final_autoconso_FR["FR"]
    
    # print(new_final_imports.sum()-Y.loc[(slice(None), sector), ("FR", slice(None))].sum())
 
    return new_final_imports


def moves_from_sorted_index_by_sector(
    model, percentage_change:float, sector: str,
    regions_index: List[int],
    reloc: bool = False,
    coeff_increase_by_region_sector=None,
    increase_french_import=CAP_IMPORTS_INCREASE_PARAM
) -> Tuple[pd.DataFrame,pd.DataFrame]:
    """Allocates french importations for a sector in the order given by region_index
 
    Args:
        model (Model): object Model defined in model.py
        sector (str): name of a product (or industry)
        regions_index (List[int]): list of ordered region indices
        reloc (bool): True if relocation is allowed. Defaults to None.
        percentage_change (float): percentage to reallocate (to reallocate 5%, the input should be 5)

    Returns:
        Tuple[pd.DataFrame]: tuple with 2 elements :
            - DataFrame with the imports of 'sector' from regions (rows) for french intermediary sectors (columns)
            - DataFrame with the imports of 'sector' from regions (rows) for french final demands (columns)
    """

    if reloc:
        regions = model.regions
    else:
        regions = [ region for region in model.regions if region!="FR"] # remove FR
    Z = model.iot.Z   
    Y = model.iot.Y   
     
    # french total importations demand for each sector / final demand
    inter_imports = Z["FR"].drop("FR", level=0).groupby(level=1).sum().loc[sector]
    final_imports = Y["FR"].drop("FR", level=0).groupby(level=1).sum().loc[sector]
        
    inter_autoconso_FR = (
        Z.loc[("FR", sector), ("FR", slice(None))]
    )
    final_autoconso_FR = (
        Y.loc[("FR", sector), ("FR", slice(None))]
    )

    #ICI
    inter_imports_before_change = inter_imports.copy()
    final_imports_before_change = final_imports.copy()
    # Si percentage_change est spécifié, on ajuste total_imports en conséquence
    if percentage_change is not None:
        inter_imports *= (1 + percentage_change/100)
        import_change_inter = inter_imports - inter_imports_before_change
        inter_autoconso_FR -= import_change_inter
        
        final_imports *= (1 + percentage_change/100)
        import_change_final = final_imports - final_imports_before_change
        final_autoconso_FR -= import_change_final

    total_imports = inter_imports.sum() + final_imports.sum()

    if coeff_increase_by_region_sector is None :
        # export capacities of each regions the two parameters determine how much production each region/sector can do for France
        INCREASE_OVERALL=0
        INCREASE_FRENCH_EXPORT=1 + increase_french_import # if under 1 and INCREASE_OVERALL=0, reduces amounts available for france ==> should create problems
        export_capacities = {
            reg: Z.drop(columns=reg, level=0).sum(axis=1).loc[(reg, sector)]*INCREASE_OVERALL
            + Y.drop(columns=reg, level=0).sum(axis=1).loc[(reg, sector)]*INCREASE_OVERALL
            + Z["FR"].sum(axis=1).loc[(reg, sector)]*INCREASE_FRENCH_EXPORT
            + Y["FR"].sum(axis=1).loc[(reg, sector)]*INCREASE_FRENCH_EXPORT
            for reg in regions
        }
    else : 
        export_capacities = {
            reg:  Z["FR"].sum(axis=1).loc[(reg, sector)]*(1 +coeff_increase_by_region_sector.loc[reg,sector])
            + Y["FR"].sum(axis=1).loc[(reg, sector)]*(1 +coeff_increase_by_region_sector.loc[reg,sector])
            for reg in regions
        }
        

    # choice of the trade partners
    imports_from_regions = pd.Series(0, index=model.regions)
    remaining_imports = total_imports
    for i in regions_index:
        reg = regions[i]
        if export_capacities[reg] <= remaining_imports:
            imports_from_regions.loc[reg] = export_capacities[reg]
            remaining_imports -= export_capacities[reg]
        else:
            imports_from_regions.loc[reg] = remaining_imports
            remaining_imports=0
            break 

    if remaining_imports>0:
        print("error {} remainig import not attributed {}".format(remaining_imports,sector))
    # allocations for intermediary imports
    new_inter_imports = imports_from_regions.to_frame("").dot(
        (inter_imports / total_imports).to_frame("").fillna(0).T
    )
    new_inter_imports.loc["FR"] += inter_autoconso_FR["FR"]

    # allocations for final imports
    new_final_imports = imports_from_regions.to_frame("").dot(
        (final_imports / total_imports).to_frame("").fillna(0).T
    )
    new_final_imports.loc["FR"] += final_autoconso_FR["FR"]

    return new_inter_imports, new_final_imports


def moves_final_demand_from_sort_rule(
    model,
    sorting_rule_by_sector: Callable[[Model,str, bool], List[int]],
    reloc: bool = False,
    scope: int =3,
) -> pymrio.IOSystem:
    """Allocates french final demand importations for all sectors, sorting the regions with a given rule for each sector

    Args:
        model (Model): object Model defined in model.py
        sorting_rule_by_sector (Callable[[str, bool], List[int]]): given a sector name and the reloc value, returns a sorted list of regions' indices
        reloc (bool, optional): True if relocation is allowed. Defaults to False.

    Returns:
        pymrio.IOSystem: modified pymrio model
    """

    sectors_list = model.sectors
    A = model.iot.A.copy()
    new_Y = model.iot.Y.copy()
    x=model.iot.x.copy()
    new_Y["FR"] = new_Y["FR"] * 0
    

    for sector in sectors_list:
        regions_index = sorting_rule_by_sector(model, sector, reloc,scope)
        new_final_imports = moves_final_demand_from_sorted_index_by_sector(
            model=model, sector=sector, regions_index=regions_index, reloc=reloc
        )
        new_Y.loc[(slice(None), sector), ("FR", slice(None))] = new_final_imports.values
    
    # integrate into mrio model 
    iot=model.iot.copy()
    iot.reset_to_coefficients()
    iot.L=None
    iot.A=A
    iot.x=None
    iot.Z=None
    iot.Y=new_Y
    iot.calc_all()
    
    return iot


def moves_from_sort_rule(
    model, sectors_list:List[str], percentage_change:float,
    sorting_rule_by_sector: Callable[[Model,str, bool, int, str], List[int]],
    reloc: bool = False,
    scope:int =3,
    coeff_increase_by_region_sector : pd.DataFrame = None,
    increase_french_import:float = CAP_IMPORTS_INCREASE_PARAM,
    scenar_stressors: str = DEFAULT_SCENAR_STRESSORS
) -> pymrio.IOSystem:
    """Allocates french importations for all sectors, sorting the regions with a given rule for each sector

    Args:
        model (Model): object Model defined in model.py
        sorting_rule_by_sector (Callable[[str, bool], List[int]]): given a sector name and the reloc value, returns a sorted list of regions' indices
        reloc (bool, optional): True if relocation is allowed. Defaults to False
        sectors_list (list): List of sectors to apply the scenario on
        coeff_increase_by_region_sector (pd.DataFrame, optional) : values per region and sector (with same aggregation as iot) of the possible amount of import increase from each foreign sector/region.
        increase_french_import (float): parameter to cap maximal increase of imports from France
        scenar_stressors (str): name of the stressors group to perform the sorting on (see predefined keys in STRESSORS_DICT_DEF variable in src/stressors.py)

    Returns:
        pymrio.IOSystem: modified pymrio model
    """

    stressors_used = STRESSORS_DICT_DEF[scenar_stressors]["dict"]

    new_Z = model.iot.Z.copy()
    new_Y = model.iot.Y.copy()
    x=model.iot.x.copy()
    new_Z.loc[(slice(None), sectors_list), ("FR", slice(None))] = new_Z.loc[(slice(None), sectors_list), ("FR", slice(None))] * 0
    new_Y.loc[(slice(None), sectors_list), ("FR", slice(None))] = new_Y.loc[(slice(None), sectors_list), ("FR", slice(None))] * 0

    for sector in sectors_list:
        regions_index = sorting_rule_by_sector(model, sector, reloc, scope, stressors_used)
        new_inter_imports, new_final_imports = moves_from_sorted_index_by_sector(
            model=model, sector=sector, regions_index=regions_index, reloc=reloc, coeff_increase_by_region_sector=coeff_increase_by_region_sector,
            percentage_change=percentage_change, increase_french_import=increase_french_import
        )
        new_Z.loc[(slice(None), sector), ("FR", slice(None))] = new_inter_imports.values
        new_Y.loc[(slice(None), sector), ("FR", slice(None))] = new_final_imports.values
    
    
    new_A=pymrio.tools.iomath.calc_A(new_Z,x)
    new_A=new_A.fillna(0)  # convert the changes we have one on Z to A, as it is the correct way to implement them
    # integrate into mrio model 
    iot=model.iot.copy()
    iot.reset_to_flows()
    iot.L=None
    iot.A=new_A
    iot.x=None
    iot.Z=None
    iot.Y=new_Y
    iot.calc_all()
    
    return iot


def sort_by_content(model, sector: str, reloc: bool = False,scope: int = 3,stressors_used: List[str]= None) -> List[int]:
    """Ascendantly sorts all regions by stressor content of a sector

    Args:
        model (Model): object Model defined in model.py
        sector (str): name of a product (or industry)
        reloc (bool, optional): True if relocation is allowed. Defaults to False.
        scope (int , optional): defines the scope of the content (1 or 3) 2 might needs special implementation based on energy sector aggregations
        stressors_used (str): list of the stressors names to perform the sorting on (see STRESSORS_DICT_DEF variable in stressors.py)

    Returns:
        np.array: array of indices of regions sorted by stressor content
    """
    
    if scope ==3:
        content=model.iot.stressor_extension.M.loc[stressors_used].sum(axis=0)
    elif scope ==1:
        content=model.iot.stressor_extension.S.loc[stressors_used].sum(axis=0)
    elif scope == 1.5:
        S=model.iot.stressor_extension.S.loc[stressors_used].sum(axis=0)
        content=S+model.iot.A.dot(S)
        
    if not reloc:
        content=content.drop("FR")
    regions_index = np.argsort(content[:, sector].values)
    return regions_index # type: ignore



### BEST AND WORST SCENARIOS ###


def scenar_best(
        model: Model,
        reloc: bool = False,
        scope:int =3,
        coeff_increase_by_region_sector : pd.DataFrame = None,
        # increase_french_import: float =CAP_IMPORTS_INCREASE_PARAM,
        scenar_stressors: str=DEFAULT_SCENAR_STRESSORS,
        percentage_change: float=None, # Nouvel argument pour définir le pourcentage d'importation à réallouer pour le secteur en cours
        sectors_list: list = None # Nouvel argument pour pouvoir définir une liste de secteurs particuliers où appliquer un scénario
        ) -> pymrio.IOSystem:
    """Finds the least stressor-intense imports reallocation for all sectors


    Args:
        model (Model): object Model defined in model.py
        reloc (bool, optional): True if relocation is allowed. Defaults to False.
        scope (int, optional): if sorting_rule_by_sector==sort_by_content, possible scope values = {3, 1, 1.5} (see sort_by_content function).
        coeff_increase_by_region_sector (pd.DataFrame, optional) : values per region and sector (with same aggregation as iot) of the possible amount of import increase from each foreign sector/region.
        scenar_stressors (str): name of the stressors group to perform the sorting on (see predefined keys in STRESSORS_DICT_DEF variable in src/stressors.py)


    Returns:
        Tuple[pd.DataFrame]: tuple with 2 elements :
            - reallocated Z matrix
            - reallocated Y matrix
    """
    sectors_list = model.sectors if not sectors_list else sectors_list

    return moves_from_sort_rule(
        model=model,
        sorting_rule_by_sector=sort_by_content,
        reloc=reloc,
        scope=scope,
        sectors_list=sectors_list,
        percentage_change=percentage_change,
        coeff_increase_by_region_sector=coeff_increase_by_region_sector,
        scenar_stressors=scenar_stressors
        # increase_french_import=increase_french_import,
    )


def scenar_worst(model: Model,
                 reloc: bool = False,
                 scope:int =3,
                 scenar_stressors: str=DEFAULT_SCENAR_STRESSORS,
                 # increase_french_import: float =CAP_IMPORTS_INCREASE_PARAM,
                 percentage_change: float=None,
                 sectors_list: list = None
                 ) -> pymrio.IOSystem:
    """Finds the most stressor-intense imports reallocation for all sectors


    Args:
        model (Model): object Model defined in model.py
        reloc (bool, optional): True if relocation is allowed. Defaults to False.
        scope (int, optional): if sorting_rule_by_sector==sort_by_content, possible scope values = {3, 1, 1.5} (see sort_by_content function).
        scenar_stressors (str): name of the stressors group to perform the sorting on (see predefined keys in STRESSORS_DICT_DEF variable in src/stressors.py)

    Returns:
        Tuple[pd.DataFrame]: tuple with 2 elements :
            - reallocated Z matrix
            - reallocated Y matrix
    """
    sectors_list = model.sectors if not sectors_list else sectors_list

    return moves_from_sort_rule(
        model=model,
        sorting_rule_by_sector=lambda *args: sort_by_content(*args)[::-1],
        scope=scope,
        sectors_list=sectors_list,
        percentage_change=percentage_change,
        reloc=reloc,
        scenar_stressors=scenar_stressors,
        # increase_french_import=increase_french_import,
    )


### BEST AND WORST SCENARIOS FOR FINAL DEMAND###


def scenar_best_final_demand(model: Model, reloc: bool = False, scope:int =3) -> pymrio.IOSystem:
    """Finds the least stressor-intense imports reallocation for all sectors


    Args:
        model (Model): object Model defined in model.py
        reloc (bool, optional): True if relocation is allowed. Defaults to False.

    Returns:
        Tuple[pd.DataFrame]: tuple with 2 elements :
            - reallocated Z matrix
            - reallocated Y matrix
    """

    return moves_final_demand_from_sort_rule(
        model=model, sorting_rule_by_sector=sort_by_content, reloc=reloc,scope=scope
    )


def scenar_worst_final_demand(model: Model, reloc: bool = False) -> pymrio.IOSystem:
    """Finds the most stressor-intense imports reallocation for all sectors


    Args:
        model (Model): object Model defined in model.py
        reloc (bool, optional): True if relocation is allowed. Defaults to False.

    Returns:
        Tuple[pd.DataFrame]: tuple with 2 elements :
            - reallocated Z matrix
            - reallocated Y matrix
    """

    return moves_final_demand_from_sort_rule(
        model=model,
        sorting_rule_by_sector=lambda *args: sort_by_content(*args)[::-1],
        reloc=reloc
    )

### PREFERENCE SCENARIOS ###


def scenar_pref(model, allies: List[str]=ALLIES, reloc: bool = False,
        percentage_change: float=None, # Nouvel argument pour définir le pourcentage d'importation à réallouer pour le secteur en cours
        sectors_list: list = None # Nouvel argument pour pouvoir définir une liste de secteurs particuliers où appliquer un scénario
        ) -> pymrio.IOSystem:
    """Finds imports reallocation in order to trade as much as possible with the allies

    Args:
        model (Model): object Model defined in model.py
        allies (List[str]): list of regions' names
        reloc (bool, optional): True if relocation is allowed. Defaults to False.

    Returns:
        Tuple[pd.DataFrame]: tuple with 2 elements :
            - reallocated Z matrix
            - reallocated Y matrix
    """

    if reloc:
        regions = model.regions
        if not "FR" in allies:
            allies += ["FR"]
    else:
        regions=[ region for region in model.regions if region!="FR"]  # remove FR

    new_Z = model.iot.Z.copy()
    new_Y = model.iot.Y.copy()
  
    


    sectors = model.sectors if not sectors_list else sectors_list
    
    new_Z.loc[(slice(None), sectors), ("FR", slice(None))] = new_Z.loc[(slice(None), sectors), ("FR", slice(None))] * 0
    new_Y.loc[(slice(None), sectors), ("FR", slice(None))] = new_Y.loc[(slice(None), sectors), ("FR", slice(None))] * 0

    for sector in sectors:
        # french total importations demand for each sector / final demand
        inter_imports = model.iot.Z["FR"].drop("FR", level=0).groupby(level=1).sum().loc[sector]
        final_imports = model.iot.Y["FR"].drop("FR", level=0).groupby(level=1).sum().loc[sector]
        inter_imports_before_change = inter_imports.copy()
        final_imports_before_change = final_imports.copy()
        
        # We compute the delta of importations
        inter_imports *= (1 + percentage_change/100)
        import_change_inter = inter_imports - inter_imports_before_change
        final_imports *= (1 + percentage_change/100)
        import_change_final = final_imports - final_imports_before_change
        
        
        ## overall trade related with sector
        sector_exports_Z = model.iot.Z.loc[(regions, sector), :].sum(axis=0, level=0)
        sector_exports_Y = model.iot.Y.loc[(regions, sector), :].sum(axis=0, level=0)
        sector_exports_by_region = sector_exports_Z.sum(
            axis=1, level=0
        ) + sector_exports_Y.sum(axis=1, level=0)

        ## french importations
        sector_imports_FR_Z = sector_exports_Z["FR"]
        sector_imports_FR_Y = sector_exports_Y["FR"]            
            
        sector_imports_FR_nonallies_Z = sector_imports_FR_Z.drop(allies).sum()
        sector_imports_FR_nonallies_Y = sector_imports_FR_Y.drop(allies).sum()
        total_imports_FR_nonallies = (
            sector_imports_FR_nonallies_Z.sum() + sector_imports_FR_nonallies_Y.sum()
        ) * (1 + percentage_change/100)
        
        ## allies' exportation capacities
        allies_export_except_FR = (
            sector_exports_by_region.loc[allies].drop(columns=["FR"]).sum(axis=1)
        )
        allies_autoexport = pd.Series(
            np.diagonal(sector_exports_by_region.loc[allies, allies]),
            index=allies,
        )
        allies_export_capacity = allies_export_except_FR.add(
            -allies_autoexport.drop("FR", errors="ignore"), fill_value=0
        )  # .add() handles the possible values of reloc
        allies_total_export_capacity = allies_export_capacity.sum()

        ## specific case leading to a division by 0
        if total_imports_FR_nonallies == 0 and allies_total_export_capacity == 0:
            for reg in regions:
                new_Z.loc[(reg, sector), ("FR", slice(None))] = sector_imports_FR_Z.loc[
                    reg
                ].values
                new_Y.loc[(reg, sector), ("FR", slice(None))] = sector_imports_FR_Y.loc[
                    reg
                ].values
            continue

        ## reallocations
        if total_imports_FR_nonallies < allies_total_export_capacity:

            coef_Z = (
                sector_imports_FR_nonallies_Z / allies_total_export_capacity
            )  # alpha_s for s in Z
            coef_Y = (
                sector_imports_FR_nonallies_Y / allies_total_export_capacity
            )  # alpha_s for s in Y

            for reg in regions:
                if reg in allies:
                    new_Z.loc[(reg, sector), ("FR", slice(None))] = (
                        sector_imports_FR_Z.loc[reg]
                        + coef_Z * allies_export_capacity[reg] if not percentage_change else sector_imports_FR_Z.loc[reg] + coef_Z * allies_export_capacity[reg] * (1 + percentage_change/100)
                    ).values
                    new_Y.loc[(reg, sector), ("FR", slice(None))] = (
                        sector_imports_FR_Y.loc[reg]
                        + coef_Y * allies_export_capacity[reg] if not percentage_change else sector_imports_FR_Y.loc[reg] + coef_Y * allies_export_capacity[reg] * (1 + percentage_change/100)
                    ).values
        else:
            coef_allies_Z = 1 + (
                allies_export_capacity.to_frame().dot(
                    sector_imports_FR_nonallies_Z.to_frame().T
                )
                / (sector_imports_FR_Z.loc[allies] * total_imports_FR_nonallies)
            ).replace([np.inf, -np.inf], np.nan).fillna(
                0
            )  # beta_r,s for Z
            coef_allies_Y = 1 + (
                allies_export_capacity.to_frame().dot(
                    sector_imports_FR_nonallies_Y.to_frame()
                    .replace([np.inf, -np.inf], np.nan)
                    .T
                )
                / (sector_imports_FR_Y.loc[allies] * total_imports_FR_nonallies)
            ).replace([np.inf, -np.inf], np.nan).fillna(
                0
            )  # beta_r,s for Y
            coef_nonallies = (
                1 - allies_total_export_capacity / total_imports_FR_nonallies
            )  # gamma

            for reg in regions:
                if reg not in allies:
                    new_Z.loc[(reg, sector), ("FR", slice(None))] = (
                        coef_nonallies * sector_imports_FR_Z.loc[reg] if not percentage_change else coef_nonallies * sector_imports_FR_2.loc[reg] * (1 + percentage_change/100)
                    ).values
                    new_Y.loc[(reg, sector), ("FR", slice(None))] = (
                        coef_nonallies * sector_imports_FR_Y.loc[reg] if not percentage_change else coef_nonallies * sector_imports_FR_Y.loc[reg] * (1 + percentage_change/100)
                    ).values
                else:
                    new_Z.loc[(reg, sector), ("FR", slice(None))] = (
                        coef_allies_Z.loc[reg] * sector_imports_FR_Z.loc[reg] if not percentage_change else coef_allies_Z.loc[reg] * sector_imports_FR_Z.loc[reg] * (1 + percentage_change/100)
                    ).values
                    new_Y.loc[(reg, sector), ("FR", slice(None))] = (
                        coef_allies_Y.loc[reg] * sector_imports_FR_Y.loc[reg] if not percentage_change else coef_allies_Y.loc[reg] * sector_imports_FR_Y.loc[reg] * (1 + percentage_change/100)
                    ).values

        ## process autoproduction
        new_Z.loc[("FR", sector), ("FR", slice(None))] += model.iot.Z.loc[
            ("FR", sector), ("FR", slice(None))
        ].values
        new_Y.loc[("FR", sector), ("FR", slice(None))] += model.iot.Y.loc[
            ("FR", sector), ("FR", slice(None))
        ].values
        
        new_Z.loc[("FR", sector), ("FR", slice(None))] -= import_change_inter
        new_Y.loc[("FR", sector), ("FR", slice(None))] -= import_change_final
    
    for sector in model.sectors:
        if sector not in sectors:
            new_Z.loc[("FR", sector), ("FR", slice(None))] += model.iot.Z.loc[
                ("FR", sector), ("FR", slice(None))
            ].values
            new_Y.loc[("FR", sector), ("FR", slice(None))] += model.iot.Y.loc[
                ("FR", sector), ("FR", slice(None))
            ].values
    
    
    
    new_A=pymrio.tools.iomath.calc_A(new_Z,model.iot.x)
    new_A=new_A.fillna(0)  # convert the changes we have one on Z to A, as it is the correct way to implement them
    # integrate into mrio model 
    iot=model.iot.copy()
    iot.reset_to_flows()
    iot.L=None
    iot.A=new_A
    iot.x=None
    iot.Z=None
    iot.Y=new_Y
    iot.calc_all()
    
    return iot


def scenar_pref_eu(model: Model, reloc: bool = False) -> pymrio.IOSystem:
    """Finds imports reallocation that prioritize trade with European Union

    Args:
        model (Model): object Model defined in model.py
        reloc (bool, optional): True if relocation is allowed. Defaults to False.

    Returns:
        Tuple[pd.DataFrame]: tuple with 2 elements :
            - reallocated Z matrix
            - reallocated Y matrix
    """

    return scenar_pref(model=model, allies=["EU"], reloc=reloc)


### TRADE WAR SCENARIOS ###


def scenar_tradewar(model: Model, opponents: List[str]=OPPONENTS, reloc: bool = False) -> pymrio.IOSystem:
    """Finds imports reallocation in order to exclude a list of opponents as much as possible

    Args:
        model (Model): object Model defined in model.py
        opponents (List[str]): list of regions' names
        reloc (bool, optional): True if relocation is allowed. Defaults to False.

    Returns:
        Tuple[pd.DataFrame,pd.DataFrame]: tuple with 2 elements :
            - reallocated Z matrix
            - reallocated Y matrix
    """

    allies = list(set(model.regions) - set(opponents))
    if not reloc:
        allies.remove("FR")
    
    return scenar_pref(model=model, allies=allies, reloc=reloc)


def scenar_tradewar_china(model: Model, reloc: bool = False) -> pymrio.IOSystem:
    """Finds imports reallocation that prevents trade with China as much as possible


    Args:
        model (Model): object Model defined in model.py
        reloc (bool, optional): True if relocation is allowed. Defaults to False.

    Returns:
        Tuple[pd.DataFrame]: tuple with 2 elements :
            - reallocated Z matrix
            - reallocated Y matrix
    """

    return scenar_tradewar(
        model=model, opponents=[ region for region in model.regions if "China" in region], reloc=reloc
    )

### DUMMY SCENARIO

def scenar_dummy(model, reloc: bool = False) -> pymrio.IOSystem:
    """Dummy scenario functions that return an unchanged scenario


    Args:
        model (Model): object Model defined in model.py
        reloc (bool, optional): True if relocation is allowed. Defaults to False. only available for compatibility

    Returns:
        
    """
    
    return model.iot.copy()


#ICI
### IMPORTATION SHIFT SCENARIO /!\ Il pourrait y avoir un problème en cas de demande d'importation suppérieure à la capacité d'un pays, il faudrait peut-être reprendre le code de scenar_pref dans cette fonction ?

def scenar_importation_shift(model: Model, percentage_change: float=None, sectors_list: list = None, reloc: bool=False) -> pymrio.IOSystem:
    
    """Imports reallocation in order to shift French importations

    Args:
        model (Model): object Model defined in model.py
        percentage_change (float, mandatory): rate of importation shift, balanced change from importations to autoconsumption
        reloc (bool, optional): True if relocation is allowed. Defaults to False.
        sectors_list (list, optional): list of sectors where the scenario applies
        
    Returns:
        iot
    """
    
    if reloc:
        regions = model.regions
    else:
        regions=[region for region in model.regions if region!="FR"]  # remove FR
        
    sectors = model.sectors if not sectors_list else sectors_list
    
    new_Z = model.iot.Z.copy()
    new_Y = model.iot.Y.copy()
      
    new_Z.loc[(slice(None), sectors), ("FR", slice(None))] = new_Z.loc[(slice(None), sectors), ("FR", slice(None))] * 0
    new_Y.loc[(slice(None), sectors), ("FR", slice(None))] = new_Y.loc[(slice(None), sectors), ("FR", slice(None))] * 0

    for sector in sectors:
        # french total importations demand for each sector / final demand
        inter_imports = model.iot.Z["FR"].drop("FR", level=0).groupby(level=1).sum().loc[sector]
        final_imports = model.iot.Y["FR"].drop("FR", level=0).groupby(level=1).sum().loc[sector]
        inter_imports_before_change = inter_imports.copy()
        final_imports_before_change = final_imports.copy()
        
        # We compute the delta of importations
        inter_imports *= (1 + percentage_change/100)
        import_change_inter = inter_imports - inter_imports_before_change
        final_imports *= (1 + percentage_change/100)
        import_change_final = final_imports - final_imports_before_change

        
        ## overall trade related with sector
        sector_exports_Z = model.iot.Z.loc[(regions, sector), :].sum(axis=0, level=0)
        sector_exports_Y = model.iot.Y.loc[(regions, sector), :].sum(axis=0, level=0)
        sector_exports_by_region = sector_exports_Z.sum(
            axis=1, level=0
        ) + sector_exports_Y.sum(axis=1, level=0)

        ## french importations
        sector_imports_FR_Z = sector_exports_Z["FR"]
        sector_imports_FR_Y = sector_exports_Y["FR"]
        
        inter_imports_before_change = sector_imports_FR_Z.copy()
        final_imports_before_change = sector_imports_FR_Y.copy()
        
        ## regions' exportation capacities
        regions_export_except_FR = (
            sector_exports_by_region.loc[regions].drop(columns=["FR"]).sum(axis=1)
        )
        regions_autoexport = pd.Series(
            np.diagonal(sector_exports_by_region.loc[regions, regions]),
            index=regions,
        )
        regions_export_capacity = regions_export_except_FR.add(
            -regions_autoexport.drop("FR", errors="ignore"), fill_value=0
        )  # .add() handles the possible values of reloc
        regions_total_export_capacity = regions_export_capacity.sum()

        ## reallocations
        for reg in regions:
            new_Z.loc[(reg, sector), ("FR", slice(None))] = (
    sector_imports_FR_Z.loc[reg]
    * (1 + percentage_change/100)).values

            new_Y.loc[(reg, sector), ("FR", slice(None))] = (
    sector_imports_FR_Y.loc[reg]
    * (1 + percentage_change/100)).values
            

        ## process autoproduction
        new_Z.loc[("FR", sector), ("FR", slice(None))] += model.iot.Z.loc[
            ("FR", sector), ("FR", slice(None))
        ].values
        new_Y.loc[("FR", sector), ("FR", slice(None))] += model.iot.Y.loc[
            ("FR", sector), ("FR", slice(None))
        ].values
        
        new_Z.loc[("FR", sector), ("FR", slice(None))] -= import_change_inter
        new_Y.loc[("FR", sector), ("FR", slice(None))] -= import_change_final
    
    for sector in model.sectors:
        if sector not in sectors:
            new_Z.loc[("FR", sector), ("FR", slice(None))] += model.iot.Z.loc[
                ("FR", sector), ("FR", slice(None))
            ].values
            new_Y.loc[("FR", sector), ("FR", slice(None))] += model.iot.Y.loc[
                ("FR", sector), ("FR", slice(None))
            ].values
    
    new_A=pymrio.tools.iomath.calc_A(new_Z,model.iot.x)
    new_A=new_A.fillna(0)  # convert the changes we have one on Z to A, as it is the correct way to implement them
    # integrate into mrio model 
    iot=model.iot.copy()
    iot.reset_to_flows()
    iot.L=None
    iot.A=new_A
    iot.x=None
    iot.Z=None
    iot.Y=new_Y
    iot.calc_all()
    
    return iot






### IMACLIM SCENARIOS



def emissivity_imaclim(model,year:int = 2050,scenario:str="INDC",except_FR=True,**kwargs) -> pymrio.IOSystem:
    """Import emissivity changes predicted by IMACLIM model into the iot model, more precisely into the emissivity matrix S
    
    Args:
        model (Model): object Model defined in model.py
        year (int, optional) : The year of the scenario we want to create. Allows to choose the right emissivity as IMACLIM predictions are given.on an annual basis. 
        scenario (str, optional) : The IMACLIM scenario from which the changes are taken from. 

    Returns:
        pymrio.IOSystem : the modififed iot object"""
        
    if except_FR:  # creates the list of countries for which we make no changes
        except_country=["FR"]
    else : except_country =[]
    
    data=extract_data(aggregation=model.aggregation_name)
    final_data_ratio,Link_country=data[0],data[2]
    
    final_data_ratio=final_data_ratio.swaplevel().sort_index()
    
    
    indexes=pd.Series(zip(final_data_ratio.index.get_level_values("scenario"),final_data_ratio.index.get_level_values("sector"))).unique()
    final_data_ratio=pd.concat([Link_country.dot(final_data_ratio.loc[scenario,sector]) for scenario,sector in indexes],
                                names=("scenario","sector","regions"),
								keys=indexes,
								axis=0)
    
    final_data_ratio=final_data_ratio.swaplevel().sort_index()

    iot=model.iot.copy()
    iot.stressor_extension.S.loc["CO2 - combustion"]= \
            pd.concat([iot.stressor_extension.S.loc["CO2 - combustion",region]*pd.Series(1+final_data_ratio.loc[(scenario,region),year],name="CO2 - combustion")  if region not in except_country
                    else iot.stressor_extension.S.loc["CO2 - combustion",region] for region in model.regions ],
                    axis=0,
                    names=("region","sector"),
                    keys=model.regions)

    # recompute the sorrect stressors based on the modifiations
    iot.stressor_extension=recal_stressor_per_region(
    iot=iot)
    
    return iot


def tech_change_imaclim(model,year:int = 2050,scenario="INDC",except_FR=True,**kwargs) -> pymrio.IOSystem:
    """Import technological changes predicted by IMACLIM model into the iot model, more precisely into the technical requirement matrix A
    
    Args:
        model (Model): object Model defined in model.py
        year (int, optional) : The year of the scenario we want to create. Allows to choose the right technological changes as IMACLIM preidtcion are on a annual basis. 
        scenario (str, optional) : The IMACLIM scenario from which the changes are taken from. 

    Returns:
        pymrio.IOSystem : the modififed iot object"""
    
    
    final_technical_coef=extract_data(aggregation=model.aggregation_name)[1]
    
    final_technical_coef_FR=final_technical_coef.copy()
    if "FR" in final_technical_coef.columns.get_level_values("region") and except_FR:
        final_technical_coef_FR.loc[:,(slice(None),slice(None),"FR")]=0 #not modifying French technologies (useful because that is done in MATMAT)
        
    
    
    iot=model.iot.copy()
    A=iot.A.copy()
    Y=iot.Y.copy()
    iot.reset_to_coefficients()
    iot.A=pd.concat([ pd.concat([A.loc[region_export,region_import]*(1+final_technical_coef_FR[scenario,year,region_import]) for region_import in model.regions],
                                names=("region","sector"),
                                keys=model.regions,
                                axis=1)
                     for region_export in model.regions],
                    names=("region","sector"),
                    keys=model.regions,
                    axis=0)
    iot.Y=Y
    iot.x = None
    iot.L=None
    #iot.Z = None # no change because reset_to_coefficients() does it already.
    
    #some checks and safeguards might be needed here in order to prevent coefficient sums in each columns of A to be greater than 1 (which can lead to negative results of consumption/production etc)
    columns_problem=iot.A.sum(axis=0)>1
    if (iot.A.sum(axis=0)>1).any():
        column_list=iot.A.loc[:,columns_problem].columns
        log_columns={}
        for column in column_list:
            big_numbers=iot.A.loc[:,column]>1 # first takes care of the coefs strictly bigger than 1
            iot.A.loc[big_numbers,column]/=(iot.A.loc[:,column].sum(axis=0)+1) # and divides them by sum of the column (this usually suffice if 1 or 2 huge values are responsible for >1)
            if iot.A.loc[:,column].sum()>1:
                iot.A.loc[:,column]/=(iot.A.loc[:,column].sum(axis=0)+0.1) # if still needed, rescale the whole column
            log_columns[column]=iot.A.loc[big_numbers,column].index
        print("Problems on sums of columns ",log_columns)#easy but dirty fix
     
    # completing the iot by calculating the missing parts
    iot.calc_all()
    
    # recompute the correct stressors based on the modifiations
    iot.stressor_extension=recal_stressor_per_region(
        iot=iot,)
    
    return iot
    
def production_change_imaclim(model,year:int =2050,scenario:str ="INDC",x_ref=None,ref_year:int=2015,scenario_for_ref_year=None,correct_negative_final_demand=True,**kwargs) -> pymrio.IOSystem:
    """Import total production changes predicted by IMACLIM model into the iot model, more precisely into the gross output vector x.
        Also create a fictional final demand Y that matches the gross output x, in order to keep a coherent iot. 
    
    Args:
        model (Model): object Model defined in model.py
        year (int, optional) : The year of the scenario we want to create. Allows to choose the right technological changes as IMACLIM preidtcion are on a annual basis. 
        scenario (str, optional) : The IMACLIM scenario from which the changes are taken from. 
        x_ref (pandas.DataFrame, optional) : The reference production from which relative changes should be applied, default to the current iot.x, but might be usefull to specify another if the current ones has already changed
        ref_year (int, optional) : The year of reference (from which the current IOT is), serves to know from which year to compute relative changes. 
        correct_negative_final_demand (bool, optinal) : Wether or not to make sure final demands are positive after it being obtained from gross output. If enabled might cause to deviate from original IMACLIM production and total emissions will be higher.
    Returns:
        pymrio.IOSystem : the modififed iot object"""

    if x_ref is None:
        x_ref=model.iot.x.sort_index().copy()
    else :
        x_ref=copy.deepcopy(x_ref.sort_index())
        
    if scenario_for_ref_year is None:
        scenario_for_ref_year=scenario
    
    production_data=extract_data(aggregation=model.aggregation_name)[4]
    
    #get the relative change in production over all sectors/region.
    production_change=production_data.loc[(scenario),year].sort_index()/production_data.loc[(scenario_for_ref_year),ref_year].sort_index()
    
    #create the new scenario iot tables that will include production changes
    iot=model.iot.copy()
    
    #include the production changes in the gross output x of new scenario
    iot.x["indout"]=x_ref["indout"]*production_change
    
    ### The following intend to enable the use of integaretd footprint calculator (they rely on Y and not x, hence modifying x makes no difference,
    ### we therfore create an artificial final demand Y that corresponds to the x we modififed)
    
    # Build a fictional Y matrix which would correspond to the current x : corresponds to the equation Y=(I-A)x
    Y_we_need=iot.x-iot.A.dot(iot.x) 

    # creates a fake detailed Y such that the row sums corresponds to the one we aim for ( we simply scale all values of a row)
    coeffs=Y_we_need["indout"]/iot.Y.sum(axis=1)  #dropped a values here for y_we_need
    for row_index in iot.Y.index:
        iot.Y.loc[row_index]=float(coeffs.loc[row_index])*iot.Y.loc[row_index]
    
    #the previous operations can lead to negative values if x is not determined according to similar technical coefficient, this gets rids of negative final demands
    if correct_negative_final_demand:
        iot.Y=iot.Y.mask(iot.Y.le(0),0)
        
    # we should now be able to compute some emissions, be carefull, the consumption based acounts don't make much sense here since we started with gross productions and made fictional Y
    iot.stressor_extension=recal_stressor_per_region(
            iot=iot,recalc_F_Y=True)
    
    return iot

def consumption_change_imaclim(model,year:int = 2050, scenario:str = "INDC", Y_ref=None,ref_year:int=2015,**kwargs) -> pymrio.IOSystem:
    """Import final demand changes predicted by IMACLIM model into the iot model, more precisely into the final demand_matrix Y
    
    Args:
        model (Model): object Model defined in model.py
        year (int, optional) : The year of the scenario we want to create. Allows to choose the right technological changes as IMACLIM preidtcion are on a annual basis. 
        scenario (str, optional) : The IMACLIM scenario from which the changes are taken from. 
        Y_ref (pandas.DataFrame, optional) : The reference demand from which relative changes should be applied, default to the current iot.x, but might be usefull to specify another if the current ones has already changed
        ref_year (int, optional) : The year of reference (from which the current IOT is), serves to know from which year to compute relative changes. 

    Returns:
        pymrio.IOSystem : the modififed iot object"""
    
    if Y_ref is None:
        Y_ref=model.iot.Y.sort_index().copy()
    else :
        Y_ref=copy.deepcopy(Y_ref.sort_index())
        
    consumption_data=extract_data(aggregation=model.aggregation_name)[5]
    
    consumption_change=consumption_data.loc[(scenario),year].sort_index()/consumption_data.loc[(scenario),ref_year].sort_index()
    
    iot=model.iot.copy()
    Y=iot.Y.copy()
    iot.reset_to_flows()
    for region in model.regions:
        for column in Y[region].columns:
            Y[(region,column)]=Y[(region,column)]*consumption_change.loc[region]
    iot.Y=Y
    
    iot.calc_all()
    
    iot.stressor_extension=recal_stressor_per_region(
            iot=iot,recalc_F_Y=True)
    return iot


### AVAILABLE SCENARIOS ###

DICT_SCENARIOS = {
    "best": scenar_best,
    #"best final demand":scenar_best_final_demand,
    "worst": scenar_worst,
    #"worst final demand": scenar_worst_final_demand,
    #"pref_eu": scenar_pref_eu,
    "pref_region": scenar_pref,
    #"tradewar_china": scenar_tradewar_china,
    "tradewar_region":scenar_tradewar,
    "dummy":scenar_dummy,
    "importation_shift": scenar_importation_shift,
    "importation_shift_v0": scenar_importation_shift_v0,
    "emissivity_IMACLIM":emissivity_imaclim,
    "technical_change_IMACLIM":tech_change_imaclim,
    #"production_change_IMACLIM":production_change_imaclim,
    #"consumption_change_imaclim":consumption_change_imaclim,
}
