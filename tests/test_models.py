from app.models import Experience, Profile


def test_profile_model_has_required_fields():
    profile = Profile(
        full_name='Jane Doe',
        headline='Analytics and Finance Professional',
        summary='Quantitative and strategic background.',
        location='San Jose, CA',
    )
    assert profile.full_name == 'Jane Doe'
    assert profile.headline == 'Analytics and Finance Professional'


def test_experience_model_supports_metrics():
    exp = Experience(title='Senior Analyst', company_name='Example Corp')
    assert exp.title == 'Senior Analyst'
    assert exp.company_name == 'Example Corp'
