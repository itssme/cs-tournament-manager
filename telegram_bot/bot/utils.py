def escape_string(input_str: str) -> str:
    input_str = input_str.replace("_", "\\_")
    input_str = input_str.replace("[", "\\[")
    input_str = input_str.replace("]", "\\]")
    input_str = input_str.replace("(", "\\(")
    input_str = input_str.replace(")", "\\)")
    input_str = input_str.replace("~", "\\~")
    input_str = input_str.replace("`", "\\`")
    input_str = input_str.replace(">", "\\>")
    input_str = input_str.replace("#", "\\#")
    input_str = input_str.replace("+", "\\+")
    input_str = input_str.replace("-", "\\-")
    input_str = input_str.replace("=", "\\=")
    input_str = input_str.replace("|", "\\|")
    input_str = input_str.replace("{", "\\{")
    input_str = input_str.replace("}", "\\}")
    input_str = input_str.replace(".", "\\.")
    input_str = input_str.replace("!", "\\!")
    return input_str


def str2bool(v):
    return v.lower() in ("yes", "y", "true", "t", "1")
