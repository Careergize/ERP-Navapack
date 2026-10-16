import { ArrowRight, Check, LoaderCircle } from "lucide-react";

export function Button({ loading, success, children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean; success?: boolean }) {
  return (
    <button {...props} className="flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-navy px-4 text-sm font-semibold text-white shadow-lg shadow-navy/20 transition hover:-translate-y-0.5 hover:bg-[#142d54] active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-60">
      {loading ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : success ? <Check className="h-4 w-4" aria-hidden="true" /> : null}
      {success ? "Signed in" : children}
      {!loading && !success && <ArrowRight className="h-4 w-4" aria-hidden="true" />}
    </button>
  );
}
