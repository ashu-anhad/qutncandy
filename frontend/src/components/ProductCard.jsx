import { Link } from "react-router-dom";
import Price from "./Price.jsx";
import Stars from "./Stars.jsx";
import Swatch from "./Swatch.jsx";

export default function ProductCard({ product }) {
  return (
    <Link to={`/p/${product.slug}`} className="product-card">
      <div className="product-card-img">
        {product.image ? <img src={product.image} alt={product.name} loading="lazy" /> : <div className="img-placeholder" />}
        {!product.in_stock && <span className="badge">Sold out</span>}
      </div>
      <div className="product-card-body">
        <span className="muted small">{product.category.name}</span>
        <span className="product-card-name">{product.name}</span>
        <span>
          {product.min_price !== product.max_price && <span className="muted small">From </span>}
          <Price min={product.min_price} />
        </span>
        {product.review_count > 0 && (
          <span className="row card-rating"><Stars value={product.avg_rating} size={12} /><span className="muted small">({product.review_count})</span></span>
        )}
        <span className="swatches">
          {product.colours.map((c) => <Swatch key={c} colour={c} />)}
        </span>
      </div>
    </Link>
  );
}
