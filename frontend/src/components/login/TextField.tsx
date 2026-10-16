import { forwardRef, InputHTMLAttributes, ReactNode } from "react";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  icon?: ReactNode;
  trailing?: ReactNode;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(function TextField({ label, error, icon, trailing, id, ...props }, ref) {
  const inputId = id ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div>
      <label htmlFor={inputId} className="mb-2 block text-sm font-medium text-ink">{label}</label>
      <div className="relative">
        {icon && <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">{icon}</span>}
        <input ref={ref} id={inputId} aria-invalid={Boolean(error)} aria-describedby={error ? `${inputId}-error` : undefined} {...props} className={`min-h-12 w-full rounded-lg border bg-white px-4 text-sm text-ink shadow-sm transition placeholder:text-slate-400 focus:border-teal focus:outline-none focus:ring-4 focus:ring-teal/15 ${icon ? "pl-10" : ""} ${trailing ? "pr-12" : ""} ${error ? "border-red-400 focus:border-red-500 focus:ring-red-100" : "border-slate-200"}`} />
        {trailing}
      </div>
      {error && <p id={`${inputId}-error`} className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
});

