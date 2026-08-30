# Это fixture-данные, не тесты: pytest не должен собирать файлы из этой директории.
collect_ignore = ["config.json"]

# Также игнорируем любые .py внутри поддиректорий fixtures.
import pathlib as _pl

for _p in _pl.Path(__file__).parent.rglob("*.py"):
    collect_ignore.append(str(_p.relative_to(_pl.Path(__file__).parent)))