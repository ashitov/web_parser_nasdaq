#-*- coding:utf-8 -*-

from datetime import datetime
from app import db


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    name = db.Column(db.String)
    symbol = db.Column(db.String)


class PriceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    price_date = db.Column(db.Date, nullable=False, default=datetime.now().date())
    open_price = db.Column(db.Float)
    high_price = db.Column(db.Float)
    low_price = db.Column(db.Float)
    close_price = db.Column(db.Float)
    volume = db.Column(db.Integer)

    company = db.relationship('Company', backref=db.backref('stock', lazy=True))



class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    name = db.Column(db.String)
    relation = db.Column(db.String)



class InsideTrades(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    saler_id = db.Column(db.Integer, db.ForeignKey('person.id'))
    trade_date = db.Column(db.Date, nullable=False, default=datetime.now().date())
    transaction_type = db.Column(db.String)
    owner_type = db.Column(db.String)
    shares_traded = db.Column(db.Integer)
    last_price = db.Column(db.Float)
    shares_held = db.Column(db.Integer)

    saler = db.relationship('Person', backref=db.backref('saler', lazy=True))
    company = db.relationship('Company', backref=db.backref('sale', lazy=True))

