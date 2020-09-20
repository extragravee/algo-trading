"""
FNCE30010 - Algorithmic Trading
Assignment 2 - CAPM
Sidakpreet Mann
921322

Notes:
    1. Covar matrix is calculated only initially, as it's known
"""
import time
from typing import List
import numpy as np
from fmclient import Agent, Session
from fmclient import Order, OrderSide, OrderType

# Submission details
SUBMISSION = {"number": "921322", "name": "Sidakpreet Mann"}


class CAPMBot(Agent):

    def __init__(self, account, email, password, marketplace_id,
                 risk_penalty=0.001, session_time=20):
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
        self._payoffs = {}
        self._risk_penalty = risk_penalty
        self._session_time = session_time
        self._market_ids = {}

        self._asset_units = []

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

        self.inform(self._market_ids)
        self.inform(self._payoffs)

    def _get_portfolio_variance(self):

        self.inform(self._asset_units)
        weights = np.array(self._asset_units)
        covar_matrix = np.cov(list(self._payoffs.values()), bias=True)
        return np.dot(np.dot(weights, covar_matrix),
                      weights.transpose())

    def get_potential_performance(self, orders):
        """
        Returns the portfolio performance if the given list of orders is
        executed. The performance as per the following formula: Performance
        = ExpectedPayoff - b * PayoffVariance, where b is the penalty for
        risk. :param orders: list of orders :return:
        """
        pass

    def is_portfolio_optimal(self):
        """
        Returns true if the current holdings are optimal (as per the
        performance formula), false otherwise. :return:
        """
        pass

    def order_accepted(self, order):
        pass

    def order_rejected(self, info, order):
        pass

    def received_orders(self, orders: List[Order]):
        self.inform("Received orders")
        self.inform(f"Portfolio var: {self._get_portfolio_variance()}")

    def received_session_info(self, session: Session):
        pass

    def pre_start_tasks(self):
        pass

    def received_holdings(self, holdings):
        self._asset_units = [holdings.assets[market].units_available
                             for market in holdings.assets]


if __name__ == "__main__":
    FM_ACCOUNT = "ardent-founder"
    FM_EMAIL = "s.mann4@student.unimelb.edu.au"
    FM_PASSWORD = "921322"
    MARKETPLACE_ID = 980  # replace this with the marketplace id

    bot = CAPMBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID)
    bot.run()
