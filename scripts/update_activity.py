"""Render a profile heatmap from GitHub's unauthenticated public calendar."""

import re
from datetime import date, timedelta
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CALENDAR_URL = "https://github.com/users/lysapala93/contributions"
COLORS = ("#1e293b", "#134e4a", "#0f766e", "#14b8a6", "#5eead4")


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.labels = {}
        self.tooltip = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and "data-date" in attrs:
            self.cells[attrs["id"]] = (
                date.fromisoformat(attrs["data-date"]),
                int(attrs["data-level"]),
            )
        if tag == "tool-tip":
            self.tooltip = attrs.get("for")
            if self.tooltip:
                self.labels[self.tooltip] = ""

    def handle_data(self, data):
        if self.tooltip:
            self.labels[self.tooltip] += data

    def handle_endtag(self, tag):
        if tag == "tool-tip":
            self.tooltip = None

    def days(self):
        days = []
        for cell_id, (day, level) in self.cells.items():
            label = self.labels.get(cell_id, "").strip()
            match = re.match(r"^(No|[0-9][0-9,]*) contributions? on ", label)
            if not match or not 0 <= level < len(COLORS):
                raise ValueError(f"Unrecognized contribution cell: {day}: {label!r}")
            count = 0 if match[1] == "No" else int(match[1].replace(",", ""))
            days.append((day, count, level))
        days.sort()
        if not 350 <= len(days) <= 371:
            raise ValueError(f"Expected a full public calendar, got {len(days)} days")
        for previous, current in zip(days, days[1:]):
            if current[0] - previous[0] != timedelta(days=1):
                raise ValueError("Contribution calendar has missing or duplicate dates")
        return days


def render(days):
    total = sum(count for _, count, _ in days)
    active = sum(count > 0 for _, count, _ in days)
    peak = max(count for _, count, _ in days)
    start, end = days[0][0], days[-1][0]
    origin = start - timedelta(days=(start.weekday() + 1) % 7)
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="350" '
        'viewBox="0 0 1000 350" role="img" aria-labelledby="title description">',
        '<title id="title">Personal GitHub contribution dashboard</title>',
        f'<desc id="description">Publicly visible contributions for lysapala93, '
        f'{start} through {end}: {total} contributions across {active} active days. '
        f'Busiest day: {peak} contributions.</desc>',
        '<rect width="1000" height="350" rx="20" fill="#0b1220"/>',
        '<rect x=".5" y=".5" width="999" height="349" rx="20" '
        'fill="none" stroke="#25364c"/>',
        '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif">',
    ]

    def text(x, y, content, size=12, color="#94a3b8", weight=400):
        elements.append(
            f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}">{escape(str(content))}</text>'
        )

    text(32, 34, "PERSONAL / OPEN SOURCE", color="#5eead4", weight=700)
    text(715, 34, f"{start:%d %b %Y} - {end:%d %b %Y}")
    for x, value, label in (
        (32, f"{total:,}", "CONTRIBUTIONS"),
        (350, active, "ACTIVE DAYS"),
        (670, peak, "BUSIEST DAY"),
    ):
        text(x, 88, value, 36, "#f1f5f9", 700)
        text(x, 112, label, 11)
    elements.append('<path d="M32 132H968" stroke="#25364c"/>')

    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        text(32, 187 + row * 17, label, 11)

    month = None
    for day, count, level in days:
        week, row = divmod((day - origin).days, 7)
        x, y = round(95 + week * 16.2, 1), 176 + row * 17
        # Label only complete month boundaries to avoid adjacent clipped labels.
        if day.day == 1 and day.month != month:
            text(x, 161, day.strftime("%b"), 11)
            month = day.month
        elements.append(
            f'<rect x="{x}" y="{y}" width="13" height="13" rx="3" '
            f'fill="{COLORS[level]}"><title>{day}: {count} contributions</title></rect>'
        )
    text(32, 327, "LYSAPALA93 / PUBLIC PROFILE ACTIVITY", 10)
    text(430, 327, f"Updated {date.today().isoformat()}", 10)
    text(790, 327, "Less", 10)
    for level, color in enumerate(COLORS):
        elements.append(
            f'<rect x="{820 + level * 19}" y="317" width="13" height="13" '
            f'rx="3" fill="{color}"/>'
        )
    text(923, 327, "More", 10)
    elements.extend(("</g>", "</svg>"))
    return "\n".join(elements) + "\n"


def main():
    request = Request(
        CALENDAR_URL,
        headers={"User-Agent": "lysapala93-profile-dashboard", "Accept-Language": "en"},
    )
    # Deliberately no token or cookies: never publish privileged account activity.
    with urlopen(request, timeout=30) as response:
        if response.url != CALENDAR_URL:
            raise RuntimeError(f"Public calendar redirected to {response.url}")
        document = response.read().decode("utf-8")
    parser = CalendarParser()
    parser.feed(document)
    days = parser.days()
    if abs((date.today() - days[-1][0]).days) > 2:
        raise ValueError("Public calendar is stale or has an unexpected end date")
    output = ROOT / "assets" / "activity.svg"
    output.write_text(render(days), encoding="utf-8")
    print(f"Updated {output.relative_to(ROOT)} from {len(days)} public calendar days")


if __name__ == "__main__":
    main()
