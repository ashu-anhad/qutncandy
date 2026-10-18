import { startPayment, verifyPayment } from "../api/orders";

const SCRIPT_URL = "https://checkout.razorpay.com/v1/checkout.js";
let scriptPromise = null;

function loadScript() {
  scriptPromise ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_URL;
    script.onload = resolve;
    script.onerror = () => {
      scriptPromise = null;
      reject(new Error("Couldn't load the payment window. Check your connection and try again."));
    };
    document.body.appendChild(script);
  });
  return scriptPromise;
}

export class PaymentDismissed extends Error {
  constructor() {
    super("Payment was not completed.");
  }
}

// Opens Razorpay for an unpaid order. Resolves with the updated (paid) order;
// rejects with PaymentDismissed if the customer closes the window.
export async function payForOrder(number) {
  const opts = await startPayment(number);
  await loadScript();
  return new Promise((resolve, reject) => {
    const rzp = new window.Razorpay({
      key: opts.key_id,
      order_id: opts.razorpay_order_id,
      amount: opts.amount,
      currency: opts.currency,
      name: opts.name,
      description: opts.description,
      prefill: opts.prefill,
      theme: { color: "#1f1d18" },
      handler: (response) => verifyPayment(response).then(resolve, reject),
      modal: { ondismiss: () => reject(new PaymentDismissed()) },
    });
    rzp.open();
  });
}
