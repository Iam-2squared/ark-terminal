"""Public JPX format probe; never certifies or writes any security master."""
from urllib.request import Request, urlopen
from urllib.parse import urljoin
import re
import xlrd

INDEX = 'https://www.jpx.co.jp/listing/others/ex-rights/index.html'

def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'ArkTerminal-source-contract/1.0'}), timeout=20) as r:
        data = r.read(8_000_001)
        if len(data) > 8_000_000:
            raise ValueError('SOURCE_SIZE')
        return data

def main():
    text = fetch(INDEX).decode('utf-8')
    links = re.findall(r'href=["\']([^"\']*/([0-9]{8})\.xls)["\']', text)
    if not links:
        raise ValueError('EX_RIGHTS_LINK_CONTRACT')
    href, day = max(links, key=lambda x: x[1])
    raw = fetch(urljoin(INDEX, href))
    book = xlrd.open_workbook(file_contents=raw, on_demand=True)
    print('PUBLIC_JPX_EXRIGHTS_PUBLICATION=' + day)
    print('PUBLIC_JPX_EXRIGHTS_SHEETS=' + repr(book.sheet_names()))
    for sheet in book.sheets():
        print('PUBLIC_SHEET_SHAPE=' + repr((sheet.name, sheet.nrows, sheet.ncols)))
        for i in range(min(18, sheet.nrows)):
            print('PUBLIC_FORMAT_ROW=' + repr(sheet.row_values(i)))
    print('CLEARANCE_PRODUCED=False\nORDER_TRANSMISSION=False')

if __name__ == '__main__':
    main()
