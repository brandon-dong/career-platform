import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./career_platform.db')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'career-platform')
CONTACT_EMAIL = os.getenv('CONTACT_EMAIL', 'bdong4@lion.lmu.edu')
LINKEDIN_URL = os.getenv('LINKEDIN_URL', 'https://www.linkedin.com/in/brandondong98/')
# Google Analytics 4 Web stream for https://brandondong.me. The ID is public
# (it appears in every page's source); set it to an empty string to turn the
# tag and the consent banner off.
GA_MEASUREMENT_ID = os.getenv('GA_MEASUREMENT_ID', 'G-RBCK2JQ78P')
