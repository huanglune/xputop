# This file is part of nvitop, the interactive NVIDIA-GPU process viewer.
# License: GNU GPL version 3.

# pylint: disable=missing-module-docstring

from xputop.tui.screens.main.panels.base import BasePanel, BaseSelectablePanel
from xputop.tui.screens.main.panels.device import DevicePanel
from xputop.tui.screens.main.panels.host import HostPanel
from xputop.tui.screens.main.panels.process import OrderName, ProcessPanel


__all__ = [
    'BasePanel',
    'BaseSelectablePanel',
    'DevicePanel',
    'HostPanel',
    'OrderName',
    'ProcessPanel',
]
