from __future__ import annotations

from dataclasses import dataclass, field

from models.beta import MoveType
from models.climber import ClimberProfile


@dataclass
class MovementDefinition:
    """Physical definition of a climbing movement technique."""

    move_type: MoveType
    description: str
    coaching_cue: str
    typical_difficulty: float  # 0-1 relative difficulty
    energy_cost: float  # 0-1
    risk_level: float  # 0-1
    min_core_strength: float  # 0-1 minimum required
    min_finger_strength: float  # 0-1 minimum required
    min_hip_mobility_deg: float
    min_shoulder_mobility_deg: float
    injury_risks: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    incompatible_injuries: list[str] = field(default_factory=list)


MOVEMENT_LIBRARY: dict[MoveType, MovementDefinition] = {
    MoveType.STATIC: MovementDefinition(
        move_type=MoveType.STATIC,
        description="Controlled static movement — move each limb deliberately without momentum",
        coaching_cue="Control your movement, engage your core, move through a still position",
        typical_difficulty=0.2,
        energy_cost=0.4,
        risk_level=0.05,
        min_core_strength=0.2,
        min_finger_strength=0.2,
        min_hip_mobility_deg=60.0,
        min_shoulder_mobility_deg=120.0,
        injury_risks=[],
        prerequisites=[],
        incompatible_injuries=[],
    ),
    MoveType.DEADPOINT: MovementDefinition(
        move_type=MoveType.DEADPOINT,
        description="Match upward momentum with precise timing to catch a hold at the peak of movement",
        coaching_cue="Generate upward momentum with your legs and hips, release and catch at the apex",
        typical_difficulty=0.5,
        energy_cost=0.55,
        risk_level=0.2,
        min_core_strength=0.4,
        min_finger_strength=0.35,
        min_hip_mobility_deg=70.0,
        min_shoulder_mobility_deg=140.0,
        injury_risks=["finger pulley", "shoulder"],
        prerequisites=["static"],
        incompatible_injuries=["acute finger injury", "shoulder impingement"],
    ),
    MoveType.CONTROLLED_DYNO: MovementDefinition(
        move_type=MoveType.CONTROLLED_DYNO,
        description="Dynamic jump to a hold with controlled landing technique",
        coaching_cue="Load your legs, explode upward, spot the hold, land soft and controlled",
        typical_difficulty=0.65,
        energy_cost=0.75,
        risk_level=0.35,
        min_core_strength=0.5,
        min_finger_strength=0.4,
        min_hip_mobility_deg=80.0,
        min_shoulder_mobility_deg=150.0,
        injury_risks=["finger pulley", "shoulder", "elbow"],
        prerequisites=["deadpoint"],
        incompatible_injuries=["finger injury", "shoulder instability"],
    ),
    MoveType.FULL_DYNO: MovementDefinition(
        move_type=MoveType.FULL_DYNO,
        description="Both feet leave the wall — fully dynamic jump to distant hold",
        coaching_cue="Full commitment — both feet off, generate max power, stick the catch",
        typical_difficulty=0.85,
        energy_cost=0.9,
        risk_level=0.55,
        min_core_strength=0.65,
        min_finger_strength=0.6,
        min_hip_mobility_deg=80.0,
        min_shoulder_mobility_deg=160.0,
        injury_risks=["finger pulley", "shoulder", "elbow", "hip flexor"],
        prerequisites=["controlled_dyno"],
        incompatible_injuries=["finger injury", "shoulder instability", "knee injury"],
    ),
    MoveType.DROP_KNEE: MovementDefinition(
        move_type=MoveType.DROP_KNEE,
        description="Inside knee drops down while outside hip rotates into the wall",
        coaching_cue="Drop your knee down and in, turn your hip to the wall, reach long",
        typical_difficulty=0.45,
        energy_cost=0.4,
        risk_level=0.25,
        min_core_strength=0.35,
        min_finger_strength=0.25,
        min_hip_mobility_deg=80.0,
        min_shoulder_mobility_deg=130.0,
        injury_risks=["knee", "hip"],
        prerequisites=[],
        incompatible_injuries=["knee injury", "hip injury"],
    ),
    MoveType.BACKSTEP: MovementDefinition(
        move_type=MoveType.BACKSTEP,
        description="Outside edge of foot on hold with hip turned into wall",
        coaching_cue="Outside edge on, turn your hip toward the wall, stay close",
        typical_difficulty=0.35,
        energy_cost=0.35,
        risk_level=0.1,
        min_core_strength=0.3,
        min_finger_strength=0.2,
        min_hip_mobility_deg=70.0,
        min_shoulder_mobility_deg=120.0,
        injury_risks=[],
        prerequisites=[],
        incompatible_injuries=[],
    ),
    MoveType.HEEL_HOOK: MovementDefinition(
        move_type=MoveType.HEEL_HOOK,
        description="Heel placed on or behind a hold to provide upward pulling force",
        coaching_cue="Drive your heel into the hold, engage your hamstring, pull with your leg",
        typical_difficulty=0.55,
        energy_cost=0.5,
        risk_level=0.3,
        min_core_strength=0.4,
        min_finger_strength=0.2,
        min_hip_mobility_deg=90.0,
        min_shoulder_mobility_deg=120.0,
        injury_risks=["hamstring", "hip flexor", "knee"],
        prerequisites=[],
        incompatible_injuries=["hamstring injury", "hip injury", "knee injury"],
    ),
    MoveType.TOE_HOOK: MovementDefinition(
        move_type=MoveType.TOE_HOOK,
        description="Top of foot hooked on hold edge, providing downward pulling force",
        coaching_cue="Hook your toe on top of the hold, pull with your shin muscle (tibialis anterior)",
        typical_difficulty=0.5,
        energy_cost=0.45,
        risk_level=0.2,
        min_core_strength=0.4,
        min_finger_strength=0.2,
        min_hip_mobility_deg=80.0,
        min_shoulder_mobility_deg=120.0,
        injury_risks=["ankle", "knee"],
        prerequisites=[],
        incompatible_injuries=["ankle injury"],
    ),
    MoveType.INSIDE_FLAG: MovementDefinition(
        move_type=MoveType.INSIDE_FLAG,
        description="Inside foot crosses behind standing leg to counterbalance",
        coaching_cue="Cross your flagging foot behind your body, keep hips close to wall",
        typical_difficulty=0.3,
        energy_cost=0.25,
        risk_level=0.1,
        min_core_strength=0.25,
        min_finger_strength=0.2,
        min_hip_mobility_deg=60.0,
        min_shoulder_mobility_deg=110.0,
        injury_risks=[],
        prerequisites=[],
        incompatible_injuries=[],
    ),
    MoveType.OUTSIDE_FLAG: MovementDefinition(
        move_type=MoveType.OUTSIDE_FLAG,
        description="Outside foot extends away from body to counterbalance hip rotation",
        coaching_cue="Extend your flagging foot outward, use it to control hip position",
        typical_difficulty=0.3,
        energy_cost=0.25,
        risk_level=0.1,
        min_core_strength=0.25,
        min_finger_strength=0.2,
        min_hip_mobility_deg=60.0,
        min_shoulder_mobility_deg=110.0,
        injury_risks=[],
        prerequisites=[],
        incompatible_injuries=[],
    ),
    MoveType.ROCK_OVER: MovementDefinition(
        move_type=MoveType.ROCK_OVER,
        description="Weight transfer over a high foot to stand up",
        coaching_cue="Place foot high, transfer weight completely over it, push to stand",
        typical_difficulty=0.55,
        energy_cost=0.5,
        risk_level=0.2,
        min_core_strength=0.4,
        min_finger_strength=0.2,
        min_hip_mobility_deg=90.0,
        min_shoulder_mobility_deg=120.0,
        injury_risks=["knee", "hip"],
        prerequisites=[],
        incompatible_injuries=["knee injury", "hip injury"],
    ),
    MoveType.HIGH_STEP: MovementDefinition(
        move_type=MoveType.HIGH_STEP,
        description="Foot placed on a high hold, knee driven up toward chest",
        coaching_cue="High step your foot, keep your heel down, drive your knee up and over",
        typical_difficulty=0.4,
        energy_cost=0.45,
        risk_level=0.15,
        min_core_strength=0.35,
        min_finger_strength=0.2,
        min_hip_mobility_deg=100.0,
        min_shoulder_mobility_deg=120.0,
        injury_risks=["hip flexor", "hamstring"],
        prerequisites=[],
        incompatible_injuries=["hip injury", "knee injury"],
    ),
    MoveType.COMPRESSION: MovementDefinition(
        move_type=MoveType.COMPRESSION,
        description="Squeeze inward on two opposing holds to generate upward force",
        coaching_cue="Push your hands in and down on opposite sides, use body tension as the hold",
        typical_difficulty=0.6,
        energy_cost=0.65,
        risk_level=0.2,
        min_core_strength=0.6,
        min_finger_strength=0.4,
        min_hip_mobility_deg=70.0,
        min_shoulder_mobility_deg=140.0,
        injury_risks=["shoulder", "core"],
        prerequisites=[],
        incompatible_injuries=["shoulder impingement"],
    ),
    MoveType.KNEEBAR: MovementDefinition(
        move_type=MoveType.KNEEBAR,
        description="Knee pressed against a volume/hold to lock off and rest",
        coaching_cue="Drive your knee into the volume, lock off, shake out your arms to rest",
        typical_difficulty=0.45,
        energy_cost=0.2,  # restful once established
        risk_level=0.3,
        min_core_strength=0.3,
        min_finger_strength=0.1,
        min_hip_mobility_deg=80.0,
        min_shoulder_mobility_deg=100.0,
        injury_risks=["knee"],
        prerequisites=[],
        incompatible_injuries=["knee injury"],
    ),
    MoveType.MANTLE: MovementDefinition(
        move_type=MoveType.MANTLE,
        description="Push down on a hold while bringing feet up to stand on it",
        coaching_cue="Pull up, transition hands from pulling to pushing, stand up on the hold",
        typical_difficulty=0.6,
        energy_cost=0.6,
        risk_level=0.2,
        min_core_strength=0.5,
        min_finger_strength=0.3,
        min_hip_mobility_deg=80.0,
        min_shoulder_mobility_deg=150.0,
        injury_risks=["shoulder", "wrist"],
        prerequisites=[],
        incompatible_injuries=["shoulder injury", "wrist injury"],
    ),
    MoveType.LOCKOFF: MovementDefinition(
        move_type=MoveType.LOCKOFF,
        description="Hold a bent-arm pull position to reach the next hold",
        coaching_cue="Pull to lock, hold the position with bent arm, reach with the free hand",
        typical_difficulty=0.55,
        energy_cost=0.7,
        risk_level=0.15,
        min_core_strength=0.5,
        min_finger_strength=0.45,
        min_hip_mobility_deg=60.0,
        min_shoulder_mobility_deg=140.0,
        injury_risks=["elbow", "shoulder"],
        prerequisites=["static"],
        incompatible_injuries=["elbow tendinitis", "shoulder injury"],
    ),
    MoveType.HIP_TWIST: MovementDefinition(
        move_type=MoveType.HIP_TWIST,
        description="Rotate hips toward wall to improve reach and reduce barn-door risk",
        coaching_cue="Turn your hip toward the wall, keep shoulders square to next target",
        typical_difficulty=0.25,
        energy_cost=0.2,
        risk_level=0.05,
        min_core_strength=0.2,
        min_finger_strength=0.1,
        min_hip_mobility_deg=60.0,
        min_shoulder_mobility_deg=100.0,
        injury_risks=[],
        prerequisites=[],
        incompatible_injuries=["hip injury"],
    ),
    MoveType.CROSS_THROUGH: MovementDefinition(
        move_type=MoveType.CROSS_THROUGH,
        description="Cross one hand underneath and in front of the other",
        coaching_cue="Cross the trailing hand through under the lead hand to gain ground",
        typical_difficulty=0.4,
        energy_cost=0.4,
        risk_level=0.15,
        min_core_strength=0.35,
        min_finger_strength=0.25,
        min_hip_mobility_deg=60.0,
        min_shoulder_mobility_deg=130.0,
        injury_risks=["shoulder"],
        prerequisites=["static"],
        incompatible_injuries=["shoulder injury"],
    ),
    MoveType.CROSS_OVER: MovementDefinition(
        move_type=MoveType.CROSS_OVER,
        description="Cross one hand over the top of the other",
        coaching_cue="Reach your crossing hand over the top, maintain balance through rotation",
        typical_difficulty=0.4,
        energy_cost=0.4,
        risk_level=0.15,
        min_core_strength=0.35,
        min_finger_strength=0.25,
        min_hip_mobility_deg=60.0,
        min_shoulder_mobility_deg=130.0,
        injury_risks=["shoulder"],
        prerequisites=["static"],
        incompatible_injuries=["shoulder injury"],
    ),
    MoveType.SWING_CONTROL: MovementDefinition(
        move_type=MoveType.SWING_CONTROL,
        description="Control body swing after cutting feet off wall",
        coaching_cue="Anticipate the swing, engage core, use the momentum constructively",
        typical_difficulty=0.5,
        energy_cost=0.55,
        risk_level=0.3,
        min_core_strength=0.55,
        min_finger_strength=0.4,
        min_hip_mobility_deg=60.0,
        min_shoulder_mobility_deg=140.0,
        injury_risks=["shoulder", "finger"],
        prerequisites=["static"],
        incompatible_injuries=["finger injury", "shoulder injury"],
    ),
    MoveType.CAMPUS_MOVE: MovementDefinition(
        move_type=MoveType.CAMPUS_MOVE,
        description="Move without using feet — hand over hand on holds",
        coaching_cue="No feet — pull hard, generate momentum with your body, move hands fast",
        typical_difficulty=0.9,
        energy_cost=0.95,
        risk_level=0.6,
        min_core_strength=0.7,
        min_finger_strength=0.75,
        min_hip_mobility_deg=60.0,
        min_shoulder_mobility_deg=160.0,
        injury_risks=["finger pulley", "shoulder", "elbow"],
        prerequisites=["lockoff", "deadpoint"],
        incompatible_injuries=["finger injury", "shoulder instability", "elbow injury"],
    ),
    MoveType.STEM: MovementDefinition(
        move_type=MoveType.STEM,
        description="Feet pressing outward on two opposing surfaces (corner stems)",
        coaching_cue="Press outward with both feet, use the opposition to rest your hands",
        typical_difficulty=0.3,
        energy_cost=0.2,
        risk_level=0.1,
        min_core_strength=0.2,
        min_finger_strength=0.1,
        min_hip_mobility_deg=70.0,
        min_shoulder_mobility_deg=100.0,
        injury_risks=[],
        prerequisites=[],
        incompatible_injuries=[],
    ),
    # Remaining move types with reasonable defaults
    MoveType.HAND_BUMP: MovementDefinition(
        move_type=MoveType.HAND_BUMP,
        description="Move a hand to a nearby intermediate position",
        coaching_cue="Small bump move — keep feet stable, move hand to improve position",
        typical_difficulty=0.25, energy_cost=0.25, risk_level=0.1,
        min_core_strength=0.2, min_finger_strength=0.2, min_hip_mobility_deg=60.0, min_shoulder_mobility_deg=110.0,
    ),
    MoveType.HAND_MATCH: MovementDefinition(
        move_type=MoveType.HAND_MATCH,
        description="Bring both hands to the same hold",
        coaching_cue="Match hands on the hold, redistribute weight, prepare for next move",
        typical_difficulty=0.2, energy_cost=0.3, risk_level=0.05,
        min_core_strength=0.2, min_finger_strength=0.2, min_hip_mobility_deg=60.0, min_shoulder_mobility_deg=110.0,
    ),
    MoveType.FOOT_MATCH: MovementDefinition(
        move_type=MoveType.FOOT_MATCH,
        description="Bring both feet to the same hold",
        coaching_cue="Match feet on the hold, balance carefully, spring up",
        typical_difficulty=0.3, energy_cost=0.3, risk_level=0.15,
        min_core_strength=0.3, min_finger_strength=0.2, min_hip_mobility_deg=70.0, min_shoulder_mobility_deg=110.0,
    ),
    MoveType.REVERSE_FLAG: MovementDefinition(
        move_type=MoveType.REVERSE_FLAG,
        description="Flag foot to the opposite side for counterbalance",
        coaching_cue="Flag your foot to the opposite side, lean into the balance",
        typical_difficulty=0.3, energy_cost=0.25, risk_level=0.1,
        min_core_strength=0.25, min_finger_strength=0.2, min_hip_mobility_deg=60.0, min_shoulder_mobility_deg=110.0,
    ),
    MoveType.BICYCLE: MovementDefinition(
        move_type=MoveType.BICYCLE,
        description="Toe and heel of same foot on opposite sides of a feature",
        coaching_cue="Pinch the hold between your toe and heel, lock in position",
        typical_difficulty=0.5, energy_cost=0.4, risk_level=0.2,
        min_core_strength=0.4, min_finger_strength=0.2, min_hip_mobility_deg=85.0, min_shoulder_mobility_deg=120.0,
        injury_risks=["ankle", "knee"], incompatible_injuries=["ankle injury", "knee injury"],
    ),
    MoveType.SCUM: MovementDefinition(
        move_type=MoveType.SCUM,
        description="Drag a body part (usually knee or hip) on the wall for balance",
        coaching_cue="Let your knee/hip touch the wall, use the contact point for stability",
        typical_difficulty=0.3, energy_cost=0.35, risk_level=0.1,
        min_core_strength=0.25, min_finger_strength=0.2, min_hip_mobility_deg=60.0, min_shoulder_mobility_deg=110.0,
    ),
    MoveType.BRIDGE: MovementDefinition(
        move_type=MoveType.BRIDGE,
        description="Feet on opposing walls or features, body bridged between them",
        coaching_cue="Press outward with both feet on opposing surfaces, stay engaged",
        typical_difficulty=0.45, energy_cost=0.4, risk_level=0.15,
        min_core_strength=0.4, min_finger_strength=0.1, min_hip_mobility_deg=70.0, min_shoulder_mobility_deg=110.0,
    ),
    MoveType.PALM_PRESS: MovementDefinition(
        move_type=MoveType.PALM_PRESS,
        description="Press palm flat against wall or volume for friction and stability",
        coaching_cue="Press your palm into the surface, commit to the friction",
        typical_difficulty=0.35, energy_cost=0.4, risk_level=0.1,
        min_core_strength=0.3, min_finger_strength=0.1, min_hip_mobility_deg=60.0, min_shoulder_mobility_deg=120.0,
    ),
    MoveType.CUT_LOOSE: MovementDefinition(
        move_type=MoveType.CUT_LOOSE,
        description="Both feet swing off the wall intentionally",
        coaching_cue="Let the feet swing, grip hard, control the pendulum, find new foot placements",
        typical_difficulty=0.7, energy_cost=0.7, risk_level=0.4,
        min_core_strength=0.6, min_finger_strength=0.55, min_hip_mobility_deg=70.0, min_shoulder_mobility_deg=150.0,
        injury_risks=["finger", "shoulder"], incompatible_injuries=["finger injury", "shoulder injury"],
    ),
    MoveType.HIP_DRIVE: MovementDefinition(
        move_type=MoveType.HIP_DRIVE,
        description="Drive hips upward to generate power for next hold",
        coaching_cue="Push hips up and toward wall, use legs as primary power source",
        typical_difficulty=0.35, energy_cost=0.45, risk_level=0.1,
        min_core_strength=0.4, min_finger_strength=0.2, min_hip_mobility_deg=70.0, min_shoulder_mobility_deg=120.0,
    ),
    MoveType.SHOULDER_ROTATION: MovementDefinition(
        move_type=MoveType.SHOULDER_ROTATION,
        description="Rotate shoulder to improve reach direction or hold orientation",
        coaching_cue="Turn your shoulder toward the hold, gain a few extra centimeters of reach",
        typical_difficulty=0.2, energy_cost=0.2, risk_level=0.1,
        min_core_strength=0.2, min_finger_strength=0.1, min_hip_mobility_deg=60.0, min_shoulder_mobility_deg=130.0,
        incompatible_injuries=["shoulder injury"],
    ),
}


class MovementLibrary:
    """Library of all climbing movement techniques with physical constraints."""

    def __init__(self) -> None:
        self._library = MOVEMENT_LIBRARY

    def get(self, move_type: MoveType) -> MovementDefinition | None:
        return self._library.get(move_type)

    def get_applicable_moves(
        self,
        profile: ClimberProfile,
        wall_angle_deg: float,
    ) -> list[tuple[MoveType, float]]:
        """Return move types applicable for this climber, sorted by suitability score.

        Returns list of (move_type, suitability_score) where 1.0 = ideal fit.
        """
        results: list[tuple[MoveType, float]] = []

        for move_type, defn in self._library.items():
            safe, _ = self.is_move_safe(move_type, profile)
            if not safe:
                continue

            score = self._compute_suitability(defn, profile, wall_angle_deg)
            results.append((move_type, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def is_move_safe(
        self, move_type: MoveType, profile: ClimberProfile
    ) -> tuple[bool, list[str]]:
        """Check if a move type is safe for the given climber profile.

        Returns (is_safe, reasons_if_not).
        """
        defn = self._library.get(move_type)
        if defn is None:
            return False, [f"Unknown move type: {move_type}"]

        reasons: list[str] = []

        # Check injury restrictions
        for restricted in defn.incompatible_injuries:
            if profile.has_restriction(restricted):
                reasons.append(f"Restricted due to injury: {restricted}")

        # Check strength requirements
        if profile.core_strength_score < defn.min_core_strength:
            reasons.append(
                f"Insufficient core strength ({profile.core_strength_score:.0%} < {defn.min_core_strength:.0%})"
            )
        if profile.finger_strength_score < defn.min_finger_strength:
            reasons.append(
                f"Insufficient finger strength ({profile.finger_strength_score:.0%} < {defn.min_finger_strength:.0%})"
            )

        # Check mobility
        if profile.hip_mobility_deg < defn.min_hip_mobility_deg:
            reasons.append(
                f"Insufficient hip mobility ({profile.hip_mobility_deg:.0f}° < {defn.min_hip_mobility_deg:.0f}°)"
            )
        if profile.shoulder_mobility_deg < defn.min_shoulder_mobility_deg:
            reasons.append(
                f"Insufficient shoulder mobility ({profile.shoulder_mobility_deg:.0f}° < {defn.min_shoulder_mobility_deg:.0f}°)"
            )

        return len(reasons) == 0, reasons

    def _compute_suitability(
        self,
        defn: MovementDefinition,
        profile: ClimberProfile,
        wall_angle_deg: float,
    ) -> float:
        """Score how well this move type suits the given climber (0-1)."""
        score = 1.0

        # Penalty for difficulty relative to experience
        experience_to_v = {
            "beginner": 3, "intermediate": 6, "advanced": 9, "expert": 12, "elite": 17
        }
        exp_v = experience_to_v.get(profile.experience_level.value, 5)
        # Harder moves are less suitable for less experienced climbers
        score -= max(0, defn.typical_difficulty - (exp_v / 17.0)) * 0.5

        # Prefer dynamic moves for dynamic climbers
        if defn.move_type in (MoveType.DEADPOINT, MoveType.CONTROLLED_DYNO, MoveType.FULL_DYNO):
            score += profile.dynamic_comfort_score * 0.2
            score -= profile.fear_of_dynamic * 0.3

        # Static preference
        if defn.move_type == MoveType.STATIC and profile.preferred_style.value == "static":
            score += 0.2

        # Energy efficiency
        score -= defn.energy_cost * 0.1

        return max(0.0, min(1.0, score))
