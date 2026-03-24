"""IR monitor content normalizers."""

from services.ir_monitor.normalizers.ir_monitor_generic_en_ir_news import (
    normalize as normalize_generic_en_ir_news,
)
from services.ir_monitor.normalizers.ir_monitor_generic_jp_ir_news import (
    normalize as normalize_generic_jp_ir_news,
)
from services.ir_monitor.normalizers.ir_monitor_generic_json_ir_feed import (
    normalize as normalize_generic_json_ir_feed,
)

__all__ = [
    "normalize_generic_en_ir_news",
    "normalize_generic_jp_ir_news",
    "normalize_generic_json_ir_feed",
]
