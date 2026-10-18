"""Sample catalog for development. Safe to re-run: skips if products already exist."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog import service
from app.catalog.models import Category, Product
from app.core.storage import save_file

COLOURS = {
    "White": "#f7f5f0", "Ivory": "#efe6d2", "Powder Blue": "#c9dbe8", "Mint": "#cfe6d8",
    "Blush Pink": "#f1d3d3", "Peach": "#f5d5bd", "Lavender": "#dcd3ec", "Lemon": "#f2ebb5",
    "Black": "#2c2c2c", "Sage": "#b9c7ad",
}

CATEGORIES = [
    ("Women", None), ("Men", None),
    ("Kurtas", "Women"), ("Kurta Sets", "Women"), ("Sarees", "Women"), ("Dupattas", "Women"),
    ("Men's Kurtas", "Men"),
]

WOMEN = ["XS", "S", "M", "L", "XL", "XXL"]
MEN = ["S", "M", "L", "XL", "XXL"]
FREE = ["Free Size"]

# name, category, base price (₹), sizes, colours, description
PRODUCTS = [
    ("Noor Hand-Embroidered Straight Kurta", "Kurtas", 1890, WOMEN, ["White", "Powder Blue", "Blush Pink"],
     "A breezy straight-cut kurta with dense bakhiya and phanda work along the yoke and hem."),
    ("Gulnaar A-Line Chikankari Kurta", "Kurtas", 2250, WOMEN, ["Mint", "Peach"],
     "Flared A-line silhouette with all-over floral jaal, finished with delicate murri knots."),
    ("Zoya Short Kurti", "Kurtas", 1290, WOMEN, ["White", "Lemon", "Lavender"],
     "Hip-length everyday kurti with scattered butis and a scalloped hem."),
    ("Mehr Anarkali Kurta", "Kurtas", 3490, ["S", "M", "L", "XL"], ["Ivory", "Blush Pink"],
     "Twenty-four kali anarkali with tepchi panels and keel-kangan detailing on the bodice."),
    ("Rooh Kurta with Palazzo Set", "Kurta Sets", 3290, WOMEN, ["White", "Sage"],
     "Straight kurta paired with matching embroidered palazzos. Two-piece set."),
    ("Ishq Three-Piece Kurta Set", "Kurta Sets", 4590, ["S", "M", "L", "XL", "XXL"], ["Powder Blue", "Peach"],
     "Kurta, straight pants and a mul-cotton dupatta, all hand-embroidered in Lucknow."),
    ("Saba Cotton Chikankari Saree", "Sarees", 5490, FREE, ["White", "Ivory"],
     "Six-yard soft cotton saree with a jaali border and pallu worked in shadow (bakhiya) stitch."),
    ("Shabnam Pastel Saree", "Sarees", 6290, FREE, ["Mint", "Lavender"],
     "Lightweight cotton saree with all-over buti and a hand-finished border. Blouse piece included."),
    ("Nazakat Mul Cotton Dupatta", "Dupattas", 990, FREE, ["White", "Blush Pink", "Lemon"],
     "Feather-light mul cotton dupatta with corner motifs and a fine pittan border."),
    ("Jaal Bordered Dupatta", "Dupattas", 1490, FREE, ["Ivory", "Black"],
     "Statement dupatta with a wide hand-embroidered jaal border on all four sides."),
    ("Aftab Classic Men's Kurta", "Men's Kurtas", 1990, MEN, ["White", "Ivory", "Black"],
     "Straight-fit men's kurta with placket and collar embroidery. A festive essential."),
    ("Riyaz Long Chikankari Kurta", "Men's Kurtas", 2690, MEN, ["Powder Blue", "Sage"],
     "Knee-length kurta with tonal chikankari down the front and on the cuffs."),
]


def placeholder_svg(colour: str, label: str) -> bytes:
    bg = COLOURS.get(colour, "#e8e1d6")
    ink = "#ffffff" if colour != "White" else "#d9d2c3"
    if colour == "Black":
        ink = "#8a8378"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800" width="600" height="800">
<defs>
  <pattern id="buti" width="60" height="60" patternUnits="userSpaceOnUse">
    <g fill="none" stroke="{ink}" stroke-width="1.6" opacity="0.85">
      <circle cx="30" cy="30" r="3" fill="{ink}"/>
      <ellipse cx="30" cy="21" rx="3.5" ry="7"/><ellipse cx="30" cy="39" rx="3.5" ry="7"/>
      <ellipse cx="21" cy="30" rx="7" ry="3.5"/><ellipse cx="39" cy="30" rx="7" ry="3.5"/>
    </g>
    <circle cx="0" cy="0" r="1.6" fill="{ink}"/><circle cx="60" cy="60" r="1.6" fill="{ink}"/>
  </pattern>
</defs>
<rect width="600" height="800" fill="{bg}"/>
<path d="M230 120 L270 100 Q300 130 330 100 L370 120 L470 200 L430 270 L400 245 L405 700 L195 700 L200 245 L170 270 L130 200 Z"
  fill="{bg}" stroke="{ink}" stroke-width="3" opacity="0.95"/>
<path d="M230 120 L270 100 Q300 130 330 100 L370 120 L470 200 L430 270 L400 245 L405 700 L195 700 L200 245 L170 270 L130 200 Z"
  fill="url(#buti)"/>
<text x="300" y="760" text-anchor="middle" font-family="Georgia, serif" font-size="22" fill="{ink if colour != 'White' else '#8a8378'}">{label}</text>
</svg>""".encode()


def seed(db: Session) -> str:
    if db.scalar(select(func.count()).select_from(Product)):
        return "Products already exist; skipping seed."

    cats: dict[str, Category] = {}
    for i, (name, parent) in enumerate(CATEGORIES):
        cat = db.scalar(select(Category).where(Category.name == name))
        if cat is None:
            cat = Category(name=name, slug=service.unique_slug(db, Category, name), sort_order=i,
                           parent_id=cats[parent].id if parent else None)
            db.add(cat)
            db.flush()
        cats[name] = cat

    for name, cat, rupees, sizes, colours, desc in PRODUCTS:
        product = Product(
            category_id=cats[cat].id, name=name, slug=service.unique_slug(db, Product, name),
            description=desc, fabric="Pure cotton", base_price=rupees * 100,
        )
        db.add(product)
        db.flush()
        for ci, colour in enumerate(colours):
            for si, size in enumerate(sizes):
                # Bigger sizes cost a little more; stock varies so some variants show as sold out.
                price = rupees * 100 + 20000 if size in ("XXL", "3XL") else None
                stock = (ci * 7 + si * 3 + product.id) % 9
                service.add_variant(db, product, {"size": size, "colour": colour, "price": price, "stock": stock})
            url = save_file(placeholder_svg(colour, colour), "products", "svg")
            service.add_image(db, product, url, colour)
            db.flush()
            db.refresh(product)
    db.commit()
    return f"Seeded {len(CATEGORIES)} categories and {len(PRODUCTS)} products."
