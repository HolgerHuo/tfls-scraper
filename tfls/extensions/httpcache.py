import logging
from email.utils import mktime_tz, parsedate_tz
from time import time
from weakref import WeakKeyDictionary

from scrapy.http import Response
from scrapy.utils.httpobj import urlparse_cached
from scrapy.utils.python import to_bytes, to_unicode

logger = logging.getLogger(__name__)

"""
This modified policy will cache all urls with '/' ending for up to a day, and the rest for up to a month if no RFC2616 defined caching rules can be found.
"""
class ModifiedRFC2616Policy:
    MAXAGE = 3600 * 24 * 31  # one month

    def __init__(self, settings):
        self.always_store = settings.getbool("HTTPCACHE_ALWAYS_STORE")
        self.ignore_schemes = settings.getlist("HTTPCACHE_IGNORE_SCHEMES")
        self._cc_parsed = WeakKeyDictionary()
        self.ignore_response_cache_controls = [
            to_bytes(cc)
            for cc in settings.getlist("HTTPCACHE_IGNORE_RESPONSE_CACHE_CONTROLS")
        ]

    def _parse_cachecontrol(self, r):
        if r not in self._cc_parsed:
            cch = r.headers.get(b"Cache-Control", b"")
            parsed = parse_cachecontrol(cch)
            if isinstance(r, Response):
                for key in self.ignore_response_cache_controls:
                    parsed.pop(key, None)
            self._cc_parsed[r] = parsed
        return self._cc_parsed[r]

    def should_cache_request(self, request):
        if urlparse_cached(request).scheme in self.ignore_schemes:
            return False
        cc = self._parse_cachecontrol(request)
        if b"no-store" in cc:
            return False
        return True

    def should_cache_response(self, response, request):
        cc = self._parse_cachecontrol(response)
        if b"no-store" in cc:
            return False
        if response.status == 304:
            return False
        if self.always_store:
            return True
        if b"max-age" in cc or b"Expires" in response.headers:
            return True
        if response.status in (300, 301, 308):
            return True
        if response.status in (200, 203, 401):
            return b"Last-Modified" in response.headers or b"ETag" in response.headers
        return False

    def is_cached_response_fresh(self, cachedresponse, request):
        cc = self._parse_cachecontrol(cachedresponse)
        ccreq = self._parse_cachecontrol(request)
        if b"no-cache" in cc or b"no-cache" in ccreq:
            return False

        now = time()
        freshnesslifetime = self._compute_freshness_lifetime(
            cachedresponse, request, now
        )
        currentage = self._compute_current_age(cachedresponse, request, now)

        reqmaxage = self._get_max_age(ccreq)
        if reqmaxage is not None:
            freshnesslifetime = min(freshnesslifetime, reqmaxage)

        if currentage < freshnesslifetime:
            return True

        if b"max-stale" in ccreq and b"must-revalidate" not in cc:
            staleage = ccreq[b"max-stale"]
            if staleage is None:
                return True

            try:
                if currentage < freshnesslifetime + max(0, int(staleage)):
                    return True
            except ValueError:
                pass

        self._set_conditional_validators(request, cachedresponse)
        return False

    def is_cached_response_valid(self, cachedresponse, response, request):
        if response.status >= 500:
            cc = self._parse_cachecontrol(cachedresponse)
            if b"must-revalidate" not in cc:
                return True

        return response.status == 304

    def _set_conditional_validators(self, request, cachedresponse):
        if b"Last-Modified" in cachedresponse.headers:
            request.headers[b"If-Modified-Since"] = cachedresponse.headers[
                b"Last-Modified"
            ]

        if b"ETag" in cachedresponse.headers:
            request.headers[b"If-None-Match"] = cachedresponse.headers[b"ETag"]

    def _get_max_age(self, cc):
        try:
            return max(0, int(cc[b"max-age"]))
        except (KeyError, ValueError):
            return None

    def _compute_freshness_lifetime(self, response, request, now):
        cc = self._parse_cachecontrol(response)
        maxage = self._get_max_age(cc)
        if maxage is not None:
            return maxage

        date = rfc1123_to_epoch(response.headers.get(b"Date")) or now

        if b"Expires" in response.headers:
            expires = rfc1123_to_epoch(response.headers[b"Expires"])
            return max(0, expires - date) if expires else 0

        if response.url.endswith('/'):
            return 3600 * 24
        else:
            return 3600 * 24 * 31

        #lastmodified = rfc1123_to_epoch(response.headers.get(b"Last-Modified"))
        #if lastmodified and lastmodified <= date:
        #    return (date - lastmodified) / 10

        if response.status in (300, 301, 308):
            return self.MAXAGE

        return 0

    def _compute_current_age(self, response, request, now):
        date = rfc1123_to_epoch(response.headers.get(b"Date")) or now
        if now > date:
            currentage = now - date

        if b"Age" in response.headers:
            try:
                age = int(response.headers[b"Age"])
                currentage = max(currentage, age)
            except ValueError:
                pass

        return currentage

def parse_cachecontrol(header):
    directives = {}
    for directive in header.split(b","):
        key, sep, val = directive.strip().partition(b"=")
        if key:
            directives[key.lower()] = val if sep else None
    return directives

def rfc1123_to_epoch(date_str):
    try:
        date_str = to_unicode(date_str, encoding="ascii")
        return mktime_tz(parsedate_tz(date_str))
    except Exception:
        return None