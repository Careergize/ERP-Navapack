import { createContext, useContext, useRef, useState, type ReactNode } from 'react';
import { MOCK_MODELS } from '@/lib/mockData';
import { useAuth } from './AuthContext';
import type { Model } from '@/types';
import { reviseProductModel } from '@/lib/productModels';
export interface Machine { id: string; name: string; department: string; type: 'extruder' | 'recycle_extruder'; active: boolean }
const Context = createContext<{ machines: Machine[]; addMachine: (machine: Omit<Machine, 'id'>) => void; models: Model[]; versions: Model[]; saveModel: (model: Model) => Model } | undefined>(undefined);
export function ModelsProvider({ children }: { children: ReactNode }) {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [versions, setVersions] = useState<Model[]>(() => MOCK_MODELS.map(m => ({ ...m, revision: 1 })));
  const current = useRef(versions); const { user } = useAuth();
  const models = versions.filter(m => !versions.some(n => n.id === m.id && (n.revision ?? 1) > (m.revision ?? 1)));
  const saveModel = (model: Model) => {
    if (!user || !['admin', 'production_manager', 'receptionist'].includes(user.role)) throw new Error('Your role cannot draft models.');
    const next = reviseProductModel(model, current.current); current.current = [...current.current, next]; setVersions(current.current); return next;
  };
  return <Context.Provider value={{ models, versions, saveModel, machines, addMachine: machine => { if (user?.role !== 'admin' || !machine.name.trim() || !machine.department.trim()) throw new Error('Admin must provide machine name and department.'); setMachines(rows => [...rows, { ...machine, id: crypto.randomUUID() }]); } }}>{children}</Context.Provider>;
}
export function useModels() { const value = useContext(Context); if (!value) throw new Error('ModelsProvider required'); return value; }
