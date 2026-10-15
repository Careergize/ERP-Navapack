import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuotations } from '@/context/QuotationsContext';
import { useAuth } from '@/context/AuthContext';
export function GenerateQuotation({customerId,prospectId,estimateId}:{customerId?:string;prospectId?:string;estimateId?:string}){const store=useQuotations(),nav=useNavigate(),{user}=useAuth(),[error,setError]=useState('');if(!['admin','receptionist','accounts'].includes(user?.role??''))return null;return <span><button type="button" className="rounded-card border px-3 py-2 text-sm text-navy" onClick={()=>{try{const q=store.generateQuotation({customerId,prospectId,estimateId});nav(`/quotations/${q.id}${q.status==='Draft'?'/edit':''}`);}catch(e){setError(e instanceof Error?e.message:'Unable to generate quotation.');}}}>Generate Quotation</button>{error&&<span role="alert" className="ml-2 text-sm text-red-700">{error}</span>}</span>;}
