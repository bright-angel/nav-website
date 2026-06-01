import os
import json
import csv
import io
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    Response,
)
from models import db, Site

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me-to-a-random-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "SQLALCHEMY_DATABASE_URI", "sqlite:///nav.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")

CSV_COLUMNS = ["name", "url", "description", "category", "icon_url", "sort_order"]


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != ADMIN_USER or auth.password != ADMIN_PASS:
            return Response(
                "Access denied",
                401,
                {"WWW-Authenticate": 'Basic realm="Nav Hub Admin"'},
            )
        return f(*args, **kwargs)

    return decorated


@app.route("/")
def index():
    sites = Site.query.order_by(Site.sort_order, Site.name).all()
    categories = {}
    for site in sites:
        categories.setdefault(site.category, []).append(site)
    return render_template("index.html", categories=categories)


@app.route("/admin")
@require_auth
def admin():
    sites = Site.query.order_by(Site.category, Site.sort_order, Site.name).all()
    all_categories = sorted({s.category for s in Site.query.all()})
    return render_template(
        "admin.html", sites=sites, all_categories=all_categories
    )


@app.route("/admin/add", methods=["POST"])
@require_auth
def admin_add():
    site = Site(
        name=request.form["name"],
        url=request.form["url"],
        description=request.form.get("description", ""),
        category=request.form.get("category", "Other"),
        icon_url=request.form.get("icon_url", ""),
        sort_order=int(request.form.get("sort_order", 0)),
    )
    db.session.add(site)
    db.session.commit()
    flash("Site added.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/edit/<int:site_id>", methods=["POST"])
@require_auth
def admin_edit(site_id):
    site = db.session.get(Site, site_id)
    if not site:
        flash("Site not found.", "danger")
        return redirect(url_for("admin"))
    site.name = request.form["name"]
    site.url = request.form["url"]
    site.description = request.form.get("description", "")
    site.category = request.form.get("category", "Other")
    site.icon_url = request.form.get("icon_url", "")
    site.sort_order = int(request.form.get("sort_order", 0))
    db.session.commit()
    flash("Site updated.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:site_id>", methods=["POST"])
@require_auth
def admin_delete(site_id):
    site = db.session.get(Site, site_id)
    if site:
        db.session.delete(site)
        db.session.commit()
        flash("Site deleted.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/export")
@require_auth
def admin_export():
    sites = Site.query.order_by(Site.category, Site.sort_order, Site.name).all()
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for s in sites:
        writer.writerow({col: getattr(s, col, "") for col in CSV_COLUMNS})
    buf.seek(0)
    data = io.BytesIO()
    data.write(buf.getvalue().encode("utf-8-sig"))
    data.seek(0)
    return send_file(
        data,
        mimetype="text/csv",
        as_attachment=True,
        download_name="nav_sites_export.csv",
    )


@app.route("/admin/import", methods=["POST"])
@require_auth
def admin_import():
    mode = request.form.get("mode", "merge")
    data_text = request.form.get("data", "")
    file = request.files.get("file")

    if file and file.filename:
        data_text = file.read().decode("utf-8-sig")

    if not data_text.strip():
        flash("No data provided.", "danger")
        return redirect(url_for("admin"))

    try:
        reader = csv.DictReader(io.StringIO(data_text), restval="")
        items = list(reader)
    except Exception as e:
        flash(f"Invalid CSV: {e}", "danger")
        return redirect(url_for("admin"))

    if not items:
        flash("No rows found in CSV.", "danger")
        return redirect(url_for("admin"))

    if mode == "replace":
        db.session.query(Site).delete()

    count = 0
    for row in items:
        name = (row.get("name") or "").strip()
        url = (row.get("url") or "").strip()
        if not name or not url:
            continue
        try:
            sort_order = int(row.get("sort_order") or 0)
        except (ValueError, TypeError):
            sort_order = 0
        site = Site(
            name=name,
            url=url,
            description=(row.get("description") or "").strip(),
            category=(row.get("category") or "Other").strip() or "Other",
            icon_url=(row.get("icon_url") or "").strip(),
            sort_order=sort_order,
        )
        db.session.add(site)
        count += 1

    db.session.commit()
    flash(f"Imported {count} sites ({mode} mode).", "success")
    return redirect(url_for("admin"))


@app.route("/admin/clear", methods=["POST"])
@require_auth
def admin_clear():
    db.session.query(Site).delete()
    db.session.commit()
    flash("All sites cleared.", "success")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if Site.query.count() == 0:
            try:
                with open("seed_data.json", "r", encoding="utf-8") as f:
                    items = json.load(f)
                for item in items:
                    db.session.add(Site(
                        name=item.get("name", ""),
                        url=item.get("url", ""),
                        description=item.get("description", ""),
                        category=item.get("category", "Other"),
                        icon_url=item.get("icon_url", ""),
                        sort_order=item.get("sort_order", 0),
                    ))
                db.session.commit()
            except FileNotFoundError:
                pass
    app.run(host="0.0.0.0", port=5000)
