import os, secrets
from pathlib import Path
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent
UPLOADS = ROOT / "uploads"
UPLOADS.mkdir(exist_ok=True)
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-before-deploy")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", f"sqlite:///{(ROOT/'portfolio.db').as_posix()}")
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
db = SQLAlchemy(app)
ALLOWED = {"png","jpg","jpeg","webp","gif","svg","pdf","mp3","wav","ogg","mp4","webm","zip","txt","md","html","css","js","py","apk","docx","pptx","xlsx"}
DEFAULT_CATEGORIES = ["Projects","E-books","Websites","Apps","Photography","Videos","Music & Audio","Trading","Other Creations"]

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)

class Creation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    cover_filename = db.Column(db.String(255))
    file_filename = db.Column(db.String(255))
    external_url = db.Column(db.String(500))
    visibility = db.Column(db.String(20), default="public", nullable=False)
    published = db.Column(db.Boolean, default=True, nullable=False)
    content_type = db.Column(db.String(30), default="project")
    access_mode = db.Column(db.String(20), default="free")
    price = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.relationship("Category", backref="creations")

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    kind = db.Column(db.String(30), default="contact")
    budget = db.Column(db.String(80), default="")
    deadline = db.Column(db.String(80), default="")
    status = db.Column(db.String(30), default="new")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def slugify(value):
    result = "".join(c.lower() if c.isalnum() else "-" for c in value.strip())
    while "--" in result: result = result.replace("--", "-")
    return result.strip("-")[:200] or secrets.token_hex(4)

def unique_slug(model, name, current_id=None):
    base, candidate, n = slugify(name), slugify(name), 2
    while True:
        q = model.query.filter_by(slug=candidate)
        if current_id: q = q.filter(model.id != current_id)
        if not q.first(): return candidate
        candidate, n = f"{base}-{n}", n+1

def save_file(storage, prefix):
    if not storage or not storage.filename: return None
    safe = secure_filename(storage.filename)
    if "." not in safe or safe.rsplit(".",1)[1].lower() not in ALLOWED:
        raise ValueError("This file type is not allowed.")
    name = f"{prefix}_{secrets.token_hex(10)}.{safe.rsplit('.',1)[1].lower()}"
    storage.save(UPLOADS / name)
    return name

def admin_required(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        if not session.get("admin_id"): return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return inner

@app.context_processor
def globals_for_templates():
    return {"site_name":"ROHIT RAJ","current_year":datetime.now().year,"logged_in":bool(session.get("admin_id"))}

@app.route("/")
def index():
    selected = request.args.get("category","")
    q = Creation.query.filter_by(visibility="public", published=True)
    if selected: q = q.join(Category).filter(Category.slug == selected)
    return render_template("index.html", creations=q.order_by(Creation.created_at.desc()).all(),
        categories=Category.query.order_by(Category.name).all(), selected_category=selected)

@app.route("/creation/<slug>")
def detail(slug):
    item = Creation.query.filter_by(slug=slug, visibility="public", published=True).first_or_404()
    if item.access_mode == "paid": return render_template("locked.html", item=item), 402
    return render_template("creation.html", item=item)

@app.route("/uploads/<path:filename>")
def uploads(filename):
    item = Creation.query.filter(
        (Creation.cover_filename == filename) | (Creation.file_filename == filename),
        Creation.visibility == "public", Creation.published.is_(True), Creation.access_mode == "free"
    ).first()
    if not item: abort(404)
    return send_from_directory(str(UPLOADS), filename)

@app.route("/contact", methods=["POST"])
def contact():
    name, email, message = (request.form.get(k,"").strip() for k in ("name","email","message"))
    if not name or not email or not message:
        flash("Please fill in your name, email and message.", "error")
        return redirect(url_for("index")+"#contact")
    db.session.add(ContactMessage(name=name[:120], email=email[:180], message=message[:10000],
        kind=request.form.get("kind","contact") if request.form.get("kind") in {"contact","hire"} else "contact",
        budget=request.form.get("budget","")[:80], deadline=request.form.get("deadline","")[:80]))
    db.session.commit()
    flash("Message received. Thanks for reaching out!", "success")
    return redirect(url_for("index")+"#contact")

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        admin = Admin.query.filter_by(username=request.form.get("username","").strip()).first()
        if admin and check_password_hash(admin.password_hash, request.form.get("password","")):
            session.clear(); session["admin_id"] = admin.id; session["admin_username"] = admin.username
            return redirect(request.args.get("next") or url_for("admin_dashboard"))
        flash("Incorrect username or password.", "error")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear(); return redirect(url_for("index"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin/dashboard.html",
        total=Creation.query.count(),
        public=Creation.query.filter_by(visibility="public",published=True).count(),
        private=Creation.query.filter_by(visibility="private").count(),
        new_messages=ContactMessage.query.filter_by(status="new").count(),
        messages=ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all())

@app.route("/admin/creations")
@admin_required
def admin_creations():
    return render_template("admin/creations.html", creations=Creation.query.order_by(Creation.created_at.desc()).all())

@app.route("/admin/creations/new", methods=["GET","POST"])
@app.route("/admin/creations/<int:item_id>/edit", methods=["GET","POST"])
@admin_required
def edit_creation(item_id=None):
    item = db.session.get(Creation,item_id) if item_id else None
    if item_id and not item: abort(404)
    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        title = request.form.get("title","").strip()
        new_cat = request.form.get("new_category","").strip()
        cat_id = request.form.get("category_id",type=int)
        if not title:
            flash("Title is required.","error")
            return render_template("admin/creation_form.html",item=item,categories=categories)
        if new_cat:
            cat = Category.query.filter_by(name=new_cat).first()
            if not cat:
                cat = Category(name=new_cat[:80],slug=unique_slug(Category,new_cat)); db.session.add(cat); db.session.flush()
            cat_id = cat.id
        cat = db.session.get(Category,cat_id) if cat_id else None
        if not cat:
            flash("Select a category or enter a new one.","error")
            return render_template("admin/creation_form.html",item=item,categories=categories)
        try:
            cover = save_file(request.files.get("cover"),"cover")
            asset = save_file(request.files.get("asset"),"asset")
        except ValueError as e:
            flash(str(e),"error")
            return render_template("admin/creation_form.html",item=item,categories=categories)
        if not item:
            item = Creation(title=title,slug=unique_slug(Creation,title)); db.session.add(item)
        else: item.slug = unique_slug(Creation,title,item.id)
        item.title, item.description, item.category_id = title[:180], request.form.get("description","")[:20000], cat.id
        item.external_url = request.form.get("external_url","").strip()[:500] or None
        item.content_type = request.form.get("content_type","project")
        item.visibility = request.form.get("visibility","public") if request.form.get("visibility") in {"public","private"} else "private"
        item.published = request.form.get("published","yes") == "yes"
        item.access_mode = request.form.get("access_mode","free") if request.form.get("access_mode") in {"free","paid"} else "free"
        item.price = max(0,request.form.get("price",type=float) or 0)
        if cover: item.cover_filename = cover
        if asset: item.file_filename = asset
        db.session.commit(); flash("Creation saved.","success")
        return redirect(url_for("admin_creations"))
    return render_template("admin/creation_form.html",item=item,categories=categories)

@app.route("/admin/creations/<int:item_id>/toggle",methods=["POST"])
@admin_required
def toggle(item_id):
    item = db.session.get(Creation,item_id)
    if not item: abort(404)
    item.published = not item.published; db.session.commit()
    return redirect(url_for("admin_creations"))

@app.route("/admin/creations/<int:item_id>/delete",methods=["POST"])
@admin_required
def delete(item_id):
    item = db.session.get(Creation,item_id)
    if not item: abort(404)
    for filename in (item.cover_filename,item.file_filename):
        if filename:
            try: (UPLOADS/filename).unlink(missing_ok=True)
            except OSError: pass
    db.session.delete(item); db.session.commit()
    flash("Creation deleted.","success")
    return redirect(url_for("admin_creations"))

@app.route("/admin/categories",methods=["GET","POST"])
@admin_required
def categories_page():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        if name and not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name[:80],slug=unique_slug(Category,name))); db.session.commit()
            flash("Category created.","success")
        else: flash("Enter a unique category name.","error")
        return redirect(url_for("categories_page"))
    return render_template("admin/categories.html",categories=Category.query.order_by(Category.name).all())

@app.route("/admin/categories/<int:cat_id>/delete",methods=["POST"])
@admin_required
def delete_category(cat_id):
    cat = db.session.get(Category,cat_id)
    if not cat: abort(404)
    if cat.creations: flash("Move or delete creations in this category first.","error")
    else: db.session.delete(cat); db.session.commit(); flash("Category deleted.","success")
    return redirect(url_for("categories_page"))

@app.route("/admin/messages")
@admin_required
def messages_page():
    return render_template("admin/messages.html",messages=ContactMessage.query.order_by(ContactMessage.created_at.desc()).all())

@app.route("/admin/messages/<int:msg_id>/status",methods=["POST"])
@admin_required
def update_message(msg_id):
    msg = db.session.get(ContactMessage,msg_id)
    if not msg: abort(404)
    status=request.form.get("status","new")
    msg.status=status if status in {"new","reviewing","in_progress","completed","archived"} else "new"
    db.session.commit(); return redirect(url_for("messages_page"))

@app.errorhandler(413)
def too_large(_):
    flash("File too large. Maximum upload size is 50 MB.","error")
    return redirect(request.referrer or url_for("index"))

with app.app_context():
    db.create_all()
    for name in DEFAULT_CATEGORIES:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name,slug=unique_slug(Category,name)))
    if not Admin.query.first():
        username=os.getenv("ADMIN_USERNAME","admin")
        password=os.getenv("ADMIN_PASSWORD","ChangeMe-123!")
        db.session.add(Admin(username=username,password_hash=generate_password_hash(password)))
        print(f"[INITIAL ADMIN] username={username}")
        if "ADMIN_PASSWORD" not in os.environ: print("[INITIAL ADMIN] dev password=ChangeMe-123! CHANGE BEFORE DEPLOYMENT")
    db.session.commit()

if __name__ == "__main__":
    app.run(host="127.0.0.1",port=int(os.getenv("PORT","5000")),debug=os.getenv("FLASK_DEBUG","0")=="1")
