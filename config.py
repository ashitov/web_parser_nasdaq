# -*- coding: utf-8 -*-


class Config(object):
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:123@localhost/tochka'
    PRICE_HISTORY_LINK = 'https://www.nasdaq.com/symbol/{}/historical'
    INSIDE_TRADES_LINK = 'https://www.nasdaq.com/symbol/{}/insider-trades?page={}'
