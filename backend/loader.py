from langchain_core.documents import Document
import json

def load_documents(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = []
    for i, item in enumerate(data):
        def safe_str(value):
            if isinstance(value, (dict, list, int, float, bool)):
                try:
                    return json.dumps(value, ensure_ascii=False)
                except:
                    return str(value)
            return str(value)

        name = safe_str(item.get("treatment", ""))
        desc = safe_str(item.get("description", ""))
        prices = item.get("price", {})
        if isinstance(prices, dict):
            price_str = "; ".join([f"{k}: {v}" for k, v in prices.items()])
        else:
            price_str = safe_str(prices)

        rec_freq = safe_str(item.get("recommended_frequency", ""))
        pre_care = ", ".join(item.get("pre_care", [])) if isinstance(item.get("pre_care", []), list) else safe_str(item.get("pre_care", ""))
        post_care = ", ".join(item.get("post_care", [])) if isinstance(item.get("post_care", []), list) else safe_str(item.get("post_care", ""))
        effects = ", ".join(item.get("effects", [])) if isinstance(item.get("effects", []), list) else safe_str(item.get("effects", ""))
        numbing = safe_str(item.get("requires_numbing_cream", ""))
        makeup_after = safe_str(item.get("makeup_after_hours", ""))
        post_proc = safe_str(item.get("post_procedure_reactions", ""))
        duration = safe_str(item.get("duration", ""))

        text = (
            f"Treatment: {name}\n"
            f"Description: {desc}\n"
            f"Price: {price_str}\n"
            f"Recommended frequency: {rec_freq}\n"
            f"Pre-care: {pre_care}\n"
            f"Post-care: {post_care}\n"
            f"Effects: {effects}\n"
            f"Requires numbing cream: {numbing}\n"
            f"Makeup after hours: {makeup_after}\n"
            f"Post-procedure reactions: {post_proc}\n"
            f"Duration: {duration} minutes\n"
        )

        docs.append(Document(page_content=text, metadata={"treatment": name}))

    return docs
