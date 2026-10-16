import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { api } from './api';
import { useAuth } from '@/context/AuthContext';

export interface UnitRecord { id: number; code: string; name: string; is_active: boolean }

export async function loadUnits(activeOnly = true): Promise<UnitRecord[]> {
  const rows: UnitRecord[] = [];
  for (let page = 1; ; page++) {
    const { data } = await api.get<{ results: UnitRecord[]; next: string | null }>('/units/', { params: { ...(activeOnly ? { active: 'true' } : {}), page } });
    rows.push(...data.results);
    if (!data.next) return rows;
  }
}

export function unitError(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail ?? (error.response ? JSON.stringify(error.response.data) : 'Unable to load or save units. Check the backend connection.');
  return error instanceof Error ? error.message : 'Unable to process units.';
}

export function useUnits(activeOnly = true) {
  const { user } = useAuth();
  const [units, setUnits] = useState<UnitRecord[]>([]), [loading, setLoading] = useState(false), [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion(v => v + 1), []);
  useEffect(() => {
    let live = true;
    setUnits([]); setError(''); setLoading(false);
    if (!user) return;
    if (user.id.startsWith('demo-')) { setError('Sign in with a backend account to load the unit master.'); return; }
    setLoading(true);
    loadUnits(activeOnly).then(rows => { if (live) setUnits(rows); }).catch(e => { if (live) setError(unitError(e)); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [user?.id, activeOnly, version]);
  return { units, loading, error, reload };
}
