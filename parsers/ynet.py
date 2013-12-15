# -*- coding: utf-8
from baseparser import BaseParser
from bs4 import BeautifulSoup, Tag
import re
import itertools


NBSP = u'\xa0'

class YnetParser(BaseParser):
    domains = ['www.ynet.co.il']

    feeder_pat   = '^http://www.ynet.co.il/articles/'
    feeder_pages = ['http://www.ynet.co.il/']

    def _parse(self, html):
        soup = BeautifulSoup(html, from_encoding='utf-8')

        self.meta = soup.find_all('meta')

        try:
            seo_title = soup.find('meta', property='og:title').get('content')
        except AttributeError:
            # find returned None, None has no get method
            self.real_article = False
            return

        try:
            self.title = soup.find('div', 'art_header_title').get_text()
        except AttributeError:
            self.title = seo_title

        try:
            byline_and_date = (soup.find('span', 'art_header_footer_author')
                .get_text())
        except AttributeError:
            self.real_article = False
            return
        
        byline, _, date = re.split(u'(פורסם|עדכון אחרון):', byline_and_date)
        self.byline = byline.strip()
        self.date = date.strip()

        sub_title_elt = soup.find('div', 'art_header_sub_title')
        sub_title = u'' if sub_title_elt is None else sub_title_elt.get_text()

        body_elt = soup.find('div', 'art_body')
        if body_elt is None:
            self.real_article = False
            return

        def replace_with_para(tag, para_text, dividers=True):
            para = soup.new_tag('p')
            para.string = para_text
            tag.replace_with(para)

            if dividers:
                pre_divider = soup.new_tag('p')
                pre_divider.string = NBSP
                para.insert_before(pre_divider)

                post_divider = soup.new_tag('p')
                post_divider.string = NBSP
                para.insert_after(post_divider)

        # TODO: handle these better, maybe mention the caption
        for video in body_elt.find_all('div', 'art_video'):
            replace_with_para(video, u'(סרטון)')

        for img in body_elt('div', 'citv_image'):
            replace_with_para(img, u'(תמונה)')

        for sidething in body_elt('div', 'arttvgenlink'):
            sidething.decompose()

        for ad in body_elt('div', 'CAATVcompAdvertiseTv'):
            # these are floated left
            replace_with_para(ad, u' (פרסומת) ', dividers=False)

        def body_part_to_text(part):
            if part.name == 'p':
                t = part.get_text()
                if t == NBSP:
                    # p contains just nbsp => this is the paragraph division
                    return u'\n\n'
                else:
                    return re.sub(r'\s+', ' ', t.strip())

            if part.name.startswith('h') and part.name[1:].isdigit():
                return part.get_text().strip() + u'\n\n'

            if part.name == 'ul':
                return u'\n' + u'\n'.join(
                    li.get_text().strip() for li in part('li'))

        # join with ' ' so that adjacent p tags get a space between them.
        # we'll later remove extra spaces.
        self.body = u' '.join(itertools.chain(
            [sub_title, u'\n\n'],
            itertools.ifilter(None,
                itertools.imap(body_part_to_text,
                    body_elt(['p', 'ul', 'h3'])))))

        # remove double spaces created by joining paragraphs with ' '
        self.body = re.sub(r' +', ' ', self.body)

        # remove spaces adjacent to dividers, created by joining paragraphs
        # with ' '
        self.body = re.sub(r'\n\n ', '\n\n', self.body)
        self.body = re.sub(r' \n\n', '\n\n', self.body)

        # also remove double dividers (note that this is done
        # after the adjacent spaces are removed)
        self.body = re.sub(r'\n{3,}', r'\n\n', self.body)
