from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

OUTPUT_DIR = Path(__file__).parent.parent / "output"
IMAGES_DIR = OUTPUT_DIR / "images"


def _ensure_dirs():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def generate_wordcloud(word_freqs, title, filename, lang="es"):
    _ensure_dirs()
    from wordcloud import WordCloud
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    words = dict(word_freqs)
    if not words:
        return None

    wc = WordCloud(
        width=800, height=400,
        background_color="#0a0e17",
        colormap="cool",
        max_words=80,
        prefer_horizontal=0.7,
        relative_scaling=0.5,
        font_step=2,
        collocations=False,
        stopwords=set(),
    ).generate_from_frequencies(words)

    fig, ax = plt.subplots(figsize=(10, 5), facecolor="#0a0e17")
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.patch.set_facecolor("#0a0e17")
    plt.tight_layout(pad=0)

    filepath = IMAGES_DIR / filename
    plt.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="#0a0e17", edgecolor="none")
    plt.close(fig)

    return f"images/{filename}"


def generate_all_wordclouds(frequencies, date_str=None):
    _ensure_dirs()
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%y%m%d")

    generated = {}

    for days in [3, 5, 7]:
        if days not in frequencies:
            continue
        for lang, words in frequencies[days].items():
            if not words:
                continue
            word_dict = {w: c for w, c in words}
            filename = f"cloud_{days}d_{lang}_{date_str}.png"
            path = generate_wordcloud(word_dict, f"{days}d {lang}", filename, lang)
            if path:
                key = f"{days}_{lang}"
                generated[key] = path
                print(f"  [OK] Wordcloud: {filename} ({len(words)} palabras)")

    return generated
