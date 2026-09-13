from decimal import Decimal, getcontext


def leibniz_pi_over4(n_terms: int) -> Decimal:
    """Compute S = 1 - 1/3 + 1/5 - ... for n_terms terms (odd denominators).

    Term k (0-indexed): sign = +1 if k even else -1
    denominator = 2*k + 1
    term = sign / denominator
    """
    # Guard digits: sum of 1/n series up to 1e6; pi/4 ~ 0.785.
    # Use extra precision for stability.
    getcontext().prec = 50

    total = Decimal(0)
    for k in range(n_terms):
        denom = 2 * k + 1
        if k % 2 == 0:
            total += Decimal(1) / Decimal(denom)
        else:
            total -= Decimal(1) / Decimal(denom)
    return total


def main() -> None:
    n_terms = 1_000_000
    s = leibniz_pi_over4(n_terms)
    result = s * Decimal(4)  # multiplying the total by 4
    print(result)


if __name__ == "__main__":
    main()
