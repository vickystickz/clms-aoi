def convert_colors(colors: dict) -> dict:
    result = {}

    for code, (rgb, name) in colors.items():
        r, g, b = rgb

        result[name] = (
            r / 255,
            g / 255,
            b / 255,
        )

    return result