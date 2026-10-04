import unittest
from datetime import date, timedelta
from xml.etree import ElementTree

from update_activity import CalendarParser, render


def calendar_html():
    cells = []
    for offset in range(365):
        day = date(2025, 1, 1) + timedelta(days=offset)
        label = "No contributions" if offset else "1,234 contributions"
        cells.append(
            f'<td id="day-{offset}" data-date="{day}" '
            f'data-level="{4 if offset == 0 else 0}"></td>'
            f'<tool-tip for="day-{offset}">{label} on January 1st.</tool-tip>'
        )
    return "".join(cells)


class ActivityTests(unittest.TestCase):
    def parse(self, html):
        parser = CalendarParser()
        parser.feed(html)
        return parser.days()

    def test_public_calendar_and_svg(self):
        days = self.parse(calendar_html())
        self.assertEqual(len(days), 365)
        self.assertEqual(sum(count for _, count, _ in days), 1234)
        svg = ElementTree.fromstring(render(days))
        ns = {"svg": "http://www.w3.org/2000/svg"}
        cells = svg.findall(".//svg:rect[svg:title]", ns)
        self.assertEqual(len(cells), 365)
        self.assertIn("1234 contributions across 1 active days", svg.find("svg:desc", ns).text)
        for cell in cells:
            self.assertLessEqual(float(cell.attrib["x"]) + 13, 968)
            self.assertLessEqual(float(cell.attrib["y"]) + 13, 300)

    def test_singular_contribution(self):
        days = self.parse(calendar_html().replace("1,234 contributions", "1 contribution"))
        self.assertEqual(days[0][1], 1)

    def test_missing_or_restricted_calendar_fails(self):
        with self.assertRaisesRegex(ValueError, "full public calendar"):
            self.parse("<html>Sign in with SSO</html>")

    def test_missing_tooltip_fails(self):
        with self.assertRaisesRegex(ValueError, "Unrecognized contribution cell"):
            self.parse(calendar_html().replace('for="day-0"', 'for="other"'))

    def test_invalid_level_fails(self):
        with self.assertRaisesRegex(ValueError, "Unrecognized contribution cell"):
            self.parse(calendar_html().replace('data-level="4"', 'data-level="5"'))

    def test_gap_fails(self):
        with self.assertRaisesRegex(ValueError, "missing or duplicate dates"):
            self.parse(calendar_html().replace("2025-01-02", "2025-01-01"))


if __name__ == "__main__":
    unittest.main()
