import matplotlib.ticker as mtick
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import pathlib
import seaborn as sns
from unidecode import unidecode
import plotly.express as px
import pymrio
import kaleido

from src.settings import COLORS, COLORS_NO_FR
from src.utils import (
    aggregate_sum,
    aggregate_sum_2levels_2axes,
    aggregate_sum_2levels_on_axis1_level0_on_axis0,
    aggregate_sum_axis,
    aggregate_sum_level0_on_axis1_2levels_on_axis0,
    aggregate_avg_simple_index,
    build_description,
    footprint_extractor,
    get_total_imports_region,
    get_very_detailed_emissions,
    diagonalize_columns_to_sectors,
    find_stressor_unit
)
from src.stressors import GHG_STRESSOR_NAMES
# from src.stressors import MATERIAL_STRESSOR_NAMES
# from src.stressors import GHG_AND_MATERIALS_PARAM
# from src.stressors import STRESSOR_DICT_GHG_MAT
from src.stressors import STRESSORS_DICT_DEF#, ALL_STRESSORS


### CARBON FOOTPRINT ###


def plot_footprint(
    model,
    region: str = "FR",
    counterfactual_name: str = None,
    stressors_to_display: str = None,
    title: str = None,
) -> None:
    """Plots region's footprint (D_pba-D_exp+D_imp+F_Y)

    Args:
        model (Model): object Model defined in model.py
        region (str, optional): region name. Defaults to "FR".
        counterfactual_name (str, optional): name of the counterfactual in model.counterfactuals. None for the reference. Defaults to None.
        title (Optional[str], optional): title of the figure. Defaults to None.
    """
    if counterfactual_name is None:
        counterfactual = model
    else:
        counterfactual = model.counterfactuals[counterfactual_name]

    carbon_footprint = pd.DataFrame(
        footprint_extractor(model=counterfactual, region=region, stressor_list=STRESSORS_DICT_DEF[stressors_to_display]['dict']), index=[""]
    )

    carbon_footprint.plot.barh(stacked=True, fontsize=17, figsize=(10, 5), rot=0)

    if title is None:
        title = f"Empreinte en {stressors_to_display} de la région {region}"
    plt.title(title, size=17, fontweight="bold")
    plt.xlabel(find_stressor_unit(stressors_to_display), size=15)
    plt.grid(visible=True)
    plt.legend(prop={"size": 15})
    plt.text(
        0.13,
        -0.2,
        build_description(model=model, counterfactual_name=counterfactual_name),
        transform=plt.gcf().transFigure,
    )
    # plt.axis([-200000, 5E6,-0.5,0.5])
    if model.save_figures:
        plt.savefig(counterfactual.figures_dir / f"empreinte_{region}.png")


def plot_footprint_FR(
    model,
    counterfactual_name: str = None,
    stressors_to_display: str = None
) -> None:
    """Plots french footprint (D_pba-D_exp+D_imp+F_Y)

    Args:
        model (Model): object Model defined in model.py
        counterfactual_name (str, optional): name of the counterfactual in model.counterfactuals. None for the reference. Defaults to None.
        stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
    """
    plot_footprint(
        model=model,
        region="FR",
        counterfactual_name=counterfactual_name,
        stressors_to_display=stressors_to_display,
        title=f"Empreinte en {stressors_to_display} de la France"
    )


### STRESSORS CONTENT DESCRIPTION ###


def plot_stressor_content_heatmap(
    model,
    counterfactual_name: str = None,
    stressors_to_display: str = None,
    prod: bool = False,
) -> None:
    """Plots the content in chosen stressor(s) of each sector for each region in a heatmap

    Args:
        model (Model): object Model defined in model.py
        counterfactual_name (str, optional): name of the counterfactual in model.counterfactuals. None for the reference. Defaults to None.
        stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
        prod (bool, optional): True to focus on production values, otherwise focus on consumption values. Defaults to False.
    """
    if counterfactual_name is None:
        counterfactual = model
    else:
        counterfactual = model.counterfactuals[counterfactual_name]
    sectors = model.agg_sectors
    regions = model.agg_regions
    if prod:
        title = f"Intensité de la production en {stressors_to_display}"
        activity = "production"
        S = counterfactual.iot.stressor_extension.S.loc[STRESSORS_DICT_DEF[stressors_to_display]['dict']].sum()
        x = counterfactual.iot.x["indout"]
        S_pond = S.multiply(x)
        S_pond_agg = aggregate_sum_axis(
            df=S_pond,
            axis=0,
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )
        x_agg = aggregate_sum_axis(
            df=x,
            axis=0,
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )
        S_mean_pond_agg = (
            S_pond_agg.div(x_agg).replace([-np.inf, np.inf], np.NaN).fillna(0)
        )
        to_display = S_mean_pond_agg.unstack().T
    else:
        title = f"Contenu du bien importé en {stressors_to_display}"
        activity = "consumption"
        M = counterfactual.iot.stressor_extension.M.loc[STRESSORS_DICT_DEF[stressors_to_display]['dict']].sum()
        y = counterfactual.iot.Y.sum(axis=1)
        M_pond = M.multiply(y)
        M_pond_agg = aggregate_sum_axis(
            df=M_pond,
            axis=0,
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )
        y_agg = aggregate_sum_axis(
            df=y,
            axis=0,
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )
        M_mean_pond_agg = (
            M_pond_agg.div(y_agg).replace([-np.inf, np.inf], np.NaN).fillna(0)
        )
        to_display = M_mean_pond_agg.unstack().T
    to_display = to_display.reindex(sectors)[regions]  # sort rows and columns
    to_display = 100 * to_display.div(
        to_display.max(axis=1), axis=0
    )  # compute relative values
    fig, ax = plt.subplots(figsize=(8, 8))
    sns.heatmap(
        to_display,
        cmap="coolwarm",
        ax=ax,
        linewidths=1,
        linecolor="black",
        cbar_kws={"format": "%.0f%%"},
    ).set_title(title, size=13, fontweight="bold")
    plt.yticks(size=11)
    plt.xticks(size=11)
    ax.set_xlabel(None)
    ax.set_ylabel(None)
    fig.tight_layout()
    plt.text(
        0.13,
        -0.2,
        build_description(model=model, counterfactual_name=counterfactual_name),
        transform=plt.gcf().transFigure,
    )
    if model.save_figures:
        plt.savefig(counterfactual.figures_dir / ("content_heatmap_" + activity))


def plot_stressor_content_production(model, counterfactual_name: str = None, stressors_to_display: str = None) -> None:
    """Compares the content in chosen stressor(s) of each region for each sector

    Args:
        model (Model): object Model defined in model.py
        stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
        counterfactual_name (str, optional): name of the counterfactual in model.counterfactuals. None for the reference. Defaults to None.
    """
    if counterfactual_name is None:
        counterfactual = model
    else:
        counterfactual = model.counterfactuals[counterfactual_name]

    S_unstacked = (counterfactual.iot.stressor_extension.S.loc[STRESSORS_DICT_DEF[stressors_to_display]['dict']]).sum().unstack().T

    S_unstacked = aggregate_avg_simple_index(
        df=S_unstacked,
        axis=0,
        new_index=model.agg_sectors,
        reverse_mapper=model.rev_sectors_mapper,
    )
    S_unstacked = aggregate_avg_simple_index(
        df=S_unstacked,
        axis=1,
        new_index=model.agg_regions,
        reverse_mapper=model.rev_regions_mapper,
    )

    S_unstacked.plot.barh(fontsize=17, figsize=(12, 8), color=COLORS)
    plt.title(
        f"Contenu de la production en {stressors_to_display}",
        size=17,
        fontweight="bold",
    )
    plt.xlabel(f"{find_stressor_unit(stressors_to_display)} / M€", size=15)
    plt.tight_layout()
    plt.grid(visible=True)
    plt.legend(prop={"size": 15})
    plt.text(
        0.13,
        -0.2,
        build_description(model=model, counterfactual_name=counterfactual_name),
        transform=plt.gcf().transFigure,
    )
    if model.save_figures:
        plt.savefig(counterfactual.figures_dir / "content_hbar_production.png")


### SCENARIO COMPARISON ###


def compare_scenarios(
    model,
    verbose: bool = False,
) -> None:
    """Plots the footprints and the imports associated with the different counterfactuals

    Args:
        model (Model): object Model defined in model.py
        verbose (bool, optional): True to print infos. Defaults to False.
    """

    if verbose:
        print("Comparing scenarios...")

    regions = model.agg_regions

    situations = model.counterfactuals
    situations["reference"] = model
    situations_names = list(situations.keys())

    stressor_all_scen = pd.DataFrame(
        0.0,
        index=regions,
        columns=situations_names,
    )
    trade_all_scen = pd.DataFrame(
        0.0,
        index=regions,
        columns=situations_names,
    )

    for name, situation in situations.items():

        if verbose:
            print(f"Processing {name}")

        D_cba = aggregate_sum_2levels_on_axis1_level0_on_axis0(
            df=situation.iot.stressor_extension.D_cba,
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )
        F_Y = aggregate_sum(
            df=situation.iot.stressor_extension.F_Y,
            level=0,
            axis=1,
            new_index=model.new_regions_index,
            reverse_mapper=model.rev_regions_mapper,
        )
        Y = aggregate_sum_level0_on_axis1_2levels_on_axis0(
            df=situation.iot.Y,
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )
        Z = aggregate_sum_2levels_2axes(
            df=situation.iot.Z,
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )

        for reg in regions:
            stressor_all_scen.loc[reg, name] = (D_cba["FR"].sum(axis=1)).sum(level=0)[
                reg
            ]
        stressor_all_scen.loc["FR", name] += F_Y["FR"].sum().sum()
        for reg in regions:
            trade_all_scen.loc[reg, name] = (
                Y["FR"].sum(axis=1) + Z["FR"].sum(axis=1)
            ).sum(level=0)[reg]

        return trade_all_scen

    if verbose:
        print("\n\n\nFrench stressors imports\n")
        print(stressor_all_scen)
        print("\n\n\nFrench imports\n")
        print(trade_all_scen)
        print("\n")

    stressor_all_scen.T.plot.bar(
        stacked=True,
        fontsize=17,
        figsize=(12, 8),
        rot=0,
        color=COLORS[: len(regions)],
    )
    plt.title(
        f"Empreinte de la France en {model.stressor_name}", size=17, fontweight="bold"
    )
    plt.ylabel(model.stressor_unit, size=15)
    plt.tight_layout()
    plt.grid(visible=True)
    plt.legend(prop={"size": 15})
    plt.text(
        0.13,
        -0.2,
        build_description(model=model, counterfactual_name=False),
        transform=plt.gcf().transFigure,
    )
    plt.savefig(model.figures_dir / "compare_scenarios_stressors.png")

    trade_all_scen.T.plot.bar(
        stacked=True,
        fontsize=17,
        figsize=(12, 8),
        rot=0,
        color=COLORS[: len(regions)],
    )
    plt.title("Provenance de la consommation de la France", size=17, fontweight="bold")
    plt.ylabel("M€", size=15)
    plt.tight_layout()
    plt.grid(visible=True)
    plt.legend(prop={"size": 15})
    plt.text(
        0.13,
        -0.2,
        build_description(model=model, counterfactual_name=False),
        transform=plt.gcf().transFigure,
    )
    plt.savefig(model.figures_dir / "compare_scenarios_trade.png")

    stressor_all_scen.drop("FR").T.plot.bar(
        stacked=True,
        fontsize=17,
        figsize=(12, 8),
        rot=0,
        color=COLORS_NO_FR[: len(regions)],
    )
    plt.title(
        f"Importations de {model.stressor_name} par la France",
        size=17,
        fontweight="bold",
    )
    plt.legend(prop={"size": 15})
    plt.tick_params(axis="x", rotation=45)
    plt.ylabel(model.stressor_unit, size=15)
    plt.tight_layout()
    plt.text(
        0.13,
        -0.2,
        build_description(model=model, counterfactual_name=False),
        transform=plt.gcf().transFigure,
    )
    plt.savefig(model.figures_dir / "compare_scenarios_stressors.png")

    trade_all_scen.drop("FR").T.plot.bar(
        stacked=True,
        fontsize=17,
        figsize=(12, 8),
        rot=0,
        legend=False,
        color=COLORS_NO_FR[: len(regions)],
    )
    plt.title("Importations françaises", size=17)
    plt.tick_params(axis="x", rotation=45)
    plt.ylabel("M€", size=15)
    plt.legend(prop={"size": 15})
    plt.text(
        0.13,
        -0.2,
        build_description(model=model, counterfactual_name=False),
        transform=plt.gcf().transFigure,
    )
    plt.tight_layout()
    plt.savefig(model.figures_dir / "compare_scenarios_imports.png")


### SPECIFIC SYNTHESES ###


def plot_df_synthesis(
    reference_df: pd.Series,
    counterfactual_df: pd.Series,
    account_name: str,
    account_description: str,
    account_unit: str,
    scenario_name: str,
    output_dir: pathlib.PosixPath,
    description: str,
    save_figures: bool,
    stressors_to_plot: str,
    plot_method: str,
) -> None:
    """Plots some figures for a given counterfactual

    Args:
        reference_df (pd.DataFrame): series with rows multiindexed by (region, sector) associated to the reference
        couterfactual_df (pd.DataFrame): series with rows multiindexed by (region, sector) associated to the counterfactual
        account_name (str): name of the account considered in french, for display purpose (eg: "importations françaises", "empreinte carbone française")
        account_unit (str): account unit for display purpose (must be the same in both dataframes)
        scenario_name(str): name of the scenario (used to save the figures)
        output_dir (pathlib.PosixPath): where to save the figure
        description (str): general settings description to display at the bottom
    """

    regions = list(
        reference_df.index.get_level_values(level=0).drop_duplicates()
    )  # doesn't use .get_regions() to deal with partial reaggregation
    sectors = list(
        reference_df.index.get_level_values(level=1).drop_duplicates()
    )  # same with .get_sectors()

    # account_name = (
    #     account_name[0].upper() + account_name[1:]
    # )  # doesn't use .capitalize() in order to preserve capital letters in the middle
    # account_name_file = unidecode(account_name.lower().replace(" ", "_"))
    # current_dir = output_dir / (scenario_name + "__" + account_name_file)
    current_dir = output_dir / (scenario_name + "__" + account_name)

    # if not os.path.isdir(current_dir):
    #     os.mkdir(current_dir)  # can overwrite existing files
    current_dir.mkdir(exist_ok = True, parents = True)

    # preliminary aggregation
    ref_conso_by_sector_FR = reference_df
    # ref_impacts_by_region_FR = ref_conso_by_sector_FR.drop("FR", level=0).sum(level=0)
    ref_impacts_by_region_FR = reference_df.sum(level=0)

    scen_conso_by_sector_FR = counterfactual_df
    # scen_impacts_by_region_FR = scen_conso_by_sector_FR.drop("FR", level=0).sum(level=0)
    scen_impacts_by_region_FR = scen_conso_by_sector_FR.sum(level=0)

    # xmax = max(max(reference_df), max(counterfactual_df.values))*1.2
    xmax = max(max(ref_impacts_by_region_FR), max(scen_impacts_by_region_FR.values))*1.2
    
    
    # # plot reference impacts
    # ref_impacts_by_region_FR.T.plot.barh(
    #     stacked=True, fontsize=17, color=COLORS, figsize=(12, 5)
    # )
    # plt.title(f"{account_description} (référence)", size=17, fontweight="bold")
    # plt.xlabel(account_unit, size=15)
    # plt.tight_layout()
    # plt.grid(visible=True)
    # plt.text(
    #     0.13,
    #     -0.2,
    #     description,
    #     transform=plt.gcf().transFigure,
    # )
    # plt.axis([0,xmax, -1, len(regions)])
    # plt.savefig(current_dir / f"{account_name}_reference.png")
    # plt.close()

    # # plot counterfactual impacts
    # scen_impacts_by_region_FR.T.plot.barh(
    #     stacked=True, fontsize=17, color=COLORS, figsize=(12, 5)
    # )
    # plt.title(
    #     f"{account_description} (scénario {scenario_name})",
    #     size=17,
    #     fontweight="bold",
    # )
    # plt.xlabel(account_unit, size=15)
    # plt.tight_layout()
    # plt.grid(visible=True)
    # plt.text(
    #     0.13,
    #     -0.2,
    #     description,
    #     transform=plt.gcf().transFigure,
    # )
    # plt.axis([0,xmax,-1, len(regions)])
    # # ax.set(xlim=(0,xmax))
    # plt.savefig(current_dir / f"{account_name}_{scenario_name}.png")

    # compare counterfactual and reference impacts
    compare_impacts_by_region_FR = pd.DataFrame(
        {
            "Référence": ref_impacts_by_region_FR,
            f"Scénario {scenario_name}": scen_impacts_by_region_FR,
        }
    )
    compare_impacts_by_region_FR.T.plot.barh(
        stacked=True, fontsize=17, figsize=(12, 8), color=COLORS
    )
    plt.title(f"{account_description} (total)", size=17, fontweight="bold")
    plt.xlabel(account_unit, size=15)
    plt.tight_layout()
    plt.grid(visible=True)
    plt.legend(prop={"size": 12}, bbox_to_anchor = (1,0.75))
    plt.text(
        0.13,
        -0.1,
        description,
        transform=plt.gcf().transFigure,
    )
    if save_figures:
        plt.savefig(current_dir / f"{account_name}_{stressors_to_plot}_total.png",  bbox_inches='tight')

    # compare each region for each sector for the reference and the counterfactual

    def grouped_and_stacked_plot(
        df_ref: pd.DataFrame,
        df_scen: pd.DataFrame,
        percent_x_scale: bool,
        plot_title: str,
        plot_filename: str,
        save_figures: bool,
    ) -> None:
        """Nested function. Plots a grouped stacked horizontal bar plot.

        Args:
            df_ref (pd.DataFrame): series with rows multiindexed by (region, sector) associated to the reference
            df_scen (pd.DataFrame): series with rows multiindexed by (region, sector) associated to the counterfactual
            percent_scale (bool): True if the x_axis should be labelled with percents (otherwise labelled with values)
            plot_title (str): title of the figure, in french for display purpose
            plot_filename (str): to save the figure
        """
        df_to_display = pd.DataFrame(
            columns=regions[0:],
            index=pd.MultiIndex.from_arrays(
                [
                    sum([2 * [sec] for sec in sectors], []),
                    len(sectors) * ["Référence", f"Scénario {scenario_name}"],
                ],
                names=("sector", "scenario"),
            ),
        )
        for sec in sectors:
            df_to_display.loc[(sec, "Référence"), :] = df_ref.loc[(slice(None), sec)]
            df_to_display.loc[(sec, f"Scénario {scenario_name}"), :] = df_scen.loc[
                (slice(None), sec)
            ]
        fig, axes = plt.subplots(
            nrows=len(sectors), ncols=1, sharex=True, figsize=(10, 10)
        )
        graph = dict(zip(df_to_display.index.levels[0], axes))
        for ax in axes:
            ax.yaxis.tick_right()
            ax.tick_params(axis="y", which="both", rotation=0)
            if percent_x_scale:
                ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0))
        list(
            map(
                lambda x: df_to_display.xs(x)
                .plot(
                    kind="barh",
                    stacked="True",
                    ax=graph[x],
                    legend=False,
                    color=COLORS,
                )
                .set_ylabel(
                    x,
                    rotation=0,
                    size=15,
                    horizontalalignment="right",
                    verticalalignment="center",
                ),
                graph,
            )
        )
        fig.subplots_adjust(wspace=0)
        fig.suptitle(plot_title, size=17, fontweight="bold")
        plt.tight_layout()
        if not percent_x_scale:
            plt.xlabel(account_unit, size=15)
        else:
            plt.xlabel(f'% of total {plot_method.replace("by_", "per ")}', size=15)
        #plt.legend(ncol=3, loc="lower left", bbox_to_anchor=(-0.35, -4.5))
        plt.legend(ncol=3, loc="lower left", bbox_to_anchor=(0.5 if plot_method=='by_products' else 0.5, -5 if plot_method=='by_products' else -2))

        plt.text(
            0.05 if plot_method=='by_products' else 0.13,
            -0.15 if plot_method=='by_products' else -0.15,
            description,
            transform=plt.gcf().transFigure,
        )
        if save_figures:
            plt.savefig(current_dir / plot_filename, bbox_inches='tight')
        plt.show()

    try:
        df_ref_parts = (
            (
                ref_conso_by_sector_FR.divide(ref_conso_by_sector_FR.sum(level=1), level=1)
            )
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )
        df_scen_parts = (
            (
                scen_conso_by_sector_FR.divide(scen_conso_by_sector_FR.sum(level=1), level=1)
            )
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )
        grouped_and_stacked_plot(
            df_ref_parts,
            df_scen_parts,
            True,
            f"{account_description}",
            f"{account_name}_{stressors_to_plot}_{plot_method}_in_relative.png",
            save_figures
        )
    except ValueError:
        pass  # ignore substressors plot, may be improved

    df_ref_values = (
        ref_conso_by_sector_FR
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )
    df_scen_values = (
        scen_conso_by_sector_FR
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )
    grouped_and_stacked_plot(
        df_ref_values,
        df_scen_values,
        False,
        f"{account_description}",
        f"{account_name}_{stressors_to_plot}_{plot_method}_in_absolute.png",
        save_figures
    )


def plot_trade_synthesis(
    model,
    counterfactual_name: str,
) -> None:
    """Plots the french importations for a given counterfactual

    Args:
        model (Model): object Model defined in model.py
        counterfactual_name (str): name of the counterfactual in model.counterfactuals
    """
    counterfactual = model.counterfactuals[counterfactual_name]

    ref_Y = aggregate_sum_level0_on_axis1_2levels_on_axis0(
        df=model.iot.Y,
        new_index_0=model.new_regions_index,
        new_index_1=model.new_sectors_index,
        reverse_mapper_0=model.rev_regions_mapper,
        reverse_mapper_1=model.rev_sectors_mapper,
    )
    ref_Z = aggregate_sum_2levels_2axes(
        df=model.iot.Z,
        new_index_0=model.new_regions_index,
        new_index_1=model.new_sectors_index,
        reverse_mapper_0=model.rev_regions_mapper,
        reverse_mapper_1=model.rev_sectors_mapper,
    )
    count_Y = aggregate_sum_level0_on_axis1_2levels_on_axis0(
        df=counterfactual.iot.Y,
        new_index_0=model.new_regions_index,
        new_index_1=model.new_sectors_index,
        reverse_mapper_0=model.rev_regions_mapper,
        reverse_mapper_1=model.rev_sectors_mapper,
    )
    count_Z = aggregate_sum_2levels_2axes(
        df=counterfactual.iot.Z,
        new_index_0=model.new_regions_index,
        new_index_1=model.new_sectors_index,
        reverse_mapper_0=model.rev_regions_mapper,
        reverse_mapper_1=model.rev_sectors_mapper,
    )

    reference_trade = ref_Y["FR"].sum(axis=1) + ref_Z["FR"].sum(axis=1)
    counterfactual_trade = count_Y["FR"].sum(axis=1) + count_Z["FR"].sum(axis=1)
    
    reference_trade.drop('FR', axis=0, level=0, inplace=True)
    counterfactual_trade.drop('FR', axis=0, level=0, inplace=True)
    
    plot_df_synthesis(
        reference_df=reference_trade,
        counterfactual_df=counterfactual_trade,
        account_name="trade",
        account_description="importations françaises",
        account_unit="M€",
        scenario_name=counterfactual_name,
        output_dir=counterfactual.figures_dir,
        description=build_description(
            model=model, counterfactual_name=counterfactual_name
        ),
        save_figures=model.save_figures,
        stressors_to_plot='',
        plot_method='by_products'
    )


def plot_stressor_synthesis(
    model,
    counterfactual_name: str,
    stressors_to_display: str,
) -> None:
    """Plots the french emissions of stressors by sector for a given counterfactual

    Args:
        model (Model): object Model defined in model.py
        counterfactual_name (str): name of the counterfactual in model.counterfactuals
        stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
    """
    counterfactual = model.counterfactuals[counterfactual_name]

    stressors_to_plot = STRESSORS_DICT_DEF[stressors_to_display]["name_EN"]

    emissions_types = {
        "D_cba": f"empreinte de la France en {stressors_to_display}",
        "D_pba": f"impact territorial de la France en {stressors_to_display}",
        "D_imp": f"empreinte importée par la France en {stressors_to_display}",
        "D_exp": f"impact exporté par la France en {stressors_to_display}",
    }

    for name, description in emissions_types.items():

        ref_df = aggregate_sum_2levels_on_axis1_level0_on_axis0(
            df=getattr(model.iot.stressor_extension, name),
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )
        count_df = aggregate_sum_2levels_on_axis1_level0_on_axis0(
            df=getattr(counterfactual.iot.stressor_extension, name),
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )

        reference_trade = ref_df["FR"].swaplevel(0,1, axis=0).loc[STRESSORS_DICT_DEF[stressors_to_display]['dict']].swaplevel(0,1, axis = 0).sum(level=0).stack()
        counterfactual_trade = count_df["FR"].swaplevel(0,1, axis=0).loc[STRESSORS_DICT_DEF[stressors_to_display]['dict']].swaplevel(0,1, axis = 0).sum(level=0).stack()

        plot_df_synthesis(
            reference_df=reference_trade,
            counterfactual_df=counterfactual_trade,
            account_name=name,
            account_description=description,
            account_unit=find_stressor_unit(stressors_to_display),
            scenario_name=counterfactual_name,
            output_dir=counterfactual.figures_dir,
            description=build_description(
                model=model, counterfactual_name=counterfactual_name
            ),
            save_figures=model.save_figures,
            stressors_to_plot=stressors_to_plot,
            plot_method='by_products'
        )


def plot_substressor_synthesis(
    model,
    counterfactual_name: str,
    stressors_to_display: str,
) -> None:
    """Plots the french emissions per substressor for a given counterfactual

    Args:
        model (Model): object Model defined in model.py
        counterfactual_name (str): name of the counterfactual in model.counterfactuals
        stressors_to_display (str, mandatory): name of the stressors to plot, to be defined in variable STRESSORS_DICT_DEF in stressors.py.
    """
    counterfactual = model.counterfactuals[counterfactual_name]
    
    stressors_to_plot = STRESSORS_DICT_DEF[stressors_to_display]["name_EN"]
    
    emissions_types = {
        "D_cba": f"empreinte de la France en {stressors_to_display}",
        # "D_pba": f"impact territorial de la France en {stressors_to_display}",
        # "D_imp": f"empreinte importée par la France en {stressors_to_display}",
        # "D_exp": f"impact exporté par la France en {stressors_to_display}",
    }

    for name, description in emissions_types.items():

        ref_df = aggregate_sum_2levels_on_axis1_level0_on_axis0(
            df=getattr(model.iot.stressor_extension, name),
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )
        count_df = aggregate_sum_2levels_on_axis1_level0_on_axis0(
            df=getattr(counterfactual.iot.stressor_extension, name),
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )

        reference_stressor = ref_df["FR"].swaplevel(0,1, axis=0).loc[STRESSORS_DICT_DEF[stressors_to_display]['dict']].swaplevel(0,1, axis = 0).sum(axis=1)
        counterfactual_stressor = count_df["FR"].swaplevel(0,1, axis=0).loc[STRESSORS_DICT_DEF[stressors_to_display]['dict']].swaplevel(0,1, axis = 0).sum(axis=1)

        plot_df_synthesis(
            reference_df=reference_stressor,
            counterfactual_df=counterfactual_stressor,
            account_name=name,
            account_description=description,
            account_unit=find_stressor_unit(stressors_to_display),
            scenario_name=counterfactual_name,
            output_dir=counterfactual.figures_dir,
            description=build_description(
                model=model, counterfactual_name=counterfactual_name
            ),
            save_figures=model.save_figures,
            stressors_to_plot=stressors_to_plot,
            plot_method='by_stressors'
        )

def plot_stressor_synthesis_k_comp(
    model,
    model_k,
) -> None:
    """Plots the french emissions of stressors by sector for a given counterfactual

    Args:
        model (Model): object Model defined in model.py
        model_k (Model): object Model defined in model.py
    """
    if model.stressor_name == 'GES':
        emissions_types = {
            "D_cba": f"empreinte de la France en {model.stressor_name}",
            "D_pba": f"émissions territoriales de la France en {model.stressor_name}",
            "D_imp": f"émissions importées par la France en {model.stressor_name}",
            "D_exp": f"émissions exportées par la France en {model.stressor_name}",
        }
    else:
        emissions_types = {
            "D_cba": f"empreinte de la France en {model.stressor_name}",
            "D_pba": f"impact territorial de la France en {model.stressor_name}",
            "D_imp": f"impact importé par la France en {model.stressor_name}",
            "D_exp": f"impact exporté par la France en {model.stressor_name}",
        }
    
    for name, description in emissions_types.items():

        ref_df = aggregate_sum_2levels_on_axis1_level0_on_axis0(
            df=getattr(model.iot.stressor_extension, name),
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )
        ref_k_df = aggregate_sum_2levels_on_axis1_level0_on_axis0(
            df=getattr(model_k.iot.stressor_extension, name),
            new_index_0=model.new_regions_index,
            new_index_1=model.new_sectors_index,
            reverse_mapper_0=model.rev_regions_mapper,
            reverse_mapper_1=model.rev_sectors_mapper,
        )

        reference_trade = ref_df["FR"].sum(level=0).stack()
        reference_k_trade = ref_k_df["FR"].sum(level=0).stack()

        plot_df_synthesis(
            reference_df=reference_trade,
            counterfactual_df=reference_k_trade,
            account_name=name,
            account_description=description,
            account_unit=model.stressor_unit,
            scenario_name='endo_capital',
            output_dir=(model_k.figures_dir)/'comparaison_k',
            description=build_description(
                model=model, counterfactual_name=None
            ),
        )
        
        
        
def plot_sector_import_distrib(iot : pymrio.IOSystem,sectors: list,country_importing="FR",normalized_quantity=True):
    """" (function description)
    
    Args:
        variable1 (type):
        
    """
    
    emissiv_df=get_emmissiv_and_quantity(iot,country_importing)

    sector_needed_emssiv=emissiv_df.loc[emissiv_df.index.get_level_values("sector").isin(sectors)].reset_index()

    sector_needed_emssiv=sector_needed_emssiv.drop(index=sector_needed_emssiv.loc[sector_needed_emssiv["quantity"]==0].index)

    if normalized_quantity:
        ecdf_norm="percent"
    else :
        ecdf_norm=None

    fig=px.ecdf(sector_needed_emssiv,x="emissivity",color="sector",y="quantity",
                log_x=True,
                ecdfnorm=ecdf_norm,
                hover_name="region",
                hover_data=["emissivity","quantity"])

    fig.show()


def plot_sector_import_distrib_full(model ,sectors: list,country_importing="FR",normalized_quantity=True,scenarios=None,stressors_to_display: str='GES',scope=3):
    """" Plots the distribution of tradded quantities per regions of selected products regarding emissivity.

    Args:
        variable1 (type):variable description
    """
    
    stressor_list = STRESSORS_DICT_DEF[stressors_to_display]['dict']

    # choose to normalize or not total quantitty produced in the graph
    if normalized_quantity:
        ecdf_norm="percent"
    else :
        ecdf_norm=None
        
    dict_df_to_print={}
    
    dict_df_to_print["base"]=get_emmissiv_and_quantity(model.iot,country_importing,stressor_list=stressor_list,scope=scope)

    for counterfactual in model.get_counterfactuals_list():
        dict_df_to_print[counterfactual]=get_emmissiv_and_quantity(model.counterfactuals[counterfactual].iot,country_importing,stressor_list=stressor_list,scope=scope)
    
    if scenarios is None : 
        scenarios=dict_df_to_print.keys()
    df_to_print=pd.concat([dict_df_to_print[scenario] for scenario in scenarios],keys=scenarios,names=("scenario","region","sector"))
    
    sector_needed_emssiv=df_to_print.loc[df_to_print.index.get_level_values("sector").isin(sectors)].reset_index()

    sector_needed_emssiv=sector_needed_emssiv.drop(index=sector_needed_emssiv.loc[sector_needed_emssiv["quantity"]==0].index)

    fig=px.ecdf(sector_needed_emssiv,x="emissivity",color="sector",y="quantity",
                log_x=True,
                ecdfnorm=ecdf_norm,
                hover_name="region",
                hover_data=["emissivity"],
                animation_frame="scenario")

    fig.show()


def get_emmissiv_and_quantity(iot,country : str ,stressor_list: list=GHG_STRESSOR_NAMES,scope=3):
    if scope ==1:
        emissiv_df=pd.DataFrame([iot.stressor_extension.S.loc[stressor_list].sum(),get_total_imports_region(iot,country, scope=scope)],index=["emissivity","quantity"]).T
        # emissiv_df=pd.DataFrame([iot.stressor_extension.S.loc[stressor_list].sum(),iot.Y[region].sum(axis = 1)[region]=0]],index=["emissivity","quantity"]).T
    else :
        emissiv_df=pd.DataFrame([iot.stressor_extension.M.loc[stressor_list].sum(),get_total_imports_region(iot,country, scope=scope)],index=["emissivity","quantity"]).T
        # emissiv_df=pd.DataFrame([iot.stressor_extension.M.loc[stressor_list].sum(),get_total_imports_region(iot,country, scope=scope)],index=["emissivity","quantity"]).T
    return emissiv_df


def get_emissions_and_quantity(iot,country : str ,stressor_list: list=GHG_STRESSOR_NAMES,scope=3):
    emissions_and_quantity=get_emmissiv_and_quantity(iot,country=country,stressor_list=stressor_list,scope=scope)
    emissions_and_quantity.loc[country]=0
    emissions_and_quantity["emissions"]=emissions_and_quantity["emissivity"]*emissions_and_quantity["quantity"]
    return emissions_and_quantity.drop("emissivity",axis=1)


def plot_emission_location_import_distrib_full(model ,sectors: list,country_importing="FR",normalized_quantity=True,scenarios=None,stressors_to_display: str='GES',scope=3):
    """" Plots the distribution of tradded quantities per regions of selected products regarding emissivity.

    Args:
        variable1 (type):variable description
    """
    
    stressor_list = STRESSORS_DICT_DEF[stressors_to_display]['dict']

    # choose to normalize or not total quantitty produced in the graph
    if normalized_quantity:
        ecdf_norm="percent"
    else :
        ecdf_norm=None
        
    dict_df_to_print={}

    dict_df_to_print["base"]=get_local_emissions_and_quantity(model.iot,country_importing=country_importing,stressor_list=stressor_list)

    for counterfactual in model.get_counterfactuals_list():
        dict_df_to_print[counterfactual]=get_local_emissions_and_quantity(model.counterfactuals[counterfactual].iot,country_importing=country_importing,stressor_list=stressor_list)
    
    if scenarios is None : 
        scenarios=dict_df_to_print.keys()
    df_to_print=pd.concat([dict_df_to_print[scenario] for scenario in scenarios],keys=scenarios,names=("scenario","region","sector"))
    
    sector_needed_emssiv=df_to_print.loc[df_to_print.index.get_level_values("sector").isin(sectors)].reset_index()

    sector_needed_emssiv=sector_needed_emssiv.drop(index=sector_needed_emssiv.loc[sector_needed_emssiv["quantity"]==0].index)

    fig=px.ecdf(sector_needed_emssiv,x="emissivity",color="sector",y="quantity",
                ecdfnorm=ecdf_norm,
                hover_name="region",
                hover_data=["emissivity"],
                animation_frame="scenario")

    fig.show()


def get_local_emissions_and_quantity(iot, country_importing : str, stressor_list: list=GHG_STRESSOR_NAMES):
    imports=iot.Y.sum(axis=1,level=0)*0
    country_imports=get_total_imports_region(iot,country_importing, scope=3)
    imports[country_importing]=country_imports
    imports_total_diag=diagonalize_columns_to_sectors(imports)[country_importing]
    prod_imports_diag=iot.L@imports_total_diag
    
    prod_imports_diag.loc[country_importing, country_importing]=0
    
    local_emissions=get_very_detailed_emissions(iot,stressors_groups={"extensions":stressor_list},production_diag=prod_imports_diag).loc[(slice(None),slice(None),"extensions")].sum(axis=0,level=0)
    local_emissions=pd.DataFrame(local_emissions.to_numpy().flatten(),index=pd.MultiIndex.from_product([local_emissions.index,local_emissions.columns]))[0]

    return pd.DataFrame([local_emissions,local_emissions],index=["emissivity","quantity"]).T



def plot_impacts_by_location_for_one_product(
        model,
        sector: str,
        country_importing="FR",
        scenarios=None,
        stressors_to_display: str='GES',
        ):
    """" Plots imported impacts by location of impacts. 
        Impacts occuring along the entire value chain are attributed to the region(s) where there actually happened.
    
    Args:
        model (Model): object Model defined in model.py
        sector (str): imported product whose impacts will be displayed 
        country_importing (str): importing country of the above product
        scenarios (list of str): scenarios to display. Default to all existing counterfactuals (cf. model.get_counterfactuals_list()).
        stressors_to_display (str): impacts to display (to be defined in variable STRESSORS_DICT_DEF in stresors.py).
    """
    
    stressor_list = STRESSORS_DICT_DEF[stressors_to_display]['dict']
    stressors_name_EN = STRESSORS_DICT_DEF[stressors_to_display]['name_EN']

    dict_df_to_print={}

    dict_df_to_print["base"]=get_local_emissions_and_quantity(model.iot,country_importing=country_importing,stressor_list=stressor_list)

    if scenarios is None : 
        scenarios_list = model.get_counterfactuals_list()
    else:
        scenarios_list = scenarios.copy()

    for counterfactual in scenarios_list:
        dict_df_to_print[counterfactual]=get_local_emissions_and_quantity(model.counterfactuals[counterfactual].iot,country_importing=country_importing,stressor_list=stressor_list)
    
    scenarios_list = ['base']+scenarios_list

    df_to_print=pd.concat([dict_df_to_print[scenario] for scenario in scenarios_list],keys=scenarios_list,names=("scenario","regions","sector"))
    
    sector_needed_emssiv=df_to_print.loc[df_to_print.index.get_level_values("sector")==sector].reset_index()

    sector_needed_emssiv=sector_needed_emssiv.drop(index=sector_needed_emssiv.loc[sector_needed_emssiv["quantity"]==0].index)

    sector_needed_emssiv['scenario'] = pd.Categorical(sector_needed_emssiv.scenario, categories = scenarios_list, ordered = True)
    
    fig=px.bar(sector_needed_emssiv.sort_values(by="scenario",kind="stable"),y="emissivity",color="regions",x="scenario",
                hover_name="regions",color_discrete_map=dict(zip(model.regions, COLORS[:len(model.regions)])))
    #.sort_values(ascending=False,by="emissivity",axis=0)
    
    fig.update_layout(
                title = f"Localisation des impacts importés par {country_importing} ({sector})",
                xaxis_title = "Scenarios",
                yaxis_title = f'{stressors_to_display}, en {find_stressor_unit(stressors_to_display)}'
                )
    
    fig.show()
    
    if model.save_figures:
        save_dir = model.figures_dir / ("Impacts_by_location_for_"+country_importing)/stressors_name_EN
        save_dir.mkdir(exist_ok = True, parents = True)
        fig.write_image(save_dir/f"{stressors_name_EN}_total_imports_imported_footprint_by_location_for_{sector}.png")


def get_Dimp_extensions_for_country(
        model,
        country_importing, 
        # sector, 
        stressor_list
        ):
    
    Dimp_extensions = model.iot.stressor_extension.D_imp[country_importing]
    # Dimp_extensions = model.iot.stressor_extension.D_imp[(country_importing, sector)]
    # Dimp_extensions = model.iot.stressor_extension.D_imp.xs(sector, level = 1, axis = 1)

    Dimp_extensions = pd.concat(
        [Dimp_extensions.loc[region].loc[stressor_list] for region in model.regions],
        axis = 0,
        keys= model.regions
        )
    
    Dimp_extensions = Dimp_extensions.groupby(level=0, axis=0, sort=False).sum()

    # Dimp_extensions = pd.concat(
    #     [Dimp_extensions.xs(extension, level = 1, axis = 0) for extension in stressor_list],
    #     axis = 0,
    #     keys = stressor_list
    #     )
    
    return Dimp_extensions



def plot_impacts_by_location_for_one_product_FD(
        model,
        sector: str,
        country_importing="FR",
        scenarios=None,
        stressors_to_display: str='GES',
        ):
    """" Plots imported impacts by location of impacts. 
        Impacts occuring along the entire value chain are attributed to the region(s) where there actually happened.
    
    Args:
        model (Model): object Model defined in model.py
        sector (str): final demand product whose imported impacts will be displayed 
        country_importing (str): importing country of the above product
        scenarios (list of str): scenarios to display. Default to all existing counterfactuals (cf. model.get_counterfactuals_list()).
        stressors_to_display (str): impacts to display (to be defined in variable STRESSORS_DICT_DEF in stresors.py).
    """
    
    stressor_list = STRESSORS_DICT_DEF[stressors_to_display]['dict']
    stressors_name_EN = STRESSORS_DICT_DEF[stressors_to_display]['name_EN']

    dict_df_to_print={}

    dict_df_to_print["base"]= get_Dimp_extensions_for_country(model,country_importing, stressor_list) 


    if scenarios is None : 
        scenarios_list = model.get_counterfactuals_list()
    else:
        scenarios_list = scenarios.copy()

    for counterfactual in scenarios_list:
        dict_df_to_print[counterfactual]=get_Dimp_extensions_for_country(model.counterfactuals[counterfactual],country_importing,stressor_list)
    
    scenarios_list = ['base']+scenarios_list

    df_to_print=pd.concat([dict_df_to_print[scenario] for scenario in scenarios_list],keys=scenarios_list,names=("scenario","regions"))
    
    df_to_print = df_to_print.reset_index()
    
    # sector_needed_emssiv=df_to_print.loc[df_to_print.index.get_level_values("sector")==sector].reset_index()
    # sector_needed_emssiv=sector_needed_emssiv.drop(index=sector_needed_emssiv.loc[sector_needed_emssiv["quantity"]==0].index)
    df_to_print['scenario'] = pd.Categorical(df_to_print.scenario, categories = scenarios_list, ordered = True)

    fig=px.bar(df_to_print.sort_values(by='scenario', kind="stable"),y=sector,color="regions",x="scenario",
                hover_name="regions",color_discrete_map=dict(zip(model.regions, COLORS[:len(model.regions)])))
    #.sort_values(ascending=False,by="emissivity",axis=0)
    
    fig.update_layout(
                title = f"Localisation des impacts importés par {country_importing} ({sector})",
                xaxis_title = "Scenarios",
                yaxis_title = f'{stressors_to_display}, en {find_stressor_unit(stressors_to_display)}'
                )
    
    fig.show()
    
    if model.save_figures:
        save_dir = model.figures_dir / ("Impacts_by_location_for_"+country_importing)/stressors_name_EN
        save_dir.mkdir(exist_ok = True, parents = True)
        fig.write_image(save_dir/f"{stressors_name_EN}_final_demand_imported_footprint_by_location_for_{sector}.png")
    
    
# def plot_impacts_by_exporting_country_for_one_product(
#         model,
#         sector: str,
#         country_importing="FR",
#         scenarios=None,
#         stressors_to_display: str="GES",
#         scope:int=3
#         ):
#     """" Plots imported impacts by origin(s) of the imported good.
#         Impacts occuring along the entire value chain (in case of scope=3) or direct impacts (scope = 1) of the selected product are attributed to last exporter of the product.
    
#     Args:
#         model (Model): object Model defined in model.py
#         sector (str): imported product whose impacts will be displayed 
#         country_importing (str): importing country of the above product
#         scenarios (list of str): scenarios to display. Default to all existing counterfactuals (cf. model.get_counterfactuals_list()).
#         stressors_to_display (str): impacts to display (to be defined in variable STRESSORS_DICT_DEF in stresors.py).
#         scope (int): 1 (direct impacts of production only) or 3 (impacts of the entire value chain).
#     """
    
#     stressor_list = STRESSORS_DICT_DEF[stressors_to_display]['dict']
#     stressors_name_EN = STRESSORS_DICT_DEF[stressors_to_display]['name_EN']
    
#     dict_df_to_print={}

#     dict_df_to_print["base"]=get_emissions_and_quantity(model.iot,country=country_importing,stressor_list=stressor_list, scope=scope)

#     if scenarios is None : 
#         scenarios_list = model.get_counterfactuals_list()
#     else:
#         scenarios_list = scenarios.copy()
    
#     for counterfactual in scenarios_list:
#         dict_df_to_print[counterfactual]=get_emissions_and_quantity(model.counterfactuals[counterfactual].iot,country=country_importing,stressor_list=stressor_list, scope=scope)
    
#     scenarios_list = ['base']+scenarios_list
    
#     df_to_print=pd.concat([dict_df_to_print[scenario] for scenario in scenarios_list],keys=scenarios_list,names=("scenario","regions","sector"))
    
#     sector_needed_emssiv=df_to_print.loc[df_to_print.index.get_level_values("sector")==sector].reset_index()

#     sector_needed_emssiv['scenario'] = pd.Categorical(sector_needed_emssiv.scenario, categories = scenarios_list, ordered = True)
    
#     fig=px.bar(sector_needed_emssiv.sort_values(by="scenario",kind="stable"),y="emissions",color="regions",x="scenario",
#                 hover_name="regions",color_discrete_map=dict(zip(model.regions, COLORS[:len(model.regions)])))
#     #.sort_values(ascending=False,by="emissions",axis=0)

#     if scope==3:
#         title_detail = f"Empreintes importées (scope{str(scope)})"
#     else:
#         title_detail = "Impacts importés (scope{str(scope)})"

#     fig.update_layout(
#                 title = f"{title_detail} par {country_importing} ({sector}) par origine d\'approvisionnement",
#                 xaxis_title = "Scenarios",
#                 yaxis_title = f'{stressors_to_display}, en {find_stressor_unit(stressors_to_display)}'
#                 )

#     fig.show()
    
    
#     if model.save_figures:
#         save_dir = model.figures_dir / ("Impacts_per_exporting_regions_to_"+country_importing)/stressors_name_EN
#         save_dir.mkdir(exist_ok = True, parents = True)
#         fig.write_image(save_dir/(f"{stressors_name_EN}_scope{str(scope)}_impacts_by_exp_reg_for_{sector}.png"))

def get_extensions_by_exporting_for_country(
        model,
        country_importing,
        stressor_list,
        scope:int=3
        ):
    
    if scope==1:
        stressor = model.iot.stressor_extension.S
    if scope==3:
        stressor = model.iot.stressor_extension.M
    
    extensions_by_exporting = stressor * get_total_imports_region(model.iot,region=country_importing, scope=scope)
    extensions_by_exporting=extensions_by_exporting.loc[stressor_list].sum()

    # extensions_by_exporting.name = 'extension'
    extensions_by_exporting = extensions_by_exporting.unstack('sector')
    extensions_by_exporting= extensions_by_exporting.reindex(index=model.regions)
     
    return extensions_by_exporting


def plot_impacts_by_exporting_country_for_one_product_2(
        model,
        sector: str,
        country_importing="FR",
        scenarios=None,
        stressors_to_display: str="GES",
        scope:int=3
        ):
    """" Plots imported impacts by origin(s) of the imported good.
        Impacts occuring along the entire value chain (in case of scope=3) or direct impacts (scope = 1) of the selected product are attributed to last exporter of the product.
    
    Args:
        model (Model): object Model defined in model.py
        sector (str): imported product whose impacts will be displayed 
        country_importing (str): importing country of the above product
        scenarios (list of str): scenarios to display. Default to all existing counterfactuals (cf. model.get_counterfactuals_list()).
        stressors_to_display (str): impacts to display (to be defined in variable STRESSORS_DICT_DEF in stresors.py).
        scope (int): 1 (direct impacts of production only) or 3 (impacts of the entire value chain).
    """
    
    stressor_list = STRESSORS_DICT_DEF[stressors_to_display]['dict']
    stressors_name_EN = STRESSORS_DICT_DEF[stressors_to_display]['name_EN']
    
    dict_df_to_print={}

    dict_df_to_print["base"]=get_extensions_by_exporting_for_country(model,country_importing,stressor_list, scope)

    if scenarios is None : 
        scenarios_list = model.get_counterfactuals_list()
    else:
        scenarios_list = scenarios.copy()
    
    for counterfactual in scenarios_list:
        dict_df_to_print[counterfactual]=get_extensions_by_exporting_for_country(model.counterfactuals[counterfactual],country_importing,stressor_list,scope)
    
    scenarios_list = ['base']+scenarios_list
    
    df_to_print=pd.concat([dict_df_to_print[scenario] for scenario in scenarios_list],keys=scenarios_list,names=("scenario","regions"))
    
    df_to_print = df_to_print.reset_index()
    
    df_to_print['scenario'] = pd.Categorical(df_to_print.scenario, categories = scenarios_list, ordered = True)

    fig=px.bar(df_to_print.sort_values(by="scenario",kind="stable"),y=sector,color="regions",x="scenario",
                hover_name="regions",color_discrete_map=dict(zip(model.regions, COLORS[:len(model.regions)])))
    #.sort_values(ascending=False,by="emissions",axis=0)

    if scope==3:
        title_detail = f"Empreintes importées (scope{str(scope)})"
    else:
        title_detail = f"Impacts importés (scope{str(scope)})"

    fig.update_layout(
                title = f"{title_detail} par {country_importing} ({sector}) par origine d\'approvisionnement",
                xaxis_title = "Scenarios",
                yaxis_title = f'{stressors_to_display}, en {find_stressor_unit(stressors_to_display)}'
                )

    fig.show()
    
    
    if model.save_figures:
        save_dir = model.figures_dir / ("Impacts_per_exporting_regions_to_"+country_importing)/stressors_name_EN
        save_dir.mkdir(exist_ok = True, parents = True)
        fig.write_image(save_dir/(f"{stressors_name_EN}_scope{str(scope)}_impacts_by_exp_reg_for_{sector}.png"))
    