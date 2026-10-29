
import re
import json
import pandas as pd
import datetime

from typing import Any
from pathlib import Path


def read_log_file(file_path: Path) -> tuple[str, str]:
    """Read a log file and return its content and encoding."""
    try:
    # Try to read the file with UTF-8
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, 'utf-8'
    except UnicodeDecodeError:
        # If decoding with UTF-8 fails, try Latin-1
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
        return content, 'latin-1'


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

def find_active_registers(data:Any) -> set[str]:
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
        transactions: list[dict[str, Any]]
        ) -> pd.DataFrame:
    """Convert a list of transaction dictionaries to a pandas DataFrame."""
    df = pd.DataFrame(transactions)
    df['timestamp'] = pd.to_datetime(
        df['timestamp'],
          format="%Y-%m-%d %H:%M:%S"
    )
    df = df.set_index("timestamp")
    df = df.sort_index()
    
    return df

def hourly_sales_per_item(df: pd.DataFrame) -> pd.DataFrame:
    """Takes the DataFrame groups it by item and returns the sum of sales for the following hour"""
    grouped =df.groupby('item')
    hourly_sales = grouped.resample('1h')

    result = hourly_sales['price'].sum()
    #makes result in to a dataFrame
    result = result.reset_index()
    return result

def create_pivot_table(df: pd.DataFrame) -> pd.DataFrame:
    """ Creates a pivot table using the dataframe"""

    pivot = df.pivot_table(
        index="item",
        columns="status",
        values="price",
        aggfunc="sum",
        #To get 0 instead of NaN if there is any
        fill_value=0
    )
    pivot = pivot.reindex(
        columns=["SUCCESS", "REFUND", "CANCELLED"], 
        fill_value=0
        )

    return pivot

def main() -> None:
    """Test the functions from task 1 & 2."""
    file_path = Path(
        "data/2026/library_cafe/POS_01/register_sales.log"
    )

    content, encoding = read_log_file(file_path)
    transactions = parse_log(content)

    print(f"Encoding: {encoding}")
    print(f"Transactions found: {len(transactions)}")

    for transaction in transactions[:3]:
        print(transaction)

     # Task 2.1: Recursively find all log files.
    log_files = find_log_files(Path("data"))

    print("\nLog file paths:")

    for file_path in log_files:
        print(file_path)

    print(f"\nLog files found: {len(log_files)}")

    config_path = Path("data/store_config.json")

    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    active_registers = find_active_registers(config)

    print(f"Active registers: {sorted(active_registers)}")

    #testing av df
    df = make_dataframe(transactions)
    print(df)

    #testing av timelig sortering
    result = hourly_sales_per_item(df)
    print(result)

    #tester pivot
    pivot = create_pivot_table(df)
    print(pivot)
if __name__ == "__main__":
    main()