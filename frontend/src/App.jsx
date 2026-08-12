import { useEffect, useState } from 'react'
import { createProduct, fetchProducts } from './api'

const initialForm = {
  name: '',
  description: '',
  price: '',
  image_url: '',
  category: ''
}

export default function App() {
  const [products, setProducts] = useState([])
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadProducts() {
    try {
      setLoading(true)
      const data = await fetchProducts()
      setProducts(data)
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProducts()
  }, [])

  function onChange(e) {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  async function onSubmit(e) {
    e.preventDefault()
    try {
      await createProduct({ ...form, price: Number(form.price) })
      setForm(initialForm)
      await loadProducts()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <main className="container">
      <header>
        <h1>QutnCandy Clothing Store</h1>
        <p>Starter e-commerce portal scaffold</p>
      </header>

      <section className="card">
        <h2>Add Product</h2>
        <form onSubmit={onSubmit} className="form-grid">
          <input name="name" placeholder="Product name" value={form.name} onChange={onChange} required />
          <input name="category" placeholder="Category" value={form.category} onChange={onChange} />
          <input name="price" type="number" step="0.01" placeholder="Price" value={form.price} onChange={onChange} required />
          <input name="image_url" placeholder="Image URL" value={form.image_url} onChange={onChange} />
          <textarea
            name="description"
            placeholder="Description"
            value={form.description}
            onChange={onChange}
            rows={3}
          />
          <button type="submit">Create Product</button>
        </form>
      </section>

      <section className="card">
        <h2>Products</h2>
        {loading ? <p>Loading...</p> : null}
        {error ? <p className="error">{error}</p> : null}
        {!loading && !products.length ? <p>No products yet.</p> : null}

        <div className="products-grid">
          {products.map((p) => (
            <article key={p.id} className="product-item">
              {p.image_url ? <img src={p.image_url} alt={p.name} /> : <div className="placeholder">No image</div>}
              <h3>{p.name}</h3>
              <p>{p.description || 'No description'}</p>
              <p className="meta">{p.category || 'Uncategorized'}</p>
              <strong>${p.price.toFixed(2)}</strong>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}
