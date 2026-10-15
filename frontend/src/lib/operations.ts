import { calculateCommercialTotals } from './commercialPricing';
import type { SalesOrder, JobCard } from '../types';
import type { FulfillmentLedger } from './fulfillment';
import { orderFulfillmentStatus } from './fulfillment';
import { productionStages } from './jobCards';
import { convertQuantity, roundMoney } from './customCosting';
export function salesMetrics(orders:SalesOrder[],cards:JobCard[],ledger:FulfillmentLedger) {
  const units:Record<string,number>={},confirmed:Record<string,number>={},dispatched:Record<string,number>={}; const products=new Set<string>(); let lines=0;
  const statuses=orders.map(o=>orderFulfillmentStatus(o,ledger,cards));
  orders.forEach(o=>{(o.items??[]).forEach(i=>{lines++;products.add(i.itemId??(i.modelId?`model:${i.modelId}`:`unlinked:${o.id}:${i.id}`));if(o.status!=='Cancelled')units[i.unit]=(units[i.unit]??0)+i.quantity;});
    const knownConfirmed=!['Draft','Open','Cancelled'].includes(o.status)||ledger.dispatches.some(d=>d.orderId===o.id&&d.status==='Confirmed');
    if(knownConfirmed&&o.currency&&o.orderTotal!==undefined)confirmed[o.currency]=roundMoney((confirmed[o.currency]??0)+o.orderTotal);
    if(o.currency){const items=o.items??[],basis=items.reduce((s,i)=>s+i.totalPrice,0);ledger.dispatches.filter(d=>d.orderId===o.id&&d.status==='Confirmed').forEach(d=>{const i=items.find(i=>i.id===d.itemId);if(i){const value=items.some(l=>l.ledSnapshot)?calculateCommercialTotals([{quantity:d.quantity,unitPrice:i.unitPrice,ledSnapshot:i.ledSnapshot?{...i.ledSnapshot,selectedAmount:i.ledSnapshot.selectedAmount*d.quantity/i.quantity}:undefined}],(o.commercialPricing?.discount??0)*(basis?i.unitPrice*d.quantity/basis:0),o.taxRate??0,o.commercialPricing?.taxMode??'exclusive').total:i.unitPrice*d.quantity*(basis&&o.orderTotal!==undefined?o.orderTotal/basis:1);dispatched[o.currency!]=roundMoney((dispatched[o.currency!]??0)+value);}});}
  });
  return {total:orders.length,products:products.size,lines,units,confirmed,dispatched,linkedCards:new Set(cards.filter(c=>orders.some(o=>o.id===c.salesOrderId)).map(c=>c.id)).size,unloadedCardReferences:new Set(orders.flatMap(o=>o.jobCardIds).filter(id=>!cards.some(c=>c.id===id))).size,manufacturing:orders.filter(o=>o.items?.some(i=>i.fulfillmentSource==='manufacturing')).length,stockOrders:orders.filter(o=>o.items?.length&&o.items.every(i=>i.fulfillmentSource==='stock')).length,partial:statuses.filter(s=>s==='Partially Dispatched').length,completed:statuses.filter(s=>['Completed','Dispatched'].includes(s)).length,pending:statuses.filter(s=>!['Completed','Dispatched','Cancelled'].includes(s)).length,forStock:cards.filter(c=>c.origin==='production_for_stock'&&!c.salesOrderId).length};
}
export function stageTracking(card:JobCard) {
  const stages=productionStages(card),current=stages.find(s=>['Received','InProgress','OnHold'].includes(s.status))??stages.find(s=>s.status==='Pending');
  return {stages,current,next:current?stages.find(s=>s.sequence>current.sequence&&s.status!=='Completed'):undefined,completed:stages.filter(s=>s.status==='Completed'),pending:stages.filter(s=>s.status!=='Completed'),lastUpdate:(card.activityHistory??[]).map(e=>e.timestamp).sort().at(-1)};
}
export function massBalance(card:JobCard) {
  const stages=productionStages(card),first=stages[0],last=stages.at(-1);
  const kg=(q:number|null|undefined,u:string|undefined)=>{if(q===null||q===undefined||!u)return null;try{return convertQuantity(q,u,'kg');}catch{return null;}};
  const input=kg(first?.inputQuantity,first?.inputUnit),output=kg(last?.outputQuantity,last?.outputUnit),wastes=stages.map(s=>kg(s.wasteQuantity,s.wasteUnit));
  const waste=wastes.length&&wastes.every(n=>n!==null)?wastes.reduce<number>((s,n)=>s+(n??0),0):null;
  const difference=input!==null&&output!==null&&waste!==null?Math.round((input-output-waste)*1e6)/1e6:null;
  return {input,output,waste,difference,otherLosses:null,message:difference===null?'Insufficient compatible KG measurements':difference!==0?'Unexplained difference — review other process losses / measurement basis':'Measured quantities reconcile; other losses are not recorded'};
}
