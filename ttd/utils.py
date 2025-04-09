import pprint

def safe_pretty_print(obj, max_len=50):
    def truncate(v):
        if isinstance(v, str) and len(v) > max_len:
            return v[:max_len] + '...'
        elif isinstance(v, dict):
            return {k: truncate(val) for k, val in v.items()}
        elif isinstance(v, list):
            return [truncate(item) for item in v]
        return v
    truncated_obj = truncate(obj)
    return pprint.pformat(truncated_obj, indent=2, width=120)