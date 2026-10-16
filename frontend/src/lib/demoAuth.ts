import type { Role } from '../types';
export const demoEnabled=(dev:boolean,setting:string|undefined)=>setting==='true'||dev&&setting!=='false';
export function demoRole(email:string,password:string,selected:Role,finance=false):Role{
 const name=email.trim().toLowerCase();
 if(password!=='test@123')throw new Error('credentials');
 if(name==='finance@navapack.com')return 'accounts';
 if(!finance&&['admin@navapack.com','admin@navpack.com'].includes(name))return selected;
 throw new Error('credentials');
}
