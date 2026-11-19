# liquidez_masiva/core/utils.py
"""
Utilidades transversales: clamps, división segura, escritura atómica.
Todas las funciones son puras o casi-puras; thread-safe por construcción.
"""
from __future__ import annotations

import math
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


def _is_nan(x: object) -> bool:
    """True si x es float('nan') (no confunde con None ni con tipos no-float)."""
    return isinstance(x, float) and math.isnan(x)


def clamp(x: float, lo: float, hi: float) -> float:
    """Recorta x al intervalo [lo, hi]. NUNCA lanza."""
    if x is None:
        return lo
    return max(lo, min(hi, x))


def safe_div(a: Optional[float], b: Optional[float],
             default: Optional[float] = None) -> Optional[float]:
    """División segura: retorna default si b≈0 o si algún operando es None/NaN."""
    if a is None or b is None or _is_nan(a) or _is_nan(b):
        return default
    if abs(b) < 1e-12:
        return default
    return a / b


@contextmanager
def atomic_write(path: Path):
    """
    Escritura atómica (texto): escribe a un fichero temporal y renombra al final.
    Evita que dos procesos (Streamlit + CI) corrompan el destino.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            yield f
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


@contextmanager
def atomic_write_binary(path: Path):
    """Variante binaria de atomic_write (para Parquet/CSV binario futuro)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    os.close(fd)
    try:
        with open(tmp, "wb") as f:
            yield f
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def fmt_pct(x: Optional[float], digits: int = 2) -> str:
    """Formatea un porcentaje para reportes. None/NaN → 'N/D'."""
    if x is None or _is_nan(x):
        return "N/D"
    return f"{x * 100:.{digits}f}%"


def fmt_num(x: Optional[float], digits: int = 3) -> str:
    """Formatea un número. None/NaN → 'N/D'."""
    if x is None or _is_nan(x):
        return "N/D"
    return f"{x:.{digits}f}"