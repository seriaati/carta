import datetime


def get_utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def get_utc8_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))


def get_utc_iso_now() -> str:
    return get_utc_now().isoformat()
