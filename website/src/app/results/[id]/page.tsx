import { getResults } from "@/lib/clients/agent-client";
import { ResultsClient } from "./results-client";

export default async function ResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  try {
    const data = await getResults(id);
    return <ResultsClient data={data} resultsId={id} />;
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Could not load results.";
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-lg">
          <h2 className="mb-3 font-serif text-2xl font-bold text-dark">
            Oops
          </h2>
          <p className="text-foreground/70">{message}</p>
        </div>
      </div>
    );
  }
}
