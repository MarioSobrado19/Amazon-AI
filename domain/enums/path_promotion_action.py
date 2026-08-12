from enum import Enum


class PathPromotionAction(str, Enum):
    SAVE = "save"
    INVESTIGATE = "investigate"
