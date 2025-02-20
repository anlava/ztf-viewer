import os
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import numpy as np
import requests

from ztf_viewer.cache import cache
from ztf_viewer.config import ZTF_FITS_PROXY_URL
from ztf_viewer.util import hmjd_to_earth, qid_from_rcid, ccdid_from_rcid


@dataclass
class DateWithFrac:
    year: int
    month: int
    day: int
    fraction: float

    @classmethod
    def from_hmjd(cls, hmjd, coord):
        t = hmjd_to_earth(hmjd, coord)
        dt = t.to_datetime()
        return cls(
            year=dt.year,
            month=dt.month,
            day=dt.day,
            fraction=t.mjd % 1,
        )

    @property
    def monthday(self):
        return f'{self.month:02d}{self.day:02d}'

    def frac_digits(self, digits):
        return round(self.fraction * 10**digits)

    @property
    def products_root(self):
        return f'/products/sci/{self.year}/{self.monthday}/'

    @property
    def products_path(self):
        return f'{self.products_root}{self.frac_digits(6):06d}/'

    def sciimg_path(self, *, fieldid, filter, rcid):
        ccdid = ccdid_from_rcid(rcid)
        qid = qid_from_rcid(rcid)
        filename = f'ztf_{self.year}{self.monthday}{self.frac_digits(6):06d}_{fieldid:06d}_{filter}_c{ccdid:02d}_o_q{qid}_sciimg.fits'
        return os.path.join(self.products_path, filename)


@cache()
def _fracs(products_root):
    url = urljoin(ZTF_FITS_PROXY_URL, products_root)
    body = requests.get(url).text
    fracs = re.findall(r'<a href="(\d{6})/">\1/</a>', body)
    return sorted(int(f) for f in fracs)


def correct_date(date_with_frac):
    fracs = _fracs(date_with_frac.products_root)
    digits = 6
    i = np.searchsorted(fracs, date_with_frac.frac_digits(digits))
    date_with_frac.fraction = fracs[i - 1] / (10.0 ** digits)
