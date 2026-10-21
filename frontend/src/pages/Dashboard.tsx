import { PersistedDashboard } from '@/pages/PersistedDashboard';
import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useSalesOrders } from '@/context/SalesOrdersContext';
import { useJobCards } from '@/context/JobCardsContext';
import { useInventory } from '@/context/InventoryContext';
import { useCosting } from '@/context/CostingContext';
import { useQuality } from '@/context/QualityContext';
import { useQuotations } from '@/context/QuotationsContext';
import { useAuth } from '@/context/AuthContext';
import { Card } from '@/components/ui/Card';
import { StockAlerts } from '@/components/StockIntelligence';
import { salesMetrics } from '@/lib/operations';
import { workItems } from '@/lib/parentJobCards';
import { FINISHED_GOODS, finishedBalance } from '@/lib/finishedGoodsData';
import { RAW_MATERIALS, rawMaterialBalance } from '@/lib/rawMaterialData';
import { today } from '@/lib/salesOrders';
import { canViewQC, subjectHeld } from '@/lib/quality';
import { effectiveQuotationStatus, QUOTATION_VIEW_ROLES } from '@/lib/quotations';
const grouped=(rows:{unit:string;quantity:number|null}[])=>{const sums:Record<string,number>={};let unknown=0;rows.forEach(r=>{if(r.quantity===null)unknown++;else sums[r.unit]=(sums[r.unit]??0)+r.quantity;});return Object.entries(sums).map(([u,n])=>`${n.toLocaleString()} ${u}`).join(' · ')+(unknown?` · ${unknown} unknown balances`:'');};
const money=(values:Record<string,number>)=>Object.entries(values).map(([c,n])=>`${n.toLocaleString()} ${c}`).join(' · ')||'No recorded confirmed value';
function Stats({title,values,link}:{title:string;values:Record<string,string|number>;link:string}){return <Card><Link className="font-semibold text-navy underline" to={link}>{title}</Link><dl className="mt-3 grid gap-3 sm:grid-cols-3">{Object.entries(values).map(([k,v])=><div key={k}><dt className="text-sm text-gray-500">{k}</dt><dd className="font-medium">{v}</dd></div>)}</dl></Card>;}
export function Dashboard() {
 const { user } = useAuth();
 return user?.backendSession ? <PersistedDashboard/> : <DemoDashboard/>;
}
function DemoDashboard() {
 const {orders}=useSalesOrders(),{cards,load}=useJobCards(),inv=useInventory(),cost=useCosting(),q=useQuality(),quotes=useQuotations(),{user}=useAuth();useEffect(()=>{void load();},[load]);
 const m=salesMetrics(orders,cards,inv.ledger),items=cards.flatMap(workItems),date=today(),stages=items.flatMap(j=>j.productionStages??[]);
 const commercial=QUOTATION_VIEW_ROLES.includes(user?.role??''),costAccess=['admin','accounts','production_manager'].includes(user?.role??'');
 const latest=cost.stockPrices.filter(p=>!cost.stockPrices.some(n=>n.productId===p.productId&&n.batch===p.batch&&n.revision>p.revision));
 const sum=(key:'estimatedCOP'|'vat'|'selectedLED'|'profit')=>latest.reduce((s,p)=>s+p.breakdown[key],0).toLocaleString()+' UGX';
 return <div className="space-y-5"><h1 className="text-2xl font-semibold text-navy">Operations dashboard</h1><p className="text-sm text-gray-500">{date} · Current session state, including preserved sample records. Values are grouped by unit/currency. Quotation values are offers; dispatch value is not automatically invoiced revenue.</p>
 {commercial&&<Stats title="Sales Overview" link="/sales-orders" values={{'Sales Orders':m.total,'Products / unlinked lines':m.products,'Ordered quantities':Object.entries(m.units).map(([u,n])=>`${n} ${u}`).join(' · ')||'None','Confirmed order value':money(m.confirmed),'Dispatched commercial value':money(m.dispatched),'Pending orders':m.pending,'Partially dispatched':m.partial,'Completed / dispatched':m.completed,'Require manufacturing':m.manufacturing,'Linked parent Job Cards':m.linkedCards,'Unloaded references':m.unloadedCardReferences,'Quotations awaiting response':quotes.quotations.filter(q=>!quotes.quotations.some(n=>n.rootId===q.rootId&&n.revision>q.revision)&&effectiveQuotationStatus(q)==='Sent').length}}/>}
 <Stats title="Production Overview" link="/job-cards" values={{'Active parent cards':cards.filter(c=>c.status!=='Completed').length,'Pending parent approvals':cards.filter(c=>['Draft','PendingApproval'].includes(c.status)).length,'Items in production':items.filter(c=>c.status==='InProduction').length,'Completed parent cards':cards.filter(c=>c.status==='Completed').length,'Delayed items':items.filter(c=>c.requiredDate&&c.requiredDate<date&&c.status!=='Completed').length,"Today's final-stage output":grouped(items.flatMap(c=>{const s=(c.productionStages??[]).filter(s=>s.kind==='production'&&s.required).sort((a,b)=>a.sequence-b.sequence).at(-1);return s?.completedAt?.slice(0,10)===date?[{quantity:s.outputQuantity,unit:s.outputUnit}]:[]}))||'None recorded','Recorded production waste':grouped(stages.map(s=>({quantity:s.wasteQuantity,unit:s.wasteUnit})))||'None recorded'}}/>
 <Stats title="Stock Overview" link="/stock" values={{'Finished Goods':grouped(FINISHED_GOODS.map(p=>({unit:p.unit,quantity:finishedBalance(p,inv.finishedMovements).currentStock}))),'Raw Materials':grouped(RAW_MATERIALS.map(p=>({unit:p.unit,quantity:rawMaterialBalance(p,inv.rawMovements).currentStock}))),'Pending finished receipt items':items.filter(c=>c.status==='ReadyForStock').length,'Recent Stock OUT (today)':inv.finishedMovements.filter(m=>m.type==='OUT'&&m.date===date).length}}/><StockAlerts compact/>
 {costAccess&&<Stats title="Costing Overview" link="/costing" values={{'Saved product/batch snapshots':latest.length,'Estimated COP':sum('estimatedCOP'),'Recorded actual COP':latest.some(s=>s.actualCOP!==undefined)?latest.filter(s=>s.actualCOP!==undefined).reduce((n,s)=>n+s.actualCOP!,0).toLocaleString()+' UGX':'Actual Cost Not Available','Actual cost coverage':`${latest.filter(s=>s.actualCOP!==undefined).length} of ${latest.length} snapshots`,'Profit / markup amounts':sum('profit'),'VAT':sum('vat'),'LED':sum('selectedLED'),'Recorded variance':latest.filter(s=>s.actualCOP!==undefined).reduce((n,s)=>n+s.actualCOP!-s.breakdown.estimatedCOP,0).toLocaleString()+' UGX (covered snapshots only)','Approved estimates':cost.estimates.filter(e=>e.status==='Approved').length}}/>}
 <Stats title="Traceability Overview" link="/track-trace" values={{'Recent batch movements (today)':inv.finishedMovements.filter(m=>m.date===date&&m.batch).length,'Items under production':items.filter(c=>c.status==='InProduction').length,'Awaiting QC':items.filter(c=>c.status==='ReadyForStock').length,'Unmapped manufacturing items':items.filter(c=>!c.finishedProductId).length,'Movements without KG snapshots':inv.finishedMovements.filter(m=>m.quantitySnapshot?.convertedKG==null).length}}/>
 {canViewQC(user?.role)&&<Stats title="Quality Control Overview" link="/qc" values={{'Inspections due today':q.inspections.filter(i=>i.date===date&&i.status==='Draft').length,'Pending QC subjects':new Set(q.inspections.filter(i=>subjectHeld(q,i.subject)).map(i=>JSON.stringify(i.subject))).size,'Failed inspections':q.inspections.filter(i=>i.status==='Failed').length,'Open corrective actions':q.nonConformances.filter(n=>n.status!=='Closed').length}}/>}
 </div>;
}
