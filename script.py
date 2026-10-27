import pathlib
import re

from pathlib import Path
import numpy as np


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


def remove_price_outliers(price_data) -> np.ndarray:
    prices = np.asarray(price_data, dtype=float).reshape(-1)

    if prices.size == 0:
        return prices

    mean_price = np.mean(prices)
    std_price = np.std(prices)

    if std_price == 0:
        return prices.copy()

    outlier_mask = np.abs(prices - mean_price) > 3 * std_price
    valid_prices = prices[~outlier_mask]

    if valid_prices.size == 0:
        return prices.copy()

    median_price = np.median(valid_prices)

    cleaned_prices = prices.copy()
    cleaned_prices[outlier_mask] = median_price

    return cleaned_prices


def main() -> None:
    """Test the functions from task 1."""
    file_path = Path(
        "data/2026/library_cafe/POS_01/register_sales.log"
    )

    content, encoding = read_log_file(file_path)
    transactions = parse_log(content)

    print(f"Encoding: {encoding}")
    print(f"Transactions found: {len(transactions)}")

    for transaction in transactions[:3]:
        print(transaction)


    price_data = [transaction["price"] for transaction in transactions]

    cleaned_prices = remove_price_outliers(price_data)
    print(cleaned_prices)
if __name__ == "__main__":
    main()