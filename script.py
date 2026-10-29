import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def read_log_file(file_path: Path) -> tuple[str, str]:
    """Read a log file and return its content and encoding."""
    try:
        # Try to read the file with UTF-8
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return content, "utf-8"
    except UnicodeDecodeError:
        # If decoding with UTF-8 fails, try Latin-1
        with open(file_path, "r", encoding="latin-1") as file:
            content = file.read()
        return content, "latin-1"


def parse_log(text: str) -> list[dict[str, str | float]]:
    """Extract valid transactions from log text."""
    pattern = (
        r"\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]"
        r" \[(?P<register_id>POS_\d+)\]"
        r" item=(?P<item>\w+)"
        r" price=(?P<price>\d+\.\d{2})"
        r" (?P<currency>EUR|NOK|USD)"
        r" \((?P<status>SUCCESS|REFUND|CANCELLED)\)"
    )

    transactions = []

    for line in text.splitlines():
        match = re.fullmatch(pattern, line.strip())

        if match:
            transaction = {
                "timestamp": match.group("timestamp"),
                "register_id": match.group("register_id"),
                "item": match.group("item"),
                "price": float(match.group("price")),
                "currency": match.group("currency"),
                "status": match.group("status"),
            }

            transactions.append(transaction)

    return transactions


def compute_refund_ratio(
    sales_count: np.ndarray,
    refund_count: np.ndarray,
) -> np.ndarray:
    """Calculate the ratio off how often a refund ocuorce"""
    epsilon: float = 1e-6
    return refund_count / (sales_count + epsilon)


def remove_price_outliers(price_data: np.ndarray) -> np.ndarray:
    """Clean prices by replacing invalid prices with a median of the
    valid ones"""
    prices = np.asarray(price_data, dtype=float).reshape(-1)

    # Controls that the array isnt empty
    if prices.size == 0:
        return prices

    mean_price = np.mean(prices)
    std_price = np.std(prices)

    # Controls that all the the prices isnt the same
    if std_price == 0:
        return prices.copy()

    outlier_mask = np.abs(prices - mean_price) > 3 * std_price
    valid_prices = prices[~outlier_mask]

    # Controls that there is valid prices
    if valid_prices.size == 0:
        return prices.copy()

    median_price = np.median(valid_prices)

    cleaned_prices = prices.copy()
    cleaned_prices[outlier_mask] = median_price

    return cleaned_prices


def find_log_files(folder: Path) -> list[Path]:
    """Recursively find all .log files in a directory."""
    folder = Path(folder)
    log_files: list[Path] = []

    for item in folder.iterdir():
        if item.is_dir():
            log_files.extend(find_log_files(item))

        elif item.is_file() and item.suffix == ".log":
            log_files.append(item)

    return log_files


def find_active_registers(data: Any) -> set[str]:
    """Recursively find all unique register IDs from the parsed log data."""
    active_registers: set[str] = set()
    if isinstance(data, dict):
        if data.get("active") is True:
            register_id = data.get("id")

            if isinstance(register_id, str):
                active_registers.add(register_id)

        for value in data.values():
            active_registers.update(find_active_registers(value))

    elif isinstance(data, list):
        for item in data:
            active_registers.update(find_active_registers(item))

    return active_registers


def make_dataframe(
    transactions: list[dict[str, Any]],
) -> pd.DataFrame:
    """Convert a list of transaction dictionaries to a pandas DataFrame."""
    df = pd.DataFrame(transactions)
    df['timestamp'] = pd.to_datetime(
        df['timestamp'],
        format="%Y-%m-%d %H:%M:%S",
    )
    df = df.set_index('timestamp')
    df = df.sort_index()

    return df


def hourly_sales_per_item(df: pd.DataFrame) -> pd.DataFrame:
    """Takes the DataFrame groups it by item and returns the sum of sales
    for the following hour"""
    grouped = df.groupby('item')
    hourly_sales = grouped.resample("1h")

    result = hourly_sales['price'].sum()
    # makes result in to a dataFrame
    result = result.reset_index()
    return result


def create_pivot_table(df: pd.DataFrame) -> pd.DataFrame:
    """Creates a pivot table using the dataframe"""

    pivot = df.pivot_table(
        index='item',
        columns='status',
        values='price',
        aggfunc="sum",
        # To get 0 instead of NaN if there is any
        fill_value=0,
    )
    pivot = pivot.reindex(
        columns=['SUCCESS', 'REFUND', 'CANCELLED'],
        fill_value=0,
    )

    return pivot


def refund_ratio_per_item(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate the refund ratio for each item."""

    counts = df.groupby(['item', 'status']).size()
    counts = counts.unstack(fill_value=0)
    counts = counts.reindex(
        columns=['SUCCESS', 'REFUND', 'CANCELLED'],
        fill_value=0,
    )
    sales_count = counts['SUCCESS'].to_numpy()
    refund_count = counts['REFUND'].to_numpy()
    ratios = compute_refund_ratio(sales_count, refund_count)
    counts['refund_ratio'] = ratios

    return counts


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    config_path = data_dir / "store_config.json"

    log_files = find_log_files(data_dir)

    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    active_registers = find_active_registers(config)

    transactions: list[dict[str, Any]] = []

    for log_file in log_files:
        content, encoding = read_log_file(log_file)
        parsed_transactions = parse_log(content)
        transactions.extend(parsed_transactions)

        print(f"Read {log_file.name} using {encoding}:")
        print(f"{len(parsed_transactions)} transactions")

    transactions = [
        transaction
        for transaction in transactions
        if transaction["register_id"] in active_registers
    ]

    df = make_dataframe(transactions)

    df['price'] = remove_price_outliers(df['price'].to_numpy())

    nok_mask = df['currency'] == "NOK"
    df.loc[nok_mask, 'price'] *= 10.0

    hourly_revenue = hourly_sales_per_item(df)
    hourly_revenue['price'] = hourly_revenue['price'].round(2)
    status_pivot = create_pivot_table(df).round(2)
    refund_ratios = refund_ratio_per_item(df)

    item_refund_ratios = refund_ratios[['refund_ratio']]

    df.to_csv(base_dir / "cleaned_transactions.csv")

    hourly_revenue.to_json(
        base_dir / "hourly_revenue.json",
        orient="records",
        date_format="iso",
        indent=2,
    )
    status_pivot.to_csv(base_dir / "status_pivot_table.csv")
    item_refund_ratios.to_csv(base_dir / "item_refund_ratios.csv")

    print("\nWorkflow completed")
    print(f"Log files found: {len(log_files)}")
    print(f"Active registers: {sorted(active_registers)}")
    print(f"Transactions processed: {len(df)}")


if __name__ == "__main__":
    main()
