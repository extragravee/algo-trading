"""
FNCE30010 - Algorithmic Trading
Assignment 1
Sidakpreet Mann
921322

Notes:
    1. Profitable trade printing only implemented for reactive bot type
    2. In reactive type, if order does not immediately trade, it remains in the book
    3. Orders are rounded such that the mod price tick is subtracted from the price
        This is done as profit margins can just be increased to offset this
    4. One action is performed per update received, to account for time delays and efficiency

What to do better next time:
    1. Track my own orders in a dict while they are active
    2. Track my cancelled orders in a separate dict
    3. Track manager orders in a separate dict
    4. At each update, check if they are in Order.current(), and make decisions based on
        the remaining quantity of the manager order / internal incentive
    5. Subclass the strategies, really messy to have it all in one file
    6. Avoid manual tracking of all orders, go with the provided functions
        of the web socket as they are rigorously tested
    7. Async techniques, and how to use them effectively
"""
import copy
from enum import Enum
from fmclient import Agent, OrderSide, Order, OrderType, Session, Market
from typing import List

# Student details
SUBMISSION = {"number": "921322", "name": "Sidakpreet Mann"}

# ------ Add a variable called PROFIT_MARGIN -----
PROFIT_MARGIN = 10
MAX_PRICE = 1000
MANAGER_ID = "M000"


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

        # async order management
        self._waiting_for_server = False
        self._tradeID = 0
        self._last_accepted_public_order_id = 0
        self._units_to_trade = 0

        # holdings trackers
        self._cash_available = 0
        self._cash = 0
        self._assets = {}
        self._private_widgets_available = 0
        self._public_widgets_available = 0

        self._priv_orders = {}

        # market state trackers
        self._session_is_open = False
        self._price_tick = 1

    # MARKET MAKER FUNCTIONALITY ##########################################################
    def _make_market(self):

        # get order book state summary
        num_private_orders, num_my_public_orders, my_stale_priv_order, \
            manager_order = self._get_order_book_state()

        if num_private_orders == 0:
            self._units_to_trade = 0

        # CANCELLING STALE ORDERS =========================================================
        if num_my_public_orders > 0 and self._units_to_trade < 1 and \
                not self._waiting_for_server:
            self._waiting_for_server = True
            self._cancel_order(my_stale_priv_order)
            self._last_accepted_public_order_id = 0
            return

        # PRIVATE ORDER CREATION ==========================================================
        # need to confirm that the last sent order traded, and manager order > 0

        if (self._last_accepted_public_order_id not in Order.current()) \
                and (self._units_to_trade > 0) and (not self._last_accepted_public_order_id == 0) \
                and (num_my_public_orders == 0):

            # determine order attributes
            is_private = True
            price = manager_order.price
            units = 1
            order_side = None

            if self.role() == Role.BUYER:
                order_side = OrderSide.SELL
            elif self.role() == Role.SELLER:
                order_side = OrderSide.BUY

            order_type = OrderType.LIMIT
            ref = f"Private order - {self._tradeID}"

            if not self._waiting_for_server:
                self._last_accepted_public_order_id = 0
                self._units_to_trade -= 1
                self._create_new_order(price, units, order_side, order_type, ref, is_private)
                return
        # END PRIVATE ORDER CREATION ======================================================

        # PUBLIC ORDER CREATION ===========================================================
        # no order of mine in the public market, but there is a private request
        # num_private_orders, num_my_public_orders, my_stale_priv_order, \
        #     manager_order = self._get_order_book_state()
        self.inform(f"{num_my_public_orders}, {num_private_orders}, remaining trades => {self._units_to_trade}")
        self.inform(self._priv_orders)

        # if units are >= 1, it over trades one, if its > 1 it under trades one, what the fuck?
        if self._units_to_trade > 0 and num_my_public_orders == 0 and \
                not self._waiting_for_server:
            self._waiting_for_server = True
            # self.inform("Creating public order.")
            # determine order attributes
            is_private = False

            if self.role() == Role.BUYER:
                order_side = OrderSide.BUY
                price = manager_order.price - PROFIT_MARGIN
            else:
                order_side = OrderSide.SELL
                price = manager_order.price + PROFIT_MARGIN

            units = 1
            order_type = OrderType.LIMIT
            ref = f"Public order - {self._tradeID}"
            if self.role() == Role.BUYER:
                if self._cash_available >= price:
                    self._waiting_for_server = True
                    self._create_new_order(price, units, order_side, order_type, ref, is_private)
                else:
                    self.inform(f"Not enough cash to trade.")
            else:
                if self.role() == Role.SELLER:
                    if self._public_widgets_available > 0:
                        self._waiting_for_server = True
                        self._create_new_order(price, units, order_side, order_type, ref, is_private)
                    else:
                        self.inform(f"Not enough widgets to trade.")
            return
        # END PUBLIC ORDER CREATION =======================================================
    # SHARED FUNCTIONALITY ################################################################

    def role(self):
        return self._role

    def pre_start_tasks(self):
        pass

    def received_holdings(self, holdings):
        """
        Tracks the portfolio holdings
        :param holdings: attributes of interest cash, cash_available, assets
        """
        # track cash assets
        self._cash = holdings.cash
        self._cash_available = holdings.cash_available

        # dict to track units of widgets and private widgets
        self._assets = holdings.assets

        # track available public and private units
        for key in self._assets:
            if key.fm_id == self._public_market_id:
                self._public_widgets_available = self._assets[key].units_available
            elif key.fm_id == self._private_market_id:
                self._private_widgets_available = self._assets[key].units_available

    def initialised(self):
        """
        Initialises bot
        Stores the market id parameters for Order Management
        """
        # dict to track market attributes
        markets_to_trade = self.markets

        for key in markets_to_trade:
            self.inform(markets_to_trade[key])

            # initialise public and private market IDs
            if markets_to_trade[key].private_market:
                self._private_market_id = key
            else:
                self._public_market_id = key

        # track public market price tick
        self._price_tick = Market(self._public_market_id).price_tick

    def order_accepted(self, order: Order):
        """
        Notifies last order being accepted
        Async - no longer waiting for the server
        :param order: previous accepted order
        """
        self._waiting_for_server = False

        # track my last accepted public order by fm_id
        if not order.is_private and (not order.order_type == OrderType.CANCEL):
            self._last_accepted_public_order_id = order.fm_id

    def order_rejected(self, info, order: Order):
        """
        Notifies last order being rejected
        Async - no longer waiting for the server
        :param info: details of rejected order
        :param order: previous rejected order
        """
        self._waiting_for_server = False

    def received_orders(self, orders: List[Order]):
        """
        Subscriber to order updates
        Notifies new updates in the market
        :param orders: list of order objects (updates)
        """
        # only call strategies if current session is open
        if not self._session_is_open:
            return

        # call appropriate strategy based on bot type
        if self._bot_type == BotType.REACTIVE:
            self._react_to_market()
        elif self._bot_type == BotType.MARKET_MAKER:
            self._make_market()

    def _create_new_order(self,
                          price: int,
                          units: int,
                          order_side: OrderSide,
                          order_type: OrderType,
                          ref: str,
                          is_private: bool):
        """
        Creates a new order given the parameters
        :param price: determined price
        :param units: # of units to be submitted, fixed to 1
        :param order_side: buy or sell
        :param order_type: limit or market, fixed to limit
        :param ref: customer string of format "Order: {self._sent_order_count} - SM"
        :return:
        """

        new_order = Order.create_new()

        # derive order attributes
        if is_private:
            market = self._private_market_id
            new_order.owner_or_target = MANAGER_ID
        else:
            market = self._public_market_id

            # make sure price is rounded in the public market
            price -= price % self._price_tick

            # in case price goes less than the tick, or more than ten
            # set prices to the bounds
            if price < self._price_tick:
                price = self._price_tick
            elif price > MAX_PRICE:
                price = MAX_PRICE

        new_order.market = Market(market)
        new_order.price = price
        new_order.units = units
        new_order.order_side = order_side
        new_order.order_type = order_type
        new_order.ref = ref

        # send order through
        self._waiting_for_server = True
        self.send_order(new_order)

        self._tradeID += 1

    def _cancel_order(self, order):
        """
        Helper function to cancel given order
        :param order: order to be cancelled
        """

        self._waiting_for_server = True

        cancel_order = copy.copy(order)
        cancel_order.order_type = OrderType.CANCEL
        cancel_order.ref = f"SM - Cancel - {order.ref}"

        self.send_order(cancel_order)

    def received_completed_orders(self, orders, market_id=None):
        pass

    def received_session_info(self, session: Session):

        # when bot is running and session is reset, reset appropriate variables
        if session.is_open:
            self._waiting_for_server = False
            self._tradeID = 0
            self._last_accepted_public_order_id = 0

            self._assets = {}
            self._units_to_trade = 0
            self._session_is_open = True

        else:
            self._session_is_open = False

    # REACTIVE FUNCTIONALITY ##########################################################

    def _react_to_market(self):
        """
        Ascertains state of the market, best bid and asks
        Creates orders in public and private market
        Cancel public order if none left in private
        """
        # track best bid and asks
        best_bid, best_ask, best_bid_order, best_ask_order = self._get_best_bid_ask()

        # track state of order book
        num_private_orders, num_my_public_orders, my_stale_priv_order, \
            manager_order = self._get_order_book_state()

        if num_private_orders == 0:
            self._units_to_trade = 0

        # CANCELLING STALE ORDERS =========================================================
        if num_my_public_orders > 0 and self._units_to_trade < 1 and \
                not self._waiting_for_server:
            # self.inform(f"Units left to trade = {self._units_to_trade}")
            # self.inform(f"Stale order - {my_stale_priv_order.ref} being cleared.")
            self._waiting_for_server = True
            self._cancel_order(my_stale_priv_order)
            self._last_accepted_public_order_id = 0

        # PRIVATE ORDER CREATION ==============================================================
        # only create private order if public order traded successfully, and there exists
        # a corresponding manager order
        if (self._last_accepted_public_order_id not in Order.current()) \
                and (self._units_to_trade > 0) and (not self._last_accepted_public_order_id == 0) \
                and (num_my_public_orders == 0):

            self._last_accepted_public_order_id = 0
            self.inform("Last public order traded, creating private order.===============")

            # determine order attributes
            is_private = True
            price = manager_order.price
            units = 1
            if self.role() == Role.BUYER:
                order_side = OrderSide.SELL
            else:
                order_side = OrderSide.BUY
            order_type = OrderType.LIMIT
            ref = f"Private order - {self._tradeID}"

            # if we are a buyer, we sell in private market. Ensure have enough priv widgets
            # if we are a seller, we buy in private market. Ensure have enough cash
            if (self.role() == Role.BUYER and self._private_widgets_available > 0) or \
                    (self.role() == Role.SELLER and self._cash_available >= price):

                # self.inform(f"Units left to trade = {self._units_to_trade}")
                if not self._waiting_for_server:
                    self._units_to_trade -= 1
                    self._create_new_order(price, units, order_side, order_type, ref, is_private)

        # END PRIVATE ORDER CREATION ==========================================================

        self.inform(f"{num_my_public_orders}, {num_private_orders}, remaining trades => {self._units_to_trade}")

        # PUBLIC ORDER CREATION ===============================================================
        # stale orders should be cleared at this stage; there exists a private order
        # create an order based on best bid / ask

        if self._units_to_trade > 0 and num_my_public_orders == 0 and \
                not self._waiting_for_server:

            is_private = False
            self._create_profitable_order(best_ask, best_bid, manager_order, is_private,
                                          best_bid_order, best_ask_order)

        # END PUBLIC ORDER CREATION ===========================================================

    @staticmethod
    def _get_best_bid_ask():
        """
        Determine and return best active bid and asks in the order book
        :return: best_bid: best buy price
                 best_ask: best sell price
                 best_ask_order: best bid order object
                 best_bid_order:  best ask order object

        """
        # initial bid and asks unrealistic / out of bound
        best_bid = 0
        best_ask = 999999
        best_ask_order = None
        best_bid_order = None

        # run through the order book, determine best bid and asks
        for fm_id, order in Order.current().items():
            if not order.is_consumed and not order.is_private:
                if order.order_side == OrderSide.BUY and order.price > best_bid:
                    best_bid = order.price
                    best_bid_order = order
                elif order.order_side == OrderSide.SELL and order.price < best_ask:
                    best_ask = order.price
                    best_ask_order = order

        return best_bid, best_ask, best_bid_order, best_ask_order

    def _print_trade_opportunity(self, other_order):
        """
        Print profitable trade opportunities
        :param other_order: order that's profitable given the profit margin
        :return:
        """
        self.inform(f"I am a {self.role()} with profitable order {other_order}")

    def _get_order_book_state(self):
        """
        Ascertain how many active orders are mine, or from the manager to me,
            and if I have a stale order in the markets
        :return: num_private_orders : number of active private orders
                 num_my_public_orders : number of my non-trade public orders
                 my_stale_priv_order : which order of mine is stale
                 manager_order : order object created by the manager
        """
        num_private_orders = 0
        manager_order = None
        num_my_public_orders = 0
        my_stale_priv_order = None

        for fm_id, order in Order.current().items():
            # if there is a private order not created by me
            if order.is_private and not order.mine:
                num_private_orders += 1
                manager_order = order
                if manager_order.original_id not in self._priv_orders:
                    self._units_to_trade = manager_order.units
                    self._priv_orders[order.fm_id] = order.units

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

    def _create_profitable_order(self, best_ask, best_bid, manager_order, is_private,
                                 best_bid_order, best_ask_order):
        """
        Handle the creation of profitable orders in the public market
        :param best_ask: best asking price
        :param best_bid: best bidding price
        :param manager_order: manager's order object
        :param is_private: if order to be created is private or not
        :param best_bid_order: order object of best bidder
        :param best_ask_order: order object of best seller
        """

        if self._units_to_trade == 0:
            return

        # if buyer
        if self.role() == Role.BUYER:
            # if the best selling price is less than
            # or equal to the price we want to buy at, submit order
            if best_ask <= manager_order.price - PROFIT_MARGIN:

                # determine order attributes
                price = best_ask
                units = 1
                order_side = OrderSide.BUY
                order_type = OrderType.LIMIT
                ref = f"SM - {order_side}-{self._tradeID}"

                # if we have enough cash available, make the order
                if self._cash_available >= price:
                    self._create_new_order(price, units, order_side, order_type, ref, is_private)
                    self.inform("Responding to profitable order")
                    self._print_trade_opportunity(best_ask_order)

                else:
                    if not self._waiting_for_server:
                        self.inform(f"Not enough cash, but want to respond to: {best_ask_order}")

        # if we are sellers
        else:
            # if the best asking price is more than
            # or equal to the price we want to sell at, submit order
            if best_bid >= manager_order.price + PROFIT_MARGIN:
                self.inform("Creating public order========================")
                price = best_bid
                units = 1
                order_side = OrderSide.SELL
                order_type = OrderType.LIMIT
                ref = f"SM - {order_side}-{self._tradeID}"

                # only sell if have any public widgets available
                if self._public_widgets_available > 0:
                    self._create_new_order(price, units, order_side, order_type, ref, is_private)
                    self.inform("Responding to profitable order.")
                    self._print_trade_opportunity(best_bid_order)

                else:
                    if not self._waiting_for_server:
                        self.inform(f"Not enough widgets, but want to respond to: {best_bid_order}")


if __name__ == "__main__":
    FM_ACCOUNT = "ardent-founder"
    FM_EMAIL = "s.mann4@student.unimelb.edu.au"
    FM_PASSWORD = "921322"
    MARKETPLACE_ID = 898

    B_TYPE = BotType.MARKET_MAKER
    # B_TYPE = BotType.REACTIVE

    # testing
    MANAGER_ID = "T033"

    ds_bot = DSBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID, B_TYPE)
    ds_bot.run()