from typing import Any, Dict, TYPE_CHECKING

import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import xarray as xr

from daquiri_common.json import RichEncoder

if TYPE_CHECKING:
    from .run import Run

__all__ = [
    "save_cls_from_short_name",
    "SaveContext",
    "RunSaver",
    "ZarrSaver",
    "PickleSaver",
    "ForgetfulSaver",
    "save_on_separate_thread",
]


def save_on_separate_thread(
    run: "Run",
    directory: Path,
    collation,
    extra_attrs=None,
    save_format="zarr",
    save_function=None,
):
    # if collation:
    #     try:
    #         collated = collation.to_xarray(run.daq_values)
    #     except:
    #         collated = None

    try:
        collated = collation.to_xarray(run.daq_values)
    except:
        collated = None

    run.save(
        directory,
        {"collated": collated},
        extra_attrs=extra_attrs,
        save_format=save_format,
        save_function=save_function,
    )


@dataclass
class SaveContext:
    save_directory: Path


class RunSaver:
    """
    Encapsulates logic around saving the result of a run.
    This was previously handled entirely by run itself,
    but now that we support different save mechanisms this makes
    sense to split out. Additionally, by having this split,
    it becomes straightforward for us to support multiple
    mechanisms for saving data, and more straightforward eventually
    to stream data when we are working with larger datasets.
    """

    short_name: str = None

    @classmethod
    def save_run(cls, metadata, data, context: SaveContext):
        raise NotImplementedError

    @staticmethod
    def save_pickle(path: Path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), "wb+") as f:
            pickle.dump(data, f, protocol=-1)

    @staticmethod
    def save_nc(path: Path, data: xr.Dataset):
        """This is super hacky and bad. Turns out it's incredibly hard to fix the data.
        Some things could be done to improve the universality of saving data but it's
        tricky. I think the best solution is to define a custom save function for each
        scan.
        """
        fixed = data.copy(deep=True)
        for data_var in data.data_vars:
            dtype = fixed[data_var].dtype
            if dtype == "object":
                bad_type = not isinstance(
                    fixed[data_var].data[0], (float, int, np.ndarray)
                )
                if bad_type:
                    fixed = fixed.drop_vars(data_var)
                else:
                    actual_type = type(fixed[data_var].data[0])
                    fixed[data_var] = fixed[data_var].astype(actual_type)

        for data_var in fixed.data_vars:
            var = fixed[data_var]
            if var.dtype == "object":
                data = var.data
                lengths = []
                for frame in data:
                    lengths.append(len(frame))
                lengths = xr.DataArray(
                    np.array(lengths),
                    coords=fixed[data_var].coords,
                    dims=fixed[data_var].dims,
                )
                fixed[data_var] = xr.DataArray(np.concatenate(data))
                fixed[f"{data_var}_lengths"] = lengths

        fixed.to_netcdf(path)

    @staticmethod
    def save_json(path: Path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), "w+") as f:
            json.dump(data, f, cls=RichEncoder, indent=2)

    @staticmethod
    def save_metadata(path: Path, metadata: Dict[str, Any]):
        RunSaver.save_json(
            path / "metadata-small.json",
            {k: v for k, v in metadata.items() if k == "metadata"},
        )
        RunSaver.save_json(path / "metadata.json", metadata)

    @staticmethod
    def save_user_extras(extra_data, context: SaveContext):
        raise NotImplementedError


class ZarrSaver(RunSaver):
    short_name = "zarr"

    @staticmethod
    def save_user_extras(extra_data, context: SaveContext):
        for k, v in extra_data.items():
            if v is None:
                continue

            v.to_zarr(context.save_directory / f"{k}.zarr")

    @staticmethod
    def save_run(metadata, data, context: SaveContext):
        ZarrSaver.save_metadata(context.save_directory, metadata)

        data.to_zarr(context.save_directory / "raw_daq.zarr")


class PickleSaver(RunSaver):
    short_name = "pickle"

    @staticmethod
    def save_user_extras(extra_data, context: SaveContext):
        for k, v in extra_data.items():
            if v is None:
                continue

            PickleSaver.save_pickle(context.save_directory / f"{k}.pickle", v)

    @staticmethod
    def save_run(metadata, data, context: SaveContext):
        PickleSaver.save_metadata(context.save_directory, metadata)
        PickleSaver.save_pickle(context.save_directory / "raw_daq.pickle", data)


class NetCDFSaver(RunSaver):
    short_name = "nc"

    @staticmethod
    def save_user_extras(extra_data, context: SaveContext):
        for k, v in extra_data.items():
            if v is None:
                continue

            NetCDFSaver.save_nc(context.save_directory / f"{k}.nc", v)

    @staticmethod
    def save_run(metadata: dict, data: xr.Dataset, context: SaveContext):
        NetCDFSaver.save_metadata(context.save_directory, metadata)
        NetCDFSaver.save_nc(context.save_directory / "raw_daq.nc", data)


class ForgetfulSaver(RunSaver):
    """
    This one doesn't do anything. This is useful if you are just
    trying to test something and don't actually want to produce data.
    """

    short_name = "forget"

    @staticmethod
    def save_run(metadata, data, context: SaveContext):
        return

    @staticmethod
    def save_user_extras(extras, context: SaveContext):
        return


_by_short_names = {
    cls.short_name: cls for cls in [ZarrSaver, PickleSaver, NetCDFSaver, ForgetfulSaver]
}
save_cls_from_short_name = _by_short_names.get
