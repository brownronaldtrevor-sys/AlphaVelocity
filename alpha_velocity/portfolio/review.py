from dataclasses import dataclass
from alpha_velocity.signals.technical import TechnicalSnapshot

@dataclass(frozen=True)
class PositionReview:
    action:str
    reason:str
    current_score:float
    replacement_score:float|None=None

def review_position(current:TechnicalSnapshot,best_alternative:TechnicalSnapshot|None,replacement_margin:float=12.0)->PositionReview:
    alt=best_alternative.composite_score if best_alternative else None
    if current.state=='AVOID_OR_EXIT_REVIEW': return PositionReview('EXIT_REVIEW','Technical state deteriorated below the hold threshold.',current.composite_score,alt)
    if alt is not None and alt>=current.composite_score+replacement_margin: return PositionReview('ROTATE_REVIEW','A materially stronger paper opportunity exceeds the current holding.',current.composite_score,alt)
    if current.composite_score>=82: return PositionReview('HOLD_OR_ADD_REVIEW','Price, trend and volume remain strongly aligned.',current.composite_score,alt)
    return PositionReview('HOLD_REVIEW','No validated technical reason to replace the position.',current.composite_score,alt)
