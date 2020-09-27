"""
FNCE30010 - Algorithmic Trading
Assignment 2 - CAPM
Sidakpreet Mann
921322

Notes:
    1. Covar matrix is calculated only initially, as it's known
    2. Best set of orders to trade gets selected based on aggressiveness_param
        be default set to 1% (new portfolio performance must be at least 1%
        better performance for those trades to go through, this can be custom
        set when instantiating the bot
"""
import itertools
from enum import Enum
from typing import List
import numpy as np
from fmclient import Agent, Session
from fmclient import Order, OrderSide, OrderType

# Submission details
SUBMISSION = {"number": "921322", "name": "Sidakpreet Mann"}

# CONSTANTS
CENTS_IN_DOLLAR = 100
VERY_HIGH_ASK = 999999
WAIT_3_SECONDS = 3
MIN_CASH_THRESHOLD = 5000

# Bot type enum
class BotType(Enum):
    MARKET_MAKER = 0
    REACTIVE = 1


class CAPMBot(Agent):

    def __init__(self, account, email, password, marketplace_id,
            risk_penalty=0.001, session_time=20, aggressiveness_param=0.01):
        """
        Constructor for the Bot
        :param account: Account name
        :param email: Email id
        :param password: password
        :param marketplace_id: id of the marketplace
        :param risk_penalty: Penalty for risk
        :param session_time: Total trading time for one session
        """
        super().__init__(account, email, password, marketplace_id,
                         name="CAPM Bot")

        self._bot_type = BotType.REACTIVE

        self._payoffs = {}
        self._risk_penalty = risk_penalty
        self._session_time = session_time
        self._market_ids = {}

        self._asset_units = {}
        self._cash_available = 0
        self._cash_settled = 0
        self._current_port_variance = 0
        self._current_exp_return = 0
        self._current_performance = 0

        self._aggressiveness_param = aggressiveness_param + 1
        self._waiting = False
        self._order_id = 0

        # reactive bot
        self._reactive_orders = []

    def initialised(self):
        # Extract payoff distribution for each security
        for market_id, market_info in self.markets.items():
            # store market id for each item -- see if it's more efficient to
            # also store the Market() objects here
            # instead of creating them every time a new order is needed
            self._market_ids[market_info.item] = market_id

            security = market_info.item
            description = market_info.description
            self._payoffs[security] = [int(a) for a in description.split(",")]

        # bot starts off as a market maker FOR NOW IT IS REACTIVE FOR TESTING
        self._bot_type = BotType.REACTIVE

        # TESTING ======================================
        # if bot is reactive, then get best orders every three seconds

        self.execute_periodically_conditionally(
                    self._reactive_strategy,
                    WAIT_3_SECONDS,
                    self._is_bot_reactive)

        # if bot is market maker, create profitable orders every three seconds
        self.execute_periodically_conditionally(
                    self._market_making,
                    WAIT_3_SECONDS,
                    self._is_bot_reactive)

        # TESTING ======================================

        self.inform(f"Market IDs: {self._market_ids}")
        self.inform(f"Payoffs   : {self._payoffs}")

    def _check_if_enough_cash(self):
        """
        Checks if there is enough cash to trade, if not
        sell some notes

        atm checking against arbitrary threshold, might be better to get best
        bid and asks, and sell notes till we have at least enough cash for
        the highest ask out of any market
        :return:
        """
        if self._cash_available < MIN_CASH_THRESHOLD:
            # sell notes to get cash
            # self._sell_notes
            pass
        pass

    def _is_bot_reactive(self):
        return self._bot_type==BotType.REACTIVE

    @staticmethod
    def _market_making():
        pass

    @staticmethod
    # this shouldn't really exist, just use this in the potential
    # performance function
    def _portfolio_performance(exp_return, risk_penalty, variance):
        """
        Calculates portfolio performance based on the risk preference
        :param exp_return   : expected payoff / return of portfolio
        :param risk_penalty : risk preference parameter
        :param variance     : variance of the portfolio
        :return             : score/utility for performance
        """
        return exp_return - risk_penalty * variance

    def _get_expected_return(self, units, cash):
        """
        Calculates expected return of a portfolio given units and
        available cash
        :param units: vector of units in some portfolio
        :param cash : available cash
        :return     : exp. return of portfolio based on diff. state payoffs
        """
        x = list(self._payoffs.values())

        return (sum(np.dot(np.dot(1 / (len(x)),
                                  units), x)) + cash) / CENTS_IN_DOLLAR

    def _get_portfolio_variance(self, units):
        """
        Calculates variance (scalar) of portfolio given units vector and stored
        payoff values

        Portfolio variance = W . Covar Matrix . Wt
        Where W is vector of weights, Wt is W transpose

        :param units: vector of weights of portfolio
        :return     : scalar variance of the portfolio
        """
        weights = np.array(units)
        covar_matrix = np.dot(1 / (CENTS_IN_DOLLAR ** 2),
                              np.cov(list(self._payoffs.values()), bias=True))
        return np.dot(np.dot(weights, covar_matrix),
                      weights.transpose())

    # @staticmethod
    def _get_best_bid_ask(self):
        """
        Walks the order book and determines what the best bid and asks are
        for each market
        :return     : dictionaries of best bid and ask orders for each
                        market
        """

        # track best bid_ask prices and orders
        # key - market, value - [best price, best price order]
        best_bids = {'A': [-1, None], 'B': [-1, None],
                     'C': [-1, None], 'note': [-1, None]}
        best_asks = {'A': [VERY_HIGH_ASK, None], 'B': [VERY_HIGH_ASK, None],
                     'C': [VERY_HIGH_ASK, None], 'note': [VERY_HIGH_ASK, None]}

        # track current best bids and asks
        for order_id, order in Order.current().items():
            # self.inform(order)
            # self.inform(order.market.item)

            dict_key = order.market.item
            if dict_key.lower() == "note":
                dict_key = "note"

            if order.order_side == OrderSide.BUY:
                if order.price > best_bids[dict_key][0]:
                    best_bids[dict_key][0] = order.price
                    best_bids[dict_key][1] = order
            else:
                if order.price < best_asks[dict_key][0]:
                    best_asks[dict_key][0] = order.price
                    best_asks[dict_key][1] = order

        return best_bids, best_asks

    def _reactive_strategy(self):
        """
        REACTIVE STRATEGY
        =================
        Generates combinations of profitable orders currently in the order book
        Called every 3 seconds periodically
        sets reactive_orders attribute to a list of orders to be executed

        """
        bids, asks = self._get_best_bid_ask()

        # filter out when there is NO order in the bid side / ask side
        bids = [x[1] for x in list(bids.values()) if x[1] is not None]
        asks = [x[1] for x in list(asks.values()) if x[1] is not None]

        orders = bids + asks
        # self.inform("Best bid and asks: ")
        # self.inform(f"Orders: {orders}")

        # initially no valid orders
        self._reactive_orders = None

        # generate combinations of possible orders to be executed
        # when first order that is good enough is found, stop looking
        for i in range(1, len(orders) + 1):

            combs = list(itertools.combinations(orders, i))
            new_set = filter(self._duplicates_in_list, combs)

            # careful! filter is an iterable object, if you loop over it once
            # u no longer have access to all sets of orders u have looped over!

            # for each order in this set, test if profitable
            for order_set in new_set:
                # self.get_potential_performance(list(order_set))
                if self.get_potential_performance(list(order_set)) \
                        > self._aggressiveness_param * self._current_performance:
                    self._reactive_orders = list(order_set)
                    break

            if self._reactive_orders is not None:
                break

        self.inform(f"Chosen order: {self._reactive_orders}")

        # if there are profitable orders, send them through
        if self._reactive_orders is not None and not self._waiting:

            self._waiting = True
            self._send_orders(self._reactive_orders)
            self._waiting = False

        return

    def _send_orders(self, orders):
        """
        Sends through a list of orders
        :param orders: list of favourable orders
        """

        # REACTIVE ORDERS
        for order in orders:

            price_tick = order.market.price_tick

            new_order = Order.create_new()
            new_order.price = order.price - (order.price % price_tick)
            new_order.market = order.market
            new_order.units = 1

            if order.order_side == OrderSide.BUY:
                new_order.order_side = OrderSide.SELL
            else:
                new_order.order_side = OrderSide.BUY

            new_order.order_type = OrderType.LIMIT
            new_order.ref = f"Order {self._order_id} - SM"

            self.send_order(new_order)

    def get_potential_performance(self, orders: List[Order]):
        """
        Returns the portfolio performance if the given list of orders is
        executed. The performance as per the following formula: Performance
        = ExpectedPayoff - b * PayoffVariance, where b is the penalty for
        risk.
        :param orders      : list of orders to be simulated on portfolio
        :return performance: percentage increase in portfolio performance
        """
        # self.inform("Testing performance of: ")
        # self.inform(orders)

        cash = self._cash_settled
        units = self._asset_units.copy()
        # self.inform(units)
        # simulate list of orders executing
        for order in orders:
            # for a buy order that exists in the market, we sell to it
            if order.order_side == OrderSide.BUY:
                cash += order.price
                units[order.market.item] -= 1

            # for a sell order, we buy from it
            else:
                cash -= order.price
                units[order.market.item] += 1

        # self.inform(f"Cash: {cash}, Units: {units}")
        x = list(units.values())

        variance = self._get_portfolio_variance(x)

        performance = self._portfolio_performance(
            self._get_expected_return(x, cash),
            self._risk_penalty,
            variance)

        # self.inform(f"Performance for {orders} is: "
        #             f"{performance}")

        return performance

    @staticmethod
    def _duplicates_in_list(list_of_orders):
        """
        Receives a list of orders and determines if those orders exist in the
        same market
        :param list_of_orders: list of 8 best bid and asks from the 4 markets
        :return              : True if orders list contains order in the same
                                market.
        """
        list_of_orders = [x.market for x in list_of_orders]

        return len(set(list_of_orders)) == len(list_of_orders)

    def is_portfolio_optimal(self):
        """
        Returns true if the current holdings are optimal (as per the
        performance formula), false otherwise. :return:
        """
        pass

    def order_accepted(self, order):
        self.inform(f"Accepted: {order} - {order.market.item}")

    def order_rejected(self, info, order):
        self.inform(f"Wish to trade, but can not because: {info}")

    def received_orders(self, orders: List[Order]):
        # seems to be called before received holdings, so don't calculate
        # the portfolio variance here! As this has old number of units
        # self.inform(f"{self._get_best_bid_ask()}")

        # Reactive orders
        # self.inform(f"Updated orders: {orders}")
        # # if there is a set of valid reactive orders, they should be sent
        # if self._reactive_orders is not None and not self._waiting:
        #
        #     self.inform(f"should execute {self._reactive_orders}")
        #
        #     # order management
        #     self._waiting = True
        #     # self._send_orders(self._reactive_orders)
        #     self._waiting = False
        #
        #     # reset reactive orders to None left
        #     self._reactive_orders = None
        #
        # # Market maker orders
        # # simulate all 4 A B C note, price 0 and change in performance is the
        # # max price to be paid. Try buy and sell and see if any can be exec
        return

    def received_session_info(self, session: Session):
        pass

    def pre_start_tasks(self):
        pass

    def received_holdings(self, holdings):

        # have to assume here that assets are arranged here in the same
        # order as the order in which payoffs were received

        self._cash_available = holdings.cash_available
        self._cash_settled = holdings.cash

        self._asset_units = {}
        for market in holdings.assets:
            self._asset_units[market.item] = holdings.assets[market].units
        # self.inform(f"Units recorded: {self._asset_units}")

        # update portfolio variance
        self._current_port_variance = self._get_portfolio_variance(
            list(self._asset_units.values()))

        # update portfolio return
        # return is based on SETTLED cash, and not on cash available
        self._current_exp_return = \
            self._get_expected_return(list(self._asset_units.values()),
                                      self._cash_settled)

        # update current performance
        self._current_performance = self._portfolio_performance(
            self._current_exp_return,
            self._risk_penalty,
            self._current_port_variance)

        # scaffolding
        self.inform(f"=============================")
        self.inform(f"Portfolio var: {self._current_port_variance}")
        self.inform(f"Exp return   : {self._current_exp_return}")
        self.inform(f"Performance  : {self._current_performance}")




if __name__ == "__main__":
    FM_ACCOUNT = "ardent-founder"
    FM_EMAIL = "s.mann4@student.unimelb.edu.au"
    FM_PASSWORD = "921322"
    MARKETPLACE_ID = 1054  # replace this with the marketplace id

    bot = CAPMBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID,
                  risk_penalty=0.007)
    bot.run()
