from dataclasses import dataclass


@dataclass
class FallbackProfile:
    headline: str = 'Analytics and Finance Professional'
    summary: str = 'Recruiter-facing profile currently served from fallback content.'
    location: str = 'San Jose, CA'


def get_fallback_profile():
    return FallbackProfile()
