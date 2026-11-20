import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Demo } from "./demo-client";

export const metadata: Metadata = {
  title: "Dales Auto Agent | Negotiation Demo",
  description: "Try a simulated dealership negotiation with human approval at each step.",
};

export default async function DemoPage() {
  await connection();
  if (!process.env.DEMO_API_URL) notFound();
  return <Demo />;
}
