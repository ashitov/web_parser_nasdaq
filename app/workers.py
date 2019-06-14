import requests

from bs4 import BeautifulSoup
from datetime import datetime
from multiprocessing.dummy import Pool as ThreadPool

from app import app, db
from app.models import Company, PriceHistory, Person, InsideTrades
from config import Config


def get_page_content(_link):
    """
    Procedure for generating parcer to page. Enter point for web page. After this all work continue localy
    :param _link: full link to page
    :return: BeautifulSoup parser obj.
    """
    return BeautifulSoup(requests.get(_link).content, 'html.parser')


def get_page_count(_page_parser):
    """
    Procedure for getting page count from page? from pagerContainer tag
    :param _page_parser: BS parser obj.
    :return: number of pages, int
    """
    pager = _page_parser.find('div', {'id': 'pagerContainer'})
    page_list = pager.find_all('li')
    if len(page_list) > 0:
        pager = [i.text for i in page_list]
        res = int(pager[pager.index('next >') - 1]) if int(pager[pager.index('next >') - 1]) < 10 else 10
    else:
        res = 0
    return res


def get_or_create_company(_code):
    """
    Procedure that check if company exists in db, and create one if not.
    :param _code: Symbol for company, AAPL, CVX or else.
    :return: Company obj.
    """
    _company = Company.query.filter_by(symbol=_code).first()
    if not _company:
        _company = Company(symbol=_code)
        db.session.add(_company)
        db.session.commit()
    return _company


def get_or_create_person(_name, _relation):
    """
    Procedure that check if person exists in db, and create one if not.
    :param _name: Person name
    :param _relation: Relation of this person
    :return: Person obj.
    """
    _person = Person.query.filter_by(name=_name).first()
    if not _person:
        _person = Person(name=_name, relation=_relation)
        db.session.add(_person)
        db.session.commit()
    return _person


def get_inside_trades_table(_page_parser):
    _inside_trades_table = _page_parser.find('div', {'class': 'genTable'})
    _inside_trades_table.find('thead').extract()
    _rows = _inside_trades_table.find_all('tr')
    return _rows


def get_inside_trades_info(_row, _company):
    _person = get_or_create_person(_row['name'], _row['relation'])
    _inside_trade = InsideTrades.query.filter_by(saler_id=_person,
                                                 company_id=_company.id,
                                                 trade_date=_row['last_date'],
                                                 shares_traded=_row['shares_traded'],
                                                 last_price=_row['last_price'],
                                                 shares_held=_row['shares_held'])


def get_stock_prices_history(_page_parser, _company):
    history_elements = _page_parser.find('div', {'id': 'historicalContainer'}).find('tbody').find_all('tr')
    for element in history_elements:
        cells = element.find_all('td')
        if cells[0].text.strip() == '':
            continue
        try:
            _price_date = datetime.strptime(cells[0].text.strip(), '%m/%d/%Y').date()
        except:
            _price_date = datetime.now().date()
        _open = cells[1].text.strip()
        _high = float(cells[2].text.strip().replace(',', ''))
        _low = float(cells[3].text.strip().replace(',', ''))
        _close = float(cells[4].text.strip().replace(',', ''))
        _volume = int(cells[5].text.strip().replace(',', ''))
        _history_price = PriceHistory.query.filter_by(company_id=_company.id, price_date=_price_date).first()
        if not _history_price:
            _new_price = PriceHistory(company_id=_company.id, price_date=_price_date,
                                      open_price=_open, high_price=_high,
                                      low_price=_low, close_price=_close, volume=_volume)
            db.session.add(_new_price)
            db.session.commit()


def get_inside_trades(_page_parser, _company):
    inside_trades_elements = get_inside_trades_table(_page_parser)
    for element in inside_trades_elements:
        cells = element.find_all('td')
        if cells[0].text.strip() == '':
            continue
        _person = get_or_create_person(cells[0].text.strip(), cells[1].text.strip())
        _trade_date = datetime.strptime(cells[2].text.strip(), '%m/%d/%Y').date()
        _transaction_type = cells[3].text.strip()
        _owner_type = cells[4].text.strip()
        _shares_traded = int(cells[5].text.strip().replace(',', ''))
        _last_price = float(cells[6].text.strip()) if cells[6].text.strip() != '' else 0.0
        _shares_held = int(cells[7].text.strip().replace(',', ''))
        _inside_trade = InsideTrades.query.filter_by(company_id=_company.id, saler_id=_person.id,
                                                     trade_date=_trade_date, transaction_type=_transaction_type,
                                                     owner_type=_owner_type, shares_traded=_shares_traded,
                                                     last_price=_last_price, shares_held=_shares_held).first()
        if not _inside_trade:
            _inside_trade = InsideTrades(company_id=_company.id, saler_id=_person.id,
                                         trade_date=_trade_date, transaction_type=_transaction_type,
                                         owner_type=_owner_type, shares_traded=_shares_traded,
                                         last_price=_last_price, shares_held=_shares_held)
            db.session.add(_inside_trade)
            db.session.commit()
        else:
            continue


def grep_history_prices_from_page(_link):
    try:
        _company = _link[1]
        _page_parser = get_page_content(_link[0])
        get_stock_prices_history(_page_parser, _company)
        return 'OK'
    except Exception as err:
        return err


def grep_inside_trades_from_page(_link):
    try:
        _company = _link[1]
        _page_parser = get_page_content(_link[0])
        get_inside_trades(_page_parser, _company)
        return 'OK'
    except Exception as err:
        return err


def parse_history_prices(_worker_number=3):
    try:
        pool = ThreadPool(_worker_number)
        _link = Config.PRICE_HISTORY_LINK
        with open('../tickers.txt', 'r') as _file:
            stocks = [stock.strip() for stock in _file]
        task_list = []
        for stock in stocks:
            _company = get_or_create_company(stock)
            _stock_link = _link.format(stock)
            tmp_list = [_stock_link, _company]
            task_list.append(tmp_list)
        pool.map(grep_history_prices_from_page, task_list)
        pool.close()
        pool.join()
        return 'OK'
    except Exception as err:
        return err


def parse_inside_trades(_worker_number=3):
    try:
        pool = ThreadPool(_worker_number)
        _link = Config.INSIDE_TRADES_LINK
        with open('../tickers.txt', 'r') as _file:
            stocks = [stock.strip() for stock in _file]
        for stock in stocks:
            _company = get_or_create_company(stock)
            _page_parser = get_page_content(_link.format(stock, 1))
            _page_counter = get_page_count(_page_parser)
            if _page_counter > 0:
                _link_list = []
                for i in range(_page_counter):
                    tmp_list = [_link.format(stock, i+1), _company]
                    _link_list.append(tmp_list)
        if len(_link_list) > 0:
            pool.map(grep_inside_trades_from_page,_link_list)
            pool.close()
            pool.join()
            return 'OK'
    except Exception as err:
        return err
