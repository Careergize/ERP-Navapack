import { createContext, useContext, useRef, useState, type ReactNode } from 'react';
import { useAuth } from './AuthContext';
import { QC_TEMPLATES, CLEANING_AREAS } from '@/lib/qualityTemplates';
import { createInspection, saveInspection, submitInspection, reviewInspection, reinspect, releaseInspection, createNonConformance, updateNonConformance, validateTemplate, type QCState, type QCTemplate, type QCInspection, type QCSubject, type QCApproval, type QCRelease, type QCNonConformance } from '@/lib/quality';

interface QualityValue extends QCState {
  templates: QCTemplate[];
  areas: { id: string; name: string }[];
  getState: () => QCState;
  create: (template: QCTemplate, subject: QCSubject, date: string, department: string, samples: number) => QCInspection;
  save: (id: string, draft: Pick<QCInspection, 'time' | 'responses' | 'metadata' | 'comments'>) => void;
  submit: (id: string) => void;
  review: (id: string, decision: QCApproval['decision'], remarks: string) => void;
  reinspection: (id: string) => QCInspection;
  release: (id: string, purpose: QCRelease['purpose'], accepted?: number, rejected?: number) => void;
  reportFinding: (id: string, description: string, severity: QCNonConformance['severity']) => void;
  updateFinding: (id: string, change: Parameters<typeof updateNonConformance>[1]) => void;
  reviseTemplate: (template: QCTemplate) => void;
  assign: (id: string, userId: string) => void;
  addArea: (name: string) => void;
}
const Context = createContext<QualityValue | undefined>(undefined);
export function QualityProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [state, setState] = useState<QCState>({ inspections: [], releases: [], nonConformances: [] });
  const current = useRef(state);
  const [templates, setTemplates] = useState(QC_TEMPLATES); const templateRef = useRef(templates);
  const [areas, setAreas] = useState(CLEANING_AREAS);
  const actor = () => { if (!user) throw new Error('Sign in to update quality records.'); return user; };
  const publish = (next: QCState) => { current.current = next; setState(next); };
  const get = (id: string) => { const i = current.current.inspections.find(i => i.id === id); if (!i) throw new Error('Inspection not found.'); return i; };
  const replace = (i: QCInspection) => publish({ ...current.current, inspections: current.current.inspections.map(row => row.id === i.id ? i : row) });
  return <Context.Provider value={{ ...state, templates, areas, getState: () => current.current,
    create: (template, subject, date, department, samples) => { const selected = templateRef.current.find(t => t.id === template.id && t.revision === template.revision); if (!selected || templateRef.current.some(t => t.id === template.id && t.revision > template.revision)) throw new Error('Select the latest template revision.'); const i = createInspection(selected, subject, actor(), date, department, samples); publish({ ...current.current, inspections: [...current.current.inspections, i] }); return i; },
    save: (id, draft) => replace(saveInspection(get(id), draft, actor())),
    submit: id => replace(submitInspection(get(id), actor())),
    review: (id, decision, remarks) => replace(reviewInspection(get(id), decision, remarks, actor())),
    reinspection: id => { const next = reinspect(get(id), actor()); publish({ ...current.current, inspections: [...current.current.inspections, next] }); return next; },
    release: (id, purpose, accepted, rejected) => publish(releaseInspection(current.current, id, purpose, `${purpose}-${id}`, actor(), accepted, rejected)),
    reportFinding: (id, description, severity) => { const n = createNonConformance(get(id), description, severity, actor()); publish({ ...current.current, nonConformances: [...current.current.nonConformances, n] }); },
    updateFinding: (id, change) => { const n = current.current.nonConformances.find(n => n.id === id); if (!n) throw new Error('Finding not found.'); const next = updateNonConformance(n, change, actor()); publish({ ...current.current, nonConformances: current.current.nonConformances.map(row => row.id === id ? next : row) }); },
    reviseTemplate: template => { if (actor().role !== 'admin') throw new Error('Admin manages templates.'); validateTemplate(template); const latest = Math.max(0, ...templateRef.current.filter(t => t.id === template.id).map(t => t.revision)); const next = { ...structuredClone(template), revision: latest + 1 }; templateRef.current = [...templateRef.current, next]; setTemplates(templateRef.current); },
    assign: (id, userId) => { const i = get(id); const u = actor(); if (u.role !== 'admin' || i.status !== 'Draft' || !userId.trim()) throw new Error('Admin assigns draft inspections to a stable user ID.'); replace({ ...i, assignedTo: userId, events: [...i.events, { id: crypto.randomUUID(), type: 'Assigned', userId: u.id, user: u.name, at: new Date().toISOString(), description: `Assigned to ${userId}.` }] }); },
    addArea: name => { if (actor().role !== 'admin' || !name.trim()) throw new Error('Admin can add cleaning areas.'); setAreas(list => [...list, { id: crypto.randomUUID(), name: name.trim() }]); },
  }}>{children}</Context.Provider>;
}
export function useQuality() { const value = useContext(Context); if (!value) throw new Error('QualityProvider required'); return value; }
