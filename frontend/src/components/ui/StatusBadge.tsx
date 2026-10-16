const STATUS_STYLES: Record<string, string> = {
  Reserved: "bg-blue/10 text-blue",
  "Stock Received": "bg-green/10 text-green",
  "Partially Dispatched": "bg-amber-50 text-amber-700",
  Dispatched: "bg-green/10 text-green",
  Cancelled: "bg-red-50 text-red-700",
  Draft: "bg-gray-100 text-gray-600",
  PendingApproval: "bg-navy/10 text-navy",
  Approved: "bg-blue/10 text-blue",
  Issued: "bg-blue/10 text-blue",
  InProduction: "bg-teal/10 text-teal",
  Pending: "bg-gray-100 text-gray-600",
  InProgress: "bg-teal/10 text-teal",
  Completed: "bg-green/10 text-green",
  Complete: "bg-green/10 text-green",
  Open: "bg-blue/10 text-blue",
  "Pending Approval": "bg-navy/10 text-navy",
  "Store Issue Pending": "bg-navy/10 text-navy",
  "Material Issued": "bg-blue/10 text-blue",
  "In Production": "bg-teal/10 text-teal",
  "In Progress": "bg-teal/10 text-teal",
  Received: "bg-blue/10 text-blue",
  "On Hold": "bg-amber-50 text-amber-700",
  Delayed: "bg-red-50 text-red-700",
  "Ready for Stock": "bg-green/10 text-green",
  "Sent to Recycling": "bg-green/10 text-green",
  "Awaiting Pickup": "bg-navy/10 text-navy",
};

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>
      {status}
    </span>
  );
}
