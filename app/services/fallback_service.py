from dataclasses import dataclass, field


@dataclass
class FallbackProfile:
    full_name: str = 'Career Platform'
    headline: str = 'Analytics and Finance Professional'
    summary: str = 'Recruiter-facing profile currently served from fallback content.'
    location: str = 'San Jose, CA'
    availability_status: str = ''
    target_roles: list = field(default_factory=list)


def get_fallback_profile():
    return FallbackProfile()
