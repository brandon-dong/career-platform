import re

MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
YEAR_MONTH = re.compile(r'^(\d{4})-(0[1-9]|1[0-2])$')


def format_month(value):
    if not value:
        return 'Present'
    match = YEAR_MONTH.match(value)
    if match is None:
        return value
    return f'{MONTHS[int(match.group(2)) - 1]} {match.group(1)}'
