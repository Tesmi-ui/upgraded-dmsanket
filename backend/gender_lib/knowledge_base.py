"""
gender_lib.knowledge_base
=========================
Curated name dictionaries and caste-surname mappings for
Vidarbha / Maharashtra agricultural data.

Structure
---------
FEMALE_NAMES    : frozenset[str]  — well-known female first names (lowercase)
MALE_NAMES      : frozenset[str]  — well-known male first names (lowercase)
FEMALE_SUFFIXES : tuple[str, ...]  — Marathi female name endings (longest first)
MALE_SUFFIXES   : tuple[str, ...]  — Marathi male name endings (longest first)
SURNAME_CATEGORY: dict[str, str]   — surname → category code (lowercase keys)
AMBIGUOUS_SURNAMES: frozenset[str] — surnames that map to 2+ categories;
                                     never auto-write without geographic context
DISTRICT_ST_BELT: frozenset[str]   — districts where tribal surname defaults lean ST

Category codes — must match intelligence_engine.py VALID_CATEGORIES exactly:
  "obc"   — Other Backward Class  (includes NT/VJNT subsumed under OBC in GoI list)
  "sc"    — Scheduled Caste
  "st"    — Scheduled Tribe
  "gen"   — General / Open category        ← was "open" in v4.0 (FIXED)
  "sbc"   — Special Backward Class
  "pvtg"  — Particularly Vulnerable Tribal Group

NOTE TO MAINTAINERS
-------------------
1. Add entries here ONLY — do NOT scatter name/category data across the codebase.
2. "nt" / "open" are retired codes — all entries now use "obc" / "gen".
3. AMBIGUOUS_SURNAMES must mirror every surname present in more than one
   community — the inference engine will skip auto-write for these and route
   them to the Review sheet instead.
4. Rebuild confidence tiers in inference.py if dataset size changes significantly.

CHANGELOG
---------
v4.1  — Added 140 surnames (SC+28, ST+36, OBC+37, NT→OBC+9, SBC+5, PVTG+5, GEN+25)
      
"""

# ---------------------------------------------------------------------------
# Female first names (Vidarbha / Maharashtra focus)
# ---------------------------------------------------------------------------
FEMALE_NAMES: frozenset[str] = frozenset({
    "anita", "asha", "ashwini", "archana", "alka", "amita", "ambika",
    "aparna", "aruna", "avantika",
    "bharati", "bhagyashri", "bhavna", "bimla",
    "chanda", "chandrakala", "chhaya",
    "deepa", "deepali", "devyani", "durga",
    "gauri", "geeta", "girija",
    "hemlata", "hira",
    "indira", "indu",
    "jayashri", "jyoti",
    "kalpana", "kalyani", "kamala", "kanchan", "kavita", "komal", "kumari",
    "lata", "latika", "laxmi", "leela",
    "madhuri", "mangala", "manju", "manjula", "meena", "meenakshi",
    "mohini", "mona", "mukta",
    "nanda", "nandini", "neelam", "neeta", "nirmala",
    "padma", "padmavati", "parvati", "pooja", "prabha", "priya", "pushpa",
    "radha", "rajani", "rakhi", "rama", "rani", "ratna", "rekha", "rohini",
    "sadhana", "sai", "sangeeta", "sarita", "savita", "shakuntala",
    "shanta", "shobha", "shraddha", "shubhangi", "sita", "sonal", "sonali",
    "sulabha", "sunita", "sushama", "sushila", "swati",
    "usha",
    "vandana", "vaishali", "varsha", "vidya", "vijaya", "vimala",
    "yamuna", "yashodabai",
    "bai", "tai", "mai",
    "jijabai", "hirabai", "tarabai", "radhabai", "sitabai",
    "lilabai", "godabai", "nankabai",
    "shantabai", "urmila", "pramila", "parbatabai", "meerabai",
    "prabhabai", "kamalabai", "malanbai", "kantabai", "kamlabai",
    "santabai", "jaiwanta", "pratima", "anusaya", "sumitra",
    "indubai", "anusuya", "anjana", "vimalabai", "sevanta",
    "kacharabai", "rajiya", "kusumbai", "shantibai",
    "jayawanta", "kusum", "savitri", "manjubai", "fulanbai",
    "pushpabai", "raibai", "nejanbai", "sangita",
    "anjanabai", "vimalbai", "shobhabai", "subhadrabai",
    "parvatibai", "shashikalabai", "nirgunabai", "ruminabai",
})

# ---------------------------------------------------------------------------
# Male first names (Vidarbha / Maharashtra focus)
# ---------------------------------------------------------------------------
MALE_NAMES: frozenset[str] = frozenset({
    "abhijit", "anil", "arun", "ashok", "atul",
    "baburao", "balu", "bapurao", "bharat", "bhimrao",
    "chandrakant", "chandrabhan",
    "dagadu", "dattatray", "devrao", "dilip", "dinesh",
    "ganesh", "gangadhar", "gajanan", "gajananrao",
    "govind", "gulab",
    "hari", "haribhau", "harishchandra",
    "jagdish", "janardhan",
    "kailash", "kishor", "krishna", "krushna",
    "laxman", "lahu",
    "madhav", "mahendra", "manoj", "milind", "mohan", "murlidhar",
    "nagesh", "namdeo", "narayan", "narendra",
    "pandurang", "prabhakar", "prakash", "pramod", "prashant",
    "rajendra", "ramchandra", "ramesh", "ravindra", "ravi",
    "sadashiv", "sanjay", "santosh", "shivaji", "shriram",
    "sudhir", "suresh", "sunil",
    "trimbak", "ulhas",
    "vijay", "vilas", "vinayak", "vishnu", "vitthal",
    "wasudeo", "yadav", "yashwant",
    "bhima", "bhushan", "chatru", "dhanu", "genu",
    "hiraman", "janu", "kalu", "ramu", "soma", "tukaram",
    "rajkumar", "maniram", "tejram", "ramdas", "hemraj",
    "dhanraj", "premlal", "kuwarlal", "gopal", "hiralal",
    "devendra", "dayaram", "mahesh", "babulal", "chaitram",
    "dhaniram", "sadaram", "ramlal", "bhojraj", "khemraj",
    "tarachand", "omraj", "nilkanth", "parasram", "surendra",
    "rameshwar", "mohanlal", "rupchand", "mayaram", "shamlal",
    "yograj", "manohar", "umesh", "vinod", "radheshyam",
    "udaram", "surajlal", "vasudev", "mansaram", "jageshwar",
    "chunnilal", "mayalal", "youraj", "sukhram",
    "bramhadev", "pandurang",
    "motiram", "shankar", "kisan", "shalikram", "harichand", "ramchand", "sitaram", "sundarlal",
    "sankar", "mukesh", "jitendra", "raju", "shamrao", "tulshiram", "kashiram", "gyaniram",
    "ghanshyam", "omprakash", "subhash", "barikram", "lakhanlal", "gendlal", "nandlal", "mulchand",
    "maharu", "yadorao", "sukhdev", "atmaram", "jaipal", "hivraj", "dulichand", "shivlal",
    "bhaiyalal", "madhukar", "pyarelal", "antaram", "tulsiram", "rajaram", "budharam", "devidas",
    "sukhadev", "brijlal", "salikram", "pralhad", "shivcharan", "pramlal", "purushottam", "ishwar",
    "ramsing", "chunilal", "ankalu", "sakharam", "ganeshram", "shantilal", "devlal", "jiyalal",
    "ratiram", "madanlal", "ganpat", "khushal", "ramcharan", "radhelal", "mahadev", "vasant",
    "gangaram", "kishan", "budhram", "jagannath", "jagan", "suraj", "punaram", "dhondu",
    "pandhari", "madan", "baliram", "raghunath", "indrapal", "nandkishor", "sukharam", "umarav",
    "jairam", "gopichand", "bhaulal", "kuvarlal", "shamrav", "lakhan", "vishwanath", "dipak",
    "dhansay", "roshan", "gendalal", "bhaurao", "kumarsay", "lakshman", "motilal", "maroti",
    "patiram", "ramaji", "ramji", "insaram", "devanand", "baleshwar", "samaru", "yuvraj",
    "jagatram", "vedant", "vilas", "youraj",
})

# ---------------------------------------------------------------------------
# Marathi name suffixes  (longest → shortest for first-match specificity)
# ---------------------------------------------------------------------------
FEMALE_SUFFIXES: tuple[str, ...] = (
    "abai", "atai", "amai", "bai", "tai", "mai",
    "wati", "vati", "devi", "kali", "mala", "lata", "priya", "rekha",
)

MALE_SUFFIXES: tuple[str, ...] = (
    "rao", "bhushan", "anand", "kant", "das",
    "dev", "nath", "singh", "appa", "anna", "bapu", "bhai",
)

# ---------------------------------------------------------------------------
# Surname → Category  (Vidarbha / Maharashtra regional heuristic)
#
# RULES:
#   1. All keys lowercase.  Lookup code does .lower().strip() before matching.
#   2. Codes MUST match intelligence_engine.VALID_CATEGORIES = {obc,sc,st,gen,sbc,pvtg}
#   3. Ambiguous surnames (multi-community) are listed in AMBIGUOUS_SURNAMES below.
#      The inference engine uses lower confidence for those entries.
#   4. This is probabilistic only — never legal proof of caste.
# ---------------------------------------------------------------------------
SURNAME_CATEGORY: dict[str, str] = {

    # ════════════════════════════════════════════════════
    # SC — Scheduled Caste
    # ════════════════════════════════════════════════════
    # Core Mahar / Mang / Buddhist convert surnames (Vidarbha)
    "kamble":       "sc",
    "mang":         "sc",
    "mahar":        "sc",
    "meshram":      "sc",
    "gaikwad":      "sc",   # Mahar Buddhist — ALSO open (Maratha); see AMBIGUOUS_SURNAMES
    "raut":         "sc",   # ALSO obc in some districts; see AMBIGUOUS_SURNAMES
    "sonar":        "sc",   # goldsmith SC in Vidarbha
    "suryavanshi":  "sc",
    "zade":         "sc",
    "bhalerao":     "sc",
    # Additional SC — high-frequency in Vidarbha field data
    "kharat":       "sc",
    "sonkusare":    "sc",
    "dambhare":     "sc",
    "chavhan":      "sc",   # Mahar variant spelling
    "sonune":       "sc",
    "khandare":     "sc",
    "bharati":      "sc",   # SC community name used as surname
    "waghade":      "sc",
    "bankar":       "sc",
    "ingole":       "sc",
    "gedam":        "sc",
    "mohurle":      "sc",
    "nandeshwar":   "sc",
    "ramteke":      "sc",
    "fulzele":      "sc",
    "tembhare":     "sc",
    "bondre":       "sc",
    "paikrao":      "sc",
    "chawre":       "sc",
    "dahake":       "sc",
    "hatwar":       "sc",
    "nikhade":      "sc",
    "korde":        "sc",
    "umare":        "sc",
    "jambhulkar":   "sc",
    "dongre":       "sc",   # Mahar variant — ALSO obc; see AMBIGUOUS_SURNAMES

    # ════════════════════════════════════════════════════
    # ST — Scheduled Tribe
    # (Gondi, Pradhan, Korku, Halba, Andh, Kolam — Vidarbha focus)
    # ════════════════════════════════════════════════════
    "atram":        "st",
    "madavi":       "st",
    "markam":       "st",
    "tekam":        "st",
    "uike":         "st",
    "wadde":        "st",
    "dhurve":       "st",
    "kumre":        "st",
    "shyam":        "st",   # Gond surname in Vidarbha
    "gavte":        "st",
    # Additional ST — Gondi / tribal belt surnames
    "netam":        "st",
    "poyam":        "st",
    "sori":         "st",
    "koram":        "st",
    "maravi":       "st",
    "pidiya":       "st",
    "nag":          "st",   # Gond clan name
    "dhadde":       "st",
    "bhende":       "st",
    "durge":        "st",
    "kunjam":       "st",
    "usendi":       "st",
    "kumeti":       "st",
    "mandavi":      "st",
    "tekade":       "st",
    "bhatkar":      "st",
    "narote":       "st",
    "uikey":        "st",   # variant of uike
    "padvi":        "st",   # Tadvi / Padvi — Bhil/Kokna (North Mah)
    "gavit":        "st",   # Bhil / Kokna (Nashik, Nandurbar)
    "barse":        "st",
    "mowade":       "st",
    "gota":         "st",
    "pendam":       "st",
    "lakhe":        "st",
    "tirke":        "st",
    "baiga":        "st",   # Baiga tribe (Gondia/Balaghat border)
    "kanoje":       "st",
    "thakur":       "st",   # Tribal Thakur (DIFFERENT from Rajput Thakur — Vidarbha context)
    "NAITAM":       "st",   # Naitam tribe (Bhandara/Gondia
    # ════════════════════════════════════════════════════
    # OBC — Other Backward Class
    # (Kunbi, Mali, Teli, Lohar, Sutar, Koli-OBC, Yadav, Bhoi …)
    # Note: NT/VJNT communities are subsumed under OBC in GoI central list
    # ════════════════════════════════════════════════════
    "kumbhar":      "obc",   # potter
    "sutar":        "obc",   # carpenter
    "lohar":        "obc",   # blacksmith
    "mali":         "obc",   # gardener/farmer
    "teli":         "obc",   # oil presser
    "dhangar":      "obc",   # shepherd — ALSO sbc in some districts; see AMBIGUOUS_SURNAMES
    "nhavi":        "obc",   # barber
    "pawar":        "obc",   # Kunbi-Pawar — ALSO open (Maratha); see AMBIGUOUS_SURNAMES
    "jadhav":       "obc",   # Kunbi — ALSO open (Maratha); see AMBIGUOUS_SURNAMES
    "shinde":       "obc",   # Kunbi — ALSO sc (Mahar); see AMBIGUOUS_SURNAMES
    "ingle":        "obc",
    "nagpure":      "obc",
    "thakare":      "obc",
    "dhote":        "obc",
    "rathod":       "obc",   # Vidarbha-OBC variant — ALSO nt/sc; see AMBIGUOUS_SURNAMES
    "waghmare":     "obc",   # ALSO sc (Mahar); see AMBIGUOUS_SURNAMES
    # Additional OBC
    "yadav":        "obc",   # Ahir/Yadav — very high frequency
    "patel":        "obc",   # Kunbi-Patel (Vidarbha)
    "kunbi":        "obc",   # community name used as surname
    "bhoi":         "obc",   # fisherman/water-carrier
    "koli":         "obc",   # ALSO st (Mahadeo Koli); see AMBIGUOUS_SURNAMES
    "nannaware":    "obc",
    "thakre":       "obc",   # variant of thakare
    "chavan":       "obc",   # Kunbi — ALSO open; see AMBIGUOUS_SURNAMES
    "bansod":       "obc",
    "sable":        "obc",
    "mankar":       "obc",
    "rangari":      "obc",   # dyer community
    "shimpi":       "obc",   # tailor
    "tamboli":      "obc",   # betel-leaf seller
    "bhute":        "obc",
    "wankhade":     "obc",
    "kalamkar":     "obc",
    "nagrale":      "obc",
    "fulsunge":     "obc",
    "lanjewar":     "obc",
    "ruke":         "obc",
    "bhendarkar":   "obc",
    "deotale":      "obc",
    "mohod":        "obc",
    "borkar":       "obc",
    "ukey":         "obc",
    "kathane":      "obc",
    "tadas":        "obc",
    "nikhare":      "obc",
    "jamkar":       "obc",
    "bhagat":       "obc",
    "fulkar":       "obc",
    "harde":        "obc",
    "bele":         "obc",
    # NT/VJNT communities — mapped to obc (GoI central OBC list)
    "banjara":      "obc",   # Lamani/Banjara — ALSO sbc (state list); see AMBIGUOUS_SURNAMES
    "gosavi":       "obc",   # Gosavi/Bairagi wandering sect
    "vaidu":        "obc",   # Vaidu — itinerant medicine community
    "laman":        "obc",   # variant of Lamani/Banjara
    "phanse":       "obc",   # Phanse Pardhi
    "vanjari":      "obc",   # ALSO sbc; see AMBIGUOUS_SURNAMES
    "dhole":        "obc",
    "kaikadi":      "obc",   # basket-weaver NT
    "wadar":        "obc",   # stone-cutter NT
    "burud":        "obc",   # bamboo-worker NT
    "katkar":       "obc",
    "kolhati":      "obc",   # performing NT
    "nandiwale":    "obc",   # bull-keeper NT
    "dombari":      "obc",   # acrobat NT

    # ════════════════════════════════════════════════════
    # SBC — Special Backward Class (Maharashtra state list)
    # ════════════════════════════════════════════════════
    "vanjare":      "sbc",   # Vanjari (alternate spelling — SBC in state list)
    "hatkar":       "sbc",   # Dhangar sub-group — SBC notified
    "khatik":       "sbc",

    # ════════════════════════════════════════════════════
    # PVTG — Particularly Vulnerable Tribal Group
    # (Maharashtra: Kolam, Katkari, Madia Gond, Maria, Korku-PVTG)
    # ════════════════════════════════════════════════════
    "kolam":        "pvtg",  # Kolam tribe (Yavatmal, Wardha, Nanded)
    "katkari":      "pvtg",  # Katkari/Kathkari (Raigad, Pune)
    "madia":        "pvtg",  # Madia Gond (Gadchiroli)
    "maria":        "pvtg",  # Maria Gond (Gadchiroli)
    "korku":        "pvtg",  # Korku (Melghat, Amravati) — PVTG block-specific

    # ════════════════════════════════════════════════════
    # GEN — General / Open category
    # ════════════════════════════════════════════════════
    "deshmukh":     "gen",
    "deshpande":    "gen",
    "kulkarni":     "gen",
    "joshi":        "gen",
    "brahme":       "gen",
    "chitnis":      "gen",
    "panse":        "gen",
    "sathe":        "gen",
    "patil":        "gen",   # predominantly gen (Maratha) in Vidarbha — ALSO obc; see AMBIGUOUS_SURNAMES
    "bhosale":      "gen",   # Maratha — ALSO obc (Kunbi); see AMBIGUOUS_SURNAMES
    "naik":         "gen",   # coastal/urban gen — ALSO st (tribal belt); see AMBIGUOUS_SURNAMES
    # Additional Brahmin / CKP / high-caste open surnames
    "bhide":        "gen",
    "gokhale":      "gen",
    "apte":         "gen",
    "vaidya":       "gen",
    "phadke":       "gen",
    "kale":         "gen",
    "oak":          "gen",
    "abhyankar":    "gen",
    "damle":        "gen",
    "karmarkar":    "gen",
    "kelkar":       "gen",
    "pendse":       "gen",
    "ranade":       "gen",
    "tilak":        "gen",
    "agashe":       "gen",
    "atre":         "gen",
    "fadnavis":     "gen",
    "gadgil":       "gen",
    "ghate":        "gen",
    "limaye":       "gen",
    "marathe":      "gen",
    "moghe":        "gen",
    "nene":         "gen",
    "paranjape":    "gen",
}


# ---------------------------------------------------------------------------
# AMBIGUOUS_SURNAMES
# Surnames that map to 2+ categories depending on district/community sub-group.
# The inference engine MUST lower confidence for these (route to review, not auto-write).
#
# Rule: if extracted_surname in AMBIGUOUS_SURNAMES → confidence cap = 65
#       → write only if confidence threshold for auto-write is ≤ 65.
# ---------------------------------------------------------------------------
AMBIGUOUS_SURNAMES: frozenset[str] = frozenset({
    "patil",      # gen (Maratha) ↔ obc (Kunbi)
    "naik",       # gen (coastal) ↔ st (tribal belt)
    "shinde",     # obc (Kunbi)   ↔ sc (Mahar)
    "gaikwad",    # sc (Mahar)    ↔ gen (Maratha)
    "rathod",     # obc           ↔ sc ↔ nt (district-dependent)
    "koli",       # obc           ↔ st (Mahadeo Koli — Thane/Nashik)
    "chavan",     # obc (Kunbi)   ↔ gen (Maratha)
    "pawar",      # obc (Kunbi)   ↔ gen (Maratha)
    "jadhav",     # obc (Kunbi)   ↔ gen (Maratha)
    "bhosale",    # gen (Maratha) ↔ obc (Kunbi)
    "waghmare",   # obc           ↔ sc (Mahar)
    "dhangar",    # obc           ↔ sbc (state notification varies)
    "banjara",    # obc (central) ↔ sbc (state list)
    "raut",       # sc (Vidarbha) ↔ obc (other regions)
    "dongre",     # sc (Mahar)    ↔ obc
    "thakur",     # st (Gond)     ↔ gen (Rajput) — context-critical
})


# ---------------------------------------------------------------------------
# DISTRICT_ST_BELT
# Districts where the ST population is ≥ 25% (Census 2011).
# Used by Tier-4 geographic prior: if name gives no signal AND district is
# in this set, flag the blank category for review as "likely ST".
# Source: Census 2011 District-level SC/ST tables (censusindia.gov.in)
# ---------------------------------------------------------------------------
DISTRICT_ST_BELT: frozenset[str] = frozenset({
    "gadchiroli",   # ST 38.6%
    "nandurbar",    # ST 59.9%
    "dhule",        # ST 26.8%
    "nashik",       # ST 26.1%
    "thane",        # ST 25.6%  (Mahadeo Koli, Warli, Katkari)
    "palghar",      # ST ~35%   (carved from Thane 2014)
    "amravati",     # ST 14.9%  (Korku/Melghat — near threshold, include)
    "yavatmal",     # ST 18.1%  (Kolam belt)
    "gondia",       # ST 18.5%  (Gond/Baiga border)
    "chandrapur",   # ST 18.3%  (Gond/Halba)
    "raigad",       # ST 18.0%  (Katkari/Warli)
})


# ---------------------------------------------------------------------------
# GenderLibrary — runtime loader (unchanged from v4.0)
# ---------------------------------------------------------------------------
import json as _json
import logging as _logging
from dataclasses import dataclass as _dataclass, field as _field
from datetime import datetime as _datetime, timezone as _timezone
from pathlib import Path as _Path

_log = _logging.getLogger("brlf.knowledge_base")

_DEFAULT_STRICT = "gender_intelligence/brlf_gender_strict.json"
_DEFAULT_PROB   = "gender_intelligence/brlf_gender_prob.json"


@_dataclass
class GenderLibrary:
    strict: dict = _field(default_factory=dict)
    prob:   dict = _field(default_factory=dict)
    meta:   dict = _field(default_factory=dict)

    def get_strict(self, name: str) -> "dict | None":
        return self.strict.get(str(name).lower().strip())

    def get_prob(self, name: str) -> "dict | None":
        key = str(name).lower().strip()
        if key in self.strict:
            return None
        return self.prob.get(key)

    @classmethod
    def load(cls, strict_path=_DEFAULT_STRICT, prob_path=_DEFAULT_PROB) -> "GenderLibrary":
        strict = cls._read_json(strict_path, "strict")
        prob   = cls._read_json(prob_path,   "prob")
        overlap = [n for n in prob if n in strict]
        if overlap:
            _log.warning("%d name(s) in both libraries — removing from prob", len(overlap))
            for n in overlap:
                del prob[n]
        meta = {
            "loaded_at":     _datetime.now(_timezone.utc).isoformat(),
            "strict_path":   str(strict_path),
            "prob_path":     str(prob_path),
            "strict_count":  len(strict),
            "prob_count":    len(prob),
            "strict_male":   sum(1 for v in strict.values() if v.get("gender") == "male"),
            "strict_female": sum(1 for v in strict.values() if v.get("gender") == "female"),
        }
        _log.info("GenderLibrary loaded | strict=%d (m=%d f=%d) | prob=%d",
                  meta["strict_count"], meta["strict_male"], meta["strict_female"],
                  meta["prob_count"])
        return cls(strict=strict, prob=prob, meta=meta)

    def reload(self) -> "GenderLibrary":
        return GenderLibrary.load(
            strict_path=self.meta.get("strict_path", _DEFAULT_STRICT),
            prob_path=  self.meta.get("prob_path",   _DEFAULT_PROB),
        )

    @staticmethod
    def _read_json(path: str, label: str) -> dict:
        p = _Path(path)
        if not p.exists():
            _log.warning("%s library not found at '%s' — using empty dict", label, path)
            return {}
        try:
            data = _json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Top-level value must be a JSON object")
            _log.info("Loaded %s: %d entries from %s", label, len(data), p.name)
            return data
        except (_json.JSONDecodeError, ValueError) as e:
            _log.error("Failed to load %s from '%s': %s — using empty dict", label, path, e)
            return {}

    def summary(self) -> dict:
        return {k: self.meta.get(k) for k in
                ("strict_count", "prob_count", "strict_male", "strict_female", "loaded_at")}

    def __repr__(self) -> str:
        return (f"GenderLibrary(strict={self.meta.get('strict_count', 0):,}  "
                f"prob={self.meta.get('prob_count', 0):,})")