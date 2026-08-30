"""data — нормализованные входные данные (именованные коллекции) генератора D2.

Public API (см. `contracts.yaml` §2 + `architecture.md` §2.2):
    from data.models import Record, Project, Task, DataValidationError
    from data.sample_data import get_rows, get_collections
"""

from data.models import DataValidationError, Project, Record, Task
from data.sample_data import get_collections, get_rows

__all__ = [
    "DataValidationError",
    "Project",
    "Record",
    "Task",
    "get_collections",
    "get_rows",
]
