import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class TradingError(Exception):
    pass


class AccountNotFoundError(TradingError):
    pass


class AccountAlreadyExistsError(TradingError):
    pass


class InvalidAmountError(TradingError):
    pass


class InvalidQuantityError(TradingError):
    pass


class InsufficientFundsError(TradingError):
    pass


class InsufficientHoldingsError(TradingError):
    pass


class UnknownSymbolError(TradingError):
    pass


def get_share_price(symbol: str) -> float:
    normalized = normalize_symbol(symbol)
    prices = {"AAPL": 150.00, "TSLA": 250.00, "GOOGL": 2800.00}
    if normalized not in prices:
        raise UnknownSymbolError(f"Unknown symbol: {symbol}")
    return prices[normalized]


class TransactionType(str, Enum):
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY = "BUY"
    SELL = "SELL"


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


@dataclass(frozen=True)
class Holding:
    symbol: str
    quantity: int
    current_price: float
    market_value: float


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


@dataclass
class Account:
    account_id: str
    username: str
    created_at: datetime
    initial_deposit: float
    cash_balance: float
    holdings: dict[str, int]
    transactions: list[Transaction]


def normalize_symbol(symbol: str) -> str:
    if not symbol or not symbol.strip():
        raise UnknownSymbolError("Symbol cannot be empty.")
    return symbol.strip().upper()


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4()}"


def validate_positive_amount(amount: float) -> None:
    if amount <= 0:
        raise InvalidAmountError("Amount must be positive.")


def validate_positive_quantity(quantity: int) -> None:
    if quantity <= 0:
        raise InvalidQuantityError("Quantity must be positive.")


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
    return Transaction(
        transaction_id=generate_id("txn"),
        account_id=account_id,
        transaction_type=transaction_type,
        timestamp=datetime.now(UTC),
        amount=amount,
        symbol=symbol,
        quantity=quantity,
        price=price,
        cash_balance_after=cash_balance_after,
        description=description,
    )


class AccountService:
    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}
        self._accounts_by_username: dict[str, str] = {}

    def create_account(self, username: str, initial_deposit: float) -> Account:
        if not username or not username.strip():
            raise TradingError("Username cannot be empty.")
        if username in self._accounts_by_username:
            raise AccountAlreadyExistsError(f"Account already exists for username: {username}")

        validate_positive_amount(initial_deposit)

        account_id = generate_id("acct")
        txn = create_transaction(
            account_id=account_id,
            transaction_type=TransactionType.ACCOUNT_CREATED,
            amount=initial_deposit,
            cash_balance_after=initial_deposit,
            description="Account created",
        )

        account = Account(
            account_id=account_id,
            username=username,
            created_at=txn.timestamp,
            initial_deposit=initial_deposit,
            cash_balance=initial_deposit,
            holdings={},
            transactions=[txn],
        )

        self._accounts[account_id] = account
        self._accounts_by_username[username] = account_id
        return account

    def get_account(self, account_id: str) -> Account:
        if account_id not in self._accounts:
            raise AccountNotFoundError(f"Account not found: {account_id}")
        return self._accounts[account_id]

    def get_account_by_username(self, username: str) -> Account:
        if username not in self._accounts_by_username:
            raise AccountNotFoundError(f"Account not found for username: {username}")
        return self.get_account(self._accounts_by_username[username])

    def list_accounts(self) -> list[Account]:
        return list(self._accounts.values())

    def deposit(self, account_id: str, amount: float) -> Transaction:
        account = self.get_account(account_id)
        validate_positive_amount(amount)

        account.cash_balance += amount
        txn = create_transaction(
            account_id=account_id,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            cash_balance_after=account.cash_balance,
            description=f"Deposited {amount}",
        )
        account.transactions.append(txn)
        return txn

    def withdraw(self, account_id: str, amount: float) -> Transaction:
        account = self.get_account(account_id)
        validate_positive_amount(amount)

        if account.cash_balance < amount:
            raise InsufficientFundsError("Insufficient cash balance for withdrawal.")

        account.cash_balance -= amount
        txn = create_transaction(
            account_id=account_id,
            transaction_type=TransactionType.WITHDRAWAL,
            amount=amount,
            cash_balance_after=account.cash_balance,
            description=f"Withdrew {amount}",
        )
        account.transactions.append(txn)
        return txn

    def buy_shares(self, account_id: str, symbol: str, quantity: int) -> Transaction:
        account = self.get_account(account_id)
        validate_positive_quantity(quantity)

        normalized_symbol = normalize_symbol(symbol)
        price = get_share_price(normalized_symbol)
        total_cost = price * quantity

        if account.cash_balance < total_cost:
            raise InsufficientFundsError("Insufficient cash balance to buy shares.")

        account.cash_balance -= total_cost
        account.holdings[normalized_symbol] = account.holdings.get(normalized_symbol, 0) + quantity

        txn = create_transaction(
            account_id=account_id,
            transaction_type=TransactionType.BUY,
            amount=total_cost,
            cash_balance_after=account.cash_balance,
            symbol=normalized_symbol,
            quantity=quantity,
            price=price,
            description=f"Bought {quantity} shares of {normalized_symbol} at {price}",
        )
        account.transactions.append(txn)
        return txn

    def sell_shares(self, account_id: str, symbol: str, quantity: int) -> Transaction:
        account = self.get_account(account_id)
        validate_positive_quantity(quantity)

        normalized_symbol = normalize_symbol(symbol)
        current_quantity = account.holdings.get(normalized_symbol, 0)

        if current_quantity < quantity:
            raise InsufficientHoldingsError(
                f"Insufficient holdings to sell. Owned: {current_quantity}, Requested: {quantity}"
            )

        price = get_share_price(normalized_symbol)
        proceeds = price * quantity

        account.cash_balance += proceeds
        account.holdings[normalized_symbol] -= quantity
        if account.holdings[normalized_symbol] == 0:
            del account.holdings[normalized_symbol]

        txn = create_transaction(
            account_id=account_id,
            transaction_type=TransactionType.SELL,
            amount=proceeds,
            cash_balance_after=account.cash_balance,
            symbol=normalized_symbol,
            quantity=quantity,
            price=price,
            description=f"Sold {quantity} shares of {normalized_symbol} at {price}",
        )
        account.transactions.append(txn)
        return txn

    def get_holdings(self, account_id: str) -> list[Holding]:
        account = self.get_account(account_id)
        holdings_list = []
        for sym, qty in account.holdings.items():
            if qty > 0:
                price = get_share_price(sym)
                holdings_list.append(
                    Holding(symbol=sym, quantity=qty, current_price=price, market_value=qty * price)
                )
        return holdings_list

    def get_holdings_as_of(self, account_id: str, as_of: datetime) -> list[Holding]:
        account = self.get_account(account_id)
        reconstructed_holdings: dict[str, int] = {}

        for txn in account.transactions:
            if txn.timestamp > as_of:
                break
            if txn.transaction_type == TransactionType.BUY and txn.symbol and txn.quantity:
                reconstructed_holdings[txn.symbol] = (
                    reconstructed_holdings.get(txn.symbol, 0) + txn.quantity
                )
            elif txn.transaction_type == TransactionType.SELL and txn.symbol and txn.quantity:
                reconstructed_holdings[txn.symbol] = (
                    reconstructed_holdings.get(txn.symbol, 0) - txn.quantity
                )

        holdings_list = []
        for sym, qty in reconstructed_holdings.items():
            if qty > 0:
                price = get_share_price(sym)
                holdings_list.append(
                    Holding(symbol=sym, quantity=qty, current_price=price, market_value=qty * price)
                )
        return holdings_list

    def get_portfolio_snapshot(self, account_id: str) -> PortfolioSnapshot:
        account = self.get_account(account_id)

        total_deposits = 0.0
        total_withdrawals = 0.0

        for txn in account.transactions:
            if txn.transaction_type in (TransactionType.ACCOUNT_CREATED, TransactionType.DEPOSIT):
                total_deposits += txn.amount
            elif txn.transaction_type == TransactionType.WITHDRAWAL:
                total_withdrawals += txn.amount

        holdings = self.get_holdings(account_id)
        holdings_value = sum(h.market_value for h in holdings)
        total_value = account.cash_balance + holdings_value
        net_contributions = total_deposits - total_withdrawals
        profit_loss = total_value - net_contributions
        profit_loss_percent = (
            (profit_loss / net_contributions * 100) if net_contributions > 0 else 0.0
        )

        return PortfolioSnapshot(
            account_id=account_id,
            username=account.username,
            as_of=datetime.now(UTC),
            cash_balance=account.cash_balance,
            holdings=holdings,
            holdings_value=holdings_value,
            total_value=total_value,
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            net_contributions=net_contributions,
            profit_loss=profit_loss,
            profit_loss_percent=profit_loss_percent,
        )

    def get_portfolio_snapshot_as_of(self, account_id: str, as_of: datetime) -> PortfolioSnapshot:
        account = self.get_account(account_id)

        reconstructed_holdings: dict[str, int] = {}
        cash_balance = 0.0
        total_deposits = 0.0
        total_withdrawals = 0.0

        for txn in account.transactions:
            if txn.timestamp > as_of:
                break

            if txn.transaction_type in (TransactionType.ACCOUNT_CREATED, TransactionType.DEPOSIT):
                cash_balance += txn.amount
                total_deposits += txn.amount
            elif txn.transaction_type == TransactionType.WITHDRAWAL:
                cash_balance -= txn.amount
                total_withdrawals += txn.amount
            elif txn.transaction_type == TransactionType.BUY and txn.symbol and txn.quantity:
                cash_balance -= txn.amount
                reconstructed_holdings[txn.symbol] = (
                    reconstructed_holdings.get(txn.symbol, 0) + txn.quantity
                )
            elif txn.transaction_type == TransactionType.SELL and txn.symbol and txn.quantity:
                cash_balance += txn.amount
                reconstructed_holdings[txn.symbol] = (
                    reconstructed_holdings.get(txn.symbol, 0) - txn.quantity
                )

        holdings_list = []
        for sym, qty in reconstructed_holdings.items():
            if qty > 0:
                price = get_share_price(sym)
                holdings_list.append(
                    Holding(symbol=sym, quantity=qty, current_price=price, market_value=qty * price)
                )

        holdings_value = sum(h.market_value for h in holdings_list)
        total_value = cash_balance + holdings_value
        net_contributions = total_deposits - total_withdrawals
        profit_loss = total_value - net_contributions
        profit_loss_percent = (
            (profit_loss / net_contributions * 100) if net_contributions > 0 else 0.0
        )

        return PortfolioSnapshot(
            account_id=account_id,
            username=account.username,
            as_of=as_of,
            cash_balance=cash_balance,
            holdings=holdings_list,
            holdings_value=holdings_value,
            total_value=total_value,
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            net_contributions=net_contributions,
            profit_loss=profit_loss,
            profit_loss_percent=profit_loss_percent,
        )

    def get_profit_loss(self, account_id: str) -> tuple[float, float]:
        snapshot = self.get_portfolio_snapshot(account_id)
        return snapshot.profit_loss, snapshot.profit_loss_percent

    def get_profit_loss_as_of(self, account_id: str, as_of: datetime) -> tuple[float, float]:
        snapshot = self.get_portfolio_snapshot_as_of(account_id, as_of)
        return snapshot.profit_loss, snapshot.profit_loss_percent

    def list_transactions(self, account_id: str) -> list[Transaction]:
        account = self.get_account(account_id)
        return list(account.transactions)

    def list_transactions_as_of(self, account_id: str, as_of: datetime) -> list[Transaction]:
        account = self.get_account(account_id)
        return [txn for txn in account.transactions if txn.timestamp <= as_of]
