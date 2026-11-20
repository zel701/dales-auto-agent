"use client";

export function StepCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen w-full items-center justify-center px-4 py-20">
      <div className="w-full max-w-2xl rounded-xl bg-white p-8 shadow-[0_30px_18px_rgba(0,0,0,0.06)] sm:p-12">
        <h2 className="mb-2 font-serif text-2xl font-bold text-dark sm:text-3xl">
          {title}
        </h2>
        {subtitle && (
          <p className="mb-8 text-sm text-gray-400">{subtitle}</p>
        )}
        {!subtitle && <div className="mb-8" />}
        {children}
      </div>
    </div>
  );
}
