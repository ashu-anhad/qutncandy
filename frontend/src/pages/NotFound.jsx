import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="center">
      <h1>Page not found</h1>
      <Link to="/">Back to home</Link>
    </section>
  );
}
