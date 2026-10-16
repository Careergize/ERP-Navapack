import { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-card border border-gray-100 bg-white p-5 shadow-sm ${className}`}>
      {children}
    </div>
  );
}
