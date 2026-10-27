
import re
import json

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
            register:id = data.get("id")

            if isinstance(register_id, str):
                active_registers.add(register_id)

    elif isinstance(data, list):



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

if __name__ == "__main__":
    main()