import sqlite3
from collections import OrderedDict

from ..units import Units
from . import get_config

RESULTS_TABLES = {
    "v_flux_indicator_aggregates": "flux_tc",
    "v_flux_indicators": "flux_tc",
    "v_pool_indicators": "pool_tc",
    "v_stock_change_indicators": "flux_tc",
}


def _get_simulation_years(conn):
    years = conn.execute(
        "SELECT MIN(year), MAX(year) from v_age_indicators").fetchone()

    return years


def _find_indicator_table(conn, indicator):
    for table, value_col in RESULTS_TABLES.items():
        if conn.execute(f"SELECT 1 FROM {table} WHERE indicator = ?", [indicator]).fetchone():
            return table, value_col

    return None, None


def _get_annual_result(conn, indicator, units=Units.Tc):
    table, value_col = _find_indicator_table(conn, indicator)
    _, units_tc, _ = units.value
    start_year, end_year = _get_simulation_years(conn)

    db_result = conn.execute(
        f"""
            SELECT years.year, COALESCE(SUM(i.{value_col}), 0) / {units_tc} AS value
            FROM (SELECT DISTINCT year FROM v_age_indicators ORDER BY year) AS years
            LEFT JOIN {table} i
                ON years.year = i.year
            WHERE i.indicator = '{indicator}'
                AND (years.year BETWEEN {start_year} AND {end_year})
            GROUP BY years.year
            ORDER BY years.year
            """).fetchall()

    data = OrderedDict()
    for year, value in db_result:
        data[str(year)] = value

    return data


def get_metadata(db_results):
    """Extract all metadata from non-spatial DB.

    Args:
        db_results: Path to SQLite DB with non-spatial data.

    Returns:
        A dict mapping keys to year-wise values of an indicator.
    """
    metadata = {}
    conn = sqlite3.connect(db_results)
    for c in get_config():
        indicator = c['database_indicator']
        metadata[indicator] = _get_annual_result(conn, indicator)
    return metadata