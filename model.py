#!/usr/bin/env python3
"""
Unit-economics model for the voice hair-try-on app.
All assumptions are explicit below — change them and re-run.
Numbers are illustrative (2026 ballpark), not a forecast.
"""

# ---- ASSUMPTIONS (edit these) ----------------------------------------------
COST_PER_CLIP   = 0.10    # all-in: GPU + storage/bw + STT + Claude parse (smart pipeline)
PAID_PRICE      = 9.99    # monthly subscription
STRIPE_PCT      = 0.029   # payment processing %
STRIPE_FIXED    = 0.30    # payment processing fixed fee per charge
CONVERSION      = 0.05    # free -> paid (consumer freemium is typically 2-5%)
PAID_CLIPS_MO   = 25      # avg clips a PAID user generates / month
FREE_CLIPS_MO   = 1.5     # avg clips a FREE active user generates / month
PAID_CHURN_MO   = 0.08    # monthly churn of paid users -> lifetime = 1/churn
FIXED_OPEX_MO   = 40_000  # team + baseline infra (illustrative seed-stage burn)
TIERS           = [1_000, 10_000, 100_000]   # total users (free + paid)
LTV_CAC_TARGET  = 3.0     # healthy LTV:CAC ratio


def per_user_econ(cost_per_clip=COST_PER_CLIP, conversion=CONVERSION):
    fee = PAID_PRICE * STRIPE_PCT + STRIPE_FIXED
    paid_cogs = PAID_CLIPS_MO * cost_per_clip
    paid_contrib = PAID_PRICE - fee - paid_cogs          # $/paid user/month
    free_cost = FREE_CLIPS_MO * cost_per_clip            # $/free user/month
    blended = conversion * paid_contrib - (1 - conversion) * free_cost
    return fee, paid_cogs, paid_contrib, free_cost, blended


def main():
    fee, paid_cogs, paid_contrib, free_cost, blended = per_user_econ()
    lifetime_mo = 1 / PAID_CHURN_MO
    ltv_paid = paid_contrib * lifetime_mo
    max_cac_per_paid = ltv_paid / LTV_CAC_TARGET
    # to acquire 1 paying user you must acquire 1/CONVERSION total users:
    max_cac_per_signup = max_cac_per_paid * CONVERSION

    print("="*64)
    print("PER-USER ECONOMICS (monthly)")
    print("="*64)
    print(f"  Paid subscription price            ${PAID_PRICE:>8.2f}")
    print(f"  - payment fee                      ${fee:>8.2f}")
    print(f"  - generation COGS ({PAID_CLIPS_MO} clips)      ${paid_cogs:>8.2f}")
    print(f"  = contribution / PAID user         ${paid_contrib:>8.2f}")
    print(f"  Cost / FREE active user ({FREE_CLIPS_MO} clips)  ${-free_cost:>8.2f}")
    print(f"  Blended contribution / TOTAL user  ${blended:>8.3f}")
    print(f"  (conversion {CONVERSION:.0%}, so {1/CONVERSION:.0f} signups per paying user)")
    print()
    print(f"  Paid lifetime (1/churn)            {lifetime_mo:>6.1f} months")
    print(f"  LTV per paid user                  ${ltv_paid:>8.2f}")
    print(f"  Max CAC / paid user (LTV:CAC {LTV_CAC_TARGET:.0f}:1) ${max_cac_per_paid:>8.2f}")
    print(f"  Max CAC / signup                   ${max_cac_per_signup:>8.2f}")
    print()

    print("="*64)
    print("MONTHLY P&L BY SCALE  (steady state, CAC excluded)")
    print("="*64)
    hdr = f"{'total users':>12} {'paid':>8} {'revenue':>11} {'COGS':>10} {'gross':>11} {'op profit':>12}"
    print(hdr); print("-"*len(hdr))
    for n in TIERS:
        paid = n * CONVERSION
        free = n - paid
        revenue = paid * PAID_PRICE
        cogs = paid * (fee + paid_cogs) + free * free_cost   # fees counted as cost here
        gross = revenue - cogs
        op = gross - FIXED_OPEX_MO
        print(f"{n:>12,} {paid:>8,.0f} ${revenue:>10,.0f} ${cogs:>9,.0f} ${gross:>10,.0f} ${op:>11,.0f}")
    print()

    # break-even user count to cover fixed opex from contribution
    if blended > 0:
        be = FIXED_OPEX_MO / blended
        print(f"Break-even scale: {be:,.0f} total users to cover ${FIXED_OPEX_MO:,}/mo fixed")
    else:
        print("Blended contribution is NEGATIVE — more users LOSE more money. "
              "Fix unit economics before scaling.")
    print()

    print("="*64)
    print("SENSITIVITY: break-even users vs cost/clip x conversion")
    print("="*64)
    costs = [0.04, 0.07, 0.10, 0.20]
    convs = [0.03, 0.05, 0.08, 0.12]
    print(f"{'cost/clip':>10} | " + " ".join(f"conv {c:>4.0%}" for c in convs))
    print("-"*52)
    for c in costs:
        row = [f"${c:>7.2f} |"]
        for v in convs:
            _, _, _, _, b = per_user_econ(cost_per_clip=c, conversion=v)
            row.append(f"{FIXED_OPEX_MO/b/1000:>7.0f}k" if b > 0 else "   neg ")
        print(" ".join(row))
    print("\n(cells = total users needed to break even on fixed opex; 'neg' = "
          "free tier outweighs paid margin → unprofitable at any scale)")


if __name__ == "__main__":
    main()
