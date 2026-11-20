import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/header";
import { CustomerSessionProvider } from "@/lib/customer-session";

export const metadata: Metadata = {
  title: "Car Analysis | Get Your Free Report",
  description:
    "Get a detailed analysis of your car's market value, insurance estimates, and common issues.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">
        <CustomerSessionProvider>
          <Header />
          {children}
        </CustomerSessionProvider>
      </body>
    </html>
  );
}
