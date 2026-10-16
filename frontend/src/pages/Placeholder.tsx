import { Card } from "@/components/ui/Card";

export function Placeholder({ title }: { title: string }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-navy">{title}</h1>
      <Card className="mt-6">
        <p className="text-sm text-gray-500">This module follows the same list/detail pattern as Job Cards.</p>
      </Card>
    </div>
  );
}
