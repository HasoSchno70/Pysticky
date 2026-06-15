"""
Dialoge für PySticky.
"""

from .blend_threads_dialog import BlendThreadsDialog
from .color_harmony_dialog import ColorHarmonyDialog
from .color_management_dialog import ColorManagementDialog
from .grid_options_dialog import GridOptionsDialog
from .heatmap_dialog import HeatmapDialog
from .hoop_planner_dialog import HoopPlannerDialog
from .image_import_dialog import ImageImportDialog
from .inventory_dialog import InventoryDialog
from .new_project_dialog import NewProjectDialog
from .palette_conversion_dialog import PaletteConversionDialog
from .pattern_import_dialog import PatternImportDialog
from .pattern_library_dialog import PatternLibraryDialog
from .pattern_preview_dialog import PatternPreviewDialog
from .pattern_properties_dialog import PatternPropertiesDialog
from .pdf_protect_dialog import PdfProtectDialog
from .plugin_dialog import PluginDialog
from .replace_color_dialog import ReplaceColorDialog
from .screen_eyedropper_dialog import (
    ScreenEyedropperDialog,
    find_nearest_thread,
    pick_color_at,
)
from .settings_dialog import SettingsDialog
from .similar_colors_dialog import SimilarColorsDialog
from .snapshot_history_dialog import SnapshotHistoryDialog
from .statistics_dialog import PatternStatisticsDialog
from .stitch_path_dialog import StitchPathDialog
from .swap_colors_dialog import SwapColorsDialog
from .symbol_editor_dialog import SymbolEditorDialog
from .user_template_dialog import (
    ManageTemplatesDialog,
    SaveTemplateDialog,
    UserTemplate,
    load_user_templates,
    save_user_templates,
)

__all__ = [
    "ImageImportDialog",
    "ReplaceColorDialog",
    "SwapColorsDialog",
    "GridOptionsDialog",
    "NewProjectDialog",
    "ColorManagementDialog",
    "PatternStatisticsDialog",
    "SymbolEditorDialog",
    "UserTemplate",
    "SaveTemplateDialog",
    "ManageTemplatesDialog",
    "load_user_templates",
    "save_user_templates",
    "ColorHarmonyDialog",
    "PatternImportDialog",
    "PatternLibraryDialog",
    "StitchPathDialog",
    "SettingsDialog",
    "PatternPreviewDialog",
    "PaletteConversionDialog",
    "SimilarColorsDialog",
    "HeatmapDialog",
    "PatternPropertiesDialog",
    "SnapshotHistoryDialog",
    "InventoryDialog",
    "HoopPlannerDialog",
    "BlendThreadsDialog",
    "PluginDialog",
    "PdfProtectDialog",
    "ScreenEyedropperDialog",
    "find_nearest_thread",
    "pick_color_at",
]
