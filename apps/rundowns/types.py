import bson
import datetime

from typing import Dict, List, Literal, Optional, TypedDict


class IEntity(TypedDict, total=False):
    _id: str


class IRef(TypedDict):
    _id: bson.ObjectId


IRefs = List[IRef]


class ISubject(TypedDict):
    name: str
    qcode: str


class IRRule(TypedDict, total=False):
    freq: Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
    interval: int
    by_month: List[int]
    by_month_day: List[int]
    by_day: List[int]
    by_week_no: List[int]


class IShow(IEntity):
    title: str
    planned_duration: int
    shortcode: str


class IRundownTitleTemplate(TypedDict, total=False):
    prefix: str
    separator: str
    date_format: str


class ISubitem(TypedDict, total=False):
    qcode: str
    content: str
    technical_info: str


class IRundownItemTemplate(TypedDict):
    item_type: str
    title: Optional[str]
    duration: Optional[int]
    planned_duration: Optional[int]
    content: Optional[str]
    show_part: Optional[str]
    additional_notes: Optional[str]
    rundown: str
    camera: List[str]
    subitems: List[ISubitem]


class IRundownItem(IRundownItemTemplate, IEntity):
    pass


class IRundownBase(IEntity, total=False):
    show: str
    title: str
    airtime_date: str
    airtime_time: str
    duration: int
    planned_duration: int
    scheduled_on: Optional[datetime.datetime]


class IRundownTemplate(IRundownBase):
    items: List[IRundownItemTemplate]
    title_template: IRundownTitleTemplate
    autocreate_on: str
    autocreate_before_seconds: Optional[int]


class IRundown(IRundownBase, total=False):
    template: str
    items: IRefs
    items_data: List[Dict[str, str]]
