from datetime import datetime, timedelta


class FMT(object):
    TIME_ISO_L = '%Y-%m-%dT%H:%M:%S.%f'
    TIME_ISO_S = '%Y-%m-%dT%H:%M:%S'
    TIME_T_TZ = '%Y-%m-%dT%H:%M:%S+08:00'
    TIME_T_UZ = '%Y-%m-%dT%H:%M:%SZ'
    DATE_TIME = '%Y%m%d_%H%M%S'


def get_week_start_date(date: datetime = None, date_string: str = None, fmt: str = FMT.TIME_ISO_S, to_str=True):
    """获取当前日期所在周的第一天，第一秒"""
    if date is None and date_string is None:
        date = datetime.now()
    if date is None:
        date = datetime.strptime(date_string, fmt)

    weekday = date.weekday()
    start_date = datetime(year=date.year, month=date.month, day=date.day) - timedelta(days=weekday)
    return datetime.strftime(start_date, fmt) if to_str else start_date


def get_week_end_date(date: datetime = None, date_string: str = None, fmt: str = FMT.TIME_ISO_S, to_str=True):
    """获取指定日期或当前日期所在周的最后一天，后一秒"""
    if date is None and date_string is None:
        date = datetime.now()
    if date is None:
        date = datetime.strptime(date_string, fmt)

    weekday = date.weekday()
    end_date = datetime(year=date.year, month=date.month, day=date.day) + timedelta(days=7 - weekday)
    return datetime.strftime(end_date, fmt) if to_str else end_date


def get_week_range(date: datetime = None, date_string: str = None, fmt: str = FMT.TIME_ISO_S, to_str=True):
    """获取当前日期所在周的范围，第一天到最后一天+1s"""
    return get_week_start_date(date, date_string, fmt), get_week_end_date(date, date_string, fmt, to_str)


def now_str(fmt=FMT.TIME_ISO_S):
    """当前时间-str"""
    return datetime.strftime(datetime.now(), fmt)
