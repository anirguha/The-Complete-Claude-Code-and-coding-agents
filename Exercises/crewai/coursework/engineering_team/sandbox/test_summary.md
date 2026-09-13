```python
import unittest
from datetime import datetime, timezone
from backend import (
    AccountService,
    TradingError,
    AccountNotFoundError,
    AccountAlreadyExistsError,
    InvalidAmountError,
    InvalidQuantityError,
    InsufficientFundsError,
    InsufficientHoldingsError,
    UnknownSymbolError,
    get_share_price,
    TransactionType,
)


class TestAccountService(unittest.TestCase):
    def setUp(self):
        self.service = AccountService()

    def test_get_share_price_known_symbols(self):
        self.assertEqual(get_share_price("AAPL"), 150.00)
        self.assertEqual(get_share_price("TSLA"), 250.00)
        self.assertEqual(get_share_price("GOOGL"), 2800.00)
        self.assertEqual(get_share_price("aapl"), 150.00)

    def test_get_share_price_unknown_symbol_raises(self):
        with self.assertRaises(UnknownSymbolError):
            get_share_price("MSFT")

    def test_create_account_success(self):
        acct = self.service.create_account("user1", 1000.0)
        self.assertEqual(acct.username, "user1")
        self.assertEqual(acct.initial_deposit, 1000.0)
        self.assertEqual(acct.cash_balance, 1000.0)
        self.assertEqual(len(acct.transactions), 1)
        self.assertEqual(acct.transactions[0].transaction_type, TransactionType.ACCOUNT_CREATED)

    def test_create_account_rejects_non_positive_initial_deposit(self):
        with self.assertRaises(InvalidAmountError):
            self.service.create_account("user2", 0)
        with self.assertRaises(InvalidAmountError):
            self.service.create_account("user3", -10)

    def test_create_account_rejects_duplicate_username(self):
        self.service.create_account("user1", 1000.0)
        with self.assertRaises(AccountAlreadyExistsError):
            self.service.create_account("user1", 500.0)

    def test_deposit_success(self):
        acct = self.service.create_account("user1", 1000.0)
        txn = self.service.deposit(acct.account_id, 500.0)
        self.assertEqual(self.service.get_account(acct.account_id).cash_balance, 1500.0)
        self.assertEqual(txn.transaction_type, TransactionType.DEPOSIT)

    def test_deposit_rejects_non_positive_amount(self):
        acct = self.service.create_account("user1", 1000.0)
        with self.assertRaises(InvalidAmountError):
            self.service.deposit(acct.account_id, 0)
        with self.assertRaises(InvalidAmountError):
            self.service.deposit(acct.account_id, -500.0)

    def test_withdraw_success(self):
        acct = self.service.create_account("user1", 1000.0)
        txn = self.service.withdraw(acct.account_id, 500.0)
        self.assertEqual(self.service.get_account(acct.account_id).cash_balance, 500.0)
        self.assertEqual(txn.transaction_type, TransactionType.WITHDRAWAL)

    def test_withdraw_rejects_non_positive_amount(self):
        acct = self.service.create_account("user1", 1000.0)
        with self.assertRaises(InvalidAmountError):
            self.service.withdraw(acct.account_id, 0)

    def test_withdraw_rejects_insufficient_funds(self):
        acct = self.service.create_account("user1", 1000.0)
        with self.assertRaises(InsufficientFundsError):
            self.service.withdraw(acct.account_id, 1500.0)

    def test_withdraw_all_cash_allowed(self):
        acct = self.service.create_account("user1", 1000.0)
        self.service.withdraw(acct.account_id, 1000.0)
        self.assertEqual(self.service.get_account(acct.account_id).cash_balance, 0.0)

    def test_buy_shares_success(self):
        acct = self.service.create_account("user1", 1000.0)
        txn = self.service.buy_shares(acct.account_id, "AAPL", 2)
        self.assertEqual(self.service.get_account(acct.account_id).cash_balance, 700.0)
        self.assertEqual(self.service.get_account(acct.account_id).holdings["AAPL"], 2)
        self.assertEqual(txn.transaction_type, TransactionType.BUY)

    def test_buy_rejects_insufficient_funds(self):
        acct = self.service.create_account("user1", 100.0)
        with self.assertRaises(InsufficientFundsError):
            self.service.buy_shares(acct.account_id, "AAPL", 1)

    def test_buy_rejects_non_positive_quantity(self):
        acct = self.service.create_account("user1", 1000.0)
        with self.assertRaises(InvalidQuantityError):
            self.service.buy_shares(acct.account_id, "AAPL", 0)

    def test_buy_unknown_symbol_raises(self):
        acct = self.service.create_account("user1", 1000.0)
        with self.assertRaises(UnknownSymbolError):
            self.service.buy_shares(acct.account_id, "MSFT", 1)

    def test_sell_shares_success(self):
        acct = self.service.create_account("user1", 1000.0)
        self.service.buy_shares(acct.account_id, "AAPL", 2)
        txn = self.service.sell_shares(acct.account_id, "AAPL", 1)
        self.assertEqual(self.service.get_account(acct.account_id).holdings["AAPL"], 1)
        self.assertEqual(self.service.get_account(acct.account_id).cash_balance, 850.0)
        self.assertEqual(txn.transaction_type, TransactionType.SELL)

    def test_sell_all_removes_holding(self):
        acct = self.service.create_account("user1", 1000.0)
        self.service.buy_shares(acct.account_id, "AAPL", 2)
        self.service.sell_shares(acct.account_id, "AAPL", 2)
        self.assertNotIn("AAPL", self.service.get_account(acct.account_id).holdings)
        holdings = self.service.get_holdings(acct.account_id)
        self.assertEqual(len(holdings), 0)

    def test_sell_rejects_insufficient_holdings(self):
        acct = self.service.create_account("user1", 1000.0)
        self.service.buy_shares(acct.account_id, "AAPL", 2)
        with self.assertRaises(InsufficientHoldingsError):
            self.service.sell_shares(acct.account_id, "AAPL", 3)

    def test_sell_rejects_non_positive_quantity(self):
        acct = self.service.create_account("user1", 1000.0)
        self.service.buy_shares(acct.account_id, "AAPL", 2)
        with self.assertRaises(InvalidQuantityError):
            self.service.sell_shares(acct.account_id, "AAPL", 0)

    def test_portfolio_snapshot_cash_only(self):
        acct = self.service.create_account("user1", 1000.0)
        snap = self.service.get_portfolio_snapshot(acct.account_id)
        self.assertEqual(snap.cash_balance, 1000.0)
        self.assertEqual(snap.holdings_value, 0.0)
        self.assertEqual(snap.total_value, 1000.0)
        self.assertEqual(snap.net_contributions, 1000.0)
        self.assertEqual(snap.profit_loss, 0.0)

    def test_portfolio_snapshot_with_holdings(self):
        acct = self.service.create_account("user1", 1000.0)
        self.service.buy_shares(acct.account_id, "AAPL", 2)
        snap = self.service.get_portfolio_snapshot(acct.account_id)
        self.assertEqual(snap.cash_balance, 700.0)
        self.assertEqual(snap.holdings_value, 300.0)
        self.assertEqual(snap.total_value, 1000.0)
        self.assertEqual(snap.profit_loss, 0.0)

    def test_profit_loss_after_price_based_trade_roundtrip(self):
        acct = self.service.create_account("user1", 1000.0)
        self.service.buy_shares(acct.account_id, "AAPL", 2)
        self.service.sell_shares(acct.account_id, "AAPL", 1)
        snap = self.service.get_portfolio_snapshot(acct.account_id)
        self.assertEqual(snap.total_value, 1000.0)
        self.assertEqual(snap.profit_loss, 0.0)

    def test_profit_loss_accounts_for_deposits_and_withdrawals(self):
        acct = self.service.create_account("user1", 1000.0)
        self.service.deposit(acct.account_id, 500.0)
        self.service.withdraw(acct.account_id, 200.0)
        snap = self.service.get_portfolio_snapshot(acct.account_id)
        self.assertEqual(snap.net_contributions, 1300.0)
        self.assertEqual(snap.total_value, 1300.0)
        self.assertEqual(snap.profit_loss, 0.0)

    def test_list_transactions_chronological(self):
        acct = self.service.create_account("user1", 1000.0)
        self.service.deposit(acct.account_id, 500.0)
        self.service.buy_shares(acct.account_id, "AAPL", 1)
        self.service.sell_shares(acct.account_id, "AAPL", 1)
        self.service.withdraw(acct.account_id, 100.0)
        txns = self.service.list_transactions(acct.account_id)
        self.assertEqual(len(txns), 5)
        self.assertEqual(txns[0].transaction_type, TransactionType.ACCOUNT_CREATED)
        self.assertEqual(txns[1].transaction_type, TransactionType.DEPOSIT)
        self.assertEqual(txns[2].transaction_type, TransactionType.BUY)
        self.assertEqual(txns[3].transaction_type, TransactionType.SELL)
        self.assertEqual(txns[4].transaction_type, TransactionType.WITHDRAWAL)

    def test_holdings_as_of_before_buy(self):
        acct = self.service.create_account("user1", 1000.0)
        ts = datetime.now(timezone.utc)
        self.service.buy_shares(acct.account_id, "AAPL", 2)
        holdings = self.service.get_holdings_as_of(acct.account_id, ts)
        self.assertEqual(len(holdings), 0)

    def test_holdings_as_of_after_buy(self):
        acct = self.service.create_account("user1", 1000.0)
        self.service.buy_shares(acct.account_id, "AAPL", 2)
        ts = datetime.now(timezone.utc)
        holdings = self.service.get_holdings_as_of(acct.account_id, ts)
        self.assertEqual(len(holdings), 1)
        self.assertEqual(holdings[0].symbol, "AAPL")
        self.assertEqual(holdings[0].quantity, 2)

    def test_portfolio_snapshot_as_of_before_later_deposit(self):
        acct = self.service.create_account("user1", 1000.0)
        ts = datetime.now(timezone.utc)
        self.service.deposit(acct.account_id, 500.0)
        snap = self.service.get_portfolio_snapshot_as_of(acct.account_id, ts)
        self.assertEqual(snap.cash_balance, 1000.0)
        self.assertEqual(snap.net_contributions, 1000.0)

    def test_get_missing_account_raises(self):
        with self.assertRaises(AccountNotFoundError):
            self.service.get_account("nonexistent")

    def test_get_account_by_username_success(self):
        acct = self.service.create_account("user1", 1000.0)
        found = self.service.get_account_by_username("user1")
        self.assertEqual(acct.account_id, found.account_id)

    def test_list_accounts(self):
        self.service.create_account("user1", 1000.0)
        self.service.create_account("user2", 500.0)
        accounts = self.service.list_accounts()
        self.assertEqual(len(accounts), 2)


if __name__ == "__main__":
    unittest.main()
```