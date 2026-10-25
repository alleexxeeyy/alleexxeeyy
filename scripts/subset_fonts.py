import sys
from pathlib import Path
from fontTools import subset


FONTS = Path(__file__).resolve().parent / "fonts"
WEIGHTS = {"Regular": "jbmono-400.woff2", "ExtraBold": "jbmono-800.woff2"}
GLYPHS = "".join(chr(c) for c in range(0x20, 0x7F)) + "●○▌█░▒▓►▸→←↑↓·—…│─┌┐└┘├┤✓✗×"


def main(src_dir):
    FONTS.mkdir(exist_ok=True)
    for weight, out in WEIGHTS.items():
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = []
        options.name_IDs = []
        options.notdef_outline = True
        options.hinting = False
        font = subset.load_font(str(Path(src_dir) / f"JetBrainsMono-{weight}.ttf"), options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(text=GLYPHS)
        subsetter.subset(font)
        missing = [ch for ch in GLYPHS if ord(ch) not in font.getBestCmap()]
        if missing:
            sys.exit(f"{weight}: в шрифте нет глифов {''.join(missing)}")
        subset.save_font(font, str(FONTS / out), options)
        print(f"{out}: {(FONTS / out).stat().st_size} байт")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 scripts/subset_fonts.py <папка с JetBrainsMono-*.ttf>")
    main(sys.argv[1])
