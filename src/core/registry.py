"""
Central model registry. Import this once at app startup so that all SQLAlchemy
models are registered with Base.metadata before any DB operation.
"""
from src.modules.currencies import models as _currencies  # noqa: F401
from src.modules.users import models as _users  # noqa: F401
from src.modules.groups import models as _groups  # noqa: F401
from src.modules.expenses import models as _expenses  # noqa: F401
from src.modules.settlements import models as _settlements  # noqa: F401
from src.modules.friendships import models as _friendships  # noqa: F401
from src.modules.notifications import models as _notifications  # noqa: F401
