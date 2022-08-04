import datetime

from typing import List, Optional, TypedDict


class IEntity(TypedDict, total=False):
    _id: str


class IRef(TypedDict):
    _id: str


IRefs = List[IRef]


class IRundownTitleTemplate(TypedDict, total=False):
    prefix: str
    separator: str
    date_format: str


class IRundownBase(IEntity):
    title: str
    show: str
    airtime_date: str
    airtime_time: str
    planned_duration: int
    scheduled_on: Optional[datetime.datetime]


class IRundownItemTemplate(TypedDict):
    item_type: str
    title: Optional[str]
    duration: Optional[int]
    planned_duration: Optional[int]


class IRundownItem(IRundownItemTemplate, IEntity):
    pass


class ITemplate(IRundownBase):
    title_template: IRundownTitleTemplate
    items: List[IRundownItemTemplate]


class IRundown(IRundownBase):
    template: Optional[str]
    items: IRefs


class IShow(IEntity):
    title: str
    planned_duration: int
