import { createContext, useContext, useRef, useState, type ReactNode } from 'react';
import { createInvoice, type Invoice, type InvoiceDraft } from '@/lib/invoices';
import { useInventory } from './InventoryContext';
import { useSalesOrders } from './SalesOrdersContext';
import { useAuth } from './AuthContext';
const Context = createContext<{ invoices: Invoice[]; create: (orderId: string, draft: InvoiceDraft) => void } | undefined>(undefined);
export function InvoicesProvider({ children }: { children: ReactNode }) {
  const [invoices, setInvoices] = useState<Invoice[]>([]); const current = useRef(invoices); const { ledger } = useInventory(); const { orders } = useSalesOrders(); const { user } = useAuth();
  return <Context.Provider value={{ invoices, create: (orderId, draft) => {
    if (!user || !['admin', 'accounts', 'receptionist'].includes(user.role)) throw new Error('Your role cannot issue invoices.');
    const order = orders.find(o => o.id === orderId); if (!order) throw new Error('Order not found.');
    const invoice = createInvoice(draft, order, ledger.dispatches, current.current); current.current = [...current.current, invoice]; setInvoices(current.current);
  } }}>{children}</Context.Provider>;
}
export function useInvoices() { const value = useContext(Context); if (!value) throw new Error('InvoicesProvider required'); return value; }
