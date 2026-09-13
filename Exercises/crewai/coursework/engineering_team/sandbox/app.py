"""Gradio UI for the Trading Simulation Account Management System."""

from __future__ import annotations

from typing import Any

import gradio as gr
from backend import (
    Account,
    AccountService,
    Holding,
    PortfolioSnapshot,
    TradingError,
    Transaction,
)

# --- Single shared backend service (single-user demo) ---
service = AccountService()

SUPPORTED_SYMBOLS = ["AAPL", "TSLA", "GOOGL"]


# ---------- Formatting helpers ----------


def snapshot_to_summary_dict(snapshot: PortfolioSnapshot) -> dict[str, Any]:
    return {
        "account_id": snapshot.account_id,
        "username": snapshot.username,
        "as_of": snapshot.as_of.isoformat(),
        "cash_balance": round(snapshot.cash_balance, 2),
        "holdings_value": round(snapshot.holdings_value, 2),
        "total_value": round(snapshot.total_value, 2),
        "total_deposits": round(snapshot.total_deposits, 2),
        "total_withdrawals": round(snapshot.total_withdrawals, 2),
        "net_contributions": round(snapshot.net_contributions, 2),
        "profit_loss": round(snapshot.profit_loss, 2),
        "profit_loss_percent": round(snapshot.profit_loss_percent, 4),
    }


def holdings_to_rows(holdings: list[Holding]) -> list[list[Any]]:
    return [
        [h.symbol, h.quantity, round(h.current_price, 2), round(h.market_value, 2)]
        for h in holdings
    ]


def transactions_to_rows(transactions: list[Transaction]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for t in transactions:
        rows.append(
            [
                t.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                t.transaction_type.value,
                t.symbol or "",
                t.quantity if t.quantity is not None else 0,
                round(t.price, 2) if t.price is not None else 0.0,
                round(t.amount, 2),
                round(t.cash_balance_after, 2),
                t.description,
            ]
        )
    return rows


def accounts_to_rows(accounts: list[Account]) -> list[list[Any]]:
    return [
        [
            a.account_id,
            a.username,
            a.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            round(a.cash_balance, 2),
            round(a.initial_deposit, 2),
        ]
        for a in accounts
    ]


def empty_summary() -> dict[str, Any]:
    return {"message": "No account selected."}


def empty_rows() -> list[list[Any]]:
    return []


def account_choices() -> list[tuple[str, str]]:
    """Return dropdown choices as (label, value) pairs for the account selector."""
    return [(f"{a.username} ({a.account_id[:12]}…)", a.account_id) for a in service.list_accounts()]


def _refresh_all(
    account_id: str | None,
) -> tuple[list[list[Any]], list[list[Any]], list[list[Any]], dict[str, Any]]:
    accounts_rows = accounts_to_rows(service.list_accounts())
    if not account_id:
        return empty_rows(), empty_rows(), accounts_rows, empty_summary()
    try:
        snap = service.get_portfolio_snapshot(account_id)
        holdings_rows = holdings_to_rows(snap.holdings)
        txns_rows = transactions_to_rows(service.list_transactions(account_id))
        summary = snapshot_to_summary_dict(snap)
        return holdings_rows, txns_rows, accounts_rows, summary
    except TradingError as e:
        return empty_rows(), empty_rows(), accounts_rows, {"error": str(e)}


# ---------- Handlers ----------


def create_account_handler(
    username: str,
    initial_deposit: float,
    current_account_id: str | None,
):
    username = (username or "").strip()
    if not username:
        holdings_rows, txns_rows, accounts_rows, summary = _refresh_all(current_account_id)
        return (
            "❌ Username cannot be empty.",
            current_account_id,
            gr.update(choices=account_choices(), value=current_account_id),
            holdings_rows,
            txns_rows,
            accounts_rows,
            summary,
        )
    try:
        acct = service.create_account(username, float(initial_deposit or 0))
        holdings_rows, txns_rows, accounts_rows, summary = _refresh_all(acct.account_id)
        return (
            f"✅ Account created for '{acct.username}' with ${acct.initial_deposit:,.2f}.",
            acct.account_id,
            gr.update(choices=account_choices(), value=acct.account_id),
            holdings_rows,
            txns_rows,
            accounts_rows,
            summary,
        )
    except TradingError as e:
        holdings_rows, txns_rows, accounts_rows, summary = _refresh_all(current_account_id)
        return (
            f"❌ {e}",
            current_account_id,
            gr.update(choices=account_choices(), value=current_account_id),
            holdings_rows,
            txns_rows,
            accounts_rows,
            summary,
        )


def deposit_handler(account_id: str | None, amount: float):
    if not account_id:
        h, t, _, s = _refresh_all(account_id)
        return "❌ No account selected. Create or select one first.", h, t, s
    try:
        txn = service.deposit(account_id, float(amount or 0))
        h, t, _, s = _refresh_all(account_id)
        return (
            f"✅ Deposited ${txn.amount:,.2f}. New cash balance: ${txn.cash_balance_after:,.2f}.",
            h,
            t,
            s,
        )
    except TradingError as e:
        h, t, _, s = _refresh_all(account_id)
        return f"❌ {e}", h, t, s


def withdraw_handler(account_id: str | None, amount: float):
    if not account_id:
        h, t, _, s = _refresh_all(account_id)
        return "❌ No account selected. Create or select one first.", h, t, s
    try:
        txn = service.withdraw(account_id, float(amount or 0))
        h, t, _, s = _refresh_all(account_id)
        return (
            f"✅ Withdrew ${txn.amount:,.2f}. New cash balance: ${txn.cash_balance_after:,.2f}.",
            h,
            t,
            s,
        )
    except TradingError as e:
        h, t, _, s = _refresh_all(account_id)
        return f"❌ {e}", h, t, s


def buy_handler(account_id: str | None, symbol: str, quantity: float):
    if not account_id:
        h, t, _, s = _refresh_all(account_id)
        return "❌ No account selected. Create or select one first.", h, t, s
    try:
        qty = int(quantity or 0)
        txn = service.buy_shares(account_id, symbol, qty)
        h, t, _, s = _refresh_all(account_id)
        return (
            f"✅ Bought {txn.quantity} × {txn.symbol} @ ${txn.price:,.2f} (total ${txn.amount:,.2f}).",
            h,
            t,
            s,
        )
    except TradingError as e:
        h, t, _, s = _refresh_all(account_id)
        return f"❌ {e}", h, t, s
    except (TypeError, ValueError):
        h, t, _, s = _refresh_all(account_id)
        return "❌ Quantity must be a whole number.", h, t, s


def sell_handler(account_id: str | None, symbol: str, quantity: float):
    if not account_id:
        h, t, _, s = _refresh_all(account_id)
        return "❌ No account selected. Create or select one first.", h, t, s
    try:
        qty = int(quantity or 0)
        txn = service.sell_shares(account_id, symbol, qty)
        h, t, _, s = _refresh_all(account_id)
        return (
            f"✅ Sold {txn.quantity} × {txn.symbol} @ ${txn.price:,.2f} (proceeds ${txn.amount:,.2f}).",
            h,
            t,
            s,
        )
    except TradingError as e:
        h, t, _, s = _refresh_all(account_id)
        return f"❌ {e}", h, t, s
    except (TypeError, ValueError):
        h, t, _, s = _refresh_all(account_id)
        return "❌ Quantity must be a whole number.", h, t, s


def refresh_handler(account_id: str | None):
    h, t, a, s = _refresh_all(account_id)
    msg = "🔄 Refreshed." if account_id else "🔄 Refreshed. No account selected."
    return msg, h, t, a, s


def select_account_handler(selected_account_id: str | None):
    if not selected_account_id:
        return "No account selected.", None, empty_rows(), empty_rows(), empty_summary()
    h, t, _, s = _refresh_all(selected_account_id)
    return f"📌 Selected account {selected_account_id[:14]}…", selected_account_id, h, t, s


# ---------- Theme & CSS ----------

# Palette: gold #ecad0a, blue #209dd7, purple #753991
PRIMARY = "#209dd7"  # blue
ACCENT = "#ecad0a"  # gold
DEEP = "#753991"  # purple

CUSTOM_CSS = f"""
:root {{
    --brand-blue: {PRIMARY};
    --brand-gold: {ACCENT};
    --brand-purple: {DEEP};
}}

#app-header {{
    padding: 18px 22px;
    border-radius: 14px;
    background: linear-gradient(135deg, {DEEP} 0%, {PRIMARY} 60%, {ACCENT} 130%);
    color: #ffffff !important;
    margin-bottom: 12px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.15);
}}
#app-header h1, #app-header p {{
    color: #ffffff !important;
    margin: 0;
}}
#app-header h1 {{
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: 0.2px;
}}
#app-header p {{
    opacity: 0.92;
    margin-top: 4px;
    font-size: 0.95rem;
}}

.brand-card {{
    border: 1px solid rgba(128,128,128,0.25);
    border-radius: 12px;
    padding: 14px 16px;
    background: var(--background-fill-secondary);
}}

.brand-badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #ffffff;
    background: {PRIMARY};
    margin-right: 6px;
}}
.brand-badge.gold {{ background: {ACCENT}; color: #2b2b2b; }}
.brand-badge.purple {{ background: {DEEP}; }}

/* Primary buttons nudge - the theme supplies blue, this reinforces on hover */
button.primary:hover {{
    filter: brightness(1.08);
}}

/* Footer note */
#footer-note {{
    text-align: center;
    opacity: 0.75;
    font-size: 0.85rem;
    margin-top: 8px;
}}
"""

THEME = gr.themes.Soft(
    primary_hue=gr.themes.Color(
        c50="#e6f4fb",
        c100="#c5e6f5",
        c200="#9ed4ee",
        c300="#6ec1e5",
        c400="#43aedd",
        c500=PRIMARY,
        c600="#1c8bc0",
        c700="#166f9a",
        c800="#0f5474",
        c900="#0a3a51",
        c950="#062633",
    ),
    secondary_hue=gr.themes.Color(
        c50="#f3e9f5",
        c100="#e0c9e6",
        c200="#c99cd3",
        c300="#b06ec0",
        c400="#9750ab",
        c500=DEEP,
        c600="#5f2e75",
        c700="#4a2459",
        c800="#361a40",
        c900="#241128",
        c950="#150a18",
    ),
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
)


# ---------- UI ----------


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Trading Simulation Account Manager") as demo:
        current_account_id = gr.State(value=None)

        gr.HTML(
            """
            <div id="app-header">
                <h1>📈 Trading Simulation — Account Manager</h1>
                <p>Create an account, manage cash, and trade simulated shares of
                <b>AAPL</b>, <b>TSLA</b>, and <b>GOOGL</b>.</p>
            </div>
            """
        )

        with gr.Row():
            status_box = gr.Textbox(
                label="Status",
                value="Welcome! Create an account below to get started.",
                interactive=False,
                lines=1,
            )

        with gr.Tabs():
            # ---------- Tab 1: Account ----------
            with gr.Tab("👤 Account"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Create Account")
                        with gr.Group(elem_classes=["brand-card"]):
                            username_in = gr.Textbox(label="Username", placeholder="e.g. alice")
                            initial_deposit_in = gr.Number(
                                label="Initial Deposit ($)", value=10000, minimum=0.01, precision=2
                            )
                            create_btn = gr.Button("Create Account", variant="primary")

                    with gr.Column(scale=1):
                        gr.Markdown("### Select Existing Account")
                        with gr.Group(elem_classes=["brand-card"]):
                            account_selector = gr.Dropdown(
                                label="Active Account",
                                choices=account_choices(),
                                value=None,
                                interactive=True,
                            )
                            select_btn = gr.Button("Use Selected Account", variant="secondary")
                            refresh_btn = gr.Button("🔄 Refresh All", variant="secondary")

                gr.Markdown("### All Accounts")
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
                    wrap=True,
                )

            # ---------- Tab 2: Cash ----------
            with gr.Tab("💵 Cash"):
                gr.Markdown(
                    "Manage cash deposits and withdrawals for the currently selected account."
                )
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Deposit")
                        with gr.Group(elem_classes=["brand-card"]):
                            deposit_amount = gr.Number(
                                label="Amount ($)", value=500, minimum=0.01, precision=2
                            )
                            deposit_btn = gr.Button("Deposit Funds", variant="primary")
                    with gr.Column():
                        gr.Markdown("#### Withdraw")
                        with gr.Group(elem_classes=["brand-card"]):
                            withdraw_amount = gr.Number(
                                label="Amount ($)", value=100, minimum=0.01, precision=2
                            )
                            withdraw_btn = gr.Button("Withdraw Funds", variant="primary")

            # ---------- Tab 3: Trading ----------
            with gr.Tab("📊 Trading"):
                gr.Markdown(
                    "Buy or sell shares in the currently selected account. "
                    "Prices: **AAPL $150.00**, **TSLA $250.00**, **GOOGL $2800.00**."
                )
                with gr.Row():
                    with gr.Column():
                        with gr.Group(elem_classes=["brand-card"]):
                            symbol_in = gr.Dropdown(
                                label="Symbol",
                                choices=SUPPORTED_SYMBOLS,
                                value="AAPL",
                                interactive=True,
                            )
                            quantity_in = gr.Number(
                                label="Quantity", value=1, minimum=1, precision=0
                            )
                            with gr.Row():
                                buy_btn = gr.Button("Buy", variant="primary")
                                sell_btn = gr.Button("Sell", variant="secondary")

                    with gr.Column():
                        gr.HTML(
                            """
                            <div class="brand-card">
                                <div style="margin-bottom:8px;">
                                    <span class="brand-badge">AAPL</span>
                                    <span class="brand-badge gold">TSLA</span>
                                    <span class="brand-badge purple">GOOGL</span>
                                </div>
                                <p style="margin:6px 0 0 0; opacity:0.85; font-size:0.9rem;">
                                    Buys are rejected if cash is insufficient. Sells are rejected
                                    if you don't own enough shares. All actions are recorded.
                                </p>
                            </div>
                            """
                        )

            # ---------- Tab 4: Portfolio ----------
            with gr.Tab("📁 Portfolio"):
                gr.Markdown("### Account Summary")
                summary_json = gr.JSON(label="Snapshot", value=empty_summary())

                gr.Markdown("### Current Holdings")
                holdings_df = gr.Dataframe(
                    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
                    datatype=["str", "number", "number", "number"],
                    interactive=False,
                    wrap=True,
                )

                gr.Markdown("### Transaction History")
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
                    wrap=True,
                )

        gr.HTML(
            '<div id="footer-note">Trading Simulation Demo · single-user in-memory session</div>'
        )

        # ---------- Wire up events ----------
        create_btn.click(
            fn=create_account_handler,
            inputs=[username_in, initial_deposit_in, current_account_id],
            outputs=[
                status_box,
                current_account_id,
                account_selector,
                holdings_df,
                transactions_df,
                accounts_df,
                summary_json,
            ],
        )

        select_btn.click(
            fn=select_account_handler,
            inputs=[account_selector],
            outputs=[status_box, current_account_id, holdings_df, transactions_df, summary_json],
        )

        refresh_btn.click(
            fn=refresh_handler,
            inputs=[current_account_id],
            outputs=[status_box, holdings_df, transactions_df, accounts_df, summary_json],
        )

        deposit_btn.click(
            fn=deposit_handler,
            inputs=[current_account_id, deposit_amount],
            outputs=[status_box, holdings_df, transactions_df, summary_json],
        )

        withdraw_btn.click(
            fn=withdraw_handler,
            inputs=[current_account_id, withdraw_amount],
            outputs=[status_box, holdings_df, transactions_df, summary_json],
        )

        buy_btn.click(
            fn=buy_handler,
            inputs=[current_account_id, symbol_in, quantity_in],
            outputs=[status_box, holdings_df, transactions_df, summary_json],
        )

        sell_btn.click(
            fn=sell_handler,
            inputs=[current_account_id, symbol_in, quantity_in],
            outputs=[status_box, holdings_df, transactions_df, summary_json],
        )

    return demo


demo = build_demo()


if __name__ == "__main__":
    demo.launch(theme=THEME, css=CUSTOM_CSS)
