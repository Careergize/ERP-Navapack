import { useSalesOrders } from '@/context/SalesOrdersContext';
import { useInventory } from '@/context/InventoryContext';
import { useJobCards } from '@/context/JobCardsContext';
import { salesMetrics } from '@/lib/operations';
import { Card } from './ui/Card';
export function SalesSummary(){const {orders}=useSalesOrders(),{ledger}=useInventory(),{cards}=useJobCards();const m=salesMetrics(orders,cards,ledger);return <Card><h2 className="font-semibold">Sales Order summary (all session orders)</h2><div className="grid gap-3 text-sm sm:grid-cols-4">{Object.entries({'Orders':m.total,'Distinct linked products / unlinked lines':m.products,'Order lines':m.lines,'Linked parent Job Cards loaded':m.linkedCards,'Unloaded Job Card references':m.unloadedCardReferences,'Orders requiring production':m.manufacturing,'Stock-only orders':m.stockOrders,'Partially dispatched':m.partial,'Production-for-stock cards':m.forStock}).map(([k,v])=><p key={k}>{k}: <strong>{v}</strong></p>)}</div><p className="mt-2 text-sm">Ordered quantities: {Object.entries(m.units).map(([u,n])=>`${n} ${u}`).join(' · ')||'None'}</p></Card>;}
