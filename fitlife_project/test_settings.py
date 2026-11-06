import os

os.environ.setdefault("FITLIFE_SECRET_KEY", "fitlife-tests-only")
from .settings import *

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
