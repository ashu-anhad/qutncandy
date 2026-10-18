import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useCart } from "../cart.jsx";
import { getProduct } from "../api/catalog";
import Price from "../components/Price.jsx";
import Reviews from "../components/Reviews.jsx";
import Stars from "../components/Stars.jsx";
import Swatch from "../components/Swatch.jsx";
import { formatPrice } from "../lib/format";

export default function ProductDetail() {
  const { slug } = useParams();
  const { hash } = useLocation();
  const { data: product, isLoading, error } = useQuery({ queryKey: ["product", slug], queryFn: () => getProduct(slug) });

  const [colour, setColour] = useState(null);
  const [size, setSize] = useState(null);
  const [imageIndex, setImageIndex] = useState(0);
  const { add } = useCart();
  const [added, setAdded] = useState(false);
  const [cartError, setCartError] = useState("");

  // Default to the first colour that has stock.
  useEffect(() => {
    if (!product) return;
    const firstInStock = product.variants.find((v) => v.stock > 0) ?? product.variants[0];
    setColour(firstInStock?.colour ?? null);
    setSize(null);
  }, [product]);

  useEffect(() => {
    setAdded(false);
    setCartError("");
  }, [size, colour]);

  const images = useMemo(() => {
    if (!product) return [];
    const forColour = product.images.filter((i) => i.colour === colour || i.colour === null);
    return forColour.length ? forColour : product.images;
  }, [product, colour]);

  useEffect(() => setImageIndex(0), [colour]);

  // Links like /p/slug#reviews (from the order page) scroll once the product has loaded.
  useEffect(() => {
    if (product && hash === "#reviews") document.getElementById("reviews")?.scrollIntoView();
  }, [product, hash]);

  if (isLoading) return <p className="muted">Loading…</p>;
  if (error) return error.status === 404 ? <NotFoundProduct /> : <p className="error">{error.message}</p>;

  const variantFor = (s, c = colour) => product.variants.find((v) => v.size === s && v.colour === c);
  const selected = size ? variantFor(size) : null;
  const colourHasStock = (c) => product.variants.some((v) => v.colour === c && v.stock > 0);
  const image = images[imageIndex];

  return (
    <div className="pdp">
      <div className="gallery">
        <div className="gallery-main">
          {image ? <img src={image.url} alt={`${product.name} in ${colour}`} /> : <div className="img-placeholder" />}
        </div>
        {images.length > 1 && (
          <div className="thumbs">
            {images.map((img, i) => (
              <button key={img.id} className={`thumb${i === imageIndex ? " selected" : ""}`} onClick={() => setImageIndex(i)}>
                <img src={img.url} alt="" />
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="pdp-info stack">
        <nav className="muted small">
          <Link to="/products">Shop</Link> / <Link to={`/c/${product.category.slug}`}>{product.category.name}</Link>
        </nav>
        <h1>{product.name}</h1>
        {product.review_count > 0 && (
          <a href="#reviews" className="row rating-link">
            <Stars value={product.avg_rating} /> <span className="small">{product.avg_rating.toFixed(1)} · {product.review_count} review{product.review_count > 1 ? "s" : ""}</span>
          </a>
        )}
        <div className="pdp-price">
          {selected ? <span className="price">{formatPrice(selected.effective_price)}</span> : <Price min={product.min_price} max={product.max_price} />}
          <span className="muted small">Inclusive of all taxes</span>
        </div>

        <div className="option">
          <span className="option-label">Colour: <strong>{colour}</strong></span>
          <div className="row">
            {product.colours.map((c) => (
              <span key={c} className={colourHasStock(c) ? "" : "faded"}>
                <Swatch colour={c} size={30} selected={c === colour} onClick={() => { setColour(c); setSize(null); }} />
              </span>
            ))}
          </div>
        </div>

        <div className="option">
          <span className="option-label">Size{size ? `: ${size}` : ""}</span>
          <div className="chips">
            {product.sizes.map((s) => {
              const v = variantFor(s);
              const available = v && v.stock > 0;
              return (
                <button
                  key={s}
                  type="button"
                  className={`chip size${size === s ? " selected" : ""}${available ? "" : " unavailable"}`}
                  disabled={!available}
                  onClick={() => setSize(s)}
                  title={available ? undefined : "Out of stock"}
                >
                  {s}
                </button>
              );
            })}
          </div>
        </div>

        <StockNote variant={selected} />

        <button
          disabled={!selected || selected.stock === 0}
          onClick={() => add(selected.id).then(() => setAdded(true)).catch((e) => setCartError(e.message))}
        >
          {selected ? "Add to cart" : "Select a size"}
        </button>
        {added && <span className="stock ok small">Added to your cart · <Link to="/cart">View cart</Link></span>}
        {cartError && <span className="stock out small">{cartError}</span>}

        <div className="pdp-details">
          <h2>Details</h2>
          <p>{product.description}</p>
          <dl>
            <dt>Fabric</dt><dd>{product.fabric}</dd>
            <dt>Work</dt><dd>Hand-embroidered Lucknowi chikankari</dd>
            {selected && <><dt>SKU</dt><dd>{selected.sku}</dd></>}
          </dl>
        </div>
      </div>
      <div className="pdp-reviews">
        <Reviews slug={product.slug} />
      </div>
    </div>
  );
}

function StockNote({ variant }) {
  if (!variant) return <span className="muted small">Select a size</span>;
  if (variant.stock === 0) return <span className="stock out">Out of stock</span>;
  if (variant.stock <= 3) return <span className="stock low">Only {variant.stock} left</span>;
  return <span className="stock ok">In stock</span>;
}

function NotFoundProduct() {
  return (
    <section className="center">
      <h1>Product not found</h1>
      <Link to="/products">Browse the collection</Link>
    </section>
  );
}
