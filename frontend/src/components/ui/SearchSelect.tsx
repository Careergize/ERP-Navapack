import { useId, useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';

export interface SearchOption { id: string; name: string; detail?: string }
interface Props {
  label: string; value: string; options: SearchOption[]; error?: string; inputId?: string;
  onChange: (value: string) => void; onSelect: (option: SearchOption) => void;
  onAdvance?: () => void;
}
export const ENTRY_INPUT = 'block w-full rounded-card border border-gray-200 px-3 py-2 text-sm text-ink focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy';
export function SearchSelect({ label, value, options, error, inputId, onChange, onSelect, onAdvance }: Props) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [position, setPosition] = useState({ left: 0, top: 0, width: 260, maxHeight: 224 });
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [searching, setSearching] = useState(false);
  const normalizeSearch = (text: string) => text.toLowerCase().replace(/\s+/g, '');
  const matches = options.filter(option => !searching || normalizeSearch(`${option.name} ${option.detail ?? ''}`).includes(normalizeSearch(value)));
  useLayoutEffect(() => {
    if (!open) return;
    const positionPanel = () => {
      const rect = input.current?.getBoundingClientRect();
      if (!rect) return;
      const below = window.innerHeight - rect.bottom - 12;
      const height = Math.min(224, Math.max(100, below >= 160 ? below : rect.top - 12));
      const width = Math.min(Math.max(rect.width, 260), window.innerWidth - 16);
      setPosition({ left: Math.min(rect.left, window.innerWidth - width - 8), top: below >= 160 ? rect.bottom + 4 : Math.max(8, rect.top - height - 4), width, maxHeight: height });
    };
    positionPanel();
    window.addEventListener('resize', positionPanel);
    window.addEventListener('scroll', positionPanel, true);
    return () => { window.removeEventListener('resize', positionPanel); window.removeEventListener('scroll', positionPanel, true); };
  }, [open]);
  const highlighted = Math.min(active, matches.length - 1);
  const choose = (option: SearchOption) => { onSelect(option); setOpen(false); setSearching(false); };
  const keydown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape' && open) { event.preventDefault(); event.stopPropagation(); setOpen(false); }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault(); setOpen(true);
      setActive(current => Math.max(0, Math.min(matches.length - 1, current + (event.key === 'ArrowDown' ? 1 : -1))));
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      if (open && matches[highlighted]) choose(matches[highlighted]);
      onAdvance?.();
    }
  };
  return <div className="relative min-w-[220px]">
    <input ref={input} id={inputId} aria-label={label} role="combobox" aria-autocomplete="list" aria-expanded={open} aria-controls={`${id}-list`} aria-activedescendant={open && matches[highlighted] ? `${id}-${highlighted}` : undefined} aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined}
      autoComplete="off" value={value} onFocus={() => { setOpen(true); setSearching(false); setActive(0); }} onBlur={() => setOpen(false)}
      onChange={event => { onChange(event.target.value); setSearching(true); setOpen(true); setActive(0); }} onKeyDown={keydown} className={ENTRY_INPUT} />
    {open && createPortal(<ul id={`${id}-list`} role="listbox" aria-label={`${label} choices`} style={position} className="fixed z-[60] overflow-auto rounded-card border border-gray-200 bg-white shadow-lg">
      {matches.length ? matches.map((option, index) => <li key={option.id} id={`${id}-${index}`} role="option" aria-selected={index === highlighted} onMouseDown={event => event.preventDefault()} onClick={() => choose(option)} className={`cursor-pointer px-3 py-2 text-sm ${index === highlighted ? 'bg-sky-50 text-navy' : 'text-gray-700 hover:bg-gray-50'}`}><span className="block font-medium">{option.name}</span>{option.detail && <span className="mt-0.5 block text-xs text-gray-500">{option.detail}</span>}</li>) : <li className="px-3 py-3 text-sm text-gray-500">No matching results</li>}
    </ul>, document.body)}
    {error && <p id={`${id}-error`} role="alert" className="mt-1 text-xs text-red-600">{error}</p>}
  </div>;
}
