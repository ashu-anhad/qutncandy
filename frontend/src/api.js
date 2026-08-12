const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function fetchProducts() {
  const response = await fetch(`${API_BASE_URL}/api/products`)
  if (!response.ok) throw new Error('Failed to load products')
  return response.json()
}

export async function createProduct(product) {
  const response = await fetch(`${API_BASE_URL}/api/products`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(product)
  })

  if (!response.ok) throw new Error('Failed to create product')
  return response.json()
}
