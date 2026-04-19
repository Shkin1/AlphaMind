# Advisors Package
# 10位投资顾问实现

from .benjamin_graham import BenjaminGrahamAdvisor
from .warren_buffett import WarrenBuffettAdvisor
from .charlie_munger import CharlieMungerAdvisor
from .peter_lynch import PeterLynchAdvisor
from .zhangkun import ZhangKunAdvisor
from .wang_chen import WangChenAdvisor
from .steve_nison import SteveNisonAdvisor
from .edwin_lefevre import EdwinLefevreAdvisor
from .lin_junrui import LinJunruiAdvisor
from .private_equity import PrivateEquityAdvisor

__all__ = [
    "BenjaminGrahamAdvisor",
    "WarrenBuffettAdvisor",
    "CharlieMungerAdvisor",
    "PeterLynchAdvisor",
    "ZhangKunAdvisor",
    "WangChenAdvisor",
    "SteveNisonAdvisor",
    "EdwinLefevreAdvisor",
    "LinJunruiAdvisor",
    "PrivateEquityAdvisor"
]