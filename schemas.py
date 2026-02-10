from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

class UserBase(BaseModel):
    dni: str
    name: str
    surname: str
    contract_type: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    class Config:
        orm_mode = True

class DeliveryBase(BaseModel):
    dni: str

class Item(BaseModel):
    name: str
    qty: int

class DeliveryCreate(DeliveryBase):
    items: List[Item]
    date: datetime

class Delivery(DeliveryBase):
    id: int
    date: datetime
    items_json: str
    pdf_path: str
    class Config:
        orm_mode = True

class LaundryBase(BaseModel):
    dni: str

class LaundryCreate(LaundryBase):
    items: List[Item]

class Laundry(LaundryBase):
    id: int
    date: datetime
    items_json: str
    class Config:
        orm_mode = True

class LaundryReturnBase(BaseModel):
    dni: str

class LaundryReturnCreate(LaundryReturnBase):
    items: List[Item]

class LaundryReturn(LaundryReturnBase):
    id: int
    date: datetime
    items_json: str
    class Config:
        orm_mode = True


class LaundryWithUser(Laundry):
    user_name: str
    user_surname: str

class LaundryPendingUser(BaseModel):
    dni: str
    user_name: str
    user_surname: str
    pending_items: List[Item]


