import { validDate } from './stockIntelligence';
import { createInspection, subjectKey, type QCInspection, type QCTemplate, type QCSubject } from './quality';
import type { User } from '../types';
export interface QCSchedule { id:string; templateId:string; subject:QCSubject; frequency:QCTemplate['frequency']; startDate:string; endDate?:string; shift?:string; assignedTo:string; department:string; active:boolean; createdBy:string; createdAt:string }
export function validateSchedule(s:QCSchedule,t:QCTemplate){
 if(!s.id||!s.assignedTo.trim()||!s.department.trim()||!validDate(s.startDate)||(s.endDate&&(!validDate(s.endDate)||s.endDate<s.startDate))||!t.active||s.templateId!==t.id||s.subject.kind!==t.category||s.frequency!==t.frequency)throw new Error('Use an active template, exact subject, assignment, matching configured frequency and valid date range.');
 if(['raw','production'].includes(s.subject.kind)&&!['per_receipt','per_batch','on_demand','per_activity'].includes(s.frequency))throw new Error('Receipt/batch inspections need a new exact source; do not recur a consumed physical lot.');
 if(s.frequency==='per_shift'&&!s.shift?.trim())throw new Error('Per-shift schedules require an explicit shift identifier.');
}
export function scheduleDue(s:QCSchedule,date:string){if(!s.active||!validDate(date)||date<s.startDate||(s.endDate&&date>s.endDate))return false;const days=(Date.parse(date)-Date.parse(s.startDate))/86400000;return s.frequency==='daily'||s.frequency==='per_shift'||s.frequency==='weekly'&&days%7===0||s.frequency==='monthly'&&date.slice(8)===s.startDate.slice(8)||['per_receipt','per_batch','on_demand','per_activity'].includes(s.frequency)&&date===s.startDate;}
export function generateScheduled(s:QCSchedule,t:QCTemplate,date:string,all:QCInspection[],user:User):QCInspection|undefined{
 validateSchedule(s,t);if(!scheduleDue(s,date))return;const key=`${s.id}:${date}:${s.shift??''}`;if(all.some(i=>i.scheduleKey===key || i.date===date && i.template.id===t.id && subjectKey(i.subject)===subjectKey(s.subject) && (i.metadata.shift??'')===(s.shift??'')))return;
 const i=createInspection(t,s.subject,user,date,s.department);return {...i,scheduleKey:key,assignedTo:s.assignedTo,metadata:{...i.metadata,scheduleId:s.id,shift:s.shift??''}};
}
