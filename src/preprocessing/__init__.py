"""Preprocessing scripts that turn raw BrainVision + behavioral Excel inputs
into ``data/results/exp{1,2,3}_u2erp.json``."""

from .preprocess_exp1 import main as preprocess_exp1
from .preprocess_exp2 import main as preprocess_exp2
from .preprocess_exp3 import main as preprocess_exp3

__all__ = ["preprocess_exp1", "preprocess_exp2", "preprocess_exp3"]
