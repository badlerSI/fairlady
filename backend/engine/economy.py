"""Economy: gas pricing, fueling math, lodging, and the cash-vs-card decision."""
from __future__ import annotations
from typing import Optional

from config import DEFAULT_GAS_PRICE, LODGING_PRICE, LITERS_PER_GALLON
from engine.state import GameState, Place


def gas_price(place: Place) -> float:
    if place.gas_price is not None:
        return float(place.gas_price)
    return DEFAULT_GAS_PRICE.get(place.region, 4.49)


def lodging_options(place: Place) -> list:
    """[(label, nightly_price)] available where you are."""
    if not place.has("lodging"):
        return []
    if place.kind == "park":
        return [("lodge", LODGING_PRICE["lodge"]), ("camp", LODGING_PRICE["camp"])]
    return [("motel", LODGING_PRICE["motel"]), ("camp", LODGING_PRICE["camp"])]


def pay(state: GameState, amount: float, prefer: Optional[str] = None) -> dict:
    """Charge `amount` to cash or card. Returns {ok, method, amount, message}.
    `prefer` overrides state.pay_method for this transaction."""
    amount = round(max(0.0, amount), 2)
    if amount == 0:
        return {"ok": True, "method": "none", "amount": 0.0, "message": ""}
    order = []
    first = (prefer or state.pay_method)
    order = ["cash", "card"] if first == "cash" else ["card", "cash"]
    for m in order:
        if m == "cash" and state.cash + 1e-9 >= amount:
            state.cash = round(state.cash - amount, 2)
            return {"ok": True, "method": "cash", "amount": amount, "message": "Paid cash."}
        if m == "card" and state.credit_available + 1e-9 >= amount:
            state.card_balance = round(state.card_balance + amount, 2)
            return {"ok": True, "method": "card", "amount": amount,
                    "message": "Swiped the card."}
    return {"ok": False, "method": None, "amount": amount,
            "message": "Declined. Not enough cash and the card won't cover it."}


def max_affordable(state: GameState, prefer: Optional[str] = None) -> float:
    first = (prefer or state.pay_method)
    if first == "cash":
        return round(max(state.cash, state.credit_available), 2)
    return round(max(state.credit_available, state.cash), 2)


def quote_fuel(state: GameState, place: Place, *, dollars: Optional[float] = None,
               liters: Optional[float] = None, gallons: Optional[float] = None,
               fill: bool = False, prefer: Optional[str] = None) -> dict:
    """Compute a fuel purchase WITHOUT mutating state. Clamps to tank room and money.
    Returns {price, liters, gallons, cost, room_l, capped_by}."""
    price = gas_price(place)                 # $/gal
    room_l = round(state.tank_l - state.fuel_l, 3)
    capped_by = None

    if fill or (dollars is None and liters is None and gallons is None):
        want_l = room_l
    elif dollars is not None:
        want_l = (max(0.0, dollars) / price) * LITERS_PER_GALLON
    elif gallons is not None:
        want_l = max(0.0, gallons) * LITERS_PER_GALLON
    else:
        want_l = max(0.0, liters)

    buy_l = want_l
    if buy_l > room_l:
        buy_l, capped_by = room_l, "tank"

    cost = (buy_l / LITERS_PER_GALLON) * price
    budget = max_affordable(state, prefer)
    if cost > budget + 1e-9:
        # buy only as much as the wallet covers
        buy_l = (budget / price) * LITERS_PER_GALLON
        if buy_l < want_l:
            capped_by = "money"
        cost = (buy_l / LITERS_PER_GALLON) * price

    return {
        "price": round(price, 2),
        "liters": round(buy_l, 2),
        "gallons": round(buy_l / LITERS_PER_GALLON, 2),
        "cost": round(cost, 2),
        "room_l": room_l,
        "capped_by": capped_by,
    }
