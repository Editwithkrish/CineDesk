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

    # Render login page to directory-style path: /login/
    login_out_dir = os.path.join(OUTPUT_DIR, "login")
    os.makedirs(login_out_dir, exist_ok=True)
    login_tpl = env.get_template("login.html")
    login_html = login_tpl.render()
    with open(os.path.join(login_out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(login_html)
    print(f"Wrote {login_out_dir}/index.html")

    # Render register page to: /register/
    register_out_dir = os.path.join(OUTPUT_DIR, "register")
    os.makedirs(register_out_dir, exist_ok=True)
    register_tpl = env.get_template("register.html")
    register_html = register_tpl.render()
    with open(os.path.join(register_out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(register_html)
    print(f"Wrote {register_out_dir}/index.html")

    # Render dashboard page to: /dashboard/
    dashboard_out_dir = os.path.join(OUTPUT_DIR, "dashboard")
    os.makedirs(dashboard_out_dir, exist_ok=True)
    dashboard_tpl = env.get_template("dashboard.html")
    dashboard_html = dashboard_tpl.render()
    with open(os.path.join(dashboard_out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(dashboard_html)
    print(f"Wrote {dashboard_out_dir}/index.html")

    # Netlify SPA-style fallback: route any path to index.html
    with open(os.path.join(OUTPUT_DIR, "_redirects"), "w", encoding="utf-8") as f:
        f.write("/* /index.html 200\n")
    print(f"Wrote {OUTPUT_DIR}/_redirects")

if __name__ == "__main__":
    main()