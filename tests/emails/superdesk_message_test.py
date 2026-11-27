from email.parser import Parser
from email.header import decode_header

from superdesk.core.types import EmailMessage, EmailRequest
from superdesk.core.emails import handle_long_lines_html
from superdesk.tests import TestCase


def check_lines_length(text: str | None, length: int = 998) -> None:
    assert text is not None
    lines = text.splitlines()
    for line in lines:
        assert len(line) < length


class SuperdeskMessageTestCase(TestCase):
    async def test_unicode_subject(self):
        subject = "темы для выделения выделения выделения"
        msg = EmailMessage()
        msg["Subject"] = subject
        out = msg.as_bytes()
        parsed = Parser().parsestr(out.decode("utf-8"), headersonly=True)
        decoded, charset = decode_header(parsed["subject"])[0]
        self.assertEqual(subject, decoded.decode(charset))

    async def test_email_avoid_long_lines(self):
        with self.mail.record_messages() as outbox:
            html = "<p>foo</p>" * 10000
            text = "a" * 500 + " " + "b" * 500 + " " + "c" * 500 + "d"
            await self.mail.send(
                EmailRequest(
                    subject="subject",
                    recipients=["to"],
                    text_body=text,
                    html_body=html,
                )
            )

            assert len(outbox) == 1
            check_lines_length(outbox[0].body)
            check_lines_length(outbox[0].html)
            lines = outbox[0].body.splitlines()
            assert 3 == len(lines)
            assert 500 == len(lines[0])
            assert 500 == len(lines[1])
            assert 501 == len(lines[2])

    async def test_handle_long_lines_html(self):
        html = "<div><p>{}</p></div>".format('foo bar <a href="test">{}</a>baz'.format("loong link" * 1000) * 50)
        formatted = handle_long_lines_html(html)
        for line in formatted.splitlines():
            assert len(line) < 998, line

    async def test_long_lines_html_links(self):
        item = {
            "version": "2",
            "type": "text",
            "byline": "Ralph D. Russo",
            "versioncreated": "2022-10-09T11:37:40+0000",
            "language": "en-CA",
            "headline": "AP Top 25 Takeaways: Interims go 4-0; Alabama misses Bryce",
            "copyrightnotice": "Copyright 2022 The Associated Press. All rights reserved. This material may not be published, broadcast, rewritten or redistributed without permission.",
            "urgency": 5,
            "pubstatus": "usable",
            "ednote": "",
            "body_html": '\n              <p>Maybe making a coaching change less than halfway through the season isn\'t such a terrible idea.</p>\n              <p><a href="https://apnews.com/article/college-football-sports-coaching-scott-frost-b4202a50a9531234e885679158cbf691">After an unprecedented spate of early season firings</a>, teams with interim head coaches went 4-0 this weekend in major college football.</p>\n              <p>“We went from trying not to lose and now we’re learning how to win,” Georgia Tech interim coach Brent Key said. "That’s a valuable lesson that these guys can take to the next game.” </p>\n              <p><a href="https://apnews.com/article/college-football-sports-georgia-jeff-sims-sahmir-hagans-a038d9590d19268c9eac6c6e4d0b4c4a">The Yellow Jackets (3-3) beat Duke</a> to make it two straight victories since Geoff Collins was fired. At 2-1 in the Atlantic Coast Conference, Georgia Tech not only can dream about bowl eligibility, but there is still a path to serious contention for a Coastal Division title.</p>\n              <p>On Friday night in New Jersey, Nebraska won its second straight game for interim coach Mickey Joseph, beating Rutgers to head into the second half of the season tied for first in the Big Ten West.</p>\n              <p>The Cornhuskers actually won a close game (14-13), something that never seemed to go their way under Scott Frost.</p>\n              <p>"A lot of adversity to push through tonight,” Nebraska quarterback Casey Thompson said.</p>\n              <p>Now also lurking in the Big Ten West is Wisconsin. The Badgers dumping Paul Chryst after five games last week was the one truly shocking move among the early firings. </p>\n              <p>Wisconsin elevated defensive coordinator Jim Leonhard, essentially giving the de facto coach-in-waiting a seven-game audition.</p>\n              <p>Good start. <a href="https://apnews.com/article/college-football-sports-illinois-paul-chryst-wisconsin-badgers-86d3f96530e5ff0482c124ce1cbc3eef">The Badgers rolled over Northwestern</a>, with maybe their best offensive game in a few seasons.</p>\n              <p>Graham Merz was 20 for 29 for 299 yards and five touchdowns and Braelon Allen ran for 135 yards. Add the obligatory it was only against Northwestern, but the Badgers looked like a different team. At 1-2 in the Big Ten West, they\'re not out of it.</p>\n              <p>“This is the reward,” Leonhard said. “You put in the work, you put in the time and you should have confidence when you step off that bus that you have the right plan, you have the right guys, you put them in position to have success.”</p>\n              <p>Arizona State made it 4 for 4 for the interim coaches this week. Shaun Aguano earned his first victory since taking over for Herm Edwards with <a href="https://apnews.com/article/college-football-sports-washington-huskies-arizona-state-sun-devils-herm-edwards-22d94d5537816b2f33358e99feef78e9">45-38 victory over No. 21 Washington</a>, which now looks like a team that was highly overrated after beating what looks like a bad Michigan State team.</p>\n              <p>Who\'s next to go?</p>\n              <p>Well, Bryan Harsin left Georgia still the Auburn coach after the <a href="https://apnews.com/article/college-football-sports-athens-georgia-bulldogs-auburn-tigers-1a45441969ba4b99574416b953377686">No. 2 Bulldogs pounded the Tigers 42-10.</a></p>\n              <p>It seems inevitable that change is coming on The Plains. The Tigers have a road trip to No. 9 Mississippi next week and then an open date.</p>\n              <p>It\'s hard to see a coaching change making a difference for Auburn the rest of the way — even though it seems to be working elsewhere.</p>\n              <p>BOOMER BUST</p>\n              <p>The long and glorious history of Oklahoma football hit a nadir in the late 1990s, after a string of failed replacements for Barry Switzer. </p>\n              <p>In 1997, during a run of three straight losing seasons for the Sooners, they were beaten 69-7 by Nebraska. </p>\n              <p>That was the last time Oklahoma was on the short end of a loss more <a href="https://apnews.com/article/college-football-sports-oklahoma-sooners-texas-longhorns-89268786ad003bc1524a78d02871f931">lopsided than Saturday’s Red River game against Texas. </a></p>\n              <p>Brent Venables is only six games into his tenure in Norman, but anytime you\'re bringing back memories of the late 1990s in Oklahoma it\'s not good at all. And really, it has been even worst than that.</p>\n              <p>Add in last week\'s pummeling against TCU, and this is the first time the Sooners have ever lost two straight by 30-plus points, according to ESPN Stats and Info.</p>\n              <p>"We’re good enough on both sides of the ball to be a lot more competitive," Venables said. “You can’t lose a game 49-0, with accountability beginning with me.”</p>\n              <p>Meanwhile, Texas fans can probably convince themselves the Longhorns would have beaten Alabama if Quinn Ewers wasn\'t injured early against the Tide last month.</p>\n              <p>Ewers threw for 289 yards and four touchdowns against Oklahoma.</p>\n              <p>In a Big 12 that seems set to be all kinds of fun and competitive up top -— <a href="https://apnews.com/article/college-football-sports-lawrence-texas-christian-horned-frogs-max-duggan-b972d90f7fa3216ca44e49d3bcb0c59e">No. 17 TCU beat No. 19 Kansas</a> in what might have been the game of the day —- Texas figures to be a factor.</p>\n              <p>As for Oklahoma, even in the dark days for the late 1990s, the Sooners never finished last in the Big 12. That is definitely on the table in 2022.</p>\n              <p>TIDE SURVIVES</p>\n              <p>Turns out Bryce Young is a very important player for No 1. Alabama.</p>\n              <p>The Heisman Trophy winner sat out Saturday night with a shore shoulder and \'Bama did everything it could to give Texas A&amp;M a chance for two straight victories against the Tide.</p>\n              <p>After four Alabama turnovers, three by backup quarterback Jalen Milroe, and two missed field goals by usually excellent kicker Will Reichard, the Aggies had one play from the Tide\'s 2 to win it at the end.</p>\n              <p>The incomplete pass kept <a href="https://apnews.com/article/college-football-sports-alabama-crimson-tide-texas-aandm-aggies-bryce-young-b051b2e0b4fc20b0576573d979b03ab0">the Tide unbeaten</a> and the play call <a href="https://twitter.com/JManziel2/status/1578951316776226816">left former A&amp;M Heisman winner Johnny Manziel dismayed.</a></p>\n              <p>It will go down as one of the stranger games of the Saban dynasty.</p>\n              <p>The Aggies deserve credit for hanging in and taking advantage of some of the Tide\'s mistakes.</p>\n              <p>It is also obvious that when Alabama goes to undefeated and No. 8 Tennessee next week, it really needs Young.</p>\n              <p>AROUND THE COUNTRY</p>\n              <p>TCU receiver Quinten Johnston is a well-known commodity to Big 12 fans and pro scouts, but his breakout game of 14 catches for 206 yards — almost double what he had coming into the game —- should turn him into a national star and legitimate All-America contender ... When you break a record set by Tony Dorsett, that\'s a great day. Pitt\'s Israel Abanikanda ran for 320 yards and six touchdowns <a href="https://apnews.com/article/college-football-sports-pittsburgh-notre-dame-fighting-irish-virginia-tech-hokies-2e0a9aab6174f86498999a22a1c0c9cf">in a victory against Virginia Tech.</a> ... There was a lot of talk about quarterback play in the ACC this year with an impressive group of returning starters. Turns out first-year starter Drake Maye of North Carolina has been the best of the bunch and the Tar Heels look like legitimate favorites in the ACC Coastal, despite their defensive flaws, <a href="https://apnews.com/article/college-football-sports-miami-hurricanes-north-carolina-6556b1ee648bf72ed5c3cd7590c1609b">after beating Miami</a>. ... It feels as if No. 3 Ohio State has not even part of the season since its opener against Notre Dame. The Buckeyes have run through their last five opponents by an average of 54-17 and have next week off before Iowa comes to Columbus. <a href="https://apnews.com/article/college-football-sports-illinois-iowa-hawkeyes-champaign-aa9ef5efa922956be7d874ac17df4f10">Considering the current state of the Hawkeyes</a>, a trip to No. 10 Penn State the following week looks like the next possible test for Ohio State. ... The build up probably took longer than a lot of people hoped, but Chip Kelly has UCLA looking a lot like his Oregon teams. T <a href="https://apnews.com/article/college-football-sports-pasadena-ucla-bruins-utah-utes-b3558ec3e26b6f6ddca88b681f8a2453">he 18th-ranked Bruins were too much for Utah</a> and now both them and <a href="https://apnews.com/article/college-football-sports-washington-southern-california-trojans-pete-carroll-e522c8909de9f2047d51930f2c09237a">No. 6 USC</a> head into the second half of the season unbeaten. Yes, they\'re leaving the Pac-12 after next season, but for now the L.A. schools — along with Oregon — have the conference in its best position to get a team in the College Football Playoff in about three years. ... It would also help the Pac-12 if Notre Dame gets its act together, which appears to be happening <a href="https://apnews.com/article/college-football-nfl-sports-brigham-young-cougars-chris-brooks-c4f0552c117342cb7f85109e98093009">as the Fighting Irish beat No. 16 BYU in Las Vegas.</a> USC finishes the season against the Irish. ... Appalachian State\'s wild season now includes <a href="https://apnews.com/article/college-football-sports-michael-hughes-san-marcos-texas-5271c8a46dfea8f08b6707a32f5635df">a double-digit loss to Texas State to fall to 3-3</a>. ... Kansas coach Lance Leipold\'s former school is doing OK, too. <a href="https://apnews.com/article/college-football-sports-james-patterson-bowling-green-buffalo-bulls-cc18b72445ac722880bb1026a93ad05c">Buffalo is off to a 3-0 start in the MAC</a> under second-year coach Maurice Linguist.</p>\n              <p>___</p>\n              <p>Follow Ralph D. Russo at https://twitter.com/ralphDrussoAP and listen at http://www.appodcasts.com</p>\n              <p>___</p>\n              <p>More AP college football: https://apnews.com/hub/college-football and https://twitter.com/ap_top25. Sign up for the AP’s college football newsletter: https://bit.ly/3pqZVaF</p>\n            \n          ',
            "slugline": "FBC-T25-AP-Top-25-Takeaways",
            "firstcreated": "2022-10-09T02:16:57+0000",
            "firstpublished": "2022-10-09T11:37:38+0000",
            "source": "The Associated Press",
            "extra": {
                "filename": "s0177",
                "itemid": "ea3ed480b5db145e60d54b58152f1c23",
                "headline_extended": "AP Top 25 Takeaways: Interims go 4-0; Alabama misses Bryce",
                "update": "UPDATES: adds links and minor edits.; With AP Photos.",
                "stocks": "",
                "provider": "AP",
                "ap_version": 2,
            },
            "profile": "autorouting",
        }
        html = "<div>{}</div>".format(item["body_html"])
        formatted = handle_long_lines_html(html)
        for line in formatted.splitlines():
            assert len(line) < 998, line

    async def test_email_subject_validation(self):
        with self.mail.record_messages() as outbox:
            html = "<p>foo</p>"
            text = "foo"
            subject = "foo\nbar"
            await self.mail.send(
                EmailRequest(
                    subject=subject,
                    recipients=["to"],
                    text_body=text,
                    html_body=html,
                )
            )
            assert len(outbox) == 1
            assert "foo" == outbox[0].subject
