import { useState } from 'react';
import { InventoryCustody } from './InventoryCustody';
import { InventoryOperations } from './InventoryOperations';
import { InventoryFoundation } from './InventoryFoundation';

export function InventoryModule({itemType,title}: {itemType:'variant'|'material'|'consumable';title:string}) {
  const [tab,setTab]=useState('balances');
  return <section className="space-y-5"><h1 className="text-2xl font-semibold text-navy">{title}</h1>
    <p>Backend records from your approved warehouse scopes. Development movements are synthetic and do not represent operational available stock.</p>
    <nav className="flex flex-wrap gap-3">{[['balances','Balances / movements'],['operations','Stock IN / OUT / openings / transfers / counts'],['configuration','Identity / warehouse configuration']].map(([id,label])=><button key={id} className={`rounded-xl border p-3 ${id===tab?'bg-navy text-white':'bg-white'}`} onClick={()=>setTab(id)}>{label}</button>)}</nav>
    {tab==='balances'?<InventoryCustody initialItemType={itemType}/>:tab==='operations'?<InventoryOperations/>:<InventoryFoundation/>}
    <button className="rounded border p-2" disabled title="Operational posting requires approved physical evidence, authority and rollout.">Operational stock posting unavailable</button>
  </section>;
}
