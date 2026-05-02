import { Suspense } from "react";
import NewestClient from "./NewestClient";

export const dynamic = "force-dynamic";

export default function NewestPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen p-6 sm:px-12 md:px-24 pt-12 pb-24 w-full max-w-5xl mx-auto font-sans text-slate-500">
          正在加载...
        </div>
      }
    >
      <NewestClient />
    </Suspense>
  );
}
