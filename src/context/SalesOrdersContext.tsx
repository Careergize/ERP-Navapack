import { createContext, useContext, useRef, useState, type ReactNode } from 'react';
import { MOCK_SALES_ORDERS } from '@/lib/mockData';
import { buildSalesOrder, type SalesOrderDraft } from '@/lib/salesOrders';
import type { SalesOrder } from '@/types';

interface OrdersContextValue {
  orders: SalesOrder[];
  getOrders: () => SalesOrder[];
  linkFinishedProduct: (orderId: string, itemId: string, productId: string) => void;
  linkEstimate: (orderId: string, itemId: string, estimateId: string) => void;
  linkJob: (orderId: string, jobId: string) => void;
  createSalesOrder: (draft: SalesOrderDraft) => SalesOrder;
}
const OrdersContext = createContext<OrdersContextValue | undefined>(undefined);
export function SalesOrdersProvider({ children }: { children: ReactNode }) {
  // Temporary frontend-only store: survives navigation, resets on browser refresh.
  // TODO: Load orders and replace createSalesOrder with backend API calls.
  const [orders, setOrders] = useState<SalesOrder[]>(MOCK_SALES_ORDERS);
  const current = useRef(orders);
  const createSalesOrder = (draft: SalesOrderDraft) => {
    const existing = draft.quotationId ? current.current.find(o => o.quotationId === draft.quotationId) : undefined;
    if (existing) return existing;
    const order = buildSalesOrder(draft, current.current);
    current.current = [order, ...current.current];
    setOrders(current.current);
    return order;
  };
  return <OrdersContext.Provider value={{ orders, getOrders: () => current.current, createSalesOrder, linkFinishedProduct: (orderId, itemId, productId) => { current.current = current.current.map(o => o.id === orderId ? { ...o, items: o.items?.map(i => i.id === itemId ? { ...i, itemId: productId } : i) } : o); setOrders(current.current); }, linkEstimate: (orderId, itemId, estimateId) => { current.current = current.current.map(o => o.id === orderId ? { ...o, items: o.items?.map(i => i.id === itemId ? { ...i, estimateId } : i) } : o); setOrders(current.current); }, linkJob: (orderId, jobId) => { current.current = current.current.map(o => o.id === orderId ? { ...o, jobCardIds: [...new Set([...o.jobCardIds, jobId])] } : o); setOrders(current.current); } }}>{children}</OrdersContext.Provider>;
}
export function useSalesOrders() {
  const value = useContext(OrdersContext);
  if (!value) throw new Error('SalesOrdersProvider is required');
  return value;
}
