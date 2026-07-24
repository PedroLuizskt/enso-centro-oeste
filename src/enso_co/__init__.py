"""
enso_co - Pipeline de teleconexao ENSO x clima do Centro-Oeste do Brasil.

Cruza indices da NOAA/CPC (RONI, ONI, SOI) com precipitacao (CHIRPS) e
temperatura (ERA5-Land) extraidas via Google Earth Engine, no nivel municipal,
e gera um dashboard WebMap autonomo (index.html).
"""

from .config import Config

__version__ = "0.5.1"
__all__ = ["Config"]
