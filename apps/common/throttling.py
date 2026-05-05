from rest_framework.throttling import SimpleRateThrottle


class PublicMonitorLookupThrottle(SimpleRateThrottle):
    scope = "public_monitor_lookup"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}

