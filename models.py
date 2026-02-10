from sqlalchemy import Column, Integer, String, DateTime, Text
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String, unique=True, index=True)
    name = Column(String)
    surname = Column(String)
    contract_type = Column(String) # "Regular Otro sindicato", "Regular PYA", "Temporal"

class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String, index=True) # Linked to User DNI
    date = Column(DateTime)
    items_json = Column(Text) # JSON string of items
    pdf_path = Column(String)

class Laundry(Base):
    __tablename__ = "laundry"

    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String, index=True)
    date = Column(DateTime)
    items_json = Column(Text)

class LaundryReturn(Base):
    __tablename__ = "laundry_returns"

    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String, index=True)
    date = Column(DateTime)
    items_json = Column(Text)

