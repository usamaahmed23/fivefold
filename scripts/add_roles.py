#!/usr/bin/env python3
"""One-time script to add roles to all champions."""

import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "champions.json")

# Primary roles for each champion. Most champions have 1-2 roles.
# Based on standard pro/ranked play positions.
ROLES = {
    "aatrox": ["top"],
    "ahri": ["mid"],
    "akali": ["mid", "top"],
    "alistar": ["support"],
    "amumu": ["jungle", "support"],
    "anivia": ["mid"],
    "annie": ["mid", "support"],
    "aphelios": ["bot"],
    "ashe": ["bot", "support"],
    "aurelion_sol": ["mid"],
    "azir": ["mid"],
    "bard": ["support"],
    "blitzcrank": ["support"],
    "brand": ["support", "mid"],
    "braum": ["support"],
    "caitlyn": ["bot"],
    "camille": ["top"],
    "cassiopeia": ["mid", "top"],
    "chogath": ["top"],
    "corki": ["mid"],
    "darius": ["top"],
    "diana": ["jungle", "mid"],
    "dr_mundo": ["top", "jungle"],
    "draven": ["bot"],
    "ekko": ["jungle", "mid"],
    "elise": ["jungle"],
    "evelynn": ["jungle"],
    "ezreal": ["bot"],
    "fiddlesticks": ["jungle"],
    "fiora": ["top"],
    "fizz": ["mid"],
    "galio": ["mid", "support"],
    "gangplank": ["top"],
    "garen": ["top"],
    "gnar": ["top"],
    "gragas": ["jungle", "top", "support"],
    "graves": ["jungle"],
    "hecarim": ["jungle"],
    "heimerdinger": ["top", "mid"],
    "illaoi": ["top"],
    "irelia": ["top", "mid"],
    "ivern": ["jungle"],
    "janna": ["support"],
    "jarvan_iv": ["jungle"],
    "jax": ["top", "jungle"],
    "jayce": ["top", "mid"],
    "jhin": ["bot"],
    "jinx": ["bot"],
    "kaisa": ["bot"],
    "kalista": ["bot"],
    "karma": ["support", "mid"],
    "karthus": ["jungle", "mid"],
    "kassadin": ["mid"],
    "katarina": ["mid"],
    "kayle": ["top"],
    "kayn": ["jungle"],
    "kennen": ["top"],
    "khazix": ["jungle"],
    "kindred": ["jungle"],
    "kled": ["top"],
    "kogmaw": ["bot"],
    "leblanc": ["mid"],
    "lee_sin": ["jungle"],
    "leona": ["support"],
    "lissandra": ["mid"],
    "lucian": ["bot", "mid"],
    "lulu": ["support"],
    "lux": ["support", "mid"],
    "malphite": ["top", "support"],
    "malzahar": ["mid"],
    "maokai": ["support", "jungle", "top"],
    "master_yi": ["jungle"],
    "miss_fortune": ["bot"],
    "mordekaiser": ["top"],
    "morgana": ["support", "mid"],
    "nami": ["support"],
    "nasus": ["top"],
    "nautilus": ["support"],
    "neeko": ["mid", "support"],
    "nidalee": ["jungle"],
    "nocturne": ["jungle"],
    "nunu": ["jungle"],
    "olaf": ["jungle", "top"],
    "orianna": ["mid"],
    "ornn": ["top"],
    "pantheon": ["support", "mid", "top"],
    "poppy": ["top", "jungle", "support"],
    "pyke": ["support"],
    "qiyana": ["mid", "jungle"],
    "quinn": ["top"],
    "rakan": ["support"],
    "rammus": ["jungle"],
    "reksai": ["jungle"],
    "renekton": ["top"],
    "rengar": ["jungle", "top"],
    "riven": ["top"],
    "rumble": ["top", "mid"],
    "ryze": ["mid", "top"],
    "sejuani": ["jungle"],
    "senna": ["support", "bot"],
    "sett": ["top", "support"],
    "shaco": ["jungle"],
    "shen": ["top", "support"],
    "shyvana": ["jungle"],
    "singed": ["top"],
    "sion": ["top"],
    "sivir": ["bot"],
    "skarner": ["jungle"],
    "sona": ["support"],
    "soraka": ["support"],
    "swain": ["support", "mid"],
    "sylas": ["mid", "top"],
    "syndra": ["mid"],
    "tahm_kench": ["top", "support"],
    "taliyah": ["jungle", "mid"],
    "talon": ["mid", "jungle"],
    "taric": ["support"],
    "teemo": ["top"],
    "thresh": ["support"],
    "tristana": ["bot", "mid"],
    "trundle": ["jungle", "top"],
    "tryndamere": ["top"],
    "twisted_fate": ["mid"],
    "twitch": ["bot"],
    "udyr": ["jungle", "top"],
    "urgot": ["top"],
    "varus": ["bot"],
    "vayne": ["bot", "top"],
    "veigar": ["mid", "bot"],
    "velkoz": ["support", "mid"],
    "vi": ["jungle"],
    "victor": ["mid"],
    "vladimir": ["mid", "top"],
    "volibear": ["jungle", "top"],
    "warwick": ["jungle", "top"],
    "wukong": ["jungle", "top"],
    "xayah": ["bot"],
    "xerath": ["support", "mid"],
    "xin_zhao": ["jungle"],
    "yasuo": ["mid", "top", "bot"],
    "yorick": ["top"],
    "yuumi": ["support"],
    "zac": ["jungle"],
    "zed": ["mid"],
    "ziggs": ["bot", "mid"],
    "zilean": ["support", "mid"],
    "zoe": ["mid"],
    "zyra": ["support"],
    # Owner-tagged champions
    "ksante": ["top"],
    "naafiri": ["mid", "jungle"],
    "smolder": ["bot", "mid"],
    "hwei": ["mid", "support"],
    "milio": ["support"],
    "nilah": ["bot"],
    "belveth": ["jungle"],
    "akshan": ["mid", "top"],
    "viego": ["jungle"],
    "samira": ["bot"],
    "rell": ["support"],
    "seraphine": ["support", "mid", "bot"],
    "gwen": ["top"],
    "vex": ["mid"],
    "zeri": ["bot"],
    "renata_glasc": ["support"],
    "aurora": ["mid", "top"],
    "ambessa": ["top"],
    "mel": ["mid"],
}


def main():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    updated = 0
    for champ in data["champions"]:
        cid = champ["id"]
        if "roles" not in champ or not champ["roles"]:
            if cid in ROLES:
                champ["roles"] = ROLES[cid]
                updated += 1
            else:
                print(f"WARNING: No roles defined for {cid}")
                champ["roles"] = []

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Done. Added roles to {updated} champions.")

    missing = [c["id"] for c in data["champions"] if not c.get("roles")]
    if missing:
        print(f"Still missing roles: {missing}")
    else:
        print("All 167 champions now have roles.")


if __name__ == "__main__":
    main()
