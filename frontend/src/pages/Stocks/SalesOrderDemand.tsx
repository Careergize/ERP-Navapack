import { Link } from 'react-router-dom';
import { reserved } from '@/lib/fulfillment';
import { useSalesOrders } from '@/context/SalesOrdersContext';
import { useInventory } from '@/context/InventoryContext';
import { findFinishedGood, finishedBalance, finishedGoodLabel } from '@/lib/finishedGoodsData';

export function SalesOrderDemand() {
  const { orders } = useSalesOrders();
  const { finishedMovements, ledger } = useInventory();
  // TODO: Replace demand projection with backend inventory requirements.
  // Each line compares against physical stock; no reservations or deductions.
  const requirements = orders.filter(order => !['Completed', 'Cancelled'].includes(order.status)).flatMap(order => (order.items ?? []).map(item => {
    const product = findFinishedGood(item.itemId, item.itemName, item.unit);
    const sameUnit = product?.unit === item.unit;
    const physical = product && sameUnit ? finishedBalance(product, finishedMovements).currentStock : null;
    const available = physical === null || !product ? null : physical - reserved(ledger, product.id);
    const dispatched = ledger.dispatches.filter(d => d.orderId === order.id && d.itemId === item.id && d.status === 'Confirmed').reduce((sum, d) => sum + d.quantity, 0);
    const demand = Math.max(0, item.quantity - dispatched);
    const required = available === null ? null : Math.max(0, demand - Math.max(0, available));
    const status = !product ? 'Not linked' : !sameUnit ? 'Unit mismatch' : available === null ? 'Not recorded' : available >= item.quantity ? 'Available' : available > 0 ? 'Partially Available' : 'Not Available';
    return { ...item, product, available, required, status, orderNumber: order.orderNumber, customer: order.customerName };
  }));
  return <section className="overflow-hidden rounded-card border border-gray-200 bg-white" aria-label="Sales Order Demand">
    <div className="border-b border-gray-200 p-4"><h2 className="font-semibold text-navy">Sales Order Demand</h2><p className="mt-1 text-xs text-gray-500">Open orders · Required Qty is the shortage against current unreserved stock. Each line is a frontend comparison; comparison does not post transactions. Reservations and confirmed dispatches share the inventory ledger.</p></div>
    {!requirements.length ? <p className="p-6 text-sm text-gray-500">Create a sales order to see its finished-goods requirements here.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm">
      <thead className="border-b border-gray-200 bg-gray-50 text-xs text-gray-500"><tr>{['Order', 'Customer', 'Product / Variant', 'Ordered Qty', 'Available Finished Stock', 'Required Qty', 'Unit', 'Status'].map(label => <th key={label} scope="col" className="px-4 py-3 font-medium">{label}</th>)}</tr></thead>
      <tbody className="divide-y divide-gray-100">{requirements.map(item => <tr key={`${item.orderNumber}-${item.id}`} className="hover:bg-gray-50">
        <td className="px-4 py-3 font-medium text-navy"><Link to={`/sales-orders/${orders.find(o => o.orderNumber === item.orderNumber)?.id}`} className="underline">{item.orderNumber}</Link></td><td className="px-4 py-3">{item.customer}</td><td className="max-w-[300px] px-4 py-3">{item.product ? finishedGoodLabel(item.product) : item.itemName}{!item.product && <p className="mt-1 text-xs text-gray-400">Link this legacy item to a finished-goods variant.</p>}</td>
        <td className="px-4 py-3 tabular-nums">{item.quantity.toLocaleString('en-IN')}</td><td className="px-4 py-3 tabular-nums">{item.available === null ? '—' : item.available.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td><td className="px-4 py-3 tabular-nums">{item.required === null ? '—' : item.required.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td><td className="px-4 py-3">{item.unit}</td>
        <td className="px-4 py-3"><span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${item.status === 'Available' ? 'bg-emerald-50 text-emerald-700' : item.status === 'Not Available' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'}`}>{item.status}</span></td>
      </tr>)}</tbody>
    </table></div>}
  </section>;
}
