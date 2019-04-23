"""
QCPortal Database ODM
"""
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pandas as pd

from pydantic import BaseModel

from .collection_utils import register_collection
from .collection import BaseProcedureDataset
from ..models import ObjectId, Molecule, OptimizationSpecification, QCSpecification, TorsionDriveInput
from ..models.torsiondrive import TDKeywords
from ..visualization import custom_plot


class TDRecord(BaseModel):
    """Data model for the `reactions` list in Dataset"""
    name: str
    initial_molecules: List[ObjectId]
    td_keywords: TDKeywords
    attributes: Dict[str, Union[int, float, str]]  # Might be overloaded key types
    object_map: Dict[str, ObjectId] = {}


class TorsionDriveSpecification(BaseModel):
    name: str
    description: Optional[str]
    optimization_spec: OptimizationSpecification
    qc_spec: QCSpecification


class TorsionDriveDataset(BaseProcedureDataset):
    class DataModel(BaseProcedureDataset.DataModel):

        records: Dict[str, TDRecord] = {}
        history: Set[str] = set()
        specs: Dict[str, TorsionDriveSpecification] = {}

        class Config(BaseProcedureDataset.DataModel.Config):
            pass

    def add_specification(self,
                          name: str,
                          optimization_spec: OptimizationSpecification,
                          qc_spec: QCSpecification,
                          description: str=None,
                          overwrite=False) -> None:
        """
        Parameters
        ----------
        name : str
            The name of the specification
        optimization_spec : OptimizationSpecification
            A full optimization specification for TorsionDrive
        qc_spec : QCSpecification
            A full quantum chemistry specification for TorsionDrive
        description : str, optional
            A short text description of the specification
        overwrite : bool, optional
            Overwrite existing specification names

        """

        spec = TorsionDriveSpecification(
            name=name, optimization_spec=optimization_spec, qc_spec=qc_spec, description=description)

        return self._add_specification(name, spec, overwrite=overwrite)

    def add_entry(self,
                  name: str,
                  initial_molecules: List[Molecule],
                  dihedrals: List[Tuple[int, int, int, int]],
                  grid_spacing: List[int],
                  dihedral_ranges: Optional[List[Tuple[int, int]]]=None,
                  energy_decrease_thresh: Optional[float]=None,
                  energy_upper_limit: Optional[float]=None,
                  attributes: Dict[str, Any]=None) -> None:
        """
        Parameters
        ----------
        name : str
            The name of the entry, will be used for the index
        initial_molecules : List[Molecule]
            The list of starting Molecules for the TorsionDrive
        dihedrals : List[Tuple[int, int, int, int]]
            A list of dihedrals to scan over
        grid_spacing : List[int]
            The grid spacing for each dihedrals
        dihedral_ranges: Optional[List[Tuple[int, int]]]
            The range limit of each dihedrals to scan, within [-180, 360]
        energy_decrease_thresh: Optional[float]
            The threshold of energy decrease to trigger activating grid points
        energy_upper_limit: Optional[float]
            The upper limit of energy relative to current global minimum to trigger activating grid points
        attributes : Dict[str, Any], optional
            Additional attributes and descriptions for the record
        """

        # Build new objects
        molecule_ids = self.client.add_molecules(initial_molecules)
        td_keywords = TDKeywords(
            dihedrals=dihedrals,
            grid_spacing=grid_spacing,
            dihedral_ranges=dihedral_ranges,
            energy_decrease_thresh=energy_decrease_thresh,
            energy_upper_limit=energy_upper_limit)

        record = TDRecord(name=name, initial_molecules=molecule_ids, td_keywords=td_keywords, attributes=attributes)

        self._add_entry(name, record)

    def compute(self, specification: str, subset: Set[str]=None, tag: Optional[str]=None,
                priority: Optional[str]=None) -> int:
        """Computes a specification for all records in the dataset.

        Parameters
        ----------
        specification : str
            The specification name.
        subset : Set[str], optional
            Computes only a subset of the dataset.
        tag : Optional[str], optional
            The queue tag to use when submitting compute requests.
        priority : Optional[str], optional
            The priority of the jobs low, medium, or high.

        Returns
        -------
        int
            The number of submitted torsiondrives
        """
        specification = specification.lower()
        spec = self.get_specification(specification)
        if subset:
            subset = set(subset)

        submitted = 0
        for rec in self.data.records.values():
            if specification in rec.object_map:
                continue

            if (subset is not None) and (rec.name not in subset):
                continue

            service = TorsionDriveInput(
                initial_molecule=rec.initial_molecules,
                keywords=rec.td_keywords,
                optimization_spec=spec.optimization_spec,
                qc_spec=spec.qc_spec)

            rec.object_map[specification] = self.client.add_service([service], tag=tag, priority=priority).ids[0]
            submitted += 1

        self.data.history.add(specification)
        self.save()
        return submitted

    def counts(self,
               entries: Union[str, List[str]],
               specs: Optional[Union[str, List[str]]]=None,
               count_gradients=False) -> 'DataFrame':
        """Counts the number of optimization or gradient evaluations associated with the
        TorsionDrives.

        Parameters
        ----------
        entries : Union[str, List[str]]
            The entries to query for
        specs : Optional[Union[str, List[str]]], optional
            The specifications to query for
        count_gradients : bool, optional
            If True, counts the total number of gradient calls. Warning! This can be slow for large datasets.

        Returns
        -------
        DataFrame
            The queried counts.
        """

        # Specifications
        if isinstance(specs, str):
            specs = [specs]

        if isinstance(entries, str):
            entries = [entries]

        # Query all of the specs and make sure they are valid
        if specs is None:
            specs = list(self.df.columns)
        else:
            for spec in specs:
                self.query(spec)

        # Count functions
        def count_gradient_evals(td):
            if td.status != "COMPLETE":
                return None

            total_grads = 0
            for key, optimizations in td.get_history().items():
                for opt in optimizations:
                    total_grads += len(opt.trajectory)
            return total_grads

        def count_optimizations(td):
            if td.status != "COMPLETE":
                return None
            return sum(len(v) for v in td.optimization_history.values())

        # Loop over the data and apply the count function
        ret = []
        for col in specs:
            data = self.df[col]
            if entries:
                data = data[entries]

            if count_gradients:
                cnts = data.apply(lambda td: count_gradient_evals(td))
            else:
                cnts = data.apply(lambda td: count_optimizations(td))
            ret.append(cnts)

        ret = pd.DataFrame(ret).transpose()
        ret.dropna(inplace=True, how="all")
        # ret = pd.DataFrame([ret[x].astype(int) for x in ret.columns]).transpose()
        return ret

    def visualize(self,
                  entries: Union[str, List[str]],
                  specs: Union[str, List[str]],
                  relative: bool=True,
                  units: str="kcal / mol",
                  digits: int=3,
                  use_measured_angle: bool=False,
                  return_figure: Optional[bool]=None) -> 'plotly.Figure':
        """
        Parameters
        ----------
        entries : Union[str, List[str]]
            A single or list of indices to plot.
        specs : Union[str, List[str]]
            A single or list of specifications to plot.
        relative : bool, optional
            Shows relative energy, lowest energy per scan is zero.
        units : str, optional
            The units of the plot.
        digits : int, optional
            Rounds the energies to n decimal places for display.
        use_measured_angle : bool, optional
            If True, the measured final angle instead of the constrained optimization angle.
            Can provide more accurate results if the optimization was ill-behaved,
            but pulls additional data from the server and may take longer.
        return_figure : Optional[bool], optional
            If True, return the raw plotly figure. If False, returns a hosted iPlot. If None, return a iPlot display in Jupyter notebook and a raw plotly figure in all other circumstances.

        Returns
        -------
        plotly.Figure
            The requested figure.
        """

        show_spec = True
        if isinstance(specs, str):
            specs = [specs]
            show_spec = False

        if isinstance(entries, str):
            entries = [entries]

        # Query all of the specs and make sure they are valid
        formatted_spec_names = []
        for spec in specs:
            formatted_spec_names.append(self.query(spec))

        traces = []
        ranges = []
        # Loop over specifications
        for spec in formatted_spec_names:
            # Loop over indices (groups colors by entry)
            for index in entries:

                # Plot the figure using the torsiondrives plotting function
                fig = self.df.loc[index, spec].visualize(
                    relative=relative,
                    units=units,
                    digits=digits,
                    use_measured_angle=use_measured_angle,
                    return_figure=True)

                ranges.append(fig.layout.xaxis.range)
                trace = fig.data[0]  # Pull out the underlying scatterplot

                if show_spec:
                    trace.name = f"{index}-{spec}"
                else:
                    trace.name = f"{index}"

                traces.append(trace)

        title = "TorsionDriveDataset 1-D Plot"
        if show_spec is False:
            title += f" [spec={formatted_spec_names[0]}]"

        if relative:
            ylabel = f"Relative Energy [{units}]"
        else:
            ylabel = f"Absolute Energy [{units}]"

        custom_layout = {
            "title": title,
            "yaxis": {
                "title": ylabel,
                "zeroline": True
            },
            "xaxis": {
                "title": "Dihedral Angle [degrees]",
                "zeroline": False,
                "range": [min(x[0] for x in ranges), max(x[1] for x in ranges)]
            }
        }

        return custom_plot(traces, custom_layout, return_figure=return_figure)


register_collection(TorsionDriveDataset)
