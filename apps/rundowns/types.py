import datetime

from typing import Dict, List, Optional, TypedDict


class IEntity(TypedDict, total=False):
    _id: str
    _links: Dict


class IRef(TypedDict):
    _id: str
    start_time: str


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
    items: List[IRef]


class ITemplate(IRundownBase):
    title_template: IRundownTitleTemplate


class IRundown(IRundownBase):
    template: Optional[str]


class IShow(IEntity):
    title: str
    planned_duration: int
