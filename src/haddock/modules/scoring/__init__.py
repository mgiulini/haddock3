"""HADDOCK3 modules to score models."""
import pandas as pd

from haddock.core.typing import FilePath
from haddock.modules.base_cns_module import BaseCNSModule
from haddock.modules import BaseHaddockModule


class ScoringModule(BaseHaddockModule):
    """Parent class for Scoring modules."""

    def output(
            self,
            output_fname: FilePath,
            sep: str = "\t",
            ascending_sort: bool = True,
            ) -> None:
        r"""Save the output in comprehensive tables.

        Parameters
        ----------
        output_fname : FilePath
            Path to the file where to write scoring data.
        sep : str, optional
            Charater used as separator in file, by default "\t"
        ascending_sort : bool, optional
            Should the data be sorted in ascending order, by default True
        """
        # saves scoring data
        sc_data = []
        for pdb in self.output_models:
            sc_data.append([pdb.file_name, pdb.ori_name, pdb.md5, pdb.score])
        
        # converts to pandas dataframe and sorts by score
        df_columns = ["structure", "original_name", "md5", "score"]
        df_sc = pd.DataFrame(sc_data, columns=df_columns)
        df_sc_sorted = df_sc.sort_values(by="score", ascending=ascending_sort)
        # writes to disk
        df_sc_sorted.to_csv(output_fname, sep=sep, index=False, na_rep="None")

        return


class CNSScoringModule(BaseCNSModule, ScoringModule):
    """Parent class for CNS Scoring modules."""
