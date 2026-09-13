# Design: Trading Simulation Account Management System

## 1. Overview

Build a simple in-memory account management system for a trading simulation platform.

Users can:

- Create an account with an initial deposit.
- Deposit and withdraw cash.
- Buy and sell shares.
- View current and historical holdings.
- View current and historical profit/loss.
- View all transactions over time.

Constraints:

- All files live in the same directory.
- No package/subdirectory structure.
- Runs in a `uv` project.
- `gradio` is installed.
- No other third-party packages are available.
- Backend should be plain Python standard library.
- Frontend should be a Gradio 6 app.
- Tests should be unit tests for the backend only.

---

## 2. File Structure

All files should be created in the same sandbox directory.

```text
backend.py
app.py
test_backend.py
README.md
```

### Ownership

| File | Owner | Purpose |
|---|---|---|
| `backend.py` | `backend_engineer` | Core account, transaction, portfolio logic |
| `app.py` | `frontend_engineer` | Gradio UI using backend |
| `test_backend.py` | `test_engineer` | Unit tests for backend |
| `README.md` | Shared, optional | How to run app and tests |

---

## 3. Backend Design

### File: `backend.py`

The backend should contain all business logic. It should be independent of Gradio and independently testable.

Use only Python standard library modules such as:

```text
dataclasses
datetime
enum
typing
uuid
```

No persistence is required. State can be in memory.

---

## 4. Core Concepts

### Account

An account represents a single user's simulated trading account.

An account has:

- `account_id`
- `username`
- `created_at`
- `initial_deposit`
- current cash balance
- share holdings by symbol
- transaction history

### Transaction

Every user action that changes the account should be recorded as a transaction:

- Account creation / initial deposit
- Deposit
- Withdrawal
- Buy
- Sell

Transactions are append-only.

### Holdings

Holdings are tracked per stock symbol.

Example:

```text
AAPL: 10 shares
TSLA: 3 shares
GOOGL: 2 shares
```

### Portfolio Value

Portfolio value is:

```text
cash balance + market value of all holdings
```

Where:

```text
market value of symbol = quantity held * get_share_price(symbol)
```

### Profit/Loss

Profit/loss should be calculated against net contributed capital:

```text
net_contributions = total_deposits - total_withdrawals
profit_loss = total_portfolio_value - net_contributions
```

This avoids treating later deposits as profit.

The initial deposit is included in `total_deposits`.

Also expose:

```text
profit_loss_percent = profit_loss / net_contributions * 100
```

If `net_contributions` is zero, return `0.0` for percentage.

---

## 5. Share Price Function

The system has access to a function:

```python
def get_share_price(symbol: str) -> float
```

The backend should include a test implementation with fixed prices:

| Symbol | Price |
|---|---:|
| `AAPL` | `150.00` |
| `TSLA` | `250.00` |
| `GOOGL` | `2800.00` |

Behavior:

- Symbols should be normalized to uppercase.
- If an unknown symbol is requested, raise `UnknownSymbolError`.

Function signature:

```python
def get_share_price(symbol: str) -> float
```

---

## 6. Backend Classes and Functions

### Exceptions

Define clear custom exceptions for validation failures.

```python
class TradingError(Exception):
    pass
```

```python
class AccountNotFoundError(TradingError):
    pass
```

```python
class AccountAlreadyExistsError(TradingError):
    pass
```

```python
class InvalidAmountError(TradingError):
    pass
```

```python
class InvalidQuantityError(TradingError):
    pass
```

```python
class InsufficientFundsError(TradingError):
    pass
```

```python
class InsufficientHoldingsError(TradingError):
    pass
```

```python
class UnknownSymbolError(TradingError):
    pass
```

---

## 7. Enums

### `TransactionType`

```python
class TransactionType(str, Enum):
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY = "BUY"
    SELL = "SELL"
```

---

## 8. Data Classes

### `Transaction`

Represents one account event.

```python
@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    account_id: str
    transaction_type: TransactionType
    timestamp: datetime
    amount: float
    symbol: str | None = None
    quantity: int | None = None
    price: float | None = None
    cash_balance_after: float = 0.0
    description: str = ""
```

Field meanings:

| Field | Meaning |
|---|---|
| `transaction_id` | Unique ID |
| `account_id` | Account affected |
| `transaction_type` | Deposit, withdrawal, buy, sell, etc. |
| `timestamp` | Transaction time |
| `amount` | Cash amount of transaction |
| `symbol` | Stock symbol for buy/sell |
| `quantity` | Number of shares for buy/sell |
| `price` | Share price used for buy/sell |
| `cash_balance_after` | Cash balance immediately after transaction |
| `description` | Human-readable description |

For buy transactions:

```text
amount = quantity * price
```

For sell transactions:

```text
amount = quantity * price
```

For deposits and withdrawals:

```text
amount = deposit or withdrawal cash amount
```

---

### `Holding`

Represents current or historical holding for a symbol.

```python
@dataclass(frozen=True)
class Holding:
    symbol: str
    quantity: int
    current_price: float
    market_value: float
```

---

### `PortfolioSnapshot`

Represents account state at a point in time.

```python
@dataclass(frozen=True)
class PortfolioSnapshot:
    account_id: str
    username: str
    as_of: datetime
    cash_balance: float
    holdings: list[Holding]
    holdings_value: float
    total_value: float
    total_deposits: float
    total_withdrawals: float
    net_contributions: float
    profit_loss: float
    profit_loss_percent: float
```

---

### `Account`

Represents mutable account state.

```python
@dataclass
class Account:
    account_id: str
    username: str
    created_at: datetime
    initial_deposit: float
    cash_balance: float
    holdings: dict[str, int]
    transactions: list[Transaction]
```

---

## 9. Backend Service Class

### `AccountService`

Main API for account management.

```python
class AccountService:
    def __init__(self) -> None
```

Internally store accounts:

```python
self._accounts: dict[str, Account]
```

Optionally store username lookup:

```python
self._accounts_by_username: dict[str, str]
```

---

### Account Creation

```python
def create_account(self, username: str, initial_deposit: float) -> Account:
```

Behavior:

- Validate username is non-empty.
- Validate `initial_deposit > 0`.
- Prevent duplicate usernames.
- Generate an `account_id`.
- Create an account.
- Set cash balance to initial deposit.
- Add an `ACCOUNT_CREATED` transaction.
- Return the account.

Raises:

- `InvalidAmountError`
- `AccountAlreadyExistsError`

---

### Account Retrieval

```python
def get_account(self, account_id: str) -> Account:
```

Behavior:

- Return account by ID.
- Raise `AccountNotFoundError` if missing.

---

```python
def get_account_by_username(self, username: str) -> Account:
```

Behavior:

- Return account by username.
- Raise `AccountNotFoundError` if missing.

---

```python
def list_accounts(self) -> list[Account]:
```

Behavior:

- Return all accounts.

---

### Deposits

```python
def deposit(self, account_id: str, amount: float) -> Transaction:
```

Behavior:

- Validate `amount > 0`.
- Increase cash balance.
- Add a `DEPOSIT` transaction.
- Return transaction.

Raises:

- `AccountNotFoundError`
- `InvalidAmountError`

---

### Withdrawals

```python
def withdraw(self, account_id: str, amount: float) -> Transaction:
```

Behavior:

- Validate `amount > 0`.
- Prevent withdrawal if it would make cash balance negative.
- Decrease cash balance.
- Add a `WITHDRAWAL` transaction.
- Return transaction.

Raises:

- `AccountNotFoundError`
- `InvalidAmountError`
- `InsufficientFundsError`

---

### Buying Shares

```python
def buy_shares(self, account_id: str, symbol: str, quantity: int) -> Transaction:
```

Behavior:

- Normalize symbol to uppercase.
- Validate `quantity > 0`.
- Get current price using `get_share_price(symbol)`.
- Calculate total cost:

```text
total_cost = price * quantity
```

- Prevent buy if total cost is greater than cash balance.
- Decrease cash balance by total cost.
- Increase holdings for symbol.
- Add a `BUY` transaction.
- Return transaction.

Raises:

- `AccountNotFoundError`
- `InvalidQuantityError`
- `UnknownSymbolError`
- `InsufficientFundsError`

---

### Selling Shares

```python
def sell_shares(self, account_id: str, symbol: str, quantity: int) -> Transaction:
```

Behavior:

- Normalize symbol to uppercase.
- Validate `quantity > 0`.
- Get current holdings for symbol.
- Prevent sale if quantity is greater than holdings.
- Get current price using `get_share_price(symbol)`.
- Calculate proceeds:

```text
proceeds = price * quantity
```

- Increase cash balance by proceeds.
- Decrease holdings for symbol.
- Remove symbol from holdings if quantity becomes zero.
- Add a `SELL` transaction.
- Return transaction.

Raises:

- `AccountNotFoundError`
- `InvalidQuantityError`
- `InsufficientHoldingsError`
- `UnknownSymbolError`

---

### Current Holdings

```python
def get_holdings(self, account_id: str) -> list[Holding]:
```

Behavior:

- Return current holdings with quantity, current price, and market value.
- Exclude symbols with zero quantity.

Raises:

- `AccountNotFoundError`
- `UnknownSymbolError`

---

### Historical Holdings

```python
def get_holdings_as_of(self, account_id: str, as_of: datetime) -> list[Holding]:
```

Behavior:

- Reconstruct holdings by replaying transactions up to and including `as_of`.
- Use current `get_share_price(symbol)` for valuation because no historical price service exists.
- Exclude zero holdings.

Raises:

- `AccountNotFoundError`
- `UnknownSymbolError`

---

### Current Portfolio Snapshot

```python
def get_portfolio_snapshot(self, account_id: str) -> PortfolioSnapshot:
```

Behavior:

- Return current account snapshot.
- Include:
  - cash balance
  - holdings
  - holdings value
  - total account value
  - total deposits
  - total withdrawals
  - net contributions
  - profit/loss
  - profit/loss percent

Raises:

- `AccountNotFoundError`
- `UnknownSymbolError`

---

### Historical Portfolio Snapshot

```python
def get_portfolio_snapshot_as_of(
    self,
    account_id: str,
    as_of: datetime,
) -> PortfolioSnapshot:
```

Behavior:

- Reconstruct account state from transactions up to and including `as_of`.
- Reconstruct:
  - cash balance
  - holdings
  - total deposits
  - total withdrawals
- Use current `get_share_price(symbol)` to value holdings.
- Return `PortfolioSnapshot`.

Raises:

- `AccountNotFoundError`
- `UnknownSymbolError`

---

### Profit/Loss

```python
def get_profit_loss(self, account_id: str) -> tuple[float, float]:
```

Returns:

```text
(profit_loss, profit_loss_percent)
```

Raises:

- `AccountNotFoundError`
- `UnknownSymbolError`

---

```python
def get_profit_loss_as_of(
    self,
    account_id: str,
    as_of: datetime,
) -> tuple[float, float]:
```

Returns historical profit/loss as of timestamp.

Raises:

- `AccountNotFoundError`
- `UnknownSymbolError`

---

### Transaction Listing

```python
def list_transactions(self, account_id: str) -> list[Transaction]:
```

Behavior:

- Return transactions in chronological order.

Raises:

- `AccountNotFoundError`

---

```python
def list_transactions_as_of(
    self,
    account_id: str,
    as_of: datetime,
) -> list[Transaction]:
```

Behavior:

- Return transactions up to and including timestamp.

Raises:

- `AccountNotFoundError`

---

## 10. Backend Helper Functions

These helpers should be private or module-level functions in `backend.py`.

### Symbol Normalization

```python
def normalize_symbol(symbol: str) -> str:
```

Behavior:

- Strip whitespace.
- Convert to uppercase.
- Validate non-empty.

---

### ID Generation

```python
def generate_id(prefix: str) -> str:
```

Behavior:

- Return unique ID string.
- Example format:

```text
acct_<uuid>
txn_<uuid>
```

---

### Validation Helpers

```python
def validate_positive_amount(amount: float) -> None:
```

Raises `InvalidAmountError`.

---

```python
def validate_positive_quantity(quantity: int) -> None:
```

Raises `InvalidQuantityError`.

---

### Transaction Creation Helper

```python
def create_transaction(
    account_id: str,
    transaction_type: TransactionType,
    amount: float,
    cash_balance_after: float,
    symbol: str | None = None,
    quantity: int | None = None,
    price: float | None = None,
    description: str = "",
) -> Transaction:
```

---

## 11. Important Business Rules

### Deposits

Allowed only if:

```text
amount > 0
```

### Withdrawals

Allowed only if:

```text
amount > 0
cash_balance - amount >= 0
```

### Buys

Allowed only if:

```text
quantity > 0
cash_balance >= quantity * current_share_price
```

### Sells

Allowed only if:

```text
quantity > 0
current_holdings[symbol] >= quantity
```

### Cash Balance

Cash balance must never become negative.

### Holdings

Holdings must never become negative.

### Unknown Symbols

Unknown symbols should raise `UnknownSymbolError`.

---

## 12. Frontend Design

### File: `app.py`

Owner: `frontend_engineer`

Build a Gradio 6 app that imports `AccountService` from `backend.py`.

The app should provide a simple UI for:

1. Creating an account.
2. Selecting an account.
3. Depositing funds.
4. Withdrawing funds.
5. Buying shares.
6. Selling shares.
7. Viewing:
   - account summary
   - holdings
   - profit/loss
   - transaction list

---

## 13. Gradio 6 API Guidance

Use:

```python
import gradio as gr
```

Use the Blocks API:

```python
with gr.Blocks() as demo:
```

Launch with:

```python
demo.launch()
```

### Event Binding

For button events, use:

```python
button.click(
    fn=handler_function,
    inputs=[input_component_1, input_component_2],
    outputs=[output_component_1, output_component_2],
)
```

For no inputs:

```python
button.click(
    fn=handler_function,
    inputs=None,
    outputs=[output_component],
)
```

For no outputs:

```python
button.click(
    fn=handler_function,
    inputs=[input_component],
    outputs=None,
)
```

### State

Use Gradio state for selected/current account ID:

```python
current_account_id = gr.State(value=None)
```

Handler functions may receive and return state.

Example signature only:

```python
def create_account_handler(
    username: str,
    initial_deposit: float,
    current_account_id: str | None,
) -> tuple[str, str, list[list[object]], list[list[object]], list[list[object]], str | None]:
```

### Dataframe Component

Use `gr.Dataframe`.

For Gradio 6, if copy/fullscreen buttons are needed, use:

```python
gr.Dataframe(buttons=["copy", "fullscreen"])
```

Do **not** use old Gradio 5 kwargs:

```text
show_copy_button=True
show_fullscreen_button=True
```

Those were replaced in Gradio 6 by the `buttons` parameter.

Recommended dataframe setup:

```python
gr.Dataframe(
    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
    datatype=["str", "number", "number", "number"],
    interactive=False,
    buttons=["copy", "fullscreen"],
)
```

### Component Choices

Use these components:

| Purpose | Component |
|---|---|
| Username | `gr.Textbox` |
| Amount | `gr.Number` |
| Symbol | `gr.Dropdown` or `gr.Textbox` |
| Quantity | `gr.Number` |
| Status messages | `gr.Textbox` or `gr.Markdown` |
| Account summary | `gr.JSON` or `gr.Markdown` |
| Holdings table | `gr.Dataframe` |
| Transactions table | `gr.Dataframe` |
| Buttons | `gr.Button` |
| Layout | `gr.Row`, `gr.Column`, `gr.Tab` |

Use supported symbols dropdown:

```text
AAPL
TSLA
GOOGL
```

---

## 14. Frontend Global State

In `app.py`, instantiate one service at module level:

```python
service = AccountService()
```

The frontend can maintain the selected account using `gr.State`.

The current account ID should be updated when:

- An account is created.
- An account is selected from a dropdown.

---

## 15. Frontend Handler Functions

The frontend engineer should define handler functions in `app.py`. These functions should call backend methods and convert backend data into UI-friendly formats.

Do not put business logic in these handlers. All validation and rules belong in `backend.py`.

---

### Account Creation Handler

```python
def create_account_handler(
    username: str,
    initial_deposit: float,
    current_account_id: str | None,
) -> tuple[
    str,
    str | None,
    list[list[object]],
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

Inputs:

- username
- initial deposit
- current account ID state

Outputs:

- status message
- updated current account ID state
- holdings dataframe rows
- transactions dataframe rows
- accounts dataframe rows
- summary JSON

Behavior:

- Call `service.create_account`.
- Set new account as selected account.
- Refresh account summary, holdings, transactions, account list.
- Catch `TradingError` and return user-friendly error.

---

### Deposit Handler

```python
def deposit_handler(
    account_id: str | None,
    amount: float,
) -> tuple[
    str,
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

Behavior:

- Validate that an account is selected.
- Call `service.deposit`.
- Refresh holdings, transactions, summary.
- Return status.

---

### Withdrawal Handler

```python
def withdraw_handler(
    account_id: str | None,
    amount: float,
) -> tuple[
    str,
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

Behavior:

- Validate account selected.
- Call `service.withdraw`.
- Refresh UI tables and summary.
- Return status.

---

### Buy Handler

```python
def buy_handler(
    account_id: str | None,
    symbol: str,
    quantity: float,
) -> tuple[
    str,
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

Behavior:

- Convert quantity to `int`.
- Validate account selected.
- Call `service.buy_shares`.
- Refresh UI.

---

### Sell Handler

```python
def sell_handler(
    account_id: str | None,
    symbol: str,
    quantity: float,
) -> tuple[
    str,
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

Behavior:

- Convert quantity to `int`.
- Validate account selected.
- Call `service.sell_shares`.
- Refresh UI.

---

### Refresh Handler

```python
def refresh_handler(
    account_id: str | None,
) -> tuple[
    str,
    list[list[object]],
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

Behavior:

- Refresh status, holdings, transactions, accounts list, summary.
- If no account selected, return empty account-specific data.

---

### Select Account Handler

```python
def select_account_handler(
    selected_account_id: str | None,
) -> tuple[
    str,
    str | None,
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

Behavior:

- Set current account ID.
- Refresh holdings, transactions, summary.

---

## 16. Frontend Formatting Helper Functions

### Account Summary Formatting

```python
def snapshot_to_summary_dict(snapshot: PortfolioSnapshot) -> dict[str, object]:
```

Return dictionary like:

```text
{
  "account_id": "...",
  "username": "...",
  "cash_balance": 1000.0,
  "holdings_value": 500.0,
  "total_value": 1500.0,
  "total_deposits": 1000.0,
  "total_withdrawals": 0.0,
  "net_contributions": 1000.0,
  "profit_loss": 500.0,
  "profit_loss_percent": 50.0
}
```

---

### Holdings Table Formatting

```python
def holdings_to_rows(holdings: list[Holding]) -> list[list[object]]:
```

Rows:

```text
[
  ["AAPL", 10, 150.00, 1500.00]
]
```

---

### Transaction Table Formatting

```python
def transactions_to_rows(transactions: list[Transaction]) -> list[list[object]]:
```

Columns:

```text
Timestamp
Type
Symbol
Quantity
Price
Amount
Cash Balance After
Description
```

---

### Accounts Table Formatting

```python
def accounts_to_rows(accounts: list[Account]) -> list[list[object]]:
```

Columns:

```text
Account ID
Username
Created At
Cash Balance
Initial Deposit
```

---

### Empty UI Helpers

```python
def empty_summary() -> dict[str, object]:
```

```python
def empty_rows() -> list[list[object]]:
```

---

## 17. Frontend Layout

Suggested Gradio layout:

```text
Title: Trading Simulation Account Manager

Tab 1: Account
- Username textbox
- Initial deposit number
- Create account button
- Accounts dataframe
- Selected account ID textbox or dropdown
- Refresh button

Tab 2: Cash
- Deposit amount number
- Deposit button
- Withdrawal amount number
- Withdraw button

Tab 3: Trading
- Symbol dropdown: AAPL, TSLA, GOOGL
- Quantity number
- Buy button
- Sell button

Tab 4: Portfolio
- Summary JSON
- Holdings dataframe
- Transactions dataframe
```

### Recommended Components

#### Status

```python
status_box = gr.Textbox(
    label="Status",
    interactive=False,
)
```

#### Summary

```python
summary_json = gr.JSON(
    label="Account Summary",
)
```

#### Holdings

```python
holdings_df = gr.Dataframe(
    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
    datatype=["str", "number", "number", "number"],
    interactive=False,
    buttons=["copy", "fullscreen"],
)
```

#### Transactions

```python
transactions_df = gr.Dataframe(
    headers=[
        "Timestamp",
        "Type",
        "Symbol",
        "Quantity",
        "Price",
        "Amount",
        "Cash Balance After",
        "Description",
    ],
    datatype=["str", "str", "str", "number", "number", "number", "number", "str"],
    interactive=False,
    buttons=["copy", "fullscreen"],
)
```

#### Accounts

```python
accounts_df = gr.Dataframe(
    headers=[
        "Account ID",
        "Username",
        "Created At",
        "Cash Balance",
        "Initial Deposit",
    ],
    datatype=["str", "str", "str", "number", "number"],
    interactive=False,
    buttons=["copy", "fullscreen"],
)
```

---

## 18. Testing Design

### File: `test_backend.py`

Owner: `test_engineer`

Use Python standard library `unittest`.

Do not test Gradio UI.

Tests should validate backend behavior thoroughly.

---

## 19. Test Cases

### Share Price Tests

```python
def test_get_share_price_known_symbols(self) -> None:
```

Validate:

- `AAPL == 150.00`
- `TSLA == 250.00`
- `GOOGL == 2800.00`
- Lowercase input works, e.g. `aapl`

---

```python
def test_get_share_price_unknown_symbol_raises(self) -> None:
```

Validate unknown symbol raises `UnknownSymbolError`.

---

### Account Creation Tests

```python
def test_create_account_success(self) -> None:
```

Validate:

- Account created.
- Cash balance equals initial deposit.
- Initial deposit stored.
- One transaction exists.
- Transaction type is `ACCOUNT_CREATED`.

---

```python
def test_create_account_rejects_non_positive_initial_deposit(self) -> None:
```

Validate zero and negative deposits raise `InvalidAmountError`.

---

```python
def test_create_account_rejects_duplicate_username(self) -> None:
```

Validate duplicate username raises `AccountAlreadyExistsError`.

---

### Deposit Tests

```python
def test_deposit_success(self) -> None:
```

Validate:

- Cash balance increases.
- Transaction created.
- Transaction type is `DEPOSIT`.

---

```python
def test_deposit_rejects_non_positive_amount(self) -> None:
```

Validate zero and negative amounts raise `InvalidAmountError`.

---

### Withdrawal Tests

```python
def test_withdraw_success(self) -> None:
```

Validate:

- Cash balance decreases.
- Transaction created.
- Transaction type is `WITHDRAWAL`.

---

```python
def test_withdraw_rejects_non_positive_amount(self) -> None:
```

Validate zero and negative amounts raise `InvalidAmountError`.

---

```python
def test_withdraw_rejects_insufficient_funds(self) -> None:
```

Validate withdrawing more than cash raises `InsufficientFundsError`.

---

```python
def test_withdraw_all_cash_allowed(self) -> None:
```

Validate withdrawing exactly the cash balance is allowed and leaves zero cash.

---

### Buy Tests

```python
def test_buy_shares_success(self) -> None:
```

Scenario:

- Create account with `1000`.
- Buy `2` AAPL at `150`.
- Validate:
  - Cash decreases to `700`.
  - Holdings `AAPL == 2`.
  - Transaction type is `BUY`.

---

```python
def test_buy_rejects_insufficient_funds(self) -> None:
```

Scenario:

- Create account with `100`.
- Try to buy `1` AAPL at `150`.
- Expect `InsufficientFundsError`.

---

```python
def test_buy_rejects_non_positive_quantity(self) -> None:
```

Validate zero and negative quantities raise `InvalidQuantityError`.

---

```python
def test_buy_unknown_symbol_raises(self) -> None:
```

Validate unknown symbol raises `UnknownSymbolError`.

---

### Sell Tests

```python
def test_sell_shares_success(self) -> None:
```

Scenario:

- Create account with `1000`.
- Buy `2` AAPL.
- Sell `1` AAPL.
- Validate:
  - Holding becomes `1`.
  - Cash increases by `150`.
  - Transaction type is `SELL`.

---

```python
def test_sell_all_removes_holding(self) -> None:
```

Scenario:

- Buy `2` AAPL.
- Sell `2` AAPL.
- Validate AAPL is removed from holdings or not returned by `get_holdings`.

---

```python
def test_sell_rejects_insufficient_holdings(self) -> None:
```

Validate selling more than owned raises `InsufficientHoldingsError`.

---

```python
def test_sell_rejects_non_positive_quantity(self) -> None:
```

Validate zero and negative quantities raise `InvalidQuantityError`.

---

### Portfolio Snapshot Tests

```python
def test_portfolio_snapshot_cash_only(self) -> None:
```

Scenario:

- Create account with `1000`.

Validate:

- Cash balance `1000`
- Holdings value `0`
- Total value `1000`
- Net contributions `1000`
- Profit/loss `0`

---

```python
def test_portfolio_snapshot_with_holdings(self) -> None:
```

Scenario:

- Create account with `1000`.
- Buy `2` AAPL.

Validate:

- Cash `700`
- Holdings value `300`
- Total value `1000`
- Profit/loss `0`

---

```python
def test_profit_loss_after_price_based_trade_roundtrip(self) -> None:
```

Scenario:

- Create account with `1000`.
- Buy `2` AAPL.
- Sell `1` AAPL.

Validate:

- Total value remains `1000` with fixed prices.
- Profit/loss remains `0`.

---

```python
def test_profit_loss_accounts_for_deposits_and_withdrawals(self) -> None:
```

Scenario:

- Create account with `1000`.
- Deposit `500`.
- Withdraw `200`.

Validate:

- Net contributions `1300`.
- If no trades, total value `1300`.
- Profit/loss `0`.

---

### Transaction Listing Tests

```python
def test_list_transactions_chronological(self) -> None:
```

Scenario:

- Create account.
- Deposit.
- Buy.
- Sell.
- Withdraw.

Validate:

- Transactions are listed in insertion/chronological order.
- Types match expected sequence.

---

### Historical Reporting Tests

```python
def test_holdings_as_of_before_buy(self) -> None:
```

Scenario:

- Create account.
- Capture timestamp.
- Buy AAPL.
- Request holdings as of captured timestamp.

Validate:

- No AAPL holding returned.

---

```python
def test_holdings_as_of_after_buy(self) -> None:
```

Scenario:

- Create account.
- Buy AAPL.
- Capture timestamp after buy.
- Request holdings as of timestamp.

Validate:

- AAPL quantity is present.

---

```python
def test_portfolio_snapshot_as_of_before_later_deposit(self) -> None:
```

Scenario:

- Create account with `1000`.
- Capture timestamp.
- Deposit `500`.
- Request snapshot as of captured timestamp.

Validate:

- Cash is `1000`.
- Net contributions are `1000`.

---

### Account Lookup Tests

```python
def test_get_missing_account_raises(self) -> None:
```

Validate missing account ID raises `AccountNotFoundError`.

---

```python
def test_get_account_by_username_success(self) -> None:
```

Validate username lookup works.

---

```python
def test_list_accounts(self) -> None:
```

Validate all created accounts are returned.

---

## 20. Engineer Assignments

## backend_engineer

### Primary File

```text
backend.py
```

### Responsibilities

Implement:

- Data classes:
  - `Transaction`
  - `Holding`
  - `PortfolioSnapshot`
  - `Account`
- Enum:
  - `TransactionType`
- Exceptions:
  - `TradingError`
  - `AccountNotFoundError`
  - `AccountAlreadyExistsError`
  - `InvalidAmountError`
  - `InvalidQuantityError`
  - `InsufficientFundsError`
  - `InsufficientHoldingsError`
  - `UnknownSymbolError`
- Share price function:
  - `get_share_price`
- Helper functions:
  - `normalize_symbol`
  - `generate_id`
  - `validate_positive_amount`
  - `validate_positive_quantity`
  - `create_transaction`
- Main service:
  - `AccountService`

### Acceptance Criteria

Backend is complete when:

- All methods described above exist.
- Business rules are enforced.
- Cash balance can never go negative.
- Holdings can never go negative.
- Transactions are recorded for every state-changing action.
- Current holdings can be reported.
- Historical holdings can be reconstructed.
- Current profit/loss can be reported.
- Historical profit/loss can be reconstructed.
- Unit tests pass.

---

## frontend_engineer

### Primary File

```text
app.py
```

### Responsibilities

Build a Gradio 6 app that:

- Imports and uses `AccountService`.
- Provides UI to:
  - create account
  - deposit
  - withdraw
  - buy shares
  - sell shares
  - refresh summary
  - view holdings
  - view transactions
  - view accounts
- Uses `gr.Blocks`.
- Uses `gr.State` for selected account ID.
- Uses `gr.Dataframe` for holdings, transactions, and accounts.
- Uses `gr.JSON` for account summary.
- Handles backend exceptions gracefully.

### Required Handler Signatures

```python
def create_account_handler(
    username: str,
    initial_deposit: float,
    current_account_id: str | None,
) -> tuple[
    str,
    str | None,
    list[list[object]],
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

```python
def deposit_handler(
    account_id: str | None,
    amount: float,
) -> tuple[
    str,
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

```python
def withdraw_handler(
    account_id: str | None,
    amount: float,
) -> tuple[
    str,
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

```python
def buy_handler(
    account_id: str | None,
    symbol: str,
    quantity: float,
) -> tuple[
    str,
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

```python
def sell_handler(
    account_id: str | None,
    symbol: str,
    quantity: float,
) -> tuple[
    str,
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

```python
def refresh_handler(
    account_id: str | None,
) -> tuple[
    str,
    list[list[object]],
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

```python
def select_account_handler(
    selected_account_id: str | None,
) -> tuple[
    str,
    str | None,
    list[list[object]],
    list[list[object]],
    dict[str, object],
]:
```

### Gradio 6 Notes

Use:

```text
gr.Dataframe(buttons=["copy", "fullscreen"])
```

Do not use:

```text
show_copy_button=True
show_fullscreen_button=True
```

Use event handlers like:

```text
button.click(fn=..., inputs=[...], outputs=[...])
```

Use:

```text
demo.launch()
```

### Acceptance Criteria

Frontend is complete when:

- App starts with `uv run python app.py`.
- User can create account.
- User can deposit and withdraw.
- User can buy and sell supported symbols.
- UI prevents crashes by displaying backend errors as status messages.
- Holdings table updates after trades.
- Transactions table updates after every action.
- Summary updates after every action.
- Invalid actions show clear error messages.

---

## test_engineer

### Primary File

```text
test_backend.py
```

### Responsibilities

Write unit tests for `backend.py` using standard library `unittest`.

Do not test Gradio.

### Required Coverage

Cover:

- Share price lookup.
- Account creation.
- Duplicate username prevention.
- Deposits.
- Withdrawals.
- Withdrawal insufficient funds.
- Buys.
- Buy insufficient funds.
- Sells.
- Sell insufficient holdings.
- Holdings reporting.
- Portfolio snapshot.
- Profit/loss.
- Transaction listing.
- Historical holdings.
- Historical portfolio snapshots.
- Missing account handling.

### Suggested Test Class

```python
class TestAccountService(unittest.TestCase):
    def setUp(self) -> None:
```

Each test should create a fresh `AccountService`.

### Acceptance Criteria

Tests are complete when:

- They can be run with:

```text
uv run python -m unittest test_backend.py
```

- They pass against a correct backend implementation.
- They fail for important rule violations such as:
  - negative cash
  - negative holdings
  - missing transaction records
  - bad profit/loss calculations

---

## 21. Run Commands

### Run App

```text
uv run python app.py
```

### Run Tests

```text
uv run python -m unittest test_backend.py
```

---

## 22. Success Criteria

The system is successful when:

- Backend business logic is implemented in `backend.py`.
- Gradio 6 frontend is implemented in `app.py`.
- Unit tests are implemented in `test_backend.py`.
- Users can create accounts.
- Users can deposit and withdraw funds.
- Users cannot withdraw more cash than they have.
- Users can buy and sell shares.
- Users cannot buy shares they cannot afford.
- Users cannot sell shares they do not own.
- Users can view current holdings.
- Users can view current profit/loss.
- Users can view transactions over time.
- Historical holdings can be reported by timestamp.
- Historical profit/loss can be reported by timestamp.
- Fixed test share prices work for `AAPL`, `TSLA`, and `GOOGL`.
- All backend tests pass.
- Gradio app runs successfully.