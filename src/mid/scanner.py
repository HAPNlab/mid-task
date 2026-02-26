"""
Scanner backend abstraction and PulseCounter.

ScannerBackend – protocol implemented by:
  HardwareBackend  – real MCC DAQ counter board
  EmulatedBackend  – software TR clock for development without scanner hardware

PulseCounter – wait/drain logic built on top of a backend; agnostic to which.
"""
from __future__ import annotations

from typing import Protocol

from mid import config


class ScannerBackend(Protocol):
    """Low-level scanner interface: absolute pulse count and pulses-per-TR."""

    pulse_rate: int

    def read(self) -> int:
        """Return current absolute pulse count (monotonically increasing)."""
        ...

    def start(self) -> None:
        """Signal that the scan has started. No-op for hardware backends."""
        ...


class HardwareBackend:
    """MCC DAQ counter board backend."""

    pulse_rate: int = config.SCANNER_PULSE_RATE

    def __init__(self) -> None:
        try:
            from mcculw import ul
            from mcculw.device_info import DaqDeviceInfo
        except Exception as exc:
            raise RuntimeError(
                "mcculw unavailable (Windows-only DAQ library). "
                "Run without fmri=True or use EmulatedBackend for testing."
            ) from exc
        self._board_num = config.BOARD_NUM
        ctr_info = DaqDeviceInfo(self._board_num).get_ctr_info()
        self._counter_num = ctr_info.chan_info[0].channel_num
        self._ul = ul

    def read(self) -> int:
        return self._ul.c_in_32(self._board_num, self._counter_num)

    def start(self) -> None:
        pass


class EmulatedBackend:
    """Software TR clock for development without scanner hardware.

    read() returns a virtual pulse count that increases at pulse_rate per TR,
    starting from when start() is called.  Before start() it returns 0.
    """

    pulse_rate: int = config.SCANNER_PULSE_RATE

    def __init__(self) -> None:
        self._emu_start: float | None = None

    def start(self) -> None:
        """Record scan start time. Call immediately after the start signal."""
        from time import perf_counter
        self._emu_start = perf_counter()

    def read(self) -> int:
        if self._emu_start is None:
            return 0
        from time import perf_counter
        elapsed = perf_counter() - self._emu_start
        tr_s = config.MR_SETTINGS["TR"]
        return int(elapsed / tr_s * self.pulse_rate)


def make_backend(fmri: bool) -> ScannerBackend:
    """Return HardwareBackend for fmri runs, EmulatedBackend otherwise."""
    if fmri:
        return HardwareBackend()
    return EmulatedBackend()


class PulseCounter:
    """
    Counts TR pulses using a ScannerBackend.

    All hardware and emulation logic lives in the backend.  PulseCounter
    contains only the wait/drain logic built on backend.read() and
    backend.pulse_rate.
    """

    def __init__(self, backend: ScannerBackend) -> None:
        self._backend = backend
        self._last = backend.read()

    def wait_for_start(self) -> None:
        """Block until the first TR pulse is detected (polls backend.read())."""
        from time import sleep
        while self._backend.read() == self._last:
            sleep(0.001)
        self._last = self._backend.read()

    def drain(self) -> int:
        """Return pulses accumulated since the last call without blocking."""
        curr = self._backend.read()
        delta = max(0, curr - self._last)
        self._last = curr
        return delta

    def wait_for_tr(self) -> int:
        """Block until pulse_rate more pulses have arrived (one TR), return delta."""
        from time import sleep
        target = self._last + self._backend.pulse_rate
        while self._backend.read() < target:
            sleep(0.001)
        curr = self._backend.read()
        delta = curr - self._last
        self._last = curr
        return delta
