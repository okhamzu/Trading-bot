from src.strategy.models.ob_retest import OrderBlockRetestModel
from src.strategy.models.ote import OTEModel
from src.strategy.models.silver_bullet import SilverBulletModel
from src.strategy.models.sweep_mss_fvg import SweepMSSFVGModel

MODELS = {
    "sweep_mss_fvg": SweepMSSFVGModel,
    "ob_retest": OrderBlockRetestModel,
    "ote": OTEModel,
    "silver_bullet": SilverBulletModel,
}
