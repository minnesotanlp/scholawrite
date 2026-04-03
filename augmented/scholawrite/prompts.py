"""Prompt templates for injection generation."""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from .schema import CognitiveState, DocumentProfile
from .config import get_sensory_anchors, get_discourse_markers

__all__ = [
    "prompt_hash",
    "build_naive_prompt",
    "build_topical_prompt",
    "build_contextual_prompt",
    "build_granular_edit_prompt",
    "build_profiling_prompt",
    "get_sensory_anchor",
    "NAIVE_PROMPT",
    "TOPICAL_PROMPT",
    "CONTEXTUAL_PROMPT",
    "LEAKAGE_GUARD",
    "SENSORY_ANCHORS",
    "PromptTemplate",
]


@dataclass(frozen=True)
class PromptTemplate:
    """A prompt template for injection generation."""
    level: str
    template: str

    def format(self, **kwargs) -> str:
        """Format the template with given keyword arguments."""
        return self.template.format(**kwargs)


# Prompt template constants
NAIVE_PROMPT = PromptTemplate(
    level="naive",
    template="Write a scholarly paragraph about academic research. Maintain formal register.",
)

TOPICAL_PROMPT = PromptTemplate(
    level="topical",
    template="Write a scholarly paragraph about {topic} in the field of {domain}. Maintain formal register.",
)

CONTEXTUAL_PROMPT = PromptTemplate(
    level="contextual",
    template="In the {section} section, write content that bridges the following passages:\n\nPreceding: {preceding}\n\nFollowing: {following}\n\nMaintain formal academic register.",
)


def build_profiling_prompt(abstract: str) -> str:
    """Build a comprehensive prompt to generate a unique DocumentProfile.

    This prompt elicits deep authorial characteristics that inform
    the biometric simulation of the writing process.
    """
    return f"""You are an expert forensic linguist and cognitive psychologist specializing in
academic writing patterns. Analyze the following paper abstract to construct a detailed
psycholinguistic profile of the author.

ABSTRACT TO ANALYZE:
\"\"\"
{abstract}
\"\"\"

Based on the abstract's vocabulary sophistication, syntactic complexity, hedging patterns,
citation density indicators, and domain-specific terminology, infer the following:

Return a JSON object with EXACTLY these fields:

{{
    "persona": "<Specific professional identity, e.g., 'Senior computational linguist with
                cognitive science background, likely 15+ years in academia, methodologically
                rigorous with preference for mixed-methods approaches'>",

    "discipline": "<Precise academic subfield, e.g., 'Psycholinguistics with computational
                   modeling focus' or 'Behavioral Finance with neuroeconomics applications'>",

    "primary_goal": "<Main rhetorical objective when revising, e.g., 'strengthen causal
                     argumentation' or 'increase theoretical precision' or 'clarify
                     methodological constraints'>",

    "secondary_goals": [
        "<Technical priority 1, e.g., 'reduce hedging in results section'>",
        "<Technical priority 2, e.g., 'strengthen transitions between theoretical claims'>",
        "<Technical priority 3, e.g., 'calibrate confidence levels to evidence strength'>"
    ],

    "stylistic_voice": "<Specific writing style description, e.g., 'precise and measured with
                        occasional rhetorical flourishes in theoretical sections; tends toward
                        nominalization; favors passive constructions in methods'>",

    "paranoia_level": <Float 0.0-1.0 representing AI-detection awareness based on field culture:
                       0.0-0.2: Traditional humanities, low tech awareness
                       0.2-0.4: Social sciences, moderate awareness
                       0.4-0.6: Applied sciences, business
                       0.6-0.8: Computer science, data science
                       0.8-1.0: AI/ML researchers, NLP specialists>
}}

IMPORTANT: Base your analysis ONLY on linguistic evidence from the abstract.
Return ONLY the JSON object, no other text.

JSON:"""


# --- Comprehensive Ambient Detail Pool ---
# Sensory anchors are loaded from configs/sensory_anchors.json
# These create realistic environmental intrusions during extended writing sessions
def _get_sensory_anchors_dict() -> Dict[str, List[str]]:
    """Load sensory anchors from config."""
    data = get_sensory_anchors()
    return data.get("anchors", {})


def _get_sensory_weights(session_phase: str) -> Dict[str, float]:
    """Get sensory category weights for a session phase."""
    data = get_sensory_anchors()
    weights = data.get("weights", {})
    phase_key = f"{session_phase}_session"
    phase_weights = weights.get(phase_key, weights.get("early_session", {
        "visual": 0.4, "auditory": 0.35, "somatic": 0.15, "olfactory": 0.05, "temporal": 0.05
    }))
    # Filter out metadata keys like _description
    return {k: v for k, v in phase_weights.items() if not k.startswith("_") and isinstance(v, (int, float))}


# For backwards compatibility
class _SensoryAnchorsProxy:
    """Proxy to lazily load sensory anchors from config."""
    def __getitem__(self, key):
        return _get_sensory_anchors_dict().get(key, [])

    def keys(self):
        return _get_sensory_anchors_dict().keys()

    def values(self):
        return _get_sensory_anchors_dict().values()

    def items(self):
        return _get_sensory_anchors_dict().items()

    def get(self, key, default=None):
        return _get_sensory_anchors_dict().get(key, default)


SENSORY_ANCHORS = _SensoryAnchorsProxy()


def get_sensory_anchor(minute: int, salt: str, weight: int = 1) -> Dict[str, str]:
    """Generate a contextually appropriate sensory intrusion.

    Intrusion probability and severity increase with session duration,
    mimicking natural attention degradation during extended writing.
    Anchors and weights are loaded from configs/sensory_anchors.json.

    Args:
        minute: Current minute in the 90-minute writing session
        salt: Deterministic seed for reproducibility
        weight: Intrusion intensity multiplier (1-3)

    Returns:
        Dict with 'severity' (none/low/medium/high) and 'anchor' description
    """
    rng = random.Random(salt)
    anchors = _get_sensory_anchors_dict()

    # Intrusion probability follows fatigue curve
    # Base 10% at start, rising to 80% at minute 90
    base_prob = 0.10 + (minute / 90.0) * 0.70
    intrusion_prob = min(base_prob * weight, 0.95)

    if rng.random() > intrusion_prob:
        return {"severity": "none", "anchor": "none"}

    # Severity based on fatigue phase
    if minute <= 25:
        severity = "low"
    elif minute <= 50:
        severity = "low" if weight == 1 else "medium"
    elif minute <= 75:
        severity = "medium" if weight == 1 else "high"
    else:
        severity = "high"

    # Select category with fatigue-weighted probabilities from config
    if minute <= 30:
        weights = _get_sensory_weights("early")
    elif minute <= 60:
        weights = _get_sensory_weights("mid")
    else:
        weights = _get_sensory_weights("late")

    categories = list(weights.keys())
    probs = list(weights.values())
    category = rng.choices(categories, weights=probs, k=1)[0]

    category_anchors = anchors.get(category, ["environmental awareness"])
    anchor = rng.choice(category_anchors) if category_anchors else "environmental awareness"

    # Compound intrusions at higher weights
    if weight > 1 and severity in ("medium", "high"):
        other_cats = [c for c in categories if c != category]
        secondary_cat = rng.choice(other_cats)
        secondary_anchors = anchors.get(secondary_cat, ["background distraction"])
        secondary_anchor = rng.choice(secondary_anchors) if secondary_anchors else "background distraction"
        anchor = f"{anchor}; simultaneously aware of {secondary_anchor}"

    if weight > 2 and severity == "high":
        tertiary_cat = rng.choice([c for c in categories if c not in (category, secondary_cat)])
        tertiary_anchors = anchors.get(tertiary_cat, ["peripheral awareness"])
        tertiary_anchor = rng.choice(tertiary_anchors) if tertiary_anchors else "peripheral awareness"
        anchor = f"{anchor}; compounded by {tertiary_anchor}"

    return {"severity": severity, "anchor": anchor}


# --- Comprehensive Leakage Prevention ---
LEAKAGE_GUARD = """
CRITICAL OUTPUT CONSTRAINTS - VIOLATION WILL INVALIDATE RESPONSE:

1. OUTPUT CONTENT: Return ONLY the revised scholarly text itself.

2. FORBIDDEN ELEMENTS (immediate disqualification if present):
   - NO meta-commentary ("Here is the revised...", "I have modified...", "The text now...")
   - NO explanations of changes made
   - NO acknowledgment of instructions received
   - NO phrases like "Sure", "Certainly", "Here you go", "As requested"
   - NO markdown formatting (**, ##, ```, etc.)
   - NO quotation marks wrapping the entire output
   - NO labels like "REVISED:", "OUTPUT:", "RESULT:"
   - NO self-references ("I", "my revision", "this version")
   - NO hedging about the task ("I hope this...", "Let me know if...")
   - NO mentions of being an AI, assistant, or language model
   - NO references to "the prompt", "instructions", "constraints"

3. REQUIRED: Output must read as if it were written directly by the simulated author
   during their writing session, indistinguishable from surrounding authentic text.

4. FORMAT: Plain scholarly prose only. Begin immediately with the revised content.
   The first character of your response must be the first character of the scholarly text.
"""


# --- Dynamic Template Components ---
# These are loaded from configs/discourse_markers.json with fallbacks
def _get_phase_descriptions() -> Dict[str, str]:
    """Load phase descriptions from config."""
    data = get_discourse_markers()
    return data.get("phase_descriptions", {
        "Peak": "cognitive resources at maximum capacity, highest syntactic complexity tolerance",
        "Maintenance": "sustained attention with periodic micro-lapses, stable performance",
        "Fatigue": "noticeably degraded executive function, increased reliance on formulaic constructions",
        "Deep Fatigue": "severe resource depletion, strong preference for familiar phrasings, minimal working memory",
    })


def _get_discipline_conventions() -> Dict[str, str]:
    """Load discipline conventions from config."""
    data = get_discourse_markers()
    return data.get("discipline_conventions", {
        "default": "standard academic conventions with field-appropriate hedging",
        "STEM": "precise technical terminology, passive voice preference, minimal hedging",
        "humanities": "complex argumentation, active engagement with sources, nuanced qualifications",
        "social_sciences": "methodological transparency, balanced hedging, empirical grounding",
        "business": "action-oriented language, clear implications, stakeholder awareness",
    })


def _get_cognitive_load_effects() -> Dict[str, str]:
    """Load cognitive load effects from config."""
    data = get_discourse_markers()
    return data.get("cognitive_load_effects", {
        "low": "full access to sophisticated vocabulary and complex syntactic structures",
        "moderate": "occasional simplification of nested clauses, slight increase in common collocations",
        "high": "marked preference for familiar constructions, reduced subordinate clause depth",
        "severe": "heavily formulaic output, minimal syntactic variation, increased repetition",
    })


# For backwards compatibility
_PHASE_DESCRIPTIONS = property(lambda self: _get_phase_descriptions())
_DISCIPLINE_CONVENTIONS = property(lambda self: _get_discipline_conventions())
_COGNITIVE_LOAD_EFFECTS = property(lambda self: _get_cognitive_load_effects())


def _get_cognitive_load_level(glucose: float, fatigue: float) -> str:
    """Determine cognitive load category from physiological state."""
    combined = (glucose + (1.0 - fatigue)) / 2.0
    if combined > 0.75:
        return "low"
    elif combined > 0.50:
        return "moderate"
    elif combined > 0.25:
        return "high"
    return "severe"


SUPERIOR_PROMPT_TEMPLATE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║  EMBODIED AUTHORIAL SIMULATION - FORENSIC WRITING PROCESS RECONSTRUCTION     ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─ SESSION PARAMETERS ─────────────────────────────────────────────────────────┐
│ Discipline: {discipline}                                                      │
│ Session Minute: {minute}/90 | Phase: {phase}                                  │
│ Phase Characteristics: {phase_description}                                    │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ PHYSIOLOGICAL STATE ────────────────────────────────────────────────────────┐
│ Blood Glucose Level: {glucose:.2f} (cognitive fuel availability)              │
│ Visual Fatigue Index: {fatigue:.2f} (screen exposure accumulation)            │
│ Cognitive Load: {load_level} - {load_description}                             │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ RESOURCE ALLOCATION (Working Memory Budget) ────────────────────────────────┐
│ Lexical Retrieval:  {lexical:3d}% ({'█' * (lexical // 10)}{'░' * (10 - lexical // 10)})│
│ Syntactic Planning: {syntactic:3d}% ({'█' * (syntactic // 10)}{'░' * (10 - syntactic // 10)})│
│ Attentional Focus:  {attention:3d}% ({'█' * (attention // 10)}{'░' * (10 - attention // 10)})│
└──────────────────────────────────────────────────────────────────────────────┘

┌─ BIOMETRIC SIGNATURE ────────────────────────────────────────────────────────┐
│ Keystroke Latency: {latency:.1f}ms (inter-key interval, log-normal dist.)     │
│ Burst Typing Speed: {burst:.1f} tokens/sec (during fluent production)         │
│ Error Vulnerability: {error_vuln:.2f} (probability of execution failure)      │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ ENVIRONMENTAL CONTEXT ──────────────────────────────────────────────────────┐
│ Sensory Intrusion: {anchor}                                                   │
│ Intrusion Severity: {severity}                                                │
│ Impact: {intrusion_impact}                                                    │
└──────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════

YOU ARE: A tenured professor in {discipline}, deep in a revision session.
YOUR GOAL: {goal}
YOUR VOICE: {voice}

COGNITIVE DYNAMICS AT MINUTE {minute}:

The current physiological state produces these specific effects on your writing:

1. LATENCY-DRIVEN AMBIGUITY ({latency:.1f}ms baseline):
   - At this latency, working memory decay during clause production creates natural
     pronoun-antecedent distance effects
   - New conceptual clusters may show subtle referential ambiguity (this is authentic)
   - {latency_instruction}

2. BURST PRODUCTION ARTIFACTS ({burst:.1f} tokens/sec):
   - During rapid production bursts, motor execution can outpace verification
   - {burst_instruction}

3. RESOURCE-GATED COMPLEXITY:
   - Current allocation permits: {complexity_ceiling}
   - {complexity_instruction}

4. FATIGUE SIGNATURES (Phase: {phase}):
   - {fatigue_instruction}

═══════════════════════════════════════════════════════════════════════════════

DOCUMENT CONTEXT:

Paper Abstract (for register calibration):
{abstract}

Local Textual Environment:
┌─ PRECEDING CONTEXT ──────────────────────────────────────────────────────────┐
{preceding}
└──────────────────────────────────────────────────────────────────────────────┘

┌─ TARGET SPAN (to revise) ────────────────────────────────────────────────────┐
{span}
└──────────────────────────────────────────────────────────────────────────────┘

┌─ FOLLOWING CONTEXT ──────────────────────────────────────────────────────────┐
{following}
└──────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════

{leakage_guard}
"""


def _get_dynamic_instructions(minute: int, latency: float, burst: float,
                               glucose: float, phase: str) -> Dict[str, str]:
    """Generate phase-appropriate cognitive effect instructions."""

    # Latency instructions
    if latency < 200:
        latency_inst = "Low latency: maintain full syntactic complexity, minimal ambiguity"
    elif latency < 350:
        latency_inst = "Moderate latency: occasional pronoun distance effects acceptable"
    elif latency < 500:
        latency_inst = "High latency: expect increased reliance on proximal references"
    else:
        latency_inst = "Very high latency: strong preference for simple reference chains"

    # Burst instructions
    if burst > 3.0:
        burst_inst = "High burst speed: may produce 1 function-word typo per 250 words (articles, prepositions only)"
    elif burst > 2.0:
        burst_inst = "Moderate burst: rare typos possible in rapid sequences, immediately self-corrected"
    else:
        burst_inst = "Low burst speed: careful production, minimal execution errors"

    # Complexity ceiling
    if glucose > 0.7:
        complexity = "full nested subordination, technical nominalization, complex hedging"
    elif glucose > 0.5:
        complexity = "moderate subordination depth (max 2 levels), standard hedging patterns"
    elif glucose > 0.3:
        complexity = "shallow embedding only, formulaic hedging, familiar collocations"
    else:
        complexity = "minimal subordination, highly formulaic constructions, repetition acceptable"

    # Complexity instruction
    if glucose > 0.6:
        complexity_inst = "Your resources support sophisticated construction; use them"
    else:
        complexity_inst = "Conserve resources by favoring established phrasings in your field"

    # Fatigue instructions
    fatigue_map = {
        "Peak": "Full cognitive engagement. Complex argumentation expected.",
        "Maintenance": "Stable but not peak. Occasional simplification is natural.",
        "Fatigue": "Noticeable resource depletion. Prefer familiar constructions.",
        "Deep Fatigue": "Severe depletion. Rely heavily on disciplinary boilerplate.",
    }
    fatigue_inst = fatigue_map.get(phase, fatigue_map["Maintenance"])

    # Intrusion impact
    if minute > 60:
        intrusion = "Environmental awareness significantly fragments attention"
    elif minute > 30:
        intrusion = "Periodic environmental intrusions cause micro-lapses"
    else:
        intrusion = "Environmental factors minimally intrusive at this phase"

    return {
        "latency_instruction": latency_inst,
        "burst_instruction": burst_inst,
        "complexity_ceiling": complexity,
        "complexity_instruction": complexity_inst,
        "fatigue_instruction": fatigue_inst,
        "intrusion_impact": intrusion,
    }


def build_granular_edit_prompt(
    abstract: str, preceding: str, span: str, following: str,
    state: CognitiveState,
    profile: Optional[DocumentProfile],
    salt: str, weight: int = 1
) -> tuple[str, dict]:
    """Build a comprehensive embodied simulation prompt for text revision.

    Args:
        abstract: Paper abstract for register calibration
        preceding: Text before the target span
        span: The target span to revise
        following: Text after the target span
        state: Current cognitive state of the simulated author
        profile: Document/author profile (optional)
        salt: Deterministic seed for reproducibility
        weight: Intrusion intensity multiplier

    Returns:
        Tuple of (formatted prompt, metadata dict)
    """
    discipline = profile.discipline if profile else "Academic Research"
    goal = profile.primary_goal if profile else "refine prose for clarity and precision"
    voice = profile.stylistic_voice if profile else "formal academic register"

    minute = state.minute
    from .embodied import EmbodiedScholar, get_syntactic_demand
    author = EmbodiedScholar(profile.persona if profile else "anonymous_academic")
    latency = author.calculate_latency(get_syntactic_demand(span))

    # Calculate burst speed (inverse relationship with latency)
    burst = max(1.5, 4.0 - (latency / 200.0))

    intrusion = get_sensory_anchor(minute, state.biometric_salt, weight)

    # Determine phase
    if minute <= 25:
        phase = "Peak"
    elif minute <= 50:
        phase = "Maintenance"
    elif minute <= 75:
        phase = "Fatigue"
    else:
        phase = "Deep Fatigue"

    # Get dynamic instructions
    load_level = _get_cognitive_load_level(state.glucose_level, state.fatigue_index)
    instructions = _get_dynamic_instructions(
        minute, latency, burst, state.glucose_level, phase
    )

    phase_descriptions = _get_phase_descriptions()
    cognitive_load_effects = _get_cognitive_load_effects()

    prompt = SUPERIOR_PROMPT_TEMPLATE.format(
        minute=minute,
        phase=phase,
        phase_description=phase_descriptions.get(phase, "stable cognitive state"),
        glucose=state.glucose_level,
        fatigue=state.fatigue_index,
        load_level=load_level,
        load_description=cognitive_load_effects.get(load_level, "standard cognitive function"),
        lexical=int(state.allocation.lexical * 100),
        syntactic=int(state.allocation.syntactic * 100),
        attention=int(state.allocation.attention * 100),
        latency=latency,
        burst=burst,
        error_vuln=max(0.05, 0.30 - state.glucose_level * 0.3),
        anchor=intrusion['anchor'],
        severity=intrusion['severity'],
        intrusion_impact=instructions['intrusion_impact'],
        discipline=discipline,
        goal=goal,
        voice=voice,
        latency_instruction=instructions['latency_instruction'],
        burst_instruction=instructions['burst_instruction'],
        complexity_ceiling=instructions['complexity_ceiling'],
        complexity_instruction=instructions['complexity_instruction'],
        fatigue_instruction=instructions['fatigue_instruction'],
        abstract=abstract[:800] if len(abstract) > 800 else abstract,
        preceding=preceding[-400:] if len(preceding) > 400 else preceding,
        following=following[:400] if len(following) > 400 else following,
        span=span,
        leakage_guard=LEAKAGE_GUARD,
    )

    meta = {
        "minute": minute,
        "phase": phase,
        "latency": latency,
        "burst": burst,
        "load_level": load_level,
        "intrusion_anchor": intrusion['anchor'],
        "intrusion_severity": intrusion['severity'],
    }
    return prompt, meta


def build_naive_prompt(profile: Optional[DocumentProfile] = None) -> str:
    """Build a naive injection prompt with optional profile awareness.

    Naive prompts produce generic academic text without specific topical
    or contextual grounding. When a profile is provided, the output is
    calibrated to the author's discipline and style.
    """
    if profile:
        discipline_hint = f" in the field of {profile.discipline}" if profile.discipline else ""
        voice_hint = f" Use a {profile.stylistic_voice} voice." if profile.stylistic_voice else ""
        paranoia_mod = ""
        if profile.paranoia_level > 0.5:
            paranoia_mod = " Ensure the text exhibits natural variation and avoids overly uniform sentence structures."

        return f"""Write a scholarly paragraph suitable for academic publication{discipline_hint}.
The paragraph should present a general methodological or theoretical point that could appear in a research paper.{voice_hint}{paranoia_mod}

{LEAKAGE_GUARD}"""

    return f"""Write a scholarly paragraph suitable for academic publication.
The paragraph should present a general methodological or theoretical point.
Use formal academic register with appropriate hedging.

{LEAKAGE_GUARD}"""


def build_topical_prompt(domain: str, topic: str, profile: Optional[DocumentProfile] = None) -> str:
    """Build a topical injection prompt with domain and topic specificity.

    Topical prompts ground the generation in a specific academic domain
    and topic, producing more targeted content than naive prompts.
    """
    if profile:
        goals_context = ""
        if profile.secondary_goals:
            goals_context = f"\nConsider addressing aspects related to: {', '.join(profile.secondary_goals[:2])}."

        voice_instruction = f"\nAdopt a {profile.stylistic_voice} writing style." if profile.stylistic_voice else ""

        paranoia_mod = ""
        if profile.paranoia_level > 0.6:
            paranoia_mod = "\nEnsure natural lexical variation and avoid formulaic academic phrases."

        return f"""Write a scholarly paragraph about {topic} within the field of {domain}.

The content should reflect the analytical standards and terminological conventions of {profile.discipline or domain}.{goals_context}{voice_instruction}{paranoia_mod}

{LEAKAGE_GUARD}"""

    return f"""Write a scholarly paragraph about {topic} within the field of {domain}.

The content should:
- Use domain-appropriate terminology and conventions
- Present a substantive point relevant to the topic
- Maintain formal academic register with appropriate hedging
- Flow naturally as if excerpted from a research paper

{LEAKAGE_GUARD}"""


def build_contextual_prompt(
    section: str, preceding: str, following: str,
    profile: Optional[DocumentProfile] = None
) -> str:
    """Build a contextual injection prompt that bridges surrounding text.

    Contextual prompts are the most sophisticated, requiring the generated
    text to coherently connect preceding and following passages while
    maintaining authorial voice consistency.
    """
    if profile:
        discipline_context = f"This is from a {profile.discipline} paper. " if profile.discipline else ""
        voice_context = f"The author's voice is {profile.stylistic_voice}. " if profile.stylistic_voice else ""
        goal_context = f"The revision goal is to {profile.primary_goal}. " if profile.primary_goal else ""

        paranoia_instructions = ""
        if profile.paranoia_level > 0.7:
            paranoia_instructions = """

AUTHENTICITY REQUIREMENTS:
- Vary sentence length naturally (mix of short and long sentences)
- Include discipline-specific hedging patterns
- Use occasional self-corrections or qualifications that feel organic
- Avoid perfectly parallel structures"""

        return f"""You are writing the {section} section of an academic paper.
{discipline_context}{voice_context}{goal_context}

Your task is to write content that seamlessly bridges the following passages:

PRECEDING TEXT:
\"\"\"{preceding[-500:] if len(preceding) > 500 else preceding}\"\"\"

FOLLOWING TEXT:
\"\"\"{following[:500] if len(following) > 500 else following}\"\"\"

Write transitional content that:
1. Logically follows from the preceding text
2. Naturally leads into the following text
3. Maintains consistent voice and register throughout
4. Feels like a natural part of the document, not an insertion{paranoia_instructions}

{LEAKAGE_GUARD}"""

    return f"""You are writing the {section} section of an academic paper.

Your task is to write content that seamlessly bridges the following passages:

PRECEDING TEXT:
\"\"\"{preceding[-500:] if len(preceding) > 500 else preceding}\"\"\"

FOLLOWING TEXT:
\"\"\"{following[:500] if len(following) > 500 else following}\"\"\"

Write transitional content that:
1. Logically follows from the preceding text
2. Naturally leads into the following text
3. Maintains formal academic register
4. Provides appropriate conceptual bridging

{LEAKAGE_GUARD}"""


def prompt_hash(prompt: str) -> str:
    """Generate a deterministic hash for a prompt string."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
