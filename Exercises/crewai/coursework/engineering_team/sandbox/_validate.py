"""Validation script: ensures app.py imports and Blocks constructs without error."""

import sys


def main() -> int:
    import app  # importing constructs `demo` at module load
    import gradio as gr

    assert hasattr(app, "demo"), "app.py must define a top-level `demo` object"
    assert isinstance(app.demo, gr.Blocks), f"`demo` should be gr.Blocks, got {type(app.demo)}"

    # Also make sure build_demo() can be invoked directly to construct a fresh Blocks.
    fresh = app.build_demo()
    assert isinstance(fresh, gr.Blocks), "build_demo() must return gr.Blocks"

    # Sanity-check a few handlers so we know the wiring imports/executes cleanly.
    status, acct_id, dropdown_update, h, t, a, s = app.create_account_handler(
        "validator_user", 1000.0, None
    )
    assert acct_id is not None, "create_account_handler should set an account id"
    assert "created" in status.lower(), f"unexpected status: {status}"

    status, h, t, s = app.deposit_handler(acct_id, 250.0)
    assert "deposited" in status.lower(), f"unexpected deposit status: {status}"

    status, h, t, s = app.buy_handler(acct_id, "AAPL", 2)
    assert "bought" in status.lower(), f"unexpected buy status: {status}"

    status, h, t, s = app.sell_handler(acct_id, "AAPL", 1)
    assert "sold" in status.lower(), f"unexpected sell status: {status}"

    # Error path: withdraw too much
    status, h, t, s = app.withdraw_handler(acct_id, 10_000_000.0)
    assert status.startswith("❌"), f"expected error status, got: {status}"

    print("OK: app.demo constructed, build_demo() works, handlers execute cleanly.")
    print(f"    demo type: {type(app.demo).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
