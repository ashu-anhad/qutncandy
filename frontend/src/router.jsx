import { createBrowserRouter } from "react-router-dom";
import { RequireAuth } from "./auth.jsx";
import AdminLayout from "./components/AdminLayout.jsx";
import Layout from "./components/Layout.jsx";
import Account from "./pages/Account.jsx";
import Cart from "./pages/Cart.jsx";
import Checkout from "./pages/Checkout.jsx";
import Home from "./pages/Home.jsx";
import ForgotPassword from "./pages/ForgotPassword.jsx";
import Login from "./pages/Login.jsx";
import Notifications from "./pages/Notifications.jsx";
import ResetPassword from "./pages/ResetPassword.jsx";
import NotFound from "./pages/NotFound.jsx";
import OrderDetail from "./pages/OrderDetail.jsx";
import Orders from "./pages/Orders.jsx";
import ProductDetail from "./pages/ProductDetail.jsx";
import ProductList from "./pages/ProductList.jsx";
import Categories from "./pages/admin/Categories.jsx";
import Dashboard from "./pages/admin/Dashboard.jsx";
import Discounts from "./pages/admin/Discounts.jsx";
import Inventory from "./pages/admin/Inventory.jsx";
import AdminOrders from "./pages/admin/Orders.jsx";
import OrderView from "./pages/admin/OrderView.jsx";
import Reports from "./pages/admin/Reports.jsx";
import AdminReviews from "./pages/admin/Reviews.jsx";
import ProductEdit from "./pages/admin/ProductEdit.jsx";
import Products from "./pages/admin/Products.jsx";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: "products", element: <ProductList /> },
      { path: "c/:slug", element: <ProductList /> },
      { path: "p/:slug", element: <ProductDetail /> },
      { path: "cart", element: <Cart /> },
      { path: "checkout", element: <RequireAuth><Checkout /></RequireAuth> },
      { path: "orders", element: <RequireAuth><Orders /></RequireAuth> },
      { path: "orders/:number", element: <RequireAuth><OrderDetail /></RequireAuth> },
      { path: "notifications", element: <RequireAuth><Notifications /></RequireAuth> },
      { path: "login", element: <Login /> },
      { path: "forgot-password", element: <ForgotPassword /> },
      { path: "reset-password", element: <ResetPassword /> },
      { path: "account", element: <RequireAuth><Account /></RequireAuth> },
      { path: "*", element: <NotFound /> },
    ],
  },
  {
    path: "/admin",
    element: <RequireAuth admin><AdminLayout /></RequireAuth>,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "orders", element: <AdminOrders /> },
      { path: "orders/:number", element: <OrderView /> },
      { path: "inventory", element: <Inventory /> },
      { path: "reviews", element: <AdminReviews /> },
      { path: "reports", element: <Reports /> },
      { path: "products", element: <Products /> },
      { path: "products/:id", element: <ProductEdit /> },
      { path: "categories", element: <Categories /> },
      { path: "discounts", element: <Discounts /> },
    ],
  },
]);
