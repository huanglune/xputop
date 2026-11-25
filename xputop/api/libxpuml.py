# This file is part of xputop, the interactive Kunlunxin-XPU process viewer.
#
# Copyright 2021-2026 Xuehai Pan. All Rights Reserved.
# Copyright 2026 Kunlunxin XPU Port Contributors. All Rights Reserved.
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
"""Python ctypes bindings for Kunlunxin XPU Management Library (``libxpuml.so``).

This module provides native ``ctypes`` bindings to Kunlunxin's ``libxpuml.so.1`` without
requiring ``nvidia-ml-py`` or ``pynvml``, while maintaining full API compatibility with
``nvitop.api.libnvml`` so higher-level device and process abstractions work seamlessly.
"""

# pylint: disable=too-many-lines,invalid-name,too-few-public-methods,missing-class-docstring

from __future__ import annotations

import atexit as _atexit
import ctypes as _ctypes
import inspect as _inspect
import logging as _logging
import os as _os
import re as _re
import sys as _sys
import threading as _threading
import time as _time
from types import FunctionType as _FunctionType
from types import ModuleType as _ModuleType
from typing import TYPE_CHECKING as _TYPE_CHECKING
from typing import Any as _Any
from typing import ClassVar as _ClassVar

from xputop.api.utils import NA, UINT_MAX, ULONGLONG_MAX, NaType
from xputop.api.utils import colored as __colored


if _TYPE_CHECKING:
    from collections.abc import Callable as _Callable
    from typing_extensions import Self as _Self
    from typing_extensions import TypeAlias as _TypeAlias


# Constants from xpuml.h / nvml.h ##################################################################

XPUML_API_VERSION = 1
XPUML_VALUE_NOT_AVAILABLE = -1

XPUML_DEVICE_PCI_BUS_ID_BUFFER_SIZE = 32
XPUML_DEVICE_UUID_BUFFER_SIZE = 96
XPUML_DEVICE_PART_NUMBER_BUFFER_SIZE = 80
XPUML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE = 80
XPUML_SYSTEM_XPUML_VERSION_BUFFER_SIZE = 80
XPUML_DEVICE_NAME_BUFFER_SIZE = 96
XPUML_DEVICE_SERIAL_BUFFER_SIZE = 17
XPUML_DEVICE_INFOROM_VERSION_BUFFER_SIZE = 16
XPUML_XPULINK_MAX_LINKS = 4
XPUML_DEVICE_MAX_PROCESS_COUNT = 100

NVML_DEVICE_PCI_BUS_ID_BUFFER_SIZE = XPUML_DEVICE_PCI_BUS_ID_BUFFER_SIZE
NVML_DEVICE_UUID_BUFFER_SIZE = XPUML_DEVICE_UUID_BUFFER_SIZE
NVML_DEVICE_NAME_BUFFER_SIZE = XPUML_DEVICE_NAME_BUFFER_SIZE
NVML_DEVICE_SERIAL_BUFFER_SIZE = XPUML_DEVICE_SERIAL_BUFFER_SIZE
NVML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE = XPUML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE
NVML_SYSTEM_NVML_VERSION_BUFFER_SIZE = XPUML_SYSTEM_XPUML_VERSION_BUFFER_SIZE

# Return codes
XPUML_SUCCESS = NVML_SUCCESS = 0
XPUML_ERROR_UNINITIALIZED = NVML_ERROR_UNINITIALIZED = 1
XPUML_ERROR_INVALID_ARGUMENT = NVML_ERROR_INVALID_ARGUMENT = 2
XPUML_ERROR_NOT_SUPPORTED = NVML_ERROR_NOT_SUPPORTED = 3
XPUML_ERROR_NO_PERMISSION = NVML_ERROR_NO_PERMISSION = 4
XPUML_ERROR_ALREADY_INITIALIZED = NVML_ERROR_ALREADY_INITIALIZED = 5
XPUML_ERROR_NOT_FOUND = NVML_ERROR_NOT_FOUND = 6
XPUML_ERROR_INSUFFICIENT_SIZE = NVML_ERROR_INSUFFICIENT_SIZE = 7
XPUML_ERROR_INSUFFICIENT_POWER = NVML_ERROR_INSUFFICIENT_POWER = 8
XPUML_ERROR_DRIVER_NOT_LOADED = NVML_ERROR_DRIVER_NOT_LOADED = 9
XPUML_ERROR_TIMEOUT = NVML_ERROR_TIMEOUT = 10
XPUML_ERROR_IRQ_ISSUE = NVML_ERROR_IRQ_ISSUE = 11
XPUML_ERROR_LIBRARY_NOT_FOUND = NVML_ERROR_LIBRARY_NOT_FOUND = 12
XPUML_ERROR_FUNCTION_NOT_FOUND = NVML_ERROR_FUNCTION_NOT_FOUND = 13
XPUML_ERROR_CORRUPTED_INFOROM = NVML_ERROR_CORRUPTED_INFOROM = 14
XPUML_ERROR_XPU_IS_LOST = XPUML_ERROR_GPU_IS_LOST = NVML_ERROR_GPU_IS_LOST = 15
XPUML_ERROR_RESET_REQUIRED = NVML_ERROR_RESET_REQUIRED = 16
XPUML_ERROR_OPERATING_SYSTEM = NVML_ERROR_OPERATING_SYSTEM = 17
XPUML_ERROR_LIB_RM_VERSION_MISMATCH = NVML_ERROR_LIB_RM_VERSION_MISMATCH = 18
XPUML_ERROR_IN_USE = NVML_ERROR_IN_USE = 19
XPUML_ERROR_MEMORY = NVML_ERROR_MEMORY = 20
XPUML_ERROR_NO_DATA = NVML_ERROR_NO_DATA = 21
XPUML_ERROR_VXPU_ECC_NOT_SUPPORTED = NVML_ERROR_VGPU_ECC_NOT_SUPPORTED = 22
XPUML_ERROR_INSUFFICIENT_RESOURCES = NVML_ERROR_INSUFFICIENT_RESOURCES = 23
XPUML_ERROR_FREQ_NOT_SUPPORTED = 24
XPUML_ERROR_UNKNOWN = NVML_ERROR_UNKNOWN = 999

# Feature enable state
XPUML_FEATURE_DISABLED = NVML_FEATURE_DISABLED = 0
XPUML_FEATURE_ENABLED = NVML_FEATURE_ENABLED = 1

# Clock types (in libxpuml: 0=XPU/Cluster, and internal nvmlDeviceGetClockInfo: 2=MEM(1450), 3=VIDEO(900), 4=Cluster(1450), 5=CDNN(1450))
XPUML_CLOCK_XPU = 0
XPUML_CLOCK_CLUSTER = 4
XPUML_CLOCK_CDNN = 5
NVML_CLOCK_GRAPHICS = 0
NVML_CLOCK_SM = 1
NVML_CLOCK_MEM = 2
NVML_CLOCK_VIDEO = 3
NVML_CLOCK_CLUSTER = 4
NVML_CLOCK_CDNN = 5

# Temperature sensors & thresholds
XPUML_TEMPERATURE_XPU = NVML_TEMPERATURE_GPU = 0
XPUML_TEMPERATURE_THRESHOLD_SHUTDOWN = NVML_TEMPERATURE_THRESHOLD_SHUTDOWN = 0
XPUML_TEMPERATURE_THRESHOLD_SLOWDOWN = NVML_TEMPERATURE_THRESHOLD_SLOWDOWN = 1

# Driver models
NVML_DRIVER_WDDM = 0
NVML_DRIVER_WDM = 1
NVML_DRIVER_MCDM = 2

# ECC error & counter types
XPUML_MEMORY_ERROR_TYPE_CORRECTED = NVML_MEMORY_ERROR_TYPE_CORRECTED = 0
XPUML_MEMORY_ERROR_TYPE_UNCORRECTED = NVML_MEMORY_ERROR_TYPE_UNCORRECTED = 1
XPUML_VOLATILE_ECC = NVML_VOLATILE_ECC = 0
XPUML_AGGREGATE_ECC = NVML_AGGREGATE_ECC = 1
XPUML_MEMORY_LOCATION_GLOBAL_MEMORY = 0
XPUML_MEMORY_LOCATION_L3_MEMORY = 1

# Compute modes
NVML_COMPUTEMODE_DEFAULT = 0
NVML_COMPUTEMODE_EXCLUSIVE_THREAD = 1
NVML_COMPUTEMODE_PROHIBITED = 2
NVML_COMPUTEMODE_EXCLUSIVE_PROCESS = 3

# Host vXPU (SR-IOV) modes
XPUML_HOST_VXPU_MODE_NON_SRIOV = 0
XPUML_HOST_VXPU_MODE_SRIOV_OFF = 1
XPUML_HOST_VXPU_MODE_SRIOV_ON = 2

# Device states
XPUML_DEVICE_STATE_UNUSED = 0
XPUML_DEVICE_STATE_RUNNING = 201
XPUML_DEVICE_STATE_IN_RESET = 205
XPUML_DEVICE_STATE_ERROR = 207
XPUML_DEVICE_STATE_IN_EXCEPTION = 208

# Device architectures
XPUML_DEVICE_ARCH_UNKNOWN = 0
XPUML_DEVICE_ARCH_KL1 = 1
XPUML_DEVICE_ARCH_KL2 = 2
XPUML_DEVICE_ARCH_KL3 = 3
XPUML_DEVICE_MODEL_KL3 = 300

# Firmware InfoROM object IDs
XPUML_INT_INFOROM_PBL = 102
XPUML_INT_INFOROM_PCIE = 103
XPUML_INT_INFOROM_SBL = 104

# PCIe & NVLink constants
XPUML_PCIE_UTIL_TX_BYTES = NVML_PCIE_UTIL_TX_BYTES = 0
XPUML_PCIE_UTIL_RX_BYTES = NVML_PCIE_UTIL_RX_BYTES = 1
NVML_NVLINK_MAX_LINKS = XPUML_XPULINK_MAX_LINKS
NVML_FI_DEV_NVLINK_LINK_COUNT = 91
NVML_FI_DEV_NVLINK_THROUGHPUT_DATA_TX = 138
NVML_FI_DEV_NVLINK_THROUGHPUT_DATA_RX = 139
NVML_FI_DEV_NVLINK_THROUGHPUT_RAW_TX = 140
NVML_FI_DEV_NVLINK_THROUGHPUT_RAW_RX = 141

# Field value types
XPUML_VALUE_TYPE_DOUBLE = NVML_VALUE_TYPE_DOUBLE = 0
XPUML_VALUE_TYPE_UNSIGNED_INT = NVML_VALUE_TYPE_UNSIGNED_INT = 1
XPUML_VALUE_TYPE_UNSIGNED_LONG = NVML_VALUE_TYPE_UNSIGNED_LONG = 2
XPUML_VALUE_TYPE_UNSIGNED_LONG_LONG = NVML_VALUE_TYPE_UNSIGNED_LONG_LONG = 3
XPUML_VALUE_TYPE_SIGNED_LONG_LONG = NVML_VALUE_TYPE_SIGNED_LONG_LONG = 4
NVML_VALUE_TYPE_SIGNED_INT = 5


# Exception hierarchy ##############################################################################

_ERRCODE_TO_STRING: dict[int, str] = {
    XPUML_SUCCESS: 'Success',
    XPUML_ERROR_UNINITIALIZED: 'Uninitialized',
    XPUML_ERROR_INVALID_ARGUMENT: 'Invalid Argument',
    XPUML_ERROR_NOT_SUPPORTED: 'Not Supported',
    XPUML_ERROR_NO_PERMISSION: 'Insufficient Permissions',
    XPUML_ERROR_ALREADY_INITIALIZED: 'Already Initialized',
    XPUML_ERROR_NOT_FOUND: 'Not Found',
    XPUML_ERROR_INSUFFICIENT_SIZE: 'Insufficient Size',
    XPUML_ERROR_INSUFFICIENT_POWER: 'Insufficient External Power',
    XPUML_ERROR_DRIVER_NOT_LOADED: 'Driver Not Loaded',
    XPUML_ERROR_TIMEOUT: 'Timeout',
    XPUML_ERROR_IRQ_ISSUE: 'Interrupt Request Issue',
    XPUML_ERROR_LIBRARY_NOT_FOUND: 'XPUML Shared Library Not Found',
    XPUML_ERROR_FUNCTION_NOT_FOUND: 'Function Not Found',
    XPUML_ERROR_CORRUPTED_INFOROM: 'Corrupted infoROM',
    XPUML_ERROR_XPU_IS_LOST: 'XPU is lost',
    XPUML_ERROR_RESET_REQUIRED: 'XPU requires restart',
    XPUML_ERROR_OPERATING_SYSTEM: 'The operating system has blocked the request.',
    XPUML_ERROR_LIB_RM_VERSION_MISMATCH: 'RM has detected a driver/library version mismatch.',
    XPUML_ERROR_IN_USE: 'XPU is currently in use',
    XPUML_ERROR_MEMORY: 'Insufficient Memory',
    XPUML_ERROR_NO_DATA: 'No Data',
    XPUML_ERROR_VXPU_ECC_NOT_SUPPORTED: 'vXPU ECC Not Supported',
    XPUML_ERROR_INSUFFICIENT_RESOURCES: 'Insufficient Resources',
    XPUML_ERROR_FREQ_NOT_SUPPORTED: 'Frequency Not Supported',
    XPUML_ERROR_UNKNOWN: 'Unknown Error',
}

_ERRCODE_CLASS_REGISTRY: dict[int, type[NVMLError]] = {}


class NVMLError(Exception):
    """Base exception class for XPUML/NVML query errors."""

    _valClassMapping: _ClassVar[dict[int, type[NVMLError]]] = _ERRCODE_CLASS_REGISTRY
    _errcode_to_string: _ClassVar[dict[int, str]] = _ERRCODE_TO_STRING
    _default_errcode: _ClassVar[int] = XPUML_ERROR_UNKNOWN

    def __new__(cls, value: int | None = None) -> NVMLError:
        if value is None:
            value = getattr(cls, '_default_errcode', XPUML_ERROR_UNKNOWN)
        if cls is NVMLError:
            cls = _ERRCODE_CLASS_REGISTRY.get(value, cls)
        obj = Exception.__new__(cls)
        obj.value = value
        return obj

    def __str__(self) -> str:
        try:
            if self.value not in _ERRCODE_TO_STRING:
                return f'Unknown XPUML Error {self.value}'
            return _ERRCODE_TO_STRING[self.value]
        except AttributeError:
            return super().__str__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, NVMLError):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return False

    def __hash__(self) -> int:
        return hash(self.value)


XPUMLError = NVMLError


def _make_error_subclass(name: str, errcode: int) -> type[NVMLError]:
    subclass = type(
        name,
        (NVMLError,),
        {
            '__doc__': f'{_ERRCODE_TO_STRING.get(errcode, name)} ({errcode}).',
            '_default_errcode': errcode,
        },
    )
    _ERRCODE_CLASS_REGISTRY[errcode] = subclass
    return subclass


NVMLError_Uninitialized = XPUMLError_Uninitialized = _make_error_subclass('NVMLError_Uninitialized', XPUML_ERROR_UNINITIALIZED)
NVMLError_InvalidArgument = XPUMLError_InvalidArgument = _make_error_subclass('NVMLError_InvalidArgument', XPUML_ERROR_INVALID_ARGUMENT)
NVMLError_NotSupported = XPUMLError_NotSupported = _make_error_subclass('NVMLError_NotSupported', XPUML_ERROR_NOT_SUPPORTED)
NVMLError_NoPermission = XPUMLError_NoPermission = _make_error_subclass('NVMLError_NoPermission', XPUML_ERROR_NO_PERMISSION)
NVMLError_AlreadyInitialized = XPUMLError_AlreadyInitialized = _make_error_subclass('NVMLError_AlreadyInitialized', XPUML_ERROR_ALREADY_INITIALIZED)
NVMLError_NotFound = XPUMLError_NotFound = _make_error_subclass('NVMLError_NotFound', XPUML_ERROR_NOT_FOUND)
NVMLError_InsufficientSize = XPUMLError_InsufficientSize = _make_error_subclass('NVMLError_InsufficientSize', XPUML_ERROR_INSUFFICIENT_SIZE)
NVMLError_InsufficientPower = XPUMLError_InsufficientPower = _make_error_subclass('NVMLError_InsufficientPower', XPUML_ERROR_INSUFFICIENT_POWER)
NVMLError_DriverNotLoaded = XPUMLError_DriverNotLoaded = _make_error_subclass('NVMLError_DriverNotLoaded', XPUML_ERROR_DRIVER_NOT_LOADED)
NVMLError_Timeout = XPUMLError_Timeout = _make_error_subclass('NVMLError_Timeout', XPUML_ERROR_TIMEOUT)
NVMLError_IrqIssue = XPUMLError_IrqIssue = _make_error_subclass('NVMLError_IrqIssue', XPUML_ERROR_IRQ_ISSUE)
NVMLError_LibraryNotFound = XPUMLError_LibraryNotFound = _make_error_subclass('NVMLError_LibraryNotFound', XPUML_ERROR_LIBRARY_NOT_FOUND)
NVMLError_FunctionNotFound = XPUMLError_FunctionNotFound = _make_error_subclass('NVMLError_FunctionNotFound', XPUML_ERROR_FUNCTION_NOT_FOUND)
NVMLError_CorruptedInforom = XPUMLError_CorruptedInforom = _make_error_subclass('NVMLError_CorruptedInforom', XPUML_ERROR_CORRUPTED_INFOROM)
NVMLError_GpuIsLost = XPUMLError_XpuIsLost = _make_error_subclass('NVMLError_GpuIsLost', XPUML_ERROR_XPU_IS_LOST)
NVMLError_ResetRequired = XPUMLError_ResetRequired = _make_error_subclass('NVMLError_ResetRequired', XPUML_ERROR_RESET_REQUIRED)
NVMLError_OperatingSystem = XPUMLError_OperatingSystem = _make_error_subclass('NVMLError_OperatingSystem', XPUML_ERROR_OPERATING_SYSTEM)
NVMLError_LibRmVersionMismatch = XPUMLError_LibRmVersionMismatch = _make_error_subclass('NVMLError_LibRmVersionMismatch', XPUML_ERROR_LIB_RM_VERSION_MISMATCH)
NVMLError_InUse = XPUMLError_InUse = _make_error_subclass('NVMLError_InUse', XPUML_ERROR_IN_USE)
NVMLError_Memory = XPUMLError_Memory = _make_error_subclass('NVMLError_Memory', XPUML_ERROR_MEMORY)
NVMLError_NoData = XPUMLError_NoData = _make_error_subclass('NVMLError_NoData', XPUML_ERROR_NO_DATA)
NVMLError_VgpuEccNotSupported = XPUMLError_VxpuEccNotSupported = _make_error_subclass('NVMLError_VgpuEccNotSupported', XPUML_ERROR_VXPU_ECC_NOT_SUPPORTED)
NVMLError_InsufficientResources = XPUMLError_InsufficientResources = _make_error_subclass('NVMLError_InsufficientResources', XPUML_ERROR_INSUFFICIENT_RESOURCES)
NVMLError_FreqNotSupported = XPUMLError_FreqNotSupported = _make_error_subclass('NVMLError_FreqNotSupported', XPUML_ERROR_FREQ_NOT_SUPPORTED)
NVMLError_Unknown = XPUMLError_Unknown = _make_error_subclass('NVMLError_Unknown', XPUML_ERROR_UNKNOWN)


def nvmlExceptionClass(errcode: int) -> type[NVMLError]:
    """Map value to a proper subclass of :class:`NVMLError`."""
    return _ERRCODE_CLASS_REGISTRY.get(errcode, NVMLError)


# ctypes Structures ################################################################################


class _PrintableStructure(_ctypes.Structure):
    _fmt_: _ClassVar[dict[str, str]] = {}

    def __str__(self) -> str:
        lines = []
        for field_name, *_ in self._fields_:
            value = getattr(self, field_name)
            lines.append(f'{field_name}: {value!r}')
        return f'{self.__class__.__name__}({", ".join(lines)})'


class FriendlyObject:
    """Friendly Python object converted from a ctypes Structure."""

    def __init__(self, dictionary: dict[str, _Any]) -> None:
        for key, value in dictionary.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        attrs = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())
        return f'{self.__class__.__name__}({attrs})'

    __repr__ = __str__


def nvmlStructToFriendlyObject(struct: _ctypes.Structure) -> FriendlyObject:
    """Convert a ctypes Structure to a FriendlyObject with decoded strings."""
    d: dict[str, _Any] = {}
    for field_name, *_ in struct._fields_:
        val = getattr(struct, field_name)
        if isinstance(val, bytes):
            val = val.decode('utf-8', errors='replace')
        d[field_name] = val
    return FriendlyObject(d)


class _Struct_c_xpumlDevice_t(_ctypes.Structure):
    pass


c_xpumlDevice_t = _ctypes.POINTER(_Struct_c_xpumlDevice_t)
c_nvmlDevice_t = c_xpumlDevice_t


class c_xpumlPciInfo_t(_PrintableStructure):
    _fields_: _ClassVar[list[tuple[str, type]]] = [
        ('domain', _ctypes.c_uint),
        ('bus', _ctypes.c_uint),
        ('device', _ctypes.c_uint),
        ('function', _ctypes.c_uint),
        ('pciDeviceId', _ctypes.c_uint),
        ('pciSubSystemId', _ctypes.c_uint),
        ('busId', _ctypes.c_char * XPUML_DEVICE_PCI_BUS_ID_BUFFER_SIZE),
        ('reserved', _ctypes.c_ulonglong * 9),
    ]


class c_xpumlUtilization_t(_PrintableStructure):
    _fields_: _ClassVar[list[tuple[str, type]]] = [
        ('xpu', _ctypes.c_uint),
        ('memory', _ctypes.c_uint),
        ('decode', _ctypes.c_uint),
        ('encode', _ctypes.c_uint),
        ('image', _ctypes.c_uint),
        ('reserved', _ctypes.c_uint * 27),
    ]

    @property
    def gpu(self) -> int:
        return int(self.xpu)


class c_xpumlMemory_t(_PrintableStructure):
    _fields_: _ClassVar[list[tuple[str, type]]] = [
        ('pageSizeGlobalMemory', _ctypes.c_ulonglong),
        ('totalGlobalMemory', _ctypes.c_ulonglong),
        ('freeGlobalMemory', _ctypes.c_ulonglong),
        ('usedGlobalMemory', _ctypes.c_ulonglong),
        ('pageSizeL3Memory', _ctypes.c_ulonglong),
        ('totalL3Memory', _ctypes.c_ulonglong),
        ('freeL3Memory', _ctypes.c_ulonglong),
        ('usedL3Memory', _ctypes.c_ulonglong),
        ('reserved_arr', _ctypes.c_ulonglong * 8),
    ]

    @property
    def total(self) -> int:
        return int(self.totalGlobalMemory)

    @property
    def free(self) -> int:
        return int(self.freeGlobalMemory)

    @property
    def used(self) -> int:
        return int(self.usedGlobalMemory)

    @property
    def reserved(self) -> int:
        return 0


class c_xpumlProcessInfo_t(_PrintableStructure):
    _fields_: _ClassVar[list[tuple[str, type]]] = [
        ('pid', _ctypes.c_uint),
        ('usedGlobalMemory', _ctypes.c_ulonglong),
        ('usedL3Memory', _ctypes.c_ulonglong),
        ('root_ns_pid', _ctypes.c_uint),
        ('reserved_u32', _ctypes.c_uint),
        ('reserved', _ctypes.c_ulonglong * 12),
    ]


c_nvmlProcessInfo_t = c_xpumlProcessInfo_t


class c_xpumlDeviceAttributes_t(_PrintableStructure):
    _fields_: _ClassVar[list[tuple[str, type]]] = [
        ('archId', _ctypes.c_int),
        ('boardId', _ctypes.c_int),
        ('modelId', _ctypes.c_int),
        ('clusterCount', _ctypes.c_uint),
        ('sdnnCount', _ctypes.c_uint),
        ('dmaEngineCount', _ctypes.c_uint),
        ('decoderCount', _ctypes.c_uint),
        ('encoderCount', _ctypes.c_uint),
        ('imgProcCount', _ctypes.c_uint),
        ('maxVFCount', _ctypes.c_uint),
        ('globalMemorySizeMB', _ctypes.c_ulonglong),
        ('l3MemorySizeMB', _ctypes.c_ulonglong),
        ('sn', _ctypes.c_ulonglong * 2),
        ('reserved', _ctypes.c_ulonglong * 7),
    ]


class c_xpumlXpuLinkInfo_t(_PrintableStructure):
    _fields_: _ClassVar[list[tuple[str, type]]] = [
        ('serverId', _ctypes.c_uint),
        ('c2cId', _ctypes.c_uint),
        ('topoType', _ctypes.c_uint),
    ]


class c_xpumlValue_t(_ctypes.Union):
    _fields_: _ClassVar[list[tuple[str, type]]] = [
        ('dVal', _ctypes.c_double),
        ('uiVal', _ctypes.c_uint),
        ('ulVal', _ctypes.c_ulong),
        ('ullVal', _ctypes.c_ulonglong),
        ('sllVal', _ctypes.c_longlong),
        ('siVal', _ctypes.c_int),
    ]


class c_xpumlFieldValue_t(_PrintableStructure):
    _fields_: _ClassVar[list[tuple[str, type]]] = [
        ('fieldId', _ctypes.c_uint),
        ('scopeId', _ctypes.c_uint),
        ('timestamp', _ctypes.c_longlong),
        ('latencyUsec', _ctypes.c_longlong),
        ('valueType', _ctypes.c_uint),
        ('nvmlReturn', _ctypes.c_uint),
        ('value', c_xpumlValue_t),
    ]


c_nvmlFieldValue_t = c_xpumlFieldValue_t


# Library loading and state management #############################################################

__libxpuml: _ctypes.CDLL | None = None
__lib_lock: _threading.Lock = _threading.Lock()
__func_pointer_cache: dict[str, _Any] = {}

__flags: list[int] = []
__initialized: bool = False
__lock: _threading.Lock = _threading.Lock()
__shutdown_condition: _threading.Condition = _threading.Condition()
__active_queries: int = 0
__shutting_down: bool = False
__atexit_registered: bool = False
_pynvml_installation_corrupted: bool = False

LOGGER: _logging.Logger = _logging.getLogger(__name__)
try:
    LOGGER.setLevel(_os.getenv('LOGLEVEL', default='WARNING').upper())
except (ValueError, TypeError):
    pass
if not LOGGER.hasHandlers() and LOGGER.isEnabledFor(_logging.DEBUG):
    _formatter = _logging.Formatter(
        '[%(levelname)s] %(asctime)s %(name)s::%(funcName)s: %(message)s',
    )
    _stream_handler = _logging.StreamHandler()
    _stream_handler.setFormatter(_formatter)
    _file_handler = _logging.FileHandler('xputop.log')
    _file_handler.setFormatter(_formatter)
    LOGGER.addHandler(_stream_handler)
    LOGGER.addHandler(_file_handler)
    del _formatter, _stream_handler, _file_handler

UNKNOWN_FUNCTIONS: dict[str, tuple[_Callable | str, NVMLError_FunctionNotFound]] = {}
UNKNOWN_FUNCTIONS_CACHE_SIZE: int = 1024
VERSIONED_PATTERN: _re.Pattern = _re.compile(r'^(?P<name>\w+)(?P<suffix>_v(\d)+)$')

_LIBXPUML_CANDIDATE_PATHS: tuple[str, ...] = (
    'libxpuml.so.1',
    'libxpuml.so',
    '/usr/lib/x86_64-linux-gnu/libxpuml.so.1',
    '/usr/lib64/libxpuml.so.1',
    '/usr/local/xpu/lib64/libxpuml.so.1',
    '/usr/local/xpu/lib/libxpuml.so.1',
)


def _load_xpuml_library() -> _ctypes.CDLL:
    """Load ``libxpuml.so.1`` from standard or environment-configured paths."""
    global __libxpuml  # pylint: disable=global-statement

    if __libxpuml is not None:
        return __libxpuml

    with __lib_lock:
        if __libxpuml is not None:
            return __libxpuml

        candidates: list[str] = []
        env_lib = _os.getenv('XPUML_LIBRARY_PATH')
        if env_lib:
            candidates.append(env_lib)
        candidates.extend(_LIBXPUML_CANDIDATE_PATHS)

        # Also check conda environment xcudart/lib if present
        conda_prefix = _os.getenv('CONDA_PREFIX') or _sys.prefix
        if conda_prefix:
            candidates.append(_os.path.join(conda_prefix, 'xcudart', 'lib', 'libxpuml.so.1'))
            candidates.append(_os.path.join(conda_prefix, 'lib', 'libxpuml.so.1'))

        for path in candidates:
            try:
                __libxpuml = _ctypes.CDLL(path)
                return __libxpuml
            except OSError:
                continue

        raise NVMLError_LibraryNotFound


def _nvmlGetFunctionPointer(name: str) -> _Any:
    """Get a function pointer from ``libxpuml.so.1``."""
    lib = _load_xpuml_library()
    try:
        return __func_pointer_cache[name]
    except KeyError:
        pass

    with __lib_lock:
        try:
            return __func_pointer_cache[name]
        except KeyError:
            try:
                fn = getattr(lib, name)
            except AttributeError as ex:
                raise NVMLError_FunctionNotFound from ex
            __func_pointer_cache[name] = fn
            return fn


def _nvmlCheckReturn(ret: int) -> None:
    if ret != XPUML_SUCCESS:
        raise NVMLError(ret)


def _lazy_init() -> None:
    """Lazily initialize the XPUML context."""
    global __atexit_registered  # pylint: disable=global-statement

    if __initialized or __shutting_down:
        return

    with __lock:
        if __initialized or __shutting_down:
            return

    nvmlInit()

    with __lock:
        if not __atexit_registered:
            _atexit.register(_atexit_shutdown, timeout=120.0)
            __atexit_registered = True


def _atexit_shutdown(timeout: float | None = None) -> None:
    """Wait for in-flight XPUML queries, then shutdown the XPUML context."""
    global __shutting_down  # pylint: disable=global-statement

    if __shutting_down:
        return

    with __shutdown_condition:
        if __shutting_down:
            return
        __shutting_down = True
        drained = __shutdown_condition.wait_for(lambda: __active_queries == 0, timeout=timeout)

    if drained:
        try:
            nvmlShutdown()
        except NVMLError:
            pass
    else:
        LOGGER.warning('Skipped `xpumlShutdown()` at exit: XPUML queries are still in flight.')


def _reset_after_fork() -> None:
    """Reset the XPUML shutdown-drain state in a forked child process."""
    global __lock, __shutdown_condition, __active_queries, __shutting_down  # pylint: disable=global-statement

    __lock = _threading.Lock()
    __shutdown_condition = _threading.Condition()
    __active_queries = 0
    __shutting_down = False


if hasattr(_os, 'register_at_fork'):
    _os.register_at_fork(after_in_child=_reset_after_fork)


def nvmlInit() -> None:
    """Initialize the XPUML context with default flag (0)."""
    nvmlInitWithFlags(0)


xpumlInit = nvmlInit


def nvmlInitWithFlags(flags: int) -> None:
    """Initialize the XPUML context with the given flags."""
    global __flags, __initialized  # pylint: disable=global-statement

    with __lock:
        if len(__flags) > 0 and flags == __flags[-1]:
            __initialized = True
            return

    try:
        fn = _nvmlGetFunctionPointer('xpumlInit')
        ret = fn()
        _nvmlCheckReturn(ret)
    except NVMLError_LibraryNotFound:
        message = (
            'FATAL ERROR: Kunlunxin XPU Management Library (libxpuml.so.1) not found.\n'
            'HINT: The Kunlunxin XPU Management Library ships with the Kunlunxin XPU driver / XRE\n'
            '      (typically at `/usr/lib/x86_64-linux-gnu/libxpuml.so.1`). You can also specify\n'
            '      its path via the `XPUML_LIBRARY_PATH` environment variable.'
        )
        for text, color, attrs in (
            ('FATAL ERROR:', 'red', ('bold',)),
            ('HINT:', 'yellow', ('bold',)),
        ):
            message = message.replace(text, __colored(text, color=color, attrs=attrs))

        LOGGER.critical(message)
        raise

    with __lock:
        __flags.append(flags)
        __initialized = True


xpumlInitWithFlags = nvmlInitWithFlags


def nvmlShutdown() -> None:
    """Shutdown the XPUML context."""
    global __flags, __initialized  # pylint: disable=global-statement

    fn = _nvmlGetFunctionPointer('xpumlShutdown')
    ret = fn()
    _nvmlCheckReturn(ret)
    with __lock:
        try:
            __flags.pop()
        except IndexError:
            pass
        __initialized = len(__flags) > 0


xpumlShutdown = nvmlShutdown


def nvmlQuery(
    func: _Callable[..., _Any] | str,
    /,
    *args: _Any,
    default: _Any = NA,
    ignore_errors: bool = True,
    ignore_function_not_found: bool = False,
    **kwargs: _Any,
) -> _Any:
    """Call a function with the given arguments from XPUML.

    The XPUML context will be automatically initialized.
    """
    global UNKNOWN_FUNCTIONS, __active_queries  # pylint: disable=global-statement

    if __shutting_down:
        if ignore_errors:
            return default
        raise NVMLError_Uninitialized

    with __shutdown_condition:
        if __shutting_down:
            if ignore_errors:
                return default
            raise NVMLError_Uninitialized
        __active_queries += 1

    try:
        _lazy_init()

        if __shutting_down:
            if ignore_errors:
                return default
            raise NVMLError_Uninitialized

        try:
            if isinstance(func, str):
                try:
                    if func.startswith('xpuml'):
                        alt_name = 'nvml' + func[5:]
                        func = getattr(__modself, func, getattr(__modself, alt_name, None))
                        if func is None:
                            raise AttributeError(func)
                    else:
                        func = getattr(__modself, func)
                except AttributeError as e1:
                    raise NVMLError_FunctionNotFound from e1

            try:
                retval = func(*args, **kwargs)
            except UnicodeDecodeError as e2:
                raise NVMLError_Unknown from e2
        except NVMLError_FunctionNotFound as e3:
            if not ignore_function_not_found:
                identifier = (
                    func
                    if isinstance(func, str)
                    else (_inspect.getsource(func) if func.__name__ == '<lambda>' else repr(func))
                )
                with __lock:
                    if (
                        identifier not in UNKNOWN_FUNCTIONS
                        and len(UNKNOWN_FUNCTIONS) < UNKNOWN_FUNCTIONS_CACHE_SIZE
                    ):
                        UNKNOWN_FUNCTIONS[identifier] = (func, e3)
                        LOGGER.exception(
                            'ERROR: A FunctionNotFound error occurred while calling %s.',
                            f'nvmlQuery({func!r}, *args, **kwargs)',
                        )
            if ignore_errors or ignore_function_not_found:
                return default
            raise
        except NVMLError:
            if ignore_errors:
                return default
            raise
    finally:
        with __shutdown_condition:
            __active_queries -= 1
            __shutdown_condition.notify_all()

    if isinstance(retval, bytes):
        retval = retval.decode('utf-8', errors='replace')
    return retval


xpumlQuery = nvmlQuery


def nvmlCheckReturn(retval: _Any, types: type | tuple[type, ...] | None = None, /) -> bool:
    """Check whether the return value is not :const:`xputop.NA` and is one of the given types."""
    if types is None:
        return retval != NA
    return retval != NA and isinstance(retval, types)


xpumlCheckReturn = nvmlCheckReturn


# XPUML / NVML Wrapper Functions ###################################################################


def nvmlSystemGetDriverVersion() -> str:
    """Retrieve the Kunlunxin KLRM driver version string (e.g., ``'5.0.21.45'``)."""
    c_version = _ctypes.create_string_buffer(XPUML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer('xpumlSystemGetDriverVersion')
    ret = fn(c_version, _ctypes.c_uint(XPUML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value.decode('utf-8', errors='replace')


xpumlSystemGetDriverVersion = nvmlSystemGetDriverVersion


def xpumlSystemGetXPUMLVersion() -> str:
    """Retrieve the XPUML version string (e.g., ``'11.515.58'``)."""
    c_version = _ctypes.create_string_buffer(XPUML_SYSTEM_XPUML_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer('xpumlSystemGetXPUMLVersion')
    ret = fn(c_version, _ctypes.c_uint(XPUML_SYSTEM_XPUML_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value.decode('utf-8', errors='replace')


nvmlSystemGetNVMLVersion = xpumlSystemGetXPUMLVersion


def nvmlSystemGetCudaDriverVersion() -> int:
    """Retrieve the XPU-RT version as an integer (e.g., ``10020`` for ``10.2``)."""
    c_version = _ctypes.c_int(0)
    try:
        fn = _nvmlGetFunctionPointer('nvmlSystemGetCudaDriverVersion_v2')
    except NVMLError_FunctionNotFound:
        fn = _nvmlGetFunctionPointer('nvmlSystemGetCudaDriverVersion')
    ret = fn(_ctypes.byref(c_version))
    _nvmlCheckReturn(ret)
    return c_version.value


nvmlSystemGetCudaDriverVersion_v2 = nvmlSystemGetCudaDriverVersion
xpumlSystemGetXpurtVersion = nvmlSystemGetCudaDriverVersion


def nvmlDeviceGetCount() -> int:
    """Retrieve the number of Kunlunxin XPU devices in the system."""
    c_count = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetCount')
    ret = fn(_ctypes.byref(c_count))
    _nvmlCheckReturn(ret)
    return int(c_count.value)


xpumlDeviceGetCount = nvmlDeviceGetCount


def nvmlDeviceGetHandleByIndex(index: int) -> c_xpumlDevice_t:
    """Acquire the handle for a particular XPU device based on its 0-based index."""
    c_index = _ctypes.c_uint(index)
    device = c_xpumlDevice_t()
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetHandleByIndex')
    ret = fn(c_index, _ctypes.byref(device))
    _nvmlCheckReturn(ret)
    return device


xpumlDeviceGetHandleByIndex = nvmlDeviceGetHandleByIndex


def nvmlDeviceGetHandleByPciBusId(pci_bus_id: str | bytes) -> c_xpumlDevice_t:
    """Acquire the handle for a particular XPU device based on its PCI bus ID."""
    if isinstance(pci_bus_id, str):
        pci_bus_id = pci_bus_id.encode('utf-8')
    device = c_xpumlDevice_t()
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetHandleByPciBusId')
    ret = fn(_ctypes.c_char_p(pci_bus_id), _ctypes.byref(device))
    _nvmlCheckReturn(ret)
    return device


xpumlDeviceGetHandleByPciBusId = nvmlDeviceGetHandleByPciBusId


def nvmlDeviceGetHandleByUUID(uuid: str | bytes) -> c_xpumlDevice_t:
    """Acquire the handle for a particular XPU device based on its UUID."""
    if isinstance(uuid, bytes):
        uuid_str = uuid.decode('utf-8', errors='replace')
    else:
        uuid_str = uuid

    # Try native nvmlDeviceGetHandleByUUID first, then fallback to iterating handles
    try:
        fn = _nvmlGetFunctionPointer('nvmlDeviceGetHandleByUUID')
        device = c_xpumlDevice_t()
        ret = fn(_ctypes.c_char_p(uuid_str.encode('utf-8')), _ctypes.byref(device))
        if ret == XPUML_SUCCESS:
            return device
    except NVMLError:
        pass

    count = nvmlDeviceGetCount()
    for index in range(count):
        handle = nvmlDeviceGetHandleByIndex(index)
        if nvmlDeviceGetUUID(handle) == uuid_str:
            return handle
    raise NVMLError_NotFound


xpumlDeviceGetHandleByUUID = nvmlDeviceGetHandleByUUID


def nvmlDeviceGetHandleBySerial(serial: str | bytes) -> c_xpumlDevice_t:
    """Acquire the handle for a particular XPU device based on its board serial number."""
    if isinstance(serial, bytes):
        serial_str = serial.decode('utf-8', errors='replace')
    else:
        serial_str = serial

    count = nvmlDeviceGetCount()
    for index in range(count):
        handle = nvmlDeviceGetHandleByIndex(index)
        if nvmlDeviceGetSerial(handle) == serial_str:
            return handle
    raise NVMLError_NotFound


xpumlDeviceGetHandleBySerial = nvmlDeviceGetHandleBySerial


def nvmlDeviceGetIndex(handle: c_xpumlDevice_t) -> int:
    """Retrieve the 0-based index of the XPU device."""
    c_index = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetIndex')
    ret = fn(handle, _ctypes.byref(c_index))
    _nvmlCheckReturn(ret)
    return int(c_index.value)


xpumlDeviceGetIndex = nvmlDeviceGetIndex


def nvmlDeviceGetName(handle: c_xpumlDevice_t) -> str:
    """Retrieve the product name of the XPU device (e.g., ``'P800 OAM'``)."""
    c_name = _ctypes.create_string_buffer(XPUML_DEVICE_NAME_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetName')
    ret = fn(handle, c_name, _ctypes.c_uint(XPUML_DEVICE_NAME_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_name.value.decode('utf-8', errors='replace')


xpumlDeviceGetName = nvmlDeviceGetName


def nvmlDeviceGetUUID(handle: c_xpumlDevice_t) -> str:
    """Retrieve the globally unique immutable UUID of the XPU device."""
    c_uuid = _ctypes.create_string_buffer(XPUML_DEVICE_UUID_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetUUID')
    ret = fn(handle, c_uuid, _ctypes.c_uint(XPUML_DEVICE_UUID_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_uuid.value.decode('utf-8', errors='replace')


xpumlDeviceGetUUID = nvmlDeviceGetUUID


def nvmlDeviceGetSerial(handle: c_xpumlDevice_t) -> str:
    """Retrieve the globally unique board serial number of the XPU device."""
    c_serial = _ctypes.create_string_buffer(XPUML_DEVICE_SERIAL_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetSerial')
    ret = fn(handle, c_serial, _ctypes.c_uint(XPUML_DEVICE_SERIAL_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_serial.value.decode('utf-8', errors='replace')


xpumlDeviceGetSerial = nvmlDeviceGetSerial


def nvmlDeviceGetMinorNumber(handle: c_xpumlDevice_t) -> int:
    """Retrieve the minor number for the device (``/dev/xpu<minor>``)."""
    c_minor = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetMinorNumber')
    ret = fn(handle, _ctypes.byref(c_minor))
    _nvmlCheckReturn(ret)
    return int(c_minor.value)


xpumlDeviceGetMinorNumber = nvmlDeviceGetMinorNumber


def nvmlDeviceGetBoardId(handle: c_xpumlDevice_t) -> int:
    """Retrieve the device board ID."""
    c_board_id = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetBoardId')
    ret = fn(handle, _ctypes.byref(c_board_id))
    _nvmlCheckReturn(ret)
    return int(c_board_id.value)


xpumlDeviceGetBoardId = nvmlDeviceGetBoardId


def nvmlDeviceGetOamId(handle: c_xpumlDevice_t) -> int:
    """Retrieve the OAM module ID of the XPU device."""
    c_oam_id = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetOamId')
    ret = fn(handle, _ctypes.byref(c_oam_id))
    _nvmlCheckReturn(ret)
    return int(c_oam_id.value)


xpumlDeviceGetOamId = nvmlDeviceGetOamId


def nvmlDeviceGetArchitecture(handle: c_xpumlDevice_t) -> int:
    """Retrieve the architecture ID of the XPU device (e.g., 300 for KL3)."""
    c_arch = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetArchitecture')
    ret = fn(handle, _ctypes.byref(c_arch))
    _nvmlCheckReturn(ret)
    return int(c_arch.value)


xpumlDeviceGetArchitecture = nvmlDeviceGetArchitecture


def nvmlDeviceGetState(handle: c_xpumlDevice_t) -> int:
    """Retrieve the operating state of the XPU device (e.g., 201 for RUNNING)."""
    c_state = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetState')
    ret = fn(handle, _ctypes.byref(c_state))
    _nvmlCheckReturn(ret)
    return int(c_state.value)


xpumlDeviceGetState = nvmlDeviceGetState


def nvmlDeviceGetHostVxpuMode(handle: c_xpumlDevice_t) -> int:
    """Retrieve the host vXPU (SR-IOV) mode of the XPU device."""
    c_mode = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetHostVxpuMode')
    ret = fn(handle, _ctypes.byref(c_mode))
    _nvmlCheckReturn(ret)
    return int(c_mode.value)


xpumlDeviceGetHostVxpuMode = nvmlDeviceGetHostVxpuMode


def nvmlDeviceGetPciInfo(handle: c_xpumlDevice_t) -> FriendlyObject:
    """Retrieve the PCI attributes of the XPU device."""
    c_pci = c_xpumlPciInfo_t()
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetPciInfo')
    ret = fn(handle, _ctypes.byref(c_pci))
    _nvmlCheckReturn(ret)
    return nvmlStructToFriendlyObject(c_pci)


xpumlDeviceGetPciInfo = nvmlDeviceGetPciInfo


def nvmlDeviceGetMemoryInfo(handle: c_xpumlDevice_t) -> c_xpumlMemory_t:
    """Retrieve the global and L3 memory usage information (in bytes) for the XPU device."""
    c_memory = c_xpumlMemory_t()
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetMemoryInfo')
    ret = fn(handle, _ctypes.byref(c_memory))
    _nvmlCheckReturn(ret)
    return c_memory


xpumlDeviceGetMemoryInfo = nvmlDeviceGetMemoryInfo


def nvmlDeviceGetBAR1MemoryInfo(handle: c_xpumlDevice_t) -> FriendlyObject:
    """BAR1 memory info is not supported on Kunlunxin XPU."""
    raise NVMLError_NotSupported


def nvmlDeviceGetUtilizationRates(handle: c_xpumlDevice_t) -> c_xpumlUtilization_t:
    """Retrieve the current utilization rates (xpu, memory, decode, encode, image) for the XPU."""
    c_util = c_xpumlUtilization_t()
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetUtilizationRates')
    ret = fn(handle, _ctypes.byref(c_util))
    _nvmlCheckReturn(ret)
    return c_util


xpumlDeviceGetUtilizationRates = nvmlDeviceGetUtilizationRates


def nvmlDeviceGetEncoderUtilization(handle: c_xpumlDevice_t) -> list[int]:
    """Retrieve encoder utilization from xpumlUtilization_t."""
    util = nvmlDeviceGetUtilizationRates(handle)
    return [int(util.encode), 1000000]


def nvmlDeviceGetDecoderUtilization(handle: c_xpumlDevice_t) -> list[int]:
    """Retrieve decoder utilization from xpumlUtilization_t."""
    util = nvmlDeviceGetUtilizationRates(handle)
    return [int(util.decode), 1000000]


def nvmlDeviceGetClockInfo(handle: c_xpumlDevice_t, clock_type: int = XPUML_CLOCK_XPU) -> int:
    """Retrieve the clock speed in MHz for the specified clock domain.

    On Kunlunxin XPU:
    - ``NVML_CLOCK_GRAPHICS`` (0), ``NVML_CLOCK_SM`` (1), ``NVML_CLOCK_CLUSTER`` (4) -> Cluster clock (MHz)
    - ``NVML_CLOCK_MEM`` (2), ``NVML_CLOCK_CDNN`` (5) -> CDNN / Memory clock (MHz)
    - ``NVML_CLOCK_VIDEO`` (3) -> Video clock (MHz)
    """
    c_clock = _ctypes.c_uint(0)
    if clock_type in (NVML_CLOCK_GRAPHICS, NVML_CLOCK_SM, NVML_CLOCK_CLUSTER):
        fn = _nvmlGetFunctionPointer('xpumlDeviceGetClockInfo')
        ret = fn(handle, _ctypes.c_uint(0), _ctypes.byref(c_clock))
        _nvmlCheckReturn(ret)
        return int(c_clock.value)
    if clock_type in (NVML_CLOCK_MEM, NVML_CLOCK_CDNN):
        try:
            fn = _nvmlGetFunctionPointer('nvmlDeviceGetClockInfo')
            ret = fn(handle, _ctypes.c_uint(5), _ctypes.byref(c_clock))
            if ret == XPUML_SUCCESS:
                return int(c_clock.value)
        except NVMLError:
            pass
        fn = _nvmlGetFunctionPointer('xpumlDeviceGetClockInfo')
        ret = fn(handle, _ctypes.c_uint(0), _ctypes.byref(c_clock))
        _nvmlCheckReturn(ret)
        return int(c_clock.value)
    if clock_type == NVML_CLOCK_VIDEO:
        try:
            fn = _nvmlGetFunctionPointer('nvmlDeviceGetClockInfo')
            ret = fn(handle, _ctypes.c_uint(3), _ctypes.byref(c_clock))
            _nvmlCheckReturn(ret)
            return int(c_clock.value)
        except NVMLError:
            raise NVMLError_NotSupported from None

    fn = _nvmlGetFunctionPointer('xpumlDeviceGetClockInfo')
    ret = fn(handle, _ctypes.c_uint(clock_type), _ctypes.byref(c_clock))
    _nvmlCheckReturn(ret)
    return int(c_clock.value)


xpumlDeviceGetClockInfo = nvmlDeviceGetClockInfo


def nvmlDeviceGetMaxClockInfo(handle: c_xpumlDevice_t, clock_type: int) -> int:
    """Maximum clock info (returns current clock if max clock is not supported)."""
    c_clock = _ctypes.c_uint(0)
    try:
        fn = _nvmlGetFunctionPointer('nvmlDeviceGetMaxClockInfo')
        ret = fn(handle, _ctypes.c_uint(clock_type), _ctypes.byref(c_clock))
        if ret == XPUML_SUCCESS:
            return int(c_clock.value)
    except NVMLError:
        pass
    raise NVMLError_NotSupported


def nvmlDeviceGetTemperature(
    handle: c_xpumlDevice_t,
    sensor: int = XPUML_TEMPERATURE_XPU,
) -> int:
    """Retrieve the current core temperature (in degrees C) for the XPU device."""
    c_temp = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetTemperature')
    ret = fn(handle, _ctypes.c_uint(sensor), _ctypes.byref(c_temp))
    _nvmlCheckReturn(ret)
    return int(c_temp.value)


xpumlDeviceGetTemperature = nvmlDeviceGetTemperature


def nvmlDeviceGetTemperatureThreshold(handle: c_xpumlDevice_t, threshold_type: int) -> int:
    """Retrieve the temperature threshold (in degrees C) for the XPU device."""
    c_temp = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetTemperatureThreshold')
    ret = fn(handle, _ctypes.c_uint(threshold_type), _ctypes.byref(c_temp))
    _nvmlCheckReturn(ret)
    return int(c_temp.value)


xpumlDeviceGetTemperatureThreshold = nvmlDeviceGetTemperatureThreshold


def nvmlDeviceGetFanSpeed(handle: c_xpumlDevice_t) -> int:
    """Retrieve the intended fan speed percentage (often N/A on passive OAM modules)."""
    c_speed = _ctypes.c_uint(0)
    try:
        fn = _nvmlGetFunctionPointer('nvmlDeviceGetFanSpeed')
    except NVMLError_FunctionNotFound:
        raise NVMLError_NotSupported from None
    ret = fn(handle, _ctypes.byref(c_speed))
    _nvmlCheckReturn(ret)
    return int(c_speed.value)


def nvmlDeviceGetPowerManagementLimit(handle: c_xpumlDevice_t) -> int:
    """Retrieve the power management limit in milliwatts (mW)."""
    c_limit = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetPowerManagementLimit')
    ret = fn(handle, _ctypes.byref(c_limit))
    _nvmlCheckReturn(ret)
    return int(c_limit.value)


xpumlDeviceGetPowerManagementLimit = nvmlDeviceGetPowerManagementLimit


def nvmlDeviceGetPowerUsage(handle: c_xpumlDevice_t) -> int:
    """Retrieve power usage for this XPU in milliwatts (mW).

    Note:
        In ``libxpuml.so.1``, ``xpumlDeviceGetPowerUsage`` divides the underlying mW value by 1000
        and returns Watts (e.g., 400 for 400W), and ``xpu-smi`` clamps the displayed power to the
        enforced power limit (400W). We convert Watts back to milliwatts and clamp to the power
        limit so ``power_usage()`` is in mW and matches ``xpu-smi`` exactly.
    """
    c_power = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetPowerUsage')
    ret = fn(handle, _ctypes.byref(c_power))
    _nvmlCheckReturn(ret)
    power_mw = int(c_power.value) * 1000
    try:
        limit_mw = nvmlDeviceGetPowerManagementLimit(handle)
        if limit_mw > 0 and power_mw > limit_mw:
            power_mw = limit_mw
    except NVMLError:
        pass
    return power_mw


xpumlDeviceGetPowerUsage = nvmlDeviceGetPowerUsage


def nvmlDeviceGetEccMode(handle: c_xpumlDevice_t) -> tuple[int, int]:
    """Retrieve the current and pending ECC modes for the XPU device."""
    c_curr = _ctypes.c_uint(0)
    c_pend = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetEccMode')
    ret = fn(handle, _ctypes.byref(c_curr), _ctypes.byref(c_pend))
    _nvmlCheckReturn(ret)
    return (int(c_curr.value), int(c_pend.value))


xpumlDeviceGetEccMode = nvmlDeviceGetEccMode


def nvmlDeviceGetTotalEccErrors(
    handle: c_xpumlDevice_t,
    error_type: int = XPUML_MEMORY_ERROR_TYPE_UNCORRECTED,
    counter_type: int = XPUML_VOLATILE_ECC,
) -> int:
    """Retrieve the total ECC error count for the XPU device."""
    c_count = _ctypes.c_ulonglong(0)
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetTotalEccErrors')
    ret = fn(handle, _ctypes.c_uint(error_type), _ctypes.c_uint(counter_type), _ctypes.byref(c_count))
    _nvmlCheckReturn(ret)
    return int(c_count.value)


xpumlDeviceGetTotalEccErrors = nvmlDeviceGetTotalEccErrors


def nvmlDeviceGetComputeMode(handle: c_xpumlDevice_t) -> int:
    """Retrieve the current compute mode for the XPU device."""
    c_mode = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('nvmlDeviceGetComputeMode')
    ret = fn(handle, _ctypes.byref(c_mode))
    _nvmlCheckReturn(ret)
    return int(c_mode.value)


def nvmlDeviceGetPersistenceMode(handle: c_xpumlDevice_t) -> int:
    """Persistence mode is reported as N/A on Kunlunxin XPU (matching ``xpu-smi``)."""
    raise NVMLError_NotSupported


def nvmlDeviceGetPerformanceState(handle: c_xpumlDevice_t) -> int:
    """Retrieve the current performance state for the XPU device."""
    c_pstate = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('nvmlDeviceGetPerformanceState')
    ret = fn(handle, _ctypes.byref(c_pstate))
    _nvmlCheckReturn(ret)
    return int(c_pstate.value)


def nvmlDeviceGetDisplayActive(handle: c_xpumlDevice_t) -> int:
    """Retrieve whether a display is active on the device."""
    c_active = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('nvmlDeviceGetDisplayActive')
    ret = fn(handle, _ctypes.byref(c_active))
    _nvmlCheckReturn(ret)
    return int(c_active.value)


def nvmlDeviceGetDisplayMode(handle: c_xpumlDevice_t) -> int:
    """Retrieve whether a physical display is connected to the device."""
    c_mode = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('nvmlDeviceGetDisplayMode')
    ret = fn(handle, _ctypes.byref(c_mode))
    _nvmlCheckReturn(ret)
    return int(c_mode.value)


def nvmlDeviceGetCurrentDriverModel(handle: c_xpumlDevice_t) -> int:
    """Driver model is not supported on Linux Kunlunxin XPU."""
    raise NVMLError_NotSupported


def nvmlDeviceGetCurrPcieLinkGeneration(handle: c_xpumlDevice_t) -> int:
    """Retrieve the current PCIe link generation."""
    c_gen = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('nvmlDeviceGetCurrPcieLinkGeneration')
    ret = fn(handle, _ctypes.byref(c_gen))
    _nvmlCheckReturn(ret)
    return int(c_gen.value)


def nvmlDeviceGetMaxPcieLinkGeneration(handle: c_xpumlDevice_t) -> int:
    """Retrieve the maximum PCIe link generation."""
    c_gen = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('nvmlDeviceGetMaxPcieLinkGeneration')
    ret = fn(handle, _ctypes.byref(c_gen))
    _nvmlCheckReturn(ret)
    return int(c_gen.value)


def nvmlDeviceGetCurrPcieLinkWidth(handle: c_xpumlDevice_t) -> int:
    """Retrieve the current PCIe link width."""
    c_width = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('nvmlDeviceGetCurrPcieLinkWidth')
    ret = fn(handle, _ctypes.byref(c_width))
    _nvmlCheckReturn(ret)
    return int(c_width.value)


def nvmlDeviceGetMaxPcieLinkWidth(handle: c_xpumlDevice_t) -> int:
    """Retrieve the maximum PCIe link width."""
    c_width = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('nvmlDeviceGetMaxPcieLinkWidth')
    ret = fn(handle, _ctypes.byref(c_width))
    _nvmlCheckReturn(ret)
    return int(c_width.value)


def nvmlDeviceGetPcieThroughput(handle: c_xpumlDevice_t, counter: int) -> int:
    """Retrieve PCIe utilization counter."""
    c_tput = _ctypes.c_uint(0)
    fn = _nvmlGetFunctionPointer('nvmlDeviceGetPcieThroughput')
    ret = fn(handle, _ctypes.c_uint(counter), _ctypes.byref(c_tput))
    _nvmlCheckReturn(ret)
    return int(c_tput.value)


def nvmlDeviceGetCudaComputeCapability(handle: c_xpumlDevice_t) -> tuple[int, int]:
    """Retrieve the compute capability version ``(major, minor)`` (e.g., ``(3, 0)`` for KL3)."""
    c_major = _ctypes.c_int(0)
    c_minor = _ctypes.c_int(0)
    fn = _nvmlGetFunctionPointer('nvmlDeviceGetCudaComputeCapability')
    ret = fn(handle, _ctypes.byref(c_major), _ctypes.byref(c_minor))
    _nvmlCheckReturn(ret)
    return (int(c_major.value), int(c_minor.value))


def xpumlDeviceGetFwVersion(handle: c_xpumlDevice_t, obj: int) -> str:
    """Retrieve firmware version (102=PBL, 103=PCIE, 104=SBL)."""
    c_ver = _ctypes.create_string_buffer(XPUML_DEVICE_INFOROM_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer('nvmlDeviceGetInforomVersion')
    ret = fn(handle, _ctypes.c_uint(obj), c_ver, _ctypes.c_uint(XPUML_DEVICE_INFOROM_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_ver.value.decode('utf-8', errors='replace')


def nvmlDeviceIsMigDeviceHandle(handle: c_xpumlDevice_t) -> bool:
    """Return whether the device handle is a MIG device handle."""
    return False


def nvmlDeviceGetMigMode(handle: c_xpumlDevice_t) -> tuple[int, int]:
    """MIG mode is not enabled by default on Kunlunxin XPU."""
    raise NVMLError_NotSupported


def nvmlDeviceGetMaxMigDeviceCount(handle: c_xpumlDevice_t) -> int:
    """Return 0 for MIG device count."""
    return 0


def nvmlDeviceGetComputeRunningProcesses(handle: c_xpumlDevice_t) -> list[FriendlyObject]:
    """Get information about processes with a compute context on an XPU device."""
    fn = _nvmlGetFunctionPointer('xpumlDeviceGetComputeRunningProcesses')
    max_count = XPUML_DEVICE_MAX_PROCESS_COUNT
    c_count = _ctypes.c_uint(max_count)
    c_procs = (c_xpumlProcessInfo_t * max_count)()

    ret = fn(handle, _ctypes.byref(c_count), c_procs)
    if ret == XPUML_ERROR_INSUFFICIENT_SIZE:
        max_count = max(int(c_count.value) * 2 + 5, XPUML_DEVICE_MAX_PROCESS_COUNT * 2)
        c_count = _ctypes.c_uint(max_count)
        c_procs = (c_xpumlProcessInfo_t * max_count)()
        ret = fn(handle, _ctypes.byref(c_count), c_procs)

    _nvmlCheckReturn(ret)

    processes: list[FriendlyObject] = []
    for i in range(c_count.value):
        proc = c_procs[i]
        used_mem: int | None = int(proc.usedGlobalMemory)
        if used_mem == ULONGLONG_MAX:
            used_mem = None
        used_l3: int | None = int(proc.usedL3Memory)
        if used_l3 == ULONGLONG_MAX:
            used_l3 = None
        processes.append(
            FriendlyObject(
                {
                    'pid': int(proc.pid),
                    'usedGpuMemory': used_mem,
                    'usedGlobalMemory': used_mem,
                    'usedL3Memory': used_l3,
                    'root_ns_pid': int(proc.root_ns_pid),
                    'gpuInstanceId': UINT_MAX,
                    'computeInstanceId': UINT_MAX,
                },
            ),
        )
    return processes


xpumlDeviceGetComputeRunningProcesses = nvmlDeviceGetComputeRunningProcesses


def nvmlDeviceGetGraphicsRunningProcesses(handle: c_xpumlDevice_t) -> list[FriendlyObject]:
    """Kunlunxin XPU does not have separate graphics processes."""
    return []


def nvmlDeviceGetMPSComputeRunningProcesses(handle: c_xpumlDevice_t) -> list[FriendlyObject]:
    """Kunlunxin XPU does not have separate MPS processes."""
    return []


def nvmlDeviceGetProcessUtilization(
    handle: c_xpumlDevice_t,
    last_seen_timestamp: int = 0,
) -> list[FriendlyObject]:
    """Per-process SM utilization is not supported by Kunlunxin XPU driver."""
    raise NVMLError_NotSupported


def nvmlQueryFieldValues(
    handle: c_xpumlDevice_t,
    field_ids: list[int | tuple[int, int]],
) -> list[tuple[float | int | NaType, int]]:
    """Field value queries are not supported on Kunlunxin XPU; return NA."""
    timestamp = _time.time_ns() // 1000
    return [(NA, timestamp) for _ in range(len(field_ids))]


# Export all public symbols
__all__ = [
    'NA',
    'UINT_MAX',
    'ULONGLONG_MAX',
    'LOGGER',
    'UNKNOWN_FUNCTIONS',
    'VERSIONED_PATTERN',
    'FriendlyObject',
    'NVMLError',
    'XPUMLError',
    'nvmlExceptionClass',
    'nvmlCheckReturn',
    'xpumlCheckReturn',
    'nvmlInit',
    'xpumlInit',
    'nvmlInitWithFlags',
    'xpumlInitWithFlags',
    'nvmlQuery',
    'xpumlQuery',
    'nvmlQueryFieldValues',
    'nvmlShutdown',
    'xpumlShutdown',
    'c_nvmlDevice_t',
    'c_xpumlDevice_t',
    'c_nvmlProcessInfo_t',
    'c_xpumlProcessInfo_t',
    'c_xpumlMemory_t',
    'c_xpumlUtilization_t',
    'c_xpumlPciInfo_t',
]

for _symbol_name, _symbol_val in list(globals().items()):
    if _symbol_name.startswith(('NVML_', 'XPUML_', 'NVMLError_', 'XPUMLError_')) or (
        _symbol_name.startswith(('nvml', 'xpuml')) and isinstance(_symbol_val, _FunctionType)
    ):
        if _symbol_name not in __all__:
            __all__.append(_symbol_name)


class _CustomModule(_ModuleType):
    """Module type supporting context manager (`with libxpuml:`)."""

    def __enter__(self) -> _Self:
        _lazy_init()
        return self

    def __exit__(self, *exc: object) -> None:
        try:
            nvmlShutdown()
        except NVMLError:
            pass


__modself = _sys.modules[__name__]
__modself.__class__ = _CustomModule
