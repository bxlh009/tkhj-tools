import json

exam = json.load(open(r"D:\codex\content-engine\prompts\persona_exam.json", encoding="utf-8-sig"))
exam["published_works"] = ["published one book on test preparation methodology", "multiple articles read by 100,000+ educators"]
exam["speaking_engagements"] = ["presented at multiple education conferences in Asia"]
exam["credentials"]["awards"] = ["recognized by a major education organization for teaching excellence"]
exam["credentials"]["phd"] = "PhD in Applied Linguistics (graduated 2012)"

with open(r"D:\codex\content-engine\prompts\persona_exam.json", "w", encoding="utf-8") as f:
    json.dump(exam, f, ensure_ascii=False, indent=2)
print("Evan done")

ai = json.load(open(r"D:\codex\content-engine\prompts\persona_ai.json", encoding="utf-8-sig"))
pubs = ai.get("technical_background", {}).get("publications", [])
ai["technical_background"]["publications"] = [p for p in pubs if not any(x in p for x in ["12+", "14", "3 patents", "2800"])]
if not ai["technical_background"]["publications"]:
    ai["technical_background"]["publications"] = ["multiple peer-reviewed papers on NLP evaluation"]

ai["credentials"]["awards"] = ["received recognition from a major AI conference", "listed among innovators under 35"]

with open(r"D:\codex\content-engine\prompts\persona_ai.json", "w", encoding="utf-8") as f:
    json.dump(ai, f, ensure_ascii=False, indent=2)
print("AI done")