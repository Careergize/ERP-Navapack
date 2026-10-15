import type { JobCard, User } from '../types';
import { updateJobStage } from './jobCards';
import { convertQuantity } from './customCosting';
export type ProductionRun = NonNullable<JobCard['productionRuns']>[number];
export function appendProductionRun(card:JobCard,run:ProductionRun,finish:boolean,user:User,now=new Date().toISOString()):JobCard {
 const duplicate=card.productionRuns?.find(r=>r.id===run.id);if(duplicate){if(JSON.stringify({...duplicate,inputKG:undefined,completesStage:undefined})!==JSON.stringify({...run,inputKG:undefined,completesStage:undefined}) || duplicate.completesStage!==finish)throw new Error('Run request ID conflicts.');return card;}
 const stage=card.productionStages?.find(s=>s.id===run.stageId);if(!stage||!run.id||!run.number.trim()||card.productionRuns?.some(r=>r.number===run.number)||![run.inputQuantity,run.outputQuantity,run.wasteQuantity].every(n=>Number.isFinite(n)&&n>=0)||run.inputQuantity<=0||!run.operator.trim()||![run.startedAt,run.completedAt].every(t=>Number.isFinite(Date.parse(t)))||run.startedAt>run.completedAt||Date.parse(run.completedAt)>Date.parse(now))throw new Error('Complete distinct run identity, quantities, operator and valid chronological times.');
 if(run.inputUnit===run.outputUnit && (run.outputQuantity>run.inputQuantity+1e-6 || run.wasteUnit===run.inputUnit && run.outputQuantity+run.wasteQuantity>run.inputQuantity+1e-6))throw new Error('Run output/waste exceeds its own input.');
 if(run.inputUnit!==stage.inputUnit||run.outputUnit!==stage.outputUnit||run.wasteUnit!==stage.wasteUnit)throw new Error('Run units must match the approved stage units.');
 const priorStage=(card.productionStages??[]).filter(s=>s.required&&s.kind==='production'&&s.sequence<stage.sequence).sort((a,b)=>b.sequence-a.sequence)[0];if(priorStage?.completedAt&&Date.parse(run.startedAt)<Date.parse(priorStage.completedAt))throw new Error('Run cannot start before the previous stage completed.');
 const previous=(card.productionRuns??[]).filter(r=>r.stageId===stage.id);
 if(!previous.length&&stage.outputQuantity!==null&&stage.outputQuantity>0)throw new Error('Historical stage quantities cannot be replaced by run aggregates.');
 if(previous.some(r=>Date.parse(r.completedAt)>Date.parse(run.startedAt)))throw new Error('Runs of this stage cannot overlap.');
 let inputKG:number|undefined;try{inputKG=convertQuantity(run.inputQuantity,run.inputUnit,'kg');}catch{/* No invented package conversion. */}
 const saved={...run,inputKG,completesStage:finish},runs=[...(card.productionRuns??[]),saved],selected=runs.filter(r=>r.stageId===stage.id),sum=(key:'inputQuantity'|'outputQuantity'|'wasteQuantity')=>selected.reduce((n,r)=>n+r[key],0);
 if(stage.handover?.unit===stage.inputUnit&&sum('inputQuantity')>stage.handover.quantity+1e-6)throw new Error('Run input exceeds received stage input.');
 if(finish&&stage.handover?.unit===stage.inputUnit&&Math.abs(sum('inputQuantity')-stage.handover.quantity)>1e-6)throw new Error('Account for all handed-over input before completing this stage.');
 const next=updateJobStage(card,stage.id,{status:finish?'Completed':'InProgress',inputQuantity:stage.handover?.unit===stage.inputUnit?stage.handover.quantity:sum('inputQuantity'),outputQuantity:sum('outputQuantity'),wasteQuantity:sum('wasteQuantity'),inputUnit:stage.inputUnit,outputUnit:stage.outputUnit,wasteUnit:stage.wasteUnit,operator:run.operator,startedAt:selected[0].startedAt,completedAt:finish?run.completedAt:undefined,remarks:run.remarks,sentToRecycling:stage.sentToRecycling??0},user,now);
 return {...next,productionRuns:runs,activityHistory:[...(next.activityHistory??[]),{id:crypto.randomUUID(),timestamp:now,user:user.name,department:stage.department,action:'Production run recorded',description:`${run.number}; stage ${stage.name}; ${run.outputQuantity} ${run.outputUnit}; ${finish?'stage completed':'additional run allowed; no handover yet'}.`}]};
}
