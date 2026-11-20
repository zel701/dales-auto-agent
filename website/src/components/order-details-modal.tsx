"use client";

import { useState } from "react";
import { PhoneNumber, type CreditScoreRange } from "@/lib/schemas";

export type OrderDetails = {
  first_name: string;
  phone: string;
  need_by_date: string;
  payment_method: "finance" | "cash";
  credit_score_range?: CreditScoreRange;
  delivery_method: "pickup" | "ship";
};

const CREDIT_OPTIONS: { value: CreditScoreRange; label: string }[] = [
  { value: "780_plus", label: "780 or above" },
  { value: "720_779", label: "720 – 779" },
  { value: "660_719", label: "660 – 719" },
  { value: "600_659", label: "600 – 659" },
  { value: "under_600", label: "Below 600" },
];

function todayIso(): string {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

type FormProps = {
  onClose: () => void;
  onSubmit: (values: OrderDetails) => void;
  submitting: boolean;
  count: number;
};

/** Closing unmounts the form, so reopening starts from blank fields — no
 * reset effect needed. */
export function OrderDetailsModal({
  open,
  ...props
}: FormProps & { open: boolean }) {
  if (!open) return null;
  return <OrderDetailsForm {...props} />;
}

function OrderDetailsForm({ onClose, onSubmit, submitting, count }: FormProps) {
  const [firstName, setFirstName] = useState("");
  const [phone, setPhone] = useState("");
  const [needBy, setNeedBy] = useState("");
  const [payment, setPayment] = useState<"finance" | "cash" | "">("");
  const [credit, setCredit] = useState<CreditScoreRange | "">("");
  const [delivery, setDelivery] = useState<"pickup" | "ship" | "">("");

  const parsedPhone = PhoneNumber.safeParse(phone);
  const creditReady = payment !== "finance" || credit !== "";
  const ready =
    firstName.trim() &&
    parsedPhone.success &&
    needBy &&
    payment &&
    creditReady &&
    delivery &&
    !submitting;

  function choosePayment(method: "finance" | "cash") {
    setPayment(method);
    // A cash order carries no credit tier — drop any answer given before the
    // buyer switched away from financing.
    if (method === "cash") setCredit("");
  }

  function handleSubmit() {
    if (!ready || !parsedPhone.success) return;
    onSubmit({
      first_name: firstName.trim(),
      phone: parsedPhone.data,
      need_by_date: needBy,
      payment_method: payment as "finance" | "cash",
      ...(payment === "finance" && credit
        ? { credit_score_range: credit as CreditScoreRange }
        : {}),
      delivery_method: delivery as "pickup" | "ship",
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-xl bg-white p-6 shadow-[0_30px_18px_rgba(0,0,0,0.06)] sm:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-2 font-serif text-2xl font-bold text-dark">
          A few quick questions
        </h2>
        <p className="mb-6 text-sm text-foreground/60">
          Help us negotiate {count} listing{count !== 1 ? "s" : ""} on your
          behalf.
        </p>

        <div className="mb-5">
          <label className="mb-2 block text-sm font-medium text-dark">
            First name
          </label>
          <input
            type="text"
            autoComplete="given-name"
            placeholder="Alex"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-pink focus:outline-none"
          />
        </div>

        <div className="mb-5">
          <label className="mb-2 block text-sm font-medium text-dark">
            Phone number
          </label>
          <input
            type="tel"
            autoComplete="tel"
            placeholder="(555) 123-4567"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-pink focus:outline-none"
          />
          <p className="mt-1.5 text-xs text-foreground/50">
            Only shared with the dealership once a price is agreed.
          </p>
        </div>

        <div className="mb-5">
          <label className="mb-2 block text-sm font-medium text-dark">
            When do you need the car by?
          </label>
          <input
            type="date"
            min={todayIso()}
            value={needBy}
            onChange={(e) => setNeedBy(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-pink focus:outline-none"
          />
        </div>

        <div className="mb-5">
          <span className="mb-2 block text-sm font-medium text-dark">
            Payment method
          </span>
          <div className="grid grid-cols-2 gap-2">
            <RadioCard
              label="Finance"
              checked={payment === "finance"}
              onSelect={() => choosePayment("finance")}
            />
            <RadioCard
              label="Cash"
              checked={payment === "cash"}
              onSelect={() => choosePayment("cash")}
            />
          </div>
        </div>

        {payment === "finance" && (
          <div className="mb-5">
            <span className="mb-2 block text-sm font-medium text-dark">
              Credit score range
            </span>
            <div className="grid gap-2">
              {CREDIT_OPTIONS.map((option) => (
                <RadioCard
                  key={option.value}
                  label={option.label}
                  checked={credit === option.value}
                  onSelect={() => setCredit(option.value)}
                />
              ))}
            </div>
            <p className="mt-1.5 text-xs text-foreground/50">
              An estimate is fine — it helps us judge the financing offers.
            </p>
          </div>
        )}

        <div className="mb-5">
          <span className="mb-2 block text-sm font-medium text-dark">
            Delivery method
          </span>
          <div className="grid grid-cols-2 gap-2">
            <RadioCard
              label="Pick up myself"
              checked={delivery === "pickup"}
              onSelect={() => setDelivery("pickup")}
            />
            <RadioCard
              label="Ship to my home"
              checked={delivery === "ship"}
              onSelect={() => setDelivery("ship")}
            />
          </div>
        </div>

        <p className="mb-6 rounded-lg bg-background p-3 text-xs text-foreground/60">
          Note: we don&apos;t support trade-ins for now — this request covers
          the purchase only.
        </p>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm font-bold text-dark transition-colors hover:bg-background disabled:opacity-60"
          >
            Back
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!ready}
            className={`flex-[2] rounded-lg px-4 py-3 text-sm font-bold text-white transition-colors ${
              ready
                ? "bg-pink hover:bg-pink-dark cursor-pointer"
                : "bg-gray-300 cursor-not-allowed"
            }`}
          >
            {submitting ? "Submitting..." : "Submit request"}
          </button>
        </div>
      </div>
    </div>
  );
}

function RadioCard({
  label,
  checked,
  onSelect,
}: {
  label: string;
  checked: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors ${
        checked
          ? "border-pink bg-pink/5 text-pink"
          : "border-gray-300 bg-white text-dark hover:bg-background"
      }`}
    >
      {label}
    </button>
  );
}
