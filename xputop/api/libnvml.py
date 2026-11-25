# This file is part of xputop, the interactive Kunlunxin-XPU process viewer.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Compatibility alias for :mod:`xputop.api.libxpuml`."""

from __future__ import annotations

import sys as _sys

from xputop.api import libxpuml as _libxpuml
from xputop.api.libxpuml import *  # noqa: F403 # pylint: disable=wildcard-import,unused-wildcard-import
from xputop.api.libxpuml import (  # noqa: F401
    UNKNOWN_FUNCTIONS,
    VERSIONED_PATTERN,
    __all__,
    _pynvml_installation_corrupted,
)


_sys.modules[__name__] = _libxpuml
