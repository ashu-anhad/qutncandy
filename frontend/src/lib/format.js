// All money from the API is in paise.
const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export const formatPrice = (paise) => (paise == null ? "" : inr.format(paise / 100));
export const toPaise = (rupees) => (rupees === "" || rupees == null ? null : Math.round(Number(rupees) * 100));
export const toRupees = (paise) => (paise == null ? "" : String(paise / 100));

export const COLOUR_HEX = {
  white: "#f7f5f0", ivory: "#efe6d2", "powder blue": "#c9dbe8", mint: "#cfe6d8", "blush pink": "#f1d3d3",
  peach: "#f5d5bd", lavender: "#dcd3ec", lemon: "#f2ebb5", black: "#2c2c2c", sage: "#b9c7ad",
  pink: "#f4c6d4", blue: "#a9c4e0", yellow: "#f4e27a", green: "#a8cfa0", beige: "#e5d8bf", grey: "#bdbab3",
};
export const colourHex = (name) => COLOUR_HEX[name?.toLowerCase()] ?? "#d8d2c6";

// Groups categories into [{...parent, children: [...]}] for menus and selects.
export function categoryTree(categories = []) {
  const roots = categories.filter((c) => !c.parent_id);
  return roots.map((r) => ({ ...r, children: categories.filter((c) => c.parent_id === r.id) }));
}

export const ORDER_STATUS = {
  pending_payment: "Awaiting payment",
  paid: "Paid",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

export const formatDateTime = (iso) =>
  new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" });
export const formatDate = (iso) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

export const REFUND_STATUS = { required: "Refund due", refunded: "Refunded" };
