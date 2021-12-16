"""Generic utils."""
from pathlib import Path

import pkg_resources


def resource_path(path):
    """Return the absolute path of a resource.

    Args:
        path (str): path of the resource relative to the package root.

    Returns:
        The absolute path.
    """
    return Path(pkg_resources.resource_filename(__package__, path)).resolve()


def filter_ids(df, query):
    """Given a dataframe and a query, return the filtered ids from the index.

    Args:
        df (pd.DataFrame): DataFrame to be filtered.
        query (str|dict): query given as a string or dict.
            Examples (str):
                'mtype=="SO_BP" & etype=="cNAC"'
                'mtype == ["SO_BP", "SP_AA"]'
            Examples (dict):
                {"mtype": "SO_BP", "etype": "cNAC"}
                {"mtype": ["SO_BP", "SP_AA"]}

    Returns:
        np.array of filtered ids.
    """
    if isinstance(query, str):
        return df.query(query).index.to_numpy()
    elif isinstance(query, dict):
        # ensure that all the values are lists
        query = {k: v if isinstance(v, list) else [v] for k, v in query.items()}
        return df.index[df[list(query)].isin(query).all("columns")].to_numpy()
    else:
        raise ValueError(f"Unsupported query type: {type(query)}")
