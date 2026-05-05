import os

from .base import *  # noqa: F403,F401

DEBUG = True

# When running the Django dev server directly on Windows, Redis and Celery
# workers are usually not running. Execute tasks inline unless explicitly
# disabled through the environment.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=os.name == "nt")
CELERY_TASK_EAGER_PROPAGATES = False
