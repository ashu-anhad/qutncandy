import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as cartApi from "./api/cart";
import { useAuth } from "./auth.jsx";

// Guests keep [{variant_id, qty}] in localStorage; logged-in carts live on the server.
// Both are priced by the backend, so the cart always shows current prices and stock.
const GUEST_KEY = "qc_guest_cart";
const MAX_QTY = 10;

const readGuest = () => {
  try {
    return JSON.parse(localStorage.getItem(GUEST_KEY)) || [];
  } catch {
    return [];
  }
};
const writeGuest = (items) => {
  try {
    if (items.length) localStorage.setItem(GUEST_KEY, JSON.stringify(items));
    else localStorage.removeItem(GUEST_KEY);
  } catch {
    /* storage unavailable: cart lasts for this page view only */
  }
};

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const { user, loading } = useAuth();
  const queryClient = useQueryClient();
  const [guestItems, setGuestItems] = useState(readGuest);
  const [merging, setMerging] = useState(false);

  const queryKey = user ? ["cart", user.id] : ["cart", "guest", guestItems];
  const cart = useQuery({
    queryKey,
    queryFn: () => (user ? cartApi.getCart() : cartApi.previewCart(guestItems)),
    enabled: !loading && !merging,
    placeholderData: (prev) => prev,
  });

  const updateGuest = useCallback((fn) => {
    setGuestItems((prev) => {
      const next = fn(prev).filter((i) => i.qty > 0);
      writeGuest(next);
      return next;
    });
  }, []);

  // On login, fold the guest cart into the account's cart once.
  useEffect(() => {
    if (!user || !guestItems.length) return;
    setMerging(true);
    cartApi
      .mergeCart(guestItems)
      .then((data) => queryClient.setQueryData(["cart", user.id], data))
      .finally(() => {
        updateGuest(() => []);
        setMerging(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  const setServerCart = (data) => queryClient.setQueryData(["cart", user.id], data);

  const value = useMemo(
    () => ({
      cart: cart.data,
      isLoading: cart.isLoading,
      count: cart.data?.item_count ?? 0,
      add: async (variantId, qty = 1) => {
        if (user) return setServerCart(await cartApi.addToCart(variantId, qty));
        updateGuest((items) => {
          const found = items.find((i) => i.variant_id === variantId);
          return found
            ? items.map((i) => (i === found ? { ...i, qty: Math.min(i.qty + qty, MAX_QTY) } : i))
            : [...items, { variant_id: variantId, qty }];
        });
      },
      setQty: async (variantId, qty) => {
        if (user) return setServerCart(await cartApi.setCartQty(variantId, qty));
        updateGuest((items) => items.map((i) => (i.variant_id === variantId ? { ...i, qty } : i)));
      },
      remove: async (variantId) => {
        if (user) return setServerCart(await cartApi.removeFromCart(variantId));
        updateGuest((items) => items.filter((i) => i.variant_id !== variantId));
      },
      refresh: () => queryClient.invalidateQueries({ queryKey: ["cart"] }),
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [cart.data, cart.isLoading, user, updateGuest]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export const useCart = () => useContext(CartContext);
