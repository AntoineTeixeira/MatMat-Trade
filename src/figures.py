import matplotlib.ticker as mtick
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import pathlib
import seaborn as sns
from unidecode import unidecode

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
)


### CARBON FOOTPRINT ###


def plot_footprint(
    model,
    region: str = "FR",
    counterfactual_name: str = None,
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
        footprint_extractor(model=counterfactual, region=region), index=[""]
    )

    carbon_footprint.plot.barh(stacked=True, fontsize=17, figsize=(10, 5), rot=0)

    if title is None:
        title = f"Empreinte en {model.stressor_name} de la région {region}"
    plt.title(title, size=17, fontweight="bold")
    plt.xlabel(model.stressor_unit, size=15)
    plt.grid(visible=True)
    plt.legend(prop={"size": 15})
    plt.text(
        0.13,
        -0.2,
        build_description(model=model, counterfactual_name=counterfactual_name),
        transform=plt.gcf().transFigure,
    )

    plt.savefig(counterfactual.figures_dir / f"empreinte_{region}.png")


def plot_footprint_FR(
    model,
    counterfactual_name: str = None,
) -> None:
    """Plots french footprint (D_pba-D_exp+D_imp+F_Y)

    Args:
        model (Model): object Model defined in model.py
        counterfactual_name (str, optional): name of the counterfactual in model.counterfactuals. None for the reference. Defaults to None.
    """
    plot_footprint(
        model=model,
        region="FR",
        counterfactual_name=counterfactual_name,
        title=f"Empreinte en {model.stressor_name} de la France",
    )


### STRESSORS CONTENT DESCRIPTION ###


def plot_stressor_content_heatmap(
    model,
    counterfactual_name: str = None,
    prod: bool = False,
) -> None:
    """Plots the content in stressors of each sector for each region in a heatmap

    Args:
        model (Model): object Model defined in model.py
        counterfactual_name (str, optional): name of the counterfactual in model.counterfactuals. None for the reference. Defaults to None.
        prod (bool, optional): True to focus on production values, otherwise focus on consumption values. Defaults to False.
    """
    if counterfactual_name is None:
        counterfactual = model
    else:
        counterfactual = model.counterfactuals[counterfactual_name]
    sectors = model.agg_sectors
    regions = model.agg_regions
    if prod:
        title = f"Intensité de la production en {model.stressor_name}"
        activity = "production"
        S = counterfactual.iot.stressor_extension.S.sum()
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
        title = f"Contenu du bien importé en {model.stressor_name}"
        activity = "consumption"
        M = counterfactual.iot.stressor_extension.M.sum()
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
    plt.savefig(model.figures_dir / ("content_heatmap_" + activity))


def plot_stressor_content_production(model, counterfactual_name: str = None) -> None:
    """Compares the content in stressors of each region for each sector

    Args:
        model (Model): object Model defined in model.py
        counterfactual_name (str, optional): name of the counterfactual in model.counterfactuals. None for the reference. Defaults to None.
    """
    if counterfactual_name is None:
        counterfactual = model
    else:
        counterfactual = model.counterfactuals[counterfactual_name]

    S_unstacked = (counterfactual.iot.stressor_extension.S).sum().unstack().T

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
        f"Contenu de la production en {model.stressor_name}",
        size=17,
        fontweight="bold",
    )
    plt.xlabel(f"{model.stressor_unit} / M€", size=15)
    plt.tight_layout()
    plt.grid(visible=True)
    plt.legend(prop={"size": 15})
    plt.text(
        0.13,
        -0.2,
        build_description(model=model, counterfactual_name=counterfactual_name),
        transform=plt.gcf().transFigure,
    )
    plt.savefig(model.figures_dir / "content_hbar_production.png")


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
    account_unit: str,
    scenario_name: str,
    output_dir: pathlib.PosixPath,
    description: str,
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

    account_name = (
        account_name[0].upper() + account_name[1:]
    )  # doesn't use .capitalize() in order to preserve capital letters in the middle
    account_name_file = unidecode(account_name.lower().replace(" ", "_"))
    current_dir = output_dir / (scenario_name + "__" + account_name_file)

    if not os.path.isdir(current_dir):
        os.mkdir(current_dir)  # can overwrite existing files

    # plot reference importations
    ref_conso_by_sector_FR = reference_df
    ref_imports_by_region_FR = ref_conso_by_sector_FR.drop("FR", level=0).sum(level=0)

    ref_imports_by_region_FR.T.plot.barh(
        stacked=True, fontsize=17, color=COLORS_NO_FR, figsize=(12, 5)
    )
    plt.title(f"{account_name} (référence)", size=17, fontweight="bold")
    plt.xlabel(account_unit, size=15)
    plt.tight_layout()
    plt.grid(visible=True)
    plt.text(
        0.13,
        -0.2,
        description,
        transform=plt.gcf().transFigure,
    )
    plt.savefig(current_dir / "reference.png")
    plt.close()

    # plot counterfactual importations
    scen_conso_by_sector_FR = counterfactual_df
    scen_imports_by_region_FR = scen_conso_by_sector_FR.drop("FR", level=0).sum(level=0)

    scen_imports_by_region_FR.T.plot.barh(
        stacked=True, fontsize=17, color=COLORS_NO_FR, figsize=(12, 5)
    )
    plt.title(
        f"{account_name} (scénario {scenario_name})",
        size=17,
        fontweight="bold",
    )
    plt.xlabel(account_unit, size=15)
    plt.grid(visible=True)
    plt.text(
        0.13,
        -0.2,
        description,
        transform=plt.gcf().transFigure,
    )
    plt.savefig(current_dir / f"{scenario_name}.png")

    # compare counterfactual and reference importations
    compare_imports_by_region_FR = pd.DataFrame(
        {
            "Référence": ref_imports_by_region_FR,
            f"Scénario {scenario_name}": scen_imports_by_region_FR,
        }
    )
    compare_imports_by_region_FR.T.plot.barh(
        stacked=True, fontsize=17, figsize=(12, 8), color=COLORS_NO_FR
    )
    plt.title(f"{account_name} (comparaison)", size=17, fontweight="bold")
    plt.xlabel(account_unit, size=15)
    plt.tight_layout()
    plt.grid(visible=True)
    plt.legend(prop={"size": 12})
    plt.text(
        0.13,
        -0.2,
        description,
        transform=plt.gcf().transFigure,
    )
    plt.savefig(current_dir / f"comparison_by_region.png")

    # compare each region for each importation sector for the reference and the counterfactual

    def grouped_and_stacked_plot(
        df_ref: pd.DataFrame,
        df_scen: pd.DataFrame,
        percent_x_scale: bool,
        plot_title: str,
        plot_filename: str,
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
            columns=regions[1:],
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
                    color=COLORS_NO_FR,
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
        plt.legend(ncol=3, loc="lower left", bbox_to_anchor=(-0.35, -4.5))
        plt.text(
            0.13,
            -0.3,
            description,
            transform=plt.gcf().transFigure,
        )
        plt.savefig(current_dir / plot_filename)
        plt.show()

    try:
        df_ref_parts = (
            (
                ref_conso_by_sector_FR.drop("FR", level=0)
                / ref_conso_by_sector_FR.drop("FR", level=0).sum(level=1)
            )
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )
        df_scen_parts = (
            (
                scen_conso_by_sector_FR.drop("FR", level=0)
                / scen_conso_by_sector_FR.drop("FR", level=0).sum(level=1)
            )
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )
        grouped_and_stacked_plot(
            df_ref_parts,
            df_scen_parts,
            True,
            f"{account_name}",
            f"comparison_parts_region_sector.png",
        )
    except ValueError:
        pass  # ignore substressors plot, may be improved

    df_ref_values = (
        ref_conso_by_sector_FR.drop("FR", level=0)
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )
    df_scen_values = (
        scen_conso_by_sector_FR.drop("FR", level=0)
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )
    grouped_and_stacked_plot(
        df_ref_values,
        df_scen_values,
        False,
        f"{account_name}",
        f"comparison_values_region_sector.png",
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

    plot_df_synthesis(
        reference_df=reference_trade,
        counterfactual_df=counterfactual_trade,
        account_name="importations françaises",
        account_unit="M€",
        scenario_name=counterfactual_name,
        output_dir=counterfactual.figures_dir,
        description=build_description(
            model=model, counterfactual_name=counterfactual_name
        ),
    )


def plot_stressor_synthesis(
    model,
    counterfactual_name: str,
) -> None:
    """Plots the french emissions of stressors by sector for a given counterfactual

    Args:
        model (Model): object Model defined in model.py
        counterfactual_name (str): name of the counterfactual in model.counterfactuals
    """
    counterfactual = model.counterfactuals[counterfactual_name]

    emissions_types = {
        "D_cba": f"empreinte de la France en {model.stressor_name}",
        "D_pba": f"émissions territoriales de la France en {model.stressor_name}",
        "D_imp": f"émissions importées par la France en {model.stressor_name}",
        "D_exp": f"émissions exportées par la France en {model.stressor_name}",
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

        reference_trade = ref_df["FR"].sum(level=0).stack()
        counterfactual_trade = count_df["FR"].sum(level=0).stack()

        plot_df_synthesis(
            reference_df=reference_trade,
            counterfactual_df=counterfactual_trade,
            account_name=description,
            account_unit=model.stressor_unit,
            scenario_name=counterfactual_name,
            output_dir=counterfactual.figures_dir,
            description=build_description(
                model=model, counterfactual_name=counterfactual_name
            ),
        )


def plot_substressor_synthesis(
    model,
    counterfactual_name: str,
) -> None:
    """Plots the french emissions per substressor for a given counterfactual

    Args:
        model (Model): object Model defined in model.py
        counterfactual_name (str): name of the counterfactual in model.counterfactuals
    """
    counterfactual = model.counterfactuals[counterfactual_name]

    emissions_types = {
        "D_cba": f"empreinte de la France en {model.stressor_name}",
        "D_pba": f"émissions territoriales de la France en {model.stressor_name}",
        "D_imp": f"émissions importées par la France en {model.stressor_name}",
        "D_exp": f"émissions exportées par la France en {model.stressor_name}",
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

        reference_stressor = ref_df["FR"].sum(axis=1)
        counterfactual_stressor = count_df["FR"].sum(axis=1)

        plot_df_synthesis(
            reference_df=reference_stressor,
            counterfactual_df=counterfactual_stressor,
            account_name=description,
            account_unit=model.stressor_unit,
            scenario_name=counterfactual_name,
            output_dir=counterfactual.figures_dir,
            description=build_description(
                model=model, counterfactual_name=counterfactual_name
            ),
        )
