"""
This is a template for Project 1, Task 1 (Induced demand-supply)
"""
import copy
from enum import Enum
from fmclient import Agent, OrderSide, Order, OrderType, Session, Market
from typing import List

# Student details
SUBMISSION = {"number": "921322", "name": "Sidakpreet Mann"}

# ------ Add a variable called PROFIT_MARGIN -----
PROFIT_MARGIN = 10


# Enum for the roles of the bot
class Role(Enum):
    BUYER = 0
    SELLER = 1


# Let us define another enumeration to deal with the type of bot
class BotType(Enum):
    MARKET_MAKER = 0
    REACTIVE = 1


class DSBot(Agent):
    # ------ Add an extra argument bot_type to the constructor -----
    def __init__(self, account, email, password, marketplace_id, bot_type):
        super().__init__(account, email, password, marketplace_id, name="DSBot")
        self._public_market_id = 0
        self._private_market_id = 0
        self._role = None
        # ------ Add new class variable _bot_type to store the type of the bot
        self._bot_type = bot_type
        self._waiting_for_server = False
        self._tradeID = 0
        self._last_accepted_public_order_id = 0

    def role(self):
        return self._role

    def pre_start_tasks(self):
        pass

    def initialised(self):
        """
        Initialises bot
        Stores the market id parameters for Order Management
        """
        # dict to track market attributes
        markets_to_trade = self.markets
        for key in markets_to_trade:
            self.inform(markets_to_trade[key])

            # initialise market ids
            if markets_to_trade[key].private_market:
                self._private_market_id = key
            else:
                self._public_market_id = key

    def order_accepted(self, order: Order):
        self._waiting_for_server = False

        # track my last accepted public order
        if not order.is_private:
            self._last_accepted_public_order_id = order.fm_id
            self.inform(self._last_accepted_public_order_id)

    def order_rejected(self, info, order: Order):
        self._waiting_for_server = False

    def received_orders(self, orders: List[Order]):
        for o in orders:
            # if o.mine or o.is_private:
            self.inform(o)

        if self._bot_type == BotType.REACTIVE:
            self._react_to_market()

    def _react_to_market(self):
        # track best bid and asks
        best_bid, best_ask = self._get_best_bid_ask()

        # track state of order book
        num_private_orders, num_my_public_orders, my_stale_priv_order, \
            manager_order = self._get_order_book_state()

        # if i have ANY orders in the public book, it's stale, so cancel it
        if my_stale_priv_order is not None:
            self.inform(f"Stale order - {my_stale_priv_order.ref} being cleared.")
            self._cancel_order(my_stale_priv_order)
            self._last_accepted_public_order = None

        # PRIVATE ORDER CREATION ==============================================================
        # only create private order if public order traded successfully
        if (not self._last_accepted_public_order_id == 0) and \
                (self._last_accepted_public_order_id not in Order.current()):

            self._last_accepted_public_order_id = 0
            self.inform("Last public order traded just fine, create private order")

            is_private = True
            price = manager_order.price
            units = 1
            if self.role() == Role.BUYER:
                order_side = OrderSide.SELL
            else:
                order_side = OrderSide.BUY
            order_type = OrderType.LIMIT
            ref = self._tradeID
            self._create_new_order(price, units, order_side, order_type, ref, is_private)

        # PRIVATE ORDER CREATION ==============================================================

        self.inform(f"Best bid: {best_bid}, Best ask: {best_ask}")
        self.inform(f"{num_my_public_orders}, {num_private_orders}")

        # PUBLIC ORDER CREATION ===============================================================
        # stale orders should be cleared at this stage; there exists a private order
        # create an order based on best bid / ask
        if num_private_orders > 0 and not self._waiting_for_server:
            is_private = False
            self._create_profitable_order(best_ask, best_bid, manager_order, is_private)
        # PUBLIC ORDER CREATION ===============================================================

    def _cancel_order(self, order):
        cancel_order = copy.copy(order)
        cancel_order.order_type = OrderType.CANCEL
        cancel_order.ref = f"SM - Cancel - {order.ref}"
        self.send_order(cancel_order)

    def _create_new_order(self,
                          price: int,
                          units: int,
                          order_side: OrderSide,
                          order_type: OrderType,
                          ref: str,
                          is_private: bool):
        """
        :param price: determined price
        :param units: # of units to be submitted, fixed to 1
        :param order_side: buy or sell
        :param order_type: limit or market, fixed to limit
        :param ref: customer string of format "Order: {self._sent_order_count} - SM"
        :return:
        """
        new_order = Order.create_new()

        if is_private:
            market = self._private_market_id
            new_order.owner_or_target = "M000"
        else:
            market = self._public_market_id

        new_order.market = Market(market)
        new_order.price = price
        new_order.units = units
        new_order.order_side = order_side
        new_order.order_type = order_type
        new_order.ref = ref

        self.send_order(new_order)
        self._waiting_for_server = True
        self._tradeID += 1

    @staticmethod
    def _get_best_bid_ask():
        # initial bid and asks unrealistic / out of bound
        best_bid = 0
        best_ask = 999999

        for fm_id, order in Order.current().items():
            if not order.is_consumed and not order.is_private:
                if order.order_side == OrderSide.BUY and order.price > best_bid:
                    best_bid = order.price
                elif order.order_side == OrderSide.SELL and order.price < best_ask:
                    best_ask = order.price

        return best_bid, best_ask

    def _print_trade_opportunity(self, other_order):
        self.inform(f"I am a {self.role()} with profitable order {other_order}")

    def received_completed_orders(self, orders, market_id=None):
        pass

    def received_holdings(self, holdings):
        pass

    def received_session_info(self, session: Session):
        pass

    def _get_order_book_state(self):
        num_private_orders = 0
        manager_order = None
        num_my_public_orders = 0
        my_stale_priv_order = None

        for fm_id, order in Order.current().items():
            # if there is a private order not created by me
            if order.is_private and not order.mine:
                num_private_orders += 1
                manager_order = order

                # figure out our role based on private order
                if manager_order.order_side == OrderSide.BUY:
                    self._role = Role.BUYER
                else:
                    self._role = Role.SELLER

            # if i created a public order that DID NOT EXECUTE IMMEDIATELY
            elif not order.is_private and order.mine:
                num_my_public_orders += 1
                my_stale_priv_order = order

        return num_private_orders, num_my_public_orders, my_stale_priv_order, manager_order

    def _create_profitable_order(self, best_ask, best_bid, manager_order, is_private):
        # if buyer
        if self.role() == Role.BUYER:
            # if the best selling price is less than
            # or equal to the price we want to buy at, submit order
            if best_ask <= manager_order.price - PROFIT_MARGIN:
                price = manager_order.price - PROFIT_MARGIN
                units = 1
                order_side = OrderSide.BUY
                order_type = OrderType.LIMIT
                ref = f"SM - {order_side}-{self._tradeID}"
                self._create_new_order(price, units, order_side, order_type, ref, is_private)

        # if we are sellers
        else:
            # if the best asking price is more than
            # or equal to the price we want to sell at, submit order
            if best_bid >= manager_order.price + PROFIT_MARGIN:
                price = manager_order.price + PROFIT_MARGIN
                units = 1
                order_side = OrderSide.SELL
                order_type = OrderType.LIMIT
                ref = f"SM - {order_side}-{self._tradeID}"
                self._create_new_order(price, units, order_side, order_type, ref, is_private)


if __name__ == "__main__":
    FM_ACCOUNT = "ardent-founder"
    FM_EMAIL = "s.mann4@student.unimelb.edu.au"
    FM_PASSWORD = "921322"
    MARKETPLACE_ID = 898

    # B_TYPE = BotType.MARKET_MAKER
    B_TYPE = BotType.REACTIVE

    ds_bot = DSBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID, B_TYPE)
    ds_bot.run()
