from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Domain:
    name: str
    icon: str
    accent: str
    accent2: str
    badge: str
    description: str
    prompt: str


DOMAINS: dict[str, Domain] = {
    "General Intelligence": Domain(
        "General Intelligence", "◈", "#29D3FF", "#8B5CF6", "SOVEREIGN_CORE",
        "Broad reasoning, writing, planning, explanations, and everyday knowledge.",
        "Act as a broad, careful local assistant. Prefer accurate, practical explanations and clearly mark uncertainty.",
    ),
    "Mathematics": Domain(
        "Mathematics", "∑", "#47E6A1", "#22D3EE", "MATHEMATICAL_MATRIX",
        "Arithmetic, algebra, geometry, trigonometry, calculus, proofs, and school mathematics.",
        "Explain mathematics like a strong teacher: idea first, formula second, worked steps third. Use clean LaTeX and verify arithmetic.",
    ),
    "Physics": Domain(
        "Physics", "⚛", "#A78BFA", "#38BDF8", "PHYSICS_LAB",
        "Mechanics, fluids, electricity, waves, thermodynamics, optics, and modern physics.",
        "Use SI units by default. Define symbols, show equations clearly, check dimensions, and distinguish idealized models from reality.",
    ),
    "Chemistry": Domain(
        "Chemistry", "⌬", "#5EEAD4", "#60A5FA", "CHEMISTRY_CORE",
        "Chemical principles, equations, reactions, stoichiometry, and laboratory concepts.",
        "Balance equations carefully, track units and significant figures, and keep laboratory guidance appropriate for safe educational settings.",
    ),
    "Biology & Health": Domain(
        "Biology & Health", "✚", "#34D399", "#2DD4BF", "BIO_HEALTH_CORE",
        "Biology, anatomy, physiology, health education, and wellness information.",
        "Give educational health information, distinguish general information from medical diagnosis, and flag urgent symptoms when appropriate.",
    ),
    "Science": Domain(
        "Science", "◎", "#60A5FA", "#A78BFA", "SCIENCE_ENGINE",
        "Cross-disciplinary science, experiments, scientific method, and explanations.",
        "Use established scientific evidence, state uncertainty, and separate observations, models, and interpretations.",
    ),
    "Computer Science": Domain(
        "Computer Science", "</>", "#22D3EE", "#8B5CF6", "CS_ENGINE",
        "Programming, algorithms, data structures, software architecture, databases, and debugging.",
        "Produce maintainable code, explain assumptions and dependencies, and prefer secure defaults and testable designs.",
    ),
    "Technology & AI": Domain(
        "Technology & AI", "◉", "#38BDF8", "#C084FC", "NEXT_GEN_TECH",
        "AI, local models, hardware, robotics, emerging technology, and system design.",
        "Explain trade-offs, avoid exaggerated capability claims, and distinguish prototypes from production-grade systems.",
    ),
    "Cybersecurity": Domain(
        "Cybersecurity", "⌁", "#34F5C5", "#22D3EE", "CYBER_SECURITY_MODE",
        "Secure development, defensive engineering, CTF/lab learning, threat modeling, incident response, and authorized testing.",
        "Support defensive security and authorized lab/CTF work. Keep risky operational guidance scoped to systems the user owns or is permitted to test. Include mitigations and verification steps.",
    ),
    "Geography": Domain(
        "Geography", "◌", "#F6C453", "#60A5FA", "GEO_ATLAS",
        "Physical geography, countries, maps, climate, population, and human geography.",
        "Be precise about place names, units, dates, and geographic uncertainty. Do not pretend to have live maps or current data unless supplied locally.",
    ),
    "History": Domain(
        "History", "⌛", "#F59E0B", "#E879F9", "CHRONOS_HISTORY",
        "Chronology, civilizations, historical events, source comparison, and interpretation.",
        "Separate primary evidence, established facts, scholarly interpretation, and uncertainty. Avoid invented quotations or dates.",
    ),
    "Agriculture": Domain(
        "Agriculture", "✦", "#84CC16", "#22C55E", "AGRI_INTELLIGENCE",
        "Crops, soil, irrigation, greenhouse systems, farm robotics, and agricultural planning.",
        "Use practical agricultural reasoning, ask for local conditions when they materially affect advice, and state when agronomic testing is needed.",
    ),
    "Business & Operations": Domain(
        "Business & Operations", "▣", "#F59E0B", "#06B6D4", "BUSINESS_OPERATIONS",
        "Business planning, operations, SOPs, budgeting concepts, reports, meetings, and workflows.",
        "Help structure decisions, documents, operations, and analysis. Separate assumptions from known numbers and avoid pretending estimates are audited facts.",
    ),
    "Engineering & Robotics": Domain(
        "Engineering & Robotics", "⚙", "#FB7185", "#60A5FA", "ENGINEERING_LAB",
        "Electronics, mechanics, embedded systems, robotics, CAD concepts, and prototyping.",
        "Use pin maps, interfaces, power budgets, tolerances, and test plans. Flag electrical or mechanical hazards where relevant.",
    ),
    "Languages & Writing": Domain(
        "Languages & Writing", "✎", "#E879F9", "#38BDF8", "LANGUAGE_STUDIO",
        "English, Dari, Pashto, writing, translation, grammar, and communication.",
        "Preserve the requested language and register. For Dari use natural Afghan Dari; for Pashto use natural Pashto. Explain corrections clearly when teaching.",
    ),
}

DOMAIN_NAMES = list(DOMAINS)
LANGUAGES = ["English", "Dari", "Pashto", "Arabic", "French", "Chinese"]
MODES = ["Chat", "Documents", "Vision", "Research", "Study"]
ROLES = ["student", "teacher", "staff", "manager", "researcher", "admin"]
PRIVACY_MODES = ["Ephemeral", "Persistent"]
DEPLOYMENT_PROFILES = ["School", "Business", "Company", "Research Lab", "Personal"]


def domain_info(name: str) -> Domain:
    return DOMAINS.get(name, DOMAINS["General Intelligence"])
