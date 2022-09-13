import datetime

from typing import Dict, List, Literal, Optional, TypedDict


class IEntity(TypedDict, total=False):
    _id: str


class IRef(TypedDict):
    _id: str


IRefs = List[IRef]


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


class IRundownItemTemplate(TypedDict):
    item_type: str
    title: Optional[str]
    duration: Optional[int]
    planned_duration: Optional[int]
    content: Optional[str]
    show_part: Optional[str]
    live_sound: Optional[str]
    guests: Optional[str]
    additional_notes: Optional[str]
    live_captions: Optional[str]
    last_sentence: Optional[str]


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


class IRundown(IRundownBase, total=False):
    template: str
    items: IRefs
    items_data: List[Dict[str, str]]
