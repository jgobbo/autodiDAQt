from pathlib import Path

import pytest

from daquiri.version import VERSION
from daquiri.mock import MockScalarDetector
from daquiri.state import (
    AppState,
    DaquiriStateAtRest,
    InstrumentState,
    SerializationSchema,
)
from tests.conftest import Mockdaquiri

from .utils import CoordinateOffsets, LogicalMockMotionController


@pytest.mark.asyncio
async def test_basic_state_collection(app: Mockdaquiri):
    app.init_with(managed_instruments={"mc": MockScalarDetector})

    # test that state defaults are reasonably populated
    state = app.collect_state()
    root = Path(__file__).parent.parent
    assert state == DaquiriStateAtRest(
        schema=SerializationSchema(
            daquiri_version=VERSION, user_version="0.0.0", app_root=root
        ),
        daquiri_state=AppState(),
        panels={},
        actors={},
        managed_instruments={
            "mc": InstrumentState(
                axes={"device": None}, properties={}, panel_state=None
            )
        },
    )


@pytest.mark.asyncio
async def test_logical_axis_state(app: Mockdaquiri):
    """Tests that logical axis state behaves appropriately.

    Note that state is only deepcopied at ``core.daquiri.collect_state`` at the moment,
    so if you want to unit test something coarser you will need to copy it yourself.
    """
    app.init_with(managed_instruments={"mc": LogicalMockMotionController})
    x_y_z, stages = app.instruments.mc.offset_x_y_z, app.instruments.mc.stages

    x_y_z.internal_state.x_off = 4.1
    state = app.collect_state()
    assert state.managed_instruments["mc"].axes[
        "offset_x_y_z"
    ].internal_state == CoordinateOffsets(x_off=4.1, y_off=0, z_off=0)

    x_y_z.internal_state.x_off = 0
    app.receive_state(state)
    assert state.managed_instruments["mc"].axes[
        "offset_x_y_z"
    ].internal_state == CoordinateOffsets(x_off=4.1, y_off=0, z_off=0)
