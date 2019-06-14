# -*- coding: utf-8 -*-

import json

from datetime import datetime, timedelta

from flask import request, render_template

from app import app, db

from app.models import Company, PriceHistory, Person, InsideTrades
from app.workers import parse_inside_trades, parse_history_prices


def get_history_prices_list(current_date, start_date, _stock):
    stock = Company.query.filter_by(symbol=_stock).first()
    return PriceHistory.query.filter(PriceHistory.company == stock).filter(
        PriceHistory.price_date <= current_date) \
        .filter(PriceHistory.price_date >= start_date).all()


def get_inside_trades(_stock):
    stock = Company.query.filter_by(symbol=_stock).first()
    return InsideTrades.query.join(Person).filter(InsideTrades.company_id == stock.id).all()


def get_person_inside_trades(_person):
    person = Person.query.filter_by(name=_person).first()
    return InsideTrades.query.join(Person).filter(InsideTrades.saler_id == person.id).all()


def get_min_max_diff_prices(date_from, date_to):
    list_of_prices = PriceHistory.query.filter(PriceHistory.price_date <= date_to).filter(
        PriceHistory.price_date >= date_from).all()
    min_prices = {'open': min([_.open_price for _ in list_of_prices]),
                  'high': min([_.high_price for _ in list_of_prices]),
                  'low': min([_.low_price for _ in list_of_prices]),
                  'close': min([_.close_price for _ in list_of_prices])}
    max_prices = {'open': max([_.open_price for _ in list_of_prices]),
                  'high': max([_.high_price for _ in list_of_prices]),
                  'low': max([_.low_price for _ in list_of_prices]),
                  'close': max([_.close_price for _ in list_of_prices])}
    diff_prices = {'open': max_prices['open'] - min_prices['open'],
                   'high': max_prices['high'] - min_prices['high'],
                   'low': max_prices['low'] - min_prices['low'],
                   'close': max_prices['close'] - min_prices['close']}
    return min_prices, max_prices, diff_prices


def get_periods(_type, val, field_mapping):
    sql_select = 'SELECT t1.price_date as t1pd, t2.price_date as t2pd, abs(t1.price_date - t2.price_date) AS date_diff '
    sql_from = 'FROM price_history AS t1 '
    sql_inner_join = 'INNER JOIN price_history AS t2 '
    sql_on = 'ON(t1.{} - t2.{} = {}) '.format(field_mapping[_type], field_mapping[_type], val)
    sql_order_by = 'ORDER BY date_diff ASC '
    sql = sql_select + sql_from + sql_inner_join + sql_on + sql_order_by
    res = db.engine.execute(sql)
    res_sorted = sorted([row for row in res], key=lambda d: d.date_diff)
    res_sorted_min = [row for row in res_sorted if row.date_diff == res_sorted[0].date_diff]
    _periods = []
    for item in res_sorted_min:
        tmp_period = {'date_from': item[0], 'date_to': item[1]}
        _periods.append(tmp_period)
    return _periods


@app.route('/')
def index():
    with open('tickers_1.txt', 'r') as _file:
        list_of_stocks = [stock.strip() for stock in _file]
    return render_template('index.html', stocks=list_of_stocks)


@app.route('/<_stock>')
@app.route('/<_stock>/')
def history_price(_stock):
    current_date = datetime.now().date()
    start_date = current_date - timedelta(days=90)
    list_of_prices = get_history_prices_list(current_date, start_date, _stock)
    return render_template('price_history.html', history=list_of_prices, stock=_stock)


@app.route('/api/<_stock>')
@app.route('/api/<_stock>/')
def history_price_api(_stock):
    current_date = datetime.now().date()
    start_date = current_date - timedelta(days=90)
    list_of_prices = get_history_prices_list(current_date, start_date, _stock)
    res = []
    for price in list_of_prices:
        tmp_res = {'price_date': price.price_date.strftime('%Y-%m-%d'), 'open_price': price.open_price,
                   'high_price': price.high_price, 'low_price': price.low_price, 'close_price': price.close_price,
                   'volume': price.volume}
        res.append(tmp_res)
    return json.dumps(res)


@app.route('/<_stock>/insider')
@app.route('/<_stock>/insider/')
def get_insider_trades(_stock):
    inside_trades = get_inside_trades(_stock)
    return render_template('insiders.html', stock=_stock, trades=inside_trades)


@app.route('/api/<_stock>/insider')
@app.route('/api/<_stock>/insider/')
def get_insider_trades_api(_stock):
    inside_trades = get_inside_trades(_stock)
    res = []
    for trade in inside_trades:
        tmp_res = {'saler_name': trade.saler.name, 'saler_relation': trade.saler.relation,
                   'stock': trade.company.symbol, 'trade_date': trade.trade_date.strftime('%Y-%m-%d'),
                   'transaction_type': trade.transaction_type, 'owner_type': trade.owner_type,
                   'shares_traded': trade.shares_traded, 'last_price': trade.last_price,
                   'shares_held': trade.shares_held}
        res.append(tmp_res)
    return json.dumps(res)


@app.route('/<_stock>/insider/<_person>/')
@app.route('/<_stock>/insider/<_person>')
def get_person_insider_trades(_stock, _person):
    inside_trades = get_person_inside_trades(_person)
    return render_template('personal_insiders.html', person=_person, trades=inside_trades)


@app.route('/api/<_stock>/insider/<_person>/')
@app.route('/api/<_stock>/insider/<_person>')
def get_person_insider_trades_api(_stock, _person):
    inside_trades = get_person_inside_trades(_person)
    res = []
    for trade in inside_trades:
        tmp_res = {'stock': trade.company.symbol, 'last_date': trade.trade_date.strftime('%Y-%m-%d'),
                   'transaction_type': trade.transaction_type, 'owner_type': trade.owner_type,
                   'shares_traded': trade.shares_traded, 'last_price': trade.last_price,
                   'shares_held': trade.shares_held}
        res.append(tmp_res)
    return json.dumps(res)


@app.route('/<_stock>/analytics/')
@app.route('/<_stock>/analytics')
def get_stock_analytics(_stock):
    date_from = request.args.get('date_from', False)
    date_to = request.args.get('date_to', False)
    if not date_from or not date_to:
        return render_template('error.html', error='There must be date_from and date_to in params')
    try:
        date_from = datetime.strptime(date_from, '%d.%m.%Y').date()
        date_to = datetime.strptime(date_to, '%d.%m.%Y').date()
    except Exception as err:
        return render_template('error.html', error=err)
    min_prices, max_prices, diff_prices = get_min_max_diff_prices(date_from, date_to)
    return render_template('analitycs.html',
                           stock=_stock,
                           date_from=date_from,
                           date_to=date_to,
                           min_price=min_prices,
                           max_price=max_prices,
                           diff_price=diff_prices)


@app.route('/api/<_stock>/analytics/')
@app.route('/api/<_stock>/analytics')
def get_stock_analytics_api(_stock):
    date_from = request.args.get('date_from', False)
    date_to = request.args.get('date_to', False)
    if not date_from or not date_to:
        return render_template('error.html', error='There must be date_from and date_to in params')
    try:
        date_from = datetime.strptime(date_from, '%d.%m.%Y').date()
        date_to = datetime.strptime(date_to, '%d.%m.%Y').date()
    except Exception as err:
        return render_template('error.html', error=err)
    min_prices, max_prices, diff_prices = get_min_max_diff_prices(date_from, date_to)
    res = {'min': min_prices, 'max': max_prices, 'diff': diff_prices}
    return json.dumps(res)


@app.route('/<_stock>/delta')
@app.route('/<_stock>/delta/')
def get_diffs_interval(_stock):
    val = request.args.get('value', False)
    val = float(val)
    _type = request.args.get('type', False)
    field_mapping = {'open': 'open_price', 'high': 'high_price', 'low': 'low_price', 'close': 'close_price'}
    if not _type or _type not in field_mapping.keys():
        return render_template('error.html',
                               error='There is no type represented or type not in (open, low, high, close)')
    if not val or val <= 0:
        return render_template('error.html', error='There is no difference value or it lower than 0')
    field_mapping = {'open': 'open_price', 'high': 'high_price', 'low': 'low_price', 'close': 'close_price'}
    _periods = get_periods(_type, val, field_mapping)
    return render_template('deltas.html', stock=_stock, delta=val, delta_type=_type, periods=_periods)


@app.route('/api/<_stock>/delta')
@app.route('/api/<_stock>/delta/')
def get_diffs_interval_api(_stock):
    val = request.args.get('value', False)
    val = float(val)
    _type = request.args.get('type', False)
    field_mapping = {'open': 'open_price', 'high': 'high_price', 'low': 'low_price', 'close': 'close_price'}
    if not _type or _type not in field_mapping.keys():
        return 'There is no type represented or type not in (open, low, high, close)'
    if not val or val <= 0:
        return 'There is no difference value or it lower than 0'
    field_mapping = {'open': 'open_price', 'high': 'high_price', 'low': 'low_price', 'close': 'close_price'}
    _periods = get_periods(_type, val, field_mapping)
    res = []
    for period in _periods:
        tmp_res = {'date_from': period['date_from'].strftime('%Y-%m-%d'),
                   'date_to': period['date_to'].strftime('%Y-%m-%d')}
        res.append(tmp_res)
    return json.dumps(res)


@app.route('/get_history/')
@app.route('/get_history')
def get_history():
    try:
        val = request.args.get('value', 3)
        val = int(val)
        parse_history_prices(val)
    except Exception as err:
        return err


@app.route('/get_insides/')
@app.route('/get_insides')
def get_insides():
    try:
        val = request.args.get('value', 3)
        val = int(val)
        parse_inside_trades(val)
    except Exception as err:
        return err