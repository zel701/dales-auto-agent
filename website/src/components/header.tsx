"use client";

import { useState } from "react";
import { LoginModal } from "@/components/login-modal";
import { useCustomerSession } from "@/lib/customer-session";

export function Header() {
  const { customer, loading, logout } = useCustomerSession();
  const [open, setOpen] = useState(false);

  return (
    <>
      <header className="pointer-events-none fixed inset-x-0 top-0 z-40 flex justify-end p-4">
        <div className="pointer-events-auto">
          {loading ? null : customer ? (
            <div className="flex items-center gap-3 rounded-full bg-white/90 px-4 py-2 text-sm shadow-sm backdrop-blur">
              <span className="hidden text-foreground/70 sm:inline">
                {customer.email}
              </span>
              <span className="inline text-foreground/70 sm:hidden">
                Signed in
              </span>
              <button
                type="button"
                onClick={() => void logout()}
                className="font-medium text-pink transition-colors hover:text-pink-dark"
              >
                Logout
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="rounded-full bg-white/90 px-5 py-2 text-sm font-bold text-pink shadow-sm backdrop-blur transition-colors hover:bg-white hover:text-pink-dark"
            >
              Login
            </button>
          )}
        </div>
      </header>
      <LoginModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
