import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

OUTPUT_DIR = "static_site"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # Render landing page as site index for GitHub Pages
    template = env.get_template("landing.html")
    html = template.render(api_token="")
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {OUTPUT_DIR}/index.html")

if __name__ == "__main__":
    main()