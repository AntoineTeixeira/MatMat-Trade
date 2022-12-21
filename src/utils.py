import os
import numpy as np
import pandas as pd
import pathlib
import pickle as pkl
import pycountry
import pymrio
from pymrio.tools import ioutil
from pymrio.tools.iomath import calc_F_Y
from scipy.io import loadmat
from typing import Dict
import warnings
import wget


from src.settings import AGGREGATION_DIR


# remove pandas warning related to pymrio future deprecations
warnings.simplefilter(action="ignore", category=FutureWarning)


### AUXILIARY FUNCTION FOR DATA BUILDERS ###


def recal_stressor_per_region(
    iot: pymrio.IOSystem,
    recalc_F_Y: bool = False,
) -> pymrio.core.mriosystem.Extension:
    """Computes the account matrices D_cba, D_pba, D_imp, D_exp and optionally F_Y
       Based on pymrio.tools.iomath's function 'calc_accounts', see https://github.com/konstantinstadler/pymrio

    Args:
        iot (pymrio.IOSystem): pymrio MRIO object
        recalc_F_Y (Bool, optional) : allows to make the function recalculate F_Y as well, usefull if a change of final demand happend

    Returns:
        pymrio.core.mriosystem.Extension: extension with account matrices completed
    """
    extension = iot.stressor_extension.copy()

    S = iot.stressor_extension.S
    L = iot.L
    Y_vect = iot.Y.sum(level=0, axis=1)
    nbsectors = len(iot.get_sectors())
    extension.M=S@L

    Y_diag = ioutil.diagonalize_blocks(Y_vect.values, blocksize=nbsectors)
    Y_diag = pd.DataFrame(Y_diag, index=Y_vect.index, columns=Y_vect.index)
    x_diag = L.dot(Y_diag)

    regions = x_diag.index.get_level_values("region").unique()

    # calc footprint
    extension.D_cba = pd.concat(
        [S[reg].dot(x_diag.loc[reg]) for reg in regions],
        axis=0,
        keys=regions,
        names=["region"],
    )

    # calc production based account
    x_tot = x_diag.sum(axis=1, level=0)
    extension.D_pba = pd.concat(
        [S.mul(x_tot[reg]) for reg in regions],
        axis=0,
        keys=regions,
        names=["region"],
    )

    # for the traded accounts set the domestic industry output to zero
    dom_block = np.zeros((nbsectors, nbsectors))
    x_trade = pd.DataFrame(
        ioutil.set_block(x_diag.values, dom_block),
        index=x_diag.index,
        columns=x_diag.columns,
    )
    extension.D_imp = pd.concat(
        [S[reg].dot(x_trade.loc[reg]) for reg in regions],
        axis=0,
        keys=regions,
        names=["region"],
    )

    x_exp = x_trade.sum(axis=1, level=0)
    extension.D_exp = pd.concat(
        [S.mul(x_exp[reg]) for reg in regions],
        axis=0,
        keys=regions,
        names=["region"],
    )

    if recalc_F_Y:
        S_Y=iot.stressor_extension.S_Y
        y=iot.Y.sum()
        extension.F_Y=calc_F_Y(S_Y,y)
    
    return extension

def get_very_detailed_emissions(iot: pymrio.IOSystem) -> pd.DataFrame:
    """Computes a precise accounting of the impacts on stressors of the production, with easy traceability to both producing industry
    and the final demand for which it is being produced

    Args:
        iot (pymrio.IOSystem): pymrio MRIO object

    Returns:
        pd.DataFrame : A detailed accounting matrix with rows for each region/sectors/stressor of production and columns for each region/goods of final demand.
    """
    S = iot.stressor_extension.S
    L = iot.L
    Y_vect = iot.Y.sum(level=0, axis=1)
    nbsectors = len(iot.get_sectors())

    Y_diag = ioutil.diagonalize_blocks(Y_vect.values, blocksize=nbsectors)
    Y_diag = pd.DataFrame(Y_diag, index=Y_vect.index, columns=Y_vect.index)
    
    #for x_diag the row is the sector/region producing and the column the region/sector consumming
    x_diag = L.dot(Y_diag)
    
    # DPDS is short for Detailed Production Demand Stressor matrix. It needs one value of stressor for
    # each region/sector of production responding to each region/sector of demand
    
    #Making the matrix
    DPDS=pd.concat([x_diag.copy() for stressor in range(iot.stressor_extension.S.shape[0])])
    DPDS.sort_index(inplace=True)
    DPDS.reset_index(inplace=True)
    stressors=np.array( [iot.stressor_extension.S.index.values for production_sources in x_diag.index]).flatten()
    DPDS["stressor"]=stressors
    DPDS.set_index(["region","sector","stressor"],inplace=True)
    
    # here for each production type and location we compute for each stressor the amount of impact.  
    DPDS=pd.concat([iot.stressor_extension.S.loc[stressor,(producing_region,producing_sector)]*x_diag.loc[(producing_region,producing_sector)]for producing_region,producing_sector,stressor in DPDS.index],
          keys=DPDS.index,
          axis=1).T.sort_index()
    
    return DPDS

def get_total_imports_region(iot: pymrio.IOSystem,region:str)-> pd.Series:
    """Computes the amount imported goods by types of demands (intermediate and final). 
    
    Args:
        iot (pymrio.IOSystem): pymrio MRIO object
        region (str): the region for which we want to compute the average stressor coefficents

    Returns:
        pd.Series : A Series of the stressor coefficient MultiIndexed by sector of final demand and stressor names
    """
    
    L = iot.L
    A=iot.A
    Y_vect = iot.Y.sum(level=0, axis=1)
    nbsectors = len(iot.get_sectors())

    Y_diag = ioutil.diagonalize_blocks(Y_vect.values, blocksize=nbsectors)
    Y_diag = pd.DataFrame(Y_diag, index=Y_vect.index, columns=Y_vect.index)
    
    # we isolate the imported final demand 
    imported_final=Y_vect[region].copy()
    imported_final[region]=0
    
    # we isolate the imported intermediate demand, deducted from the gross output of the region and the technical coefficients.
    x = L.dot(iot.Y.sum(axis=1)) #summing along axis 1 beacuse where the production goes is not relevant
    x_region=pd.DataFrame(x.loc[(region,slice(None))]).sort_index()
    imported_intermediate=A[region].sort_index().dot(x_region.values) 
    imported_intermediate.loc[(region,slice(None))]=0
    
    total_imports=imported_final.add(imported_intermediate[0])
    return total_imports
    

def get_import_mean_stressor(iot: pymrio.IOSystem,region:str)-> pd.Series:
    """Computes the average stressor impact of imported goods by types of demands (intermediate and final). 
    This corresponds to CoefRoW in MatMat.
    
    Args:
        iot (pymrio.IOSystem): pymrio MRIO object
        region (str): the region for which we want to compute the average stressor coefficents

    Returns:
        pd.Series : A Series of the stressor coefficient MultiIndexed by sector of final demand and stressor names
    """
    
    
    S = iot.stressor_extension.S
    L = iot.L
    
    total_imports=get_total_imports_region(iot,region)
    
    # Know those totals imports are used to get a weighted average of stressor impact per industry over the different import sources
    
    S_L=S.dot(L)
    import_mean_stressor=pd.concat([total_imports.mul(S_L.loc[stressor]).sum(level=1)/total_imports.sum(level=1)  for stressor in S_L.index.get_level_values(0).unique()],
                                     keys=S_L.index.get_level_values(0).unique())
    
    return import_mean_stressor
    


def convert_region_from_capital_matrix(reg: str) -> str:
    """Converts a capital matrix-formatted region code into an Exiobase-formatted region code

    Args:
        reg (str): capital matrix-formatted region code

    Returns:
        str: Exiobase v3-formatted region code
    """

    try:
        return pycountry.countries.get(alpha_3=reg).alpha_2
    except AttributeError:
        if reg == "ROM":
            return "RO"  # for Roumania, UNDP country code differs from alpha_3
        elif reg in ["WWA", "WWL", "WWE", "WWF", "WWM"]:
            return reg[1:]
        else:
            raise (ValueError, f"the country code {reg} is unkown.")


def load_Kbar(year: int, system: str, path: pathlib.PosixPath) -> pd.DataFrame:
    """Loads capital consumption matrix as a Pandas dataframe (including downloading if necessary)

    Args:
        year (int): year in 4 digits
        system (str): system ('pxp', 'pxi')
        path (pathlib.PosixPath): where to save the .mat file

    Returns:
        pd.DataFrame: same formatting than pymrio's Z matrix
    """
    if not os.path.isfile(path):
        wget.download(
            f"https://zenodo.org/record/3874309/files/Kbar_exio_v3_6_{year}{system}.mat",
            str(path),
        )
    data_dict = loadmat(path)
    data_array = data_dict["KbarCfc"]
    capital_regions = [
        convert_region_from_capital_matrix(reg[0][0]) for reg in data_dict["countries"]
    ]
    capital_sectors = [sec[0][0] for sec in data_dict["prodLabels"]]
    capital_multiindex = pd.MultiIndex.from_tuples(
        [(reg, sec) for reg in capital_regions for sec in capital_sectors],
        names=["region", "sector"],
    )
    return pd.DataFrame.sparse.from_spmatrix(
        data_array, index=capital_multiindex, columns=capital_multiindex
    )


### DATA BUILDERS ###


def build_reference_data(model) -> pymrio.IOSystem:
    """Builds the pymrio object given reference's settings

    Args:
        model (Model): object Model defined in model.py

    Returns:
        pymrio.IOSystem: pymrio object
    """

    # checks if calibration is necessary
    force_calib = not os.path.isfile(model.model_dir / "file_parameters.json")

    # create directories if necessary
    for path in [model.exiobase_dir, model.model_dir, model.figures_dir]:
        if not os.path.isdir(path):
            os.mkdir(path)

    # downloading data if necessary
    if not os.path.isfile(model.exiobase_dir / model.raw_file_name):
        print("Downloading data... (may take a few minutes)")
        pymrio.download_exiobase3(
            storage_folder=model.exiobase_dir,
            system=model.system,
            years=model.base_year,
        )
        print("Data downloaded successfully !")

    if model.calib or force_calib:

        print("Loading data... (may take a few minutes)")

        # import exiobase data
        if os.path.isfile(model.exiobase_dir / model.exiobase_pickle_file_name):
            with open(model.exiobase_dir / model.exiobase_pickle_file_name, "rb") as f:
                iot = pkl.load(f)
        else:
            iot = pymrio.parse_exiobase3(  # may need RAM + SWAP ~ 15 Gb
                model.exiobase_dir / model.raw_file_name
            )
            with open(model.exiobase_dir / model.exiobase_pickle_file_name, "wb") as f:
                pkl.dump(iot, f)

        # endogenize capital
        if model.capital:
            Kbar = load_Kbar(
                year=model.base_year,
                system=model.system,
                path=model.capital_consumption_path,
            )
            iot.Z += Kbar
            cfc = iot.satellite.S.loc["Operating surplus: Consumption of fixed capital"]
            gfcf = iot.Y.loc[
                slice(None), (slice(None), "Gross fixed capital formation")
            ]
            iot.Y.loc[slice(None), (slice(None), "Gross fixed capital formation")] -= (
                gfcf.divide(
                    gfcf.sum(axis=1), axis="index"
                )  # the CFC is shared among regions depending on their current level of investment in the associated couple (region x sector)
                .fillna(
                    1 / len(iot.get_regions())
                )  # given that past investments are not available, if no region invests currently in a specific region's sector, then the investment is assumed to be equitable among all regions
                .multiply(cfc, axis="index")
            )

            # capital endogenization check

            supply = iot.Y.sum(axis=1) + iot.Z.sum(axis=1)
            use = iot.satellite.F.iloc[:9].sum(axis=0) + iot.Z.sum(axis=0)
            print(
                "--- Vérification de l'équilibre emplois/ressources après endogénéisation du capital ---"
            )
            print(f"Le R² des vecteurs emplois/ressources est de {supply.corr(use)}.")
            print(f"Emplois - Ressources = {use.sum() - supply.sum()}")
            print(
                f"abs(Emplois - Ressources) / Emplois = {abs(use.sum() - supply.sum()) / use.sum()}"
            )

        # extract emissions
        extension_list = list()

        for stressor in model.stressor_dict.keys():

            extension = pymrio.Extension(stressor)

            for elt in ["F", "F_Y", "unit"]:

                component = getattr(iot.satellite, elt).loc[
                    model.stressor_dict[stressor]["exiobase_keys"]
                ]

                if elt == "unit":
                    component = pd.DataFrame(
                        component.values[0],
                        index=pd.Index([stressor]),
                        columns=["unit"],
                    )
                else:
                    component = (
                        component.sum(axis=0).to_frame(stressor).T
                        * model.stressor_dict[stressor]["weight"]
                    )

                setattr(extension, elt, component)

            extension_list.append(extension)

        iot.stressor_extension = pymrio.concate_extension(
            extension_list, name="stressors"
        )

        # del useless extensions
        iot.remove_extension(["satellite", "impacts"])

        # import aggregation matrices
        agg_matrix = {
            axis: pd.read_excel(
                AGGREGATION_DIR / f"{model.aggregation_name}.xlsx", sheet_name=axis
            )
            for axis in ["sectors", "regions"]
        }
        agg_matrix["sectors"].set_index(
            ["category", "sub_category", "sector"], inplace=True
        )
        agg_matrix["regions"].set_index(["Country name", "Country code"], inplace=True)

        # apply regional and sectorial agregations
        iot.aggregate(
            region_agg=agg_matrix["regions"].T.values,
            sector_agg=agg_matrix["sectors"].T.values,
            region_names=agg_matrix["regions"].columns.tolist(),
            sector_names=agg_matrix["sectors"].columns.tolist(),
        )

        # reset A, L, S, S_Y, M and all of the account matrices
        iot = iot.reset_to_flows()
        iot.stressor_extension.reset_to_flows()

        # compute missing matrices
        iot.calc_all()

        # compute emission accounts by region
        iot.stressor_extension = recal_stressor_per_region(iot=iot)

        # save model
        iot.save_all(model.model_dir)

        print("Data loaded successfully !")

    else:

        # import calibration data previously built with calib = True
        iot = pymrio.parse_exiobase3(model.model_dir)

    return iot


def build_counterfactual_data(
    model,
    scenar_function,
    **kwargs
) -> pymrio.IOSystem:
    """Builds the pymrio object given reference's settings and the scenario parameters

    Args:
        model (Model): object Model defined in model.py
        scenar_function (Callable[[Model, bool], Tuple[pd.DataFrame]]): builds the new Z and Y matrices
        **kwargs used :
            reloc (bool, optional): True if relocation is allowed. Defaults to False.
            year (int,optional) : Year for which the scenario is created. 
    Returns:
        pymrio.IOSystem: modified pymrio model
    """
    
    iot=scenar_function(model=model,**kwargs)
    
    iot.calc_all()

    iot.stressor_extension = recal_stressor_per_region(
        iot=iot,
    )

    return iot


### AGGREGATORS ###


def reverse_mapper(mapper: Dict) -> Dict:
    """Reverse a mapping dictionary

    Args:
        mapper (Dict): dictionnary with new categories as keys and old ones as values, no aggregation if is None. Defaults to None.

    Returns:
        Dict: dictionnary with old categories as keys and new ones as values, no aggregation if is None.
    """

    if mapper is None:
        return None

    new_mapper = {}
    for key, value in mapper.items():
        for elt in value:
            new_mapper[elt] = key

    return new_mapper


def aggregate_avg_simple_index(
    df: pd.DataFrame,
    axis: int,
    new_index: pd.Index,
    reverse_mapper: Dict = None,
) -> pd.DataFrame:
    """Aggregates data along given axis according to mapper.
    WARNING: the aggregation is based on means, so it works only with intensive data.

    Args:
        df (pd.DataFrame): multiindexed DataFrame
        axis (int): axis of aggregation (0 or 1)
        new_index (pd.Index): aggregated index (useful to set the right order)
        reverse_mapper (Dict, optional): dictionnary with old categories as keys and new ones as values, no aggregation if is None. Defaults to None.
    Returns:
        pd.DataFrame: aggregated DataFrame
    """
    if reverse_mapper is None:
        return df
    if axis == 1:
        df = df.T
    df = df.groupby(df.index.map(lambda x: reverse_mapper[x])).mean().reindex(new_index)
    if axis == 1:
        df = df.T
    return df


def aggregate_sum(
    df: pd.DataFrame,
    level: int,
    axis: int,
    new_index: pd.Index,
    reverse_mapper: Dict = None,
) -> pd.DataFrame:
    """Aggregates data at given level along given axis according to mapper.
    WARNING: the aggregation is based on sums, so it works only with additive data.

    Args:
        df (pd.DataFrame): multiindexed DataFrame
        level (int): level of aggregation on multiindex (0 or 1)
        axis (int): axis of aggregation (0 or 1)
        new_index (pd.Index): aggregated index (useful to set the right order)
        reverse_mapper (Dict, optional): dictionnary with old categories as keys and new ones as values, no aggregation if is None. Defaults to None.
    Returns:
        pd.DataFrame: aggregated DataFrame
    """
    if reverse_mapper is None:
        return df
    if axis == 1:
        df = df.T
    if level == 0:
        index_level_1 = df.index.get_level_values(1).drop_duplicates()
        df = (
            df.groupby(
                [
                    df.index.get_level_values(0).map(lambda x: reverse_mapper[x]),
                    df.index.get_level_values(1),
                ]
            )
            .sum()
            .reindex(new_index, level=0)
            .reindex(index_level_1, level=1)
        )
    else:  # level = 1
        index_level_0 = df.index.get_level_values(0).drop_duplicates()
        df = (
            df.groupby(
                [
                    df.index.get_level_values(0),
                    df.index.get_level_values(1).map(lambda x: reverse_mapper[x]),
                ]
            )
            .sum()
            .reindex(new_index, level=1)
            .reindex(index_level_0, level=0)
        )
    if axis == 1:
        df = df.T
    return df


def aggregate_sum_axis(
    df: pd.DataFrame,
    axis: int,
    new_index_0: pd.Index,
    new_index_1: pd.Index,
    reverse_mapper_0: Dict = None,
    reverse_mapper_1: Dict = None,
) -> pd.DataFrame:
    """Aggregates data at all levels (0 and 1) along given axis according to both mappers.
    WARNING: the aggregation is based on sums, so it works only with additive data.

    Args:
        df (pd.DataFrame): multiindexed DataFrame
        axis (int): axis of aggregation (0 or 1)
        new_index_0 (pd.Index): aggregated index at level 0 (useful to set the right order)
        new_index_1 (pd.Index): aggregated index at level 1 (useful to set the right order)
        reverse_mapper_0 (Dict, optional): dictionnary with old categories as keys and new ones as values at level 0, no aggregation if is None. Defaults to None.
        reverse_mapper_1 (Dict, optional): dictionnary with old categories as keys and new ones as values at level 1, no aggregation if is None. Defaults to None.

    Returns:
        pd.DataFrame: aggregated DataFrame
    """

    return aggregate_sum(
        df=aggregate_sum(
            df=df,
            level=0,
            axis=axis,
            new_index=new_index_0,
            reverse_mapper=reverse_mapper_0,
        ),
        level=1,
        axis=axis,
        new_index=new_index_1,
        reverse_mapper=reverse_mapper_1,
    )


def aggregate_sum_2levels_2axes(
    df: pd.DataFrame,
    new_index_0: pd.Index,
    new_index_1: pd.Index,
    reverse_mapper_0: Dict = None,
    reverse_mapper_1: Dict = None,
) -> pd.DataFrame:
    """Aggregates data at all levels (0 and 1) along all axes (0 and 1) according to both mappers, with a DataFrame whose MultiIndex is identical along both axes.
    WARNING: the aggregation is based on sums, so it works only with additive data.

    Args:
        df (pd.DataFrame): multiindexed DataFrame
        new_index_0 (pd.Index): aggregated index at level 0 (useful to set the right order)
        new_index_1 (pd.Index): aggregated index at level 1 (useful to set the right order)
        reverse_mapper_0 (Dict, optional): dictionnary with old categories as keys and new ones as values at level 0, no aggregation if is None. Defaults to None.
        reverse_mapper_1 (Dict, optional): dictionnary with old categories as keys and new ones as values at level 1, no aggregation if is None. Defaults to None.

    Returns:
        pd.DataFrame: aggregated DataFrame
    """

    return aggregate_sum_axis(
        df=aggregate_sum_axis(
            df=df,
            axis=0,
            new_index_0=new_index_0,
            new_index_1=new_index_1,
            reverse_mapper_0=reverse_mapper_0,
            reverse_mapper_1=reverse_mapper_1,
        ),
        axis=1,
        new_index_0=new_index_0,
        new_index_1=new_index_1,
        reverse_mapper_0=reverse_mapper_0,
        reverse_mapper_1=reverse_mapper_1,
    )


def aggregate_sum_2levels_on_axis1_level0_on_axis0(
    df: pd.DataFrame,
    new_index_0: pd.Index,
    new_index_1: pd.Index,
    reverse_mapper_0: Dict = None,
    reverse_mapper_1: Dict = None,
) -> pd.DataFrame:
    """Aggregates data at all levels (0 and 1) along axis 1 and at level 0 only along axis 0 according to both mappers.
    WARNING: the aggregation is based on sums, so it works only with additive data.

    Args:
        df (pd.DataFrame): multiindexed DataFrame
        new_index_0 (pd.Index): aggregated index at level 0 (useful to set the right order)
        new_index_1 (pd.Index): aggregated index at level 1 (useful to set the right order)
        reverse_mapper_0 (Dict, optional): dictionnary with old categories as keys and new ones as values at level 0, no aggregation if is None. Defaults to None.
        reverse_mapper_1 (Dict, optional): dictionnary with old categories as keys and new ones as values at level 1, no aggregation if is None. Defaults to None.

    Returns:
        pd.DataFrame: aggregated DataFrame
    """

    return aggregate_sum(
        df=aggregate_sum_2levels_2axes(
            df=df,
            new_index_0=new_index_0,
            new_index_1=None,
            reverse_mapper_0=reverse_mapper_0,
            reverse_mapper_1=None,
        ),
        level=1,
        axis=1,
        new_index=new_index_1,
        reverse_mapper=reverse_mapper_1,
    )


def aggregate_sum_level0_on_axis1_2levels_on_axis0(
    df: pd.DataFrame,
    new_index_0: pd.Index,
    new_index_1: pd.Index,
    reverse_mapper_0: Dict = None,
    reverse_mapper_1: Dict = None,
) -> pd.DataFrame:
    """Aggregates data at level 0 along axis 1 and at all levels (0 and 1) along axis 0 according to both mappers.
    WARNING: the aggregation is based on sums, so it works only with additive data.

    Args:
        df (pd.DataFrame): multiindexed DataFrame
        new_index_0 (pd.Index): aggregated index at level 0 (useful to set the right order)
        new_index_1 (pd.Index): aggregated index at level 1 (useful to set the right order)
        reverse_mapper_0 (Dict, optional): dictionnary with old categories as keys and new ones as values at level 0, no aggregation if is None. Defaults to None.
        reverse_mapper_1 (Dict, optional): dictionnary with old categories as keys and new ones as values at level 1, no aggregation if is None. Defaults to None.

    Returns:
        pd.DataFrame: aggregated DataFrame
    """

    return aggregate_sum(
        df=aggregate_sum_2levels_2axes(
            df=df,
            new_index_0=new_index_0,
            new_index_1=None,
            reverse_mapper_0=reverse_mapper_0,
            reverse_mapper_1=None,
        ),
        level=1,
        axis=0,
        new_index=new_index_1,
        reverse_mapper=reverse_mapper_1,
    )


### FEATURE EXTRACTORS ###


def footprint_extractor(model, region: str = "FR") -> Dict:
    """Computes region's footprint (D_pba-D_exp+D_imp+F_Y)

    Args:
        model (Union[Model, Counterfactual]): object Model or Counterfactual defined in model.py
        region (str, optional): region name. Defaults to "FR".

    Returns:
        Dict: values of -D_exp, D_pba, D_imp and F_Y
    """
    stressor_extension = model.iot.stressor_extension
    return {
        "Exportations": -stressor_extension.D_exp[region].sum().sum(),
        "Production": stressor_extension.D_pba[region].sum().sum(),
        "Importations": stressor_extension.D_imp[region].sum().sum(),
        "Consommation": stressor_extension.F_Y[region].sum().sum(),
    }


### AUXILIARY FUNCTIONS FOR FIGURES EDITING ###


def build_description(model, counterfactual_name: str = None) -> str:
    """Builds a descriptions of the parameters used to edit a figure

    Args:
        model (Model): object Model defined in model.py
        counterfactual_name (str, optional): name of the counterfactual in model.counterfactuals. None for the reference, False for multiscenario figures. Defaults to None.

    Returns:
        str: description
    """
    if counterfactual_name is None:
        output = "Scénario de référence\n"
    elif not counterfactual_name:
        output = ""
    else:
        output = f"Scénario : {counterfactual_name}\n"
    output += f"Année : {model.base_year}\n"
    output += f"Système : {model.system}\n"
    output += f"Stressor : {model.stressor_name}\n"
    output += f"Base de données : Exiobase {model.iot.meta.version}\n"
    if model.capital:
        output += "Modèle à capital endogène"
    else:
        output += "Modèle sans capital endogène"
    if counterfactual_name:
        if model.counterfactuals[counterfactual_name].reloc:
            output += "\nScénario avec relocalisation"
        else:
            output += "\nScénario sans relocalisation"
    return output
